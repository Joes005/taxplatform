import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.exceptions import NotFoundError
from app.core.permissions import PermissionCode
from app.models.compliance_enums import NotificationType
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.notification import NotificationRead, UnreadCount
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=SuccessResponse[PaginatedData[NotificationRead]])
async def list_notifications(
    company_id: uuid.UUID,
    notification_type: NotificationType | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_NOTIFICATION_VIEW.value)),
):
    service = NotificationService(db)
    items, total = await service.list_for_user(
        company_id, current_user.id, notification_type=notification_type, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[NotificationRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/unread", response_model=SuccessResponse[PaginatedData[NotificationRead]])
async def list_unread_notifications(
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_NOTIFICATION_VIEW.value)),
):
    service = NotificationService(db)
    items, total = await service.list_for_user(
        company_id, current_user.id, unread_only=True, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[NotificationRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/unread-count", response_model=SuccessResponse[UnreadCount])
async def unread_count(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_NOTIFICATION_VIEW.value)),
):
    service = NotificationService(db)
    count = await service.unread_count(company_id, current_user.id)
    return SuccessResponse(data=UnreadCount(unread_count=count))


@router.patch("/{notification_id}/read", response_model=SuccessResponse[NotificationRead])
async def mark_read(
    notification_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_NOTIFICATION_MANAGE.value)),
):
    service = NotificationService(db)
    notification = await service.mark_read(current_user.id, notification_id)
    await db.commit()
    if notification is None:
        raise NotFoundError("Notification not found", code="NOTIFICATION_NOT_FOUND")
    return SuccessResponse(data=NotificationRead.model_validate(notification), message="Marked as read")


@router.post("/read-all", response_model=SuccessResponse[None])
async def mark_all_read(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_NOTIFICATION_MANAGE.value)),
):
    service = NotificationService(db)
    await service.mark_all_read(company_id, current_user.id)
    await db.commit()
    return SuccessResponse(data=None, message="All notifications marked as read")
