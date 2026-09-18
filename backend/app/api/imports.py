import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_membership, get_current_user, get_request_meta, require_permission
from app.core.exceptions import PermissionDeniedError
from app.core.permissions import PermissionCode
from app.models.accounting_enums import ImportType
from app.models.membership import CompanyMembership
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.schemas.common import PaginatedData, SuccessResponse, build_pagination_meta
from app.schemas.import_job import (
    FieldDefinitionRead,
    ImportColumnPreview,
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


async def _ensure_permission(
    db: AsyncSession,
    current_user: User,
    membership: CompanyMembership | None,
    code: PermissionCode,
) -> None:
    """The generic import endpoints below gate on ACCOUNTING_IMPORT* for
    every import_type. GSTR-2B additionally requires the GST-specific
    permission (PHASE4 section 59) — checked here, after the request body
    (for create) or the fetched job (for commit) reveals the import_type,
    rather than duplicating this whole router per GST import type."""
    if current_user.is_platform_super_admin:
        return
    assert membership is not None
    codes = await RoleRepository(db).get_permission_codes_for_role(membership.role_id)
    if code.value not in codes:
        raise PermissionDeniedError(
            f"You do not have permission to perform this action ({code.value})"
        )


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


@router.get("/preview-columns", response_model=SuccessResponse[ImportColumnPreview])
async def preview_import_columns(
    company_id: uuid.UUID,
    document_id: uuid.UUID,
    import_type: ImportType,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_IMPORT.value)),
):
    """Lets the mapping-wizard step show the file's own column headers (and
    a few sample rows) before the user commits to a column mapping —
    reuses the same adapters as the real parse, so what the user sees here
    always matches what actually gets parsed on create_job.
    """
    document = await DocumentService(db, storage).get_document(
        company_id=company_id, document_id=document_id
    )
    service = ImportService(db, storage)
    columns, sample_rows = await service.preview_columns(document=document, import_type=import_type)
    return SuccessResponse(data=ImportColumnPreview(columns=columns, sample_rows=sample_rows))


@router.post("", response_model=SuccessResponse[ImportJobRead], status_code=201)
async def create_import_job(
    company_id: uuid.UUID,
    payload: ImportJobCreate,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    membership: CompanyMembership | None = Depends(get_current_membership),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_IMPORT.value)),
):
    if payload.import_type == ImportType.GSTR2B:
        await _ensure_permission(db, current_user, membership, PermissionCode.GSTR2B_IMPORT)
    elif payload.import_type == ImportType.TDS:
        await _ensure_permission(db, current_user, membership, PermissionCode.TDS_IMPORT)
    elif payload.import_type == ImportType.BANK_STATEMENT:
        await _ensure_permission(db, current_user, membership, PermissionCode.BANK_STATEMENT_IMPORT)

    document = await DocumentService(db, storage).get_document(
        company_id=company_id, document_id=payload.document_id
    )
    service = ImportService(db, storage)
    job = await service.create_job(
        company_id,
        document=document,
        import_type=payload.import_type,
        financial_year_id=payload.financial_year_id,
        return_period_id=payload.return_period_id,
        bank_statement_id=payload.bank_statement_id,
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
    membership: CompanyMembership | None = Depends(get_current_membership),
    _membership=Depends(require_permission(PermissionCode.ACCOUNTING_IMPORT_COMMIT.value)),
):
    service = ImportService(db, storage)
    existing = await service.get(company_id, job_id)
    if existing.import_type == ImportType.GSTR2B:
        await _ensure_permission(db, current_user, membership, PermissionCode.GSTR2B_IMPORT)
    elif existing.import_type == ImportType.TDS:
        await _ensure_permission(db, current_user, membership, PermissionCode.TDS_IMPORT_COMMIT)
    elif existing.import_type == ImportType.BANK_STATEMENT:
        await _ensure_permission(db, current_user, membership, PermissionCode.BANK_STATEMENT_IMPORT_COMMIT)

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
