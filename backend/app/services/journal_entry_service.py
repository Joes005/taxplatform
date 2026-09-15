import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.accounting_enums import TransactionStatus
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.user import User
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.journal_entry_repository import JournalEntryRepository
from app.repositories.ledger_repository import LedgerRepository
from app.schemas.journal_entry import JournalEntryCreate
from app.services.accounting_calculation_service import AccountingCalculationService
from app.services.accounting_guards import assert_date_in_financial_year, assert_period_open
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class JournalEntryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = JournalEntryRepository(db)
        self.financial_years = FinancialYearRepository(db)
        self.ledgers = LedgerRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: JournalEntryCreate, current_user: User, meta: RequestMeta
    ) -> JournalEntry:
        fy = await self.financial_years.get_by_id_for_company(payload.financial_year_id, company_id)
        if fy is None:
            raise ValidationAppError(
                "Financial year not found in this company", code="INVALID_FINANCIAL_YEAR"
            )
        assert_date_in_financial_year(fy, payload.journal_date)

        total_debit = sum((line.debit_amount for line in payload.lines), Decimal("0"))
        total_credit = sum((line.credit_amount for line in payload.lines), Decimal("0"))
        # §17 — validated at creation, not only at posting: an entry that
        # doesn't balance is never allowed to exist, DRAFT or not.
        AccountingCalculationService.validate_journal_balance(total_debit, total_credit)

        lines = []
        for line_payload in payload.lines:
            ledger = await self.ledgers.get_by_id_for_company(line_payload.ledger_id, company_id)
            if ledger is None:
                raise ValidationAppError(
                    "Ledger not found in this company", code="INVALID_LEDGER"
                )
            lines.append(
                JournalEntryLine(
                    ledger_id=line_payload.ledger_id,
                    debit_amount=line_payload.debit_amount,
                    credit_amount=line_payload.credit_amount,
                    description=line_payload.description,
                )
            )

        entry = JournalEntry(
            company_id=company_id,
            financial_year_id=payload.financial_year_id,
            journal_number=payload.journal_number,
            journal_date=payload.journal_date,
            narration=payload.narration,
            status=TransactionStatus.DRAFT,
            source=payload.source,
            source_reference=payload.source_reference,
            lines=lines,
        )
        await self.repo.create(entry)

        await self.audit.log(
            action=AuditAction.ACCOUNTING_CREATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="journal_entry",
            resource_id=str(entry.id),
            description=f"Journal entry '{entry.journal_number}' created",
            metadata={"total_debit": str(total_debit), "total_credit": str(total_credit)},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entry

    async def get(self, company_id: uuid.UUID, entry_id: uuid.UUID) -> JournalEntry:
        entry = await self.repo.get_by_id_for_company(entry_id, company_id)
        if entry is None:
            raise NotFoundError("Journal entry not found", code="JOURNAL_ENTRY_NOT_FOUND")
        return entry

    async def list(self, company_id: uuid.UUID, *, page: int, page_size: int, **filters):
        return await self.repo.list_for_company(
            company_id, offset=(page - 1) * page_size, limit=page_size, **filters
        )

    async def post(
        self, company_id: uuid.UUID, entry_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> JournalEntry:
        entry = await self.get(company_id, entry_id)
        if entry.status != TransactionStatus.DRAFT:
            raise ConflictError(
                f"Only a DRAFT journal entry can be posted (current status: {entry.status.value})",
                code="INVALID_STATUS_TRANSITION",
            )

        total_debit = sum((line.debit_amount for line in entry.lines), Decimal("0"))
        total_credit = sum((line.credit_amount for line in entry.lines), Decimal("0"))
        AccountingCalculationService.validate_journal_balance(total_debit, total_credit)

        fy = await self.financial_years.get_by_id_for_company(entry.financial_year_id, company_id)
        assert_date_in_financial_year(fy, entry.journal_date)
        await assert_period_open(self.db, company_id=company_id, on_date=entry.journal_date)

        entry.status = TransactionStatus.POSTED
        await self.db.flush()
        await self.db.refresh(entry, attribute_names=["updated_at"])

        await self.audit.log(
            action=AuditAction.ACCOUNTING_POST,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="journal_entry",
            resource_id=str(entry.id),
            description=f"Journal entry '{entry.journal_number}' posted",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entry
