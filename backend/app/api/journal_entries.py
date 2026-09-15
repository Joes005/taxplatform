import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.accounting_enums import TransactionStatus
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.journal_entry import JournalEntryCreate, JournalEntryRead
from app.services.auth_service import RequestMeta
from app.services.journal_entry_service import JournalEntryService

router = APIRouter(prefix="/accounting/journal-entries", tags=["accounting-journal-entries"])


@router.post("", response_model=SuccessResponse[JournalEntryRead], status_code=201)
async def create_journal_entry(
    company_id: uuid.UUID,
    payload: JournalEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.JOURNAL_CREATE.value)),
):
    service = JournalEntryService(db)
    entry = await service.create(company_id, payload, current_user, meta)
    await db.commit()
    return SuccessResponse(data=JournalEntryRead.model_validate(entry), message="Journal entry created")


@router.get("", response_model=SuccessResponse[PaginatedData[JournalEntryRead]])
async def list_journal_entries(
    company_id: uuid.UUID,
    financial_year_id: uuid.UUID | None = Query(default=None),
    status: TransactionStatus | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.JOURNAL_VIEW.value)),
):
    service = JournalEntryService(db)
    items, total = await service.list(
        company_id,
        page=page,
        page_size=page_size,
        financial_year_id=financial_year_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    data = PaginatedData(
        items=[JournalEntryRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{entry_id}", response_model=SuccessResponse[JournalEntryRead])
async def get_journal_entry(
    entry_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _membership=Depends(require_permission(PermissionCode.JOURNAL_VIEW.value)),
):
    service = JournalEntryService(db)
    entry = await service.get(company_id, entry_id)
    return SuccessResponse(data=JournalEntryRead.model_validate(entry))


@router.post("/{entry_id}/post", response_model=SuccessResponse[JournalEntryRead])
async def post_journal_entry(
    entry_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.JOURNAL_POST.value)),
):
    service = JournalEntryService(db)
    entry = await service.post(company_id, entry_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=JournalEntryRead.model_validate(entry), message="Journal entry posted")
