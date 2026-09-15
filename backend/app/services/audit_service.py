import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.repositories.audit_repository import AuditRepository


class AuditAction:
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    REGISTER = "REGISTER"
    TOKEN_REFRESH = "TOKEN_REFRESH"
    COMPANY_SWITCH = "COMPANY_SWITCH"

    COMPANY_CREATE = "COMPANY_CREATE"
    COMPANY_UPDATE = "COMPANY_UPDATE"

    USER_CREATE = "USER_CREATE"
    USER_UPDATE = "USER_UPDATE"
    USER_DEACTIVATE = "USER_DEACTIVATE"
    USER_ROLE_ASSIGN = "USER_ROLE_ASSIGN"

    DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"
    DOCUMENT_DOWNLOAD = "DOCUMENT_DOWNLOAD"
    DOCUMENT_UPDATE = "DOCUMENT_UPDATE"
    DOCUMENT_ARCHIVE = "DOCUMENT_ARCHIVE"
    DOCUMENT_RESTORE = "DOCUMENT_RESTORE"
    DOCUMENT_DELETE = "DOCUMENT_DELETE"
    DOCUMENT_DUPLICATE_ATTEMPT = "DOCUMENT_DUPLICATE_ATTEMPT"
    DOCUMENT_ACCESS_DENIED = "DOCUMENT_ACCESS_DENIED"

    # --- Accounting (Phase 3) ---
    ACCOUNTING_CREATE = "CREATE"
    ACCOUNTING_UPDATE = "UPDATE"
    ACCOUNTING_DELETE = "DELETE"
    ACCOUNTING_POST = "POST"
    ACCOUNTING_CANCEL = "CANCEL"

    IMPORT_CREATE = "IMPORT"
    IMPORT_COMMIT = "IMPORT_COMMIT"
    IMPORT_FAILED = "IMPORT_FAILED"
    DUPLICATE_DETECTED = "DUPLICATE_DETECTED"

    OPENING_BALANCE_CREATED = "OPENING_BALANCE_CREATED"
    PERIOD_CLOSED = "PERIOD_CLOSED"
    PERIOD_LOCKED = "PERIOD_LOCKED"


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuditRepository(db)

    async def log(
        self,
        *,
        action: str,
        user_id: uuid.UUID | None,
        company_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        description: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        log_entry = AuditLog(
            company_id=company_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            log_metadata=metadata,
        )
        return await self.repo.create(log_entry)
