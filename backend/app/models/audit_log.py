from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable record of a security- or state-changing action.

    company_id is nullable to support platform-level actions (e.g. a
    SUPER_ADMIN creating a company, before any membership exists).
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_company_created", "company_id", "created_at"),
    )

    company_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Structured, non-sensitive context. Never store passwords or tokens here.
    # Python attribute is `log_metadata` because SQLAlchemy reserves
    # `metadata` on declarative models; the underlying column is `metadata`.
    log_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
