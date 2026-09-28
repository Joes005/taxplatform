"""Shared enums for the compliance coordination layer (Phase 9).

Named `compliance_enums` to stay unambiguous next to the pre-existing
platform-wide `AuditLog`/`AuditAction` (Phase 1) and the CA/Auditor
workflow's own `audit_workflow_enums` (Phase 7) — Phase 9 sits on top of
both, and extends rather than duplicates them.
"""

from enum import StrEnum


class ComplianceCategory(StrEnum):
    GST = "GST"
    TDS = "TDS"
    INCOME_TAX = "INCOME_TAX"
    AUDIT = "AUDIT"
    ACCOUNTING = "ACCOUNTING"
    BANK = "BANK"
    GENERAL = "GENERAL"
    OTHER = "OTHER"


class ComplianceModule(StrEnum):
    GST = "GST"
    TDS = "TDS"
    INCOME_TAX = "INCOME_TAX"
    AUDIT = "AUDIT"
    BANK_RECONCILIATION = "BANK_RECONCILIATION"
    ACCOUNTING = "ACCOUNTING"
    DOCUMENTS = "DOCUMENTS"
    GENERAL = "GENERAL"


class ComplianceFrequency(StrEnum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"
    ONE_TIME = "ONE_TIME"
    CUSTOM = "CUSTOM"


class CompliancePriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ComplianceObligationStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    FULFILLED = "FULFILLED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"
    REOPENED = "REOPENED"


class ReadinessStatus(StrEnum):
    READY = "READY"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
    BLOCKED = "BLOCKED"
    MISSING_DATA = "MISSING_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ComplianceHealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    ATTENTION_REQUIRED = "ATTENTION_REQUIRED"
    AT_RISK = "AT_RISK"
    OVERDUE = "OVERDUE"


class ComplianceTaskStatus(StrEnum):
    """PHASE9 §4, §43 — server-side transitions only, enforced by
    `ComplianceTaskService`'s transition table, the same pattern already
    used for `TaxComputationStatus`/`AuditEngagementStatus`.
    `OVERDUE` is an overlay a lightweight sweep applies to a still-open
    task past its due date (PHASE9 §16) — it is never reached through a
    user action, and every forward action a task's underlying state
    supported still applies from it."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_REVIEW = "PENDING_REVIEW"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"
    LOCKED = "LOCKED"


class ComplianceSourceType(StrEnum):
    """Generic reference target tying a task back to the existing module
    record it's actually about (PHASE9 §35) — the same shape
    `TDSTransaction.source_type`/`AuditFinding.source_type` already use."""

    GST_RETURN = "GST_RETURN"
    TDS_RETURN = "TDS_RETURN"
    INCOME_TAX_RETURN = "INCOME_TAX_RETURN"
    AUDIT_ENGAGEMENT = "AUDIT_ENGAGEMENT"
    AUDIT_CHECKLIST = "AUDIT_CHECKLIST"
    BANK_RECONCILIATION = "BANK_RECONCILIATION"
    ACCOUNTING_PERIOD = "ACCOUNTING_PERIOD"
    DOCUMENT = "DOCUMENT"
    MANUAL = "MANUAL"


class NotificationType(StrEnum):
    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_DUE_SOON = "TASK_DUE_SOON"
    TASK_OVERDUE = "TASK_OVERDUE"
    TASK_REVIEW_REQUIRED = "TASK_REVIEW_REQUIRED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_VERIFIED = "TASK_VERIFIED"
    COMMENT_ADDED = "COMMENT_ADDED"
    TASK_REASSIGNED = "TASK_REASSIGNED"
    OBLIGATION_ASSIGNED = "OBLIGATION_ASSIGNED"
    OBLIGATION_DUE_SOON = "OBLIGATION_DUE_SOON"
    OBLIGATION_OVERDUE = "OBLIGATION_OVERDUE"
    OBLIGATION_REVIEW = "OBLIGATION_REVIEW"
    OBLIGATION_APPROVED = "OBLIGATION_APPROVED"
    OBLIGATION_REJECTED = "OBLIGATION_REJECTED"
    OBLIGATION_COMPLETED = "OBLIGATION_COMPLETED"
    OBLIGATION_BLOCKED = "OBLIGATION_BLOCKED"
    OBLIGATION_REOPENED = "OBLIGATION_REOPENED"


class NotificationSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
