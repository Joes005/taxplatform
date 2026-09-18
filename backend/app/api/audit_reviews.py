import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.audit_review import (
    AuditReviewCompleteRequest,
    AuditReviewCreate,
    AuditReviewRead,
    AuditReviewReturnRequest,
)
from app.schemas.common import SuccessResponse
from app.services.audit_review_service import AuditReviewService
from app.services.auth_service import RequestMeta

router = APIRouter(prefix="/audits/engagements/{engagement_id}/reviews", tags=["audit-reviews"])


@router.post("", response_model=SuccessResponse[AuditReviewRead], status_code=201)
async def start_review(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_REVIEW.value)),
):
    service = AuditReviewService(db)
    review = await service.start(company_id, engagement_id, payload.review_type, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditReviewRead.model_validate(review), message="Review started")


@router.get("", response_model=SuccessResponse[list[AuditReviewRead]])
async def list_reviews(
    engagement_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_VIEW.value)),
):
    service = AuditReviewService(db)
    reviews = await service.list_for_engagement(company_id, engagement_id)
    return SuccessResponse(data=[AuditReviewRead.model_validate(r) for r in reviews])


@router.post("/{review_id}/complete", response_model=SuccessResponse[AuditReviewRead])
async def complete_review(
    engagement_id: uuid.UUID,
    review_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditReviewCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_REVIEW.value)),
):
    service = AuditReviewService(db)
    review = await service.complete(company_id, review_id, payload.summary, payload.notes, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditReviewRead.model_validate(review), message="Review completed")


@router.post("/{review_id}/return", response_model=SuccessResponse[AuditReviewRead])
async def return_review(
    engagement_id: uuid.UUID,
    review_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: AuditReviewReturnRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.AUDIT_ENGAGEMENT_REVIEW.value)),
):
    service = AuditReviewService(db)
    review = await service.return_review(company_id, review_id, payload.notes, current_user, meta)
    await db.commit()
    return SuccessResponse(data=AuditReviewRead.model_validate(review), message="Review returned")
