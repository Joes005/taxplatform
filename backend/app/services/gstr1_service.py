"""GSTR-1 preparation — turns already-posted Phase 3 sales data into the
structured rows a CA reviews before filing GSTR-1 elsewhere. This module
never files anything and never edits SalesInvoice/CreditNote/DebitNote; it
only reads POSTED records and classifies/aggregates them.

Known, deliberate limitation: Phase 3's Customer/SalesInvoice models carry
no export/SEZ indicator (no country, no SEZ flag), so `get_exports` always
returns an empty list rather than guessing which B2B invoices might be
exports — see PHASE4 section 20 ("do not pretend to have information that
is not present"). A future phase can add that indicator to Customer.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationAppError
from app.models.accounting_enums import TransactionStatus
from app.models.credit_note import CreditNote
from app.models.debit_note import DebitNote
from app.models.gst_enums import GSTTransactionCategory, SupplyType, ValidationSeverity
from app.models.sales_invoice import SalesInvoice
from app.repositories.gst_profile_repository import GSTProfileRepository
from app.repositories.gst_return_period_repository import GSTReturnPeriodRepository
from app.repositories.gstr1_repository import GSTR1Repository
from app.schemas.gst_common import GSTValidationFinding
from app.schemas.gstr1 import (
    GSTR1B2BRow,
    GSTR1B2CLargeRow,
    GSTR1B2COthersRow,
    GSTR1DocumentSummaryRow,
    GSTR1HSNRow,
    GSTR1NoteRow,
    GSTR1Overview,
)
from app.services.gst_classification_service import GSTTransactionClassificationService
from app.services.gst_place_of_supply_service import GSTPlaceOfSupplyService
from app.services.gst_validation_service import GSTValidationService, make_finding

B2C_LARGE_INTERSTATE_THRESHOLD = Decimal("250000")

ALL_STATUSES = (TransactionStatus.DRAFT, TransactionStatus.POSTED, TransactionStatus.CANCELLED)


@dataclass
class _ClassifiedInvoice:
    invoice: SalesInvoice
    category: GSTTransactionCategory
    supply_type: SupplyType | None
    reason: str | None = None


@dataclass
class _PreparedData:
    supplier_state_code: str
    classified: list[_ClassifiedInvoice] = field(default_factory=list)
    credit_notes: list[CreditNote] = field(default_factory=list)
    debit_notes: list[DebitNote] = field(default_factory=list)


class GSTR1Service:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = GSTR1Repository(db)
        self.profile_repo = GSTProfileRepository(db)
        self.period_repo = GSTReturnPeriodRepository(db)

    async def _get_period(self, company_id: uuid.UUID, return_period_id: uuid.UUID):
        from app.core.exceptions import NotFoundError

        period = await self.period_repo.get_by_id_for_company(return_period_id, company_id)
        if period is None:
            raise NotFoundError("GST return period not found", code="GST_RETURN_PERIOD_NOT_FOUND")
        return period

    async def _prepare(self, company_id: uuid.UUID, return_period_id: uuid.UUID) -> _PreparedData:
        period = await self._get_period(company_id, return_period_id)

        profile = await self.profile_repo.get_for_company(company_id)
        if profile is None:
            raise ValidationAppError(
                "A GST profile must be created for this company before preparing GSTR-1",
                code="GST_PROFILE_REQUIRED",
            )

        invoices = await self.repo.list_sales_invoices(
            company_id, period.period_start, period.period_end
        )
        credit_notes = await self.repo.list_notes(
            CreditNote, company_id, period.period_start, period.period_end
        )
        debit_notes = await self.repo.list_notes(
            DebitNote, company_id, period.period_start, period.period_end
        )

        classified: list[_ClassifiedInvoice] = []
        for invoice in invoices:
            result = GSTTransactionClassificationService.classify_sales_transaction(
                customer_gstin=invoice.customer.gstin if invoice.customer else None,
                customer_state_code=invoice.customer.state_code if invoice.customer else None,
                place_of_supply_state_code=invoice.place_of_supply_state_code,
            )
            supply_type = None
            if invoice.place_of_supply_state_code:
                supply_type = GSTPlaceOfSupplyService.determine_supply_type(
                    profile.state_code, invoice.place_of_supply_state_code
                )
            classified.append(
                _ClassifiedInvoice(
                    invoice=invoice,
                    category=result.category,
                    supply_type=supply_type,
                    reason=result.reason,
                )
            )

        return _PreparedData(
            supplier_state_code=profile.state_code,
            classified=classified,
            credit_notes=credit_notes,
            debit_notes=debit_notes,
        )

    def _is_b2c_large(self, item: _ClassifiedInvoice) -> bool:
        return (
            item.category == GSTTransactionCategory.B2C
            and item.supply_type == SupplyType.INTER_STATE
            and item.invoice.grand_total > B2C_LARGE_INTERSTATE_THRESHOLD
        )

    async def get_b2b(self, company_id: uuid.UUID, return_period_id: uuid.UUID) -> list[GSTR1B2BRow]:
        data = await self._prepare(company_id, return_period_id)
        return [
            GSTR1B2BRow(
                sales_invoice_id=c.invoice.id,
                recipient_gstin=c.invoice.customer.gstin,
                recipient_name=c.invoice.customer.name,
                invoice_number=c.invoice.invoice_number,
                invoice_date=c.invoice.invoice_date,
                invoice_value=c.invoice.grand_total,
                place_of_supply_state_code=c.invoice.place_of_supply_state_code,
                taxable_value=c.invoice.taxable_amount,
                cgst_amount=c.invoice.cgst_amount,
                sgst_amount=c.invoice.sgst_amount,
                igst_amount=c.invoice.igst_amount,
                cess_amount=c.invoice.cess_amount,
            )
            for c in data.classified
            if c.category == GSTTransactionCategory.B2B
        ]

    async def get_b2c_large(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID
    ) -> list[GSTR1B2CLargeRow]:
        data = await self._prepare(company_id, return_period_id)
        return [
            GSTR1B2CLargeRow(
                sales_invoice_id=c.invoice.id,
                invoice_number=c.invoice.invoice_number,
                invoice_date=c.invoice.invoice_date,
                invoice_value=c.invoice.grand_total,
                place_of_supply_state_code=c.invoice.place_of_supply_state_code,
                taxable_value=c.invoice.taxable_amount,
                cgst_amount=c.invoice.cgst_amount,
                sgst_amount=c.invoice.sgst_amount,
                igst_amount=c.invoice.igst_amount,
                cess_amount=c.invoice.cess_amount,
            )
            for c in data.classified
            if self._is_b2c_large(c)
        ]

    async def get_b2c_others(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID
    ) -> list[GSTR1B2COthersRow]:
        data = await self._prepare(company_id, return_period_id)
        groups: dict[tuple[str | None, Decimal], dict] = {}
        for c in data.classified:
            if c.category != GSTTransactionCategory.B2C or self._is_b2c_large(c):
                continue
            for item in c.invoice.items:
                key = (c.invoice.place_of_supply_state_code, item.tax_rate)
                bucket = groups.setdefault(
                    key,
                    {
                        "invoice_ids": set(),
                        "taxable_value": Decimal("0"),
                        "cgst_amount": Decimal("0"),
                        "sgst_amount": Decimal("0"),
                        "igst_amount": Decimal("0"),
                        "cess_amount": Decimal("0"),
                    },
                )
                bucket["invoice_ids"].add(c.invoice.id)
                bucket["taxable_value"] += item.taxable_value
                bucket["cgst_amount"] += item.cgst_amount
                bucket["sgst_amount"] += item.sgst_amount
                bucket["igst_amount"] += item.igst_amount
                bucket["cess_amount"] += item.cess_amount

        return [
            GSTR1B2COthersRow(
                place_of_supply_state_code=state_code,
                tax_rate=rate,
                invoice_count=len(bucket["invoice_ids"]),
                taxable_value=bucket["taxable_value"],
                cgst_amount=bucket["cgst_amount"],
                sgst_amount=bucket["sgst_amount"],
                igst_amount=bucket["igst_amount"],
                cess_amount=bucket["cess_amount"],
            )
            for (state_code, rate), bucket in sorted(groups.items(), key=lambda kv: (kv[0][0] or "", kv[0][1]))
        ]

    async def get_exports(self, company_id: uuid.UUID, return_period_id: uuid.UUID) -> list:
        await self._get_period(company_id, return_period_id)
        return []

    async def _get_note_rows(
        self,
        company_id: uuid.UUID,
        notes: list[CreditNote] | list[DebitNote],
        number_attr: str,
        date_attr: str,
    ) -> list[GSTR1NoteRow]:
        reference_ids = {n.reference_sales_invoice_id for n in notes if n.reference_sales_invoice_id}
        invoice_numbers = await self.repo.get_invoice_numbers_by_ids(company_id, reference_ids)

        rows = []
        for note in notes:
            rows.append(
                GSTR1NoteRow(
                    note_id=note.id,
                    note_number=getattr(note, number_attr),
                    note_date=getattr(note, date_attr),
                    reference_invoice_id=note.reference_sales_invoice_id,
                    reference_invoice_number=invoice_numbers.get(note.reference_sales_invoice_id),
                    recipient_gstin=note.customer.gstin if note.customer else None,
                    recipient_name=note.customer.name if note.customer else None,
                    taxable_value=note.taxable_amount,
                    cgst_amount=note.cgst_amount,
                    sgst_amount=note.sgst_amount,
                    igst_amount=note.igst_amount,
                    cess_amount=note.cess_amount,
                )
            )
        return rows

    async def get_credit_notes(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID
    ) -> list[GSTR1NoteRow]:
        data = await self._prepare(company_id, return_period_id)
        return await self._get_note_rows(
            company_id, data.credit_notes, "credit_note_number", "credit_note_date"
        )

    async def get_debit_notes(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID
    ) -> list[GSTR1NoteRow]:
        data = await self._prepare(company_id, return_period_id)
        return await self._get_note_rows(
            company_id, data.debit_notes, "debit_note_number", "debit_note_date"
        )

    async def get_hsn_summary(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID
    ) -> list[GSTR1HSNRow]:
        data = await self._prepare(company_id, return_period_id)
        counted_invoices = [
            c.invoice
            for c in data.classified
            if c.category in (GSTTransactionCategory.B2B, GSTTransactionCategory.B2C)
        ]
        product_ids = {
            item.product_service_id
            for invoice in counted_invoices
            for item in invoice.items
            if item.product_service_id is not None
        }
        products = await self.repo.get_products_by_ids(company_id, product_ids)

        groups: dict[tuple[str | None, Decimal], dict] = {}
        for invoice in counted_invoices:
            for item in invoice.items:
                product = products.get(item.product_service_id) if item.product_service_id else None
                hsn_sac = product.hsn_sac if product else None
                key = (hsn_sac, item.tax_rate)
                bucket = groups.setdefault(
                    key,
                    {
                        "description": product.name if product else item.description,
                        "uqc": item.unit,
                        "quantity": Decimal("0"),
                        "taxable_value": Decimal("0"),
                        "cgst_amount": Decimal("0"),
                        "sgst_amount": Decimal("0"),
                        "igst_amount": Decimal("0"),
                        "cess_amount": Decimal("0"),
                    },
                )
                bucket["quantity"] += item.quantity
                bucket["taxable_value"] += item.taxable_value
                bucket["cgst_amount"] += item.cgst_amount
                bucket["sgst_amount"] += item.sgst_amount
                bucket["igst_amount"] += item.igst_amount
                bucket["cess_amount"] += item.cess_amount

        rows = []
        for (hsn_sac, rate), bucket in sorted(groups.items(), key=lambda kv: (kv[0][0] or "", kv[0][1])):
            total_tax = (
                bucket["cgst_amount"] + bucket["sgst_amount"] + bucket["igst_amount"] + bucket["cess_amount"]
            )
            rows.append(
                GSTR1HSNRow(
                    hsn_sac=hsn_sac,
                    description=bucket["description"],
                    uqc=bucket["uqc"],
                    tax_rate=rate,
                    quantity=bucket["quantity"],
                    taxable_value=bucket["taxable_value"],
                    cgst_amount=bucket["cgst_amount"],
                    sgst_amount=bucket["sgst_amount"],
                    igst_amount=bucket["igst_amount"],
                    cess_amount=bucket["cess_amount"],
                    total_value=bucket["taxable_value"] + total_tax,
                )
            )
        return rows

    async def get_document_summary(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID
    ) -> list[GSTR1DocumentSummaryRow]:
        period = await self._get_period(company_id, return_period_id)

        rows = []
        for label, model, date_field_name in (
            ("Sales Invoice", SalesInvoice, "invoice_date"),
            ("Credit Note", CreditNote, "credit_note_date"),
            ("Debit Note", DebitNote, "debit_note_date"),
        ):
            if model is SalesInvoice:
                records = await self.repo.list_sales_invoices(
                    company_id, period.period_start, period.period_end, statuses=ALL_STATUSES
                )
            else:
                records = await self.repo.list_notes(
                    model, company_id, period.period_start, period.period_end, statuses=ALL_STATUSES
                )
            total = len(records)
            cancelled = sum(1 for r in records if r.status == TransactionStatus.CANCELLED)
            rows.append(
                GSTR1DocumentSummaryRow(
                    document_type=label,
                    total_count=total,
                    cancelled_count=cancelled,
                    net_count=total - cancelled,
                )
            )
        return rows

    async def validate(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID
    ) -> list[GSTValidationFinding]:
        data = await self._prepare(company_id, return_period_id)
        findings: list[GSTValidationFinding] = []
        seen_invoice_numbers: set[str] = set()

        for c in data.classified:
            invoice = c.invoice
            entity_id = str(invoice.id)

            if invoice.invoice_number in seen_invoice_numbers:
                findings.append(
                    make_finding(
                        code="DUPLICATE_INVOICE",
                        severity=ValidationSeverity.ERROR,
                        entity="SalesInvoice",
                        entity_id=entity_id,
                        message=f"Invoice number '{invoice.invoice_number}' appears more than once",
                    )
                )
            seen_invoice_numbers.add(invoice.invoice_number)

            findings.extend(
                GSTValidationService.validate_place_of_supply(
                    invoice.place_of_supply_state_code, entity="SalesInvoice", entity_id=entity_id
                )
            )
            findings.extend(
                GSTValidationService.validate_non_negative_amounts(
                    {
                        "taxable_amount": invoice.taxable_amount,
                        "cgst_amount": invoice.cgst_amount,
                        "sgst_amount": invoice.sgst_amount,
                        "igst_amount": invoice.igst_amount,
                        "cess_amount": invoice.cess_amount,
                    },
                    entity="SalesInvoice",
                    entity_id=entity_id,
                )
            )
            findings.extend(
                GSTValidationService.check_review_required(
                    c.category, entity="SalesInvoice", entity_id=entity_id
                )
            )
            if c.category == GSTTransactionCategory.B2B:
                findings.extend(
                    GSTValidationService.validate_gstin_field(
                        invoice.customer.gstin if invoice.customer else None,
                        required=True,
                        entity="SalesInvoice",
                        entity_id=entity_id,
                    )
                )

        hsn_rows = await self.get_hsn_summary(company_id, return_period_id)
        for row in hsn_rows:
            if not row.hsn_sac:
                findings.append(
                    make_finding(
                        code="MISSING_HSN_SAC",
                        severity=ValidationSeverity.WARNING,
                        entity="GSTR1HSNGroup",
                        entity_id=f"rate-{row.tax_rate}",
                        message="One or more line items in this rate group have no HSN/SAC code",
                    )
                )

        return findings

    async def get_overview(
        self, company_id: uuid.UUID, return_period_id: uuid.UUID
    ) -> GSTR1Overview:
        data = await self._prepare(company_id, return_period_id)
        b2b = [c for c in data.classified if c.category == GSTTransactionCategory.B2B]
        b2c_large = [c for c in data.classified if self._is_b2c_large(c)]
        b2c_others = [
            c
            for c in data.classified
            if c.category == GSTTransactionCategory.B2C and not self._is_b2c_large(c)
        ]
        findings = await self.validate(company_id, return_period_id)

        taxable_value = sum((c.invoice.taxable_amount for c in b2b + b2c_large + b2c_others), Decimal("0"))
        cgst = sum((c.invoice.cgst_amount for c in b2b + b2c_large + b2c_others), Decimal("0"))
        sgst = sum((c.invoice.sgst_amount for c in b2b + b2c_large + b2c_others), Decimal("0"))
        igst = sum((c.invoice.igst_amount for c in b2b + b2c_large + b2c_others), Decimal("0"))
        cess = sum((c.invoice.cess_amount for c in b2b + b2c_large + b2c_others), Decimal("0"))

        return GSTR1Overview(
            return_period_id=return_period_id,
            b2b_invoice_count=len(b2b),
            b2c_large_invoice_count=len(b2c_large),
            b2c_others_invoice_count=len(b2c_others),
            export_count=0,
            credit_note_count=len(data.credit_notes),
            debit_note_count=len(data.debit_notes),
            taxable_value=taxable_value,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=igst,
            cess_amount=cess,
            error_count=sum(1 for f in findings if f.severity == ValidationSeverity.ERROR),
            warning_count=sum(1 for f in findings if f.severity == ValidationSeverity.WARNING),
        )
