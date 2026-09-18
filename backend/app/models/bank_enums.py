"""Shared enums for the bank reconciliation domain (Phase 6)."""

from enum import StrEnum


class BankAccountType(StrEnum):
    SAVINGS = "SAVINGS"
    CURRENT = "CURRENT"
    CASH_CREDIT = "CASH_CREDIT"
    OVERDRAFT = "OVERDRAFT"
    OTHER = "OTHER"


class BankStatementSourceType(StrEnum):
    CSV = "CSV"
    XLSX = "XLSX"
    DOCUMENT = "DOCUMENT"
    MANUAL = "MANUAL"


class BankStatementStatus(StrEnum):
    IMPORTED = "IMPORTED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    RECONCILING = "RECONCILING"
    RECONCILED = "RECONCILED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class BankTransactionType(StrEnum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class BankTransactionReconciliationStatus(StrEnum):
    """Never a plain matched/unmatched boolean — MATCH_SUGGESTED and
    REVIEW_REQUIRED exist so the matching engine can say "here are
    candidates" or "I can't tell" instead of picking one (PHASE6 §20)."""

    UNMATCHED = "UNMATCHED"
    MATCH_SUGGESTED = "MATCH_SUGGESTED"
    PARTIALLY_MATCHED = "PARTIALLY_MATCHED"
    MATCHED = "MATCHED"
    MANUALLY_MATCHED = "MANUALLY_MATCHED"
    EXCLUDED = "EXCLUDED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class BankMatchType(StrEnum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"
    PARTIAL = "PARTIAL"
    ADJUSTMENT = "ADJUSTMENT"


class BankMatchStatus(StrEnum):
    ACTIVE = "ACTIVE"
    REVERSED = "REVERSED"


class BankMatchSourceType(StrEnum):
    PAYMENT = "PAYMENT"
    RECEIPT = "RECEIPT"
    JOURNAL_ENTRY = "JOURNAL_ENTRY"


class BankReconciliationStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_REVIEW = "PENDING_REVIEW"
    RECONCILED = "RECONCILED"
    LOCKED = "LOCKED"
    CANCELLED = "CANCELLED"
