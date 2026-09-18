import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.tds_rule import TDSRuleCreate, TDSRuleRead, TDSRuleUpdate
from app.services.auth_service import RequestMeta
from app.services.tds_rule_service import TDSRuleService

router = APIRouter(prefix="/tds/rules", tags=["tds-rules"])


@router.post("", response_model=SuccessResponse[TDSRuleRead], status_code=201)
async def create_tds_rule(
    company_id: uuid.UUID,
    payload: TDSRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_RULE_MANAGE.value)),
):
    service = TDSRuleService(db)
    rule = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=TDSRuleRead.model_validate(rule), message="TDS rule created")


@router.get("", response_model=SuccessResponse[list[TDSRuleRead]])
async def list_tds_rules(
    company_id: uuid.UUID,
    tds_section_id: uuid.UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    as_of: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_RULE_VIEW.value)),
):
    service = TDSRuleService(db)
    rules = await service.list(
        company_id, tds_section_id=tds_section_id, is_active=is_active, as_of=as_of
    )
    return SuccessResponse(data=[TDSRuleRead.model_validate(r) for r in rules])


@router.patch("/{rule_id}", response_model=SuccessResponse[TDSRuleRead])
async def update_tds_rule(
    rule_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: TDSRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_RULE_MANAGE.value)),
):
    service = TDSRuleService(db)
    rule = await service.update(company_id, rule_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=TDSRuleRead.model_validate(rule), message="TDS rule updated")
