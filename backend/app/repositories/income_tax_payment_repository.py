import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.income_tax_payment import IncomeTaxAdvanceTaxPayment, IncomeTaxSelfAssessmentTaxPayment


class IncomeTaxAdvanceTaxPaymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entity: IncomeTaxAdvanceTaxPayment) -> IncomeTaxAdvanceTaxPayment:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id_for_company(
        self, entity_id: uuid.UUID, company_id: uuid.UUID
    ) -> IncomeTaxAdvanceTaxPayment | None:
        result = await self.db.execute(
            select(IncomeTaxAdvanceTaxPayment).where(
                IncomeTaxAdvanceTaxPayment.id == entity_id, IncomeTaxAdvanceTaxPayment.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_fy(
        self, company_id: uuid.UUID, financial_year_id: uuid.UUID
    ) -> list[IncomeTaxAdvanceTaxPayment]:
        result = await self.db.execute(
            select(IncomeTaxAdvanceTaxPayment).where(
                IncomeTaxAdvanceTaxPayment.company_id == company_id,
                IncomeTaxAdvanceTaxPayment.financial_year_id == financial_year_id,
            )
        )
        return list(result.scalars().all())


class IncomeTaxSelfAssessmentTaxPaymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entity: IncomeTaxSelfAssessmentTaxPayment) -> IncomeTaxSelfAssessmentTaxPayment:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id_for_company(
        self, entity_id: uuid.UUID, company_id: uuid.UUID
    ) -> IncomeTaxSelfAssessmentTaxPayment | None:
        result = await self.db.execute(
            select(IncomeTaxSelfAssessmentTaxPayment).where(
                IncomeTaxSelfAssessmentTaxPayment.id == entity_id,
                IncomeTaxSelfAssessmentTaxPayment.company_id == company_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_fy(
        self, company_id: uuid.UUID, financial_year_id: uuid.UUID
    ) -> list[IncomeTaxSelfAssessmentTaxPayment]:
        result = await self.db.execute(
            select(IncomeTaxSelfAssessmentTaxPayment).where(
                IncomeTaxSelfAssessmentTaxPayment.company_id == company_id,
                IncomeTaxSelfAssessmentTaxPayment.financial_year_id == financial_year_id,
            )
        )
        return list(result.scalars().all())
