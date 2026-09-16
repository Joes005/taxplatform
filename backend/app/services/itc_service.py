"""Input Tax Credit review, built directly on top of the latest
reconciliation run's results (PHASE4 sections 35-38). This service never
changes accounting source data — reviewing/accepting/rejecting an ITC
figure only ever updates the reconciliation result row itself.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.gst_enums import ITCCategory, ITCReviewStatus
from app.models.gst_reconciliation import GSTReconciliationResult
from app.models.user import User
from app.repositories.gst_reconciliation_repository import GSTReconciliationRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

_REVIEW_ACTION_BY_STATUS = {
    ITCReviewStatus.REVIEWED: AuditAction.ITC_REVIEWED,
    ITCReviewStatus.ACCEPTED: AuditAction.ITC_APPROVED,
    ITCReviewStatus.REJECTED: AuditAction.ITC_REJECTED,
}


class ITCService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = GSTReconciliationRepository(db)
        self.audit = AuditService(db)

    async def get_summary(self, company_id: uuid.UUID, return_period_id: uuid.UUID) -> dict:
        run = await self.repo.get_latest_run(company_id, return_period_id)
        if run is None:
            raise NotFoundError(
                "No reconciliation has been run for this return period yet",
                code="GST_RECONCILIATION_NOT_FOUND",
            )
        by_category = await self.repo.summary_for_run(run.id)

        summary = {}
        for category in ITCCategory:
            entry = by_category.get(category, {
                "count": 0,
                "taxable_value": Decimal("0"),
                "cgst_amount": Decimal("0"),
                "sgst_amount": Decimal("0"),
                "igst_amount": Decimal("0"),
                "cess_amount": Decimal("0"),
            })
            entry["total_itc"] = entry["cgst_amount"] + entry["sgst_amount"] + entry["igst_amount"] + entry["cess_amount"]
            summary[category] = entry
        return summary

    async def list(
        self,
        company_id: uuid.UUID,
        return_period_id: uuid.UUID,
        *,
        category: ITCCategory | None,
        review_status: ITCReviewStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[GSTReconciliationResult], int]:
        run = await self.repo.get_latest_run(company_id, return_period_id)
        if run is None:
            raise NotFoundError(
                "No reconciliation has been run for this return period yet",
                code="GST_RECONCILIATION_NOT_FOUND",
            )
        results, total = await self.repo.list_results_for_run(
            run.id, itc_category=category, offset=(page - 1) * page_size, limit=page_size
        )
        if review_status is not None:
            results = [r for r in results if r.itc_review_status == review_status]
        return results, total

    async def review(
        self,
        company_id: uuid.UUID,
        result_id: uuid.UUID,
        *,
        status: ITCReviewStatus,
        comment: str | None,
        current_user: User,
        meta: RequestMeta,
    ) -> GSTReconciliationResult:
        if status == ITCReviewStatus.PENDING:
            raise ValidationAppError("Cannot set ITC review status back to PENDING", code="INVALID_ITC_STATUS")

        result = await self.repo.get_result_by_id_for_company(result_id, company_id)
        if result is None:
            raise NotFoundError("Reconciliation result not found", code="GST_RECONCILIATION_RESULT_NOT_FOUND")

        result.itc_review_status = status
        result.reviewed_by = current_user.id
        result.reviewed_at = datetime.now(timezone.utc)
        result.review_comment = comment
        await self.db.flush()
        await self.db.refresh(result)

        await self.audit.log(
            action=_REVIEW_ACTION_BY_STATUS[status],
            user_id=current_user.id,
            company_id=company_id,
            resource_type="gst_reconciliation_result",
            resource_id=str(result.id),
            description=f"ITC result marked {status.value}",
            metadata={"comment": comment} if comment else None,
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return result
