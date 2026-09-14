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
    ],
    RoleCode.ACCOUNTANT: [
        PermissionCode.COMPANY_VIEW,
        PermissionCode.USER_VIEW,
        PermissionCode.DASHBOARD_VIEW,
        PermissionCode.DOCUMENT_VIEW,
        PermissionCode.DOCUMENT_UPLOAD,
        PermissionCode.DOCUMENT_UPDATE,
        PermissionCode.DOCUMENT_DOWNLOAD,
    ],
    RoleCode.AUDITOR: [
        PermissionCode.COMPANY_VIEW,
        PermissionCode.DASHBOARD_VIEW,
        PermissionCode.AUDIT_LOG_VIEW,
        PermissionCode.DOCUMENT_VIEW,
        PermissionCode.DOCUMENT_DOWNLOAD,
    ],
}

ROLE_DESCRIPTIONS: dict[RoleCode, str] = {
    RoleCode.SUPER_ADMIN: "Platform administrator with full system access",
    RoleCode.COMPANY_ADMIN: "Administers a single company's users and settings",
    RoleCode.ACCOUNTANT: "Prepares and manages day-to-day compliance data",
    RoleCode.AUDITOR: "Read-only reviewer with audit trail visibility",
}
