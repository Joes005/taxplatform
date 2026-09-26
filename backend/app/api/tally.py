import csv
import io
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Response, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_membership,
    get_current_user,
    get_request_meta,
    require_permission,
)
from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationAppError
from app.core.permissions import PermissionCode
from app.models.membership import CompanyMembership
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.schemas.common import SuccessResponse
from app.schemas.tally import (
    TallyCommitRequest,
    TallyCommitResponse,
    TallyDetectResponse,
    TallyExportPreviewResponse,
    TallyExportRequest,
    TallyMappingTemplateCreate,
    TallyMappingTemplateRead,
    TallyMappingTemplateUpdate,
    TallyPreviewRequest,
    TallyPreviewResponse,
    TallyRowPreview,
)
from app.services.auth_service import RequestMeta
from app.services.document_service import DocumentService
from app.services.tally.tally_adapter import TallyImportAdapter
from app.services.tally.tally_exporter import TallyExporter
from app.services.tally.tally_mapper import TallyMappingTemplateService
from app.services.tally.tally_models import TallyReconciliationReport
from app.storage import StorageProvider, get_storage_provider

router = APIRouter(prefix="/tally", tags=["tally"])


async def _check_tally_permission(
    db: AsyncSession,
    current_user: User,
    membership: CompanyMembership | None,
    allowed_codes: list[str],
) -> None:
    if current_user.is_platform_super_admin:
        return
    if membership is None:
        raise PermissionDeniedError("Company membership required")
    codes = await RoleRepository(db).get_permission_codes_for_role(membership.role_id)
    if not any(code in codes for code in allowed_codes):
        raise PermissionDeniedError(
            f"You do not have permission to perform this action. Required one of: {allowed_codes}"
        )


@router.post("/detect", response_model=SuccessResponse[TallyDetectResponse])
async def detect_file_format(
    company_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: CompanyMembership | None = Depends(get_current_membership),
):
    """Detects format, encoding, and Tally markers from uploaded file bytes."""
    await _check_tally_permission(
        db, current_user, membership,
        [PermissionCode.TALLY_IMPORT_CREATE.value, PermissionCode.ACCOUNTING_IMPORT.value]
    )
    content = await file.read()
    adapter = TallyImportAdapter(db, company_id)
    res = adapter.detect(content, filename=file.filename or "", mime_type=file.content_type)
    return SuccessResponse(
        data=TallyDetectResponse(
            format=res.format,
            detected_encoding=res.detected_encoding,
            file_size=res.file_size,
            is_valid=res.is_valid,
            error_message=res.error_message,
            has_tally_markers=res.has_tally_markers,
        )
    )


@router.post("/preview", response_model=SuccessResponse[TallyPreviewResponse])
async def preview_tally_import(
    company_id: uuid.UUID,
    payload: TallyPreviewRequest,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    membership: CompanyMembership | None = Depends(get_current_membership),
):
    """Ingests, parses, normalizes, maps, and validates a Tally import without committing."""
    await _check_tally_permission(
        db, current_user, membership,
        [PermissionCode.TALLY_IMPORT_CREATE.value, PermissionCode.ACCOUNTING_IMPORT.value]
    )

    doc_service = DocumentService(db, storage)
    document = await doc_service.get_document(company_id=company_id, document_id=payload.document_id)
    content = await storage.get(document.storage_path)

    adapter = TallyImportAdapter(db, company_id)
    job, batch, mapping_rules, val_result = await adapter.preview_and_stage(
        content=content,
        filename=document.original_filename,
        document_id=document.id,
        financial_year_id=payload.financial_year_id,
        current_user=current_user,
        meta=meta,
        template_id=payload.template_id,
        manual_mappings=payload.manual_mappings,
    )
    await db.commit()

    # Build row previews
    row_previews = []
    for idx, v in enumerate(batch.vouchers[:100], start=1):
        is_dup = (
            v.fingerprint in val_result.duplicate_fingerprints
            or v.voucher_number in val_result.duplicate_vouchers
        )
        row_previews.append(
            TallyRowPreview(
                row_number=idx,
                voucher_type=v.voucher_type,
                voucher_number=v.voucher_number,
                voucher_date=v.voucher_date.isoformat(),
                party_name=v.party_name or "",
                total_amount=float(v.total_amount),
                status="DUPLICATE" if is_dup else "VALID",
                is_duplicate=is_dup,
                narration=v.narration,
            )
        )

    all_errors = val_result.errors + val_result.warnings + val_result.reviews_required

    return SuccessResponse(
        data=TallyPreviewResponse(
            job_id=job.id,
            format=batch.detected_format.value,
            total_records=len(batch.vouchers),
            valid_records=val_result.valid_vouchers_count,
            invalid_records=val_result.invalid_vouchers_count,
            duplicate_records=len(val_result.duplicate_vouchers),
            warnings_count=len(val_result.warnings),
            review_required_count=len(val_result.reviews_required),
            can_commit=val_result.is_valid_to_commit,
            mappings=mapping_rules,
            errors=all_errors,
            rows=row_previews,
        )
    )


@router.post("/commit", response_model=SuccessResponse[TallyCommitResponse])
async def commit_tally_import(
    company_id: uuid.UUID,
    payload: TallyCommitRequest,
    db: AsyncSession = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    membership: CompanyMembership | None = Depends(get_current_membership),
):
    """Commits validated Tally import into accounting system with rollback safety and reconciliation."""
    await _check_tally_permission(
        db, current_user, membership,
        [PermissionCode.TALLY_IMPORT_COMMIT.value, PermissionCode.ACCOUNTING_IMPORT_COMMIT.value]
    )

    adapter = TallyImportAdapter(db, company_id)
    job = await adapter.repo.get_by_id_for_company(payload.job_id, company_id)
    if not job:
        raise NotFoundError("Import job not found", code="IMPORT_JOB_NOT_FOUND")

    doc_service = DocumentService(db, storage)
    document = await doc_service.get_document(company_id=company_id, document_id=job.document_id)
    content = await storage.get(document.storage_path)

    inspection = adapter.detect(content, filename=document.original_filename)
    batch = adapter.parse_to_canonical(content, inspection)

    # Save as template if requested
    confirmed_rules = payload.confirmed_mappings or []
    if payload.save_as_template_name and confirmed_rules:
        template_service = TallyMappingTemplateService(db)
        tpl_rules = {
            "ledgers": [r.model_dump() for r in confirmed_rules if r.source_type == "LEDGER"],
            "parties": [r.model_dump() for r in confirmed_rules if r.source_type == "PARTY"],
        }
        await template_service.create_template(
            company_id=company_id,
            name=payload.save_as_template_name,
            rules=tpl_rules,
            created_by=current_user.id,
        )

    val_result = await adapter.validator.validate_batch(batch)

    job, recon_report = await adapter.commit_job(
        job_id=payload.job_id,
        batch=batch,
        rules=confirmed_rules,
        validation=val_result,
        financial_year_id=payload.financial_year_id or job.financial_year_id,
        current_user=current_user,
        meta=meta,
    )
    await db.commit()

    return SuccessResponse(
        data=TallyCommitResponse(
            job_id=job.id,
            status=job.status.value,
            reconciliation=recon_report,
            message="Tally data successfully committed and reconciled",
        )
    )


@router.get("/reconciliation/{job_id}", response_model=SuccessResponse[TallyReconciliationReport])
async def get_import_reconciliation(
    job_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: CompanyMembership | None = Depends(get_current_membership),
):
    """Retrieves reconciliation report for a completed Tally import job."""
    await _check_tally_permission(
        db, current_user, membership,
        [PermissionCode.TALLY_IMPORT_VIEW.value, PermissionCode.ACCOUNTING_IMPORT_VIEW.value]
    )
    adapter = TallyImportAdapter(db, company_id)
    job = await adapter.repo.get_by_id_for_company(job_id, company_id)
    if not job:
        raise NotFoundError("Import job not found", code="IMPORT_JOB_NOT_FOUND")

    if not job.reconciliation:
        raise NotFoundError("Reconciliation report not found for this import", code="RECONCILIATION_NOT_FOUND")

    return SuccessResponse(data=TallyReconciliationReport.model_validate(job.reconciliation))


@router.get("/errors/{job_id}/csv")
async def download_import_errors_csv(
    job_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: CompanyMembership | None = Depends(get_current_membership),
):
    """Downloads CSV report of import validation errors and warnings."""
    await _check_tally_permission(
        db, current_user, membership,
        [PermissionCode.TALLY_IMPORT_VIEW.value, PermissionCode.ACCOUNTING_IMPORT_VIEW.value]
    )
    adapter = TallyImportAdapter(db, company_id)
    job = await adapter.repo.get_by_id_for_company(job_id, company_id)
    if not job:
        raise NotFoundError("Import job not found", code="IMPORT_JOB_NOT_FOUND")

    errors, _ = await adapter.repo.list_errors(job_id, offset=0, limit=5000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Row Number", "Field", "Error Code", "Error Message", "Raw Value"])
    for e in errors:
        writer.writerow([e.row_number, e.field_name or "", e.error_code, e.error_message, e.raw_value or ""])

    csv_data = output.getvalue().encode("utf-8")
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tally_import_errors_{job_id}.csv"},
    )


# --- Mapping Templates Endpoints ---

@router.get("/templates", response_model=SuccessResponse[list[TallyMappingTemplateRead]])
async def list_mapping_templates(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: CompanyMembership | None = Depends(get_current_membership),
):
    """Lists company-scoped mapping templates."""
    await _check_tally_permission(
        db, current_user, membership,
        [PermissionCode.TALLY_MAPPING_MANAGE.value, PermissionCode.ACCOUNTING_IMPORT.value]
    )
    svc = TallyMappingTemplateService(db)
    templates = await svc.list_templates(company_id)
    return SuccessResponse(data=[TallyMappingTemplateRead.model_validate(t) for t in templates])


@router.post("/templates", response_model=SuccessResponse[TallyMappingTemplateRead], status_code=201)
async def create_mapping_template(
    company_id: uuid.UUID,
    payload: TallyMappingTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: CompanyMembership | None = Depends(get_current_membership),
):
    """Creates a new company-scoped mapping template."""
    await _check_tally_permission(
        db, current_user, membership,
        [PermissionCode.TALLY_MAPPING_MANAGE.value, PermissionCode.ACCOUNTING_IMPORT.value]
    )
    svc = TallyMappingTemplateService(db)
    tpl = await svc.create_template(
        company_id=company_id,
        name=payload.name,
        rules=payload.rules,
        created_by=current_user.id,
    )
    await db.commit()
    return SuccessResponse(data=TallyMappingTemplateRead.model_validate(tpl))


@router.get("/templates/{template_id}", response_model=SuccessResponse[TallyMappingTemplateRead])
async def get_mapping_template(
    template_id: uuid.UUID,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: CompanyMembership | None = Depends(get_current_membership),
):
    await _check_tally_permission(
        db, current_user, membership,
        [PermissionCode.TALLY_MAPPING_MANAGE.value, PermissionCode.ACCOUNTING_IMPORT.value]
    )
    svc = TallyMappingTemplateService(db)
    tpl = await svc.get_template(company_id, template_id)
    if not tpl:
        raise NotFoundError("Mapping template not found", code="TEMPLATE_NOT_FOUND")
    return SuccessResponse(data=TallyMappingTemplateRead.model_validate(tpl))


@router.put("/templates/{template_id}", response_model=SuccessResponse[TallyMappingTemplateRead])
async def update_mapping_template(
    template_id: uuid.UUID,
    company_id: uuid.UUID,
    payload: TallyMappingTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: CompanyMembership | None = Depends(get_current_membership),
):
    await _check_tally_permission(
        db, current_user, membership,
        [PermissionCode.TALLY_MAPPING_MANAGE.value, PermissionCode.ACCOUNTING_IMPORT.value]
    )
    svc = TallyMappingTemplateService(db)
    tpl = await svc.update_template(
        company_id=company_id,
        template_id=template_id,
        name=payload.name,
        rules=payload.rules,
    )
    if not tpl:
        raise NotFoundError("Mapping template not found", code="TEMPLATE_NOT_FOUND")
    await db.commit()
    return SuccessResponse(data=TallyMappingTemplateRead.model_validate(tpl))


# --- Tally Export Endpoints ---

@router.post("/export/preview", response_model=SuccessResponse[TallyExportPreviewResponse])
async def preview_tally_export(
    company_id: uuid.UUID,
    payload: TallyExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: CompanyMembership | None = Depends(get_current_membership),
):
    """Previews record counts and total financial amounts for export selection."""
    await _check_tally_permission(
        db, current_user, membership,
        [PermissionCode.TALLY_EXPORT_VIEW.value, PermissionCode.ACCOUNTING_IMPORT_VIEW.value]
    )
    exporter = TallyExporter(db, company_id)
    preview_data = await exporter.get_preview(
        financial_year_id=payload.financial_year_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        voucher_types=payload.voucher_types,
    )
    return SuccessResponse(data=TallyExportPreviewResponse(**preview_data))


@router.post("/export")
async def generate_tally_export(
    company_id: uuid.UUID,
    payload: TallyExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    meta: RequestMeta = Depends(get_request_meta),
    membership: CompanyMembership | None = Depends(get_current_membership),
):
    """Generates and downloads Tally-compatible XML, CSV, or Excel file."""
    await _check_tally_permission(
        db, current_user, membership,
        [PermissionCode.TALLY_EXPORT_CREATE.value, PermissionCode.ACCOUNTING_IMPORT.value]
    )
    exporter = TallyExporter(db, company_id)

    fmt = payload.format.upper()
    if fmt == "XML":
        data_bytes = await exporter.export_xml(
            financial_year_id=payload.financial_year_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            voucher_types=payload.voucher_types,
        )
        media_type = "application/xml"
        filename = f"tally_export_{company_id}.xml"
    elif fmt == "CSV":
        data_bytes = await exporter.export_csv(
            financial_year_id=payload.financial_year_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            voucher_types=payload.voucher_types,
        )
        media_type = "text/csv"
        filename = f"tally_export_{company_id}.csv"
    elif fmt in ("XLSX", "EXCEL"):
        data_bytes = await exporter.export_xlsx(
            financial_year_id=payload.financial_year_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            voucher_types=payload.voucher_types,
        )
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"tally_export_{company_id}.xlsx"
    else:
        raise ValidationAppError(f"Unsupported export format: {payload.format}", code="INVALID_FORMAT")

    audit = exporter.db
    # Record audit log
    from app.services.audit_service import AuditAction, AuditService
    await AuditService(db).log(
        action=AuditAction.TALLY_EXPORT_GENERATED,
        user_id=current_user.id,
        company_id=company_id,
        resource_type="tally_export",
        resource_id=str(uuid.uuid4()),
        description=f"Generated Tally {fmt} export ({len(data_bytes)} bytes)",
        ip_address=meta.ip_address,
        user_agent=meta.user_agent,
    )
    await db.commit()

    return Response(
        content=data_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
