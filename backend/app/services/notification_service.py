"""In-app notifications and extensible notification provider architecture (PHASE9 §18).

This module defines the `NotificationProvider` protocol and concrete providers:
- `InAppNotificationProvider`: Default provider. Persists notifications in the database.
- `LoggingNotificationProvider`: Logs notification events via Python's standard logging.
- `NoopNotificationProvider`: Silent provider for testing or suppressing external notifications.
- `CompositeNotificationProvider`: Dispatches notifications to multiple providers safely.

Future SMTP / SMS Integration:
To add an SMTP email provider (e.g. for external compliance alerts):
1. Create `EmailNotificationProvider(NotificationProvider)` implementing `send(notification)`.
2. Connect to an SMTP server using `aiosmtplib` with host, port, username, password.
3. Configure via `Settings.SMTP_HOST`, `Settings.SMTP_PORT`, etc.
4. Add to `CompositeNotificationProvider([InAppNotificationProvider(), EmailNotificationProvider()])`.

To add an SMS provider (e.g. Twilio / Gupshup):
1. Create `SMSNotificationProvider(NotificationProvider)` implementing `send(notification)`.
2. Use HTTP client (e.g. `httpx`) to send payload to SMS gateway.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Protocol, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.compliance_enums import NotificationSeverity, NotificationType
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.services.audit_service import AuditAction, AuditService

logger = logging.getLogger("app.notifications")


class NotificationProvider(Protocol):
    """Protocol for all notification delivery mechanisms."""

    async def send(self, notification: Notification) -> None: ...


class InAppNotificationProvider:
    """The standard in-app provider — the database row itself, once persisted,
    is the primary delivery record; send is a no-op."""

    async def send(self, notification: Notification) -> None:
        return None


class LoggingNotificationProvider:
    """Logs notification events to the application logger.
    Useful for development, auditing, and fallback when external delivery fails."""

    async def send(self, notification: Notification) -> None:
        logger.info(
            "Notification [%s] for user %s (company %s): %s - %s",
            notification.type.value if hasattr(notification.type, "value") else notification.type,
            notification.user_id,
            notification.company_id,
            notification.title,
            notification.message,
        )


class NoopNotificationProvider:
    """Silent notification provider that does nothing. Useful for unit testing."""

    async def send(self, notification: Notification) -> None:
        return None


class CompositeNotificationProvider:
    """Fans out notification delivery to multiple providers sequentially.
    Ensures that an exception in one external provider does not abort delivery
    to subsequent providers."""

    def __init__(self, providers: Sequence[NotificationProvider]) -> None:
        self.providers = list(providers)

    async def send(self, notification: Notification) -> None:
        for provider in self.providers:
            try:
                await provider.send(notification)
            except Exception as e:
                logger.warning(
                    "Error delivering notification %s via provider %s: %s",
                    notification.id,
                    provider.__class__.__name__,
                    e,
                )


def get_notification_provider(provider_type: str | None = None) -> NotificationProvider:
    """Factory that returns the configured notification provider."""
    ptype = (provider_type or getattr(settings, "NOTIFICATION_PROVIDER", "in_app")).lower()
    if ptype == "logging":
        return LoggingNotificationProvider()
    elif ptype == "noop":
        return NoopNotificationProvider()
    elif ptype == "composite":
        return CompositeNotificationProvider([InAppNotificationProvider(), LoggingNotificationProvider()])
    return InAppNotificationProvider()


class NotificationService:
    def __init__(self, db: AsyncSession, provider: NotificationProvider | None = None) -> None:
        self.db = db
        self.repo = NotificationRepository(db)
        self.audit = AuditService(db)
        self.provider = provider or get_notification_provider()

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
