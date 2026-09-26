"""Canonical catalogue of permission codes and role -> permission mappings.

This is the single source of truth for Phase 1 RBAC. Future modules (GST,
TDS, DOCUMENTS, RECONCILIATION, AUDIT, REPORTS, FILING) should extend
`PERMISSIONS` and `ROLE_PERMISSIONS` here rather than hardcoding checks
elsewhere in the codebase.
"""

from enum import StrEnum


class PermissionCode(StrEnum):
    AUTH_VIEW = "AUTH_VIEW"
    AUTH_MANAGE = "AUTH_MANAGE"

    COMPANY_VIEW = "COMPANY_VIEW"
    COMPANY_CREATE = "COMPANY_CREATE"
    COMPANY_UPDATE = "COMPANY_UPDATE"
    COMPANY_MANAGE_USERS = "COMPANY_MANAGE_USERS"

    USER_VIEW = "USER_VIEW"
    USER_CREATE = "USER_CREATE"
    USER_UPDATE = "USER_UPDATE"
    USER_DEACTIVATE = "USER_DEACTIVATE"

    ROLE_VIEW = "ROLE_VIEW"
    ROLE_ASSIGN = "ROLE_ASSIGN"

    AUDIT_LOG_VIEW = "AUDIT_LOG_VIEW"

    DASHBOARD_VIEW = "DASHBOARD_VIEW"

    DOCUMENT_VIEW = "DOCUMENT_VIEW"
    DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"
    DOCUMENT_UPDATE = "DOCUMENT_UPDATE"
    DOCUMENT_ARCHIVE = "DOCUMENT_ARCHIVE"
    DOCUMENT_RESTORE = "DOCUMENT_RESTORE"
    DOCUMENT_DOWNLOAD = "DOCUMENT_DOWNLOAD"
    DOCUMENT_DELETE = "DOCUMENT_DELETE"
    DOCUMENT_MANAGE = "DOCUMENT_MANAGE"

    ACCOUNTING_VIEW = "ACCOUNTING_VIEW"
    ACCOUNTING_CREATE = "ACCOUNTING_CREATE"
    ACCOUNTING_UPDATE = "ACCOUNTING_UPDATE"
    ACCOUNTING_DELETE = "ACCOUNTING_DELETE"

    LEDGER_VIEW = "LEDGER_VIEW"
    LEDGER_MANAGE = "LEDGER_MANAGE"

    CUSTOMER_VIEW = "CUSTOMER_VIEW"
    CUSTOMER_MANAGE = "CUSTOMER_MANAGE"

    VENDOR_VIEW = "VENDOR_VIEW"
    VENDOR_MANAGE = "VENDOR_MANAGE"

    PRODUCT_VIEW = "PRODUCT_VIEW"
    PRODUCT_MANAGE = "PRODUCT_MANAGE"

    SALES_VIEW = "SALES_VIEW"
    SALES_CREATE = "SALES_CREATE"
    SALES_UPDATE = "SALES_UPDATE"
    SALES_POST = "SALES_POST"
    SALES_CANCEL = "SALES_CANCEL"

    PURCHASE_VIEW = "PURCHASE_VIEW"
    PURCHASE_CREATE = "PURCHASE_CREATE"
    PURCHASE_UPDATE = "PURCHASE_UPDATE"
    PURCHASE_POST = "PURCHASE_POST"
    PURCHASE_CANCEL = "PURCHASE_CANCEL"

    PAYMENT_VIEW = "PAYMENT_VIEW"
    PAYMENT_CREATE = "PAYMENT_CREATE"

    RECEIPT_VIEW = "RECEIPT_VIEW"
    RECEIPT_CREATE = "RECEIPT_CREATE"

    JOURNAL_VIEW = "JOURNAL_VIEW"
    JOURNAL_CREATE = "JOURNAL_CREATE"
    JOURNAL_POST = "JOURNAL_POST"

    ACCOUNTING_IMPORT = "ACCOUNTING_IMPORT"
    ACCOUNTING_IMPORT_COMMIT = "ACCOUNTING_IMPORT_COMMIT"
    ACCOUNTING_IMPORT_VIEW = "ACCOUNTING_IMPORT_VIEW"

    # --- Tally Compatibility (Phase 12) ---
    TALLY_IMPORT_VIEW = "TALLY_IMPORT_VIEW"
    TALLY_IMPORT_CREATE = "TALLY_IMPORT_CREATE"
    TALLY_IMPORT_COMMIT = "TALLY_IMPORT_COMMIT"
    TALLY_IMPORT_EXPORT = "TALLY_IMPORT_EXPORT"
    TALLY_MAPPING_MANAGE = "TALLY_MAPPING_MANAGE"
    TALLY_EXPORT_VIEW = "TALLY_EXPORT_VIEW"
    TALLY_EXPORT_CREATE = "TALLY_EXPORT_CREATE"

    # --- GST (Phase 4) ---
    GST_VIEW = "GST_VIEW"
    GST_CREATE = "GST_CREATE"
    GST_UPDATE = "GST_UPDATE"

    GST_RETURN_VIEW = "GST_RETURN_VIEW"
    GST_RETURN_GENERATE = "GST_RETURN_GENERATE"
    GST_RETURN_VALIDATE = "GST_RETURN_VALIDATE"
    GST_RETURN_APPROVE = "GST_RETURN_APPROVE"
    GST_RETURN_FINALIZE = "GST_RETURN_FINALIZE"

    GSTR1_VIEW = "GSTR1_VIEW"
    GSTR1_GENERATE = "GSTR1_GENERATE"
    GSTR1_EXPORT = "GSTR1_EXPORT"

    GSTR2B_IMPORT = "GSTR2B_IMPORT"
    GSTR2B_VIEW = "GSTR2B_VIEW"
    GSTR2B_RECONCILE = "GSTR2B_RECONCILE"

    ITC_VIEW = "ITC_VIEW"
    ITC_REVIEW = "ITC_REVIEW"
    ITC_APPROVE = "ITC_APPROVE"

    GSTR3B_VIEW = "GSTR3B_VIEW"
    GSTR3B_GENERATE = "GSTR3B_GENERATE"
    GSTR3B_EXPORT = "GSTR3B_EXPORT"

    # --- TDS (Phase 5) ---
    TDS_VIEW = "TDS_VIEW"
    TDS_CREATE = "TDS_CREATE"
    TDS_UPDATE = "TDS_UPDATE"

    TDS_DEDUCTEE_VIEW = "TDS_DEDUCTEE_VIEW"
    TDS_DEDUCTEE_MANAGE = "TDS_DEDUCTEE_MANAGE"

    TDS_RULE_VIEW = "TDS_RULE_VIEW"
    TDS_RULE_MANAGE = "TDS_RULE_MANAGE"

    TDS_TRANSACTION_VIEW = "TDS_TRANSACTION_VIEW"
    TDS_TRANSACTION_CREATE = "TDS_TRANSACTION_CREATE"
    TDS_TRANSACTION_UPDATE = "TDS_TRANSACTION_UPDATE"
    TDS_TRANSACTION_CALCULATE = "TDS_TRANSACTION_CALCULATE"
    TDS_TRANSACTION_CANCEL = "TDS_TRANSACTION_CANCEL"

    TDS_CHALLAN_VIEW = "TDS_CHALLAN_VIEW"
    TDS_CHALLAN_CREATE = "TDS_CHALLAN_CREATE"
    TDS_CHALLAN_UPDATE = "TDS_CHALLAN_UPDATE"
    TDS_CHALLAN_RECONCILE = "TDS_CHALLAN_RECONCILE"

    TDS_RETURN_VIEW = "TDS_RETURN_VIEW"
    TDS_RETURN_GENERATE = "TDS_RETURN_GENERATE"
    TDS_RETURN_VALIDATE = "TDS_RETURN_VALIDATE"
    TDS_RETURN_APPROVE = "TDS_RETURN_APPROVE"
    TDS_RETURN_FINALIZE = "TDS_RETURN_FINALIZE"

    TDS_IMPORT = "TDS_IMPORT"
    TDS_IMPORT_COMMIT = "TDS_IMPORT_COMMIT"

    TDS_REPORT_VIEW = "TDS_REPORT_VIEW"
    TDS_REPORT_EXPORT = "TDS_REPORT_EXPORT"

    # --- Bank Reconciliation (Phase 6) ---
    BANK_VIEW = "BANK_VIEW"
    BANK_CREATE = "BANK_CREATE"
    BANK_UPDATE = "BANK_UPDATE"

    BANK_STATEMENT_VIEW = "BANK_STATEMENT_VIEW"
    BANK_STATEMENT_IMPORT = "BANK_STATEMENT_IMPORT"
    BANK_STATEMENT_IMPORT_COMMIT = "BANK_STATEMENT_IMPORT_COMMIT"

    BANK_TRANSACTION_VIEW = "BANK_TRANSACTION_VIEW"
    BANK_TRANSACTION_UPDATE = "BANK_TRANSACTION_UPDATE"

    BANK_MATCH_VIEW = "BANK_MATCH_VIEW"
    BANK_MATCH_CREATE = "BANK_MATCH_CREATE"
    BANK_MATCH_REVERSE = "BANK_MATCH_REVERSE"

    BANK_ADJUST = "BANK_ADJUST"

    BANK_RECONCILE_VIEW = "BANK_RECONCILE_VIEW"
    BANK_RECONCILE_RUN = "BANK_RECONCILE_RUN"
    BANK_RECONCILE_SUBMIT = "BANK_RECONCILE_SUBMIT"
    BANK_RECONCILE_APPROVE = "BANK_RECONCILE_APPROVE"
    BANK_RECONCILE_LOCK = "BANK_RECONCILE_LOCK"

    BANK_REPORT_VIEW = "BANK_REPORT_VIEW"
    BANK_REPORT_EXPORT = "BANK_REPORT_EXPORT"

    # --- CA/Auditor Workflow (Phase 7) ---
    AUDIT_ENGAGEMENT_VIEW = "AUDIT_ENGAGEMENT_VIEW"
    AUDIT_ENGAGEMENT_CREATE = "AUDIT_ENGAGEMENT_CREATE"
    AUDIT_ENGAGEMENT_UPDATE = "AUDIT_ENGAGEMENT_UPDATE"
    AUDIT_ENGAGEMENT_ASSIGN = "AUDIT_ENGAGEMENT_ASSIGN"

    AUDIT_CHECKLIST_VIEW = "AUDIT_CHECKLIST_VIEW"
    AUDIT_CHECKLIST_MANAGE = "AUDIT_CHECKLIST_MANAGE"

    AUDIT_FINDING_VIEW = "AUDIT_FINDING_VIEW"
    AUDIT_FINDING_CREATE = "AUDIT_FINDING_CREATE"
    AUDIT_FINDING_UPDATE = "AUDIT_FINDING_UPDATE"
    AUDIT_FINDING_ASSIGN = "AUDIT_FINDING_ASSIGN"
    AUDIT_FINDING_RESPOND = "AUDIT_FINDING_RESPOND"
    AUDIT_FINDING_REVIEW = "AUDIT_FINDING_REVIEW"
    AUDIT_FINDING_RESOLVE = "AUDIT_FINDING_RESOLVE"
    AUDIT_FINDING_REOPEN = "AUDIT_FINDING_REOPEN"

    AUDIT_EVIDENCE_MANAGE = "AUDIT_EVIDENCE_MANAGE"

    AUDIT_ENGAGEMENT_REVIEW = "AUDIT_ENGAGEMENT_REVIEW"
    AUDIT_ENGAGEMENT_APPROVE = "AUDIT_ENGAGEMENT_APPROVE"
    AUDIT_ENGAGEMENT_SIGNOFF = "AUDIT_ENGAGEMENT_SIGNOFF"
    AUDIT_ENGAGEMENT_LOCK = "AUDIT_ENGAGEMENT_LOCK"

    AUDIT_REPORT_VIEW = "AUDIT_REPORT_VIEW"
    AUDIT_REPORT_EXPORT = "AUDIT_REPORT_EXPORT"

    # --- Income Tax (Phase 8) ---
    INCOME_TAX_VIEW = "INCOME_TAX_VIEW"
    INCOME_TAX_CREATE = "INCOME_TAX_CREATE"
    INCOME_TAX_UPDATE = "INCOME_TAX_UPDATE"
    INCOME_TAX_CALCULATE = "INCOME_TAX_CALCULATE"
    INCOME_TAX_VALIDATE = "INCOME_TAX_VALIDATE"
    INCOME_TAX_REVIEW = "INCOME_TAX_REVIEW"
    INCOME_TAX_APPROVE = "INCOME_TAX_APPROVE"
    INCOME_TAX_LOCK = "INCOME_TAX_LOCK"
    INCOME_TAX_EXPORT = "INCOME_TAX_EXPORT"

    # --- Compliance Calendar / Tasks / Notifications (Phase 9) ---
    COMPLIANCE_VIEW = "COMPLIANCE_VIEW"
    COMPLIANCE_TASK_CREATE = "COMPLIANCE_TASK_CREATE"
    COMPLIANCE_TASK_UPDATE = "COMPLIANCE_TASK_UPDATE"
    COMPLIANCE_TASK_ASSIGN = "COMPLIANCE_TASK_ASSIGN"
    COMPLIANCE_TASK_COMPLETE = "COMPLIANCE_TASK_COMPLETE"
    COMPLIANCE_TASK_REVIEW = "COMPLIANCE_TASK_REVIEW"
    COMPLIANCE_TASK_VERIFY = "COMPLIANCE_TASK_VERIFY"
    COMPLIANCE_TASK_CANCEL = "COMPLIANCE_TASK_CANCEL"
    COMPLIANCE_TASK_LOCK = "COMPLIANCE_TASK_LOCK"
    COMPLIANCE_OBLIGATION_MANAGE = "COMPLIANCE_OBLIGATION_MANAGE"
    COMPLIANCE_RULE_MANAGE = "COMPLIANCE_RULE_MANAGE"
    COMPLIANCE_CALENDAR_VIEW = "COMPLIANCE_CALENDAR_VIEW"
    COMPLIANCE_NOTIFICATION_VIEW = "COMPLIANCE_NOTIFICATION_VIEW"
    COMPLIANCE_NOTIFICATION_MANAGE = "COMPLIANCE_NOTIFICATION_MANAGE"
    COMPLIANCE_REPORT_EXPORT = "COMPLIANCE_REPORT_EXPORT"


class RoleCode(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    COMPANY_ADMIN = "COMPANY_ADMIN"
    ACCOUNTANT = "ACCOUNTANT"
    AUDITOR = "AUDITOR"


# (code, module, description)
PERMISSIONS: list[tuple[PermissionCode, str, str]] = [
    (PermissionCode.AUTH_VIEW, "AUTH", "View authentication/session information"),
    (PermissionCode.AUTH_MANAGE, "AUTH", "Manage authentication settings"),
    (PermissionCode.COMPANY_VIEW, "COMPANY", "View company details"),
    (PermissionCode.COMPANY_CREATE, "COMPANY", "Create new companies"),
    (PermissionCode.COMPANY_UPDATE, "COMPANY", "Update company details"),
    (PermissionCode.COMPANY_MANAGE_USERS, "COMPANY", "Manage users within a company"),
    (PermissionCode.USER_VIEW, "USER", "View users"),
    (PermissionCode.USER_CREATE, "USER", "Create users"),
    (PermissionCode.USER_UPDATE, "USER", "Update users"),
    (PermissionCode.USER_DEACTIVATE, "USER", "Deactivate users"),
    (PermissionCode.ROLE_VIEW, "ROLE", "View roles"),
    (PermissionCode.ROLE_ASSIGN, "ROLE", "Assign roles to users"),
    (PermissionCode.AUDIT_LOG_VIEW, "AUDIT", "View audit logs"),
    (PermissionCode.DASHBOARD_VIEW, "DASHBOARD", "View dashboard"),
    (PermissionCode.DOCUMENT_VIEW, "DOCUMENT", "View documents and their metadata"),
    (PermissionCode.DOCUMENT_UPLOAD, "DOCUMENT", "Upload new documents"),
    (PermissionCode.DOCUMENT_UPDATE, "DOCUMENT", "Update document metadata"),
    (PermissionCode.DOCUMENT_ARCHIVE, "DOCUMENT", "Archive documents"),
    (PermissionCode.DOCUMENT_RESTORE, "DOCUMENT", "Restore archived documents"),
    (PermissionCode.DOCUMENT_DOWNLOAD, "DOCUMENT", "Download document files"),
    (PermissionCode.DOCUMENT_DELETE, "DOCUMENT", "Permanently delete documents"),
    (PermissionCode.DOCUMENT_MANAGE, "DOCUMENT", "Full document module administration"),
    (PermissionCode.ACCOUNTING_VIEW, "ACCOUNTING", "View accounting data"),
    (PermissionCode.ACCOUNTING_CREATE, "ACCOUNTING", "Create accounting records"),
    (PermissionCode.ACCOUNTING_UPDATE, "ACCOUNTING", "Update accounting records"),
    (PermissionCode.ACCOUNTING_DELETE, "ACCOUNTING", "Delete/void accounting records"),
    (PermissionCode.LEDGER_VIEW, "ACCOUNTING", "View ledgers (chart of accounts)"),
    (PermissionCode.LEDGER_MANAGE, "ACCOUNTING", "Create and update ledgers"),
    (PermissionCode.CUSTOMER_VIEW, "ACCOUNTING", "View customers"),
    (PermissionCode.CUSTOMER_MANAGE, "ACCOUNTING", "Create and update customers"),
    (PermissionCode.VENDOR_VIEW, "ACCOUNTING", "View vendors"),
    (PermissionCode.VENDOR_MANAGE, "ACCOUNTING", "Create and update vendors"),
    (PermissionCode.PRODUCT_VIEW, "ACCOUNTING", "View products/services"),
    (PermissionCode.PRODUCT_MANAGE, "ACCOUNTING", "Create and update products/services"),
    (PermissionCode.SALES_VIEW, "ACCOUNTING", "View sales invoices"),
    (PermissionCode.SALES_CREATE, "ACCOUNTING", "Create sales invoices"),
    (PermissionCode.SALES_UPDATE, "ACCOUNTING", "Update draft sales invoices"),
    (PermissionCode.SALES_POST, "ACCOUNTING", "Post sales invoices"),
    (PermissionCode.SALES_CANCEL, "ACCOUNTING", "Cancel sales invoices"),
    (PermissionCode.PURCHASE_VIEW, "ACCOUNTING", "View purchase invoices"),
    (PermissionCode.PURCHASE_CREATE, "ACCOUNTING", "Create purchase invoices"),
    (PermissionCode.PURCHASE_UPDATE, "ACCOUNTING", "Update draft purchase invoices"),
    (PermissionCode.PURCHASE_POST, "ACCOUNTING", "Post purchase invoices"),
    (PermissionCode.PURCHASE_CANCEL, "ACCOUNTING", "Cancel purchase invoices"),
    (PermissionCode.PAYMENT_VIEW, "ACCOUNTING", "View payments"),
    (PermissionCode.PAYMENT_CREATE, "ACCOUNTING", "Record payments"),
    (PermissionCode.RECEIPT_VIEW, "ACCOUNTING", "View receipts"),
    (PermissionCode.RECEIPT_CREATE, "ACCOUNTING", "Record receipts"),
    (PermissionCode.JOURNAL_VIEW, "ACCOUNTING", "View journal entries"),
    (PermissionCode.JOURNAL_CREATE, "ACCOUNTING", "Create journal entries"),
    (PermissionCode.JOURNAL_POST, "ACCOUNTING", "Post journal entries"),
    (PermissionCode.ACCOUNTING_IMPORT, "ACCOUNTING", "Upload and preview accounting data imports"),
    (PermissionCode.ACCOUNTING_IMPORT_COMMIT, "ACCOUNTING", "Commit accounting data imports"),
    (PermissionCode.ACCOUNTING_IMPORT_VIEW, "ACCOUNTING", "View import jobs and their results"),
    (PermissionCode.TALLY_IMPORT_VIEW, "TALLY", "View Tally imports and reconciliation"),
    (PermissionCode.TALLY_IMPORT_CREATE, "TALLY", "Upload and preview Tally imports"),
    (PermissionCode.TALLY_IMPORT_COMMIT, "TALLY", "Commit Tally data into accounting"),
    (PermissionCode.TALLY_IMPORT_EXPORT, "TALLY", "Manage Tally import and export pipelines"),
    (PermissionCode.TALLY_MAPPING_MANAGE, "TALLY", "Create and manage Tally mapping templates"),
    (PermissionCode.TALLY_EXPORT_VIEW, "TALLY", "View Tally export profiles"),
    (PermissionCode.TALLY_EXPORT_CREATE, "TALLY", "Generate Tally compatible export files"),
    (PermissionCode.GST_VIEW, "GST", "View GST profile and tax configuration"),
    (PermissionCode.GST_CREATE, "GST", "Create GST profile and tax configuration"),
    (PermissionCode.GST_UPDATE, "GST", "Update GST profile and tax configuration"),
    (PermissionCode.GST_RETURN_VIEW, "GST", "View GST return periods"),
    (PermissionCode.GST_RETURN_GENERATE, "GST", "Generate GST return preparation data"),
    (PermissionCode.GST_RETURN_VALIDATE, "GST", "Validate GST return preparation data"),
    (PermissionCode.GST_RETURN_APPROVE, "GST", "Approve a GST return preparation"),
    (PermissionCode.GST_RETURN_FINALIZE, "GST", "Finalize a GST return preparation"),
    (PermissionCode.GSTR1_VIEW, "GST", "View GSTR-1 preparation data"),
    (PermissionCode.GSTR1_GENERATE, "GST", "Generate GSTR-1 preparation data"),
    (PermissionCode.GSTR1_EXPORT, "GST", "Export GSTR-1 preparation reports"),
    (PermissionCode.GSTR2B_IMPORT, "GST", "Import GSTR-2B statements"),
    (PermissionCode.GSTR2B_VIEW, "GST", "View imported GSTR-2B records"),
    (PermissionCode.GSTR2B_RECONCILE, "GST", "Run purchase-vs-GSTR-2B reconciliation"),
    (PermissionCode.ITC_VIEW, "GST", "View Input Tax Credit analysis"),
    (PermissionCode.ITC_REVIEW, "GST", "Mark ITC reconciliation results as reviewed"),
    (PermissionCode.ITC_APPROVE, "GST", "Approve or reject ITC reconciliation results"),
    (PermissionCode.GSTR3B_VIEW, "GST", "View GSTR-3B preparation data"),
    (PermissionCode.GSTR3B_GENERATE, "GST", "Generate GSTR-3B preparation data"),
    (PermissionCode.GSTR3B_EXPORT, "GST", "Export GSTR-3B preparation reports"),
    (PermissionCode.TDS_VIEW, "TDS", "View TDS profile and configuration"),
    (PermissionCode.TDS_CREATE, "TDS", "Create TDS profile and configuration"),
    (PermissionCode.TDS_UPDATE, "TDS", "Update TDS profile and configuration"),
    (PermissionCode.TDS_DEDUCTEE_VIEW, "TDS", "View deductees"),
    (PermissionCode.TDS_DEDUCTEE_MANAGE, "TDS", "Create and update deductees"),
    (PermissionCode.TDS_RULE_VIEW, "TDS", "View TDS sections and rules"),
    (PermissionCode.TDS_RULE_MANAGE, "TDS", "Create and update TDS rules"),
    (PermissionCode.TDS_TRANSACTION_VIEW, "TDS", "View TDS transactions"),
    (PermissionCode.TDS_TRANSACTION_CREATE, "TDS", "Create TDS transactions"),
    (PermissionCode.TDS_TRANSACTION_UPDATE, "TDS", "Update draft TDS transactions"),
    (PermissionCode.TDS_TRANSACTION_CALCULATE, "TDS", "Run TDS applicability/calculation"),
    (PermissionCode.TDS_TRANSACTION_CANCEL, "TDS", "Cancel a TDS transaction"),
    (PermissionCode.TDS_CHALLAN_VIEW, "TDS", "View TDS challans"),
    (PermissionCode.TDS_CHALLAN_CREATE, "TDS", "Create TDS challans"),
    (PermissionCode.TDS_CHALLAN_UPDATE, "TDS", "Update/allocate TDS challans"),
    (PermissionCode.TDS_CHALLAN_RECONCILE, "TDS", "Run TDS payment reconciliation"),
    (PermissionCode.TDS_RETURN_VIEW, "TDS", "View TDS return periods"),
    (PermissionCode.TDS_RETURN_GENERATE, "TDS", "Generate TDS return preparation data"),
    (PermissionCode.TDS_RETURN_VALIDATE, "TDS", "Validate TDS return preparation data"),
    (PermissionCode.TDS_RETURN_APPROVE, "TDS", "Approve a TDS return preparation"),
    (PermissionCode.TDS_RETURN_FINALIZE, "TDS", "Finalize a TDS return preparation"),
    (PermissionCode.TDS_IMPORT, "TDS", "Upload and preview TDS data imports"),
    (PermissionCode.TDS_IMPORT_COMMIT, "TDS", "Commit TDS data imports"),
    (PermissionCode.TDS_REPORT_VIEW, "TDS", "View TDS reports"),
    (PermissionCode.TDS_REPORT_EXPORT, "TDS", "Export TDS preparation/reconciliation reports"),
    (PermissionCode.BANK_VIEW, "BANK", "View bank accounts"),
    (PermissionCode.BANK_CREATE, "BANK", "Create bank accounts"),
    (PermissionCode.BANK_UPDATE, "BANK", "Update bank accounts"),
    (PermissionCode.BANK_STATEMENT_VIEW, "BANK", "View bank statements and their transactions"),
    (PermissionCode.BANK_STATEMENT_IMPORT, "BANK", "Upload and preview bank statement imports"),
    (PermissionCode.BANK_STATEMENT_IMPORT_COMMIT, "BANK", "Commit bank statement imports"),
    (PermissionCode.BANK_TRANSACTION_VIEW, "BANK", "View bank transactions"),
    (PermissionCode.BANK_TRANSACTION_UPDATE, "BANK", "Exclude/flag bank transactions for review"),
    (PermissionCode.BANK_MATCH_VIEW, "BANK", "View match candidates and match history"),
    (PermissionCode.BANK_MATCH_CREATE, "BANK", "Create manual/partial matches"),
    (PermissionCode.BANK_MATCH_REVERSE, "BANK", "Reverse an existing match"),
    (PermissionCode.BANK_ADJUST, "BANK", "Create an adjustment journal entry from a bank transaction"),
    (PermissionCode.BANK_RECONCILE_VIEW, "BANK", "View reconciliation sessions"),
    (PermissionCode.BANK_RECONCILE_RUN, "BANK", "Start a reconciliation session and run auto-matching"),
    (PermissionCode.BANK_RECONCILE_SUBMIT, "BANK", "Submit a reconciliation session for review"),
    (PermissionCode.BANK_RECONCILE_APPROVE, "BANK", "Approve/reject a reconciliation session"),
    (PermissionCode.BANK_RECONCILE_LOCK, "BANK", "Lock a reconciled session"),
    (PermissionCode.BANK_REPORT_VIEW, "BANK", "View bank reconciliation reports"),
    (PermissionCode.BANK_REPORT_EXPORT, "BANK", "Export bank reconciliation reports"),
    (PermissionCode.AUDIT_ENGAGEMENT_VIEW, "AUDIT_WORKFLOW", "View audit engagements"),
    (PermissionCode.AUDIT_ENGAGEMENT_CREATE, "AUDIT_WORKFLOW", "Create audit engagements"),
    (PermissionCode.AUDIT_ENGAGEMENT_UPDATE, "AUDIT_WORKFLOW", "Update audit engagements and their status"),
    (PermissionCode.AUDIT_ENGAGEMENT_ASSIGN, "AUDIT_WORKFLOW", "Assign/unassign users to an engagement"),
    (PermissionCode.AUDIT_CHECKLIST_VIEW, "AUDIT_WORKFLOW", "View an engagement's checklist"),
    (PermissionCode.AUDIT_CHECKLIST_MANAGE, "AUDIT_WORKFLOW", "Generate and update checklist items"),
    (PermissionCode.AUDIT_FINDING_VIEW, "AUDIT_WORKFLOW", "View audit findings"),
    (PermissionCode.AUDIT_FINDING_CREATE, "AUDIT_WORKFLOW", "Create audit findings"),
    (PermissionCode.AUDIT_FINDING_UPDATE, "AUDIT_WORKFLOW", "Update findings and add comments"),
    (PermissionCode.AUDIT_FINDING_ASSIGN, "AUDIT_WORKFLOW", "Assign a finding to a user"),
    (PermissionCode.AUDIT_FINDING_RESPOND, "AUDIT_WORKFLOW", "Submit a response to an assigned finding"),
    (PermissionCode.AUDIT_FINDING_REVIEW, "AUDIT_WORKFLOW", "Accept/reject a finding response"),
    (PermissionCode.AUDIT_FINDING_RESOLVE, "AUDIT_WORKFLOW", "Resolve or close a finding"),
    (PermissionCode.AUDIT_FINDING_REOPEN, "AUDIT_WORKFLOW", "Reopen a resolved/closed finding"),
    (PermissionCode.AUDIT_EVIDENCE_MANAGE, "AUDIT_WORKFLOW", "Attach or remove finding evidence"),
    (PermissionCode.AUDIT_ENGAGEMENT_REVIEW, "AUDIT_WORKFLOW", "Start/complete an engagement review pass"),
    (PermissionCode.AUDIT_ENGAGEMENT_APPROVE, "AUDIT_WORKFLOW", "Approve an engagement"),
    (PermissionCode.AUDIT_ENGAGEMENT_SIGNOFF, "AUDIT_WORKFLOW", "Record an internal sign-off"),
    (PermissionCode.AUDIT_ENGAGEMENT_LOCK, "AUDIT_WORKFLOW", "Close and lock an engagement"),
    (PermissionCode.AUDIT_REPORT_VIEW, "AUDIT_WORKFLOW", "View audit workflow reports and the review queue"),
    (PermissionCode.AUDIT_REPORT_EXPORT, "AUDIT_WORKFLOW", "Export audit workflow reports"),
    (PermissionCode.INCOME_TAX_VIEW, "INCOME_TAX", "View Income Tax profile, income, deductions, and computations"),
    (PermissionCode.INCOME_TAX_CREATE, "INCOME_TAX", "Create Income Tax profile, income, deduction, and payment records"),
    (PermissionCode.INCOME_TAX_UPDATE, "INCOME_TAX", "Update Income Tax profile, income, deduction, and payment records"),
    (PermissionCode.INCOME_TAX_CALCULATE, "INCOME_TAX", "Run a tax computation"),
    (PermissionCode.INCOME_TAX_VALIDATE, "INCOME_TAX", "Run ITR validation"),
    (PermissionCode.INCOME_TAX_REVIEW, "INCOME_TAX", "Submit a computation/ITR preparation for review"),
    (PermissionCode.INCOME_TAX_APPROVE, "INCOME_TAX", "Approve a tax computation or ITR preparation"),
    (PermissionCode.INCOME_TAX_LOCK, "INCOME_TAX", "Lock an approved tax computation or ITR preparation"),
    (PermissionCode.INCOME_TAX_EXPORT, "INCOME_TAX", "Export Income Tax reports"),
    (PermissionCode.COMPLIANCE_VIEW, "COMPLIANCE", "View compliance obligations, tasks, and the calendar"),
    (PermissionCode.COMPLIANCE_TASK_CREATE, "COMPLIANCE", "Create compliance tasks"),
    (PermissionCode.COMPLIANCE_TASK_UPDATE, "COMPLIANCE", "Update compliance tasks, start work, add comments/evidence"),
    (PermissionCode.COMPLIANCE_TASK_ASSIGN, "COMPLIANCE", "Assign/reassign a compliance task"),
    (PermissionCode.COMPLIANCE_TASK_COMPLETE, "COMPLIANCE", "Submit a compliance task for review or mark it complete"),
    (PermissionCode.COMPLIANCE_TASK_REVIEW, "COMPLIANCE", "Return a compliance task for changes after review"),
    (PermissionCode.COMPLIANCE_TASK_VERIFY, "COMPLIANCE", "Verify a completed compliance task"),
    (PermissionCode.COMPLIANCE_TASK_CANCEL, "COMPLIANCE", "Cancel a compliance task"),
    (PermissionCode.COMPLIANCE_TASK_LOCK, "COMPLIANCE", "Lock a verified/completed compliance task"),
    (PermissionCode.COMPLIANCE_OBLIGATION_MANAGE, "COMPLIANCE", "Create/update compliance obligations and generate tasks from them"),
    (PermissionCode.COMPLIANCE_RULE_MANAGE, "COMPLIANCE", "Create/update/activate/deactivate compliance rules"),
    (PermissionCode.COMPLIANCE_CALENDAR_VIEW, "COMPLIANCE", "View the compliance calendar"),
    (PermissionCode.COMPLIANCE_NOTIFICATION_VIEW, "COMPLIANCE", "View own in-app notifications"),
    (PermissionCode.COMPLIANCE_NOTIFICATION_MANAGE, "COMPLIANCE", "Mark own notifications as read"),
    (PermissionCode.COMPLIANCE_REPORT_EXPORT, "COMPLIANCE", "Export compliance reports"),
]

ALL_PERMISSION_CODES: list[PermissionCode] = [p[0] for p in PERMISSIONS]

ROLE_PERMISSIONS: dict[RoleCode, list[PermissionCode]] = {
    # SUPER_ADMIN receives every permission that exists, including anything
    # added by future modules, via wildcard handling in the RBAC dependency
    # rather than an enumerated list here.
    RoleCode.SUPER_ADMIN: ALL_PERMISSION_CODES,
    RoleCode.COMPANY_ADMIN: [
        PermissionCode.COMPANY_VIEW,
        PermissionCode.COMPANY_UPDATE,
        PermissionCode.COMPANY_MANAGE_USERS,
        PermissionCode.USER_VIEW,
        PermissionCode.USER_CREATE,
        PermissionCode.USER_UPDATE,
        PermissionCode.USER_DEACTIVATE,
        PermissionCode.ROLE_VIEW,
        PermissionCode.ROLE_ASSIGN,
        PermissionCode.DASHBOARD_VIEW,
        PermissionCode.AUDIT_LOG_VIEW,
        PermissionCode.DOCUMENT_VIEW,
        PermissionCode.DOCUMENT_UPLOAD,
        PermissionCode.DOCUMENT_UPDATE,
        PermissionCode.DOCUMENT_ARCHIVE,
        PermissionCode.DOCUMENT_RESTORE,
        PermissionCode.DOCUMENT_DOWNLOAD,
        PermissionCode.ACCOUNTING_VIEW,
        PermissionCode.ACCOUNTING_CREATE,
        PermissionCode.ACCOUNTING_UPDATE,
        PermissionCode.ACCOUNTING_DELETE,
        PermissionCode.LEDGER_VIEW,
        PermissionCode.LEDGER_MANAGE,
        PermissionCode.CUSTOMER_VIEW,
        PermissionCode.CUSTOMER_MANAGE,
        PermissionCode.VENDOR_VIEW,
        PermissionCode.VENDOR_MANAGE,
        PermissionCode.PRODUCT_VIEW,
        PermissionCode.PRODUCT_MANAGE,
        PermissionCode.SALES_VIEW,
        PermissionCode.SALES_CREATE,
        PermissionCode.SALES_UPDATE,
        PermissionCode.SALES_POST,
        PermissionCode.SALES_CANCEL,
        PermissionCode.PURCHASE_VIEW,
        PermissionCode.PURCHASE_CREATE,
        PermissionCode.PURCHASE_UPDATE,
        PermissionCode.PURCHASE_POST,
        PermissionCode.PURCHASE_CANCEL,
        PermissionCode.PAYMENT_VIEW,
        PermissionCode.PAYMENT_CREATE,
        PermissionCode.RECEIPT_VIEW,
        PermissionCode.RECEIPT_CREATE,
        PermissionCode.JOURNAL_VIEW,
        PermissionCode.JOURNAL_CREATE,
        PermissionCode.JOURNAL_POST,
        PermissionCode.ACCOUNTING_IMPORT,
        PermissionCode.ACCOUNTING_IMPORT_COMMIT,
        PermissionCode.ACCOUNTING_IMPORT_VIEW,
        PermissionCode.TALLY_IMPORT_VIEW,
        PermissionCode.TALLY_IMPORT_CREATE,
        PermissionCode.TALLY_IMPORT_COMMIT,
        PermissionCode.TALLY_IMPORT_EXPORT,
        PermissionCode.TALLY_MAPPING_MANAGE,
        PermissionCode.TALLY_EXPORT_VIEW,
        PermissionCode.TALLY_EXPORT_CREATE,
        PermissionCode.GST_VIEW,
        PermissionCode.GST_CREATE,
        PermissionCode.GST_UPDATE,
        PermissionCode.GST_RETURN_VIEW,
        PermissionCode.GST_RETURN_GENERATE,
        PermissionCode.GST_RETURN_VALIDATE,
        PermissionCode.GST_RETURN_APPROVE,
        PermissionCode.GST_RETURN_FINALIZE,
        PermissionCode.GSTR1_VIEW,
        PermissionCode.GSTR1_GENERATE,
        PermissionCode.GSTR1_EXPORT,
        PermissionCode.GSTR2B_IMPORT,
        PermissionCode.GSTR2B_VIEW,
        PermissionCode.GSTR2B_RECONCILE,
        PermissionCode.ITC_VIEW,
        PermissionCode.ITC_REVIEW,
        PermissionCode.ITC_APPROVE,
        PermissionCode.GSTR3B_VIEW,
        PermissionCode.GSTR3B_GENERATE,
        PermissionCode.GSTR3B_EXPORT,
        PermissionCode.TDS_VIEW,
        PermissionCode.TDS_CREATE,
        PermissionCode.TDS_UPDATE,
        PermissionCode.TDS_DEDUCTEE_VIEW,
        PermissionCode.TDS_DEDUCTEE_MANAGE,
        PermissionCode.TDS_RULE_VIEW,
        PermissionCode.TDS_RULE_MANAGE,
        PermissionCode.TDS_TRANSACTION_VIEW,
        PermissionCode.TDS_TRANSACTION_CREATE,
        PermissionCode.TDS_TRANSACTION_UPDATE,
        PermissionCode.TDS_TRANSACTION_CALCULATE,
        PermissionCode.TDS_TRANSACTION_CANCEL,
        PermissionCode.TDS_CHALLAN_VIEW,
        PermissionCode.TDS_CHALLAN_CREATE,
        PermissionCode.TDS_CHALLAN_UPDATE,
        PermissionCode.TDS_CHALLAN_RECONCILE,
        PermissionCode.TDS_RETURN_VIEW,
        PermissionCode.TDS_RETURN_GENERATE,
        PermissionCode.TDS_RETURN_VALIDATE,
        PermissionCode.TDS_RETURN_APPROVE,
        PermissionCode.TDS_RETURN_FINALIZE,
        PermissionCode.TDS_IMPORT,
        PermissionCode.TDS_IMPORT_COMMIT,
        PermissionCode.TDS_REPORT_VIEW,
        PermissionCode.TDS_REPORT_EXPORT,
        PermissionCode.BANK_VIEW,
        PermissionCode.BANK_CREATE,
        PermissionCode.BANK_UPDATE,
        PermissionCode.BANK_STATEMENT_VIEW,
        PermissionCode.BANK_STATEMENT_IMPORT,
        PermissionCode.BANK_STATEMENT_IMPORT_COMMIT,
        PermissionCode.BANK_TRANSACTION_VIEW,
        PermissionCode.BANK_TRANSACTION_UPDATE,
        PermissionCode.BANK_MATCH_VIEW,
        PermissionCode.BANK_MATCH_CREATE,
        PermissionCode.BANK_MATCH_REVERSE,
        PermissionCode.BANK_ADJUST,
        PermissionCode.BANK_RECONCILE_VIEW,
        PermissionCode.BANK_RECONCILE_RUN,
        PermissionCode.BANK_RECONCILE_SUBMIT,
        PermissionCode.BANK_RECONCILE_APPROVE,
        PermissionCode.BANK_RECONCILE_LOCK,
        PermissionCode.BANK_REPORT_VIEW,
        PermissionCode.BANK_REPORT_EXPORT,
        PermissionCode.AUDIT_ENGAGEMENT_VIEW,
        PermissionCode.AUDIT_ENGAGEMENT_CREATE,
        PermissionCode.AUDIT_ENGAGEMENT_UPDATE,
        PermissionCode.AUDIT_ENGAGEMENT_ASSIGN,
        PermissionCode.AUDIT_CHECKLIST_VIEW,
        PermissionCode.AUDIT_CHECKLIST_MANAGE,
        PermissionCode.AUDIT_FINDING_VIEW,
        PermissionCode.AUDIT_FINDING_RESPOND,
        PermissionCode.AUDIT_EVIDENCE_MANAGE,
        PermissionCode.AUDIT_REPORT_VIEW,
        PermissionCode.AUDIT_REPORT_EXPORT,
        PermissionCode.INCOME_TAX_VIEW,
        PermissionCode.INCOME_TAX_CREATE,
        PermissionCode.INCOME_TAX_UPDATE,
        PermissionCode.INCOME_TAX_CALCULATE,
        PermissionCode.INCOME_TAX_VALIDATE,
        PermissionCode.INCOME_TAX_REVIEW,
        PermissionCode.INCOME_TAX_EXPORT,
        PermissionCode.COMPLIANCE_VIEW,
        PermissionCode.COMPLIANCE_TASK_CREATE,
        PermissionCode.COMPLIANCE_TASK_UPDATE,
        PermissionCode.COMPLIANCE_TASK_ASSIGN,
        PermissionCode.COMPLIANCE_TASK_COMPLETE,
        PermissionCode.COMPLIANCE_TASK_CANCEL,
        PermissionCode.COMPLIANCE_OBLIGATION_MANAGE,
        PermissionCode.COMPLIANCE_RULE_MANAGE,
        PermissionCode.COMPLIANCE_CALENDAR_VIEW,
        PermissionCode.COMPLIANCE_NOTIFICATION_VIEW,
        PermissionCode.COMPLIANCE_NOTIFICATION_MANAGE,
        PermissionCode.COMPLIANCE_REPORT_EXPORT,
    ],
    RoleCode.ACCOUNTANT: [
        PermissionCode.COMPANY_VIEW,
        PermissionCode.USER_VIEW,
        PermissionCode.DASHBOARD_VIEW,
        PermissionCode.DOCUMENT_VIEW,
        PermissionCode.DOCUMENT_UPLOAD,
        PermissionCode.DOCUMENT_UPDATE,
        PermissionCode.DOCUMENT_DOWNLOAD,
        PermissionCode.ACCOUNTING_VIEW,
        PermissionCode.ACCOUNTING_CREATE,
        PermissionCode.ACCOUNTING_UPDATE,
        PermissionCode.LEDGER_VIEW,
        PermissionCode.LEDGER_MANAGE,
        PermissionCode.CUSTOMER_VIEW,
        PermissionCode.CUSTOMER_MANAGE,
        PermissionCode.VENDOR_VIEW,
        PermissionCode.VENDOR_MANAGE,
        PermissionCode.PRODUCT_VIEW,
        PermissionCode.PRODUCT_MANAGE,
        PermissionCode.SALES_VIEW,
        PermissionCode.SALES_CREATE,
        PermissionCode.SALES_UPDATE,
        PermissionCode.SALES_POST,
        PermissionCode.SALES_CANCEL,
        PermissionCode.PURCHASE_VIEW,
        PermissionCode.PURCHASE_CREATE,
        PermissionCode.PURCHASE_UPDATE,
        PermissionCode.PURCHASE_POST,
        PermissionCode.PURCHASE_CANCEL,
        PermissionCode.PAYMENT_VIEW,
        PermissionCode.PAYMENT_CREATE,
        PermissionCode.RECEIPT_VIEW,
        PermissionCode.RECEIPT_CREATE,
        PermissionCode.JOURNAL_VIEW,
        PermissionCode.JOURNAL_CREATE,
        PermissionCode.JOURNAL_POST,
        PermissionCode.ACCOUNTING_IMPORT,
        PermissionCode.ACCOUNTING_IMPORT_COMMIT,
        PermissionCode.ACCOUNTING_IMPORT_VIEW,
        PermissionCode.TALLY_IMPORT_VIEW,
        PermissionCode.TALLY_IMPORT_CREATE,
        PermissionCode.TALLY_IMPORT_COMMIT,
        PermissionCode.TALLY_IMPORT_EXPORT,
        PermissionCode.TALLY_MAPPING_MANAGE,
        PermissionCode.TALLY_EXPORT_VIEW,
        PermissionCode.TALLY_EXPORT_CREATE,
        PermissionCode.GST_VIEW,
        PermissionCode.GST_CREATE,
        PermissionCode.GST_UPDATE,
        PermissionCode.GST_RETURN_VIEW,
        PermissionCode.GST_RETURN_GENERATE,
        PermissionCode.GST_RETURN_VALIDATE,
        PermissionCode.GSTR1_VIEW,
        PermissionCode.GSTR1_GENERATE,
        PermissionCode.GSTR1_EXPORT,
        PermissionCode.GSTR2B_IMPORT,
        PermissionCode.GSTR2B_VIEW,
        PermissionCode.GSTR2B_RECONCILE,
        PermissionCode.ITC_VIEW,
        PermissionCode.ITC_REVIEW,
        PermissionCode.GSTR3B_VIEW,
        PermissionCode.GSTR3B_GENERATE,
        PermissionCode.GSTR3B_EXPORT,
        PermissionCode.TDS_VIEW,
        PermissionCode.TDS_CREATE,
        PermissionCode.TDS_UPDATE,
        PermissionCode.TDS_DEDUCTEE_VIEW,
        PermissionCode.TDS_DEDUCTEE_MANAGE,
        PermissionCode.TDS_RULE_VIEW,
        PermissionCode.TDS_TRANSACTION_VIEW,
        PermissionCode.TDS_TRANSACTION_CREATE,
        PermissionCode.TDS_TRANSACTION_UPDATE,
        PermissionCode.TDS_TRANSACTION_CALCULATE,
        PermissionCode.TDS_TRANSACTION_CANCEL,
        PermissionCode.TDS_CHALLAN_VIEW,
        PermissionCode.TDS_CHALLAN_CREATE,
        PermissionCode.TDS_CHALLAN_UPDATE,
        PermissionCode.TDS_CHALLAN_RECONCILE,
        PermissionCode.TDS_RETURN_VIEW,
        PermissionCode.TDS_RETURN_GENERATE,
        PermissionCode.TDS_RETURN_VALIDATE,
        PermissionCode.TDS_IMPORT,
        PermissionCode.TDS_IMPORT_COMMIT,
        PermissionCode.TDS_REPORT_VIEW,
        PermissionCode.TDS_REPORT_EXPORT,
        PermissionCode.BANK_VIEW,
        PermissionCode.BANK_CREATE,
        PermissionCode.BANK_UPDATE,
        PermissionCode.BANK_STATEMENT_VIEW,
        PermissionCode.BANK_STATEMENT_IMPORT,
        PermissionCode.BANK_STATEMENT_IMPORT_COMMIT,
        PermissionCode.BANK_TRANSACTION_VIEW,
        PermissionCode.BANK_TRANSACTION_UPDATE,
        PermissionCode.BANK_MATCH_VIEW,
        PermissionCode.BANK_MATCH_CREATE,
        PermissionCode.BANK_MATCH_REVERSE,
        PermissionCode.BANK_ADJUST,
        PermissionCode.BANK_RECONCILE_VIEW,
        PermissionCode.BANK_RECONCILE_RUN,
        PermissionCode.BANK_RECONCILE_SUBMIT,
        PermissionCode.BANK_REPORT_VIEW,
        PermissionCode.BANK_REPORT_EXPORT,
        PermissionCode.AUDIT_ENGAGEMENT_VIEW,
        PermissionCode.AUDIT_CHECKLIST_VIEW,
        PermissionCode.AUDIT_FINDING_VIEW,
        PermissionCode.AUDIT_FINDING_RESPOND,
        PermissionCode.AUDIT_EVIDENCE_MANAGE,
        PermissionCode.AUDIT_REPORT_VIEW,
        PermissionCode.INCOME_TAX_VIEW,
        PermissionCode.INCOME_TAX_CREATE,
        PermissionCode.INCOME_TAX_UPDATE,
        PermissionCode.INCOME_TAX_CALCULATE,
        PermissionCode.INCOME_TAX_VALIDATE,
        PermissionCode.INCOME_TAX_REVIEW,
        PermissionCode.INCOME_TAX_EXPORT,
        PermissionCode.COMPLIANCE_VIEW,
        PermissionCode.COMPLIANCE_TASK_CREATE,
        PermissionCode.COMPLIANCE_TASK_UPDATE,
        PermissionCode.COMPLIANCE_TASK_COMPLETE,
        PermissionCode.COMPLIANCE_CALENDAR_VIEW,
        PermissionCode.COMPLIANCE_NOTIFICATION_VIEW,
        PermissionCode.COMPLIANCE_NOTIFICATION_MANAGE,
        PermissionCode.COMPLIANCE_REPORT_EXPORT,
    ],
    RoleCode.AUDITOR: [
        PermissionCode.COMPANY_VIEW,
        PermissionCode.DASHBOARD_VIEW,
        PermissionCode.AUDIT_LOG_VIEW,
        PermissionCode.DOCUMENT_VIEW,
        PermissionCode.DOCUMENT_DOWNLOAD,
        PermissionCode.ACCOUNTING_VIEW,
        PermissionCode.LEDGER_VIEW,
        PermissionCode.CUSTOMER_VIEW,
        PermissionCode.VENDOR_VIEW,
        PermissionCode.PRODUCT_VIEW,
        PermissionCode.SALES_VIEW,
        PermissionCode.PURCHASE_VIEW,
        PermissionCode.PAYMENT_VIEW,
        PermissionCode.RECEIPT_VIEW,
        PermissionCode.JOURNAL_VIEW,
        PermissionCode.ACCOUNTING_IMPORT_VIEW,
        PermissionCode.TALLY_IMPORT_VIEW,
        PermissionCode.TALLY_EXPORT_VIEW,
        PermissionCode.GST_VIEW,
        PermissionCode.GST_RETURN_VIEW,
        PermissionCode.GST_RETURN_APPROVE,
        PermissionCode.GSTR1_VIEW,
        PermissionCode.GSTR2B_VIEW,
        PermissionCode.ITC_VIEW,
        PermissionCode.ITC_APPROVE,
        PermissionCode.GSTR3B_VIEW,
        PermissionCode.TDS_VIEW,
        PermissionCode.TDS_DEDUCTEE_VIEW,
        PermissionCode.TDS_RULE_VIEW,
        PermissionCode.TDS_TRANSACTION_VIEW,
        PermissionCode.TDS_CHALLAN_VIEW,
        PermissionCode.TDS_RETURN_VIEW,
        PermissionCode.TDS_RETURN_APPROVE,
        PermissionCode.TDS_RETURN_FINALIZE,
        PermissionCode.TDS_REPORT_VIEW,
        PermissionCode.BANK_VIEW,
        PermissionCode.BANK_STATEMENT_VIEW,
        PermissionCode.BANK_TRANSACTION_VIEW,
        PermissionCode.BANK_MATCH_VIEW,
        PermissionCode.BANK_RECONCILE_VIEW,
        PermissionCode.BANK_RECONCILE_APPROVE,
        PermissionCode.BANK_RECONCILE_LOCK,
        PermissionCode.BANK_REPORT_VIEW,
        PermissionCode.AUDIT_ENGAGEMENT_VIEW,
        PermissionCode.AUDIT_ENGAGEMENT_UPDATE,
        PermissionCode.AUDIT_CHECKLIST_VIEW,
        PermissionCode.AUDIT_CHECKLIST_MANAGE,
        PermissionCode.AUDIT_FINDING_VIEW,
        PermissionCode.AUDIT_FINDING_CREATE,
        PermissionCode.AUDIT_FINDING_UPDATE,
        PermissionCode.AUDIT_FINDING_ASSIGN,
        PermissionCode.AUDIT_FINDING_REVIEW,
        PermissionCode.AUDIT_FINDING_RESOLVE,
        PermissionCode.AUDIT_FINDING_REOPEN,
        PermissionCode.AUDIT_EVIDENCE_MANAGE,
        PermissionCode.AUDIT_ENGAGEMENT_REVIEW,
        PermissionCode.AUDIT_ENGAGEMENT_APPROVE,
        PermissionCode.AUDIT_ENGAGEMENT_SIGNOFF,
        PermissionCode.AUDIT_ENGAGEMENT_LOCK,
        PermissionCode.AUDIT_REPORT_VIEW,
        PermissionCode.AUDIT_REPORT_EXPORT,
        PermissionCode.INCOME_TAX_VIEW,
        PermissionCode.INCOME_TAX_APPROVE,
        PermissionCode.INCOME_TAX_LOCK,
        PermissionCode.INCOME_TAX_EXPORT,
        PermissionCode.COMPLIANCE_VIEW,
        PermissionCode.COMPLIANCE_TASK_REVIEW,
        PermissionCode.COMPLIANCE_TASK_VERIFY,
        PermissionCode.COMPLIANCE_TASK_LOCK,
        PermissionCode.COMPLIANCE_CALENDAR_VIEW,
        PermissionCode.COMPLIANCE_NOTIFICATION_VIEW,
        PermissionCode.COMPLIANCE_NOTIFICATION_MANAGE,
        PermissionCode.COMPLIANCE_REPORT_EXPORT,
    ],
}

ROLE_DESCRIPTIONS: dict[RoleCode, str] = {
    RoleCode.SUPER_ADMIN: "Platform administrator with full system access",
    RoleCode.COMPANY_ADMIN: "Administers a single company's users and settings",
    RoleCode.ACCOUNTANT: "Prepares and manages day-to-day compliance data",
    RoleCode.AUDITOR: "Read-only reviewer with audit trail visibility",
}
