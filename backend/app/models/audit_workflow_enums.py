"""Shared enums for the CA/Auditor workflow domain (Phase 7).

Named `audit_workflow_enums` — not `audit_enums` — to stay unambiguous
next to the pre-existing platform-wide `AuditLog`/`AuditAction` (Phase 1
security audit trail), which this phase never touches or duplicates.
"""

from enum import StrEnum


class AuditEngagementType(StrEnum):
    INTERNAL_REVIEW = "INTERNAL_REVIEW"
    TAX_COMPLIANCE_REVIEW = "TAX_COMPLIANCE_REVIEW"
    FINANCIAL_REVIEW = "FINANCIAL_REVIEW"
    BOOKS_REVIEW = "BOOKS_REVIEW"
    PRE_AUDIT_REVIEW = "PRE_AUDIT_REVIEW"
    GENERAL_AUDIT = "GENERAL_AUDIT"
    OTHER = "OTHER"


class AuditEngagementStatus(StrEnum):
    """A controlled lifecycle (PHASE7 §9) — transitions are enforced by
    `AuditEngagementService`'s transition table, never by direct
    assignment elsewhere. `is_locked` (a separate flag on the model) is
    reachable only once CLOSED and is not itself a status value — it's an
    immutability switch layered on top of a terminal status."""

    DRAFT = "DRAFT"
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_REVIEW = "IN_REVIEW"
    PENDING_CLIENT_ACTION = "PENDING_CLIENT_ACTION"
    PENDING_AUDITOR_REVIEW = "PENDING_AUDITOR_REVIEW"
    APPROVED = "APPROVED"
    SIGNED_OFF = "SIGNED_OFF"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class AuditAssignmentRole(StrEnum):
    LEAD_AUDITOR = "LEAD_AUDITOR"
    AUDITOR = "AUDITOR"
    REVIEWER = "REVIEWER"
    ACCOUNTANT = "ACCOUNTANT"
    CLIENT_CONTACT = "CLIENT_CONTACT"


class AuditChecklistItemStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    REQUIRES_ATTENTION = "REQUIRES_ATTENTION"


class AuditChecklistCategory(StrEnum):
    ACCOUNTING = "ACCOUNTING"
    GST = "GST"
    TDS = "TDS"
    BANK = "BANK"
    DOCUMENTS = "DOCUMENTS"
    INTERNAL_CONTROLS = "INTERNAL_CONTROLS"
    OTHER = "OTHER"


class AuditFindingCategory(StrEnum):
    ACCOUNTING = "ACCOUNTING"
    GST = "GST"
    TDS = "TDS"
    BANK = "BANK"
    DOCUMENT = "DOCUMENT"
    DATA_QUALITY = "DATA_QUALITY"
    CONTROL = "CONTROL"
    COMPLIANCE = "COMPLIANCE"
    PROCESS = "PROCESS"
    # --- Income Tax (Phase 8) ---
    INCOME_TAX = "INCOME_TAX"
    TAX_COMPUTATION = "TAX_COMPUTATION"
    ITR_VALIDATION = "ITR_VALIDATION"
    TDS_CREDIT = "TDS_CREDIT"
    DEDUCTION = "DEDUCTION"
    CAPITAL_GAINS = "CAPITAL_GAINS"
    BUSINESS_INCOME = "BUSINESS_INCOME"
    OTHER = "OTHER"


class AuditFindingSeverity(StrEnum):
    """An internal workflow classification, never a legal determination
    (PHASE7 §18) — a HIGH/CRITICAL severity flags something for urgent
    human attention, it does not itself allege wrongdoing."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AuditFindingStatus(StrEnum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_REVIEW = "IN_REVIEW"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    RESPONSE_SUBMITTED = "RESPONSE_SUBMITTED"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


class AuditFindingSourceType(StrEnum):
    """What a finding's `source_type`/`source_id` may point to (PHASE7
    §15) — a generic reference, validated for tenant ownership at write
    time, never a hard FK (the target tables span five different
    modules)."""

    DOCUMENT = "DOCUMENT"
    SALES_INVOICE = "SALES_INVOICE"
    PURCHASE_INVOICE = "PURCHASE_INVOICE"
    PAYMENT = "PAYMENT"
    RECEIPT = "RECEIPT"
    JOURNAL_ENTRY = "JOURNAL_ENTRY"
    GST_RETURN_PERIOD = "GST_RETURN_PERIOD"
    GSTR2B_RECORD = "GSTR2B_RECORD"
    TDS_TRANSACTION = "TDS_TRANSACTION"
    TDS_CHALLAN = "TDS_CHALLAN"
    BANK_TRANSACTION = "BANK_TRANSACTION"
    BANK_RECONCILIATION = "BANK_RECONCILIATION"
    # --- Income Tax (Phase 8) --- kept to <=20 chars: this StrEnum backs
    # `audit_findings.source_type`, an existing VARCHAR(20) column from
    # Phase 7 (PHASE8 §90 — smallest compatible change, no ALTER needed).
    TAX_COMPUTATION = "TAX_COMPUTATION"
    ITR_PREPARATION = "ITR_PREPARATION"
    TAX_DEDUCTION = "TAX_DEDUCTION"
    CAPITAL_GAIN = "CAPITAL_GAIN"
    TAX_CREDIT_ENTRY = "TAX_CREDIT_ENTRY"
    OTHER = "OTHER"


class AuditFindingResponseStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class AuditReviewType(StrEnum):
    INITIAL_REVIEW = "INITIAL_REVIEW"
    FINAL_REVIEW = "FINAL_REVIEW"
    SECOND_REVIEW = "SECOND_REVIEW"
    QUALITY_REVIEW = "QUALITY_REVIEW"


class AuditReviewStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    RETURNED = "RETURNED"


class AuditSignOffType(StrEnum):
    """Always an internal application acknowledgement — never a DSC,
    ICAI, or government signature (PHASE7 §28-29)."""

    LEAD_AUDITOR = "LEAD_AUDITOR"
    REVIEWER = "REVIEWER"
    COMPANY_ACKNOWLEDGEMENT = "COMPANY_ACKNOWLEDGEMENT"
