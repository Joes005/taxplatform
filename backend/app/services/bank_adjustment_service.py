import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationAppError
from app.models.bank_enums import BankMatchSourceType, BankMatchStatus, BankMatchType, BankTransactionType
from app.models.bank_transaction_match import BankTransactionMatch
from app.models.journal_entry import JournalEntry
from app.models.user import User
from app.repositories.bank_account_repository import BankAccountRepository
from app.repositories.bank_transaction_match_repository import BankTransactionMatchRepository
from app.repositories.bank_transaction_repository import BankTransactionRepository
from app.schemas.bank_adjustment import BankAdjustmentCreate
from app.schemas.journal_entry import JournalEntryCreate, JournalEntryLineCreate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.bank_match_service import BankMatchService
from app.services.journal_entry_service import JournalEntryService


class BankAdjustmentService:
    """Turns an unmatched bank transaction (bank charges, interest, an
    unknown deposit, ...) into a real, POSTED JournalEntry via the
    existing Phase 3 service — this class owns none of the accounting
    logic itself, only the bank-side wiring: build the two offsetting
    lines, post through `JournalEntryService` (which already enforces
    financial-year and period-lock rules), then record an ADJUSTMENT
    match so the bank transaction is marked resolved (PHASE6 §24, §29).
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.transactions = BankTransactionRepository(db)
        self.accounts = BankAccountRepository(db)
        self.matches = BankTransactionMatchRepository(db)
        self.journal_entries = JournalEntryService(db)
        self.match_service = BankMatchService(db)
        self.audit = AuditService(db)

    async def create_adjustment(
        self,
        company_id: uuid.UUID,
        bank_transaction_id: uuid.UUID,
        payload: BankAdjustmentCreate,
        current_user: User,
        meta: RequestMeta,
    ) -> JournalEntry:
        transaction = await self.transactions.get_by_id_for_company(bank_transaction_id, company_id)
        if transaction is None:
            raise ValidationAppError("Bank transaction not found", code="BANK_TRANSACTION_NOT_FOUND")

        account = await self.accounts.get_by_id_for_company(transaction.bank_account_id, company_id)
        if account is None or account.ledger_id is None:
            raise ValidationAppError(
                "This bank account has no linked ledger — link one before creating adjustments",
                code="BANK_ACCOUNT_LEDGER_REQUIRED",
            )

        already_matched = await self.matches.sum_active_matched_amount(transaction.id)
        remaining = transaction.amount - already_matched
        if remaining <= 0:
            raise ValidationAppError(
                "This bank transaction has no unmatched balance left to adjust",
                code="BANK_TRANSACTION_FULLY_MATCHED",
            )

        # A DEBIT bank transaction (money out, e.g. bank charges) debits
        # the offset expense ledger and credits the bank ledger; a CREDIT
        # transaction (money in, e.g. interest) is the mirror image.
        if transaction.transaction_type == BankTransactionType.DEBIT:
            lines = [
                JournalEntryLineCreate(ledger_id=payload.offset_ledger_id, debit_amount=remaining, description=transaction.description),
                JournalEntryLineCreate(ledger_id=account.ledger_id, credit_amount=remaining, description=transaction.description),
            ]
        else:
            lines = [
                JournalEntryLineCreate(ledger_id=account.ledger_id, debit_amount=remaining, description=transaction.description),
                JournalEntryLineCreate(ledger_id=payload.offset_ledger_id, credit_amount=remaining, description=transaction.description),
            ]

        entry = await self.journal_entries.create(
            company_id,
            JournalEntryCreate(
                financial_year_id=payload.financial_year_id,
                journal_number=payload.journal_number,
                journal_date=transaction.transaction_date,
                narration=payload.narration or f"Bank adjustment: {transaction.description}",
                lines=lines,
                source_reference=f"bank_transaction:{transaction.id}",
            ),
            current_user,
            meta,
        )
        entry = await self.journal_entries.post(company_id, entry.id, current_user, meta)

        match = BankTransactionMatch(
            company_id=company_id,
            bank_transaction_id=transaction.id,
            source_type=BankMatchSourceType.JOURNAL_ENTRY,
            source_id=entry.id,
            matched_amount=remaining,
            match_type=BankMatchType.ADJUSTMENT,
            status=BankMatchStatus.ACTIVE,
            matched_by=current_user.id,
            matched_at=datetime.now(timezone.utc),
            notes="Adjustment journal entry",
        )
        await self.matches.create(match)
        await self.match_service.sync_bank_transaction_status(transaction)

        await self.audit.log(
            action=AuditAction.BANK_ADJUSTMENT_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="bank_transaction",
            resource_id=str(transaction.id),
            description=f"Adjustment journal '{entry.journal_number}' created for bank transaction {transaction.id}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entry
