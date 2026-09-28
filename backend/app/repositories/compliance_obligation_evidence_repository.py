import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_obligation_evidence import ComplianceObligationEvidence


class ComplianceObligationEvidenceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, evidence: ComplianceObligationEvidence) -> ComplianceObligationEvidence:
        self.db.add(evidence)
        await self.db.flush()
        await self.db.refresh(evidence)
        return evidence

    async def list_for_obligation(
        self, obligation_id: uuid.UUID, company_id: uuid.UUID
    ) -> list[ComplianceObligationEvidence]:
        stmt = (
            select(ComplianceObligationEvidence)
            .where(
                ComplianceObligationEvidence.obligation_id == str(obligation_id),
                ComplianceObligationEvidence.company_id == str(company_id),
            )
            .order_by(ComplianceObligationEvidence.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_by_id(
        self, evidence_id: uuid.UUID, company_id: uuid.UUID
    ) -> ComplianceObligationEvidence | None:
        stmt = select(ComplianceObligationEvidence).where(
            ComplianceObligationEvidence.id == str(evidence_id),
            ComplianceObligationEvidence.company_id == str(company_id),
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def delete(self, evidence: ComplianceObligationEvidence) -> None:
        await self.db.delete(evidence)
        await self.db.flush()
