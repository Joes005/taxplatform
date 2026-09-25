"""Accounting-derived business/professional income (PHASE8 §23-26, §60).

Revenue and purchases come straight from Phase 3's `SalesInvoice`/
`PurchaseInvoice` (net of `CreditNote`/`DebitNote`) — these are never
auto-posted to ledgers in this codebase (see `ReportService.trial_balance`'s
own docstring), so summing invoice totals and summing `JournalEntryLine`
movement on INCOME/EXPENSE ledgers are genuinely non-overlapping data
sources, not a double-count risk. A ledger's tax treatment
(`IncomeTaxLedgerClassification`) is only ever set explicitly by a human;
an unclassified expense ledger is still deducted at book value (never
silently disallowed), and only a ledger a human has marked `DISALLOWABLE`
is added back — no ledger name is ever interpreted automatically.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.accounting_enums import LedgerType, NoteType, TransactionStatus
from app.models.credit_note import CreditNote
from app.models.debit_note import DebitNote
from app.models.income_tax_adjustment import IncomeTaxAdjustment
from app.models.income_tax_enums import LedgerTaxClassification, TaxAdjustmentType
from app.models.income_tax_ledger_classification import IncomeTaxLedgerClassification
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.ledger import Ledger
from app.models.purchase_invoice import PurchaseInvoice
from app.models.sales_invoice import SalesInvoice
from app.models.user import User
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.income_tax_adjustment_repository import IncomeTaxAdjustmentRepository
from app.repositories.income_tax_ledger_classification_repository import IncomeTaxLedgerClassificationRepository
from app.schemas.income_tax_adjustment import IncomeTaxAdjustmentCreate
from app.services.accounting_calculation_service import round_money
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

ZERO = Decimal("0")


@dataclass
class BusinessIncomeBreakdown:
    revenue: Decimal = ZERO
    purchases: Decimal = ZERO
    ledger_income: Decimal = ZERO
    ledger_expense_total: Decimal = ZERO
    gross_business_income: Decimal = ZERO
    eligible_expenses: Decimal = ZERO
    disallowances: Decimal = ZERO
    other_adjustments: Decimal = ZERO
    depreciation_adjustments: Decimal = ZERO
    taxable_business_income: Decimal = ZERO
    review_required_ledger_ids: list[uuid.UUID] = field(default_factory=list)


class BusinessIncomeCalculationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.classifications = IncomeTaxLedgerClassificationRepository(db)
        self.adjustments = IncomeTaxAdjustmentRepository(db)

    async def calculate(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> BusinessIncomeBreakdown:
        sales = (
            await self.db.execute(
                select(func.coalesce(func.sum(SalesInvoice.taxable_amount), ZERO)).where(
                    SalesInvoice.company_id == company_id,
                    SalesInvoice.financial_year_id == financial_year_id,
                    SalesInvoice.status == TransactionStatus.POSTED,
                )
            )
        ).scalar_one()
        sales_returns = (
            await self.db.execute(
                select(func.coalesce(func.sum(CreditNote.taxable_amount), ZERO)).where(
                    CreditNote.company_id == company_id,
                    CreditNote.financial_year_id == financial_year_id,
                    CreditNote.status == TransactionStatus.POSTED,
                    CreditNote.note_type == NoteType.SALES,
                )
            )
        ).scalar_one()
        purchases = (
            await self.db.execute(
                select(func.coalesce(func.sum(PurchaseInvoice.taxable_amount), ZERO)).where(
                    PurchaseInvoice.company_id == company_id,
                    PurchaseInvoice.financial_year_id == financial_year_id,
                    PurchaseInvoice.status == TransactionStatus.POSTED,
                )
            )
        ).scalar_one()
        purchase_returns = (
            await self.db.execute(
                select(func.coalesce(func.sum(DebitNote.taxable_amount), ZERO)).where(
                    DebitNote.company_id == company_id,
                    DebitNote.financial_year_id == financial_year_id,
                    DebitNote.status == TransactionStatus.POSTED,
                    DebitNote.note_type == NoteType.PURCHASE,
                )
            )
        ).scalar_one()

        ledger_rows = (
            await self.db.execute(
                select(
                    Ledger.id,
                    Ledger.ledger_type,
                    func.coalesce(func.sum(JournalEntryLine.debit_amount), ZERO),
                    func.coalesce(func.sum(JournalEntryLine.credit_amount), ZERO),
                )
                .join(JournalEntryLine, JournalEntryLine.ledger_id == Ledger.id)
                .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
                .where(
                    JournalEntry.company_id == company_id,
                    JournalEntry.financial_year_id == financial_year_id,
                    JournalEntry.status == TransactionStatus.POSTED,
                    Ledger.ledger_type.in_([LedgerType.INCOME, LedgerType.EXPENSE]),
                    or_(
                        JournalEntry.source_reference.is_(None),
                        and_(
                            ~JournalEntry.source_reference.startswith("sales_invoice"),
                            ~JournalEntry.source_reference.startswith("purchase_invoice"),
                        ),
                    ),
                )
                .group_by(Ledger.id, Ledger.ledger_type)
            )
        ).all()

        ledger_income = ZERO
        ledger_expense_total = ZERO
        disallowed = ZERO
        review_required_ledger_ids: list[uuid.UUID] = []

        for ledger_id, ledger_type, debit_total, credit_total in ledger_rows:
            if ledger_type == LedgerType.INCOME:
                ledger_income += credit_total - debit_total
            else:
                expense_amount = debit_total - credit_total
                ledger_expense_total += expense_amount
                classification_row = await self.classifications.get_for_ledger(company_id, ledger_id)
                classification = (
                    classification_row.classification if classification_row else LedgerTaxClassification.NOT_CLASSIFIED
                )
                if classification == LedgerTaxClassification.DISALLOWABLE:
                    disallowed += expense_amount
                elif classification in (LedgerTaxClassification.REVIEW_REQUIRED, LedgerTaxClassification.NOT_CLASSIFIED):
                    review_required_ledger_ids.append(ledger_id)

        adjustment_rows = (
            await self.db.execute(
                select(IncomeTaxAdjustment.adjustment_type, IncomeTaxAdjustment.difference).where(
                    IncomeTaxAdjustment.company_id == company_id,
                    IncomeTaxAdjustment.financial_year_id == financial_year_id,
                )
            )
        ).all()
        depreciation_adjustments = sum(
            (diff for adj_type, diff in adjustment_rows if adj_type == TaxAdjustmentType.DEPRECIATION_ADJUSTMENT), ZERO
        )
        other_adjustments = sum(
            (diff for adj_type, diff in adjustment_rows if adj_type != TaxAdjustmentType.DEPRECIATION_ADJUSTMENT), ZERO
        )

        revenue = round_money(sales - sales_returns)
        net_purchases = round_money(purchases - purchase_returns)
        allowable_expense = ledger_expense_total - disallowed

        gross_business_income = round_money(revenue + ledger_income)
        eligible_expenses = round_money(net_purchases + allowable_expense)
        taxable_business_income = round_money(
            gross_business_income - eligible_expenses + other_adjustments + depreciation_adjustments
        )

        return BusinessIncomeBreakdown(
            revenue=revenue,
            purchases=net_purchases,
            ledger_income=round_money(ledger_income),
            ledger_expense_total=round_money(ledger_expense_total),
            gross_business_income=gross_business_income,
            eligible_expenses=eligible_expenses,
            disallowances=round_money(disallowed),
            other_adjustments=round_money(other_adjustments),
            depreciation_adjustments=round_money(depreciation_adjustments),
            taxable_business_income=taxable_business_income,
            review_required_ledger_ids=review_required_ledger_ids,
        )


class IncomeTaxLedgerClassificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncomeTaxLedgerClassificationRepository(db)

    async def set_classification(
        self, company_id: uuid.UUID, ledger_id: uuid.UUID, classification: LedgerTaxClassification, notes: str | None
    ) -> IncomeTaxLedgerClassification:
        existing = await self.repo.get_for_ledger(company_id, ledger_id)
        if existing is not None:
            existing.classification = classification
            existing.notes = notes
            await self.db.flush()
            await self.db.refresh(existing)
            return existing

        entity = IncomeTaxLedgerClassification(
            company_id=company_id, ledger_id=ledger_id, classification=classification, notes=notes
        )
        return await self.repo.create(entity)

    async def list_for_company(self, company_id: uuid.UUID) -> list[IncomeTaxLedgerClassification]:
        return await self.repo.list_for_company(company_id)


class IncomeTaxAdjustmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncomeTaxAdjustmentRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: IncomeTaxAdjustmentCreate, current_user: User, meta: RequestMeta
    ) -> IncomeTaxAdjustment:
        if await self.fy_repo.get_by_id_for_company(payload.financial_year_id, company_id) is None:
            raise ValidationAppError("Financial year not found for this company", code="INVALID_FINANCIAL_YEAR")

        entity = IncomeTaxAdjustment(
            company_id=company_id,
            created_by=current_user.id,
            **payload.model_dump(),
        )
        entity.difference = round_money(entity.tax_amount - entity.book_amount)
        await self.repo.create(entity)

        await self.audit.log(
            action=AuditAction.TAX_INCOME_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_adjustment",
            resource_id=str(entity.id),
            description=f"Business income adjustment recorded: {entity.description}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def list_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> list[IncomeTaxAdjustment]:
        return await self.repo.list_for_fy(company_id, financial_year_id)

    async def delete(self, company_id: uuid.UUID, entity_id: uuid.UUID) -> None:
        entity = await self.repo.get_by_id_for_company(entity_id, company_id)
        if entity is None:
            raise NotFoundError("Adjustment not found", code="TAX_ADJUSTMENT_NOT_FOUND")
        await self.repo.delete(entity)
