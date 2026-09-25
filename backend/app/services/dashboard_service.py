import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting_enums import BalanceType, TransactionStatus
from app.models.audit_engagement import AuditEngagement
from app.models.audit_finding import AuditFinding
from app.models.audit_workflow_enums import (
    AuditEngagementStatus,
    AuditFindingSeverity,
    AuditFindingStatus,
)
from app.models.bank_account import BankAccount
from app.models.bank_enums import (
    BankReconciliationStatus,
    BankTransactionReconciliationStatus,
)
from app.models.bank_reconciliation import BankReconciliation
from app.models.bank_transaction import BankTransaction
from app.models.company import Company
from app.models.compliance_enums import ComplianceTaskStatus
from app.models.compliance_obligation import ComplianceObligation
from app.models.compliance_task import ComplianceTask
from app.models.document import Document
from app.models.financial_year import FinancialYear
from app.models.gst_enums import GSTReturnPeriodStatus
from app.models.gst_profile import GSTProfile
from app.models.gst_return_period import GSTReturnPeriod
from app.models.import_job import ImportJob
from app.models.income_tax_enums import ITRPreparationStatus, TaxComputationStatus
from app.models.income_tax_profile import IncomeTaxProfile
from app.models.itr_preparation import ITRPreparation
from app.models.journal_entry import JournalEntry
from app.models.ledger import Ledger
from app.models.opening_balance import OpeningBalance
from app.models.purchase_invoice import PurchaseInvoice
from app.models.sales_invoice import SalesInvoice
from app.models.tax_computation import TaxComputation
from app.models.tds_challan import TDSChallanAllocation
from app.models.tds_enums import TDSTransactionStatus
from app.models.tds_profile import TDSProfile
from app.models.tds_transaction import TDSTransaction
from app.models.user import User
from app.schemas.dashboard import (
    ActionCenterItem,
    AttentionSummary,
    CompanyHealth,
    DashboardActionItem,
    DashboardSummary,
    HealthAreaStatus,
    SetupProgress,
    SetupStep,
    WorkflowStage,
)
from app.services.report_service import ReportService


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_summary(
        self, company_id: uuid.UUID, current_user: User, role_code: str
    ) -> DashboardSummary:
        company_res = await self.db.execute(select(Company).where(Company.id == company_id))
        company = company_res.scalar_one_or_none()
        company_name = company.legal_name if company else "Company"

        today = date.today()
        due_soon_threshold = today + timedelta(days=7)

        # 1. Critical
        critical_findings_q = select(func.count(AuditFinding.id)).where(
            AuditFinding.company_id == company_id,
            AuditFinding.severity == AuditFindingSeverity.CRITICAL,
            AuditFinding.status.notin_([AuditFindingStatus.RESOLVED, AuditFindingStatus.CLOSED]),
        )
        overdue_tasks_q = select(func.count(ComplianceTask.id)).where(
            ComplianceTask.company_id == company_id,
            ComplianceTask.status.notin_([
                ComplianceTaskStatus.COMPLETED,
                ComplianceTaskStatus.VERIFIED,
                ComplianceTaskStatus.CANCELLED,
                ComplianceTaskStatus.LOCKED,
            ]),
            or_(ComplianceTask.status == ComplianceTaskStatus.OVERDUE, ComplianceTask.due_date < today),
        )
        critical_count = (await self.db.execute(critical_findings_q)).scalar_one() + (
            await self.db.execute(overdue_tasks_q)
        ).scalar_one()

        # 2. High Priority
        high_findings_q = select(func.count(AuditFinding.id)).where(
            AuditFinding.company_id == company_id,
            AuditFinding.severity == AuditFindingSeverity.HIGH,
            AuditFinding.status.notin_([AuditFindingStatus.RESOLVED, AuditFindingStatus.CLOSED]),
        )
        due_3days = today + timedelta(days=3)
        due_soon_tasks_q = select(func.count(ComplianceTask.id)).where(
            ComplianceTask.company_id == company_id,
            ComplianceTask.status.in_([ComplianceTaskStatus.PENDING, ComplianceTaskStatus.IN_PROGRESS]),
            ComplianceTask.due_date >= today,
            ComplianceTask.due_date <= due_3days,
        )
        unallocated_tds_q = select(func.count(TDSTransaction.id)).where(
            TDSTransaction.company_id == company_id,
            TDSTransaction.status == TDSTransactionStatus.DEDUCTED,
            ~TDSTransaction.id.in_(select(TDSChallanAllocation.tds_transaction_id)),
        )
        high_priority_count = (
            (await self.db.execute(high_findings_q)).scalar_one()
            + (await self.db.execute(due_soon_tasks_q)).scalar_one()
            + (await self.db.execute(unallocated_tds_q)).scalar_one()
        )

        # 3. Due Soon (7 days)
        due_7days_tasks_q = select(func.count(ComplianceTask.id)).where(
            ComplianceTask.company_id == company_id,
            ComplianceTask.status.in_([ComplianceTaskStatus.PENDING, ComplianceTaskStatus.IN_PROGRESS]),
            ComplianceTask.due_date >= today,
            ComplianceTask.due_date <= due_soon_threshold,
        )
        due_soon_count = (await self.db.execute(due_7days_tasks_q)).scalar_one()

        # 4. Pending Review
        bank_review_q = select(func.count(BankReconciliation.id)).where(
            BankReconciliation.company_id == company_id,
            BankReconciliation.status == BankReconciliationStatus.PENDING_REVIEW,
        )
        bank_tx_review_q = select(func.count(BankTransaction.id)).where(
            BankTransaction.company_id == company_id,
            BankTransaction.reconciliation_status.in_([
                BankTransactionReconciliationStatus.REVIEW_REQUIRED,
                BankTransactionReconciliationStatus.MATCH_SUGGESTED,
            ]),
        )
        itr_review_q = select(func.count(ITRPreparation.id)).where(
            ITRPreparation.company_id == company_id,
            ITRPreparation.status == ITRPreparationStatus.READY_FOR_REVIEW,
        )
        audit_review_q = select(func.count(AuditEngagement.id)).where(
            AuditEngagement.company_id == company_id,
            AuditEngagement.status == AuditEngagementStatus.PENDING_AUDITOR_REVIEW,
        )
        compliance_review_q = select(func.count(ComplianceTask.id)).where(
            ComplianceTask.company_id == company_id,
            ComplianceTask.status == ComplianceTaskStatus.PENDING_REVIEW,
        )
        pending_review_count = (
            (await self.db.execute(bank_review_q)).scalar_one()
            + (await self.db.execute(bank_tx_review_q)).scalar_one()
            + (await self.db.execute(itr_review_q)).scalar_one()
            + (await self.db.execute(audit_review_q)).scalar_one()
            + (await self.db.execute(compliance_review_q)).scalar_one()
        )

        # 5. Overdue
        overdue_count = (await self.db.execute(overdue_tasks_q)).scalar_one()

        # 6. Completed
        comp_tasks_q = select(func.count(ComplianceTask.id)).where(
            ComplianceTask.company_id == company_id,
            ComplianceTask.status.in_([ComplianceTaskStatus.COMPLETED, ComplianceTaskStatus.VERIFIED]),
        )
        rec_sessions_q = select(func.count(BankReconciliation.id)).where(
            BankReconciliation.company_id == company_id,
            BankReconciliation.status.in_([BankReconciliationStatus.RECONCILED, BankReconciliationStatus.LOCKED]),
        )
        closed_audits_q = select(func.count(AuditEngagement.id)).where(
            AuditEngagement.company_id == company_id,
            AuditEngagement.status.in_([AuditEngagementStatus.CLOSED, AuditEngagementStatus.SIGNED_OFF]),
        )
        completed_count = (
            (await self.db.execute(comp_tasks_q)).scalar_one()
            + (await self.db.execute(rec_sessions_q)).scalar_one()
            + (await self.db.execute(closed_audits_q)).scalar_one()
        )

        # FY info
        fy_q = select(FinancialYear).where(FinancialYear.company_id == company_id).order_by(FinancialYear.start_date.desc()).limit(1)
        fy_row = (await self.db.execute(fy_q)).scalar_one_or_none()
        fy_name = fy_row.name if fy_row else None
        fy_id = fy_row.id if fy_row else None

        # Last data update
        last_inv_q = select(func.max(SalesInvoice.updated_at)).where(SalesInvoice.company_id == company_id)
        last_update = (await self.db.execute(last_inv_q)).scalar_one_or_none() or datetime.now(timezone.utc)

        return DashboardSummary(
            company_id=company_id,
            company_name=company_name,
            financial_year=fy_name,
            financial_year_id=fy_id,
            active_period=f"{today.strftime('%B %Y')}",
            last_data_update=last_update,
            attention=AttentionSummary(
                critical_count=critical_count,
                high_priority_count=high_priority_count,
                due_soon_count=due_soon_count,
                pending_review_count=pending_review_count,
                overdue_count=overdue_count,
                completed_count=completed_count,
            ),
            role=role_code,
        )

    async def get_actions(
        self, company_id: uuid.UUID, current_user: User, role_code: str
    ) -> list[DashboardActionItem]:
        items: list[DashboardActionItem] = []
        today = date.today()

        # 1. GST Actions
        gst_periods = (
            await self.db.execute(
                select(GSTReturnPeriod)
                .where(
                    GSTReturnPeriod.company_id == company_id,
                    GSTReturnPeriod.status.in_([GSTReturnPeriodStatus.OPEN, GSTReturnPeriodStatus.UNDER_REVIEW]),
                )
                .order_by(GSTReturnPeriod.year.desc(), GSTReturnPeriod.month.desc())
                .limit(3)
            )
        ).scalars().all()
        for gp in gst_periods:
            items.append(
                DashboardActionItem(
                    id=f"gst-period-{gp.id}",
                    title=f"GST Return {gp.month}/{gp.year} Pending",
                    description=f"Prepare and review GSTR-1 and GSTR-3B filings for period {gp.month}/{gp.year}",
                    module="GST",
                    severity="HIGH" if gp.status == GSTReturnPeriodStatus.OPEN else "MEDIUM",
                    category="TAX",
                    due_date=str(gp.period_end),
                    status=str(gp.status),
                    target_url=f"/gst/return-periods/{gp.id}",
                    responsible_roles=["COMPANY_ADMIN", "ACCOUNTANT"],
                    source_reference=f"gst_return_period:{gp.id}",
                )
            )

        # 2. TDS Actions
        unalloc_tds_count = (
            await self.db.execute(
                select(func.count(TDSTransaction.id)).where(
                    TDSTransaction.company_id == company_id,
                    TDSTransaction.status == TDSTransactionStatus.DEDUCTED,
                    ~TDSTransaction.id.in_(select(TDSChallanAllocation.tds_transaction_id)),
                )
            )
        ).scalar_one()
        if unalloc_tds_count > 0:
            items.append(
                DashboardActionItem(
                    id="tds-unallocated-challans",
                    title=f"TDS Challan Allocation Pending ({unalloc_tds_count} items)",
                    description=f"{unalloc_tds_count} deducted TDS transactions need to be allocated to government deposit challans",
                    module="TDS",
                    severity="HIGH",
                    category="TAX",
                    status="ACTION_REQUIRED",
                    target_url="/tds/challans",
                    responsible_roles=["COMPANY_ADMIN", "ACCOUNTANT"],
                    source_reference="tds:unallocated",
                )
            )

        calc_tds_count = (
            await self.db.execute(
                select(func.count(TDSTransaction.id)).where(
                    TDSTransaction.company_id == company_id,
                    TDSTransaction.status == TDSTransactionStatus.CALCULATED,
                )
            )
        ).scalar_one()
        if calc_tds_count > 0:
            items.append(
                DashboardActionItem(
                    id="tds-calculated-pending-deduction",
                    title=f"TDS Deduction Pending ({calc_tds_count} transactions)",
                    description=f"{calc_tds_count} transactions have calculated tax amounts ready for deduction approval",
                    module="TDS",
                    severity="MEDIUM",
                    category="TAX",
                    status="CALCULATED",
                    target_url="/tds/transactions",
                    responsible_roles=["COMPANY_ADMIN", "ACCOUNTANT"],
                    source_reference="tds:calculated",
                )
            )

        # 3. Bank Actions
        unmatched_bank_tx = (
            await self.db.execute(
                select(func.count(BankTransaction.id)).where(
                    BankTransaction.company_id == company_id,
                    BankTransaction.reconciliation_status.in_([
                        BankTransactionReconciliationStatus.UNMATCHED,
                        BankTransactionReconciliationStatus.REVIEW_REQUIRED,
                        BankTransactionReconciliationStatus.MATCH_SUGGESTED,
                    ]),
                )
            )
        ).scalar_one()
        if unmatched_bank_tx > 0:
            items.append(
                DashboardActionItem(
                    id="bank-unmatched-tx",
                    title=f"{unmatched_bank_tx} Bank Transactions Require Matching",
                    description="Imported bank transactions need to be matched against book receipts, payments, or adjusted via journal",
                    module="BANK",
                    severity="HIGH" if unmatched_bank_tx > 5 else "MEDIUM",
                    category="RECONCILIATION",
                    status="UNMATCHED",
                    target_url="/bank/transactions",
                    responsible_roles=["COMPANY_ADMIN", "ACCOUNTANT"],
                    source_reference="bank:unmatched",
                )
            )

        bank_review_sessions = (
            await self.db.execute(
                select(BankReconciliation)
                .where(
                    BankReconciliation.company_id == company_id,
                    BankReconciliation.status == BankReconciliationStatus.PENDING_REVIEW,
                )
                .limit(2)
            )
        ).scalars().all()
        for br in bank_review_sessions:
            items.append(
                DashboardActionItem(
                    id=f"bank-recon-{br.id}",
                    title="Bank Reconciliation Session Awaiting Approval",
                    description=f"Period {br.period_start} to {br.period_end} submitted for review and approval lock",
                    module="BANK",
                    severity="HIGH",
                    category="RECONCILIATION",
                    status="PENDING_REVIEW",
                    target_url=f"/bank/reconciliations/{br.id}",
                    responsible_roles=["COMPANY_ADMIN", "AUDITOR"],
                    source_reference=f"bank_reconciliation:{br.id}",
                )
            )

        # 4. Accounting Actions
        draft_sales_count = (
            await self.db.execute(
                select(func.count(SalesInvoice.id)).where(
                    SalesInvoice.company_id == company_id, SalesInvoice.status == TransactionStatus.DRAFT
                )
            )
        ).scalar_one()
        if draft_sales_count > 0:
            items.append(
                DashboardActionItem(
                    id="accounting-draft-sales",
                    title=f"{draft_sales_count} Draft Sales Invoices to Post",
                    description="Invoices saved in draft status require posting to update general ledgers and GST registers",
                    module="ACCOUNTING",
                    severity="MEDIUM",
                    category="ACCOUNTING",
                    status="DRAFT",
                    target_url="/accounting/sales-invoices",
                    responsible_roles=["COMPANY_ADMIN", "ACCOUNTANT"],
                    source_reference="sales_invoice:draft",
                )
            )

        draft_purchase_count = (
            await self.db.execute(
                select(func.count(PurchaseInvoice.id)).where(
                    PurchaseInvoice.company_id == company_id, PurchaseInvoice.status == TransactionStatus.DRAFT
                )
            )
        ).scalar_one()
        if draft_purchase_count > 0:
            items.append(
                DashboardActionItem(
                    id="accounting-draft-purchases",
                    title=f"{draft_purchase_count} Draft Purchase Invoices to Post",
                    description="Vendor bills saved in draft require validation and posting for ITC entitlement and payable tracking",
                    module="ACCOUNTING",
                    severity="MEDIUM",
                    category="ACCOUNTING",
                    status="DRAFT",
                    target_url="/accounting/purchase-invoices",
                    responsible_roles=["COMPANY_ADMIN", "ACCOUNTANT"],
                    source_reference="purchase_invoice:draft",
                )
            )

        # 5. Income Tax Actions
        itr_reviews = (
            await self.db.execute(
                select(ITRPreparation)
                .where(
                    ITRPreparation.company_id == company_id,
                    ITRPreparation.status == ITRPreparationStatus.READY_FOR_REVIEW,
                )
                .limit(2)
            )
        ).scalars().all()
        for itr in itr_reviews:
            items.append(
                DashboardActionItem(
                    id=f"income-tax-itr-{itr.id}",
                    title=f"ITR Filing Preparation ({itr.itr_form_type}) Requires Sign-Off",
                    description="Tax computation and form schedules have been validated and await Chartered Accountant sign-off",
                    module="INCOME_TAX",
                    severity="HIGH",
                    category="TAX",
                    status="READY_FOR_REVIEW",
                    target_url="/income-tax/computations",
                    responsible_roles=["COMPANY_ADMIN", "AUDITOR"],
                    source_reference=f"itr_preparation:{itr.id}",
                )
            )

        # 6. Audit Actions
        findings = (
            await self.db.execute(
                select(AuditFinding)
                .where(
                    AuditFinding.company_id == company_id,
                    AuditFinding.status.notin_([AuditFindingStatus.RESOLVED, AuditFindingStatus.CLOSED]),
                )
                .order_by(AuditFinding.severity.desc(), AuditFinding.created_at.desc())
                .limit(5)
            )
        ).scalars().all()
        for finding in findings:
            items.append(
                DashboardActionItem(
                    id=f"audit-finding-{finding.id}",
                    title=f"Audit Finding [{finding.severity}]: {finding.title}",
                    description=finding.description or "Open audit observation requiring management response or resolution",
                    module="AUDIT",
                    severity=str(finding.severity),
                    category="AUDIT",
                    status=str(finding.status),
                    target_url=f"/audits/engagements/{finding.engagement_id}",
                    responsible_roles=["COMPANY_ADMIN", "AUDITOR", "ACCOUNTANT"],
                    source_reference=f"audit_finding:{finding.id}",
                )
            )

        # 7. Compliance Tasks
        tasks = (
            await self.db.execute(
                select(ComplianceTask)
                .where(
                    ComplianceTask.company_id == company_id,
                    ComplianceTask.status.in_([
                        ComplianceTaskStatus.PENDING,
                        ComplianceTaskStatus.IN_PROGRESS,
                        ComplianceTaskStatus.PENDING_REVIEW,
                        ComplianceTaskStatus.OVERDUE,
                    ]),
                )
                .order_by(ComplianceTask.due_date.asc())
                .limit(6)
            )
        ).scalars().all()
        for task in tasks:
            is_overdue = task.status == ComplianceTaskStatus.OVERDUE or (task.due_date and task.due_date < today)
            items.append(
                DashboardActionItem(
                    id=f"compliance-task-{task.id}",
                    title=f"{'Overdue: ' if is_overdue else ''}{task.title}",
                    description=task.description or f"Compliance obligation due {task.due_date}",
                    module="COMPLIANCE",
                    severity="CRITICAL" if is_overdue else "HIGH",
                    category="COMPLIANCE",
                    due_date=str(task.due_date) if task.due_date else None,
                    status=str(task.status),
                    target_url=f"/compliance/tasks/{task.id}",
                    responsible_roles=["COMPANY_ADMIN", "ACCOUNTANT"],
                    source_reference=f"compliance_task:{task.id}",
                )
            )

        # Sort items by severity priority (CRITICAL > HIGH > MEDIUM > LOW > INFO)
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        items.sort(key=lambda x: order.get(x.severity, 99))
        return items

    async def get_workflow(self, company_id: uuid.UUID) -> list[WorkflowStage]:
        stages: list[WorkflowStage] = []

        # 1. DATA INPUT
        doc_count = (await self.db.execute(select(func.count(Document.id)).where(Document.company_id == company_id))).scalar_one()
        import_count = (await self.db.execute(select(func.count(ImportJob.id)).where(ImportJob.company_id == company_id))).scalar_one()
        input_status = "COMPLETE" if (doc_count > 0 or import_count > 0) else "NOT_STARTED"
        stages.append(
            WorkflowStage(
                stage_key="DATA_INPUT",
                name="Data Ingestion",
                status=input_status,
                pending_count=0,
                blocking_count=0,
                next_action_label="Upload document" if doc_count == 0 else "Import files",
                next_action_url="/documents",
            )
        )

        # 2. ACCOUNTING
        posted_inv = (
            await self.db.execute(
                select(func.count(SalesInvoice.id)).where(
                    SalesInvoice.company_id == company_id, SalesInvoice.status == TransactionStatus.POSTED
                )
            )
        ).scalar_one()
        draft_inv = (
            await self.db.execute(
                select(func.count(SalesInvoice.id)).where(
                    SalesInvoice.company_id == company_id, SalesInvoice.status == TransactionStatus.DRAFT
                )
            )
        ).scalar_one()
        acc_status = "COMPLETE" if (posted_inv > 0 and draft_inv == 0) else ("IN_PROGRESS" if (posted_inv > 0 or draft_inv > 0) else "NOT_STARTED")
        stages.append(
            WorkflowStage(
                stage_key="ACCOUNTING",
                name="Double-Entry Accounting",
                status=acc_status,
                pending_count=draft_inv,
                blocking_count=draft_inv,
                next_action_label="Post invoices" if draft_inv > 0 else "Create invoice",
                next_action_url="/accounting/sales-invoices",
            )
        )

        # 3. GST & TDS
        gst_profile_exists = (
            await self.db.execute(select(func.count(GSTProfile.id)).where(GSTProfile.company_id == company_id))
        ).scalar_one() > 0
        open_periods = (
            await self.db.execute(
                select(func.count(GSTReturnPeriod.id)).where(
                    GSTReturnPeriod.company_id == company_id,
                    GSTReturnPeriod.status == GSTReturnPeriodStatus.OPEN,
                )
            )
        ).scalar_one()
        tax_status = "COMPLETE" if (gst_profile_exists and open_periods == 0) else ("IN_PROGRESS" if gst_profile_exists else "NOT_STARTED")
        stages.append(
            WorkflowStage(
                stage_key="GST_TDS",
                name="GST & TDS Returns",
                status=tax_status,
                pending_count=open_periods,
                blocking_count=0,
                next_action_label="Configure GST" if not gst_profile_exists else "Prepare Returns",
                next_action_url="/gst",
            )
        )

        # 4. BANK RECONCILIATION
        unmatched_bank = (
            await self.db.execute(
                select(func.count(BankTransaction.id)).where(
                    BankTransaction.company_id == company_id,
                    BankTransaction.reconciliation_status != BankTransactionReconciliationStatus.MATCHED,
                )
            )
        ).scalar_one()
        bank_status = "COMPLETE" if unmatched_bank == 0 else "IN_PROGRESS"
        stages.append(
            WorkflowStage(
                stage_key="BANK",
                name="Bank Reconciliation",
                status=bank_status,
                pending_count=unmatched_bank,
                blocking_count=unmatched_bank if unmatched_bank > 5 else 0,
                next_action_label="Reconcile Transactions",
                next_action_url="/bank/transactions",
            )
        )

        # 5. INCOME TAX
        it_profile = (
            await self.db.execute(select(func.count(IncomeTaxProfile.id)).where(IncomeTaxProfile.company_id == company_id))
        ).scalar_one() > 0
        itr_locked = (
            await self.db.execute(
                select(func.count(ITRPreparation.id)).where(
                    ITRPreparation.company_id == company_id,
                    ITRPreparation.status.in_([ITRPreparationStatus.APPROVED, ITRPreparationStatus.LOCKED]),
                )
            )
        ).scalar_one() > 0
        it_status = "COMPLETE" if itr_locked else ("IN_PROGRESS" if it_profile else "NOT_STARTED")
        stages.append(
            WorkflowStage(
                stage_key="INCOME_TAX",
                name="Income Tax & ITR",
                status=it_status,
                pending_count=0 if itr_locked else 1,
                blocking_count=0,
                next_action_label="Compute Taxes" if it_profile else "Configure Profile",
                next_action_url="/income-tax",
            )
        )

        # 6. AUDIT
        open_findings = (
            await self.db.execute(
                select(func.count(AuditFinding.id)).where(
                    AuditFinding.company_id == company_id,
                    AuditFinding.status.notin_([AuditFindingStatus.RESOLVED, AuditFindingStatus.CLOSED]),
                )
            )
        ).scalar_one()
        audit_eng = (
            await self.db.execute(select(func.count(AuditEngagement.id)).where(AuditEngagement.company_id == company_id))
        ).scalar_one()
        audit_status = "COMPLETE" if (audit_eng > 0 and open_findings == 0) else ("IN_PROGRESS" if audit_eng > 0 else "NOT_STARTED")
        stages.append(
            WorkflowStage(
                stage_key="AUDIT",
                name="Statutory Audit",
                status=audit_status,
                pending_count=open_findings,
                blocking_count=open_findings,
                next_action_label="Review Findings" if open_findings > 0 else "View Engagements",
                next_action_url="/audits/engagements",
            )
        )

        # 7. COMPLIANCE
        overdue_tasks = (
            await self.db.execute(
                select(func.count(ComplianceTask.id)).where(
                    ComplianceTask.company_id == company_id,
                    ComplianceTask.status.notin_([
                        ComplianceTaskStatus.COMPLETED,
                        ComplianceTaskStatus.VERIFIED,
                        ComplianceTaskStatus.CANCELLED,
                        ComplianceTaskStatus.LOCKED,
                    ]),
                    or_(ComplianceTask.status == ComplianceTaskStatus.OVERDUE, ComplianceTask.due_date < date.today()),
                )
            )
        ).scalar_one()
        comp_status = "BLOCKED" if overdue_tasks > 0 else "COMPLETE"
        stages.append(
            WorkflowStage(
                stage_key="COMPLIANCE",
                name="Compliance Tasks",
                status=comp_status,
                pending_count=overdue_tasks,
                blocking_count=overdue_tasks,
                next_action_label="Complete Overdue Tasks" if overdue_tasks > 0 else "View Calendar",
                next_action_url="/compliance/tasks",
            )
        )

        # 8. REPORTING
        report_service = ReportService(self.db)
        tb = await report_service.trial_balance(company_id, as_of=None)
        rep_status = "COMPLETE" if tb.is_balanced and len(tb.lines) > 0 else ("BLOCKED" if not tb.is_balanced else "NOT_STARTED")
        stages.append(
            WorkflowStage(
                stage_key="REPORTING",
                name="Reconciliation & Reports",
                status=rep_status,
                pending_count=0 if tb.is_balanced else 1,
                blocking_count=0 if tb.is_balanced else 1,
                next_action_label="View Trial Balance",
                next_action_url="/accounting/reports",
            )
        )

        return stages

    async def get_setup_progress(self, company_id: uuid.UUID) -> SetupProgress:
        steps: list[SetupStep] = []

        # 1. Company Profile
        comp = (await self.db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
        step1_done = bool(comp and comp.legal_name and comp.pan)
        steps.append(
            SetupStep(
                key="COMPANY_PROFILE",
                label="Company Profile & Legal Identification",
                completed=step1_done,
                description="Legal entity name, trade name, PAN and registered address",
                target_url=f"/companies/{company_id}",
            )
        )

        # 2. Financial Year
        fy_count = (await self.db.execute(select(func.count(FinancialYear.id)).where(FinancialYear.company_id == company_id))).scalar_one()
        steps.append(
            SetupStep(
                key="FINANCIAL_YEAR",
                label="Financial Year (April–March)",
                completed=fy_count > 0,
                description="Active statutory accounting period for double-entry records",
                target_url="/accounting/financial-years",
            )
        )

        # 3. Chart of Accounts
        ledger_count = (await self.db.execute(select(func.count(Ledger.id)).where(Ledger.company_id == company_id))).scalar_one()
        steps.append(
            SetupStep(
                key="CHART_OF_ACCOUNTS",
                label="Core Chart of Accounts",
                completed=ledger_count >= 13,
                description="13 standardized general ledgers (Cash, Bank, Debtors, Creditors, GST)",
                target_url="/accounting/ledgers",
            )
        )

        # 4. GST Profile
        gst_prof = (await self.db.execute(select(func.count(GSTProfile.id)).where(GSTProfile.company_id == company_id))).scalar_one()
        steps.append(
            SetupStep(
                key="GST_PROFILE",
                label="GST Registration & Profile",
                completed=gst_prof > 0,
                description="15-digit GSTIN, state code, and return filing frequency configuration",
                target_url="/gst",
            )
        )

        # 5. TDS Profile
        tds_prof = (await self.db.execute(select(func.count(TDSProfile.id)).where(TDSProfile.company_id == company_id))).scalar_one()
        steps.append(
            SetupStep(
                key="TDS_PROFILE",
                label="TDS Deductor Profile",
                completed=tds_prof > 0,
                description="10-character Tax Deduction Account Number (TAN) and deductor category",
                target_url="/tds",
            )
        )

        # 6. Bank Account
        bank_count = (await self.db.execute(select(func.count(BankAccount.id)).where(BankAccount.company_id == company_id))).scalar_one()
        steps.append(
            SetupStep(
                key="BANK_ACCOUNT",
                label="Bank Account & Ledger Linking",
                completed=bank_count > 0,
                description="Commercial bank account linked with dedicated double-entry bank ledger",
                target_url="/bank/accounts",
            )
        )

        # 7. Opening Balances
        ob_count = (await self.db.execute(select(func.count(OpeningBalance.id)).where(OpeningBalance.company_id == company_id))).scalar_one()
        steps.append(
            SetupStep(
                key="OPENING_BALANCES",
                label="Opening Balances Confirmation",
                completed=ob_count > 0,
                description="Prior year balance sheet carry-forwards verified and posted",
                target_url="/accounting/opening-balances",
            )
        )

        # 8. First Accounting Transaction / Import
        tx_count = (
            (await self.db.execute(select(func.count(SalesInvoice.id)).where(SalesInvoice.company_id == company_id))).scalar_one()
            + (await self.db.execute(select(func.count(PurchaseInvoice.id)).where(PurchaseInvoice.company_id == company_id))).scalar_one()
            + (await self.db.execute(select(func.count(JournalEntry.id)).where(JournalEntry.company_id == company_id))).scalar_one()
            + (await self.db.execute(select(func.count(ImportJob.id)).where(ImportJob.company_id == company_id))).scalar_one()
        )
        steps.append(
            SetupStep(
                key="FIRST_TRANSACTION",
                label="First Transaction or Statement Import",
                completed=tx_count > 0,
                description="Initial sales bill, purchase invoice, or CSV data batch ingestion",
                target_url="/accounting/sales-invoices/new",
            )
        )

        completed_count = sum(1 for s in steps if s.completed)
        return SetupProgress(
            completed_count=completed_count,
            total_count=len(steps),
            is_all_complete=completed_count == len(steps),
            steps=steps,
        )

    async def get_health(self, company_id: uuid.UUID) -> CompanyHealth:
        areas: list[HealthAreaStatus] = []

        # 1. Accounting Health
        ledgers = (await self.db.execute(select(func.count(Ledger.id)).where(Ledger.company_id == company_id))).scalar_one()
        draft_sales = (await self.db.execute(select(func.count(SalesInvoice.id)).where(SalesInvoice.company_id == company_id, SalesInvoice.status == TransactionStatus.DRAFT))).scalar_one()
        report_service = ReportService(self.db)
        tb = await report_service.trial_balance(company_id, as_of=None)
        if ledgers == 0:
            acc_status = "NOT_CONFIGURED"
            acc_msg = "Chart of Accounts not initialized"
        elif not tb.is_balanced:
            acc_status = "BLOCKED"
            acc_msg = f"Trial balance out of balance by {abs(tb.total_debit - tb.total_credit)}"
        elif draft_sales > 0:
            acc_status = "NEEDS_ATTENTION"
            acc_msg = f"{draft_sales} draft invoices awaiting posting"
        else:
            acc_status = "READY"
            acc_msg = "Ledgers balanced and in good standing"
        areas.append(
            HealthAreaStatus(
                area="Accounting",
                status=acc_status,
                message=acc_msg,
                metrics={"ledgers": ledgers, "is_balanced": tb.is_balanced, "draft_invoices": draft_sales},
                target_url="/accounting/dashboard",
            )
        )

        # 2. GST Health
        gst_prof = (await self.db.execute(select(func.count(GSTProfile.id)).where(GSTProfile.company_id == company_id))).scalar_one() > 0
        open_periods = (await self.db.execute(select(func.count(GSTReturnPeriod.id)).where(GSTReturnPeriod.company_id == company_id, GSTReturnPeriod.status == GSTReturnPeriodStatus.OPEN))).scalar_one()
        if not gst_prof:
            gst_st = "NOT_CONFIGURED"
            gst_msg = "GST profile not configured"
        elif open_periods > 0:
            gst_st = "NEEDS_ATTENTION"
            gst_msg = f"{open_periods} return periods pending filing"
        else:
            gst_st = "READY"
            gst_msg = "All return periods up to date"
        areas.append(
            HealthAreaStatus(
                area="GST",
                status=gst_st,
                message=gst_msg,
                metrics={"profile_configured": gst_prof, "open_periods": open_periods},
                target_url="/gst",
            )
        )

        # 3. TDS Health
        tds_prof = (await self.db.execute(select(func.count(TDSProfile.id)).where(TDSProfile.company_id == company_id))).scalar_one() > 0
        unalloc_tds = (await self.db.execute(select(func.count(TDSTransaction.id)).where(TDSTransaction.company_id == company_id, TDSTransaction.status == TDSTransactionStatus.DEDUCTED, ~TDSTransaction.id.in_(select(TDSChallanAllocation.tds_transaction_id))))).scalar_one()
        if not tds_prof:
            tds_st = "NOT_CONFIGURED"
            tds_msg = "TDS profile not configured"
        elif unalloc_tds > 0:
            tds_st = "NEEDS_ATTENTION"
            tds_msg = f"{unalloc_tds} deducted transactions unallocated to challans"
        else:
            tds_st = "READY"
            tds_msg = "TDS deductions allocated to challans"
        areas.append(
            HealthAreaStatus(
                area="TDS",
                status=tds_st,
                message=tds_msg,
                metrics={"profile_configured": tds_prof, "unallocated_transactions": unalloc_tds},
                target_url="/tds",
            )
        )

        # 4. Bank Health
        bank_accounts = (await self.db.execute(select(func.count(BankAccount.id)).where(BankAccount.company_id == company_id))).scalar_one()
        unmatched_bank = (await self.db.execute(select(func.count(BankTransaction.id)).where(BankTransaction.company_id == company_id, BankTransaction.reconciliation_status != BankTransactionReconciliationStatus.MATCHED))).scalar_one()
        if bank_accounts == 0:
            bank_st = "NOT_CONFIGURED"
            bank_msg = "No bank accounts linked"
        elif unmatched_bank > 0:
            bank_st = "NEEDS_ATTENTION"
            bank_msg = f"{unmatched_bank} transactions awaiting reconciliation"
        else:
            bank_st = "READY"
            bank_msg = "All bank statements reconciled"
        areas.append(
            HealthAreaStatus(
                area="Bank",
                status=bank_st,
                message=bank_msg,
                metrics={"accounts": bank_accounts, "unmatched_transactions": unmatched_bank},
                target_url="/bank",
            )
        )

        # 5. Income Tax Health
        it_prof = (await self.db.execute(select(func.count(IncomeTaxProfile.id)).where(IncomeTaxProfile.company_id == company_id))).scalar_one() > 0
        computations_count = (await self.db.execute(select(func.count(TaxComputation.id)).where(TaxComputation.company_id == company_id))).scalar_one()
        draft_comp = (await self.db.execute(select(func.count(TaxComputation.id)).where(TaxComputation.company_id == company_id, TaxComputation.status == TaxComputationStatus.DRAFT))).scalar_one()
        if not it_prof:
            it_st = "NOT_CONFIGURED"
            it_msg = "Income Tax profile not set up"
        elif draft_comp > 0:
            it_st = "NEEDS_ATTENTION"
            it_msg = f"{draft_comp} draft tax computations in progress"
        else:
            it_st = "READY"
            it_msg = "Tax computations reviewed"
        areas.append(
            HealthAreaStatus(
                area="IncomeTax",
                status=it_st,
                message=it_msg,
                metrics={"profile_configured": it_prof, "computations": computations_count},
                target_url="/income-tax",
            )
        )

        # 6. Audit Health
        engagements = (await self.db.execute(select(func.count(AuditEngagement.id)).where(AuditEngagement.company_id == company_id))).scalar_one()
        open_findings = (await self.db.execute(select(func.count(AuditFinding.id)).where(AuditFinding.company_id == company_id, AuditFinding.status.notin_([AuditFindingStatus.RESOLVED, AuditFindingStatus.CLOSED])))).scalar_one()
        if engagements == 0:
            aud_st = "NOT_CONFIGURED"
            aud_msg = "No audit engagements active"
        elif open_findings > 0:
            aud_st = "NEEDS_ATTENTION"
            aud_msg = f"{open_findings} unresolved audit findings"
        else:
            aud_st = "READY"
            aud_msg = "Audit observations resolved"
        areas.append(
            HealthAreaStatus(
                area="Audit",
                status=aud_st,
                message=aud_msg,
                metrics={"engagements": engagements, "open_findings": open_findings},
                target_url="/audits",
            )
        )

        # 7. Compliance Health
        obligations = (await self.db.execute(select(func.count(ComplianceObligation.id)).where(ComplianceObligation.company_id == company_id))).scalar_one()
        overdue_tasks = (await self.db.execute(select(func.count(ComplianceTask.id)).where(ComplianceTask.company_id == company_id, ComplianceTask.status.notin_([ComplianceTaskStatus.COMPLETED, ComplianceTaskStatus.VERIFIED, ComplianceTaskStatus.CANCELLED, ComplianceTaskStatus.LOCKED]), or_(ComplianceTask.status == ComplianceTaskStatus.OVERDUE, ComplianceTask.due_date < date.today())))).scalar_one()
        if obligations == 0:
            comp_st = "NOT_CONFIGURED"
            comp_msg = "No compliance obligations configured"
        elif overdue_tasks > 0:
            comp_st = "BLOCKED"
            comp_msg = f"{overdue_tasks} overdue statutory tasks"
        else:
            comp_st = "READY"
            comp_msg = "All statutory deadlines met"
        areas.append(
            HealthAreaStatus(
                area="Compliance",
                status=comp_st,
                message=comp_msg,
                metrics={"obligations": obligations, "overdue_tasks": overdue_tasks},
                target_url="/compliance/calendar",
            )
        )

        # Overall Status
        if any(a.status == "BLOCKED" for a in areas):
            overall = "BLOCKED"
        elif any(a.status == "NEEDS_ATTENTION" for a in areas):
            overall = "NEEDS_ATTENTION"
        elif all(a.status == "READY" for a in areas):
            overall = "READY"
        else:
            overall = "NEEDS_ATTENTION"

        return CompanyHealth(overall_status=overall, areas=areas)

    async def get_action_center(
        self,
        company_id: uuid.UUID,
        current_user: User,
        role_code: str,
        *,
        category: str | None = None,
        severity: str | None = None,
        module: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        all_actions = await self.get_actions(company_id, current_user, role_code)

        filtered = all_actions
        if category:
            cat_upper = category.upper()
            if cat_upper in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
                filtered = [a for a in filtered if a.severity == cat_upper]
            elif cat_upper == "DUE_SOON":
                filtered = [a for a in filtered if a.due_date and a.due_date <= str(date.today() + timedelta(days=7))]
            elif cat_upper == "OVERDUE":
                filtered = [a for a in filtered if a.due_date and a.due_date < str(date.today())]
            elif cat_upper in ("REVIEW_REQUIRED", "PENDING_REVIEW"):
                filtered = [a for a in filtered if "review" in a.status.lower() or "review" in a.title.lower()]
            else:
                filtered = [a for a in filtered if a.category.upper() == cat_upper]

        if severity:
            filtered = [a for a in filtered if a.severity.upper() == severity.upper()]

        if module:
            filtered = [a for a in filtered if a.module.upper() == module.upper()]

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        paged_items = filtered[start:end]

        return {
            "items": [
                ActionCenterItem(
                    id=item.id,
                    title=item.title,
                    description=item.description,
                    module=item.module,
                    severity=item.severity,
                    category=item.category,
                    due_date=item.due_date,
                    created_date=item.created_date,
                    status=item.status,
                    target_url=item.target_url,
                    responsible_roles=item.responsible_roles,
                    source_reference=item.source_reference,
                )
                for item in paged_items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
