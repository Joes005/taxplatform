"""Return-level review workflow (PHASE4 sections 16, 43, 75, 76).

Generating a return preparation snapshots the current GSTR-1/GSTR-3B
numbers so a later edit to the underlying accounting data can never
silently change something already under review or finalized — the next
`generate` call simply produces a new version instead. A FINALIZED
snapshot is immutable: no transition function accepts it as a starting
state.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError, NotFoundError
from app.models.gst_enums import GSTReturnPeriodStatus, GSTReturnSnapshotStatus, GSTReturnType
from app.models.gst_return_snapshot import GSTReturnSnapshot
from app.models.user import User
from app.repositories.gst_return_period_repository import GSTReturnPeriodRepository
from app.repositories.gst_return_snapshot_repository import GSTReturnSnapshotRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.gstr1_service import GSTR1Service
from app.services.gstr3b_service import GSTR3BService

# (from_status, action) -> to_status. Anything not listed here is refused —
# in particular, nothing transitions *out of* FINALIZED, and CHANGES_REQUESTED
# is a dead end for that version (a new `generate` call starts the next one).
_TRANSITIONS: dict[tuple[GSTReturnSnapshotStatus, str], GSTReturnSnapshotStatus] = {
    (GSTReturnSnapshotStatus.DRAFT, "submit"): GSTReturnSnapshotStatus.UNDER_REVIEW,
    (GSTReturnSnapshotStatus.UNDER_REVIEW, "approve"): GSTReturnSnapshotStatus.APPROVED,
    (GSTReturnSnapshotStatus.UNDER_REVIEW, "request_changes"): GSTReturnSnapshotStatus.CHANGES_REQUESTED,
    (GSTReturnSnapshotStatus.APPROVED, "finalize"): GSTReturnSnapshotStatus.FINALIZED,
}

_AUDIT_ACTION_BY_ACTION = {
    "submit": AuditAction.GST_RETURN_VALIDATED,
    "approve": AuditAction.GST_RETURN_APPROVED,
    "request_changes": AuditAction.GST_RETURN_CHANGES_REQUESTED,
    "finalize": AuditAction.GST_RETURN_FINALIZED,
}


class GSTReturnSnapshotService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = GSTReturnSnapshotRepository(db)
        self.period_repo = GSTReturnPeriodRepository(db)
        self.gstr1 = GSTR1Service(db)
        self.gstr3b = GSTR3BService(db)
        self.audit = AuditService(db)

    async def generate(
        self,
        company_id: uuid.UUID,
        return_period_id: uuid.UUID,
        return_type: GSTReturnType,
        current_user: User,
        meta: RequestMeta,
    ) -> GSTReturnSnapshot:
        period = await self.period_repo.get_by_id_for_company(return_period_id, company_id)
        if period is None:
            raise NotFoundError("GST return period not found", code="GST_RETURN_PERIOD_NOT_FOUND")

        if return_type == GSTReturnType.GSTR1:
            summary = await self.gstr1.get_overview(company_id, return_period_id)
        else:
            summary = await self.gstr3b.generate(company_id, return_period_id)

        latest = await self.repo.get_latest(company_id, return_period_id, return_type)
        next_version = (latest.version + 1) if latest else 1

        snapshot = GSTReturnSnapshot(
            company_id=company_id,
            return_period_id=return_period_id,
            return_type=return_type,
            version=next_version,
            status=GSTReturnSnapshotStatus.DRAFT,
            generated_at=datetime.now(timezone.utc),
            generated_by=current_user.id,
            summary_data=summary.model_dump(mode="json"),
        )
        await self.repo.create(snapshot)

        await self.audit.log(
            action=AuditAction.GST_RETURN_GENERATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="gst_return_snapshot",
            resource_id=str(snapshot.id),
            description=f"{return_type.value} version {next_version} generated for return period {return_period_id}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return snapshot

    async def get_latest(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID, return_type: GSTReturnType
    ) -> GSTReturnSnapshot:
        snapshot = await self.repo.get_latest(company_id, return_period_id, return_type)
        if snapshot is None:
            raise NotFoundError(
                f"No {return_type.value} has been generated for this return period yet",
                code="GST_RETURN_SNAPSHOT_NOT_FOUND",
            )
        return snapshot

    async def list_versions(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID, return_type: GSTReturnType
    ) -> list[GSTReturnSnapshot]:
        return await self.repo.list_versions(company_id, return_period_id, return_type)

    async def _transition(
        self,
        company_id: uuid.UUID,
        return_period_id: uuid.UUID,
        return_type: GSTReturnType,
        action: str,
        current_user: User,
        meta: RequestMeta,
        comment: str | None,
    ) -> GSTReturnSnapshot:
        snapshot = await self.get_latest(company_id, return_period_id, return_type)
        key = (snapshot.status, action)
        if key not in _TRANSITIONS:
            raise InvalidStateError(
                f"Cannot {action.replace('_', ' ')} a {return_type.value} snapshot in status "
                f"{snapshot.status.value}",
                code="INVALID_SNAPSHOT_TRANSITION",
            )

        snapshot.status = _TRANSITIONS[key]
        await self.db.flush()
        await self.db.refresh(snapshot)

        await self._sync_period_status(company_id, return_period_id, snapshot.status)

        await self.audit.log(
            action=_AUDIT_ACTION_BY_ACTION[action],
            user_id=current_user.id,
            company_id=company_id,
            resource_type="gst_return_snapshot",
            resource_id=str(snapshot.id),
            description=f"{return_type.value} version {snapshot.version} moved to {snapshot.status.value}",
            metadata={"comment": comment} if comment else None,
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return snapshot

    async def _sync_period_status(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID, snapshot_status: GSTReturnSnapshotStatus
    ) -> None:
        period = await self.period_repo.get_by_id_for_company(return_period_id, company_id)
        if period is None or period.status == GSTReturnPeriodStatus.ARCHIVED:
            return

        if snapshot_status == GSTReturnSnapshotStatus.FINALIZED:
            gstr1 = await self.repo.get_latest(company_id, return_period_id, GSTReturnType.GSTR1)
            gstr3b = await self.repo.get_latest(company_id, return_period_id, GSTReturnType.GSTR3B)
            both_finalized = (
                gstr1 is not None
                and gstr1.status == GSTReturnSnapshotStatus.FINALIZED
                and gstr3b is not None
                and gstr3b.status == GSTReturnSnapshotStatus.FINALIZED
            )
            period.status = (
                GSTReturnPeriodStatus.FINALIZED if both_finalized else GSTReturnPeriodStatus.UNDER_REVIEW
            )
        elif period.status == GSTReturnPeriodStatus.OPEN:
            period.status = GSTReturnPeriodStatus.UNDER_REVIEW
        await self.db.flush()

    async def submit_for_review(
        self, company_id, return_period_id, return_type, current_user, meta
    ) -> GSTReturnSnapshot:
        return await self._transition(
            company_id, return_period_id, return_type, "submit", current_user, meta, None
        )

    async def approve(
        self, company_id, return_period_id, return_type, current_user, meta, comment=None
    ) -> GSTReturnSnapshot:
        return await self._transition(
            company_id, return_period_id, return_type, "approve", current_user, meta, comment
        )

    async def request_changes(
        self, company_id, return_period_id, return_type, current_user, meta, comment=None
    ) -> GSTReturnSnapshot:
        return await self._transition(
            company_id, return_period_id, return_type, "request_changes", current_user, meta, comment
        )

    async def finalize(
        self, company_id, return_period_id, return_type, current_user, meta
    ) -> GSTReturnSnapshot:
        return await self._transition(
            company_id, return_period_id, return_type, "finalize", current_user, meta, None
        )
