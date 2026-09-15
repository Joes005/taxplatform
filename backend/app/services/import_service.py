import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.accounting_enums import (
    DataSource,
    ImportStatus,
    ImportType,
    TransactionStatus,
)
from app.models.customer import Customer
from app.models.import_job import ImportError as ImportErrorModel
from app.models.import_job import ImportJob, ImportRow
from app.models.import_job import ImportRowStatus as RowStatus
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.ledger import Ledger
from app.models.payment import Payment
from app.models.product_service import ProductService
from app.models.purchase_invoice import PurchaseInvoice
from app.models.receipt import Receipt
from app.models.sales_invoice import SalesInvoice
from app.models.user import User
from app.models.vendor import Vendor
from app.repositories.import_job_repository import ImportJobRepository
from app.repositories.purchase_invoice_repository import PurchaseInvoiceRepository
from app.repositories.sales_invoice_repository import SalesInvoiceRepository
from app.services.accounting_calculation_service import round_money
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.imports.adapters import get_adapter
from app.services.imports.column_mapping import apply_mapping, validate_mapping
from app.services.imports.field_definitions import get_field_definitions
from app.services.imports.row_validators import ImportContext, validate_row
from app.storage.base import StorageProvider


class ImportService:
    def __init__(self, db: AsyncSession, storage: StorageProvider) -> None:
        self.db = db
        self.storage = storage
        self.repo = ImportJobRepository(db)
        self.sales_invoices = SalesInvoiceRepository(db)
        self.purchase_invoices = PurchaseInvoiceRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------
    # Upload -> parse -> normalize -> validate -> stage
    # ------------------------------------------------------------------

    async def create_job(
        self,
        company_id: uuid.UUID,
        *,
        document,
        import_type: ImportType,
        financial_year_id: uuid.UUID | None,
        column_mapping: dict[str, str],
        current_user: User,
        meta: RequestMeta,
    ) -> ImportJob:
        fields = get_field_definitions(import_type)
        validate_mapping(column_mapping, fields)

        content = await self.storage.get(document.storage_path)
        adapter = get_adapter(document.file_extension, is_tally=(import_type == ImportType.TALLY))
        raw_rows = adapter.parse(content)

        if not raw_rows:
            raise ValidationAppError("The uploaded file has no data rows", code="EMPTY_IMPORT_FILE")

        job = ImportJob(
            company_id=company_id,
            document_id=document.id,
            financial_year_id=financial_year_id,
            import_type=import_type,
            status=ImportStatus.VALIDATING,
            column_mapping=column_mapping,
            total_rows=len(raw_rows),
            created_by=current_user.id,
        )
        await self.repo.create(job)

        ctx = ImportContext(self.db, company_id)
        await ctx.load()

        successful = 0
        failed = 0
        duplicate = 0
        seen_keys: set[tuple] = set()

        for index, raw_row in enumerate(raw_rows, start=1):
            mapped = apply_mapping(raw_row, column_mapping)
            result = validate_row(import_type, mapped, ctx)

            if not result.is_valid:
                failed += 1
                row = ImportRow(
                    import_job_id=job.id,
                    row_number=index,
                    raw_data={k: str(v) for k, v in raw_row.items()},
                    normalized_data=None,
                    status=RowStatus.ERROR,
                )
                await self.repo.add_row(row)
                for err in result.errors:
                    await self.repo.add_error(
                        ImportErrorModel(
                            import_job_id=job.id,
                            row_number=index,
                            field_name=err.field_name,
                            error_code=err.error_code,
                            error_message=err.error_message,
                            raw_value=str(raw_row.get(err.field_name, ""))[:500]
                            if err.field_name
                            else None,
                        )
                    )
                continue

            dup_key = self._duplicate_key(import_type, result.normalized)
            is_duplicate = dup_key is not None and dup_key in seen_keys
            if not is_duplicate and dup_key is not None:
                is_duplicate = await self._check_existing_duplicate(
                    import_type, company_id, result.normalized
                )

            row_status = RowStatus.VALID
            if is_duplicate:
                duplicate += 1
                row_status = RowStatus.DUPLICATE
                await self.audit.log(
                    action=AuditAction.DUPLICATE_DETECTED,
                    user_id=current_user.id,
                    company_id=company_id,
                    resource_type="import_row",
                    resource_id=f"{job.id}:{index}",
                    description=f"Duplicate row {index} detected during import",
                    ip_address=meta.ip_address,
                    user_agent=meta.user_agent,
                )
            else:
                successful += 1
                if dup_key is not None:
                    seen_keys.add(dup_key)

            row = ImportRow(
                import_job_id=job.id,
                row_number=index,
                raw_data={k: str(v) for k, v in raw_row.items()},
                normalized_data=_json_safe(result.normalized),
                status=row_status,
            )
            await self.repo.add_row(row)

        job.successful_rows = successful
        job.failed_rows = failed
        job.duplicate_rows = duplicate
        job.status = ImportStatus.READY
        await self.db.flush()
        await self.db.refresh(job)

        await self.audit.log(
            action=AuditAction.IMPORT_CREATE,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="import_job",
            resource_id=str(job.id),
            description=f"Import job created ({import_type.value}): "
            f"{successful} valid, {failed} errors, {duplicate} duplicates of {len(raw_rows)} rows",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return job

    def _duplicate_key(self, import_type: ImportType, normalized: dict) -> tuple | None:
        if import_type in (ImportType.SALES, ImportType.TALLY):
            return ("sales", normalized.get("invoice_number"), normalized.get("customer_id"))
        if import_type == ImportType.PURCHASES:
            return ("purchase", normalized.get("invoice_number"), normalized.get("vendor_id"))
        if import_type == ImportType.CUSTOMERS:
            return ("customer", normalized.get("name", "").lower())
        if import_type == ImportType.VENDORS:
            return ("vendor", normalized.get("name", "").lower())
        if import_type == ImportType.PRODUCTS:
            return ("product", normalized.get("name", "").lower())
        if import_type == ImportType.LEDGERS:
            return ("ledger", normalized.get("name", "").lower())
        return None

    async def _check_existing_duplicate(
        self, import_type: ImportType, company_id: uuid.UUID, normalized: dict
    ) -> bool:
        if import_type in (ImportType.SALES, ImportType.TALLY) and normalized.get("customer_id"):
            existing = await self.sales_invoices.find_duplicate(
                company_id=company_id,
                invoice_number=normalized["invoice_number"],
                invoice_date=normalized["invoice_date"],
                customer_id=normalized["customer_id"],
            )
            return existing is not None
        if import_type == ImportType.PURCHASES and normalized.get("vendor_id"):
            existing = await self.purchase_invoices.find_duplicate(
                company_id=company_id,
                invoice_number=normalized["invoice_number"],
                invoice_date=normalized["invoice_date"],
                vendor_id=normalized["vendor_id"],
            )
            return existing is not None
        return False

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get(self, company_id: uuid.UUID, job_id: uuid.UUID) -> ImportJob:
        job = await self.repo.get_by_id_for_company(job_id, company_id)
        if job is None:
            raise NotFoundError("Import job not found", code="IMPORT_JOB_NOT_FOUND")
        return job

    async def list_jobs(self, company_id: uuid.UUID, *, page: int, page_size: int):
        return await self.repo.list_for_company(
            company_id, offset=(page - 1) * page_size, limit=page_size
        )

    async def preview(
        self, company_id: uuid.UUID, job_id: uuid.UUID, *, status: str | None, page: int, page_size: int
    ):
        await self.get(company_id, job_id)
        return await self.repo.list_rows(
            job_id, status=status, offset=(page - 1) * page_size, limit=page_size
        )

    async def errors(self, company_id: uuid.UUID, job_id: uuid.UUID, *, page: int, page_size: int):
        await self.get(company_id, job_id)
        return await self.repo.list_errors(job_id, offset=(page - 1) * page_size, limit=page_size)

    # ------------------------------------------------------------------
    # Commit — the only place staged rows become real accounting records
    # ------------------------------------------------------------------

    async def commit(
        self, company_id: uuid.UUID, job_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> ImportJob:
        job = await self.get(company_id, job_id)
        # COMPLETED_WITH_ERRORS is a terminal state a job *reaches* after
        # committing (some rows failed, the valid ones were still
        # created) — it is never a valid state to commit *from* again.
        # Only READY (parsed, never yet committed) may be committed.
        if job.status != ImportStatus.READY:
            raise ConflictError(
                f"Import job cannot be committed from status {job.status.value}",
                code="INVALID_IMPORT_STATUS",
            )

        rows = await self.repo.list_all_rows(job_id)
        valid_rows = [r for r in rows if r.status == RowStatus.VALID]

        try:
            if job.import_type == ImportType.CUSTOMERS:
                await self._commit_customers(company_id, valid_rows)
            elif job.import_type == ImportType.VENDORS:
                await self._commit_vendors(company_id, valid_rows)
            elif job.import_type == ImportType.PRODUCTS:
                await self._commit_products(company_id, valid_rows)
            elif job.import_type == ImportType.LEDGERS:
                await self._commit_ledgers(company_id, valid_rows)
            elif job.import_type in (ImportType.SALES, ImportType.TALLY):
                await self._commit_sales(company_id, job, valid_rows)
            elif job.import_type == ImportType.PURCHASES:
                await self._commit_purchases(company_id, job, valid_rows)
            elif job.import_type == ImportType.PAYMENTS:
                await self._commit_payments(company_id, job, valid_rows)
            elif job.import_type == ImportType.RECEIPTS:
                await self._commit_receipts(company_id, job, valid_rows)
            elif job.import_type == ImportType.JOURNALS:
                await self._commit_journals(company_id, job, valid_rows)
        except Exception:
            await self.db.rollback()
            job.status = ImportStatus.FAILED
            await self.db.flush()
            await self.audit.log(
                action=AuditAction.IMPORT_FAILED,
                user_id=current_user.id,
                company_id=company_id,
                resource_type="import_job",
                resource_id=str(job.id),
                description="Import commit failed and was rolled back",
                ip_address=meta.ip_address,
                user_agent=meta.user_agent,
            )
            raise

        # Recomputed from final row statuses, not the parse-time cache: a
        # JOURNALS group can only be confirmed balanced (or not) once every
        # row sharing its journal_number is known, which happens here in
        # commit — so a late-discovered imbalance must still be reflected
        # in the job's reported counts.
        rows = await self.repo.list_all_rows(job_id)
        job.successful_rows = sum(1 for r in rows if r.status == RowStatus.COMMITTED)
        job.failed_rows = sum(1 for r in rows if r.status == RowStatus.ERROR)
        job.duplicate_rows = sum(1 for r in rows if r.status == RowStatus.DUPLICATE)

        job.status = (
            ImportStatus.COMPLETED if job.failed_rows == 0 else ImportStatus.COMPLETED_WITH_ERRORS
        )
        job.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(job)

        await self.audit.log(
            action=AuditAction.IMPORT_COMMIT,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="import_job",
            resource_id=str(job.id),
            description=f"Import job committed: {len(valid_rows)} records created",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return job

    async def cancel(
        self, company_id: uuid.UUID, job_id: uuid.UUID, current_user: User, meta: RequestMeta
    ) -> ImportJob:
        job = await self.get(company_id, job_id)
        if job.status in (ImportStatus.COMPLETED, ImportStatus.COMPLETED_WITH_ERRORS):
            raise ConflictError("A completed import job cannot be cancelled", code="INVALID_IMPORT_STATUS")

        job.status = ImportStatus.CANCELLED
        await self.db.flush()
        await self.db.refresh(job)

        await self.audit.log(
            action=AuditAction.ACCOUNTING_CANCEL,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="import_job",
            resource_id=str(job.id),
            description="Import job cancelled",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return job

    # ------------------------------------------------------------------
    # Per-type commit helpers
    # ------------------------------------------------------------------

    async def _commit_customers(self, company_id: uuid.UUID, rows: list[ImportRow]) -> None:
        for row in rows:
            data = row.normalized_data
            entity = Customer(company_id=company_id, **data)
            self.db.add(entity)
            await self.db.flush()
            row.status = RowStatus.COMMITTED
            row.created_record_id = str(entity.id)

    async def _commit_vendors(self, company_id: uuid.UUID, rows: list[ImportRow]) -> None:
        for row in rows:
            entity = Vendor(company_id=company_id, **row.normalized_data)
            self.db.add(entity)
            await self.db.flush()
            row.status = RowStatus.COMMITTED
            row.created_record_id = str(entity.id)

    async def _commit_products(self, company_id: uuid.UUID, rows: list[ImportRow]) -> None:
        for row in rows:
            data = dict(row.normalized_data)
            data["tax_rate"] = _dec(data["tax_rate"])
            entity = ProductService(company_id=company_id, **data)
            self.db.add(entity)
            await self.db.flush()
            row.status = RowStatus.COMMITTED
            row.created_record_id = str(entity.id)

    async def _commit_ledgers(self, company_id: uuid.UUID, rows: list[ImportRow]) -> None:
        for row in rows:
            data = dict(row.normalized_data)
            data["opening_balance"] = _dec(data["opening_balance"])
            entity = Ledger(company_id=company_id, **data)
            self.db.add(entity)
            await self.db.flush()
            row.status = RowStatus.COMMITTED
            row.created_record_id = str(entity.id)

    async def _commit_sales(self, company_id: uuid.UUID, job: ImportJob, rows: list[ImportRow]) -> None:
        for row in rows:
            data = row.normalized_data
            taxable = round_money(_dec(data["taxable_amount"]))
            cgst = round_money(_dec(data["cgst_amount"]))
            sgst = round_money(_dec(data["sgst_amount"]))
            igst = round_money(_dec(data["igst_amount"]))
            cess = round_money(_dec(data["cess_amount"]))
            total_tax = cgst + sgst + igst + cess
            invoice = SalesInvoice(
                company_id=company_id,
                financial_year_id=job.financial_year_id,
                customer_id=uuid.UUID(data["customer_id"]),
                invoice_number=data["invoice_number"],
                invoice_date=_to_date(data["invoice_date"]),
                place_of_supply=data.get("place_of_supply"),
                subtotal=taxable,
                taxable_amount=taxable,
                cgst_amount=cgst,
                sgst_amount=sgst,
                igst_amount=igst,
                cess_amount=cess,
                total_tax=total_tax,
                grand_total=taxable + total_tax,
                status=TransactionStatus.POSTED,
                source=DataSource.TALLY if job.import_type == ImportType.TALLY else DataSource.CSV,
                source_reference=f"import:{job.id}:row:{row.row_number}",
            )
            self.db.add(invoice)
            await self.db.flush()
            row.status = RowStatus.COMMITTED
            row.created_record_id = str(invoice.id)

    async def _commit_purchases(
        self, company_id: uuid.UUID, job: ImportJob, rows: list[ImportRow]
    ) -> None:
        for row in rows:
            data = row.normalized_data
            taxable = round_money(_dec(data["taxable_amount"]))
            cgst = round_money(_dec(data["cgst_amount"]))
            sgst = round_money(_dec(data["sgst_amount"]))
            igst = round_money(_dec(data["igst_amount"]))
            cess = round_money(_dec(data["cess_amount"]))
            total_tax = cgst + sgst + igst + cess
            invoice = PurchaseInvoice(
                company_id=company_id,
                financial_year_id=job.financial_year_id,
                vendor_id=uuid.UUID(data["vendor_id"]),
                invoice_number=data["invoice_number"],
                invoice_date=_to_date(data["invoice_date"]),
                subtotal=taxable,
                taxable_amount=taxable,
                cgst_amount=cgst,
                sgst_amount=sgst,
                igst_amount=igst,
                cess_amount=cess,
                total_tax=total_tax,
                grand_total=taxable + total_tax,
                status=TransactionStatus.POSTED,
                source=DataSource.CSV,
                source_reference=f"import:{job.id}:row:{row.row_number}",
            )
            self.db.add(invoice)
            await self.db.flush()
            row.status = RowStatus.COMMITTED
            row.created_record_id = str(invoice.id)

    async def _commit_payments(
        self, company_id: uuid.UUID, job: ImportJob, rows: list[ImportRow]
    ) -> None:
        for row in rows:
            data = row.normalized_data
            payment = Payment(
                company_id=company_id,
                financial_year_id=job.financial_year_id,
                payment_date=_to_date(data["payment_date"]),
                payment_number=data["payment_number"],
                ledger_id=uuid.UUID(data["ledger_id"]),
                amount=round_money(_dec(data["amount"])),
                payment_mode=data["payment_mode"],
                reference_number=data.get("reference_number"),
                source=DataSource.CSV,
                source_reference=f"import:{job.id}:row:{row.row_number}",
            )
            self.db.add(payment)
            await self.db.flush()
            row.status = RowStatus.COMMITTED
            row.created_record_id = str(payment.id)

    async def _commit_receipts(
        self, company_id: uuid.UUID, job: ImportJob, rows: list[ImportRow]
    ) -> None:
        for row in rows:
            data = row.normalized_data
            receipt = Receipt(
                company_id=company_id,
                financial_year_id=job.financial_year_id,
                receipt_date=_to_date(data["receipt_date"]),
                receipt_number=data["receipt_number"],
                customer_id=uuid.UUID(data["customer_id"]),
                ledger_id=uuid.UUID(data["ledger_id"]),
                amount=round_money(_dec(data["amount"])),
                payment_mode=data["payment_mode"],
                source=DataSource.CSV,
                source_reference=f"import:{job.id}:row:{row.row_number}",
            )
            self.db.add(receipt)
            await self.db.flush()
            row.status = RowStatus.COMMITTED
            row.created_record_id = str(receipt.id)

    async def _commit_journals(
        self, company_id: uuid.UUID, job: ImportJob, rows: list[ImportRow]
    ) -> None:
        # Tally-style journal exports carry one row per line; group by
        # journal_number so multiple rows become the lines of one entry.
        groups: dict[str, list[ImportRow]] = {}
        for row in rows:
            groups.setdefault(row.normalized_data["journal_number"], []).append(row)

        for journal_number, group_rows in groups.items():
            first = group_rows[0].normalized_data
            total_debit = sum((_dec(r.normalized_data["debit_amount"]) for r in group_rows), _dec("0"))
            total_credit = sum((_dec(r.normalized_data["credit_amount"]) for r in group_rows), _dec("0"))
            if round_money(total_debit) != round_money(total_credit):
                for r in group_rows:
                    r.status = RowStatus.ERROR
                continue

            entry = JournalEntry(
                company_id=company_id,
                financial_year_id=job.financial_year_id,
                journal_number=journal_number,
                journal_date=_to_date(first["journal_date"]),
                narration=first.get("narration"),
                status=TransactionStatus.POSTED,
                source=DataSource.CSV,
                source_reference=f"import:{job.id}",
                lines=[
                    JournalEntryLine(
                        ledger_id=uuid.UUID(r.normalized_data["ledger_id"]),
                        debit_amount=round_money(_dec(r.normalized_data["debit_amount"])),
                        credit_amount=round_money(_dec(r.normalized_data["credit_amount"])),
                        description=r.normalized_data.get("narration"),
                    )
                    for r in group_rows
                ],
            )
            self.db.add(entry)
            await self.db.flush()
            for r in group_rows:
                r.status = RowStatus.COMMITTED
                r.created_record_id = str(entry.id)


def _dec(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _to_date(value):
    """`normalized_data` is read back from a JSON column, so dates arrive
    as ISO strings (see `_json_safe`) — every commit helper that reads a
    date out of it must round-trip through this, never pass the string
    straight into a Date-typed column."""
    from datetime import date as _date

    if isinstance(value, _date):
        return value
    return _date.fromisoformat(value)


def _json_safe(data: dict) -> dict:
    """ImportRow.normalized_data is a JSON column — dates, Decimals, and
    UUIDs from the validators need to become JSON-safe strings first."""
    import datetime as _dt

    safe = {}
    for key, value in data.items():
        if isinstance(value, (_dt.date, _dt.datetime)):
            safe[key] = value.isoformat()
        elif isinstance(value, Decimal):
            safe[key] = str(value)
        elif isinstance(value, uuid.UUID):
            safe[key] = str(value)
        else:
            safe[key] = value
    return safe
