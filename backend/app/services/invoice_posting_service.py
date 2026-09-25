"""Invoice posting service.

Automatically creates balanced, double-entry JournalEntry and
JournalEntryLine records when Sales Invoices and Purchase Invoices are posted,
and handles reversal / cancellation.
"""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ValidationAppError
from app.models.accounting_enums import BalanceType, DataSource, LedgerType, TransactionStatus
from app.models.customer import Customer
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.ledger import Ledger
from app.models.purchase_invoice import PurchaseInvoice
from app.models.sales_invoice import SalesInvoice
from app.models.user import User
from app.models.vendor import Vendor
from app.services.accounting_calculation_service import AccountingCalculationService
from app.services.accounting_guards import assert_date_in_financial_year, assert_period_open
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta

ZERO = Decimal("0")


class InvoicePostingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def _get_or_create_ledger(
        self,
        company_id: uuid.UUID,
        *,
        name: str,
        ledger_type: LedgerType,
        opening_balance_type: BalanceType = BalanceType.DEBIT,
    ) -> Ledger:
        """Find an existing active ledger by name or matching type, or create a standard one."""
        query = select(Ledger).where(
            Ledger.company_id == company_id,
            Ledger.name == name,
        )
        ledger = (await self.db.execute(query)).scalar_one_or_none()
        if ledger is not None:
            return ledger

        # If not found by exact name, look for any active ledger of the desired type
        type_query = select(Ledger).where(
            Ledger.company_id == company_id,
            Ledger.ledger_type == ledger_type,
            Ledger.is_active.is_(True),
        )
        existing_of_type = (await self.db.execute(type_query)).scalars().all()
        for cand in existing_of_type:
            if name.lower() in cand.name.lower() or cand.name.lower() in name.lower():
                return cand

        # Otherwise create a standard ledger
        new_ledger = Ledger(
            company_id=company_id,
            name=name,
            ledger_type=ledger_type,
            opening_balance_type=opening_balance_type,
            opening_balance=ZERO,
            is_active=True,
        )
        self.db.add(new_ledger)
        await self.db.flush()
        return new_ledger

    async def _resolve_customer_ledger(self, company_id: uuid.UUID, customer_id: uuid.UUID) -> Ledger:
        customer = (
            await self.db.execute(
                select(Customer).where(Customer.id == customer_id, Customer.company_id == company_id)
            )
        ).scalar_one_or_none()
        if customer:
            # Check if there is a ledger with the customer's name
            query = select(Ledger).where(
                Ledger.company_id == company_id,
                Ledger.name == customer.name,
                Ledger.is_active.is_(True),
            )
            cust_ledger = (await self.db.execute(query)).scalar_one_or_none()
            if cust_ledger:
                return cust_ledger

        # Otherwise resolve Accounts Receivable
        return await self._get_or_create_ledger(
            company_id,
            name="Accounts Receivable",
            ledger_type=LedgerType.RECEIVABLE,
            opening_balance_type=BalanceType.DEBIT,
        )

    async def _resolve_vendor_ledger(self, company_id: uuid.UUID, vendor_id: uuid.UUID) -> Ledger:
        vendor = (
            await self.db.execute(
                select(Vendor).where(Vendor.id == vendor_id, Vendor.company_id == company_id)
            )
        ).scalar_one_or_none()
        if vendor:
            # Check if there is a ledger with the vendor's name
            query = select(Ledger).where(
                Ledger.company_id == company_id,
                Ledger.name == vendor.name,
                Ledger.is_active.is_(True),
            )
            vend_ledger = (await self.db.execute(query)).scalar_one_or_none()
            if vend_ledger:
                return vend_ledger

        # Otherwise resolve Accounts Payable
        return await self._get_or_create_ledger(
            company_id,
            name="Accounts Payable",
            ledger_type=LedgerType.PAYABLE,
            opening_balance_type=BalanceType.CREDIT,
        )

    async def _generate_unique_journal_number(
        self, company_id: uuid.UUID, financial_year_id: uuid.UUID, prefix: str
    ) -> str:
        candidate = prefix
        counter = 1
        while True:
            exists = (
                await self.db.execute(
                    select(JournalEntry.id).where(
                        JournalEntry.company_id == company_id,
                        JournalEntry.financial_year_id == financial_year_id,
                        JournalEntry.journal_number == candidate,
                    )
                )
            ).scalar_one_or_none()
            if not exists:
                return candidate
            candidate = f"{prefix}-{counter}"
            counter += 1

    async def post_sales_invoice(
        self, company_id: uuid.UUID, invoice: SalesInvoice, current_user: User, meta: RequestMeta
    ) -> JournalEntry:
        source_ref = f"sales_invoice:{invoice.id}"
        existing_journal = (
            await self.db.execute(
                select(JournalEntry).where(
                    JournalEntry.company_id == company_id,
                    JournalEntry.source_reference == source_ref,
                    JournalEntry.status == TransactionStatus.POSTED,
                )
            )
        ).scalar_one_or_none()
        if existing_journal is not None:
            raise ConflictError(
                "A posted journal entry already exists for this sales invoice",
                code="ALREADY_POSTED",
            )

        # Resolve ledgers
        cust_ledger = await self._resolve_customer_ledger(company_id, invoice.customer_id)
        sales_ledger = await self._get_or_create_ledger(
            company_id,
            name="Sales Account",
            ledger_type=LedgerType.INCOME,
            opening_balance_type=BalanceType.CREDIT,
        )

        lines: list[JournalEntryLine] = []

        # 1. Debit Customer Receivable for Grand Total
        lines.append(
            JournalEntryLine(
                ledger_id=cust_ledger.id,
                debit_amount=invoice.grand_total,
                credit_amount=ZERO,
                description=f"Receivable for invoice {invoice.invoice_number}",
            )
        )

        # 2. Credit Sales Revenue for Taxable Amount
        lines.append(
            JournalEntryLine(
                ledger_id=sales_ledger.id,
                debit_amount=ZERO,
                credit_amount=invoice.taxable_amount,
                description=f"Revenue for invoice {invoice.invoice_number}",
            )
        )

        # 3. Credit Output Taxes
        if invoice.cgst_amount > ZERO:
            cgst_ledger = await self._get_or_create_ledger(
                company_id,
                name="Output CGST",
                ledger_type=LedgerType.TAX,
                opening_balance_type=BalanceType.CREDIT,
            )
            lines.append(
                JournalEntryLine(
                    ledger_id=cgst_ledger.id,
                    debit_amount=ZERO,
                    credit_amount=invoice.cgst_amount,
                    description=f"Output CGST on invoice {invoice.invoice_number}",
                )
            )

        if invoice.sgst_amount > ZERO:
            sgst_ledger = await self._get_or_create_ledger(
                company_id,
                name="Output SGST",
                ledger_type=LedgerType.TAX,
                opening_balance_type=BalanceType.CREDIT,
            )
            lines.append(
                JournalEntryLine(
                    ledger_id=sgst_ledger.id,
                    debit_amount=ZERO,
                    credit_amount=invoice.sgst_amount,
                    description=f"Output SGST on invoice {invoice.invoice_number}",
                )
            )

        if invoice.igst_amount > ZERO:
            igst_ledger = await self._get_or_create_ledger(
                company_id,
                name="Output IGST",
                ledger_type=LedgerType.TAX,
                opening_balance_type=BalanceType.CREDIT,
            )
            lines.append(
                JournalEntryLine(
                    ledger_id=igst_ledger.id,
                    debit_amount=ZERO,
                    credit_amount=invoice.igst_amount,
                    description=f"Output IGST on invoice {invoice.invoice_number}",
                )
            )

        if invoice.cess_amount > ZERO:
            cess_ledger = await self._get_or_create_ledger(
                company_id,
                name="Output Cess",
                ledger_type=LedgerType.TAX,
                opening_balance_type=BalanceType.CREDIT,
            )
            lines.append(
                JournalEntryLine(
                    ledger_id=cess_ledger.id,
                    debit_amount=ZERO,
                    credit_amount=invoice.cess_amount,
                    description=f"Output Cess on invoice {invoice.invoice_number}",
                )
            )

        # 4. Handle Round Off
        if invoice.round_off != ZERO:
            round_off_ledger = await self._get_or_create_ledger(
                company_id,
                name="Round Off",
                ledger_type=LedgerType.EXPENSE,
                opening_balance_type=BalanceType.DEBIT,
            )
            if invoice.round_off < ZERO:
                # Round-off loss / expense -> Debit
                lines.append(
                    JournalEntryLine(
                        ledger_id=round_off_ledger.id,
                        debit_amount=abs(invoice.round_off),
                        credit_amount=ZERO,
                        description=f"Round off for invoice {invoice.invoice_number}",
                    )
                )
            else:
                # Round-off gain / income -> Credit
                lines.append(
                    JournalEntryLine(
                        ledger_id=round_off_ledger.id,
                        debit_amount=ZERO,
                        credit_amount=invoice.round_off,
                        description=f"Round off for invoice {invoice.invoice_number}",
                    )
                )

        # Validate balance
        total_debit = sum((line.debit_amount for line in lines), ZERO)
        total_credit = sum((line.credit_amount for line in lines), ZERO)
        AccountingCalculationService.validate_journal_balance(total_debit, total_credit)

        journal_number = await self._generate_unique_journal_number(
            company_id, invoice.financial_year_id, f"JV-INV-{invoice.invoice_number}"
        )

        entry = JournalEntry(
            company_id=company_id,
            financial_year_id=invoice.financial_year_id,
            journal_number=journal_number,
            journal_date=invoice.invoice_date,
            narration=f"Auto-posted for Sales Invoice {invoice.invoice_number}",
            status=TransactionStatus.POSTED,
            source=DataSource.MANUAL,
            source_reference=source_ref,
            lines=lines,
        )
        self.db.add(entry)
        await self.db.flush()

        await self.audit.log(
            action=AuditAction.ACCOUNTING_POST,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="journal_entry",
            resource_id=str(entry.id),
            description=f"Journal entry '{entry.journal_number}' auto-posted for sales invoice '{invoice.invoice_number}'",
            metadata={"total_debit": str(total_debit), "total_credit": str(total_credit)},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entry

    async def post_purchase_invoice(
        self, company_id: uuid.UUID, invoice: PurchaseInvoice, current_user: User, meta: RequestMeta
    ) -> JournalEntry:
        source_ref = f"purchase_invoice:{invoice.id}"
        existing_journal = (
            await self.db.execute(
                select(JournalEntry).where(
                    JournalEntry.company_id == company_id,
                    JournalEntry.source_reference == source_ref,
                    JournalEntry.status == TransactionStatus.POSTED,
                )
            )
        ).scalar_one_or_none()
        if existing_journal is not None:
            raise ConflictError(
                "A posted journal entry already exists for this purchase invoice",
                code="ALREADY_POSTED",
            )

        # Resolve ledgers
        vend_ledger = await self._resolve_vendor_ledger(company_id, invoice.vendor_id)
        purchase_ledger = await self._get_or_create_ledger(
            company_id,
            name="Purchase Account",
            ledger_type=LedgerType.EXPENSE,
            opening_balance_type=BalanceType.DEBIT,
        )

        lines: list[JournalEntryLine] = []

        # 1. Debit Purchase Expense for Taxable Amount
        lines.append(
            JournalEntryLine(
                ledger_id=purchase_ledger.id,
                debit_amount=invoice.taxable_amount,
                credit_amount=ZERO,
                description=f"Expense for purchase invoice {invoice.invoice_number}",
            )
        )

        # 2. Debit Input Taxes
        if invoice.cgst_amount > ZERO:
            cgst_ledger = await self._get_or_create_ledger(
                company_id,
                name="Input CGST",
                ledger_type=LedgerType.TAX,
                opening_balance_type=BalanceType.DEBIT,
            )
            lines.append(
                JournalEntryLine(
                    ledger_id=cgst_ledger.id,
                    debit_amount=invoice.cgst_amount,
                    credit_amount=ZERO,
                    description=f"Input CGST on purchase invoice {invoice.invoice_number}",
                )
            )

        if invoice.sgst_amount > ZERO:
            sgst_ledger = await self._get_or_create_ledger(
                company_id,
                name="Input SGST",
                ledger_type=LedgerType.TAX,
                opening_balance_type=BalanceType.DEBIT,
            )
            lines.append(
                JournalEntryLine(
                    ledger_id=sgst_ledger.id,
                    debit_amount=invoice.sgst_amount,
                    credit_amount=ZERO,
                    description=f"Input SGST on purchase invoice {invoice.invoice_number}",
                )
            )

        if invoice.igst_amount > ZERO:
            igst_ledger = await self._get_or_create_ledger(
                company_id,
                name="Input IGST",
                ledger_type=LedgerType.TAX,
                opening_balance_type=BalanceType.DEBIT,
            )
            lines.append(
                JournalEntryLine(
                    ledger_id=igst_ledger.id,
                    debit_amount=invoice.igst_amount,
                    credit_amount=ZERO,
                    description=f"Input IGST on purchase invoice {invoice.invoice_number}",
                )
            )

        if invoice.cess_amount > ZERO:
            cess_ledger = await self._get_or_create_ledger(
                company_id,
                name="Input Cess",
                ledger_type=LedgerType.TAX,
                opening_balance_type=BalanceType.DEBIT,
            )
            lines.append(
                JournalEntryLine(
                    ledger_id=cess_ledger.id,
                    debit_amount=invoice.cess_amount,
                    credit_amount=ZERO,
                    description=f"Input Cess on purchase invoice {invoice.invoice_number}",
                )
            )

        # 3. Handle Round Off
        round_off = getattr(invoice, "round_off", None)
        if round_off is None:
            round_off = invoice.grand_total - (invoice.taxable_amount + invoice.total_tax)

        if round_off != ZERO:
            round_off_ledger = await self._get_or_create_ledger(
                company_id,
                name="Round Off",
                ledger_type=LedgerType.EXPENSE,
                opening_balance_type=BalanceType.DEBIT,
            )
            if round_off > ZERO:
                # Purchase rounding up -> Debit expense
                lines.append(
                    JournalEntryLine(
                        ledger_id=round_off_ledger.id,
                        debit_amount=round_off,
                        credit_amount=ZERO,
                        description=f"Round off for purchase invoice {invoice.invoice_number}",
                    )
                )
            else:
                # Purchase rounding down -> Credit income/gain
                lines.append(
                    JournalEntryLine(
                        ledger_id=round_off_ledger.id,
                        debit_amount=ZERO,
                        credit_amount=abs(round_off),
                        description=f"Round off for purchase invoice {invoice.invoice_number}",
                    )
                )

        # 4. Credit Vendor Payable for Grand Total
        lines.append(
            JournalEntryLine(
                ledger_id=vend_ledger.id,
                debit_amount=ZERO,
                credit_amount=invoice.grand_total,
                description=f"Payable for purchase invoice {invoice.invoice_number}",
            )
        )

        # Validate balance
        total_debit = sum((line.debit_amount for line in lines), ZERO)
        total_credit = sum((line.credit_amount for line in lines), ZERO)
        AccountingCalculationService.validate_journal_balance(total_debit, total_credit)

        journal_number = await self._generate_unique_journal_number(
            company_id, invoice.financial_year_id, f"JV-BILL-{invoice.invoice_number}"
        )

        entry = JournalEntry(
            company_id=company_id,
            financial_year_id=invoice.financial_year_id,
            journal_number=journal_number,
            journal_date=invoice.invoice_date,
            narration=f"Auto-posted for Purchase Invoice {invoice.invoice_number}",
            status=TransactionStatus.POSTED,
            source=DataSource.MANUAL,
            source_reference=source_ref,
            lines=lines,
        )
        self.db.add(entry)
        await self.db.flush()

        await self.audit.log(
            action=AuditAction.ACCOUNTING_POST,
            user_id=current_user.id,
            company_id=company_id,
            resource_type="journal_entry",
            resource_id=str(entry.id),
            description=f"Journal entry '{entry.journal_number}' auto-posted for purchase invoice '{invoice.invoice_number}'",
            metadata={"total_debit": str(total_debit), "total_credit": str(total_credit)},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )
        return entry

    async def cancel_sales_invoice_posting(
        self, company_id: uuid.UUID, invoice: SalesInvoice, current_user: User, meta: RequestMeta
    ) -> JournalEntry | None:
        source_ref = f"sales_invoice:{invoice.id}"
        journal = (
            await self.db.execute(
                select(JournalEntry).where(
                    JournalEntry.company_id == company_id,
                    JournalEntry.source_reference == source_ref,
                    JournalEntry.status == TransactionStatus.POSTED,
                )
            )
        ).scalar_one_or_none()
        if journal is not None:
            journal.status = TransactionStatus.CANCELLED
            await self.db.flush()
            await self.audit.log(
                action=AuditAction.ACCOUNTING_CANCEL,
                user_id=current_user.id,
                company_id=company_id,
                resource_type="journal_entry",
                resource_id=str(journal.id),
                description=f"Journal entry '{journal.journal_number}' cancelled due to sales invoice cancellation",
                ip_address=meta.ip_address,
                user_agent=meta.user_agent,
            )
        return journal

    async def cancel_purchase_invoice_posting(
        self, company_id: uuid.UUID, invoice: PurchaseInvoice, current_user: User, meta: RequestMeta
    ) -> JournalEntry | None:
        source_ref = f"purchase_invoice:{invoice.id}"
        journal = (
            await self.db.execute(
                select(JournalEntry).where(
                    JournalEntry.company_id == company_id,
                    JournalEntry.source_reference == source_ref,
                    JournalEntry.status == TransactionStatus.POSTED,
                )
            )
        ).scalar_one_or_none()
        if journal is not None:
            journal.status = TransactionStatus.CANCELLED
            await self.db.flush()
            await self.audit.log(
                action=AuditAction.ACCOUNTING_CANCEL,
                user_id=current_user.id,
                company_id=company_id,
                resource_type="journal_entry",
                resource_id=str(journal.id),
                description=f"Journal entry '{journal.journal_number}' cancelled due to purchase invoice cancellation",
                ip_address=meta.ip_address,
                user_agent=meta.user_agent,
            )
        return journal
