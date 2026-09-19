import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.income_tax_profile import IncomeTaxProfileCreate, IncomeTaxProfileRead, IncomeTaxProfileUpdate
from app.schemas.income_tax_rule_set import IncomeTaxRuleSetRead
from app.services.auth_service import RequestMeta
from app.services.income_tax_profile_service import IncomeTaxProfileService
from app.services.income_tax_rule_service import IncomeTaxRuleService

router = APIRouter(prefix="/income-tax", tags=["income-tax-profile"])


@router.get("/profile", response_model=SuccessResponse[IncomeTaxProfileRead])
async def get_profile(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = IncomeTaxProfileService(db)
    profile = await service.get(company_id)
    return SuccessResponse(data=IncomeTaxProfileRead.model_validate(profile))


@router.post("/profile", response_model=SuccessResponse[IncomeTaxProfileRead], status_code=201)
async def create_profile(
    company_id: uuid.UUID,
    payload: IncomeTaxProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_CREATE.value)),
):
    service = IncomeTaxProfileService(db)
    profile = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxProfileRead.model_validate(profile), message="Income Tax profile created")


@router.patch("/profile", response_model=SuccessResponse[IncomeTaxProfileRead])
async def update_profile(
    company_id: uuid.UUID,
    payload: IncomeTaxProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_UPDATE.value)),
):
    service = IncomeTaxProfileService(db)
    profile = await service.update(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=IncomeTaxProfileRead.model_validate(profile), message="Income Tax profile updated")


@router.get("/rules", response_model=SuccessResponse[list[IncomeTaxRuleSetRead]])
async def list_rule_sets(
    company_id: uuid.UUID,
    assessment_year: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.INCOME_TAX_VIEW.value)),
):
    service = IncomeTaxRuleService(db)
    rule_sets = await service.list_for_assessment_year(assessment_year)
    return SuccessResponse(data=[IncomeTaxRuleSetRead.model_validate(r) for r in rule_sets])
