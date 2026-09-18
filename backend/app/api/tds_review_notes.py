import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.tds_review_note import TDSReviewNoteCreate, TDSReviewNoteRead
from app.services.auth_service import RequestMeta
from app.services.tds_review_note_service import TDSReviewNoteService

router = APIRouter(prefix="/tds/review-notes", tags=["tds-review-notes"])


@router.post("", response_model=SuccessResponse[TDSReviewNoteRead], status_code=201)
async def create_review_note(
    company_id: uuid.UUID,
    payload: TDSReviewNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_RETURN_VIEW.value)),
):
    service = TDSReviewNoteService(db)
    note = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=TDSReviewNoteRead.model_validate(note), message="Review note added")


@router.get("", response_model=SuccessResponse[list[TDSReviewNoteRead]])
async def list_review_notes(
    company_id: uuid.UUID,
    return_period_id: uuid.UUID,
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.TDS_RETURN_VIEW.value)),
):
    service = TDSReviewNoteService(db)
    notes = await service.list(
        company_id, return_period_id, entity_type=entity_type, entity_id=entity_id
    )
    return SuccessResponse(data=[TDSReviewNoteRead.model_validate(n) for n in notes])


@router.post("/{note_id}/resolve", response_model=SuccessResponse[TDSReviewNoteRead])
async def resolve_review_note(
    note_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.TDS_RETURN_VIEW.value)),
):
    service = TDSReviewNoteService(db)
    note = await service.resolve(company_id, note_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=TDSReviewNoteRead.model_validate(note), message="Review note resolved")
