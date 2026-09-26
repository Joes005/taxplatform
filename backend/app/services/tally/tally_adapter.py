from datetime import date, datetime, timezone
from decimal import Decimal
import io
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationAppError
from app.models.accounting_enums import ImportStatus, ImportType
from app.models.import_job import ImportError as ImportErrorModel, ImportJob, ImportRow, ImportRowStatus
from app.models.user import User
from app.repositories.import_job_repository import ImportJobRepository
from app.services.auth_service import RequestMeta
from app.services.tally.tally_detector import FileInspectionResult, detect_tally_format
from app.services.tally.tally_importer import TallyImporter
from app.services.tally.tally_mapper import TallyMapper, TallyMappingTemplateService
from app.services.tally.tally_models import (
    MappingStatus,
    TallyFormat,
    TallyImportBatch,
    TallyMappingRule,
    TallyReconciliationReport,
    ValidationSeverity,
)
from app.services.tally.tally_tabular_parser import TallyTabularParser
from app.services.tally.tally_validator import TallyValidationResult, TallyValidator
from app.services.tally.tally_xml_parser import TallyXMLParser


class TallyImportAdapter:
    """Unified adapter coordinating detection, parsing, mapping, validation,
    preview, and commit for all Tally export formats (XML, CSV, XLSX)."""

    def __init__(self, db: AsyncSession, company_id: uuid.UUID) -> None:
        self.db = db
        self.company_id = company_id
        self.repo = ImportJobRepository(db)
        self.validator = TallyValidator(db, company_id)
        self.mapper = TallyMapper(db, company_id)
        self.importer = TallyImporter(db, company_id)
        self.template_service = TallyMappingTemplateService(db)

    def detect(self, content: bytes, filename: str = "", mime_type: str | None = None) -> FileInspectionResult:
        return detect_tally_format(content, filename=filename, mime_type=mime_type)

    def parse_to_canonical(self, content: bytes, inspection: FileInspectionResult) -> TallyImportBatch:
        """Parses raw content bytes into intermediate canonical TallyImportBatch."""
        if not inspection.is_valid:
            raise ValidationAppError(
                inspection.error_message or "Unsupported or invalid file format",
                code="INVALID_IMPORT_FILE",
            )

        if inspection.format == TallyFormat.TALLY_XML or inspection.format == TallyFormat.XML:
            parser = TallyXMLParser(str(self.company_id))
            return parser.parse(content)
        elif inspection.format == TallyFormat.CSV:
            parser = TallyTabularParser(str(self.company_id))
            return parser.parse_csv(content)
        elif inspection.format == TallyFormat.XLSX:
            parser = TallyTabularParser(str(self.company_id))
            return parser.parse_xlsx(content)
        else:
            raise ValidationAppError(
                f"Unsupported format {inspection.format.value}", code="UNSUPPORTED_FORMAT"
            )

    async def preview_and_stage(
        self,
        content: bytes,
        filename: str,
        document_id: uuid.UUID,
        financial_year_id: uuid.UUID | None,
        current_user: User,
        meta: RequestMeta,
        template_id: uuid.UUID | None = None,
        manual_mappings: dict[str, str] | None = None,
    ) -> tuple[ImportJob, TallyImportBatch, list[TallyMappingRule], TallyValidationResult]:
        """Full ingestion flow:
        Detection -> Parsing -> Normalization -> Mapping -> Validation -> Stage ImportJob + Rows."""

        # 1. Detection
        inspection = self.detect(content, filename=filename)
        if not inspection.is_valid:
            raise ValidationAppError(
                inspection.error_message or "Invalid file format", code="INVALID_FILE"
            )

        # 2. Parse to Canonical
        batch = self.parse_to_canonical(content, inspection)
        if batch.raw_record_count == 0 and len(batch.vouchers) == 0 and len(batch.ledgers) == 0:
            raise ValidationAppError("The import file contains no recognizable accounting records", code="EMPTY_IMPORT_FILE")

        # 3. Mapping
        template_rules = None
        if template_id:
            tpl = await self.template_service.get_template(self.company_id, template_id)
            if tpl:
                template_rules = tpl.rules

        mapping_rules = await self.mapper.map_batch(
            batch,
            template_rules=template_rules,
            manual_mappings=manual_mappings,
        )

        # 4. Validation & Duplicate Detection
        validation_result = await self.validator.validate_batch(batch)

        # 5. Create or stage ImportJob in DB
        job = ImportJob(
            company_id=self.company_id,
            document_id=document_id,
            financial_year_id=financial_year_id,
            import_type=ImportType.TALLY,
            status=ImportStatus.READY if validation_result.is_valid_to_commit else ImportStatus.VALIDATING,
            total_rows=len(batch.vouchers) if batch.vouchers else len(batch.ledgers),
            successful_rows=validation_result.valid_vouchers_count,
            failed_rows=validation_result.invalid_vouchers_count,
            duplicate_rows=len(validation_result.duplicate_vouchers),
            created_by=current_user.id,
            column_mapping={"format": inspection.format.value, "detected_encoding": inspection.detected_encoding},
        )
        await self.repo.create(job)

        # 6. Stage rows in import_rows table for preview
        for idx, voucher in enumerate(batch.vouchers, start=1):
            is_dup = (
                voucher.fingerprint in validation_result.duplicate_fingerprints
                or voucher.voucher_number in validation_result.duplicate_vouchers
            )
            has_error = any(e.row_ref == idx and e.severity == ValidationSeverity.ERROR for e in validation_result.errors)

            if is_dup:
                row_status = ImportRowStatus.DUPLICATE
            elif has_error:
                row_status = ImportRowStatus.ERROR
            else:
                row_status = ImportRowStatus.VALID

            raw_dict = {
                "voucher_type": voucher.voucher_type,
                "voucher_number": voucher.voucher_number,
                "voucher_date": voucher.voucher_date.isoformat(),
                "party_name": voucher.party_name or "",
                "total_amount": float(voucher.total_amount),
                "narration": voucher.narration or "",
            }

            norm_dict = {
                "normalized_type": voucher.normalized_type.value,
                "voucher_number": voucher.voucher_number,
                "voucher_date": voucher.voucher_date.isoformat(),
                "party_name": voucher.party_name or "",
                "total_amount": float(voucher.total_amount),
                "fingerprint": voucher.fingerprint,
                "lines_count": len(voucher.lines),
                "is_duplicate": is_dup,
            }

            row = ImportRow(
                import_job_id=job.id,
                row_number=idx,
                raw_data=raw_dict,
                normalized_data=norm_dict,
                status=row_status,
            )
            await self.repo.add_row(row)

        # Stage validation errors in import_errors table
        for err in validation_result.errors + validation_result.warnings + validation_result.reviews_required:
            row_num = int(err.row_ref) if isinstance(err.row_ref, int) else 0
            await self.repo.add_error(
                ImportErrorModel(
                    import_job_id=job.id,
                    row_number=row_num,
                    field_name=err.field,
                    error_code=err.code,
                    error_message=err.message,
                    raw_value=str(err.extra) if err.extra else None,
                )
            )

        await self.db.flush()
        await self.db.refresh(job)

        return job, batch, mapping_rules, validation_result

    async def commit_job(
        self,
        job_id: uuid.UUID,
        batch: TallyImportBatch,
        rules: list[TallyMappingRule],
        validation: TallyValidationResult,
        financial_year_id: uuid.UUID | None,
        current_user: User,
        meta: RequestMeta,
    ) -> tuple[ImportJob, TallyReconciliationReport]:
        """Commits staged Tally import with rollback safety, updating job status and reconciliation."""
        job = await self.repo.get_by_id_for_company(job_id, self.company_id)
        if not job:
            raise ValidationAppError("Import job not found", code="JOB_NOT_FOUND")

        if job.status == ImportStatus.COMPLETED:
            raise ConflictError("Import job is already committed", code="JOB_ALREADY_COMMITTED")

        # Atomic commit
        recon_report = await self.importer.commit_batch(
            batch=batch,
            rules=rules,
            validation=validation,
            financial_year_id=financial_year_id,
            current_user=current_user,
            meta=meta,
            job_id=job.id,
        )

        # Update rows status to COMMITTED
        rows = await self.repo.list_all_rows(job.id)
        for r in rows:
            if r.status == ImportRowStatus.VALID:
                r.status = ImportRowStatus.COMMITTED

        job.successful_rows = sum(item.imported_count for item in recon_report.items)
        job.duplicate_rows = len(validation.duplicate_vouchers)
        job.failed_rows = len(validation.errors)
        job.status = ImportStatus.COMPLETED if recon_report.overall_matched else ImportStatus.COMPLETED_WITH_ERRORS
        job.completed_at = datetime.now(timezone.utc)
        job.reconciliation = recon_report.model_dump(mode="json")

        await self.db.flush()
        await self.db.refresh(job)

        return job, recon_report
