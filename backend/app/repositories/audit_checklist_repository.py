import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit_checklist import AuditChecklist, AuditChecklistItem
from app.models.audit_workflow_enums import AuditChecklistItemStatus


class AuditChecklistRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, checklist: AuditChecklist) -> AuditChecklist:
        self.db.add(checklist)
        await self.db.flush()
        return checklist

    async def get_for_engagement(
        self, engagement_id: uuid.UUID, company_id: uuid.UUID
    ) -> AuditChecklist | None:
        result = await self.db.execute(
            select(AuditChecklist)
            .options(selectinload(AuditChecklist.items))
            .where(
                AuditChecklist.engagement_id == engagement_id,
                AuditChecklist.company_id == company_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_item(self, item: AuditChecklistItem) -> AuditChecklistItem:
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_item_for_company(
        self, item_id: uuid.UUID, company_id: uuid.UUID
    ) -> AuditChecklistItem | None:
        result = await self.db.execute(
            select(AuditChecklistItem).where(
                AuditChecklistItem.id == item_id, AuditChecklistItem.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_items_for_engagement(
        self, engagement_id: uuid.UUID, *, status: AuditChecklistItemStatus | None = None
    ) -> list[AuditChecklistItem]:
        query = select(AuditChecklistItem).where(AuditChecklistItem.engagement_id == engagement_id)
        if status is not None:
            query = query.where(AuditChecklistItem.status == status)
        result = await self.db.execute(query.order_by(AuditChecklistItem.order_index.asc()))
        return list(result.scalars().all())
