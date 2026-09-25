"""§33 — basic accounting reports, deliberately not a full reporting
engine: server-side aggregation of data that already exists, nothing more.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting_enums import BalanceType, PartyType, TransactionStatus
from app.models.customer import Customer
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.ledger import Ledger
from app.models.payment import Payment
from app.models.purchase_invoice import PurchaseInvoice
from app.models.receipt import Receipt
from app.models.sales_invoice import SalesInvoice
from app.models.vendor import Vendor
from app.schemas.reports import LedgerBalance, PartyOutstanding, SalesPurchaseSummary, TrialBalance
from app.utils.export import ExportFile, ExportFormat, render_export

ZERO = Decimal("0")


class ReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def sales_summary(
        self, company_id: uuid.UUID, *, date_from: date | None, date_to: date | None
    ) -> SalesPurchaseSummary:
        query = select(
            func.count(SalesInvoice.id),
            func.coalesce(func.sum(SalesInvoice.taxable_amount), ZERO),
            func.coalesce(func.sum(SalesInvoice.cgst_amount), ZERO),
            func.coalesce(func.sum(SalesInvoice.sgst_amount), ZERO),
            func.coalesce(func.sum(SalesInvoice.igst_amount), ZERO),
            func.coalesce(func.sum(SalesInvoice.cess_amount), ZERO),
            func.coalesce(func.sum(SalesInvoice.total_tax), ZERO),
            func.coalesce(func.sum(SalesInvoice.grand_total), ZERO),
        ).where(SalesInvoice.company_id == company_id, SalesInvoice.status == TransactionStatus.POSTED)
        if date_from:
            query = query.where(SalesInvoice.invoice_date >= date_from)
        if date_to:
            query = query.where(SalesInvoice.invoice_date <= date_to)

        row = (await self.db.execute(query)).one()
        return SalesPurchaseSummary(
            date_from=date_from,
            date_to=date_to,
            invoice_count=row[0],
            taxable_amount=row[1],
            cgst_amount=row[2],
            sgst_amount=row[3],
            igst_amount=row[4],
            cess_amount=row[5],
            total_tax=row[6],
            grand_total=row[7],
        )

    async def purchase_summary(
        self, company_id: uuid.UUID, *, date_from: date | None, date_to: date | None
    ) -> SalesPurchaseSummary:
        query = select(
            func.count(PurchaseInvoice.id),
            func.coalesce(func.sum(PurchaseInvoice.taxable_amount), ZERO),
            func.coalesce(func.sum(PurchaseInvoice.cgst_amount), ZERO),
            func.coalesce(func.sum(PurchaseInvoice.sgst_amount), ZERO),
            func.coalesce(func.sum(PurchaseInvoice.igst_amount), ZERO),
            func.coalesce(func.sum(PurchaseInvoice.cess_amount), ZERO),
            func.coalesce(func.sum(PurchaseInvoice.total_tax), ZERO),
            func.coalesce(func.sum(PurchaseInvoice.grand_total), ZERO),
        ).where(
            PurchaseInvoice.company_id == company_id,
            PurchaseInvoice.status == TransactionStatus.POSTED,
        )
        if date_from:
            query = query.where(PurchaseInvoice.invoice_date >= date_from)
        if date_to:
            query = query.where(PurchaseInvoice.invoice_date <= date_to)

        row = (await self.db.execute(query)).one()
        return SalesPurchaseSummary(
            date_from=date_from,
            date_to=date_to,
            invoice_count=row[0],
            taxable_amount=row[1],
            cgst_amount=row[2],
            sgst_amount=row[3],
            igst_amount=row[4],
            cess_amount=row[5],
            total_tax=row[6],
            grand_total=row[7],
        )

    async def customer_outstanding(self, company_id: uuid.UUID) -> list[PartyOutstanding]:
        invoiced_query = (
            select(SalesInvoice.customer_id, func.coalesce(func.sum(SalesInvoice.grand_total), ZERO))
            .where(SalesInvoice.company_id == company_id, SalesInvoice.status == TransactionStatus.POSTED)
            .group_by(SalesInvoice.customer_id)
        )
        invoiced = dict((await self.db.execute(invoiced_query)).all())

        received_query = (
            select(Receipt.customer_id, func.coalesce(func.sum(Receipt.amount), ZERO))
            .where(Receipt.company_id == company_id, Receipt.status == TransactionStatus.POSTED)
            .group_by(Receipt.customer_id)
        )
        received = dict((await self.db.execute(received_query)).all())

        customer_ids = set(invoiced) | set(received)
        if not customer_ids:
            return []

        names_result = await self.db.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_(customer_ids))
        )
        names = dict(names_result.all())

        results = []
        for customer_id in customer_ids:
            inv = invoiced.get(customer_id, ZERO)
            rec = received.get(customer_id, ZERO)
            results.append(
                PartyOutstanding(
                    party_id=customer_id,
                    party_name=names.get(customer_id, "Unknown"),
                    invoiced_total=inv,
                    settled_total=rec,
                    outstanding=inv - rec,
                )
            )
        return sorted(results, key=lambda r: r.party_name)

    async def vendor_outstanding(self, company_id: uuid.UUID) -> list[PartyOutstanding]:
        invoiced_query = (
            select(PurchaseInvoice.vendor_id, func.coalesce(func.sum(PurchaseInvoice.grand_total), ZERO))
            .where(
                PurchaseInvoice.company_id == company_id,
                PurchaseInvoice.status == TransactionStatus.POSTED,
            )
            .group_by(PurchaseInvoice.vendor_id)
        )
        invoiced = dict((await self.db.execute(invoiced_query)).all())

        paid_query = (
            select(Payment.party_id, func.coalesce(func.sum(Payment.amount), ZERO))
            .where(
                Payment.company_id == company_id,
                Payment.status == TransactionStatus.POSTED,
                Payment.party_type == PartyType.VENDOR,
            )
            .group_by(Payment.party_id)
        )
        paid = dict((await self.db.execute(paid_query)).all())

        vendor_ids = set(invoiced) | set(paid)
        if not vendor_ids:
            return []

        names_result = await self.db.execute(
            select(Vendor.id, Vendor.name).where(Vendor.id.in_(vendor_ids))
        )
        names = dict(names_result.all())

        results = []
        for vendor_id in vendor_ids:
            inv = invoiced.get(vendor_id, ZERO)
            pay = paid.get(vendor_id, ZERO)
            results.append(
                PartyOutstanding(
                    party_id=vendor_id,
                    party_name=names.get(vendor_id, "Unknown"),
                    invoiced_total=inv,
                    settled_total=pay,
                    outstanding=inv - pay,
                )
            )
        return sorted(results, key=lambda r: r.party_name)

    async def trial_balance(self, company_id: uuid.UUID, *, as_of: date | None) -> TrialBalance:
        """Balance per ledger = opening balance + posted journal-line
        movement. Sales/Purchase invoices are not auto-posted to ledgers
        in Phase 3 (no auto-posting engine exists yet), so this reflects
        exactly what a real double-entry system has recorded through
        Ledgers and Journal Entries — an incomplete opening-balance setup
        will legitimately show as unbalanced here, which is useful
        information for the user, not something to paper over.
        """
        ledgers_result = await self.db.execute(
            select(Ledger).where(Ledger.company_id == company_id, Ledger.is_active.is_(True))
        )
        ledgers = list(ledgers_result.scalars().all())

        movement_query = (
            select(
                JournalEntryLine.ledger_id,
                func.coalesce(func.sum(JournalEntryLine.debit_amount), ZERO),
                func.coalesce(func.sum(JournalEntryLine.credit_amount), ZERO),
            )
            .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
            .where(JournalEntry.company_id == company_id, JournalEntry.status == TransactionStatus.POSTED)
        )
        if as_of:
            movement_query = movement_query.where(JournalEntry.journal_date <= as_of)
        movement_query = movement_query.group_by(JournalEntryLine.ledger_id)

        movement_rows = (await self.db.execute(movement_query)).all()
        movement = {row[0]: (row[1], row[2]) for row in movement_rows}

        lines = []
        total_debit = ZERO
        total_credit = ZERO
        for ledger in ledgers:
            debit_move, credit_move = movement.get(ledger.id, (ZERO, ZERO))
            opening_debit = ledger.opening_balance if ledger.opening_balance_type == BalanceType.DEBIT else ZERO
            opening_credit = ledger.opening_balance if ledger.opening_balance_type == BalanceType.CREDIT else ZERO

            debit = opening_debit + debit_move
            credit = opening_credit + credit_move
            net = debit - credit

            if net == ZERO and debit == ZERO and credit == ZERO:
                continue

            balance_type = BalanceType.DEBIT if net >= 0 else BalanceType.CREDIT
            lines.append(
                LedgerBalance(
                    ledger_id=ledger.id,
                    ledger_name=ledger.name,
                    ledger_type=ledger.ledger_type.value,
                    debit=debit,
                    credit=credit,
                    balance=abs(net),
                    balance_type=balance_type,
                )
            )
            total_debit += debit
            total_credit += credit

        return TrialBalance(
            as_of=as_of,
            lines=sorted(lines, key=lambda entry_line: entry_line.ledger_name),
            total_debit=total_debit,
            total_credit=total_credit,
            is_balanced=(total_debit == total_credit),
        )

    async def export_sales_register(
        self,
        company_id: uuid.UUID,
        fmt: ExportFormat,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> ExportFile:
        query = (
            select(SalesInvoice, Customer.name, Customer.gstin)
            .join(Customer, Customer.id == SalesInvoice.customer_id)
            .where(SalesInvoice.company_id == company_id)
            .order_by(SalesInvoice.invoice_date.desc(), SalesInvoice.invoice_number.desc())
        )
        if date_from:
            query = query.where(SalesInvoice.invoice_date >= date_from)
        if date_to:
            query = query.where(SalesInvoice.invoice_date <= date_to)

        result = await self.db.execute(query)
        rows_data = result.all()

        headers = [
            "Invoice Number",
            "Invoice Date",
            "Customer Name",
            "Customer GSTIN",
            "Place of Supply",
            "Status",
            "Taxable Amount",
            "CGST",
            "SGST",
            "IGST",
            "Cess",
            "Total Tax",
            "Grand Total",
        ]
        rows = []
        for inv, cust_name, cust_gstin in rows_data:
            rows.append([
                inv.invoice_number,
                inv.invoice_date,
                cust_name or "",
                cust_gstin or "",
                inv.place_of_supply or "",
                inv.status.value if hasattr(inv.status, "value") else str(inv.status),
                inv.taxable_amount,
                inv.cgst_amount,
                inv.sgst_amount,
                inv.igst_amount,
                inv.cess_amount,
                inv.total_tax,
                inv.grand_total,
            ])

        return render_export(
            headers=headers,
            rows=rows,
            title="Sales Register",
            fmt=fmt,
            filename_stub=f"sales_register_{company_id}_{date.today().isoformat()}",
            sheet_name="Sales Register",
        )

    async def export_purchase_register(
        self,
        company_id: uuid.UUID,
        fmt: ExportFormat,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> ExportFile:
        query = (
            select(PurchaseInvoice, Vendor.name, Vendor.gstin)
            .join(Vendor, Vendor.id == PurchaseInvoice.vendor_id)
            .where(PurchaseInvoice.company_id == company_id)
            .order_by(PurchaseInvoice.invoice_date.desc(), PurchaseInvoice.invoice_number.desc())
        )
        if date_from:
            query = query.where(PurchaseInvoice.invoice_date >= date_from)
        if date_to:
            query = query.where(PurchaseInvoice.invoice_date <= date_to)

        result = await self.db.execute(query)
        rows_data = result.all()

        headers = [
            "Invoice Number",
            "Invoice Date",
            "Supplier Invoice Number",
            "Supplier Invoice Date",
            "Vendor Name",
            "Vendor GSTIN",
            "Place of Supply",
            "Status",
            "Taxable Amount",
            "CGST",
            "SGST",
            "IGST",
            "Cess",
            "Total Tax",
            "Grand Total",
        ]
        rows = []
        for inv, vend_name, vend_gstin in rows_data:
            rows.append([
                inv.invoice_number,
                inv.invoice_date,
                inv.supplier_invoice_number or "",
                inv.supplier_invoice_date or "",
                vend_name or "",
                vend_gstin or "",
                inv.place_of_supply or "",
                inv.status.value if hasattr(inv.status, "value") else str(inv.status),
                inv.taxable_amount,
                inv.cgst_amount,
                inv.sgst_amount,
                inv.igst_amount,
                inv.cess_amount,
                inv.total_tax,
                inv.grand_total,
            ])

        return render_export(
            headers=headers,
            rows=rows,
            title="Purchase Register",
            fmt=fmt,
            filename_stub=f"purchase_register_{company_id}_{date.today().isoformat()}",
            sheet_name="Purchase Register",
        )

    async def export_trial_balance(
        self,
        company_id: uuid.UUID,
        fmt: ExportFormat,
        *,
        as_of: date | None = None,
    ) -> ExportFile:
        tb = await self.trial_balance(company_id, as_of=as_of)

        headers = [
            "Ledger Name",
            "Ledger Type",
            "Debit",
            "Credit",
            "Balance",
            "Balance Type",
        ]
        rows = []
        for line in tb.lines:
            rows.append([
                line.ledger_name,
                line.ledger_type,
                line.debit,
                line.credit,
                line.balance,
                line.balance_type.value if hasattr(line.balance_type, "value") else str(line.balance_type),
            ])
        rows.append([
            "Total",
            "",
            tb.total_debit,
            tb.total_credit,
            abs(tb.total_debit - tb.total_credit),
            "BALANCED" if tb.is_balanced else "UNBALANCED",
        ])

        as_of_str = as_of.isoformat() if as_of else date.today().isoformat()
        return render_export(
            headers=headers,
            rows=rows,
            title=f"Trial Balance (As of {as_of_str})",
            fmt=fmt,
            filename_stub=f"trial_balance_{company_id}_{as_of_str}",
            sheet_name="Trial Balance",
        )

