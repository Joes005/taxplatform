import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.gst_profile import GSTProfileCreate, GSTProfileRead, GSTProfileUpdate
from app.services.auth_service import RequestMeta
from app.services.gst_profile_service import GSTProfileService

router = APIRouter(prefix="/gst/profile", tags=["gst-profile"])


@router.post("", response_model=SuccessResponse[GSTProfileRead], status_code=201)
async def create_gst_profile(
    company_id: uuid.UUID,
    payload: GSTProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.GST_CREATE.value)),
):
    service = GSTProfileService(db)
    profile = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=GSTProfileRead.model_validate(profile), message="GST profile created")


@router.get("", response_model=SuccessResponse[GSTProfileRead])
async def get_gst_profile(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GST_VIEW.value)),
):
    service = GSTProfileService(db)
    profile = await service.get(company_id)
    return SuccessResponse(data=GSTProfileRead.model_validate(profile))


@router.patch("", response_model=SuccessResponse[GSTProfileRead])
async def update_gst_profile(
    company_id: uuid.UUID,
    payload: GSTProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.GST_UPDATE.value)),
):
    service = GSTProfileService(db)
    profile = await service.update(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=GSTProfileRead.model_validate(profile), message="GST profile updated")
