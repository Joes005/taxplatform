import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.audit_checklist import AuditChecklistItemCreate, AuditChecklistItemRead, AuditChecklistItemUpdate, AuditChecklistRead
from app.schemas.common import SuccessResponse
from app.services.audit_checklist_service import AuditChecklistService
from app.services.auth_service import RequestMeta

router = APIRouter(prefix="/audits/engagements/{engagement_id}/checklist", tags=["audit-checklist"])


@router.get("", response_model=SuccessResponse[AuditChecklistRead])
async def get_checklist(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_CHECKLIST_VIEW.value)),
):
    service = AuditChecklistService(db)
    checklist = await service.get_or_create(company_id, engagement_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditChecklistRead.model_validate(checklist))


@router.post("/items", response_model=SuccessResponse[AuditChecklistItemRead], status_code=201)
async def add_checklist_item(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditChecklistItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_CHECKLIST_MANAGE.value)),
):
    service = AuditChecklistService(db)
    item = await service.add_item(company_id, engagement_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditChecklistItemRead.model_validate(item), message="Checklist item added")


@router.patch("/items/{item_id}", response_model=SuccessResponse[AuditChecklistItemRead])
async def update_checklist_item(
    engagement_id: uuid.UUID,
    item_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditChecklistItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_CHECKLIST_MANAGE.value)),
):
    service = AuditChecklistService(db)
    item = await service.update_item(company_id, item_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditChecklistItemRead.model_validate(item), message="Checklist item updated")
