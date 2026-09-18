import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_review import AuditReview
from app.models.audit_signoff import AuditSignOff


class AuditReviewRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, review: AuditReview) -> AuditReview:
        self.db.add(review)
        await self.db.flush()
        return review

    async def get_by_id_for_company(self, review_id: uuid.UUID, company_id: uuid.UUID) -> AuditReview | None:
        result = await self.db.execute(
            select(AuditReview).where(AuditReview.id == review_id, AuditReview.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def list_for_engagement(self, engagement_id: uuid.UUID) -> list[AuditReview]:
        result = await self.db.execute(
            select(AuditReview)
            .where(AuditReview.engagement_id == engagement_id)
            .order_by(AuditReview.created_at.asc())
        )
        return list(result.scalars().all())


class AuditSignOffRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, signoff: AuditSignOff) -> AuditSignOff:
        self.db.add(signoff)
        await self.db.flush()
        return signoff

    async def list_for_engagement(self, engagement_id: uuid.UUID) -> list[AuditSignOff]:
        result = await self.db.execute(
            select(AuditSignOff)
            .where(AuditSignOff.engagement_id == engagement_id)
            .order_by(AuditSignOff.created_at.asc())
        )
        return list(result.scalars().all())
