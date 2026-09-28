"""Deterministic Compliance Health Service (PHASE13 §9).

Evaluates company-level compliance health without opaque black-box AI scores.
Aggregates deterministic metrics across obligations, tasks, audit findings,
bank reconciliations, and tax readiness. Every reason affecting health is
explicitly itemized for transparency.

Statuses:
- HEALTHY: No overdue obligations, no blocked items, no critical findings.
- ATTENTION_REQUIRED: Upcoming deadlines due in <= 7 days or minor reconciliations pending.
- AT_RISK: Blocked obligations, unresolved high/critical findings, or missing prerequisites.
- OVERDUE: One or more compliance obligations or tasks are past their due date.
"""

import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_finding import AuditFinding
from app.models.audit_workflow_enums import AuditFindingSeverity, AuditFindingStatus
from app.models.bank_enums import BankTransactionReconciliationStatus
from app.models.bank_transaction import BankTransaction
from app.models.compliance_enums import (
    ComplianceHealthStatus,
    ComplianceObligationStatus,
    ComplianceTaskStatus,
    ReadinessStatus,
)
from app.models.compliance_obligation import ComplianceObligation
from app.models.compliance_task import ComplianceTask
from app.models.tds_enums import TDSTransactionStatus
from app.models.tds_transaction import TDSTransaction


class ComplianceHealthResult:
    def __init__(
        self,
        health_status: ComplianceHealthStatus,
        score: int,
        summary: str,
        reasons: list[str],
        dimensions: dict[str, int],
    ) -> None:
        self.health_status = health_status
        self.score = score
        self.summary = summary
        self.reasons = reasons
        self.dimensions = dimensions

    def to_dict(self) -> dict[str, Any]:
        return {
            "health_status": self.health_status.value,
            "score": self.score,
            "summary": self.summary,
            "reasons": self.reasons,
            "dimensions": self.dimensions,
        }


class ComplianceHealthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def compute_company_health(self, company_id: uuid.UUID) -> ComplianceHealthResult:
        today = date.today()
        due_soon_threshold = today + timedelta(days=7)
        reasons: list[str] = []

        # 1. Overdue Obligations
        closed_statuses = [
            ComplianceObligationStatus.COMPLETED,
            ComplianceObligationStatus.FULFILLED,
            ComplianceObligationStatus.CANCELLED,
        ]
        overdue_ob_q = select(func.count(ComplianceObligation.id)).where(
            ComplianceObligation.company_id == company_id,
            ComplianceObligation.active.is_(True),
            ComplianceObligation.status.notin_(closed_statuses),
            or_(
                ComplianceObligation.status == ComplianceObligationStatus.OVERDUE,
                ComplianceObligation.due_date < today,
            ),
        )
        overdue_obligations = (await self.db.execute(overdue_ob_q)).scalar_one()

        # 2. Overdue Tasks
        closed_task_statuses = [
            ComplianceTaskStatus.COMPLETED,
            ComplianceTaskStatus.VERIFIED,
            ComplianceTaskStatus.CANCELLED,
            ComplianceTaskStatus.LOCKED,
        ]
        overdue_task_q = select(func.count(ComplianceTask.id)).where(
            ComplianceTask.company_id == company_id,
            ComplianceTask.status.notin_(closed_task_statuses),
            or_(
                ComplianceTask.status == ComplianceTaskStatus.OVERDUE,
                ComplianceTask.due_date < today,
            ),
        )
        overdue_tasks = (await self.db.execute(overdue_task_q)).scalar_one()
        total_overdue = overdue_obligations + overdue_tasks

        if overdue_obligations > 0:
            reasons.append(f"{overdue_obligations} compliance obligation(s) overdue past statutory due date")
        if overdue_tasks > 0:
            reasons.append(f"{overdue_tasks} compliance task(s) overdue")

        # 3. Blocked Obligations
        blocked_ob_q = select(func.count(ComplianceObligation.id)).where(
            ComplianceObligation.company_id == company_id,
            ComplianceObligation.active.is_(True),
            or_(
                ComplianceObligation.status == ComplianceObligationStatus.BLOCKED,
                ComplianceObligation.readiness_status == ReadinessStatus.BLOCKED.value,
            ),
        )
        blocked_obligations = (await self.db.execute(blocked_ob_q)).scalar_one()
        if blocked_obligations > 0:
            reasons.append(f"{blocked_obligations} compliance obligation(s) blocked by prerequisite data failures")

        # 4. Due Soon (next 7 days)
        due_soon_ob_q = select(func.count(ComplianceObligation.id)).where(
            ComplianceObligation.company_id == company_id,
            ComplianceObligation.active.is_(True),
            ComplianceObligation.status.notin_(closed_statuses),
            ComplianceObligation.due_date >= today,
            ComplianceObligation.due_date <= due_soon_threshold,
        )
        due_soon_obligations = (await self.db.execute(due_soon_ob_q)).scalar_one()
        if due_soon_obligations > 0:
            reasons.append(f"{due_soon_obligations} obligation(s) due within the next 7 days")

        # 5. Pending Reviews
        pending_review_ob_q = select(func.count(ComplianceObligation.id)).where(
            ComplianceObligation.company_id == company_id,
            ComplianceObligation.active.is_(True),
            ComplianceObligation.status.in_([
                ComplianceObligationStatus.UNDER_REVIEW,
                ComplianceObligationStatus.READY_FOR_REVIEW,
            ]),
        )
        pending_reviews = (await self.db.execute(pending_review_ob_q)).scalar_one()
        if pending_reviews > 0:
            reasons.append(f"{pending_reviews} obligation(s) awaiting auditor or admin review")

        # 6. Unresolved Critical/High Audit Findings
        findings_q = select(func.count(AuditFinding.id)).where(
            AuditFinding.company_id == company_id,
            AuditFinding.severity.in_([AuditFindingSeverity.CRITICAL, AuditFindingSeverity.HIGH]),
            AuditFinding.status.notin_([AuditFindingStatus.RESOLVED, AuditFindingStatus.CLOSED]),
        )
        critical_findings = (await self.db.execute(findings_q)).scalar_one()
        if critical_findings > 0:
            reasons.append(f"{critical_findings} unresolved CRITICAL/HIGH audit finding(s)")

        # 7. Unreconciled Bank Transactions
        unmatched_bank_q = select(func.count(BankTransaction.id)).where(
            BankTransaction.company_id == company_id,
            BankTransaction.reconciliation_status == BankTransactionReconciliationStatus.UNMATCHED,
        )
        unmatched_bank = (await self.db.execute(unmatched_bank_q)).scalar_one()
        if unmatched_bank > 0:
            reasons.append(f"{unmatched_bank} bank transaction(s) pending reconciliation")

        # 8. Unallocated TDS Transactions
        unallocated_tds_q = select(func.count(TDSTransaction.id)).where(
            TDSTransaction.company_id == company_id,
            TDSTransaction.status == TDSTransactionStatus.DEDUCTED,
        )
        unallocated_tds = (await self.db.execute(unallocated_tds_q)).scalar_one()
        if unallocated_tds > 0:
            reasons.append(f"{unallocated_tds} deducted TDS item(s) unallocated to challans")

        # Deterministic Score Calculation
        score = 100
        score -= min(total_overdue * 25, 50)
        score -= min(blocked_obligations * 20, 30)
        score -= min(critical_findings * 15, 25)
        if due_soon_obligations > 0:
            score -= 5
        if unmatched_bank > 0:
            score -= 5
        if unallocated_tds > 0:
            score -= 5
        score = max(0, min(100, score))

        # Status Assignment
        if total_overdue > 0:
            health_status = ComplianceHealthStatus.OVERDUE
            summary = "Statutory deadlines have lapsed. Immediate remediation required."
        elif blocked_obligations > 0 or critical_findings > 0:
            health_status = ComplianceHealthStatus.AT_RISK
            summary = "Compliance items are blocked or have high-risk audit findings."
        elif due_soon_obligations > 0 or unmatched_bank > 0 or pending_reviews > 0:
            health_status = ComplianceHealthStatus.ATTENTION_REQUIRED
            summary = "Upcoming deadlines or pending review items require attention."
        else:
            health_status = ComplianceHealthStatus.HEALTHY
            summary = "All compliance obligations and prerequisites are in order."

        dimensions = {
            "overdue_obligations": overdue_obligations,
            "overdue_tasks": overdue_tasks,
            "total_overdue": total_overdue,
            "blocked_obligations": blocked_obligations,
            "due_soon_obligations": due_soon_obligations,
            "pending_reviews": pending_reviews,
            "critical_audit_findings": critical_findings,
            "unmatched_bank_transactions": unmatched_bank,
            "unallocated_tds_transactions": unallocated_tds,
        }

        return ComplianceHealthResult(
            health_status=health_status,
            score=score,
            summary=summary,
            reasons=reasons,
            dimensions=dimensions,
        )
