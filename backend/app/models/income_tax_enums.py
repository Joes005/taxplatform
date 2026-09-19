"""Shared enums for the Income Tax Compliance Engine (Phase 8).

Named `income_tax_enums` to stay unambiguous next to the pre-existing
`AuditLog`/`AuditAction` (Phase 1) and the CA/Auditor workflow's own
`audit_workflow_enums` (Phase 7), which this phase extends but never
duplicates.
"""

from enum import StrEnum


class TaxpayerType(StrEnum):
    INDIVIDUAL = "INDIVIDUAL"
    HUF = "HUF"
    PARTNERSHIP = "PARTNERSHIP"
    LLP = "LLP"
    COMPANY = "COMPANY"
    TRUST = "TRUST"
    OTHER = "OTHER"


class ResidentialStatus(StrEnum):
    RESIDENT = "RESIDENT"
    RESIDENT_NOT_ORDINARILY_RESIDENT = "RESIDENT_NOT_ORDINARILY_RESIDENT"
    NON_RESIDENT = "NON_RESIDENT"


class TaxRegime(StrEnum):
    OLD_REGIME = "OLD_REGIME"
    NEW_REGIME = "NEW_REGIME"


class HousePropertyType(StrEnum):
    SELF_OCCUPIED = "SELF_OCCUPIED"
    LET_OUT = "LET_OUT"


class CapitalGainType(StrEnum):
    SHORT_TERM = "SHORT_TERM"
    LONG_TERM = "LONG_TERM"


class CapitalAssetType(StrEnum):
    EQUITY_SHARES = "EQUITY_SHARES"
    MUTUAL_FUND = "MUTUAL_FUND"
    IMMOVABLE_PROPERTY = "IMMOVABLE_PROPERTY"
    GOLD_JEWELLERY = "GOLD_JEWELLERY"
    DEBT_INSTRUMENT = "DEBT_INSTRUMENT"
    OTHER = "OTHER"


class TaxAdjustmentType(StrEnum):
    """How one line of `IncomeTaxAdjustment` moves book profit toward
    taxable business income (PHASE8 §26) — never a legal conclusion, just
    an arithmetic direction the CA/accountant has chosen for a specific
    amount."""

    ADD_BACK = "ADD_BACK"
    DEDUCTION = "DEDUCTION"
    TIMING_DIFFERENCE = "TIMING_DIFFERENCE"
    DEPRECIATION_ADJUSTMENT = "DEPRECIATION_ADJUSTMENT"
    OTHER = "OTHER"


class LedgerTaxClassification(StrEnum):
    """A ledger's tax treatment for business-income purposes (PHASE8 §25)
    — set explicitly per ledger by a human, never inferred from the
    ledger's name. `NOT_CLASSIFIED` (the default) intentionally excludes
    the ledger from the automatic add-back total until someone decides."""

    ALLOWABLE = "ALLOWABLE"
    PARTIALLY_ALLOWABLE = "PARTIALLY_ALLOWABLE"
    DISALLOWABLE = "DISALLOWABLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_CLASSIFIED = "NOT_CLASSIFIED"


class TaxLossType(StrEnum):
    BUSINESS = "BUSINESS"
    CAPITAL_SHORT_TERM = "CAPITAL_SHORT_TERM"
    CAPITAL_LONG_TERM = "CAPITAL_LONG_TERM"
    HOUSE_PROPERTY = "HOUSE_PROPERTY"
    OTHER = "OTHER"


class IncomeTaxSourceType(StrEnum):
    """Generic reference target for deductions/adjustments/credits tracing
    back to an existing accounting/document record (PHASE8 §93-94) — the
    same shape `TDSTransaction.source_type`/`AuditFinding.source_type`
    already use, so this phase adds no new hard FK into five other
    modules."""

    SALES_INVOICE = "SALES_INVOICE"
    PURCHASE_INVOICE = "PURCHASE_INVOICE"
    PAYMENT = "PAYMENT"
    RECEIPT = "RECEIPT"
    JOURNAL_ENTRY = "JOURNAL_ENTRY"
    LEDGER = "LEDGER"
    DOCUMENT = "DOCUMENT"
    TDS_TRANSACTION = "TDS_TRANSACTION"
    OTHER = "OTHER"


class TaxComputationStatus(StrEnum):
    """PHASE8 §42 — server-side transitions only, enforced by
    `IncomeTaxComputationService`'s transition table, the same pattern
    already used for `AuditEngagementStatus`/`BankReconciliationStatus`."""

    DRAFT = "DRAFT"
    CALCULATED = "CALCULATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    LOCKED = "LOCKED"
    CANCELLED = "CANCELLED"


class ITRFormType(StrEnum):
    """Only the forms this platform can confidently determine
    applicability for (PHASE8 §44) — anything else resolves to
    `NOT_DETERMINED`, which the API surfaces as `REVIEW_REQUIRED` rather
    than a guess."""

    ITR_1 = "ITR_1"
    ITR_2 = "ITR_2"
    ITR_3 = "ITR_3"
    ITR_5 = "ITR_5"
    ITR_6 = "ITR_6"
    ITR_7 = "ITR_7"
    NOT_DETERMINED = "NOT_DETERMINED"


class ITRPreparationStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    VALIDATION_REQUIRED = "VALIDATION_REQUIRED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    LOCKED = "LOCKED"


class ValidationSeverity(StrEnum):
    """Never silently ignored (PHASE8 §46-47) — `ITRValidationService`
    returns a list of these; an `ERROR` blocks approval, a `WARNING` or
    `REVIEW_REQUIRED` does not but is always shown."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
