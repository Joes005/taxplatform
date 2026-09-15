import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.credit_note import CreditNoteCreate, CreditNoteRead
from app.services.auth_service import RequestMeta
from app.services.credit_note_service import CreditNoteService

router = APIRouter(prefix="/accounting/credit-notes", tags=["accounting-credit-notes"])


@router.post("", response_model=SuccessResponse[CreditNoteRead], status_code=201)
async def create_credit_note(
    company_id: uuid.UUID,
    payload: CreditNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_CREATE.value)),
):
    service = CreditNoteService(db)
    note = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=CreditNoteRead.model_validate(note), message="Credit note created")


@router.get("", response_model=SuccessResponse[PaginatedData[CreditNoteRead]])
async def list_credit_notes(
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_VIEW.value)),
):
    service = CreditNoteService(db)
    items, total = await service.list(company_id, page=page, page_size=page_size)
    data = PaginatedData(
        items=[CreditNoteRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{note_id}", response_model=SuccessResponse[CreditNoteRead])
async def get_credit_note(
    note_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_VIEW.value)),
):
    service = CreditNoteService(db)
    note = await service.get(company_id, note_id)
    return SuccessResponse(data=CreditNoteRead.model_validate(note))
