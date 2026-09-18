import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_finding_comment import AuditFindingComment
from app.models.audit_finding_evidence import AuditFindingEvidence
from app.models.audit_finding_response import AuditFindingResponse


class AuditFindingEvidenceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, evidence: AuditFindingEvidence) -> AuditFindingEvidence:
        self.db.add(evidence)
        await self.db.flush()
        return evidence

    async def get_by_id_for_company(
        self, evidence_id: uuid.UUID, company_id: uuid.UUID
    ) -> AuditFindingEvidence | None:
        result = await self.db.execute(
            select(AuditFindingEvidence).where(
                AuditFindingEvidence.id == evidence_id, AuditFindingEvidence.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_finding(self, finding_id: uuid.UUID) -> list[AuditFindingEvidence]:
        result = await self.db.execute(
            select(AuditFindingEvidence)
            .where(AuditFindingEvidence.finding_id == finding_id)
            .order_by(AuditFindingEvidence.added_at.asc())
        )
        return list(result.scalars().all())

    async def delete(self, evidence: AuditFindingEvidence) -> None:
        await self.db.delete(evidence)
        await self.db.flush()


class AuditFindingCommentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, comment: AuditFindingComment) -> AuditFindingComment:
        self.db.add(comment)
        await self.db.flush()
        return comment

    async def list_for_finding(self, finding_id: uuid.UUID) -> list[AuditFindingComment]:
        result = await self.db.execute(
            select(AuditFindingComment)
            .where(AuditFindingComment.finding_id == finding_id)
            .order_by(AuditFindingComment.created_at.asc())
        )
        return list(result.scalars().all())


class AuditFindingResponseRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, response: AuditFindingResponse) -> AuditFindingResponse:
        self.db.add(response)
        await self.db.flush()
        return response

    async def get_by_id_for_company(
        self, response_id: uuid.UUID, company_id: uuid.UUID
    ) -> AuditFindingResponse | None:
        result = await self.db.execute(
            select(AuditFindingResponse).where(
                AuditFindingResponse.id == response_id, AuditFindingResponse.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_finding(self, finding_id: uuid.UUID) -> list[AuditFindingResponse]:
        result = await self.db.execute(
            select(AuditFindingResponse)
            .where(AuditFindingResponse.finding_id == finding_id)
            .order_by(AuditFindingResponse.submitted_at.asc())
        )
        return list(result.scalars().all())
