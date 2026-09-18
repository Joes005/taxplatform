import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.tds_review_note import TDSReviewNote
from app.models.tds_enums import TDSReviewNoteStatus
from app.models.user import User
from app.repositories.tds_review_note_repository import TDSReviewNoteRepository
from app.schemas.tds_review_note import TDSReviewNoteCreate
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta


class TDSReviewNoteService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TDSReviewNoteRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, company_id: uuid.UUID, payload: TDSReviewNoteCreate, current_user: User, meta: RequestMeta
    ) -> TDSReviewNote:
        note = TDSReviewNote(
            company_id=company_id,
            return_period_id=payload.return_period_id,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            note=payload.note,
            created_by=current_user.id,
        )
        await self.repo.create(note)

        await self.audit.log(
            action=AuditAction.TDS_REVIEW_CREATED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_review_note",
            resource_id=str(note.id),
            description=f"Review note added on {payload.entity_type} {payload.entity_id}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return note

    async def list(
        self,
        company_id: uuid.UUID,
        return_period_id: uuid.UUID,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> list[TDSReviewNote]:
        return await self.repo.list_for_period(
            company_id, return_period_id, entity_type=entity_type, entity_id=entity_id
        )

    async def resolve(
        self, company_id: uuid.UUID, note_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> TDSReviewNote:
        note = await self.repo.get_by_id_for_company(note_id, company_id)
        if note is None:
            raise NotFoundError("Review note not found", code="TDS_REVIEW_NOTE_NOT_FOUND")
        if note.status == TDSReviewNoteStatus.RESOLVED:
            raise ConflictError("Review note is already resolved", code="TDS_REVIEW_NOTE_ALREADY_RESOLVED")

        note.status = TDSReviewNoteStatus.RESOLVED
        await self.db.flush()
        await self.db.refresh(note)

        await self.audit.log(
            action=AuditAction.TDS_REVIEW_RESOLVED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="tds_review_note",
            resource_id=str(note.id),
            description="Review note resolved",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return note
