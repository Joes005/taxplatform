import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.gst_enums import GSTReturnType
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.gst_return_snapshot import (
    GSTReturnSnapshotGenerateRequest,
    GSTReturnSnapshotRead,
    GSTReturnSnapshotTransitionRequest,
)
from app.services.auth_service import RequestMeta
from app.services.gst_return_snapshot_service import GSTReturnSnapshotService

router = APIRouter(prefix="/gst/return-periods/{period_id}", tags=["gst-return-workflow"])


@router.post("/generate", response_model=SuccessResponse[GSTReturnSnapshotRead], status_code=201)
async def generate_return_snapshot(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: GSTReturnSnapshotGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.GST_RETURN_GENERATE.value)),
):
    service = GSTReturnSnapshotService(db)
    snapshot = await service.generate(company_id, period_id, payload.return_type, current_user, meta)
    await db.commit()
    return SuccessResponse(
        data=GSTReturnSnapshotRead.model_validate(snapshot),
        message=f"{payload.return_type.value} version {snapshot.version} generated",
    )


@router.post("/submit-for-review", response_model=SuccessResponse[GSTReturnSnapshotRead])
async def submit_for_review(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: GSTReturnSnapshotTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.GST_RETURN_VALIDATE.value)),
):
    service = GSTReturnSnapshotService(db)
    snapshot = await service.submit_for_review(company_id, period_id, payload.return_type, current_user, meta)
    await db.commit()
    return SuccessResponse(data=GSTReturnSnapshotRead.model_validate(snapshot), message="Submitted for review")


@router.post("/approve", response_model=SuccessResponse[GSTReturnSnapshotRead])
async def approve_return_snapshot(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: GSTReturnSnapshotTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.GST_RETURN_APPROVE.value)),
):
    service = GSTReturnSnapshotService(db)
    snapshot = await service.approve(
        company_id, period_id, payload.return_type, current_user, meta, payload.comment
    )
    await db.commit()
    return SuccessResponse(data=GSTReturnSnapshotRead.model_validate(snapshot), message="Approved")


@router.post("/request-changes", response_model=SuccessResponse[GSTReturnSnapshotRead])
async def request_changes(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: GSTReturnSnapshotTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.GST_RETURN_APPROVE.value)),
):
    service = GSTReturnSnapshotService(db)
    snapshot = await service.request_changes(
        company_id, period_id, payload.return_type, current_user, meta, payload.comment
    )
    await db.commit()
    return SuccessResponse(data=GSTReturnSnapshotRead.model_validate(snapshot), message="Changes requested")


@router.post("/finalize", response_model=SuccessResponse[GSTReturnSnapshotRead])
async def finalize_return_snapshot(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: GSTReturnSnapshotGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.GST_RETURN_FINALIZE.value)),
):
    service = GSTReturnSnapshotService(db)
    snapshot = await service.finalize(company_id, period_id, payload.return_type, current_user, meta)
    await db.commit()
    return SuccessResponse(data=GSTReturnSnapshotRead.model_validate(snapshot), message="Finalized")


@router.get("/snapshots", response_model=SuccessResponse[list[GSTReturnSnapshotRead]])
async def list_return_snapshots(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    return_type: GSTReturnType = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GST_RETURN_VIEW.value)),
):
    service = GSTReturnSnapshotService(db)
    versions = await service.list_versions(company_id, period_id, return_type)
    return SuccessResponse(data=[GSTReturnSnapshotRead.model_validate(v) for v in versions])


@router.get("/snapshots/latest", response_model=SuccessResponse[GSTReturnSnapshotRead])
async def get_latest_return_snapshot(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    return_type: GSTReturnType = Query(...),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.GST_RETURN_VIEW.value)),
):
    service = GSTReturnSnapshotService(db)
    snapshot = await service.get_latest(company_id, period_id, return_type)
    return SuccessResponse(data=GSTReturnSnapshotRead.model_validate(snapshot))
