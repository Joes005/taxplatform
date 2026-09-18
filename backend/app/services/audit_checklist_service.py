"""Engagement checklist generation and tracking (PHASE7 §12-13). Items are
seeded once from `STANDARD_CHECKLIST_TEMPLATE` — a small, documented,
non-authoritative starting point, never a statutory checklist — and from
then on are tracked/updated individually; there is no re-sync that would
silently overwrite a CA's edits.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.audit_checklist import AuditChecklist, AuditChecklistItem
from app.models.audit_workflow_enums import AuditChecklistItemStatus
from app.models.user import User
from app.repositories.audit_checklist_repository import AuditChecklistRepository
from app.repositories.audit_engagement_repository import AuditEngagementRepository
from app.schemas.audit_checklist import AuditChecklistItemCreate, AuditChecklistItemUpdate
from app.services.audit_checklist_templates import STANDARD_CHECKLIST_TEMPLATE
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class AuditChecklistService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuditChecklistRepository(db)
        self.engagements = AuditEngagementRepository(db)
        self.audit = AuditService(db)

    async def get_or_create(
        self, company_id: uuid.UUID, engagement_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> AuditChecklist:
        engagement = await self.engagements.get_by_id_for_company(engagement_id, company_id)
        if engagement is None:
            raise NotFoundError("Audit engagement not found", code="AUDIT_ENGAGEMENT_NOT_FOUND")

        checklist = await self.repo.get_for_engagement(engagement_id, company_id)
        if checklist is not None:
            return checklist

        checklist = AuditChecklist(engagement_id=engagement_id, company_id=company_id)
        await self.repo.create(checklist)

        for index, template_item in enumerate(STANDARD_CHECKLIST_TEMPLATE):
            item = AuditChecklistItem(
                checklist_id=checklist.id,
                engagement_id=engagement_id,
                company_id=company_id,
                category=template_item["category"],
                title=template_item["title"],
                description=template_item.get("description"),
                order_index=index,
            )
            await self.repo.add_item(item)

        await self.db.flush()
        checklist = await self.repo.get_for_engagement(engagement_id, company_id)

        await self.audit.log(
            action=AuditAction.AUDIT_CHECKLIST_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_checklist",
            resource_id=str(checklist.id),
            description=f"Checklist generated for engagement {engagement.engagement_code} "
            f"with {len(STANDARD_CHECKLIST_TEMPLATE)} standard items",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return checklist

    async def add_item(
        self,
        company_id: uuid.UUID,
        engagement_id: uuid.UUID,
        payload: AuditChecklistItemCreate,
        current_user: User,
        meta: RequestMeta,
    ) -> AuditChecklistItem:
        checklist = await self.get_or_create(company_id, engagement_id, current_user, meta)

        item = AuditChecklistItem(
            checklist_id=checklist.id,
            engagement_id=engagement_id,
            company_id=company_id,
            category=payload.category,
            title=payload.title,
            description=payload.description,
            order_index=payload.order_index,
        )
        await self.repo.add_item(item)

        await self.audit.log(
            action=AuditAction.AUDIT_CHECKLIST_UPDATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_checklist_item",
            resource_id=str(item.id),
            description=f"Checklist item added: {item.title}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return item

    async def update_item(
        self,
        company_id: uuid.UUID,
        item_id: uuid.UUID,
        payload: AuditChecklistItemUpdate,
        current_user: User,
        meta: RequestMeta,
    ) -> AuditChecklistItem:
        item = await self.repo.get_item_for_company(item_id, company_id)
        if item is None:
            raise NotFoundError("Checklist item not found", code="AUDIT_CHECKLIST_ITEM_NOT_FOUND")

        if payload.status is not None:
            item.status = payload.status
            if payload.status == AuditChecklistItemStatus.COMPLETED:
                item.completed_by = current_user.id
                item.completed_at = datetime.now(timezone.utc)
            else:
                item.completed_by = None
                item.completed_at = None
        if payload.assigned_to is not None:
            item.assigned_to = payload.assigned_to
        if payload.notes is not None:
            item.notes = payload.notes

        await self.db.flush()
        await self.db.refresh(item)

        action = (
            AuditAction.AUDIT_CHECKLIST_COMPLETED
            if item.status == AuditChecklistItemStatus.COMPLETED
            else AuditAction.AUDIT_CHECKLIST_UPDATED
        )
        await self.audit.log(
            action=action,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="audit_checklist_item",
            resource_id=str(item.id),
            description=f"Checklist item '{item.title}' updated to {item.status.value}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return item
