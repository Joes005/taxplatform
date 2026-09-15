"""Shared enums for the accounting data layer (Phase 3).

Centralized here (rather than repeated per-model, as Phase 1/2 did for their
one or two enums each) because ~10 of these are reused across a dozen
accounting models — BalanceType alone appears on Ledger, JournalEntryLine,
and OpeningBalance.
"""

from enum import StrEnum


class BalanceType(StrEnum):
    """Double-entry bookkeeping has exactly two directions a balance can
    sit in. Assets/Expenses normally carry a DEBIT balance;
    Liabilities/Equity/Income normally carry a CREDIT balance."""

    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class TransactionStatus(StrEnum):
    """DRAFT is freely editable. POSTED is the permanent accounting record
    and must never be silently edited. CANCELLED is terminal — corrections
    happen via a new document (credit/debit note), not by rewriting
    history."""

    DRAFT = "DRAFT"
    POSTED = "POSTED"
    CANCELLED = "CANCELLED"


class DataSource(StrEnum):
    """Where a record's data originated — preserved on every transactional
    row for audit traceability back to an import job."""

    MANUAL = "MANUAL"
    CSV = "CSV"
    EXCEL = "EXCEL"
    TALLY = "TALLY"


class LedgerType(StrEnum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    RECEIVABLE = "RECEIVABLE"
    PAYABLE = "PAYABLE"
    BANK = "BANK"
    CASH = "CASH"
    TAX = "TAX"


class ItemType(StrEnum):
    PRODUCT = "PRODUCT"
    SERVICE = "SERVICE"


class PaymentMode(StrEnum):
    CASH = "CASH"
    BANK = "BANK"
    UPI = "UPI"
    CHEQUE = "CHEQUE"
    CARD = "CARD"
    OTHER = "OTHER"


class FinancialYearStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class PeriodStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    LOCKED = "LOCKED"


class PartyType(StrEnum):
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"
    OTHER = "OTHER"


class NoteType(StrEnum):
    """A CreditNote/DebitNote can adjust either a sales or a purchase
    transaction — this decides which party FK (customer_id or vendor_id)
    and which reference-invoice FK is populated."""

    SALES = "SALES"
    PURCHASE = "PURCHASE"


class OpeningBalanceAccountType(StrEnum):
    LEDGER = "LEDGER"
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"


class ImportType(StrEnum):
    SALES = "SALES"
    PURCHASES = "PURCHASES"
    CUSTOMERS = "CUSTOMERS"
    VENDORS = "VENDORS"
    PRODUCTS = "PRODUCTS"
    PAYMENTS = "PAYMENTS"
    RECEIPTS = "RECEIPTS"
    LEDGERS = "LEDGERS"
    JOURNALS = "JOURNALS"
    TALLY = "TALLY"


class ImportStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PARSING = "PARSING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
