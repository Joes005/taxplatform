import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.gst_tax_rate import GSTTaxRateCreate, GSTTaxRateRead, GSTTaxRateUpdate
from app.services.auth_service import RequestMeta
from app.services.gst_tax_rate_service import GSTTaxRateService

router = APIRouter(prefix="/gst/tax-rates", tags=["gst-tax-rates"])


@router.post("", response_model=SuccessResponse[GSTTaxRateRead], status_code=201)
async def create_tax_rate(
    company_id: uuid.UUID,
    payload: GSTTaxRateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.GST_CREATE.value)),
):
    service = GSTTaxRateService(db)
    rate = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=GSTTaxRateRead.model_validate(rate), message="GST tax rate created")


@router.get("", response_model=SuccessResponse[list[GSTTaxRateRead]])
async def list_tax_rates(
    company_id: uuid.UUID,
    is_active: bool | None = Query(default=None),
    as_of: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GST_VIEW.value)),
):
    service = GSTTaxRateService(db)
    rates = await service.list(company_id, is_active=is_active, as_of=as_of)
    return SuccessResponse(data=[GSTTaxRateRead.model_validate(r) for r in rates])


@router.patch("/{rate_id}", response_model=SuccessResponse[GSTTaxRateRead])
async def update_tax_rate(
    rate_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: GSTTaxRateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.GST_UPDATE.value)),
):
    service = GSTTaxRateService(db)
    rate = await service.update(company_id, rate_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=GSTTaxRateRead.model_validate(rate), message="GST tax rate updated")
