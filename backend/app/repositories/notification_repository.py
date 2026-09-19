import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_enums import NotificationType
from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, notification: Notification) -> Notification:
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def get_by_id_for_user(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification | None:
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        unread_only: bool = False,
        notification_type: NotificationType | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Notification], int]:
        query = select(Notification).where(
            Notification.company_id == company_id, Notification.user_id == user_id
        )
        if unread_only:
            query = query.where(Notification.is_read.is_(False))
        if notification_type is not None:
            query = query.where(Notification.type == notification_type)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def unread_count(self, company_id: uuid.UUID, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.company_id == company_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        return result.scalar_one()

    async def mark_all_read(self, company_id: uuid.UUID, user_id: uuid.UUID) -> None:
        from datetime import datetime, timezone

        from sqlalchemy import update

        await self.db.execute(
            update(Notification)
            .where(
                Notification.company_id == company_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        await self.db.flush()

    async def find_recent_duplicate(
        self,
        *,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> Notification | None:
        """Used to avoid re-raising the same unread notification for the
        same event twice (PHASE9 §19) — e.g. re-running the overdue sweep
        should not spam a fresh `TASK_OVERDUE` row every time it runs."""
        result = await self.db.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.type == notification_type,
                Notification.entity_type == entity_type,
                Notification.entity_id == entity_id,
                Notification.is_read.is_(False),
            )
        )
        return result.scalars().first()
