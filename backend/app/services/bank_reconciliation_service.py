"""Bank reconciliation session lifecycle (PHASE6 §16, §17, §26, §28, §30):
OPEN -> IN_PROGRESS -> PENDING_REVIEW -> RECONCILED -> LOCKED, with
CANCELLED reachable early and REJECTED looping PENDING_REVIEW back to
IN_PROGRESS for correction. `book_balance` is computed independently from
the Phase 3 ledger (never from the bank transactions themselves — that
would make "bank vs. book" circular) whenever the account has a linked
Ledger; otherwise it stays unset and the UI shows bank-side numbers only.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.accounting_enums import BalanceType, TransactionStatus
from app.models.bank_enums import BankReconciliationStatus, BankTransactionReconciliationStatus
from app.models.bank_reconciliation import BankReconciliation
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.ledger import Ledger
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.models.user import User
from app.repositories.bank_account_repository import BankAccountRepository
from app.repositories.bank_reconciliation_repository import BankReconciliationRepository
from app.repositories.bank_transaction_repository import BankTransactionRepository
from app.schemas.bank_reconciliation import BankReconciliationCreate, BankReconciliationSummary
from app.services.accounting_calculation_service import round_money
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.bank_matching_service import BankMatchingService

_TRANSITIONS: dict[tuple[BankReconciliationStatus, str], BankReconciliationStatus] = {
    (BankReconciliationStatus.OPEN, "run_matching"): BankReconciliationStatus.IN_PROGRESS,
    (BankReconciliationStatus.IN_PROGRESS, "run_matching"): BankReconciliationStatus.IN_PROGRESS,
    (BankReconciliationStatus.IN_PROGRESS, "submit"): BankReconciliationStatus.PENDING_REVIEW,
    (BankReconciliationStatus.PENDING_REVIEW, "approve"): BankReconciliationStatus.RECONCILED,
    (BankReconciliationStatus.PENDING_REVIEW, "reject"): BankReconciliationStatus.IN_PROGRESS,
    (BankReconciliationStatus.RECONCILED, "lock"): BankReconciliationStatus.LOCKED,
    (BankReconciliationStatus.OPEN, "cancel"): BankReconciliationStatus.CANCELLED,
    (BankReconciliationStatus.IN_PROGRESS, "cancel"): BankReconciliationStatus.CANCELLED,
}

_AUDIT_ACTION_BY_ACTION = {
    "run_matching": AuditAction.BANK_RECONCILIATION_MATCHING_RUN,
    "submit": AuditAction.BANK_RECONCILIATION_SUBMITTED,
    "approve": AuditAction.BANK_RECONCILIATION_APPROVED,
    "reject": AuditAction.BANK_RECONCILIATION_REJECTED,
    "lock": AuditAction.BANK_RECONCILIATION_LOCKED,
}


class BankReconciliationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = BankReconciliationRepository(db)
        self.accounts = BankAccountRepository(db)
        self.transactions = BankTransactionRepository(db)
        self.matching = BankMatchingService(db)
        self.audit = AuditService(db)

    async def start(
        self, company_id: uuid.UUID, payload: BankReconciliationCreate, current_user: User, meta: RequestMeta
    ) -> BankReconciliation:
        account = await self.accounts.get_by_id_for_company(payload.bank_account_id, company_id)
        if account is None:
            raise ValidationAppError("Bank account not found for this company", code="BANK_ACCOUNT_NOT_FOUND")

        existing = await self.repo.get_open_for_account_period(
            company_id, account.id, payload.period_start, payload.period_end
        )
        if existing is not None:
            raise ValidationAppError(
                "A reconciliation session already exists for this account and period",
                code="BANK_RECONCILIATION_ALREADY_EXISTS",
            )

        reconciliation = BankReconciliation(
            company_id=company_id,
            bank_account_id=account.id,
            period_start=payload.period_start,
            period_end=payload.period_end,
            opening_balance=round_money(payload.opening_balance),
            closing_balance=round_money(payload.closing_balance),
            status=BankReconciliationStatus.OPEN,
            started_by=current_user.id,
            started_at=datetime.now(timezone.utc),
        )
        await self.repo.create(reconciliation)

        await self.audit.log(
            action=AuditAction.BANK_RECONCILIATION_STARTED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="bank_reconciliation",
            resource_id=str(reconciliation.id),
            description=f"Bank reconciliation started for {account.account_name} "
            f"({payload.period_start} to {payload.period_end})",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return reconciliation

    async def get(self, company_id: uuid.UUID, reconciliation_id: uuid.UUID) -> BankReconciliation:
        reconciliation = await self.repo.get_by_id_for_company(reconciliation_id, company_id)
        if reconciliation is None:
            raise NotFoundError("Bank reconciliation not found", code="BANK_RECONCILIATION_NOT_FOUND")
        return reconciliation

    async def list(
        self, company_id: uuid.UUID, *, bank_account_id: uuid.UUID | None, page: int, page_size: int
    ) -> tuple[list[BankReconciliation], int]:
        return await self.repo.list_for_company(
            company_id, bank_account_id=bank_account_id, offset=(page - 1) * page_size, limit=page_size
        )

    async def _compute_book_balance(
        self, company_id: uuid.UUID, ledger_id: uuid.UUID, as_of: date
    ) -> Decimal:
        ledger = (
            await self.db.execute(select(Ledger).where(Ledger.id == ledger_id, Ledger.company_id == company_id))
        ).scalar_one()

        journal_totals = (
            await self.db.execute(
                select(
                    JournalEntryLine.debit_amount, JournalEntryLine.credit_amount
                ).join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
                .where(
                    JournalEntry.company_id == company_id,
                    JournalEntry.status == TransactionStatus.POSTED,
                    JournalEntryLine.ledger_id == ledger_id,
                    JournalEntry.journal_date <= as_of,
                )
            )
        ).all()
        total_debit = sum((d for d, _c in journal_totals), Decimal("0"))
        total_credit = sum((c for _d, c in journal_totals), Decimal("0"))

        receipts = (
            await self.db.execute(
                select(Receipt.amount).where(
                    Receipt.company_id == company_id,
                    Receipt.ledger_id == ledger_id,
                    Receipt.status == TransactionStatus.POSTED,
                    Receipt.receipt_date <= as_of,
                )
            )
        ).scalars().all()
        total_debit += sum(receipts, Decimal("0"))  # money in = a debit to a BANK/CASH ledger

        payments = (
            await self.db.execute(
                select(Payment.amount).where(
                    Payment.company_id == company_id,
                    Payment.ledger_id == ledger_id,
                    Payment.status == TransactionStatus.POSTED,
                    Payment.payment_date <= as_of,
                )
            )
        ).scalars().all()
        total_credit += sum(payments, Decimal("0"))  # money out = a credit to a BANK/CASH ledger

        signed_opening = ledger.opening_balance if ledger.opening_balance_type == BalanceType.DEBIT else -ledger.opening_balance
        return round_money(signed_opening + total_debit - total_credit)

    async def run_matching(
        self, company_id: uuid.UUID, reconciliation_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> BankReconciliation:
        reconciliation = await self._transition(company_id, reconciliation_id, "run_matching", current_user, meta)

        unmatched = await self.transactions.list_unmatched_for_account(
            company_id,
            uuid.UUID(str(reconciliation.bank_account_id)),
            period_start=reconciliation.period_start,
            period_end=reconciliation.period_end,
        )
        counts = await self.matching.run_auto_matching(company_id, unmatched, current_user, meta)

        account = await self.accounts.get_by_id_for_company(
            uuid.UUID(str(reconciliation.bank_account_id)), company_id
        )
        reconciliation.bank_balance = reconciliation.closing_balance
        if account and account.ledger_id:
            reconciliation.book_balance = await self._compute_book_balance(
                company_id, uuid.UUID(str(account.ledger_id)), reconciliation.period_end
            )
            reconciliation.difference = round_money(reconciliation.bank_balance - reconciliation.book_balance)
        await self.db.flush()
        await self.db.refresh(reconciliation)

        await self.audit.log(
            action=AuditAction.BANK_RECONCILIATION_MATCHING_RUN,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="bank_reconciliation",
            resource_id=str(reconciliation.id),
            description=f"Matching run: {counts['auto_matched']} auto-matched, "
            f"{counts['suggested']} suggested, {counts['review_required']} need review, "
            f"{counts['unmatched']} unmatched",
            metadata=counts,
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return reconciliation

    async def summary(self, company_id: uuid.UUID, reconciliation_id: uuid.UUID) -> BankReconciliationSummary:
        from app.schemas.bank_reconciliation import BankReconciliationRead

        reconciliation = await self.get(company_id, reconciliation_id)
        transactions = await self.transactions.list_for_account_period(
            company_id,
            uuid.UUID(str(reconciliation.bank_account_id)),
            period_start=reconciliation.period_start,
            period_end=reconciliation.period_end,
        )
        counts = {status: 0 for status in BankTransactionReconciliationStatus}
        for t in transactions:
            counts[t.reconciliation_status] += 1

        matched = counts[BankTransactionReconciliationStatus.MATCHED] + counts[
            BankTransactionReconciliationStatus.MANUALLY_MATCHED
        ]
        return BankReconciliationSummary(
            reconciliation=BankReconciliationRead.model_validate(reconciliation),
            matched_count=matched,
            partially_matched_count=counts[BankTransactionReconciliationStatus.PARTIALLY_MATCHED],
            unmatched_count=counts[BankTransactionReconciliationStatus.UNMATCHED]
            + counts[BankTransactionReconciliationStatus.MATCH_SUGGESTED],
            review_required_count=counts[BankTransactionReconciliationStatus.REVIEW_REQUIRED],
            excluded_count=counts[BankTransactionReconciliationStatus.EXCLUDED],
        )

    async def _transition(
        self,
        company_id: uuid.UUID,
        reconciliation_id: uuid.UUID,
        action: str,
        current_user: User,
        meta: RequestMeta,
        comment: str | None = None,
    ) -> BankReconciliation:
        reconciliation = await self.get(company_id, reconciliation_id)
        key = (reconciliation.status, action)
        if key not in _TRANSITIONS:
            raise ConflictError(
                f"Cannot {action.replace('_', ' ')} a reconciliation in status {reconciliation.status.value}",
                code="INVALID_BANK_RECONCILIATION_TRANSITION",
            )
        reconciliation.status = _TRANSITIONS[key]

        if action == "approve":
            reconciliation.reviewed_by = current_user.id
            reconciliation.reviewed_at = datetime.now(timezone.utc)
            reconciliation.completed_at = datetime.now(timezone.utc)
        elif action == "reject":
            reconciliation.reviewed_by = current_user.id
            reconciliation.reviewed_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(reconciliation)

        if action in _AUDIT_ACTION_BY_ACTION and action != "run_matching":
            await self.audit.log(
                action=_AUDIT_ACTION_BY_ACTION[action],
                user_id=current_user.id,
                company_id=company_id,
                resource_type="bank_reconciliation",
                resource_id=str(reconciliation.id),
                description=f"Bank reconciliation moved to {reconciliation.status.value}",
                metadata={"comment": comment} if comment else None,
                ip_address=meta.ip_address,
                user_agent=meta.user_agent,
            )
        return reconciliation

    async def submit(self, company_id, reconciliation_id, current_user, meta) -> BankReconciliation:
        return await self._transition(company_id, reconciliation_id, "submit", current_user, meta)

    async def approve(self, company_id, reconciliation_id, current_user, meta, comment=None) -> BankReconciliation:
        return await self._transition(company_id, reconciliation_id, "approve", current_user, meta, comment)

    async def reject(self, company_id, reconciliation_id, current_user, meta, comment=None) -> BankReconciliation:
        return await self._transition(company_id, reconciliation_id, "reject", current_user, meta, comment)

    async def lock(self, company_id, reconciliation_id, current_user, meta) -> BankReconciliation:
        return await self._transition(company_id, reconciliation_id, "lock", current_user, meta)

    async def cancel(self, company_id, reconciliation_id, current_user, meta) -> BankReconciliation:
        reconciliation = await self.get(company_id, reconciliation_id)
        key = (reconciliation.status, "cancel")
        if key not in _TRANSITIONS:
            raise ConflictError(
                f"Cannot cancel a reconciliation in status {reconciliation.status.value}",
                code="INVALID_BANK_RECONCILIATION_TRANSITION",
            )
        reconciliation.status = _TRANSITIONS[key]
        await self.db.flush()
        await self.db.refresh(reconciliation)
        return reconciliation
