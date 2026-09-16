"""Purchase Books vs. imported GSTR-2B reconciliation (PHASE4 sections
30-34). Matching runs in stages — exact identifiers first, then a
normalized invoice number, then a cross-GSTIN check purely to explain a
mismatch — and never silently decides an amount is "close enough" beyond
a small, explicit rupee tolerance. Re-running a period's reconciliation
replaces its prior result rows; the run header itself is kept so match-rate
history is visible on the dashboard.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.gst_enums import ITCCategory, ITCReviewStatus, ReconciliationStatus
from app.models.gst_reconciliation import GSTReconciliation, GSTReconciliationResult
from app.models.gstr2b_record import GSTR2BRecord
from app.models.purchase_invoice import PurchaseInvoice
from app.models.user import User
from app.repositories.gst_reconciliation_repository import GSTReconciliationRepository
from app.repositories.gst_return_period_repository import GSTReturnPeriodRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.utils.invoice_number import normalize_invoice_number

AMOUNT_TOLERANCE = Decimal("1.00")

_STATUS_TO_ITC_CATEGORY = {
    ReconciliationStatus.MATCHED: ITCCategory.MATCHED_ITC,
    ReconciliationStatus.PARTIALLY_MATCHED: ITCCategory.UNMATCHED_ITC,
    ReconciliationStatus.AMOUNT_MISMATCH: ITCCategory.UNMATCHED_ITC,
    ReconciliationStatus.DATE_MISMATCH: ITCCategory.UNMATCHED_ITC,
    ReconciliationStatus.INVOICE_NUMBER_MISMATCH: ITCCategory.UNMATCHED_ITC,
    ReconciliationStatus.GSTIN_MISMATCH: ITCCategory.UNMATCHED_ITC,
    ReconciliationStatus.BOOKS_ONLY: ITCCategory.POTENTIAL_ITC,
    ReconciliationStatus.GSTR2B_ONLY: ITCCategory.REVIEW_REQUIRED,
    ReconciliationStatus.DUPLICATE: ITCCategory.REVIEW_REQUIRED,
    ReconciliationStatus.REVIEW_REQUIRED: ITCCategory.REVIEW_REQUIRED,
}


@dataclass
class _BookLine:
    invoice: PurchaseInvoice
    supplier_gstin: str | None
    match_invoice_number: str
    match_invoice_date: date


def _within_tolerance(a: Decimal | None, b: Decimal | None) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= AMOUNT_TOLERANCE


class GSTReconciliationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = GSTReconciliationRepository(db)
        self.period_repo = GSTReturnPeriodRepository(db)
        self.audit = AuditService(db)

    async def run(
        self,
        company_id: uuid.UUID,
        return_period_id: uuid.UUID,
        current_user: User,
        meta: RequestMeta,
    ) -> GSTReconciliation:
        period = await self.period_repo.get_by_id_for_company(return_period_id, company_id)
        if period is None:
            raise NotFoundError("GST return period not found", code="GST_RETURN_PERIOD_NOT_FOUND")

        purchase_invoices = await self.repo.list_posted_purchase_invoices(
            company_id, period.period_start, period.period_end
        )
        records = await self.repo.list_gstr2b_records(company_id, return_period_id)

        exact_index: dict[tuple[str, str], list[GSTR2BRecord]] = {}
        normalized_index: dict[tuple[str, str], list[GSTR2BRecord]] = {}
        normalized_any_gstin: dict[str, list[GSTR2BRecord]] = {}
        for record in records:
            exact_index.setdefault((record.supplier_gstin, record.invoice_number), []).append(record)
            norm_number = normalize_invoice_number(record.invoice_number)
            normalized_index.setdefault((record.supplier_gstin, norm_number), []).append(record)
            normalized_any_gstin.setdefault(norm_number, []).append(record)

        matched_ids: set[uuid.UUID] = set()
        results: list[GSTReconciliationResult] = []

        for invoice in purchase_invoices:
            supplier_gstin = invoice.vendor.gstin if invoice.vendor else None
            match_number = invoice.supplier_invoice_number or invoice.invoice_number
            match_date = invoice.supplier_invoice_date or invoice.invoice_date

            books_amounts = {
                "books_taxable_value": invoice.taxable_amount,
                "books_cgst_amount": invoice.cgst_amount,
                "books_sgst_amount": invoice.sgst_amount,
                "books_igst_amount": invoice.igst_amount,
                "books_cess_amount": invoice.cess_amount,
            }
            books_total_tax = invoice.cgst_amount + invoice.sgst_amount + invoice.igst_amount + invoice.cess_amount

            if not supplier_gstin:
                results.append(
                    self._build_result(
                        company_id,
                        purchase_invoice_id=invoice.id,
                        gstr2b_record_id=None,
                        status=ReconciliationStatus.REVIEW_REQUIRED,
                        books_amounts=books_amounts,
                        gstr2b_amounts=None,
                    )
                )
                continue

            record = self._find_unmatched(exact_index.get((supplier_gstin, match_number)), matched_ids)
            status: ReconciliationStatus
            if record is not None:
                matched_ids.add(record.id)
                if record.invoice_date != match_date:
                    status = ReconciliationStatus.DATE_MISMATCH
                elif _within_tolerance(
                    invoice.taxable_amount, record.taxable_value
                ) and _within_tolerance(books_total_tax, record.total_tax):
                    status = ReconciliationStatus.MATCHED
                else:
                    status = ReconciliationStatus.AMOUNT_MISMATCH
            else:
                norm_number = normalize_invoice_number(match_number)
                record = self._find_unmatched(
                    normalized_index.get((supplier_gstin, norm_number)), matched_ids
                )
                if record is not None:
                    matched_ids.add(record.id)
                    if _within_tolerance(
                        invoice.taxable_amount, record.taxable_value
                    ) and _within_tolerance(books_total_tax, record.total_tax):
                        status = ReconciliationStatus.PARTIALLY_MATCHED
                    else:
                        status = ReconciliationStatus.AMOUNT_MISMATCH
                else:
                    record = self._find_unmatched(normalized_any_gstin.get(norm_number), matched_ids)
                    if record is not None:
                        matched_ids.add(record.id)
                        status = ReconciliationStatus.GSTIN_MISMATCH
                    else:
                        status = ReconciliationStatus.BOOKS_ONLY

            results.append(
                self._build_result(
                    company_id,
                    purchase_invoice_id=invoice.id,
                    gstr2b_record_id=record.id if record else None,
                    status=status,
                    books_amounts=books_amounts,
                    gstr2b_amounts=self._record_amounts(record) if record else None,
                )
            )

        leftover = [r for r in records if r.id not in matched_ids]
        seen_leftover_keys: set[tuple[str, str]] = set()
        for record in leftover:
            key = (record.supplier_gstin, record.invoice_number)
            status = (
                ReconciliationStatus.DUPLICATE
                if key in seen_leftover_keys
                else ReconciliationStatus.GSTR2B_ONLY
            )
            seen_leftover_keys.add(key)
            results.append(
                self._build_result(
                    company_id,
                    purchase_invoice_id=None,
                    gstr2b_record_id=record.id,
                    status=status,
                    books_amounts=None,
                    gstr2b_amounts=self._record_amounts(record),
                )
            )

        await self.repo.delete_previous_runs(company_id, return_period_id)

        counts = {status: 0 for status in ReconciliationStatus}
        for r in results:
            counts[r.status] += 1

        run = GSTReconciliation(
            company_id=company_id,
            return_period_id=return_period_id,
            run_at=datetime.now(timezone.utc),
            run_by=current_user.id,
            total_purchase_invoices=len(purchase_invoices),
            matched_count=counts[ReconciliationStatus.MATCHED],
            partially_matched_count=counts[ReconciliationStatus.PARTIALLY_MATCHED],
            mismatch_count=(
                counts[ReconciliationStatus.AMOUNT_MISMATCH]
                + counts[ReconciliationStatus.DATE_MISMATCH]
                + counts[ReconciliationStatus.GSTIN_MISMATCH]
                + counts[ReconciliationStatus.INVOICE_NUMBER_MISMATCH]
            ),
            books_only_count=counts[ReconciliationStatus.BOOKS_ONLY],
            gstr2b_only_count=counts[ReconciliationStatus.GSTR2B_ONLY],
            duplicate_count=counts[ReconciliationStatus.DUPLICATE],
            review_required_count=counts[ReconciliationStatus.REVIEW_REQUIRED],
        )
        await self.repo.create_run(run)
        for r in results:
            r.reconciliation_id = run.id
        await self.repo.add_results(results)

        await self.audit.log(
            action=AuditAction.GSTR2B_RECONCILED,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="gst_reconciliation",
            resource_id=str(run.id),
            description=(
                f"Reconciliation run: {run.matched_count} matched, {run.mismatch_count} mismatched, "
                f"{run.books_only_count} books-only, {run.gstr2b_only_count} 2B-only of "
                f"{run.total_purchase_invoices} purchase invoices"
            ),
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return run

    @staticmethod
    def _find_unmatched(
        candidates: list[GSTR2BRecord] | None, matched_ids: set[uuid.UUID]
    ) -> GSTR2BRecord | None:
        if not candidates:
            return None
        for c in candidates:
            if c.id not in matched_ids:
                return c
        return None

    @staticmethod
    def _record_amounts(record: GSTR2BRecord) -> dict:
        return {
            "gstr2b_taxable_value": record.taxable_value,
            "gstr2b_cgst_amount": record.cgst_amount,
            "gstr2b_sgst_amount": record.sgst_amount,
            "gstr2b_igst_amount": record.igst_amount,
            "gstr2b_cess_amount": record.cess_amount,
        }

    def _build_result(
        self,
        company_id: uuid.UUID,
        *,
        purchase_invoice_id: uuid.UUID | None,
        gstr2b_record_id: uuid.UUID | None,
        status: ReconciliationStatus,
        books_amounts: dict | None,
        gstr2b_amounts: dict | None,
    ) -> GSTReconciliationResult:
        books_amounts = books_amounts or {}
        gstr2b_amounts = gstr2b_amounts or {}

        taxable_value_diff = None
        tax_diff = None
        if books_amounts.get("books_taxable_value") is not None and gstr2b_amounts.get(
            "gstr2b_taxable_value"
        ) is not None:
            taxable_value_diff = books_amounts["books_taxable_value"] - gstr2b_amounts["gstr2b_taxable_value"]
            books_tax = (
                books_amounts["books_cgst_amount"]
                + books_amounts["books_sgst_amount"]
                + books_amounts["books_igst_amount"]
                + books_amounts["books_cess_amount"]
            )
            gstr2b_tax = (
                gstr2b_amounts["gstr2b_cgst_amount"]
                + gstr2b_amounts["gstr2b_sgst_amount"]
                + gstr2b_amounts["gstr2b_igst_amount"]
                + gstr2b_amounts["gstr2b_cess_amount"]
            )
            tax_diff = books_tax - gstr2b_tax

        return GSTReconciliationResult(
            company_id=company_id,
            purchase_invoice_id=purchase_invoice_id,
            gstr2b_record_id=gstr2b_record_id,
            status=status,
            taxable_value_diff=taxable_value_diff,
            tax_diff=tax_diff,
            itc_category=_STATUS_TO_ITC_CATEGORY[status],
            itc_review_status=ITCReviewStatus.PENDING,
            **books_amounts,
            **gstr2b_amounts,
        )

    async def get_latest(self, company_id: uuid.UUID, return_period_id: uuid.UUID) -> GSTReconciliation:
        run = await self.repo.get_latest_run(company_id, return_period_id)
        if run is None:
            raise NotFoundError(
                "No reconciliation has been run for this return period yet",
                code="GST_RECONCILIATION_NOT_FOUND",
            )
        return run

    async def list_results(
        self,
        company_id: uuid.UUID,
        return_period_id: uuid.UUID,
        *,
        status: ReconciliationStatus | None,
        itc_category: ITCCategory | None,
        page: int,
        page_size: int,
    ) -> tuple[list[GSTReconciliationResult], int]:
        run = await self.get_latest(company_id, return_period_id)
        return await self.repo.list_results_for_run(
            run.id,
            status=status,
            itc_category=itc_category,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
