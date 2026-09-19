"""TDS/TCS credit and advance/self-assessment tax payment tracking
(PHASE8 §36-40). No live Form 26AS/AIS fetch — every figure here is
manually entered or derived from an existing local record.
"""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationAppError
from app.models.income_tax_credit import IncomeTaxCreditEntry
from app.models.income_tax_income import IncomeTaxOtherIncome, IncomeTaxSalaryIncome
from app.models.income_tax_payment import IncomeTaxAdvanceTaxPayment, IncomeTaxSelfAssessmentTaxPayment
from app.models.user import User
from app.repositories.financial_year_repository import FinancialYearRepository
from app.repositories.income_tax_credit_repository import IncomeTaxCreditRepository
from app.repositories.income_tax_payment_repository import (
    IncomeTaxAdvanceTaxPaymentRepository,
    IncomeTaxSelfAssessmentTaxPaymentRepository,
)
from app.schemas.income_tax_credit import IncomeTaxCreditEntryCreate
from app.schemas.income_tax_payment import IncomeTaxPaymentCreate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

ZERO = Decimal("0")


class TaxCreditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncomeTaxCreditRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: IncomeTaxCreditEntryCreate, current_user: User, meta: RequestMeta
    ) -> IncomeTaxCreditEntry:
        if await self.fy_repo.get_by_id_for_company(payload.financial_year_id, company_id) is None:
            raise ValidationAppError("Financial year not found for this company", code="INVALID_FINANCIAL_YEAR")

        entity = IncomeTaxCreditEntry(company_id=company_id, created_by=current_user.id, **payload.model_dump())
        await self.repo.create(entity)

        await self.audit.log(
            action=AuditAction.TAX_CREDIT_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_credit_entry",
            resource_id=str(entity.id),
            description=f"TDS/TCS credit recorded from {entity.deductor_name}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def list_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> list[IncomeTaxCreditEntry]:
        return await self.repo.list_for_fy(company_id, financial_year_id)

    async def total_tds_credit_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> Decimal:
        """Sums TDS already deducted on salary/other-source income plus
        any separately recorded credit entries — every TDS figure the
        platform has for this company/year, from every place it can
        legitimately come from."""
        salary_tds = (
            await self.db.execute(
                select(func.coalesce(func.sum(IncomeTaxSalaryIncome.tds), ZERO)).where(
                    IncomeTaxSalaryIncome.company_id == company_id,
                    IncomeTaxSalaryIncome.financial_year_id == financial_year_id,
                )
            )
        ).scalar_one()
        other_tds = (
            await self.db.execute(
                select(func.coalesce(func.sum(IncomeTaxOtherIncome.tds), ZERO)).where(
                    IncomeTaxOtherIncome.company_id == company_id,
                    IncomeTaxOtherIncome.financial_year_id == financial_year_id,
                )
            )
        ).scalar_one()
        credit_entries = (
            await self.db.execute(
                select(func.coalesce(func.sum(IncomeTaxCreditEntry.amount), ZERO)).where(
                    IncomeTaxCreditEntry.company_id == company_id,
                    IncomeTaxCreditEntry.financial_year_id == financial_year_id,
                )
            )
        ).scalar_one()
        return salary_tds + other_tds + credit_entries


class IncomeTaxAdvanceTaxPaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncomeTaxAdvanceTaxPaymentRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: IncomeTaxPaymentCreate, current_user: User, meta: RequestMeta
    ) -> IncomeTaxAdvanceTaxPayment:
        if await self.fy_repo.get_by_id_for_company(payload.financial_year_id, company_id) is None:
            raise ValidationAppError("Financial year not found for this company", code="INVALID_FINANCIAL_YEAR")

        entity = IncomeTaxAdvanceTaxPayment(company_id=company_id, created_by=current_user.id, **payload.model_dump())
        await self.repo.create(entity)

        await self.audit.log(
            action=AuditAction.TAX_PAYMENT_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_advance_tax_payment",
            resource_id=str(entity.id),
            description=f"Advance tax payment of {entity.amount} recorded",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def list_for_fy(
        self, company_id: uuid.UUID, financial_year_id: uuid.UUID
    ) -> list[IncomeTaxAdvanceTaxPayment]:
        return await self.repo.list_for_fy(company_id, financial_year_id)

    async def total_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> Decimal:
        payments = await self.repo.list_for_fy(company_id, financial_year_id)
        return sum((p.amount for p in payments), ZERO)


class IncomeTaxSelfAssessmentTaxPaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncomeTaxSelfAssessmentTaxPaymentRepository(db)
        self.fy_repo = FinancialYearRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: IncomeTaxPaymentCreate, current_user: User, meta: RequestMeta
    ) -> IncomeTaxSelfAssessmentTaxPayment:
        if await self.fy_repo.get_by_id_for_company(payload.financial_year_id, company_id) is None:
            raise ValidationAppError("Financial year not found for this company", code="INVALID_FINANCIAL_YEAR")

        entity = IncomeTaxSelfAssessmentTaxPayment(
            company_id=company_id, created_by=current_user.id, **payload.model_dump()
        )
        await self.repo.create(entity)

        await self.audit.log(
            action=AuditAction.TAX_PAYMENT_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="income_tax_self_assessment_tax_payment",
            resource_id=str(entity.id),
            description=f"Self-assessment tax payment of {entity.amount} recorded",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entity

    async def list_for_fy(
        self, company_id: uuid.UUID, financial_year_id: uuid.UUID
    ) -> list[IncomeTaxSelfAssessmentTaxPayment]:
        return await self.repo.list_for_fy(company_id, financial_year_id)

    async def total_for_fy(self, company_id: uuid.UUID, financial_year_id: uuid.UUID) -> Decimal:
        payments = await self.repo.list_for_fy(company_id, financial_year_id)
        return sum((p.amount for p in payments), ZERO)
