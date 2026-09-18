"""Return-level review workflow for TDS — the TDS analogue of
`GSTReturnSnapshotService` (PHASE5 sections 24-26, 37). Generating a
return preparation snapshots the current quarterly numbers so a later
edit to a TDS transaction can never silently change something already
under review or finalized; the next `generate` call produces a new
version instead. A FINALIZED snapshot is immutable — no transition
accepts it as a starting state.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError, NotFoundError
from app.models.tds_enums import TDSReturnPeriodStatus, TDSReturnSnapshotStatus, TDSReturnType
from app.models.tds_return_snapshot import TDSReturnSnapshot
from app.models.user import User
from app.repositories.tds_return_period_repository import TDSReturnPeriodRepository
from app.repositories.tds_return_snapshot_repository import TDSReturnSnapshotRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.tds_return_service import TDSReturnService

_TRANSITIONS: dict[tuple[TDSReturnSnapshotStatus, str], TDSReturnSnapshotStatus] = {
    (TDSReturnSnapshotStatus.DRAFT, "submit"): TDSReturnSnapshotStatus.UNDER_REVIEW,
    (TDSReturnSnapshotStatus.UNDER_REVIEW, "approve"): TDSReturnSnapshotStatus.APPROVED,
    (TDSReturnSnapshotStatus.UNDER_REVIEW, "request_changes"): TDSReturnSnapshotStatus.CHANGES_REQUESTED,
    (TDSReturnSnapshotStatus.APPROVED, "finalize"): TDSReturnSnapshotStatus.FINALIZED,
}

_AUDIT_ACTION_BY_ACTION = {
    "submit": AuditAction.TDS_RETURN_VALIDATED,
    "approve": AuditAction.TDS_RETURN_APPROVED,
    "request_changes": AuditAction.TDS_RETURN_CHANGES_REQUESTED,
    "finalize": AuditAction.TDS_RETURN_FINALIZED,
}

_PERIOD_STATUS_BY_SNAPSHOT_STATUS = {
    TDSReturnSnapshotStatus.UNDER_REVIEW: TDSReturnPeriodStatus.UNDER_REVIEW,
    TDSReturnSnapshotStatus.APPROVED: TDSReturnPeriodStatus.APPROVED,
    TDSReturnSnapshotStatus.FINALIZED: TDSReturnPeriodStatus.FINALIZED,
}


class TDSReturnSnapshotService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TDSReturnSnapshotRepository(db)
        self.period_repo = TDSReturnPeriodRepository(db)
        self.return_service = TDSReturnService(db)
        self.audit = AuditService(db)

    async def generate(
        self,
        company_id: uuid.UUID,
        return_period_id: uuid.UUID,
        return_type: TDSReturnType,
        current_user: User,
        meta: RequestMeta,
    ) -> TDSReturnSnapshot:
        period = await self.period_repo.get_by_id_for_company(return_period_id, company_id)
        if period is None:
            raise NotFoundError("TDS return period not found", code="TDS_RETURN_PERIOD_NOT_FOUND")

        summary = await self.return_service.generate_summary(period)

        latest = await self.repo.get_latest(company_id, return_period_id, return_type)
        next_version = (latest.version + 1) if latest else 1

        snapshot = TDSReturnSnapshot(
            company_id=company_id,
            return_period_id=return_period_id,
            return_type=return_type,
            version=next_version,
            status=TDSReturnSnapshotStatus.DRAFT,
            generated_at=datetime.now(timezone.utc),
            generated_by=current_user.id,
            summary_data=summary.model_dump(mode="json"),
        )
        await self.repo.create(snapshot)

        await self.audit.log(
            action=AuditAction.TDS_RETURN_GENERATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_return_snapshot",
            resource_id=str(snapshot.id),
            description=f"{return_type.value} version {next_version} generated for TDS return period "
            f"{return_period_id}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return snapshot

    async def get_latest(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID, return_type: TDSReturnType
    ) -> TDSReturnSnapshot:
        snapshot = await self.repo.get_latest(company_id, return_period_id, return_type)
        if snapshot is None:
            raise NotFoundError(
                f"No {return_type.value} has been generated for this return period yet",
                code="TDS_RETURN_SNAPSHOT_NOT_FOUND",
            )
        return snapshot

    async def list_versions(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID, return_type: TDSReturnType
    ) -> list[TDSReturnSnapshot]:
        return await self.repo.list_versions(company_id, return_period_id, return_type)

    async def _transition(
        self,
        company_id: uuid.UUID,
        return_period_id: uuid.UUID,
        return_type: TDSReturnType,
        action: str,
        current_user: User,
        meta: RequestMeta,
        comment: str | None,
    ) -> TDSReturnSnapshot:
        snapshot = await self.get_latest(company_id, return_period_id, return_type)
        key = (snapshot.status, action)
        if key not in _TRANSITIONS:
            raise InvalidStateError(
                f"Cannot {action.replace('_', ' ')} a {return_type.value} snapshot in status "
                f"{snapshot.status.value}",
                code="INVALID_TDS_SNAPSHOT_TRANSITION",
            )

        snapshot.status = _TRANSITIONS[key]
        await self.db.flush()
        await self.db.refresh(snapshot)

        await self._sync_period_status(company_id, return_period_id, snapshot.status)

        await self.audit.log(
            action=_AUDIT_ACTION_BY_ACTION[action],
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_return_snapshot",
            resource_id=str(snapshot.id),
            description=f"{return_type.value} version {snapshot.version} moved to {snapshot.status.value}",
            metadata={"comment": comment} if comment else None,
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return snapshot

    async def _sync_period_status(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID, snapshot_status: TDSReturnSnapshotStatus
    ) -> None:
        period = await self.period_repo.get_by_id_for_company(return_period_id, company_id)
        if period is None or period.status == TDSReturnPeriodStatus.ARCHIVED:
            return

        new_status = _PERIOD_STATUS_BY_SNAPSHOT_STATUS.get(snapshot_status)
        if new_status is not None:
            period.status = new_status
            await self.db.flush()

    async def submit_for_review(
        self, company_id, return_period_id, return_type, current_user, meta
    ) -> TDSReturnSnapshot:
        return await self._transition(
            company_id, return_period_id, return_type, "submit", current_user, meta, None
        )

    async def approve(
        self, company_id, return_period_id, return_type, current_user, meta, comment=None
    ) -> TDSReturnSnapshot:
        return await self._transition(
            company_id, return_period_id, return_type, "approve", current_user, meta, comment
        )

    async def request_changes(
        self, company_id, return_period_id, return_type, current_user, meta, comment=None
    ) -> TDSReturnSnapshot:
        return await self._transition(
            company_id, return_period_id, return_type, "request_changes", current_user, meta, comment
        )

    async def finalize(
        self, company_id, return_period_id, return_type, current_user, meta
    ) -> TDSReturnSnapshot:
        return await self._transition(
            company_id, return_period_id, return_type, "finalize", current_user, meta, None
        )
