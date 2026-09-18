import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.tds_challan import TDSChallan
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.tds_challan import (
    TDSChallanAllocateRequest,
    TDSChallanAllocationRead,
    TDSChallanCreate,
    TDSChallanRead,
    TDSChallanUpdate,
)
from app.services.auth_service import RequestMeta
from app.services.tds_challan_service import TDSChallanService

router = APIRouter(prefix="/tds/challans", tags=["tds-challans"])


async def _to_read(challan: TDSChallan, service: TDSChallanService) -> TDSChallanRead:
    allocated = await service.allocated_amount(challan.id)
    return TDSChallanRead(
        id=challan.id,
        company_id=challan.company_id,
        financial_year_id=challan.financial_year_id,
        challan_number=challan.challan_number,
        challan_date=challan.challan_date,
        amount=challan.amount,
        status=challan.status,
        bank_reference_number=challan.bank_reference_number,
        notes=challan.notes,
        allocated_amount=allocated,
        unallocated_amount=challan.amount - allocated,
        created_at=challan.created_at,
        updated_at=challan.updated_at,
    )


@router.post("", response_model=SuccessResponse[TDSChallanRead], status_code=201)
async def create_tds_challan(
    company_id: uuid.UUID,
    payload: TDSChallanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_CHALLAN_CREATE.value)),
):
    service = TDSChallanService(db)
    challan = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=await _to_read(challan, service), message="TDS challan created")


@router.get("", response_model=SuccessResponse[PaginatedData[TDSChallanRead]])
async def list_tds_challans(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_CHALLAN_VIEW.value)),
):
    service = TDSChallanService(db)
    items, total = await service.list(
        company_id, financial_year_id=financial_year_id, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[await _to_read(i, service) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{challan_id}", response_model=SuccessResponse[TDSChallanRead])
async def get_tds_challan(
    challan_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_CHALLAN_VIEW.value)),
):
    service = TDSChallanService(db)
    challan = await service.get(company_id, challan_id)
    return SuccessResponse(data=await _to_read(challan, service))


@router.patch("/{challan_id}", response_model=SuccessResponse[TDSChallanRead])
async def update_tds_challan(
    challan_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: TDSChallanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_CHALLAN_UPDATE.value)),
):
    service = TDSChallanService(db)
    challan = await service.update(company_id, challan_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=await _to_read(challan, service), message="TDS challan updated")


@router.post("/{challan_id}/allocate", response_model=SuccessResponse[TDSChallanAllocationRead])
async def allocate_tds_challan(
    challan_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: TDSChallanAllocateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_CHALLAN_UPDATE.value)),
):
    service = TDSChallanService(db)
    allocation = await service.allocate(company_id, challan_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=TDSChallanAllocationRead.model_validate(allocation), message="Challan allocated"
    )
