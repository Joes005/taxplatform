import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.accounting_enums import TransactionStatus
from app.models.bank_enums import (
    BankMatchSourceType,
    BankMatchStatus,
    BankMatchType,
    BankTransactionReconciliationStatus,
)
from app.models.bank_transaction_match import BankTransactionMatch
from app.models.journal_entry import JournalEntry
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.models.user import User
from app.repositories.bank_transaction_match_repository import BankTransactionMatchRepository
from app.repositories.bank_transaction_repository import BankTransactionRepository
from app.schemas.bank_match import ManualMatchCreate
from app.services.accounting_calculation_service import round_money
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

_SOURCE_MODEL = {
    BankMatchSourceType.PAYMENT: Payment,
    BankMatchSourceType.RECEIPT: Receipt,
    BankMatchSourceType.JOURNAL_ENTRY: JournalEntry,
}

_UNCLAIMABLE_BANK_STATUSES = {
    BankTransactionReconciliationStatus.MATCHED,
    BankTransactionReconciliationStatus.MANUALLY_MATCHED,
    BankTransactionReconciliationStatus.EXCLUDED,
}


class BankMatchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.matches = BankTransactionMatchRepository(db)
        self.bank_transactions = BankTransactionRepository(db)
        self.audit = AuditService(db)

    async def _get_source_amount(
        self, company_id: uuid.UUID, source_type: BankMatchSourceType, source_id: uuid.UUID
    ) -> Decimal:
        model = _SOURCE_MODEL[source_type]
        result = await self.db.execute(
            select(model).where(model.company_id == company_id, model.id == source_id)
        )
        entity = result.scalar_one_or_none()
        if entity is None:
            raise ValidationAppError(
                f"{source_type.value.replace('_', ' ').title()} not found for this company",
                code="BANK_MATCH_SOURCE_NOT_FOUND",
            )
        if entity.status != TransactionStatus.POSTED:
            raise ValidationAppError(
                f"Only a POSTED {source_type.value.replace('_', ' ').title()} can be matched",
                code="BANK_MATCH_SOURCE_NOT_POSTED",
            )

        if source_type == BankMatchSourceType.JOURNAL_ENTRY:
            # A journal entry has no single "amount" — its lines can touch
            # several ledgers. Matching against one is validated by amount
            # compatibility alone (the caller states matched_amount); the
            # entry itself is just confirmed to exist, belong to this
            # company, and be posted.
            return Decimal("999999999999.99")
        return entity.amount

    async def create_manual_match(
        self,
        company_id: uuid.UUID,
        bank_transaction_id: uuid.UUID,
        payload: ManualMatchCreate,
        current_user: User,
        meta: RequestMeta,
        *,
        match_type: BankMatchType = BankMatchType.MANUAL,
    ) -> BankTransactionMatch:
        bank_transaction = await self.bank_transactions.get_by_id_for_company(bank_transaction_id, company_id)
        if bank_transaction is None:
            raise NotFoundError("Bank transaction not found", code="BANK_TRANSACTION_NOT_FOUND")
        if bank_transaction.reconciliation_status in _UNCLAIMABLE_BANK_STATUSES:
            raise ConflictError(
                f"Cannot match a bank transaction in status {bank_transaction.reconciliation_status.value}",
                code="INVALID_BANK_TRANSACTION_STATUS",
            )

        matched_amount = round_money(payload.matched_amount)

        bank_already_matched = await self.matches.sum_active_matched_amount(bank_transaction.id)
        if bank_already_matched + matched_amount > bank_transaction.amount:
            raise ValidationAppError(
                f"Matched amount {matched_amount} would exceed the bank transaction's remaining "
                f"unmatched balance of {bank_transaction.amount - bank_already_matched}",
                code="MATCH_AMOUNT_EXCEEDS_BANK_TRANSACTION",
            )

        source_amount = await self._get_source_amount(company_id, payload.source_type, payload.source_id)
        source_already_matched = await self.matches.sum_active_matched_amount_for_source(
            payload.source_type, payload.source_id
        )
        if source_already_matched + matched_amount > source_amount:
            raise ValidationAppError(
                f"Matched amount {matched_amount} would exceed the accounting record's remaining "
                f"unmatched balance of {source_amount - source_already_matched}",
                code="MATCH_AMOUNT_EXCEEDS_SOURCE",
            )

        match = BankTransactionMatch(
            company_id=company_id,
            bank_transaction_id=bank_transaction.id,
            source_type=payload.source_type,
            source_id=payload.source_id,
            matched_amount=matched_amount,
            match_type=match_type,
            match_score=None,
            status=BankMatchStatus.ACTIVE,
            matched_by=current_user.id,
            matched_at=datetime.now(timezone.utc),
            notes=payload.notes,
        )
        await self.matches.create(match)
        await self.sync_bank_transaction_status(bank_transaction)

        await self.audit.log(
            action=AuditAction.BANK_MATCH_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="bank_transaction_match",
            resource_id=str(match.id),
            description=f"{match_type.value} match created: bank transaction {bank_transaction.id} "
            f"<-> {payload.source_type.value} {payload.source_id} for {matched_amount}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return match

    async def sync_bank_transaction_status(self, bank_transaction) -> None:
        active = await self.matches.list_active_for_bank_transaction(bank_transaction.id)
        total_matched = sum((m.matched_amount for m in active), Decimal("0"))
        if total_matched >= bank_transaction.amount:
            # MATCHED only when every claim on this transaction is an
            # unreviewed AUTO match; a single manual/partial/adjustment
            # claim in the mix means a human made the call, so it's
            # MANUALLY_MATCHED even if the rest were auto-suggested.
            all_auto = all(m.match_type == BankMatchType.AUTO for m in active)
            bank_transaction.reconciliation_status = (
                BankTransactionReconciliationStatus.MATCHED
                if all_auto
                else BankTransactionReconciliationStatus.MANUALLY_MATCHED
            )
        elif total_matched > 0:
            bank_transaction.reconciliation_status = BankTransactionReconciliationStatus.PARTIALLY_MATCHED
        else:
            bank_transaction.reconciliation_status = BankTransactionReconciliationStatus.UNMATCHED
        await self.db.flush()

    async def reverse(
        self, company_id: uuid.UUID, match_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> BankTransactionMatch:
        match = await self.matches.get_by_id_for_company(match_id, company_id)
        if match is None:
            raise NotFoundError("Match not found", code="BANK_MATCH_NOT_FOUND")
        if match.status == BankMatchStatus.REVERSED:
            raise ConflictError("Match is already reversed", code="BANK_MATCH_ALREADY_REVERSED")

        match.status = BankMatchStatus.REVERSED
        await self.db.flush()

        bank_transaction = await self.bank_transactions.get_by_id_for_company(
            uuid.UUID(str(match.bank_transaction_id)), company_id
        )
        await self.sync_bank_transaction_status(bank_transaction)

        await self.audit.log(
            action=AuditAction.BANK_MATCH_REVERSED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="bank_transaction_match",
            resource_id=str(match.id),
            description=f"Match reversed: bank transaction {match.bank_transaction_id}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return match

    async def list_for_bank_transaction(
        self, company_id: uuid.UUID, bank_transaction_id: uuid.UUID
    ) -> list[BankTransactionMatch]:
        bank_transaction = await self.bank_transactions.get_by_id_for_company(bank_transaction_id, company_id)
        if bank_transaction is None:
            raise NotFoundError("Bank transaction not found", code="BANK_TRANSACTION_NOT_FOUND")
        return await self.matches.list_for_bank_transaction(bank_transaction_id)
