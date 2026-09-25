import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_finding import AuditFinding
from app.models.bank_transaction import BankTransaction
from app.models.compliance_obligation import ComplianceObligation
from app.models.customer import Customer
from app.models.document import Document
from app.models.ledger import Ledger
from app.models.payment import Payment
from app.models.purchase_invoice import PurchaseInvoice
from app.models.receipt import Receipt
from app.models.sales_invoice import SalesInvoice
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.search import SearchResponse, SearchResultItem


class SearchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search(
        self,
        company_id: uuid.UUID,
        query: str,
        current_user: User,
        role_code: str,
        *,
        type_filter: str | None = None,
        limit: int = 25,
    ) -> SearchResponse:
        q = query.strip()
        if not q:
            return SearchResponse(query=query, total=0, items=[])

        pattern = f"%{q}%"
        results: list[SearchResultItem] = []

        # 1. Customers
        if not type_filter or type_filter.upper() == "CUSTOMER":
            cust_stmt = (
                select(Customer)
                .where(
                    Customer.company_id == company_id,
                    or_(
                        Customer.name.ilike(pattern),
                        Customer.gstin.ilike(pattern),
                        Customer.pan.ilike(pattern),
                        Customer.code.ilike(pattern),
                    ),
                )
                .limit(limit)
            )
            for c in (await self.db.execute(cust_stmt)).scalars().all():
                results.append(
                    SearchResultItem(
                        id=str(c.id),
                        type="CUSTOMER",
                        identifier=c.code or c.name,
                        title=c.name,
                        subtitle=f"GSTIN: {c.gstin}" if c.gstin else (f"PAN: {c.pan}" if c.pan else None),
                        status="ACTIVE" if c.is_active else "INACTIVE",
                        target_url="/accounting/customers",
                    )
                )

        # 2. Vendors
        if not type_filter or type_filter.upper() == "VENDOR":
            vend_stmt = (
                select(Vendor)
                .where(
                    Vendor.company_id == company_id,
                    or_(
                        Vendor.name.ilike(pattern),
                        Vendor.gstin.ilike(pattern),
                        Vendor.pan.ilike(pattern),
                        Vendor.code.ilike(pattern),
                    ),
                )
                .limit(limit)
            )
            for v in (await self.db.execute(vend_stmt)).scalars().all():
                results.append(
                    SearchResultItem(
                        id=str(v.id),
                        type="VENDOR",
                        identifier=v.code or v.name,
                        title=v.name,
                        subtitle=f"GSTIN: {v.gstin}" if v.gstin else (f"PAN: {v.pan}" if v.pan else None),
                        status="ACTIVE" if v.is_active else "INACTIVE",
                        target_url="/accounting/vendors",
                    )
                )

        # 3. Sales Invoices
        if not type_filter or type_filter.upper() in ("SALES_INVOICE", "INVOICE"):
            inv_stmt = (
                select(SalesInvoice)
                .where(
                    SalesInvoice.company_id == company_id,
                    SalesInvoice.invoice_number.ilike(pattern),
                )
                .limit(limit)
            )
            for inv in (await self.db.execute(inv_stmt)).scalars().all():
                results.append(
                    SearchResultItem(
                        id=str(inv.id),
                        type="SALES_INVOICE",
                        identifier=inv.invoice_number,
                        title=f"Sales Invoice #{inv.invoice_number}",
                        subtitle=f"Date: {inv.invoice_date}",
                        status=str(inv.status),
                        date=str(inv.invoice_date),
                        amount=inv.grand_total,
                        target_url=f"/accounting/sales-invoices/{inv.id}",
                    )
                )

        # 4. Purchase Invoices
        if not type_filter or type_filter.upper() in ("PURCHASE_INVOICE", "BILL"):
            pinv_stmt = (
                select(PurchaseInvoice)
                .where(
                    PurchaseInvoice.company_id == company_id,
                    or_(
                        PurchaseInvoice.invoice_number.ilike(pattern),
                        PurchaseInvoice.supplier_invoice_number.ilike(pattern),
                    ),
                )
                .limit(limit)
            )
            for pinv in (await self.db.execute(pinv_stmt)).scalars().all():
                results.append(
                    SearchResultItem(
                        id=str(pinv.id),
                        type="PURCHASE_INVOICE",
                        identifier=pinv.invoice_number,
                        title=f"Purchase Bill #{pinv.invoice_number}",
                        subtitle=f"Date: {pinv.invoice_date}",
                        status=str(pinv.status),
                        date=str(pinv.invoice_date),
                        amount=pinv.grand_total,
                        target_url=f"/accounting/purchase-invoices/{pinv.id}",
                    )
                )

        # 5. Receipts
        if not type_filter or type_filter.upper() == "RECEIPT":
            rec_stmt = (
                select(Receipt)
                .where(
                    Receipt.company_id == company_id,
                    or_(
                        Receipt.receipt_number.ilike(pattern),
                        Receipt.reference_number.ilike(pattern),
                        Receipt.notes.ilike(pattern),
                    ),
                )
                .limit(limit)
            )
            for rec in (await self.db.execute(rec_stmt)).scalars().all():
                results.append(
                    SearchResultItem(
                        id=str(rec.id),
                        type="RECEIPT",
                        identifier=rec.receipt_number,
                        title=f"Receipt #{rec.receipt_number}",
                        subtitle=f"Ref: {rec.reference_number}" if rec.reference_number else f"Mode: {rec.payment_mode}",
                        date=str(rec.receipt_date),
                        amount=rec.amount,
                        target_url="/accounting/transactions",
                    )
                )

        # 6. Payments
        if not type_filter or type_filter.upper() == "PAYMENT":
            pay_stmt = (
                select(Payment)
                .where(
                    Payment.company_id == company_id,
                    or_(
                        Payment.payment_number.ilike(pattern),
                        Payment.reference_number.ilike(pattern),
                        Payment.notes.ilike(pattern),
                    ),
                )
                .limit(limit)
            )
            for pay in (await self.db.execute(pay_stmt)).scalars().all():
                results.append(
                    SearchResultItem(
                        id=str(pay.id),
                        type="PAYMENT",
                        identifier=pay.payment_number,
                        title=f"Payment #{pay.payment_number}",
                        subtitle=f"Ref: {pay.reference_number}" if pay.reference_number else f"Mode: {pay.payment_mode}",
                        date=str(pay.payment_date),
                        amount=pay.amount,
                        target_url="/accounting/transactions",
                    )
                )

        # 7. Ledgers
        if not type_filter or type_filter.upper() == "LEDGER":
            led_stmt = (
                select(Ledger)
                .where(
                    Ledger.company_id == company_id,
                    or_(
                        Ledger.name.ilike(pattern),
                        Ledger.code.ilike(pattern),
                    ),
                )
                .limit(limit)
            )
            for led in (await self.db.execute(led_stmt)).scalars().all():
                results.append(
                    SearchResultItem(
                        id=str(led.id),
                        type="LEDGER",
                        identifier=led.code or led.name,
                        title=led.name,
                        subtitle=f"Type: {led.ledger_type}",
                        status="ACTIVE" if led.is_active else "INACTIVE",
                        target_url="/accounting/ledgers",
                    )
                )

        # 8. Documents
        if not type_filter or type_filter.upper() == "DOCUMENT":
            doc_stmt = (
                select(Document)
                .where(
                    Document.company_id == company_id,
                    Document.original_filename.ilike(pattern),
                )
                .limit(limit)
            )
            for doc in (await self.db.execute(doc_stmt)).scalars().all():
                results.append(
                    SearchResultItem(
                        id=str(doc.id),
                        type="DOCUMENT",
                        identifier=doc.original_filename,
                        title=doc.original_filename,
                        subtitle=f"Category: {doc.category}",
                        status=str(doc.status),
                        date=str(doc.created_at.date()),
                        target_url="/documents",
                    )
                )

        # 9. Bank Transactions
        if not type_filter or type_filter.upper() == "BANK_TRANSACTION":
            btx_stmt = (
                select(BankTransaction)
                .where(
                    BankTransaction.company_id == company_id,
                    or_(
                        BankTransaction.description.ilike(pattern),
                        BankTransaction.reference_number.ilike(pattern),
                    ),
                )
                .limit(limit)
            )
            for btx in (await self.db.execute(btx_stmt)).scalars().all():
                results.append(
                    SearchResultItem(
                        id=str(btx.id),
                        type="BANK_TRANSACTION",
                        identifier=btx.reference_number or str(btx.id)[:8],
                        title=btx.description[:60],
                        subtitle=f"{btx.transaction_type} · {btx.transaction_date}",
                        status=str(btx.reconciliation_status),
                        date=str(btx.transaction_date),
                        amount=btx.amount,
                        target_url="/bank/transactions",
                    )
                )

        # 10. Audit Findings
        if not type_filter or type_filter.upper() == "AUDIT_FINDING":
            af_stmt = (
                select(AuditFinding)
                .where(
                    AuditFinding.company_id == company_id,
                    or_(
                        AuditFinding.title.ilike(pattern),
                        AuditFinding.finding_code.ilike(pattern),
                        AuditFinding.description.ilike(pattern),
                    ),
                )
                .limit(limit)
            )
            for af in (await self.db.execute(af_stmt)).scalars().all():
                results.append(
                    SearchResultItem(
                        id=str(af.id),
                        type="AUDIT_FINDING",
                        identifier=af.finding_code or "FINDING",
                        title=f"Finding: {af.title}",
                        subtitle=f"Severity: {af.severity} · Category: {af.category}",
                        status=str(af.status),
                        date=str(af.created_at.date()),
                        target_url=f"/audits/engagements/{af.engagement_id}",
                    )
                )

        # 11. Compliance Obligations
        if not type_filter or type_filter.upper() == "COMPLIANCE_OBLIGATION":
            co_stmt = (
                select(ComplianceObligation)
                .where(
                    ComplianceObligation.company_id == company_id,
                    or_(
                        ComplianceObligation.name.ilike(pattern),
                        ComplianceObligation.code.ilike(pattern),
                    ),
                )
                .limit(limit)
            )
            for co in (await self.db.execute(co_stmt)).scalars().all():
                results.append(
                    SearchResultItem(
                        id=str(co.id),
                        type="COMPLIANCE_OBLIGATION",
                        identifier=co.code,
                        title=co.name,
                        subtitle=f"Module: {co.module} · Frequency: {co.frequency}",
                        status=str(co.status),
                        target_url="/compliance/obligations",
                    )
                )

        return SearchResponse(query=query, total=len(results), items=results[:limit])
