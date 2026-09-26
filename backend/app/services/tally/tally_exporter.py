import csv
from datetime import date
from decimal import Decimal
import io
import uuid
import xml.sax.saxutils as saxutils
from typing import Any

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ValidationAppError
from app.models.accounting_enums import BalanceType
from app.models.company import Company
from app.models.customer import Customer
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.ledger import Ledger
from app.models.payment import Payment
from app.models.purchase_invoice import PurchaseInvoice
from app.models.receipt import Receipt
from app.models.sales_invoice import SalesInvoice
from app.models.vendor import Vendor


def _xml_esc(val: Any) -> str:
    if val is None:
        return ""
    return saxutils.escape(str(val))


def _fmt_tally_date(d: date | None) -> str:
    if not d:
        return ""
    return d.strftime("%Y%m%d")


class TallyExporter:
    """Tally-compatible XML, CSV, and Excel exporter for TALLY TAX."""

    def __init__(self, db: AsyncSession, company_id: uuid.UUID) -> None:
        self.db = db
        self.company_id = company_id

    async def get_preview(
        self,
        financial_year_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        voucher_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Calculates count and total amount of exportable records."""
        types = voucher_types or ["SALES", "PURCHASE", "RECEIPT", "PAYMENT", "JOURNAL"]

        stats: dict[str, dict[str, Any]] = {}
        for t in types:
            stats[t] = {"count": 0, "amount": Decimal(0)}

        # Sales
        if "SALES" in types:
            q = select(SalesInvoice).where(SalesInvoice.company_id == self.company_id)
            if financial_year_id:
                q = q.where(SalesInvoice.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(SalesInvoice.invoice_date >= start_date)
            if end_date:
                q = q.where(SalesInvoice.invoice_date <= end_date)
            res = await self.db.execute(q)
            invoices = res.scalars().all()
            stats["SALES"]["count"] = len(invoices)
            stats["SALES"]["amount"] = sum((i.grand_total for i in invoices), Decimal(0))

        # Purchases
        if "PURCHASE" in types:
            q = select(PurchaseInvoice).where(PurchaseInvoice.company_id == self.company_id)
            if financial_year_id:
                q = q.where(PurchaseInvoice.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(PurchaseInvoice.invoice_date >= start_date)
            if end_date:
                q = q.where(PurchaseInvoice.invoice_date <= end_date)
            res = await self.db.execute(q)
            invoices = res.scalars().all()
            stats["PURCHASE"]["count"] = len(invoices)
            stats["PURCHASE"]["amount"] = sum((i.grand_total for i in invoices), Decimal(0))

        # Receipts
        if "RECEIPT" in types:
            q = select(Receipt).where(Receipt.company_id == self.company_id)
            if financial_year_id:
                q = q.where(Receipt.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(Receipt.receipt_date >= start_date)
            if end_date:
                q = q.where(Receipt.receipt_date <= end_date)
            res = await self.db.execute(q)
            recs = res.scalars().all()
            stats["RECEIPT"]["count"] = len(recs)
            stats["RECEIPT"]["amount"] = sum((r.amount for r in recs), Decimal(0))

        # Payments
        if "PAYMENT" in types:
            q = select(Payment).where(Payment.company_id == self.company_id)
            if financial_year_id:
                q = q.where(Payment.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(Payment.payment_date >= start_date)
            if end_date:
                q = q.where(Payment.payment_date <= end_date)
            res = await self.db.execute(q)
            pays = res.scalars().all()
            stats["PAYMENT"]["count"] = len(pays)
            stats["PAYMENT"]["amount"] = sum((p.amount for p in pays), Decimal(0))

        # Journals
        if "JOURNAL" in types:
            q = select(JournalEntry).options(selectinload(JournalEntry.lines)).where(JournalEntry.company_id == self.company_id)
            if financial_year_id:
                q = q.where(JournalEntry.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(JournalEntry.journal_date >= start_date)
            if end_date:
                q = q.where(JournalEntry.journal_date <= end_date)
            res = await self.db.execute(q)
            js = res.scalars().all()
            stats["JOURNAL"]["count"] = len(js)
            j_amt = Decimal(0)
            for j in js:
                j_amt += sum((l.debit_amount for l in j.lines), Decimal(0))
            stats["JOURNAL"]["amount"] = j_amt

        # Ledgers
        l_res = await self.db.execute(select(Ledger).where(Ledger.company_id == self.company_id))
        ledgers = l_res.scalars().all()

        total_vouchers = sum(s["count"] for s in stats.values())
        total_amt = sum(s["amount"] for s in stats.values())

        return {
            "total_vouchers": total_vouchers,
            "total_amount": float(total_amt),
            "total_ledgers": len(ledgers),
            "by_type": {k: {"count": v["count"], "amount": float(v["amount"])} for k, v in stats.items()},
        }

    async def export_xml(
        self,
        financial_year_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        voucher_types: list[str] | None = None,
    ) -> bytes:
        """Generates compliant Tally XML data envelope."""
        comp_res = await self.db.execute(select(Company).where(Company.id == self.company_id))
        company = comp_res.scalar_one_or_none()
        company_name = (company.legal_name or company.trade_name) if company else "Company"

        types = voucher_types or ["SALES", "PURCHASE", "RECEIPT", "PAYMENT", "JOURNAL"]

        xml_lines = [
            '<?xml version="1.0" encoding="utf-8"?>',
            '<ENVELOPE>',
            '  <HEADER>',
            '    <TALLYREQUEST>Export Data</TALLYREQUEST>',
            '  </HEADER>',
            '  <BODY>',
            '    <DATA>',
            '      <TALLYMESSAGE xmlns:UDF="TallyUDF">',
            '        <COMPANY>',
            '          <REMOTECMPINFO.LIST>',
            f'            <NAME>{_xml_esc(company_name)}</NAME>',
            '          </REMOTECMPINFO.LIST>',
            '        </COMPANY>',
            '      </TALLYMESSAGE>',
        ]

        # 1. Export Ledgers
        l_res = await self.db.execute(select(Ledger).where(Ledger.company_id == self.company_id))
        for ledger in l_res.scalars().all():
            xml_lines.extend([
                '      <TALLYMESSAGE>',
                f'        <LEDGER NAME="{_xml_esc(ledger.name)}" RESERVEDNAME="">',
                f'          <NAME>{_xml_esc(ledger.name)}</NAME>',
                f'          <PARENT>{_xml_esc(ledger.ledger_type.value)}</PARENT>',
                f'          <OPENINGBALANCE>{ledger.opening_balance}</OPENINGBALANCE>',
                '        </LEDGER>',
                '      </TALLYMESSAGE>',
            ])

        # 2. Export Sales Invoices
        if "SALES" in types:
            q = (
                select(SalesInvoice)
                .options(selectinload(SalesInvoice.customer), selectinload(SalesInvoice.items))
                .where(SalesInvoice.company_id == self.company_id)
            )
            if financial_year_id:
                q = q.where(SalesInvoice.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(SalesInvoice.invoice_date >= start_date)
            if end_date:
                q = q.where(SalesInvoice.invoice_date <= end_date)
            res = await self.db.execute(q)
            for inv in res.scalars().all():
                c_name = inv.customer.name if inv.customer else "Customer"
                date_str = _fmt_tally_date(inv.invoice_date)
                xml_lines.extend([
                    '      <TALLYMESSAGE>',
                    f'        <VOUCHER VOUCHERTYPENAME="Sales" ACTION="Create">',
                    f'          <DATE>{date_str}</DATE>',
                    f'          <VOUCHERNUMBER>{_xml_esc(inv.invoice_number)}</VOUCHERNUMBER>',
                    f'          <PARTYLEDGERNAME>{_xml_esc(c_name)}</PARTYLEDGERNAME>',
                    f'          <NARRATION>Sales Invoice {_xml_esc(inv.invoice_number)}</NARRATION>',
                    # Customer line (Debit)
                    '          <ALLLEDGERENTRIES.LIST>',
                    f'            <LEDGERNAME>{_xml_esc(c_name)}</LEDGERNAME>',
                    '            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
                    f'            <AMOUNT>-{inv.grand_total}</AMOUNT>',
                    '          </ALLLEDGERENTRIES.LIST>',
                    # Sales Revenue line (Credit)
                    '          <ALLLEDGERENTRIES.LIST>',
                    '            <LEDGERNAME>Sales Revenue</LEDGERNAME>',
                    '            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
                    f'            <AMOUNT>{inv.taxable_amount}</AMOUNT>',
                    '          </ALLLEDGERENTRIES.LIST>',
                ])
                # Tax lines
                if inv.cgst_amount > 0:
                    xml_lines.extend([
                        '          <ALLLEDGERENTRIES.LIST>',
                        '            <LEDGERNAME>Output CGST</LEDGERNAME>',
                        '            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
                        f'            <AMOUNT>{inv.cgst_amount}</AMOUNT>',
                        '          </ALLLEDGERENTRIES.LIST>',
                    ])
                if inv.sgst_amount > 0:
                    xml_lines.extend([
                        '          <ALLLEDGERENTRIES.LIST>',
                        '            <LEDGERNAME>Output SGST</LEDGERNAME>',
                        '            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
                        f'            <AMOUNT>{inv.sgst_amount}</AMOUNT>',
                        '          </ALLLEDGERENTRIES.LIST>',
                    ])
                if inv.igst_amount > 0:
                    xml_lines.extend([
                        '          <ALLLEDGERENTRIES.LIST>',
                        '            <LEDGERNAME>Output IGST</LEDGERNAME>',
                        '            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
                        f'            <AMOUNT>{inv.igst_amount}</AMOUNT>',
                        '          </ALLLEDGERENTRIES.LIST>',
                    ])
                xml_lines.extend([
                    '        </VOUCHER>',
                    '      </TALLYMESSAGE>',
                ])

        # 3. Export Purchase Invoices
        if "PURCHASE" in types:
            q = (
                select(PurchaseInvoice)
                .options(selectinload(PurchaseInvoice.vendor), selectinload(PurchaseInvoice.items))
                .where(PurchaseInvoice.company_id == self.company_id)
            )
            if financial_year_id:
                q = q.where(PurchaseInvoice.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(PurchaseInvoice.invoice_date >= start_date)
            if end_date:
                q = q.where(PurchaseInvoice.invoice_date <= end_date)
            res = await self.db.execute(q)
            for inv in res.scalars().all():
                v_name = inv.vendor.name if inv.vendor else "Vendor"
                date_str = _fmt_tally_date(inv.invoice_date)
                xml_lines.extend([
                    '      <TALLYMESSAGE>',
                    f'        <VOUCHER VOUCHERTYPENAME="Purchase" ACTION="Create">',
                    f'          <DATE>{date_str}</DATE>',
                    f'          <VOUCHERNUMBER>{_xml_esc(inv.invoice_number)}</VOUCHERNUMBER>',
                    f'          <PARTYLEDGERNAME>{_xml_esc(v_name)}</PARTYLEDGERNAME>',
                    f'          <NARRATION>Purchase Bill {_xml_esc(inv.invoice_number)}</NARRATION>',
                    # Expense line (Debit)
                    '          <ALLLEDGERENTRIES.LIST>',
                    '            <LEDGERNAME>Purchase Expense</LEDGERNAME>',
                    '            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
                    f'            <AMOUNT>-{inv.taxable_amount}</AMOUNT>',
                    '          </ALLLEDGERENTRIES.LIST>',
                ])
                if inv.cgst_amount > 0:
                    xml_lines.extend([
                        '          <ALLLEDGERENTRIES.LIST>',
                        '            <LEDGERNAME>Input CGST</LEDGERNAME>',
                        '            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
                        f'            <AMOUNT>-{inv.cgst_amount}</AMOUNT>',
                        '          </ALLLEDGERENTRIES.LIST>',
                    ])
                if inv.sgst_amount > 0:
                    xml_lines.extend([
                        '          <ALLLEDGERENTRIES.LIST>',
                        '            <LEDGERNAME>Input SGST</LEDGERNAME>',
                        '            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
                        f'            <AMOUNT>-{inv.sgst_amount}</AMOUNT>',
                        '          </ALLLEDGERENTRIES.LIST>',
                    ])
                if inv.igst_amount > 0:
                    xml_lines.extend([
                        '          <ALLLEDGERENTRIES.LIST>',
                        '            <LEDGERNAME>Input IGST</LEDGERNAME>',
                        '            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
                        f'            <AMOUNT>-{inv.igst_amount}</AMOUNT>',
                        '          </ALLLEDGERENTRIES.LIST>',
                    ])
                # Vendor line (Credit)
                xml_lines.extend([
                    '          <ALLLEDGERENTRIES.LIST>',
                    f'            <LEDGERNAME>{_xml_esc(v_name)}</LEDGERNAME>',
                    '            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
                    f'            <AMOUNT>{inv.grand_total}</AMOUNT>',
                    '          </ALLLEDGERENTRIES.LIST>',
                    '        </VOUCHER>',
                    '      </TALLYMESSAGE>',
                ])

        # 4. Export Receipts
        if "RECEIPT" in types:
            q = select(Receipt).options(selectinload(Receipt.customer), selectinload(Receipt.ledger)).where(Receipt.company_id == self.company_id)
            if financial_year_id:
                q = q.where(Receipt.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(Receipt.receipt_date >= start_date)
            if end_date:
                q = q.where(Receipt.receipt_date <= end_date)
            res = await self.db.execute(q)
            for rec in res.scalars().all():
                c_name = rec.customer.name if rec.customer else "Customer"
                l_name = rec.ledger.name if rec.ledger else "Bank Account"
                date_str = _fmt_tally_date(rec.receipt_date)
                xml_lines.extend([
                    '      <TALLYMESSAGE>',
                    '        <VOUCHER VOUCHERTYPENAME="Receipt" ACTION="Create">',
                    f'          <DATE>{date_str}</DATE>',
                    f'          <VOUCHERNUMBER>{_xml_esc(rec.receipt_number)}</VOUCHERNUMBER>',
                    f'          <PARTYLEDGERNAME>{_xml_esc(c_name)}</PARTYLEDGERNAME>',
                    # Bank line (Debit)
                    '          <ALLLEDGERENTRIES.LIST>',
                    f'            <LEDGERNAME>{_xml_esc(l_name)}</LEDGERNAME>',
                    '            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
                    f'            <AMOUNT>-{rec.amount}</AMOUNT>',
                    '          </ALLLEDGERENTRIES.LIST>',
                    # Customer line (Credit)
                    '          <ALLLEDGERENTRIES.LIST>',
                    f'            <LEDGERNAME>{_xml_esc(c_name)}</LEDGERNAME>',
                    '            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
                    f'            <AMOUNT>{rec.amount}</AMOUNT>',
                    '          </ALLLEDGERENTRIES.LIST>',
                    '        </VOUCHER>',
                    '      </TALLYMESSAGE>',
                ])

        # 5. Export Payments
        if "PAYMENT" in types:
            q = select(Payment).options(selectinload(Payment.ledger)).where(Payment.company_id == self.company_id)
            if financial_year_id:
                q = q.where(Payment.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(Payment.payment_date >= start_date)
            if end_date:
                q = q.where(Payment.payment_date <= end_date)
            res = await self.db.execute(q)
            for pay in res.scalars().all():
                l_name = pay.ledger.name if pay.ledger else "Bank Account"
                date_str = _fmt_tally_date(pay.payment_date)
                xml_lines.extend([
                    '      <TALLYMESSAGE>',
                    '        <VOUCHER VOUCHERTYPENAME="Payment" ACTION="Create">',
                    f'          <DATE>{date_str}</DATE>',
                    f'          <VOUCHERNUMBER>{_xml_esc(pay.payment_number)}</VOUCHERNUMBER>',
                    # Expense / Vendor line (Debit)
                    '          <ALLLEDGERENTRIES.LIST>',
                    f'            <LEDGERNAME>{_xml_esc(pay.reference_number or "General Expense")}</LEDGERNAME>',
                    '            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
                    f'            <AMOUNT>-{pay.amount}</AMOUNT>',
                    '          </ALLLEDGERENTRIES.LIST>',
                    # Bank line (Credit)
                    '          <ALLLEDGERENTRIES.LIST>',
                    f'            <LEDGERNAME>{_xml_esc(l_name)}</LEDGERNAME>',
                    '            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
                    f'            <AMOUNT>{pay.amount}</AMOUNT>',
                    '          </ALLLEDGERENTRIES.LIST>',
                    '        </VOUCHER>',
                    '      </TALLYMESSAGE>',
                ])

        # 6. Export Journals
        if "JOURNAL" in types:
            q = select(JournalEntry).options(selectinload(JournalEntry.lines).selectinload(JournalEntryLine.ledger)).where(JournalEntry.company_id == self.company_id)
            if financial_year_id:
                q = q.where(JournalEntry.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(JournalEntry.journal_date >= start_date)
            if end_date:
                q = q.where(JournalEntry.journal_date <= end_date)
            res = await self.db.execute(q)
            for j in res.scalars().all():
                date_str = _fmt_tally_date(j.journal_date)
                xml_lines.extend([
                    '      <TALLYMESSAGE>',
                    '        <VOUCHER VOUCHERTYPENAME="Journal" ACTION="Create">',
                    f'          <DATE>{date_str}</DATE>',
                    f'          <VOUCHERNUMBER>{_xml_esc(j.journal_number)}</VOUCHERNUMBER>',
                    f'          <NARRATION>{_xml_esc(j.narration or "")}</NARRATION>',
                ])
                for line in j.lines:
                    l_name = line.ledger.name if line.ledger else "Ledger"
                    if line.debit_amount > 0:
                        xml_lines.extend([
                            '          <ALLLEDGERENTRIES.LIST>',
                            f'            <LEDGERNAME>{_xml_esc(l_name)}</LEDGERNAME>',
                            '            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
                            f'            <AMOUNT>-{line.debit_amount}</AMOUNT>',
                            '          </ALLLEDGERENTRIES.LIST>',
                        ])
                    else:
                        xml_lines.extend([
                            '          <ALLLEDGERENTRIES.LIST>',
                            f'            <LEDGERNAME>{_xml_esc(l_name)}</LEDGERNAME>',
                            '            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
                            f'            <AMOUNT>{line.credit_amount}</AMOUNT>',
                            '          </ALLLEDGERENTRIES.LIST>',
                        ])
                xml_lines.extend([
                    '        </VOUCHER>',
                    '      </TALLYMESSAGE>',
                ])

        xml_lines.extend([
            '    </DATA>',
            '  </BODY>',
            '</ENVELOPE>',
        ])

        return "\n".join(xml_lines).encode("utf-8")

    async def export_csv(
        self,
        financial_year_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        voucher_types: list[str] | None = None,
    ) -> bytes:
        """Exports Tally-compatible Daybook CSV format."""
        types = voucher_types or ["SALES", "PURCHASE", "RECEIPT", "PAYMENT", "JOURNAL"]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Voucher Type", "Voucher No", "Particulars", "Debit Amount", "Credit Amount", "Narration"])

        # Sales
        if "SALES" in types:
            q = select(SalesInvoice).options(selectinload(SalesInvoice.customer)).where(SalesInvoice.company_id == self.company_id)
            if financial_year_id:
                q = q.where(SalesInvoice.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(SalesInvoice.invoice_date >= start_date)
            if end_date:
                q = q.where(SalesInvoice.invoice_date <= end_date)
            res = await self.db.execute(q)
            for inv in res.scalars().all():
                c_name = inv.customer.name if inv.customer else "Customer"
                writer.writerow([inv.invoice_date.isoformat(), "Sales", inv.invoice_number, c_name, inv.grand_total, "", "Sales Invoice"])
                writer.writerow([inv.invoice_date.isoformat(), "Sales", inv.invoice_number, "Sales Revenue", "", inv.taxable_amount, ""])
                if inv.total_tax > 0:
                    writer.writerow([inv.invoice_date.isoformat(), "Sales", inv.invoice_number, "GST Output", "", inv.total_tax, ""])

        # Purchases
        if "PURCHASE" in types:
            q = select(PurchaseInvoice).options(selectinload(PurchaseInvoice.vendor)).where(PurchaseInvoice.company_id == self.company_id)
            if financial_year_id:
                q = q.where(PurchaseInvoice.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(PurchaseInvoice.invoice_date >= start_date)
            if end_date:
                q = q.where(PurchaseInvoice.invoice_date <= end_date)
            res = await self.db.execute(q)
            for inv in res.scalars().all():
                v_name = inv.vendor.name if inv.vendor else "Vendor"
                writer.writerow([inv.invoice_date.isoformat(), "Purchase", inv.invoice_number, "Purchase Expense", inv.taxable_amount, "", ""])
                if inv.total_tax > 0:
                    writer.writerow([inv.invoice_date.isoformat(), "Purchase", inv.invoice_number, "GST Input", inv.total_tax, "", ""])
                writer.writerow([inv.invoice_date.isoformat(), "Purchase", inv.invoice_number, v_name, "", inv.grand_total, "Purchase Bill"])

        # Receipts
        if "RECEIPT" in types:
            q = select(Receipt).options(selectinload(Receipt.customer), selectinload(Receipt.ledger)).where(Receipt.company_id == self.company_id)
            if financial_year_id:
                q = q.where(Receipt.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(Receipt.receipt_date >= start_date)
            if end_date:
                q = q.where(Receipt.receipt_date <= end_date)
            res = await self.db.execute(q)
            for rec in res.scalars().all():
                c_name = rec.customer.name if rec.customer else "Customer"
                l_name = rec.ledger.name if rec.ledger else "Bank"
                writer.writerow([rec.receipt_date.isoformat(), "Receipt", rec.receipt_number, l_name, rec.amount, "", "Receipt"])
                writer.writerow([rec.receipt_date.isoformat(), "Receipt", rec.receipt_number, c_name, "", rec.amount, ""])

        # Payments
        if "PAYMENT" in types:
            q = select(Payment).options(selectinload(Payment.ledger)).where(Payment.company_id == self.company_id)
            if financial_year_id:
                q = q.where(Payment.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(Payment.payment_date >= start_date)
            if end_date:
                q = q.where(Payment.payment_date <= end_date)
            res = await self.db.execute(q)
            for pay in res.scalars().all():
                l_name = pay.ledger.name if pay.ledger else "Bank"
                writer.writerow([pay.payment_date.isoformat(), "Payment", pay.payment_number, pay.reference_number or "Vendor Expense", pay.amount, "", "Payment"])
                writer.writerow([pay.payment_date.isoformat(), "Payment", pay.payment_number, l_name, "", pay.amount, ""])

        # Journals
        if "JOURNAL" in types:
            q = select(JournalEntry).options(selectinload(JournalEntry.lines).selectinload(JournalEntryLine.ledger)).where(JournalEntry.company_id == self.company_id)
            if financial_year_id:
                q = q.where(JournalEntry.financial_year_id == financial_year_id)
            if start_date:
                q = q.where(JournalEntry.journal_date >= start_date)
            if end_date:
                q = q.where(JournalEntry.journal_date <= end_date)
            res = await self.db.execute(q)
            for j in res.scalars().all():
                for line in j.lines:
                    l_name = line.ledger.name if line.ledger else "Ledger"
                    dr = line.debit_amount if line.debit_amount > 0 else ""
                    cr = line.credit_amount if line.credit_amount > 0 else ""
                    writer.writerow([j.journal_date.isoformat(), "Journal", j.journal_number, l_name, dr, cr, j.narration or ""])

        return output.getvalue().encode("utf-8")

    async def export_xlsx(
        self,
        financial_year_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        voucher_types: list[str] | None = None,
    ) -> bytes:
        """Exports Tally-compatible multi-sheet Excel workbook."""
        wb = Workbook()
        ws_daybook = wb.active
        ws_daybook.title = "Daybook"
        ws_daybook.append(["Date", "Voucher Type", "Voucher No", "Particulars", "Debit Amount", "Credit Amount", "Narration"])

        csv_bytes = await self.export_csv(financial_year_id, start_date, end_date, voucher_types)
        csv_text = csv_bytes.decode("utf-8")
        reader = csv.reader(io.StringIO(csv_text))
        next(reader)  # Skip header
        for row in reader:
            ws_daybook.append(row)

        # Ledgers sheet
        ws_ledgers = wb.create_sheet(title="Ledgers")
        ws_ledgers.append(["Ledger Name", "Type", "Opening Balance", "Debit/Credit"])
        l_res = await self.db.execute(select(Ledger).where(Ledger.company_id == self.company_id))
        for l in l_res.scalars().all():
            dr_cr = "Dr" if getattr(l, "opening_balance_type", None) == BalanceType.DEBIT else "Cr"
            ws_ledgers.append([l.name, l.ledger_type.value, float(l.opening_balance), dr_cr])

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
