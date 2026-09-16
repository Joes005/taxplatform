"""Shared enums for the GST compliance domain (Phase 4)."""

from enum import StrEnum


class GSTRegistrationType(StrEnum):
    REGULAR = "REGULAR"
    COMPOSITION = "COMPOSITION"
    CASUAL = "CASUAL"
    SEZ = "SEZ"
    OTHER = "OTHER"


class SupplyType(StrEnum):
    """Whether a transaction is treated as within one state (CGST+SGST)
    or across states (IGST), derived from supplier vs. place-of-supply
    state codes."""

    INTRA_STATE = "INTRA_STATE"
    INTER_STATE = "INTER_STATE"


class GSTTransactionCategory(StrEnum):
    """Classification used to route a sales transaction into the correct
    GSTR-1 section. REVIEW_REQUIRED means the data on hand was not enough
    to classify confidently — the system never guesses (PHASE4 section 12)."""

    B2B = "B2B"
    B2C = "B2C"
    EXPORT = "EXPORT"
    SEZ = "SEZ"
    NIL_RATED = "NIL_RATED"
    EXEMPT = "EXEMPT"
    NON_GST = "NON_GST"
    OTHER = "OTHER"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class GSTReturnPeriodStatus(StrEnum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    FINALIZED = "FINALIZED"
    ARCHIVED = "ARCHIVED"


class GSTReturnType(StrEnum):
    GSTR1 = "GSTR1"
    GSTR3B = "GSTR3B"


class GSTReturnSnapshotStatus(StrEnum):
    """Review workflow for one generated return preparation (PHASE4
    section 43): DRAFT -> UNDER_REVIEW -> (CHANGES_REQUESTED loops back to
    DRAFT, or) APPROVED -> FINALIZED. FINALIZED snapshots are immutable;
    a later regeneration creates a new version instead."""

    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    FINALIZED = "FINALIZED"


class GSTR2BDocumentType(StrEnum):
    INVOICE = "INVOICE"
    CREDIT_NOTE = "CREDIT_NOTE"
    DEBIT_NOTE = "DEBIT_NOTE"


class ReconciliationStatus(StrEnum):
    MATCHED = "MATCHED"
    PARTIALLY_MATCHED = "PARTIALLY_MATCHED"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    DATE_MISMATCH = "DATE_MISMATCH"
    GSTIN_MISMATCH = "GSTIN_MISMATCH"
    INVOICE_NUMBER_MISMATCH = "INVOICE_NUMBER_MISMATCH"
    BOOKS_ONLY = "BOOKS_ONLY"
    GSTR2B_ONLY = "GSTR2B_ONLY"
    DUPLICATE = "DUPLICATE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class ITCCategory(StrEnum):
    MATCHED_ITC = "MATCHED_ITC"
    UNMATCHED_ITC = "UNMATCHED_ITC"
    POTENTIAL_ITC = "POTENTIAL_ITC"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    INELIGIBLE = "INELIGIBLE"


class ITCReviewStatus(StrEnum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class ValidationSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class GSTReviewNoteStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
