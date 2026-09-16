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
        PermissionCode.GST_VIEW,
        PermissionCode.GST_RETURN_VIEW,
        PermissionCode.GST_RETURN_APPROVE,
        PermissionCode.GSTR1_VIEW,
        PermissionCode.GSTR2B_VIEW,
        PermissionCode.ITC_VIEW,
        PermissionCode.ITC_APPROVE,
        PermissionCode.GSTR3B_VIEW,
    ],
}

ROLE_DESCRIPTIONS: dict[RoleCode, str] = {
    RoleCode.SUPER_ADMIN: "Platform administrator with full system access",
    RoleCode.COMPANY_ADMIN: "Administers a single company's users and settings",
    RoleCode.ACCOUNTANT: "Prepares and manages day-to-day compliance data",
    RoleCode.AUDITOR: "Read-only reviewer with audit trail visibility",
}
