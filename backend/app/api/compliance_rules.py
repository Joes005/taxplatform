import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.compliance_enums import ComplianceCategory, ComplianceModule
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.compliance_obligation import ComplianceObligationRead
from app.schemas.compliance_rule import ComplianceRuleCreate, ComplianceRuleRead, ComplianceRuleUpdate, GenerateObligationRequest
from app.services.auth_service import RequestMeta
from app.services.compliance_obligation_service import ComplianceObligationService
from app.services.compliance_rule_service import ComplianceRuleService

router = APIRouter(prefix="/compliance/rules", tags=["compliance-rules"])


@router.post("", response_model=SuccessResponse[ComplianceRuleRead], status_code=201)
async def create_rule(
    company_id: uuid.UUID,
    payload: ComplianceRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_RULE_MANAGE.value)),
):
    service = ComplianceRuleService(db)
    rule = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ComplianceRuleRead.model_validate(rule), message="Compliance rule created")


@router.get("", response_model=SuccessResponse[list[ComplianceRuleRead]])
async def list_rules(
    company_id: uuid.UUID,
    category: ComplianceCategory | None = Query(default=None),
    module: ComplianceModule | None = Query(default=None),
    active_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    service = ComplianceRuleService(db)
    rules = await service.list_for_company(company_id, category=category, module=module, active_only=active_only)
    return SuccessResponse(data=[ComplianceRuleRead.model_validate(r) for r in rules])


@router.get("/{rule_id}", response_model=SuccessResponse[ComplianceRuleRead])
async def get_rule(
    rule_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_VIEW.value)),
):
    service = ComplianceRuleService(db)
    rule = await service.get(company_id, rule_id)
    return SuccessResponse(data=ComplianceRuleRead.model_validate(rule))


@router.patch("/{rule_id}", response_model=SuccessResponse[ComplianceRuleRead])
async def update_rule(
    rule_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ComplianceRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_RULE_MANAGE.value)),
):
    service = ComplianceRuleService(db)
    rule = await service.update(company_id, rule_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ComplianceRuleRead.model_validate(rule), message="Compliance rule updated")


@router.post("/{rule_id}/activate", response_model=SuccessResponse[ComplianceRuleRead])
async def activate_rule(
    rule_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_RULE_MANAGE.value)),
):
    service = ComplianceRuleService(db)
    rule = await service.set_active(company_id, rule_id, True, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ComplianceRuleRead.model_validate(rule), message="Compliance rule activated")


@router.post("/{rule_id}/deactivate", response_model=SuccessResponse[ComplianceRuleRead])
async def deactivate_rule(
    rule_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_RULE_MANAGE.value)),
):
    service = ComplianceRuleService(db)
    rule = await service.set_active(company_id, rule_id, False, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ComplianceRuleRead.model_validate(rule), message="Compliance rule deactivated")


@router.post(
    "/{rule_id}/generate-obligations",
    response_model=SuccessResponse[ComplianceObligationRead],
    status_code=201,
)
async def generate_obligations(
    rule_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: GenerateObligationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.COMPLIANCE_OBLIGATION_MANAGE.value)),
):
    rule_service = ComplianceRuleService(db)
    rule = await rule_service.get(company_id, rule_id)

    obligation_service = ComplianceObligationService(db)
    obligation = await obligation_service.generate_from_rule(
        company_id,
        rule_code=rule.code,
        financial_year_id=payload.financial_year_id,
        tax_period=payload.tax_period,
        period_start=payload.period_start,
        period_end=payload.period_end,
        current_user=current_user,
        meta=meta,
    )
    await db.commit()
    return SuccessResponse(
        data=ComplianceObligationRead.model_validate(obligation),
        message="Obligation generated from rule",
    )
