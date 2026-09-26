from datetime import date
from decimal import Decimal
import hashlib
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting_enums import PeriodStatus
from app.models.accounting_period import AccountingPeriod
from app.models.import_job import ImportRow, ImportRowStatus
from app.models.journal_entry import JournalEntry
from app.models.payment import Payment
from app.models.purchase_invoice import PurchaseInvoice
from app.models.receipt import Receipt
from app.models.sales_invoice import SalesInvoice
from app.services.tally.tally_models import (
    TallyImportBatch,
    TallyValidationError,
    TallyVoucherRecord,
    TallyVoucherType,
    ValidationSeverity,
)


def compute_voucher_fingerprint(company_id: uuid.UUID, voucher: TallyVoucherRecord) -> str:
    """Deterministic hash of voucher identity for duplicate detection."""
    v_type = voucher.normalized_type.value
    v_num = (voucher.voucher_number or "").strip().upper()
    v_date = voucher.voucher_date.isoformat() if voucher.voucher_date else ""
    v_amt = f"{voucher.total_amount:.2f}"
    v_party = (voucher.party_name or "").strip().upper()
    raw_str = f"{company_id}|{v_type}|{v_num}|{v_date}|{v_amt}|{v_party}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


class TallyValidationResult:
    def __init__(self) -> None:
        self.errors: list[TallyValidationError] = []
        self.warnings: list[TallyValidationError] = []
        self.reviews_required: list[TallyValidationError] = []
        self.duplicate_vouchers: set[str] = set()  # voucher numbers that are duplicates
        self.duplicate_fingerprints: set[str] = set()
        self.valid_vouchers_count: int = 0
        self.invalid_vouchers_count: int = 0

    @property
    def is_valid_to_commit(self) -> bool:
        return len(self.errors) == 0 and len(self.reviews_required) == 0


class TallyValidator:
    """Comprehensive validation engine for Tally imports."""

    def __init__(self, db: AsyncSession, company_id: uuid.UUID) -> None:
        self.db = db
        self.company_id = company_id
        self._locked_periods: list[AccountingPeriod] = []
        self._existing_sales_numbers: set[str] = set()
        self._existing_purchase_numbers: set[str] = set()
        self._existing_payment_numbers: set[str] = set()
        self._existing_receipt_numbers: set[str] = set()
        self._existing_journal_numbers: set[str] = set()
        self._existing_fingerprints: set[str] = set()
        self._loaded = False

    async def load_existing_records(self) -> None:
        if self._loaded:
            return

        # 1. Locked accounting periods
        p_res = await self.db.execute(
            select(AccountingPeriod).where(
                AccountingPeriod.company_id == self.company_id,
                AccountingPeriod.status == PeriodStatus.LOCKED,
            )
        )
        self._locked_periods = list(p_res.scalars().all())

        # 2. Existing transactions
        s_res = await self.db.execute(
            select(SalesInvoice.invoice_number, SalesInvoice.source_reference).where(
                SalesInvoice.company_id == self.company_id
            )
        )
        for num, s_ref in s_res.all():
            if num:
                self._existing_sales_numbers.add(num.strip().upper())
            if s_ref and s_ref.startswith("fp:"):
                self._existing_fingerprints.add(s_ref[3:])

        p_res = await self.db.execute(
            select(PurchaseInvoice.invoice_number, PurchaseInvoice.supplier_invoice_number, PurchaseInvoice.source_reference).where(
                PurchaseInvoice.company_id == self.company_id
            )
        )
        for num, sup_num, s_ref in p_res.all():
            if num:
                self._existing_purchase_numbers.add(num.strip().upper())
            if sup_num:
                self._existing_purchase_numbers.add(sup_num.strip().upper())
            if s_ref and s_ref.startswith("fp:"):
                self._existing_fingerprints.add(s_ref[3:])

        pay_res = await self.db.execute(
            select(Payment.payment_number, Payment.source_reference).where(Payment.company_id == self.company_id)
        )
        for num, s_ref in pay_res.all():
            if num:
                self._existing_payment_numbers.add(num.strip().upper())
            if s_ref and s_ref.startswith("fp:"):
                self._existing_fingerprints.add(s_ref[3:])

        rec_res = await self.db.execute(
            select(Receipt.receipt_number, Receipt.source_reference).where(Receipt.company_id == self.company_id)
        )
        for num, s_ref in rec_res.all():
            if num:
                self._existing_receipt_numbers.add(num.strip().upper())
            if s_ref and s_ref.startswith("fp:"):
                self._existing_fingerprints.add(s_ref[3:])

        j_res = await self.db.execute(
            select(JournalEntry.journal_number, JournalEntry.source_reference).where(
                JournalEntry.company_id == self.company_id
            )
        )
        for num, s_ref in j_res.all():
            if num:
                self._existing_journal_numbers.add(num.strip().upper())
            if s_ref and s_ref.startswith("fp:"):
                self._existing_fingerprints.add(s_ref[3:])

        # 3. Check previously committed import rows
        row_res = await self.db.execute(
            select(ImportRow.normalized_data).where(
                ImportRow.status == ImportRowStatus.COMMITTED
            )
        )
        for (norm_data,) in row_res.all():
            if norm_data and isinstance(norm_data, dict):
                fp = norm_data.get("fingerprint")
                if fp:
                    self._existing_fingerprints.add(fp)

        self._loaded = True

    async def validate_batch(self, batch: TallyImportBatch) -> TallyValidationResult:
        await self.load_existing_records()
        result = TallyValidationResult()

        seen_in_batch_fingerprints: set[str] = set()
        seen_in_batch_vouchers: set[tuple[str, str]] = set()

        # 1. Validate Vouchers
        for idx, voucher in enumerate(batch.vouchers, start=1):
            fp = compute_voucher_fingerprint(self.company_id, voucher)
            voucher.fingerprint = fp

            v_num = (voucher.voucher_number or "").strip()
            v_key = (voucher.normalized_type.value, v_num.upper())

            voucher_has_error = False

            # Check Duplicate
            is_dup = False
            dup_reason = ""
            if fp in self._existing_fingerprints or fp in seen_in_batch_fingerprints:
                is_dup = True
                dup_reason = "Already Imported (exact fingerprint match)"
            elif v_key in seen_in_batch_vouchers:
                is_dup = True
                dup_reason = f"Duplicate voucher number '{v_num}' in this import file"
            else:
                # Check entity-specific numbering
                if voucher.normalized_type == TallyVoucherType.SALES and v_num.upper() in self._existing_sales_numbers:
                    is_dup = True
                    dup_reason = f"Sales invoice '{v_num}' already exists in company"
                elif voucher.normalized_type == TallyVoucherType.PURCHASE and v_num.upper() in self._existing_purchase_numbers:
                    is_dup = True
                    dup_reason = f"Purchase invoice '{v_num}' already exists in company"
                elif voucher.normalized_type == TallyVoucherType.PAYMENT and v_num.upper() in self._existing_payment_numbers:
                    is_dup = True
                    dup_reason = f"Payment voucher '{v_num}' already exists in company"
                elif voucher.normalized_type == TallyVoucherType.RECEIPT and v_num.upper() in self._existing_receipt_numbers:
                    is_dup = True
                    dup_reason = f"Receipt voucher '{v_num}' already exists in company"
                elif voucher.normalized_type == TallyVoucherType.JOURNAL and v_num.upper() in self._existing_journal_numbers:
                    is_dup = True
                    dup_reason = f"Journal entry '{v_num}' already exists in company"

            if is_dup:
                result.duplicate_vouchers.add(v_num)
                result.duplicate_fingerprints.add(fp)
                result.warnings.append(
                    TallyValidationError(
                        code="DUPLICATE_RECORD",
                        message=dup_reason,
                        entity="VOUCHER",
                        row_ref=idx,
                        field="voucher_number",
                        severity=ValidationSeverity.WARNING,
                        extra={"fingerprint": fp, "voucher_number": v_num},
                    )
                )
            else:
                seen_in_batch_fingerprints.add(fp)
                seen_in_batch_vouchers.add(v_key)

            # Check Period Lock
            if voucher.voucher_date:
                for period in self._locked_periods:
                    if period.start_date <= voucher.voucher_date <= period.end_date:
                        voucher_has_error = True
                        result.errors.append(
                            TallyValidationError(
                                code="PERIOD_LOCKED",
                                message=f"Transaction date {voucher.voucher_date} falls into locked accounting period '{period.name}'",
                                entity="VOUCHER",
                                row_ref=idx,
                                field="voucher_date",
                                severity=ValidationSeverity.ERROR,
                            )
                        )
                        break

            # Check Amount
            if voucher.total_amount <= Decimal(0):
                voucher_has_error = True
                result.errors.append(
                    TallyValidationError(
                        code="INVALID_AMOUNT",
                        message=f"Voucher {v_num} has non-positive amount {voucher.total_amount}",
                        entity="VOUCHER",
                        row_ref=idx,
                        field="total_amount",
                        severity=ValidationSeverity.ERROR,
                    )
                )

            # Check Double-Entry Consistency
            debit_total = sum((l.amount for l in voucher.lines if l.is_debit), Decimal(0))
            credit_total = sum((l.amount for l in voucher.lines if not l.is_debit), Decimal(0))

            if voucher.lines:
                if abs(debit_total - credit_total) > Decimal("0.05"):
                    # For Journal vouchers, double entry is strictly required
                    if voucher.normalized_type in (TallyVoucherType.JOURNAL, TallyVoucherType.CONTRA):
                        voucher_has_error = True
                        result.errors.append(
                            TallyValidationError(
                                code="UNBALANCED_VOUCHER",
                                message=f"Journal voucher {v_num} is unbalanced: Debit={debit_total} vs Credit={credit_total}",
                                entity="VOUCHER",
                                row_ref=idx,
                                field="lines",
                                severity=ValidationSeverity.ERROR,
                            )
                        )
                    else:
                        result.warnings.append(
                            TallyValidationError(
                                code="UNBALANCED_VOUCHER",
                                message=f"Voucher {v_num} lines differ by {abs(debit_total - credit_total)}: Debit={debit_total}, Credit={credit_total}",
                                entity="VOUCHER",
                                row_ref=idx,
                                field="lines",
                                severity=ValidationSeverity.WARNING,
                            )
                        )

            # Check GST Consistency
            tb = voucher.tax_breakdown
            if tb.total_tax > Decimal(0) and tb.taxable_amount > Decimal(0):
                implied_rate = (tb.total_tax / tb.taxable_amount) * Decimal(100)
                # If implied rate is wildly unusual or tax doesn't add up
                tax_sum = tb.cgst_amount + tb.sgst_amount + tb.igst_amount + tb.cess_amount
                if abs(tax_sum - tb.total_tax) > Decimal("0.05"):
                    result.reviews_required.append(
                        TallyValidationError(
                            code="IMPORT_TAX_MISMATCH",
                            message=f"GST components ({tax_sum}) do not sum to total tax ({tb.total_tax}) on voucher {v_num}",
                            entity="VOUCHER",
                            row_ref=idx,
                            field="tax_breakdown",
                            severity=ValidationSeverity.REVIEW_REQUIRED,
                            extra={"components_sum": float(tax_sum), "total_tax": float(tb.total_tax)},
                        )
                    )

            if voucher_has_error:
                result.invalid_vouchers_count += 1
            else:
                result.valid_vouchers_count += 1

        # 2. Validate Opening Balances
        if batch.opening_balances:
            total_ob_dr = sum((ob.amount for ob in batch.opening_balances if ob.is_debit), Decimal(0))
            total_ob_cr = sum((ob.amount for ob in batch.opening_balances if not ob.is_debit), Decimal(0))
            if abs(total_ob_dr - total_ob_cr) > Decimal("0.05"):
                result.reviews_required.append(
                    TallyValidationError(
                        code="UNBALANCED_OPENING_BALANCE",
                        message=f"Opening balances are unbalanced: Total Debit ₹{total_ob_dr:,.2f} != Total Credit ₹{total_ob_cr:,.2f}",
                        entity="OPENING_BALANCE",
                        row_ref="OPENING_BALANCES",
                        field="amount",
                        severity=ValidationSeverity.REVIEW_REQUIRED,
                        extra={"total_debit": float(total_ob_dr), "total_credit": float(total_ob_cr)},
                    )
                )

        return result
