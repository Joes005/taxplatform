"""Shared enums for the TDS compliance domain (Phase 5)."""

from enum import StrEnum


class DeductorType(StrEnum):
    COMPANY = "COMPANY"
    INDIVIDUAL = "INDIVIDUAL"
    HUF = "HUF"
    FIRM = "FIRM"
    LLP = "LLP"
    GOVERNMENT = "GOVERNMENT"
    TRUST = "TRUST"
    OTHER = "OTHER"


class TDSProfileStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class DeducteeType(StrEnum):
    INDIVIDUAL = "INDIVIDUAL"
    COMPANY = "COMPANY"
    FIRM = "FIRM"
    LLP = "LLP"
    TRUST = "TRUST"
    HUF = "HUF"
    OTHER = "OTHER"


class PANStatus(StrEnum):
    """Whether a deductee's PAN is on file, not whether it has been
    verified against the Income Tax e-filing portal (this platform never
    calls that). Section 206AA of the Income Tax Act requires a higher
    TDS rate when PAN is unavailable — `PANStatus` is what
    `TDSCalculationService` reads to decide whether that applies."""

    AVAILABLE = "AVAILABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    INVALID = "INVALID"
    PENDING_REVIEW = "PENDING_REVIEW"


class TDSRateType(StrEnum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


class TDSApplicabilityStatus(StrEnum):
    """Never a plain boolean — REVIEW_REQUIRED and MISSING_DATA exist so
    the applicability engine can say "I don't know" instead of guessing
    (PHASE5 section 3)."""

    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    MISSING_DATA = "MISSING_DATA"


class TDSTransactionStatus(StrEnum):
    """DRAFT -> CALCULATED -> DEDUCTED -> PAID is the happy path;
    CALCULATED may also move to CANCELLED. REVIEW_REQUIRED is a side
    branch reachable from DRAFT/CALCULATED when the applicability engine
    could not confidently determine tax treatment. All transitions are
    enforced by TDSTransactionService, never by direct field assignment
    elsewhere (PHASE5 section 19)."""

    DRAFT = "DRAFT"
    CALCULATED = "CALCULATED"
    DEDUCTED = "DEDUCTED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class TDSChallanStatus(StrEnum):
    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    PAID = "PAID"
    RECONCILED = "RECONCILED"
    CANCELLED = "CANCELLED"


class TDSReconciliationStatus(StrEnum):
    MATCHED = "MATCHED"
    PARTIALLY_MATCHED = "PARTIALLY_MATCHED"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    MISSING_CHALLAN = "MISSING_CHALLAN"
    UNALLOCATED_PAYMENT = "UNALLOCATED_PAYMENT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class TDSReturnPeriodStatus(StrEnum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    FINALIZED = "FINALIZED"
    ARCHIVED = "ARCHIVED"


class TDSQuarter(StrEnum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"


class TDSReturnType(StrEnum):
    """The four government TDS return forms this platform prepares data
    for — it never files any of them (PHASE5 section 1)."""

    FORM_24Q = "FORM_24Q"
    FORM_26Q = "FORM_26Q"
    FORM_27Q = "FORM_27Q"
    FORM_27EQ = "FORM_27EQ"


class TDSReturnSnapshotStatus(StrEnum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    FINALIZED = "FINALIZED"


class TDSReviewNoteStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class TDSValidationSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
