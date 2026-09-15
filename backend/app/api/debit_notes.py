import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.debit_note import DebitNoteCreate, DebitNoteRead
from app.services.auth_service import RequestMeta
from app.services.debit_note_service import DebitNoteService

router = APIRouter(prefix="/accounting/debit-notes", tags=["accounting-debit-notes"])


@router.post("", response_model=SuccessResponse[DebitNoteRead], status_code=201)
async def create_debit_note(
    company_id: uuid.UUID,
    payload: DebitNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_CREATE.value)),
):
    service = DebitNoteService(db)
    note = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=DebitNoteRead.model_validate(note), message="Debit note created")


@router.get("", response_model=SuccessResponse[PaginatedData[DebitNoteRead]])
async def list_debit_notes(
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_VIEW.value)),
):
    service = DebitNoteService(db)
    items, total = await service.list(company_id, page=page, page_size=page_size)
    data = PaginatedData(
        items=[DebitNoteRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{note_id}", response_model=SuccessResponse[DebitNoteRead])
async def get_debit_note(
    note_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_VIEW.value)),
):
    service = DebitNoteService(db)
    note = await service.get(company_id, note_id)
    return SuccessResponse(data=DebitNoteRead.model_validate(note))
