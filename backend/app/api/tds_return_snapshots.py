import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.tds_enums import TDSReturnType
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.tds_return_snapshot import (
    TDSReturnSnapshotGenerateRequest,
    TDSReturnSnapshotRead,
    TDSReturnSnapshotTransitionRequest,
)
from app.services.auth_service import RequestMeta
from app.services.tds_return_snapshot_service import TDSReturnSnapshotService

router = APIRouter(prefix="/tds/return-periods/{period_id}", tags=["tds-return-workflow"])


@router.post("/generate", response_model=SuccessResponse[TDSReturnSnapshotRead], status_code=201)
async def generate_return_snapshot(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: TDSReturnSnapshotGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_RETURN_GENERATE.value)),
):
    service = TDSReturnSnapshotService(db)
    snapshot = await service.generate(company_id, period_id, payload.return_type, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=TDSReturnSnapshotRead.model_validate(snapshot),
        message=f"{payload.return_type.value} version {snapshot.version} generated",
    )


@router.post("/submit-for-review", response_model=SuccessResponse[TDSReturnSnapshotRead])
async def submit_for_review(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: TDSReturnSnapshotTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_RETURN_VALIDATE.value)),
):
    service = TDSReturnSnapshotService(db)
    snapshot = await service.submit_for_review(company_id, period_id, payload.return_type, current_user, meta)
    await db.commit()
    return SuccessResponse(data=TDSReturnSnapshotRead.model_validate(snapshot), message="Submitted for review")


@router.post("/approve", response_model=SuccessResponse[TDSReturnSnapshotRead])
async def approve_return_snapshot(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: TDSReturnSnapshotTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_RETURN_APPROVE.value)),
):
    service = TDSReturnSnapshotService(db)
    snapshot = await service.approve(
        company_id, period_id, payload.return_type, current_user, meta, payload.comment
    )
    await db.commit()
    return SuccessResponse(data=TDSReturnSnapshotRead.model_validate(snapshot), message="Approved")


@router.post("/request-changes", response_model=SuccessResponse[TDSReturnSnapshotRead])
async def request_changes(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: TDSReturnSnapshotTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_RETURN_APPROVE.value)),
):
    service = TDSReturnSnapshotService(db)
    snapshot = await service.request_changes(
        company_id, period_id, payload.return_type, current_user, meta, payload.comment
    )
    await db.commit()
    return SuccessResponse(data=TDSReturnSnapshotRead.model_validate(snapshot), message="Changes requested")


@router.post("/finalize", response_model=SuccessResponse[TDSReturnSnapshotRead])
async def finalize_return_snapshot(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: TDSReturnSnapshotGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_RETURN_FINALIZE.value)),
):
    service = TDSReturnSnapshotService(db)
    snapshot = await service.finalize(company_id, period_id, payload.return_type, current_user, meta)
    await db.commit()
    return SuccessResponse(data=TDSReturnSnapshotRead.model_validate(snapshot), message="Finalized")


@router.get("/snapshots", response_model=SuccessResponse[list[TDSReturnSnapshotRead]])
async def list_return_snapshots(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    return_type: TDSReturnType = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_RETURN_VIEW.value)),
):
    service = TDSReturnSnapshotService(db)
    versions = await service.list_versions(company_id, period_id, return_type)
    return SuccessResponse(data=[TDSReturnSnapshotRead.model_validate(v) for v in versions])


@router.get("/snapshots/latest", response_model=SuccessResponse[TDSReturnSnapshotRead])
async def get_latest_return_snapshot(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    return_type: TDSReturnType = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_RETURN_VIEW.value)),
):
    service = TDSReturnSnapshotService(db)
    snapshot = await service.get_latest(company_id, period_id, return_type)
    return SuccessResponse(data=TDSReturnSnapshotRead.model_validate(snapshot))
