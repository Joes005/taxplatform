import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.income_tax_loss import IncomeTaxLossCreate, IncomeTaxLossRead
from app.services.auth_service import RequestMeta
from app.services.income_tax_loss_service import IncomeTaxLossService

router = APIRouter(prefix="/income-tax/losses", tags=["income-tax-losses"])


class LossSetoffRequest(BaseModel):
    setoff_amount: Decimal


@router.post("", response_model=SuccessResponse[IncomeTaxLossRead], status_code=201)
async def create_loss(
    company_id: uuid.UUID,
    payload: IncomeTaxLossCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CREATE.value)),
):
    service = IncomeTaxLossService(db)
    entity = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxLossRead.model_validate(entity), message="Loss recorded")


@router.get("", response_model=SuccessResponse[list[IncomeTaxLossRead]])
async def list_losses(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = IncomeTaxLossService(db)
    items = await service.list_for_company(company_id)
    return SuccessResponse(data=[IncomeTaxLossRead.model_validate(i) for i in items])


@router.patch("/{loss_id}/setoff", response_model=SuccessResponse[IncomeTaxLossRead])
async def set_loss_setoff(
    loss_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: LossSetoffRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = IncomeTaxLossService(db)
    entity = await service.set_setoff_amount(company_id, loss_id, payload.setoff_amount, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxLossRead.model_validate(entity), message="Loss set-off updated")
