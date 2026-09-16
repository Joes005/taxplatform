import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.permissions import PermissionCode
from app.schemas.common import SuccessResponse
from app.schemas.gstr3b import GSTR3BSummary
from app.services.gstr3b_service import GSTR3BService

router = APIRouter(prefix="/gst/return-periods/{period_id}/gstr3b", tags=["gstr3b"])


@router.get("", response_model=SuccessResponse[GSTR3BSummary])
async def get_gstr3b_summary(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GSTR3B_VIEW.value)),
):
    service = GSTR3BService(db)
    summary = await service.generate(company_id, period_id)
    return SuccessResponse(data=summary)
