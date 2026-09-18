import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.tds_profile import TDSProfileCreate, TDSProfileRead, TDSProfileUpdate
from app.services.auth_service import RequestMeta
from app.services.tds_profile_service import TDSProfileService

router = APIRouter(prefix="/tds/profile", tags=["tds-profile"])


@router.post("", response_model=SuccessResponse[TDSProfileRead], status_code=201)
async def create_tds_profile(
    company_id: uuid.UUID,
    payload: TDSProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_CREATE.value)),
):
    service = TDSProfileService(db)
    profile = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=TDSProfileRead.model_validate(profile), message="TDS profile created")


@router.get("", response_model=SuccessResponse[TDSProfileRead])
async def get_tds_profile(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_VIEW.value)),
):
    service = TDSProfileService(db)
    profile = await service.get(company_id)
    return SuccessResponse(data=TDSProfileRead.model_validate(profile))


@router.patch("", response_model=SuccessResponse[TDSProfileRead])
async def update_tds_profile(
    company_id: uuid.UUID,
    payload: TDSProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_UPDATE.value)),
):
    service = TDSProfileService(db)
    profile = await service.update(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=TDSProfileRead.model_validate(profile), message="TDS profile updated")
