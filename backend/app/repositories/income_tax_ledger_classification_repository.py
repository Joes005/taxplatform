import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.income_tax_ledger_classification import IncomeTaxLedgerClassification


class IncomeTaxLedgerClassificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entity: IncomeTaxLedgerClassification) -> IncomeTaxLedgerClassification:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_for_ledger(
        self, company_id: uuid.UUID, ledger_id: uuid.UUID
    ) -> IncomeTaxLedgerClassification | None:
        result = await self.db.execute(
            select(IncomeTaxLedgerClassification).where(
                IncomeTaxLedgerClassification.company_id == company_id,
                IncomeTaxLedgerClassification.ledger_id == ledger_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_company(self, company_id: uuid.UUID) -> list[IncomeTaxLedgerClassification]:
        result = await self.db.execute(
            select(IncomeTaxLedgerClassification).where(IncomeTaxLedgerClassification.company_id == company_id)
        )
        return list(result.scalars().all())
