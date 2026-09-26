from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ValidationAppError
from app.models.accounting_enums import (
    BalanceType,
    DataSource,
    FinancialYearStatus,
    LedgerType,
    OpeningBalanceAccountType,
    PaymentMode,
    TransactionStatus,
)
from app.services.company_initialization_service import compute_default_financial_year
from app.models.customer import Customer
from app.models.financial_year import FinancialYear
from app.models.import_job import ImportError as ImportErrorModel, ImportJob, ImportRow, ImportRowStatus
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.ledger import Ledger
from app.models.opening_balance import OpeningBalance
from app.models.payment import Payment
from app.models.purchase_invoice import PurchaseInvoice, PurchaseInvoiceItem
from app.models.receipt import Receipt
from app.models.sales_invoice import SalesInvoice, SalesInvoiceItem
from app.models.user import User
from app.models.vendor import Vendor
from app.services.accounting_calculation_service import round_money
from app.services.audit_service import AuditAction, AuditService
from app.services.auth_service import RequestMeta
from app.services.tally.tally_models import (
    MappingStatus,
    TallyImportBatch,
    TallyMappingRule,
    TallyReconciliationItem,
    TallyReconciliationReport,
    TallyVoucherRecord,
    TallyVoucherType,
    ValidationSeverity,
)
from app.services.tally.tally_validator import TallyValidationResult


def _dec(val: Any) -> Decimal:
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal(0)


class TallyImporter:
    """Commit engine and reconciliation calculator for Tally imports."""

    def __init__(self, db: AsyncSession, company_id: uuid.UUID) -> None:
        self.db = db
        self.company_id = company_id
        self.audit = AuditService(db)

    async def commit_batch(
        self,
        batch: TallyImportBatch,
        rules: list[TallyMappingRule],
        validation: TallyValidationResult,
        financial_year_id: uuid.UUID | None,
        current_user: User,
        meta: RequestMeta,
        job_id: uuid.UUID | None = None,
    ) -> TallyReconciliationReport:
        """Atomically commits non-duplicate valid vouchers, ledgers, parties,
        and opening balances into the accounting database."""

        # 1. Resolve Financial Year
        if not financial_year_id:
            sample_date = date.today()
            if batch.vouchers:
                sample_date = batch.vouchers[0].voucher_date

            fy_res = await self.db.execute(
                select(FinancialYear)
                .where(FinancialYear.company_id == self.company_id)
                .order_by(FinancialYear.start_date.desc())
            )
            all_fys = list(fy_res.scalars().all())
            matching_fy = next((f for f in all_fys if f.contains(sample_date)), None)
            if not matching_fy and all_fys:
                matching_fy = all_fys[0]

            if not matching_fy:
                fy_name, fy_start, fy_end = compute_default_financial_year(sample_date)
                matching_fy = FinancialYear(
                    company_id=self.company_id,
                    name=fy_name,
                    start_date=fy_start,
                    end_date=fy_end,
                    is_current=True,
                    status=FinancialYearStatus.OPEN,
                )
                self.db.add(matching_fy)
                await self.db.flush()
            financial_year_id = uuid.UUID(str(matching_fy.id))

        # 2. Build mapping lookups
        ledger_target_map: dict[str, uuid.UUID] = {}
        party_target_map: dict[str, tuple[str, uuid.UUID]] = {}  # name -> (type, uuid)

        for r in rules:
            if r.source_type == "LEDGER" and r.target_id:
                try:
                    ledger_target_map[r.source_name.strip().lower()] = uuid.UUID(r.target_id)
                except ValueError:
                    pass
            elif r.source_type == "PARTY" and r.target_id:
                try:
                    party_target_map[r.source_name.strip().lower()] = ("CUSTOMER", uuid.UUID(r.target_id))
                except ValueError:
                    pass

        # 3. Create missing/new Ledgers and Parties within transaction
        await self._ensure_parties(batch, party_target_map)
        await self._ensure_ledgers(batch, ledger_target_map)

        # Track reconciliation stats
        recon_stats: dict[str, dict[str, Decimal | int]] = {
            "SALES": {"src_cnt": 0, "src_amt": Decimal(0), "imp_cnt": 0, "imp_amt": Decimal(0)},
            "PURCHASES": {"src_cnt": 0, "src_amt": Decimal(0), "imp_cnt": 0, "imp_amt": Decimal(0)},
            "RECEIPTS": {"src_cnt": 0, "src_amt": Decimal(0), "imp_cnt": 0, "imp_amt": Decimal(0)},
            "PAYMENTS": {"src_cnt": 0, "src_amt": Decimal(0), "imp_cnt": 0, "imp_amt": Decimal(0)},
            "JOURNALS": {"src_cnt": 0, "src_amt": Decimal(0), "imp_cnt": 0, "imp_amt": Decimal(0)},
            "OPENING_BALANCES": {"src_cnt": 0, "src_amt": Decimal(0), "imp_cnt": 0, "imp_amt": Decimal(0)},
        }

        # Source voucher stats
        for v in batch.vouchers:
            stat_key = self._get_stat_key(v.normalized_type)
            if stat_key in recon_stats:
                recon_stats[stat_key]["src_cnt"] += 1
                recon_stats[stat_key]["src_amt"] += v.total_amount

        for ob in batch.opening_balances:
            recon_stats["OPENING_BALANCES"]["src_cnt"] += 1
            recon_stats["OPENING_BALANCES"]["src_amt"] += ob.amount

        # 4. Commit non-duplicate vouchers
        committed_rows = 0
        import_source_ref = f"tally_import:{job_id or 'batch'}"

        for idx, voucher in enumerate(batch.vouchers, start=1):
            if voucher.fingerprint in validation.duplicate_fingerprints or voucher.voucher_number in validation.duplicate_vouchers:
                continue

            stat_key = self._get_stat_key(voucher.normalized_type)

            if voucher.normalized_type == TallyVoucherType.SALES:
                inv = await self._commit_sales_voucher(voucher, financial_year_id, party_target_map, import_source_ref)
                if inv:
                    committed_rows += 1
                    recon_stats[stat_key]["imp_cnt"] += 1
                    recon_stats[stat_key]["imp_amt"] += inv.grand_total

            elif voucher.normalized_type == TallyVoucherType.PURCHASE:
                inv = await self._commit_purchase_voucher(voucher, financial_year_id, party_target_map, import_source_ref)
                if inv:
                    committed_rows += 1
                    recon_stats[stat_key]["imp_cnt"] += 1
                    recon_stats[stat_key]["imp_amt"] += inv.grand_total

            elif voucher.normalized_type == TallyVoucherType.RECEIPT:
                rec = await self._commit_receipt_voucher(voucher, financial_year_id, party_target_map, ledger_target_map, import_source_ref)
                if rec:
                    committed_rows += 1
                    recon_stats[stat_key]["imp_cnt"] += 1
                    recon_stats[stat_key]["imp_amt"] += rec.amount

            elif voucher.normalized_type == TallyVoucherType.PAYMENT:
                pay = await self._commit_payment_voucher(voucher, financial_year_id, party_target_map, ledger_target_map, import_source_ref)
                if pay:
                    committed_rows += 1
                    recon_stats[stat_key]["imp_cnt"] += 1
                    recon_stats[stat_key]["imp_amt"] += pay.amount

            elif voucher.normalized_type in (TallyVoucherType.JOURNAL, TallyVoucherType.CONTRA, TallyVoucherType.CREDIT_NOTE, TallyVoucherType.DEBIT_NOTE):
                j = await self._commit_journal_voucher(voucher, financial_year_id, ledger_target_map, import_source_ref)
                if j:
                    committed_rows += 1
                    recon_stats["JOURNALS"]["imp_cnt"] += 1
                    recon_stats["JOURNALS"]["imp_amt"] += voucher.total_amount

        # 5. Commit Opening Balances
        for ob in batch.opening_balances:
            l_id = ledger_target_map.get(ob.ledger_name.strip().lower())
            if l_id:
                await self._commit_opening_balance(ob, financial_year_id, l_id)
                recon_stats["OPENING_BALANCES"]["imp_cnt"] += 1
                recon_stats["OPENING_BALANCES"]["imp_amt"] += ob.amount

        await self.db.flush()

        # 6. Build Reconciliation Report
        items: list[TallyReconciliationItem] = []
        overall_matched = True
        total_src = Decimal(0)
        total_imp = Decimal(0)

        for k, v in recon_stats.items():
            s_amt = round_money(v["src_amt"])
            i_amt = round_money(v["imp_amt"])
            d_amt = round_money(s_amt - i_amt)
            d_cnt = v["src_cnt"] - v["imp_cnt"]
            is_m = (d_amt == Decimal(0) and d_cnt == 0)
            if not is_m and v["src_cnt"] > 0:
                overall_matched = False

            total_src += s_amt
            total_imp += i_amt

            items.append(
                TallyReconciliationItem(
                    entity_type=k,
                    source_count=v["src_cnt"],
                    source_amount=s_amt,
                    imported_count=v["imp_cnt"],
                    imported_amount=i_amt,
                    difference_count=d_cnt,
                    difference_amount=d_amt,
                    is_matched=is_m,
                    notes="Fully reconciled" if is_m else f"Variance: {d_cnt} records, ₹{d_amt:,.2f}",
                )
            )

        report = TallyReconciliationReport(
            company_id=str(self.company_id),
            import_job_id=str(job_id) if job_id else None,
            reconciled_at=datetime.now(timezone.utc),
            items=items,
            overall_matched=overall_matched,
            source_total=total_src,
            imported_total=total_imp,
            total_difference=total_src - total_imp,
        )

        await self.audit.log(
            action=AuditAction.IMPORT_COMMIT,
            user_id=current_user.id,
            company_id=self.company_id,
            resource_type="tally_import",
            resource_id=str(job_id or uuid.uuid4()),
            description=f"Tally import committed: {committed_rows} records created, overall matched={overall_matched}",
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
        )

        return report

    def _get_stat_key(self, norm_type: TallyVoucherType) -> str:
        if norm_type == TallyVoucherType.SALES:
            return "SALES"
        if norm_type == TallyVoucherType.PURCHASE:
            return "PURCHASES"
        if norm_type == TallyVoucherType.RECEIPT:
            return "RECEIPTS"
        if norm_type == TallyVoucherType.PAYMENT:
            return "PAYMENTS"
        return "JOURNALS"

    async def _ensure_parties(self, batch: TallyImportBatch, party_map: dict[str, tuple[str, uuid.UUID]]) -> None:
        """Creates customers/vendors for any new parties referenced in import batch."""
        for p in batch.parties:
            norm_name = p.name.strip().lower()
            if norm_name in party_map:
                continue

            if p.party_type == "VENDOR":
                vendor = Vendor(
                    company_id=self.company_id,
                    name=p.name,
                    gstin=p.gstin,
                    pan=p.pan,
                    state=p.state,
                    state_code=p.state_code,
                    address=p.address,
                )
                self.db.add(vendor)
                await self.db.flush()
                party_map[norm_name] = ("VENDOR", uuid.UUID(str(vendor.id)))
            else:
                customer = Customer(
                    company_id=self.company_id,
                    name=p.name,
                    gstin=p.gstin,
                    pan=p.pan,
                    state=p.state,
                    state_code=p.state_code,
                    billing_address=p.address,
                )
                self.db.add(customer)
                await self.db.flush()
                party_map[norm_name] = ("CUSTOMER", uuid.UUID(str(customer.id)))

    async def _ensure_ledgers(self, batch: TallyImportBatch, ledger_map: dict[str, uuid.UUID]) -> None:
        """Creates ledgers in CoA for any new ledgers referenced in import batch."""
        needed: set[str] = set()
        for l in batch.ledgers:
            needed.add(l.name)
        for v in batch.vouchers:
            for line in v.lines:
                needed.add(line.ledger_name)

        for l_name in needed:
            norm = l_name.strip().lower()
            if norm in ledger_map or not norm:
                continue

            # Guess ledger type from name
            norm_upper = l_name.upper()
            l_type = LedgerType.EXPENSE
            if "SALES" in norm_upper or "REVENUE" in norm_upper or "INCOME" in norm_upper:
                l_type = LedgerType.INCOME
            elif "TAX" in norm_upper or "GST" in norm_upper or "DUTIES" in norm_upper:
                l_type = LedgerType.TAX
            elif "BANK" in norm_upper:
                l_type = LedgerType.BANK
            elif "CASH" in norm_upper:
                l_type = LedgerType.CASH
            elif "ASSET" in norm_upper or "DEBTOR" in norm_upper:
                l_type = LedgerType.ASSET
            elif "LIABILITY" in norm_upper or "CREDITOR" in norm_upper or "CAPITAL" in norm_upper:
                l_type = LedgerType.LIABILITY

            ledger = Ledger(
                company_id=self.company_id,
                name=l_name,
                ledger_type=l_type,
            )
            self.db.add(ledger)
            await self.db.flush()
            ledger_map[norm] = uuid.UUID(str(ledger.id))

    async def _commit_sales_voucher(
        self,
        v: TallyVoucherRecord,
        fy_id: uuid.UUID,
        party_map: dict[str, tuple[str, uuid.UUID]],
        source_ref: str,
    ) -> SalesInvoice | None:
        party_name = (v.party_name or "").strip().lower()
        party_entry = party_map.get(party_name)

        customer_id = party_entry[1] if party_entry else None
        if not customer_id:
            # Fallback to creating customer
            c = Customer(company_id=self.company_id, name=v.party_name or "Tally Customer")
            self.db.add(c)
            await self.db.flush()
            customer_id = uuid.UUID(str(c.id))
            party_map[party_name] = ("CUSTOMER", customer_id)

        tb = v.tax_breakdown
        taxable = round_money(tb.taxable_amount if tb.taxable_amount > 0 else v.total_amount)
        cgst = round_money(tb.cgst_amount)
        sgst = round_money(tb.sgst_amount)
        igst = round_money(tb.igst_amount)
        cess = round_money(tb.cess_amount)
        total_tax = cgst + sgst + igst + cess
        grand_total = round_money(taxable + total_tax)

        invoice = SalesInvoice(
            company_id=self.company_id,
            financial_year_id=fy_id,
            customer_id=customer_id,
            invoice_number=v.voucher_number,
            invoice_date=v.voucher_date,
            subtotal=taxable,
            taxable_amount=taxable,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=igst,
            cess_amount=cess,
            total_tax=total_tax,
            grand_total=grand_total,
            status=TransactionStatus.POSTED,
            source=DataSource.TALLY,
            source_reference=f"{source_ref}:{v.voucher_number}|fp:{v.fingerprint}",
        )
        self.db.add(invoice)
        await self.db.flush()

        # Add line items if inventory present
        if v.inventory:
            for item in v.inventory:
                desc = f"{item.item_name} (HSN: {item.hsn_sac})" if item.hsn_sac else item.item_name
                self.db.add(
                    SalesInvoiceItem(
                        sales_invoice_id=invoice.id,
                        description=desc,
                        quantity=item.quantity,
                        unit_price=item.rate,
                        taxable_value=item.amount,
                        total_amount=item.amount,
                    )
                )
        else:
            self.db.add(
                SalesInvoiceItem(
                    sales_invoice_id=invoice.id,
                    description=v.narration or "Goods/Services",
                    quantity=Decimal(1),
                    unit_price=taxable,
                    taxable_value=taxable,
                    total_amount=taxable,
                )
            )

        return invoice

    async def _commit_purchase_voucher(
        self,
        v: TallyVoucherRecord,
        fy_id: uuid.UUID,
        party_map: dict[str, tuple[str, uuid.UUID]],
        source_ref: str,
    ) -> PurchaseInvoice | None:
        party_name = (v.party_name or "").strip().lower()
        party_entry = party_map.get(party_name)

        vendor_id = party_entry[1] if party_entry else None
        if not vendor_id:
            vendor = Vendor(company_id=self.company_id, name=v.party_name or "Tally Vendor")
            self.db.add(vendor)
            await self.db.flush()
            vendor_id = uuid.UUID(str(vendor.id))
            party_map[party_name] = ("VENDOR", vendor_id)

        tb = v.tax_breakdown
        taxable = round_money(tb.taxable_amount if tb.taxable_amount > 0 else v.total_amount)
        cgst = round_money(tb.cgst_amount)
        sgst = round_money(tb.sgst_amount)
        igst = round_money(tb.igst_amount)
        cess = round_money(tb.cess_amount)
        total_tax = cgst + sgst + igst + cess
        grand_total = round_money(taxable + total_tax)

        invoice = PurchaseInvoice(
            company_id=self.company_id,
            financial_year_id=fy_id,
            vendor_id=vendor_id,
            invoice_number=v.voucher_number,
            invoice_date=v.voucher_date,
            supplier_invoice_number=v.reference_no or v.voucher_number,
            supplier_invoice_date=v.reference_date or v.voucher_date,
            subtotal=taxable,
            taxable_amount=taxable,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=igst,
            cess_amount=cess,
            total_tax=total_tax,
            grand_total=grand_total,
            status=TransactionStatus.POSTED,
            source=DataSource.TALLY,
            source_reference=f"{source_ref}:{v.voucher_number}|fp:{v.fingerprint}",
        )
        self.db.add(invoice)
        await self.db.flush()

        if v.inventory:
            for item in v.inventory:
                desc = f"{item.item_name} (HSN: {item.hsn_sac})" if item.hsn_sac else item.item_name
                self.db.add(
                    PurchaseInvoiceItem(
                        purchase_invoice_id=invoice.id,
                        description=desc,
                        quantity=item.quantity,
                        unit_price=item.rate,
                        taxable_value=item.amount,
                        total_amount=item.amount,
                    )
                )
        else:
            self.db.add(
                PurchaseInvoiceItem(
                    purchase_invoice_id=invoice.id,
                    description=v.narration or "Goods/Services",
                    quantity=Decimal(1),
                    unit_price=taxable,
                    taxable_value=taxable,
                    total_amount=taxable,
                )
            )

        return invoice

    async def _commit_receipt_voucher(
        self,
        v: TallyVoucherRecord,
        fy_id: uuid.UUID,
        party_map: dict[str, tuple[str, uuid.UUID]],
        ledger_map: dict[str, uuid.UUID],
        source_ref: str,
    ) -> Receipt | None:
        party_name = (v.party_name or "").strip().lower()
        party_entry = party_map.get(party_name)
        customer_id = party_entry[1] if party_entry else None
        if not customer_id:
            c = Customer(company_id=self.company_id, name=v.party_name or "Tally Customer")
            self.db.add(c)
            await self.db.flush()
            customer_id = uuid.UUID(str(c.id))

        # Receipt ledger (Bank or Cash)
        ledger_id = None
        for line in v.lines:
            if line.is_debit:
                ledger_id = ledger_map.get(line.ledger_name.strip().lower())
                if ledger_id:
                    break
        if not ledger_id:
            ledger_id = next(iter(ledger_map.values()), None)

        receipt = Receipt(
            company_id=self.company_id,
            financial_year_id=fy_id,
            receipt_date=v.voucher_date,
            receipt_number=v.voucher_number,
            customer_id=customer_id,
            ledger_id=ledger_id,
            amount=round_money(v.total_amount),
            payment_mode=PaymentMode.BANK,
            source=DataSource.TALLY,
            source_reference=f"{source_ref}:{v.voucher_number}|fp:{v.fingerprint}",
        )
        self.db.add(receipt)
        await self.db.flush()
        return receipt

    async def _commit_payment_voucher(
        self,
        v: TallyVoucherRecord,
        fy_id: uuid.UUID,
        party_map: dict[str, tuple[str, uuid.UUID]],
        ledger_map: dict[str, uuid.UUID],
        source_ref: str,
    ) -> Payment | None:
        # Bank/Cash ledger
        ledger_id = None
        for line in v.lines:
            if not line.is_debit:
                ledger_id = ledger_map.get(line.ledger_name.strip().lower())
                if ledger_id:
                    break
        if not ledger_id:
            ledger_id = next(iter(ledger_map.values()), None)

        payment = Payment(
            company_id=self.company_id,
            financial_year_id=fy_id,
            payment_date=v.voucher_date,
            payment_number=v.voucher_number,
            ledger_id=ledger_id,
            amount=round_money(v.total_amount),
            payment_mode=PaymentMode.BANK,
            source=DataSource.TALLY,
            source_reference=f"{source_ref}:{v.voucher_number}|fp:{v.fingerprint}",
        )
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def _commit_journal_voucher(
        self,
        v: TallyVoucherRecord,
        fy_id: uuid.UUID,
        ledger_map: dict[str, uuid.UUID],
        source_ref: str,
    ) -> JournalEntry | None:
        lines: list[JournalEntryLine] = []
        for line in v.lines:
            l_id = ledger_map.get(line.ledger_name.strip().lower())
            if not l_id:
                # Get any ledger or create
                l_id = next(iter(ledger_map.values()), None)

            lines.append(
                JournalEntryLine(
                    ledger_id=l_id,
                    debit_amount=round_money(line.amount if line.is_debit else Decimal(0)),
                    credit_amount=round_money(line.amount if not line.is_debit else Decimal(0)),
                    description=line.narration or v.narration,
                )
            )

        if not lines:
            return None

        # Double check balance
        tot_dr = sum((l.debit_amount for l in lines), Decimal(0))
        tot_cr = sum((l.credit_amount for l in lines), Decimal(0))
        if tot_dr != tot_cr and len(lines) >= 2:
            # Adjust rounding difference on last line if <= 0.05
            diff = tot_dr - tot_cr
            if abs(diff) <= Decimal("0.05"):
                if diff > 0:
                    lines[-1].credit_amount += diff
                else:
                    lines[-1].debit_amount += abs(diff)

        entry = JournalEntry(
            company_id=self.company_id,
            financial_year_id=fy_id,
            journal_number=v.voucher_number,
            journal_date=v.voucher_date,
            narration=v.narration,
            status=TransactionStatus.POSTED,
            source=DataSource.TALLY,
            source_reference=f"{source_ref}:{v.voucher_number}|fp:{v.fingerprint}",
            lines=lines,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def _commit_opening_balance(
        self,
        ob: Any,
        fy_id: uuid.UUID,
        ledger_id: uuid.UUID,
    ) -> None:
        balance_type = BalanceType.DEBIT if ob.is_debit else BalanceType.CREDIT
        existing_res = await self.db.execute(
            select(OpeningBalance).where(
                OpeningBalance.company_id == self.company_id,
                OpeningBalance.financial_year_id == fy_id,
                OpeningBalance.account_type == OpeningBalanceAccountType.LEDGER,
                OpeningBalance.account_id == ledger_id,
            )
        )
        existing = existing_res.scalar_one_or_none()
        if existing:
            existing.amount = ob.amount
            existing.balance_type = balance_type
        else:
            self.db.add(
                OpeningBalance(
                    company_id=self.company_id,
                    financial_year_id=fy_id,
                    account_type=OpeningBalanceAccountType.LEDGER,
                    account_id=ledger_id,
                    amount=ob.amount,
                    balance_type=balance_type,
                    notes="Imported from Tally",
                )
            )
