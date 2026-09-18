"""Standard audit review checklist template (PHASE7 §13).

A small, hardcoded, explicitly-non-authoritative starting point for an
engagement's checklist — the same "small, documented sample configuration"
precedent Phase 5 set for `DEFAULT_TDS_SECTIONS` in `app/seed.py`. It is
not a statutory or ICAI-prescribed checklist; a CA is expected to add,
remove, or mark items not applicable as the engagement actually requires
(PHASE7 §12, item status includes NOT_APPLICABLE for exactly this reason).
"""

from app.models.audit_workflow_enums import AuditChecklistCategory

STANDARD_CHECKLIST_TEMPLATE: list[dict] = [
    {
        "category": AuditChecklistCategory.ACCOUNTING,
        "title": "Trial balance ties out and all periods are posted",
        "description": "Confirm all accounting periods in scope are POSTED/CLOSED and the trial balance is balanced.",
    },
    {
        "category": AuditChecklistCategory.ACCOUNTING,
        "title": "Opening balances agree with prior period closing balances",
        "description": "Verify opening balances were carried forward correctly for the financial year in scope.",
    },
    {
        "category": AuditChecklistCategory.ACCOUNTING,
        "title": "Journal entries reviewed for unusual or manual adjustments",
        "description": "Scan journal entries for large, round-figure, or period-end manual adjustments.",
    },
    {
        "category": AuditChecklistCategory.GST,
        "title": "GSTR-1 vs books sales reconciliation reviewed",
        "description": "Confirm GST return periods in scope have been generated and validated.",
    },
    {
        "category": AuditChecklistCategory.GST,
        "title": "GSTR-2B reconciliation and ITC review completed",
        "description": "Confirm ITC claims for the period have been reviewed/approved, and mismatches investigated.",
    },
    {
        "category": AuditChecklistCategory.TDS,
        "title": "TDS deducted and deposited within due dates",
        "description": "Review TDS transactions and challans for the period for late deduction/deposit.",
    },
    {
        "category": AuditChecklistCategory.TDS,
        "title": "TDS challans reconciled against transactions",
        "description": "Confirm challan-to-transaction reconciliation has no unexplained variances.",
    },
    {
        "category": AuditChecklistCategory.BANK,
        "title": "Bank accounts reconciled for the period",
        "description": "Confirm bank reconciliation sessions covering the period are RECONCILED or LOCKED.",
    },
    {
        "category": AuditChecklistCategory.BANK,
        "title": "Unmatched or review-required bank transactions investigated",
        "description": "Review any bank transactions left UNMATCHED or REVIEW_REQUIRED for the period.",
    },
    {
        "category": AuditChecklistCategory.DOCUMENTS,
        "title": "Supporting documents available for high-value transactions",
        "description": "Spot-check that invoices/receipts/documents exist for a sample of high-value entries.",
    },
    {
        "category": AuditChecklistCategory.INTERNAL_CONTROLS,
        "title": "User access and approval workflow reviewed",
        "description": "Confirm roles/permissions in use are appropriate and approval steps were followed.",
    },
]
