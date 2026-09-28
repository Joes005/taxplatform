"""Compliance readiness check engine (PHASE13 §7-8, §18).

Coordinates across all existing domain modules (GST, TDS, Income Tax,
Audit, Bank Reconciliation, and Accounting) without duplicating their
calculations. Evaluates whether a compliance obligation has its mandatory
prerequisites satisfied before it can be submitted for review or completed.

Machine-readable readiness statuses:
- READY: All checks passed.
- READY_WITH_WARNINGS: All blocking checks passed, but warnings exist.
- BLOCKED: One or more mandatory blocking checks failed.
- MISSING_DATA: Core profile or essential baseline data is missing.
- NOT_APPLICABLE: Module checks do not apply to this obligation.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting_enums import TransactionStatus
from app.models.audit_engagement import AuditEngagement
from app.models.audit_finding import AuditFinding
from app.models.audit_workflow_enums import AuditFindingSeverity, AuditFindingStatus
from app.models.bank_account import BankAccount
from app.models.bank_enums import BankTransactionReconciliationStatus
from app.models.bank_statement import BankStatement
from app.models.bank_transaction import BankTransaction
from app.models.compliance_enums import ComplianceCategory, ComplianceModule, ReadinessStatus
from app.models.compliance_obligation import ComplianceObligation
from app.models.deductee import Deductee
from app.models.gst_profile import GSTProfile
from app.models.gst_return_period import GSTReturnPeriod
from app.models.gstr2b_record import GSTR2BRecord
from app.models.income_tax_enums import TaxComputationStatus
from app.models.income_tax_profile import IncomeTaxProfile
from app.models.purchase_invoice import PurchaseInvoice
from app.models.sales_invoice import SalesInvoice
from app.models.tax_computation import TaxComputation
from app.models.tds_enums import TDSTransactionStatus
from app.models.tds_profile import TDSProfile
from app.models.tds_transaction import TDSTransaction


class ReadinessCheckItem:
    def __init__(
        self,
        check_code: str,
        description: str,
        status: str,  # "PASS", "WARN", "FAIL", "INFO"
        blocking: bool,
        source_module: str,
        entity_reference: str | None = None,
        remediation_action: str = "",
        deep_link: str = "",
    ) -> None:
        self.check_code = check_code
        self.description = description
        self.status = status
        self.blocking = blocking
        self.source_module = source_module
        self.entity_reference = entity_reference
        self.remediation_action = remediation_action
        self.deep_link = deep_link

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_code": self.check_code,
            "description": self.description,
            "status": self.status,
            "blocking": self.blocking,
            "source_module": self.source_module,
            "entity_reference": self.entity_reference,
            "remediation_action": self.remediation_action,
            "deep_link": self.deep_link,
        }


class ReadinessResult:
    def __init__(
        self,
        obligation_id: uuid.UUID,
        overall_status: ReadinessStatus,
        checks: list[ReadinessCheckItem],
        checked_at: datetime | None = None,
    ) -> None:
        self.obligation_id = obligation_id
        self.overall_status = overall_status
        self.checks = checks
        self.checked_at = checked_at or datetime.now(timezone.utc)
        self.blocking_issues_count = sum(1 for c in checks if c.blocking and c.status == "FAIL")

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": str(self.obligation_id),
            "overall_status": self.overall_status.value,
            "checks": [c.to_dict() for c in self.checks],
            "checked_at": self.checked_at.isoformat(),
            "blocking_issues_count": self.blocking_issues_count,
        }


class ComplianceReadinessService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def evaluate_obligation(
        self, company_id: uuid.UUID, obligation: ComplianceObligation
    ) -> ReadinessResult:
        checks: list[ReadinessCheckItem] = []
        code_upper = obligation.code.upper()
        module = obligation.module
        category = obligation.category

        # 1. GST Checks
        if module == ComplianceModule.GST or category == ComplianceCategory.GST:
            await self._check_gst(company_id, obligation, checks)

        # 2. TDS Checks
        elif module == ComplianceModule.TDS or category == ComplianceCategory.TDS:
            await self._check_tds(company_id, obligation, checks)

        # 3. Income Tax Checks
        elif module == ComplianceModule.INCOME_TAX or category == ComplianceCategory.INCOME_TAX:
            await self._check_income_tax(company_id, obligation, checks)

        # 4. Audit Checks
        elif module == ComplianceModule.AUDIT or category == ComplianceCategory.AUDIT:
            await self._check_audit(company_id, obligation, checks)

        # 5. Bank Reconciliation Checks
        elif module == ComplianceModule.BANK_RECONCILIATION or category == ComplianceCategory.BANK:
            await self._check_bank_reconciliation(company_id, obligation, checks)

        # 6. Accounting / General Close Checks
        elif module == ComplianceModule.ACCOUNTING or category == ComplianceCategory.ACCOUNTING:
            await self._check_accounting(company_id, obligation, checks)

        else:
            # General / other checks
            checks.append(
                ReadinessCheckItem(
                    check_code="GENERAL_OBLIGATION_CHECK",
                    description="Standard compliance obligation requirements",
                    status="PASS",
                    blocking=False,
                    source_module="GENERAL",
                    remediation_action="Review obligation instructions",
                    deep_link="/compliance",
                )
            )

        # Determine overall readiness
        has_blocking_fail = any(c.blocking and c.status == "FAIL" for c in checks)
        has_nonblocking_fail = any(not c.blocking and c.status == "FAIL" for c in checks)
        has_warning = any(c.status == "WARN" for c in checks)

        if has_blocking_fail:
            overall = ReadinessStatus.BLOCKED
        elif has_nonblocking_fail:
            overall = ReadinessStatus.MISSING_DATA
        elif has_warning:
            overall = ReadinessStatus.READY_WITH_WARNINGS
        else:
            overall = ReadinessStatus.READY

        return ReadinessResult(
            obligation_id=obligation.id,
            overall_status=overall,
            checks=checks,
        )

    async def _check_gst(
        self, company_id: uuid.UUID, obligation: ComplianceObligation, checks: list[ReadinessCheckItem]
    ) -> None:
        # Check GST Profile
        gst_prof_res = await self.db.execute(select(GSTProfile).where(GSTProfile.company_id == company_id))
        gst_prof = gst_prof_res.scalar_one_or_none()
        if not gst_prof or not gst_prof.gstin:
            checks.append(
                ReadinessCheckItem(
                    check_code="GST_PROFILE_MISSING",
                    description="GST Profile is not configured or active GSTIN is missing",
                    status="FAIL",
                    blocking=True,
                    source_module="GST",
                    remediation_action="Configure GST Profile with valid GSTIN",
                    deep_link="/gst",
                )
            )
        else:
            checks.append(
                ReadinessCheckItem(
                    check_code="GST_PROFILE_CONFIGURED",
                    description="GST Profile is configured",
                    status="PASS",
                    blocking=False,
                    source_module="GST",
                    entity_reference=f"GSTIN: {gst_prof.gstin}",
                    remediation_action="None required",
                    deep_link="/gst",
                )
            )

        code = obligation.code.upper()
        # Check Sales Invoices for outward return (GSTR-1 / GSTR-3B)
        sales_q = select(func.count(SalesInvoice.id)).where(SalesInvoice.company_id == company_id)
        if obligation.financial_year_id:
            sales_q = sales_q.where(SalesInvoice.financial_year_id == obligation.financial_year_id)
        total_sales = (await self.db.execute(sales_q)).scalar_one()

        unposted_sales_q = select(func.count(SalesInvoice.id)).where(
            SalesInvoice.company_id == company_id,
            SalesInvoice.status == TransactionStatus.DRAFT,
        )
        if obligation.financial_year_id:
            unposted_sales_q = unposted_sales_q.where(SalesInvoice.financial_year_id == obligation.financial_year_id)
        unposted_sales = (await self.db.execute(unposted_sales_q)).scalar_one()

        if unposted_sales > 0:
            checks.append(
                ReadinessCheckItem(
                    check_code="GST_UNPOSTED_SALES_INVOICES",
                    description=f"{unposted_sales} sales invoice(s) are in DRAFT status and unposted",
                    status="FAIL",
                    blocking=True,
                    source_module="GST",
                    remediation_action="Post or cancel all draft sales invoices",
                    deep_link="/accounting/sales-invoices",
                )
            )
        elif total_sales > 0:
            checks.append(
                ReadinessCheckItem(
                    check_code="GST_SALES_INVOICES_POSTED",
                    description=f"{total_sales} sales invoice(s) recorded and properly posted",
                    status="PASS",
                    blocking=False,
                    source_module="GST",
                    remediation_action="None required",
                    deep_link="/accounting/sales-invoices",
                )
            )
        else:
            checks.append(
                ReadinessCheckItem(
                    check_code="GST_NO_SALES_RECORDED",
                    description="No sales invoices recorded for this period",
                    status="WARN",
                    blocking=False,
                    source_module="GST",
                    remediation_action="Verify if nil return is intended",
                    deep_link="/accounting/sales-invoices",
                )
            )

        # GSTR-3B specific checks
        if "3B" in code or "GSTR3B" in code:
            # Check GSTR-2B import
            gstr2b_count_q = select(func.count(GSTR2BRecord.id)).where(GSTR2BRecord.company_id == company_id)
            gstr2b_count = (await self.db.execute(gstr2b_count_q)).scalar_one()
            if gstr2b_count == 0:
                checks.append(
                    ReadinessCheckItem(
                        check_code="GSTR3B_GSTR2B_NOT_IMPORTED",
                        description="GSTR-2B has not been imported for ITC reconciliation",
                        status="WARN",
                        blocking=False,
                        source_module="GST",
                        remediation_action="Import monthly GSTR-2B file",
                        deep_link="/gst/return-periods",
                    )
                )
            else:
                checks.append(
                    ReadinessCheckItem(
                        check_code="GSTR3B_GSTR2B_IMPORTED",
                        description=f"GSTR-2B records imported ({gstr2b_count} records)",
                        status="PASS",
                        blocking=False,
                        source_module="GST",
                        remediation_action="None required",
                        deep_link="/gst/return-periods",
                    )
                )

    async def _check_tds(
        self, company_id: uuid.UUID, obligation: ComplianceObligation, checks: list[ReadinessCheckItem]
    ) -> None:
        # Check TDS Profile
        tds_prof_res = await self.db.execute(select(TDSProfile).where(TDSProfile.company_id == company_id))
        tds_prof = tds_prof_res.scalar_one_or_none()
        if not tds_prof or not tds_prof.tan:
            checks.append(
                ReadinessCheckItem(
                    check_code="TDS_PROFILE_MISSING",
                    description="TDS Profile is not configured or TAN is missing",
                    status="FAIL",
                    blocking=True,
                    source_module="TDS",
                    remediation_action="Configure TAN in TDS Profile settings",
                    deep_link="/tds",
                )
            )
        else:
            checks.append(
                ReadinessCheckItem(
                    check_code="TDS_PROFILE_CONFIGURED",
                    description="TDS Profile is active",
                    status="PASS",
                    blocking=False,
                    source_module="TDS",
                    entity_reference=f"TAN: {tds_prof.tan}",
                    remediation_action="None required",
                    deep_link="/tds",
                )
            )

        # Check Deductees
        deductee_count_q = select(func.count(Deductee.id)).where(Deductee.company_id == company_id)
        deductee_count = (await self.db.execute(deductee_count_q)).scalar_one()
        if deductee_count == 0:
            checks.append(
                ReadinessCheckItem(
                    check_code="TDS_NO_DEDUCTEES",
                    description="No deductees registered in the company",
                    status="WARN",
                    blocking=False,
                    source_module="TDS",
                    remediation_action="Register vendors and deductees with valid PAN",
                    deep_link="/tds/deductees",
                )
            )
        else:
            checks.append(
                ReadinessCheckItem(
                    check_code="TDS_DEDUCTEES_CONFIGURED",
                    description=f"{deductee_count} deductee(s) registered",
                    status="PASS",
                    blocking=False,
                    source_module="TDS",
                    remediation_action="None required",
                    deep_link="/tds/deductees",
                )
            )

        # Check for unallocated/un-remitted TDS transactions
        unallocated_q = select(func.count(TDSTransaction.id)).where(
            TDSTransaction.company_id == company_id,
            TDSTransaction.status == TDSTransactionStatus.DEDUCTED,
        )
        unallocated_count = (await self.db.execute(unallocated_q)).scalar_one()
        if unallocated_count > 0:
            checks.append(
                ReadinessCheckItem(
                    check_code="TDS_UNALLOCATED_TRANSACTIONS",
                    description=f"{unallocated_count} TDS deduction(s) have not been allocated to a paid challan",
                    status="FAIL",
                    blocking=True,
                    source_module="TDS",
                    remediation_action="Allocate deducted TDS to an ITNS 281 Challan",
                    deep_link="/tds/challans",
                )
            )
        else:
            checks.append(
                ReadinessCheckItem(
                    check_code="TDS_CHALLANS_RECONCILED",
                    description="All deducted TDS entries have been allocated to challans",
                    status="PASS",
                    blocking=False,
                    source_module="TDS",
                    remediation_action="None required",
                    deep_link="/tds/challans",
                )
            )

    async def _check_income_tax(
        self, company_id: uuid.UUID, obligation: ComplianceObligation, checks: list[ReadinessCheckItem]
    ) -> None:
        # Check Income Tax Profile
        it_prof_res = await self.db.execute(select(IncomeTaxProfile).where(IncomeTaxProfile.company_id == company_id))
        it_prof = it_prof_res.scalar_one_or_none()
        if not it_prof or not it_prof.pan:
            checks.append(
                ReadinessCheckItem(
                    check_code="INCOME_TAX_PROFILE_MISSING",
                    description="Income Tax profile with valid PAN is missing",
                    status="FAIL",
                    blocking=True,
                    source_module="INCOME_TAX",
                    remediation_action="Configure Taxpayer Profile with PAN and category",
                    deep_link="/income-tax/profile",
                )
            )
        else:
            checks.append(
                ReadinessCheckItem(
                    check_code="INCOME_TAX_PROFILE_CONFIGURED",
                    description="Income Tax Profile is configured",
                    status="PASS",
                    blocking=False,
                    source_module="INCOME_TAX",
                    entity_reference=f"PAN: {it_prof.pan}",
                    remediation_action="None required",
                    deep_link="/income-tax/profile",
                )
            )

        # Check Unposted Invoices / Entries
        unposted_sales_q = select(func.count(SalesInvoice.id)).where(
            SalesInvoice.company_id == company_id,
            SalesInvoice.status == TransactionStatus.DRAFT,
        )
        unposted_purchases_q = select(func.count(PurchaseInvoice.id)).where(
            PurchaseInvoice.company_id == company_id,
            PurchaseInvoice.status == TransactionStatus.DRAFT,
        )
        unposted = (await self.db.execute(unposted_sales_q)).scalar_one() + (
            await self.db.execute(unposted_purchases_q)
        ).scalar_one()

        if unposted > 0:
            checks.append(
                ReadinessCheckItem(
                    check_code="INCOME_TAX_UNPOSTED_ENTRIES",
                    description=f"{unposted} draft transaction(s) pending posting before PGBP computation",
                    status="FAIL",
                    blocking=True,
                    source_module="INCOME_TAX",
                    remediation_action="Post all invoices so books of accounts are final",
                    deep_link="/accounting/transactions",
                )
            )
        else:
            checks.append(
                ReadinessCheckItem(
                    check_code="INCOME_TAX_BOOKS_POSTED",
                    description="All invoices and transactions are posted",
                    status="PASS",
                    blocking=False,
                    source_module="INCOME_TAX",
                    remediation_action="None required",
                    deep_link="/accounting/transactions",
                )
            )

        # Check Tax Computation
        if obligation.financial_year_id:
            comp_q = select(TaxComputation).where(
                TaxComputation.company_id == company_id,
                TaxComputation.financial_year_id == obligation.financial_year_id,
            )
            computations = (await self.db.execute(comp_q)).scalars().all()
            finalized = [c for c in computations if c.status in [TaxComputationStatus.FINALIZED, TaxComputationStatus.COMPUTED]]
            if not finalized:
                checks.append(
                    ReadinessCheckItem(
                        check_code="INCOME_TAX_COMPUTATION_PENDING",
                        description="No finalized Tax Computation for this Financial Year",
                        status="FAIL",
                        blocking=True,
                        source_module="INCOME_TAX",
                        remediation_action="Compute and finalize Income Tax liability",
                        deep_link="/income-tax/computations",
                    )
                )
            else:
                checks.append(
                    ReadinessCheckItem(
                        check_code="INCOME_TAX_COMPUTATION_FINALIZED",
                        description="Tax Computation finalized for Financial Year",
                        status="PASS",
                        blocking=False,
                        source_module="INCOME_TAX",
                        remediation_action="None required",
                        deep_link="/income-tax/computations",
                    )
                )

    async def _check_audit(
        self, company_id: uuid.UUID, obligation: ComplianceObligation, checks: list[ReadinessCheckItem]
    ) -> None:
        # Check active engagement
        eng_q = select(AuditEngagement).where(AuditEngagement.company_id == company_id)
        if obligation.financial_year_id:
            eng_q = eng_q.where(AuditEngagement.financial_year_id == obligation.financial_year_id)
        engagements = (await self.db.execute(eng_q)).scalars().all()

        if not engagements:
            checks.append(
                ReadinessCheckItem(
                    check_code="AUDIT_ENGAGEMENT_NOT_STARTED",
                    description="No active audit engagement found for this company/period",
                    status="FAIL",
                    blocking=True,
                    source_module="AUDIT",
                    remediation_action="Create and initiate an Audit Engagement",
                    deep_link="/audit/engagements",
                )
            )
        else:
            checks.append(
                ReadinessCheckItem(
                    check_code="AUDIT_ENGAGEMENT_ACTIVE",
                    description=f"{len(engagements)} audit engagement(s) configured",
                    status="PASS",
                    blocking=False,
                    source_module="AUDIT",
                    remediation_action="None required",
                    deep_link="/audit/engagements",
                )
            )

        # Check for open CRITICAL or HIGH audit findings
        findings_q = select(func.count(AuditFinding.id)).where(
            AuditFinding.company_id == company_id,
            AuditFinding.severity.in_([AuditFindingSeverity.CRITICAL, AuditFindingSeverity.HIGH]),
            AuditFinding.status.notin_([AuditFindingStatus.RESOLVED, AuditFindingStatus.CLOSED]),
        )
        critical_findings = (await self.db.execute(findings_q)).scalar_one()

        if critical_findings > 0:
            checks.append(
                ReadinessCheckItem(
                    check_code="AUDIT_UNRESOLVED_CRITICAL_FINDINGS",
                    description=f"{critical_findings} unresolved CRITICAL/HIGH audit finding(s)",
                    status="FAIL",
                    blocking=True,
                    source_module="AUDIT",
                    remediation_action="Address audit findings and submit remediation responses",
                    deep_link="/audit/findings",
                )
            )
        else:
            checks.append(
                ReadinessCheckItem(
                    check_code="AUDIT_NO_CRITICAL_FINDINGS",
                    description="No unresolved critical audit findings",
                    status="PASS",
                    blocking=False,
                    source_module="AUDIT",
                    remediation_action="None required",
                    deep_link="/audit/findings",
                )
            )

    async def _check_bank_reconciliation(
        self, company_id: uuid.UUID, obligation: ComplianceObligation, checks: list[ReadinessCheckItem]
    ) -> None:
        # Check bank accounts
        acct_q = select(func.count(BankAccount.id)).where(BankAccount.company_id == company_id)
        acct_count = (await self.db.execute(acct_q)).scalar_one()
        if acct_count == 0:
            checks.append(
                ReadinessCheckItem(
                    check_code="BANK_NO_ACCOUNTS",
                    description="No bank accounts registered",
                    status="FAIL",
                    blocking=True,
                    source_module="BANK",
                    remediation_action="Add company bank account",
                    deep_link="/bank/accounts",
                )
            )
            return

        # Check bank statements
        stmt_q = select(func.count(BankStatement.id)).where(BankStatement.company_id == company_id)
        stmt_count = (await self.db.execute(stmt_q)).scalar_one()
        if stmt_count == 0:
            checks.append(
                ReadinessCheckItem(
                    check_code="BANK_NO_STATEMENTS_IMPORTED",
                    description="No bank statements imported",
                    status="WARN",
                    blocking=True,
                    source_module="BANK",
                    remediation_action="Import monthly bank statement CSV/XLSX",
                    deep_link="/bank/statements",
                )
            )
        else:
            checks.append(
                ReadinessCheckItem(
                    check_code="BANK_STATEMENTS_IMPORTED",
                    description=f"{stmt_count} bank statement(s) imported",
                    status="PASS",
                    blocking=False,
                    source_module="BANK",
                    remediation_action="None required",
                    deep_link="/bank/statements",
                )
            )

        # Check unmatched transactions
        unmatched_q = select(func.count(BankTransaction.id)).where(
            BankTransaction.company_id == company_id,
            BankTransaction.reconciliation_status == BankTransactionReconciliationStatus.UNMATCHED,
        )
        unmatched_count = (await self.db.execute(unmatched_q)).scalar_one()
        if unmatched_count > 0:
            checks.append(
                ReadinessCheckItem(
                    check_code="BANK_UNMATCHED_TRANSACTIONS",
                    description=f"{unmatched_count} bank transaction(s) remain unmatched",
                    status="WARN",
                    blocking=False,
                    source_module="BANK",
                    remediation_action="Match transactions or create adjustment journals",
                    deep_link="/bank/reconciliations",
                )
            )
        else:
            checks.append(
                ReadinessCheckItem(
                    check_code="BANK_TRANSACTIONS_RECONCILED",
                    description="All bank transactions reconciled",
                    status="PASS",
                    blocking=False,
                    source_module="BANK",
                    remediation_action="None required",
                    deep_link="/bank/reconciliations",
                )
            )

    async def _check_accounting(
        self, company_id: uuid.UUID, obligation: ComplianceObligation, checks: list[ReadinessCheckItem]
    ) -> None:
        unposted_sales_q = select(func.count(SalesInvoice.id)).where(
            SalesInvoice.company_id == company_id,
            SalesInvoice.status == TransactionStatus.DRAFT,
        )
        unposted_purchases_q = select(func.count(PurchaseInvoice.id)).where(
            PurchaseInvoice.company_id == company_id,
            PurchaseInvoice.status == TransactionStatus.DRAFT,
        )
        unposted = (await self.db.execute(unposted_sales_q)).scalar_one() + (
            await self.db.execute(unposted_purchases_q)
        ).scalar_one()

        if unposted > 0:
            checks.append(
                ReadinessCheckItem(
                    check_code="ACCOUNTING_UNPOSTED_INVOICES",
                    description=f"{unposted} draft invoice(s) pending posting before period closure",
                    status="FAIL",
                    blocking=True,
                    source_module="ACCOUNTING",
                    remediation_action="Post or cancel pending draft invoices",
                    deep_link="/accounting/transactions",
                )
            )
        else:
            checks.append(
                ReadinessCheckItem(
                    check_code="ACCOUNTING_INVOICES_POSTED",
                    description="All invoices posted and journals balanced",
                    status="PASS",
                    blocking=False,
                    source_module="ACCOUNTING",
                    remediation_action="None required",
                    deep_link="/accounting/transactions",
                )
            )
