import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.exceptions import NotFoundError
from app.core.permissions import PermissionCode
from app.repositories.gstr2b_record_repository import GSTR2BRecordRepository
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.gstr2b_record import GSTR2BRecordRead

router = APIRouter(prefix="/gst/gstr2b", tags=["gstr2b"])


@router.get("", response_model=SuccessResponse[PaginatedData[GSTR2BRecordRead]])
async def list_gstr2b_records(
    company_id: uuid.UUID,
    return_period_id: uuid.UUID | None = Query(default=None),
    supplier_gstin: str | None = Query(default=None),
    invoice_number: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GSTR2B_VIEW.value)),
):
    repo = GSTR2BRecordRepository(db)
    items, total = await repo.list_for_company(
        company_id,
        return_period_id=return_period_id,
        supplier_gstin=supplier_gstin,
        invoice_number=invoice_number,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    data = PaginatedData(
        items=[GSTR2BRecordRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{record_id}", response_model=SuccessResponse[GSTR2BRecordRead])
async def get_gstr2b_record(
    record_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GSTR2B_VIEW.value)),
):
    repo = GSTR2BRecordRepository(db)
    record = await repo.get_by_id_for_company(record_id, company_id)
    if record is None:
        raise NotFoundError("GSTR-2B record not found", code="GSTR2B_RECORD_NOT_FOUND")
    return SuccessResponse(data=GSTR2BRecordRead.model_validate(record))
