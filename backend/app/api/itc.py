import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.gst_enums import ITCCategory, ITCReviewStatus
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.gst_reconciliation import (
    GSTReconciliationResultRead,
    ITCApprovalRequest,
    ITCReviewCommentRequest,
    ITCSummaryEntry,
)
from app.services.auth_service import RequestMeta
from app.services.itc_service import ITCService

router = APIRouter(prefix="/gst/return-periods/{period_id}/itc", tags=["itc"])


@router.get("/summary", response_model=SuccessResponse[dict[str, ITCSummaryEntry]])
async def get_itc_summary(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.ITC_VIEW.value)),
):
    service = ITCService(db)
    summary = await service.get_summary(company_id, period_id)
    return SuccessResponse(data={category.value: ITCSummaryEntry(**entry) for category, entry in summary.items()})


@router.get("", response_model=SuccessResponse[PaginatedData[GSTReconciliationResultRead]])
async def list_itc_results(
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    category: ITCCategory | None = Query(default=None),
    review_status: ITCReviewStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.ITC_VIEW.value)),
):
    service = ITCService(db)
    items, total = await service.list(
        company_id, period_id, category=category, review_status=review_status, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[GSTReconciliationResultRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.post("/{result_id}/review", response_model=SuccessResponse[GSTReconciliationResultRead])
async def mark_itc_reviewed(
    result_id: uuid.UUID,
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ITCReviewCommentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.ITC_REVIEW.value)),
):
    service = ITCService(db)
    result = await service.review(
        company_id,
        result_id,
        status=ITCReviewStatus.REVIEWED,
        comment=payload.comment,
        current_user=current_user,
        meta=meta,
    )
    await db.commit()
    return SuccessResponse(data=GSTReconciliationResultRead.model_validate(result), message="Marked reviewed")


@router.post("/{result_id}/approve", response_model=SuccessResponse[GSTReconciliationResultRead])
async def approve_or_reject_itc(
    result_id: uuid.UUID,
    period_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: ITCApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.ITC_APPROVE.value)),
):
    service = ITCService(db)
    result = await service.review(
        company_id,
        result_id,
        status=ITCReviewStatus.ACCEPTED if payload.approved else ITCReviewStatus.REJECTED,
        comment=payload.comment,
        current_user=current_user,
        meta=meta,
    )
    await db.commit()
    message = "ITC approved" if payload.approved else "ITC rejected"
    return SuccessResponse(data=GSTReconciliationResultRead.model_validate(result), message=message)
