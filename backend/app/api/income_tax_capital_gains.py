import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.income_tax_capital_gain import (
    IncomeTaxCapitalGainCreate,
    IncomeTaxCapitalGainRead,
    IncomeTaxCapitalGainUpdate,
)
from app.services.auth_service import RequestMeta
from app.services.capital_gain_service import CapitalGainService

router = APIRouter(prefix="/income-tax/capital-gains", tags=["income-tax-capital-gains"])


@router.post("", response_model=SuccessResponse[IncomeTaxCapitalGainRead], status_code=201)
async def create_capital_gain(
    company_id: uuid.UUID,
    payload: IncomeTaxCapitalGainCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CREATE.value)),
):
    service = CapitalGainService(db)
    entity = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxCapitalGainRead.model_validate(entity), message="Capital gain recorded")


@router.get("", response_model=SuccessResponse[list[IncomeTaxCapitalGainRead]])
async def list_capital_gains(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = CapitalGainService(db)
    items = await service.list_for_fy(company_id, financial_year_id)
    return SuccessResponse(data=[IncomeTaxCapitalGainRead.model_validate(i) for i in items])


@router.patch("/{entity_id}", response_model=SuccessResponse[IncomeTaxCapitalGainRead])
async def update_capital_gain(
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: IncomeTaxCapitalGainUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = CapitalGainService(db)
    entity = await service.update(company_id, entity_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxCapitalGainRead.model_validate(entity), message="Capital gain updated")


@router.delete("/{entity_id}", response_model=SuccessResponse[None])
async def delete_capital_gain(
    entity_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = CapitalGainService(db)
    await service.delete(company_id, entity_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=None, message="Capital gain deleted")
