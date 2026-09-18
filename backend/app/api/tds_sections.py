import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.permissions import PermissionCode
from app.schemas.common import SuccessResponse
from app.schemas.tds_section import TDSSectionRead
from app.services.tds_section_service import TDSSectionService

router = APIRouter(prefix="/tds/sections", tags=["tds-sections"])


@router.get("", response_model=SuccessResponse[list[TDSSectionRead]])
async def list_tds_sections(
    company_id: uuid.UUID,
    is_active: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_RULE_VIEW.value)),
):
    service = TDSSectionService(db)
    sections = await service.list(is_active=is_active)
    return SuccessResponse(data=[TDSSectionRead.model_validate(s) for s in sections])
