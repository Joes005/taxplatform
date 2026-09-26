from sqlalchemy import ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class TallyMappingTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Company-scoped, versioned mapping template for Tally ledgers,
    parties, and voucher types. Never shared across companies."""

    __tablename__ = "tally_mapping_templates"
    __table_args__ = (
        Index("ix_tally_mapping_templates_company", "company_id"),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # rules is a dict with structure:
    # {
    #   "ledgers": [{"source_name": "Sales", "target_id": "...", "target_name": "Sales Revenue"}, ...],
    #   "parties": [{"source_name": "ABC Corp", "target_id": "...", "target_name": "ABC Corp", "party_type": "CUSTOMER"}, ...],
    #   "voucher_types": {"Sales": "SALES", "Purchase": "PURCHASES", ...}
    # }
    rules: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
