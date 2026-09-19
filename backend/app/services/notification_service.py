"""In-app notifications only (PHASE9 §18) — no email/SMS/push provider
exists anywhere in this codebase. `InAppNotificationProvider` is the only
implementation of the small `NotificationProvider` protocol below; a
future `EmailNotificationProvider`/`SMSNotificationProvider` can be added
without touching any caller, since every trigger helper here goes through
`NotificationService.notify()` rather than writing a `Notification` row
directly.
"""

import uuid
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_enums import NotificationSeverity, NotificationType
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.services.audit_service import AuditAction, AuditService


class NotificationProvider(Protocol):
    async def send(self, notification: Notification) -> None: ...


class InAppNotificationProvider:
    """The only provider Phase 9 ships — the row itself, once persisted,
    *is* the delivery; there is nothing further to "send" anywhere."""

    async def send(self, notification: Notification) -> None:
        return None


class NotificationService:
    def __init__(self, db: AsyncSession, provider: NotificationProvider | None = None) -> None:
        self.db = db
        self.repo = NotificationRepository(db)
        self.audit = AuditService(db)
        self.provider = provider or InAppNotificationProvider()

    async def notify(
        self,
        *,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        severity: NotificationSeverity = NotificationSeverity.INFO,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        dedupe: bool = True,
    ) -> Notification | None:
        """Creates one notification, skipping it if an unread duplicate
        for the same (user, type, entity) already exists (PHASE9 §19) —
        so re-running the overdue sweep or re-viewing a task never spams
        the same user with the same event twice."""
        if dedupe and entity_type is not None and entity_id is not None:
            existing = await self.repo.find_recent_duplicate(
                user_id=user_id, notification_type=notification_type, entity_type=entity_type, entity_id=entity_id
            )
            if existing is not None:
                return None

        notification = Notification(
            company_id=company_id,
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            severity=severity,
            entity_type=entity_type,
            entity_id=entity_id,
            created_at=datetime.now(timezone.utc),
        )
        await self.repo.create(notification)
        await self.provider.send(notification)

        await self.audit.log(
            action=AuditAction.NOTIFICATION_CREATED,
            user_id=user_id,
            company_id=company_id,
            resource_type="notification",
            resource_id=str(notification.id),
            description=f"{notification_type.value} notification created",
        )
        return notification

    async def list_for_user(
        self,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        unread_only: bool = False,
        notification_type: NotificationType | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Notification], int]:
        return await self.repo.list_for_user(
            company_id,
            user_id,
            unread_only=unread_only,
            notification_type=notification_type,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    async def unread_count(self, company_id: uuid.UUID, user_id: uuid.UUID) -> int:
        return await self.repo.unread_count(company_id, user_id)

    async def mark_read(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification | None:
        notification = await self.repo.get_by_id_for_user(notification_id, user_id)
        if notification is None:
            return None
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            await self.db.flush()
            await self.db.refresh(notification)
        return notification

    async def mark_all_read(self, company_id: uuid.UUID, user_id: uuid.UUID) -> None:
        await self.repo.mark_all_read(company_id, user_id)
