import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_request_meta, require_permission
from app.core.permissions import PermissionCode
from app.models.accounting_enums import ImportType
from app.models.user import User
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.import_job import (
    FieldDefinitionRead,
    ImportErrorRead,
    ImportJobCreate,
    ImportJobRead,
    ImportRowRead,
)
from app.services.auth_service import RequestMeta
from app.services.document_service import DocumentService
from app.services.import_service import ImportService
from app.services.imports.field_definitions import get_field_definitions
from app.storage import StorageProvider, get_storage_provider

router = APIRouter(prefix="/accounting/imports", tags=["accounting-imports"])


@router.get("/fields", response_model=SuccessResponse[list[FieldDefinitionRead]])
async def get_import_fields(
    import_type: ImportType,
    _current_user: User = Depends(get_current_user),
):
    """Drives the column-mapping wizard step (§39): the target fields this
    import type accepts, and which are required."""
    fields = get_field_definitions(import_type)
    return SuccessResponse(
        data=[FieldDefinitionRead(name=f.name, label=f.label, required=f.required) for f in fields]
    )


@router.post("", response_model=SuccessResponse[ImportJobRead], status_code=201)
async def create_import_job(
    company_id: uuid.UUID,
    payload: ImportJobCreate,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_IMPORT.value)),
):
    document = await DocumentService(db, storage).get_document(
        company_id=company_id, document_id=payload.document_id
    )
    service = ImportService(db, storage)
    job = await service.create_job(
        company_id,
        document=document,
        import_type=payload.import_type,
        financial_year_id=payload.financial_year_id,
        column_mapping=payload.column_mapping,
        current_user=current_user,
        meta=meta,
    )
    await db.commit()
    return SuccessResponse(data=ImportJobRead.model_validate(job), message="Import parsed and staged")


@router.get("", response_model=SuccessResponse[PaginatedData[ImportJobRead]])
async def list_import_jobs(
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_IMPORT_VIEW.value)),
):
    service = ImportService(db, storage)
    items, total = await service.list_jobs(company_id, page=page, page_size=page_size)
    data = PaginatedData(
        items=[ImportJobRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{job_id}", response_model=SuccessResponse[ImportJobRead])
async def get_import_job(
    job_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_IMPORT_VIEW.value)),
):
    service = ImportService(db, storage)
    job = await service.get(company_id, job_id)
    return SuccessResponse(data=ImportJobRead.model_validate(job))


@router.get("/{job_id}/preview", response_model=SuccessResponse[PaginatedData[ImportRowRead]])
async def preview_import_job(
    job_id: uuid.UUID,
    company_id: uuid.UUID,
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_IMPORT_VIEW.value)),
):
    service = ImportService(db, storage)
    items, total = await service.preview(
        company_id, job_id, status=status, page=page, page_size=page_size
    )
    data = PaginatedData(
        items=[ImportRowRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.get("/{job_id}/errors", response_model=SuccessResponse[PaginatedData[ImportErrorRead]])
async def list_import_errors(
    job_id: uuid.UUID,
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_IMPORT_VIEW.value)),
):
    service = ImportService(db, storage)
    items, total = await service.errors(company_id, job_id, page=page, page_size=page_size)
    data = PaginatedData(
        items=[ImportErrorRead.model_validate(i) for i in items],
        pagination=build_pagination_meta(page=page, page_size=page_size, total=total),
    )
    return SuccessResponse(data=data)


@router.post("/{job_id}/commit", response_model=SuccessResponse[ImportJobRead])
async def commit_import_job(
    job_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_IMPORT_COMMIT.value)),
):
    service = ImportService(db, storage)
    job = await service.commit(company_id, job_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ImportJobRead.model_validate(job), message="Import committed")


@router.post("/{job_id}/cancel", response_model=SuccessResponse[ImportJobRead])
async def cancel_import_job(
    job_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_IMPORT.value)),
):
    service = ImportService(db, storage)
    job = await service.cancel(company_id, job_id, current_user, meta)
    await db.commit()
    return SuccessResponse(data=ImportJobRead.model_validate(job), message="Import cancelled")
