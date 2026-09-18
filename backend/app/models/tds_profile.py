from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.tds_enums import DeductorType, TDSProfileStatus
from app.utils.types import GUID


class TDSProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A company's TDS deductor registration details. One company has at
    most one profile — TAN/PAN format are checked structurally on write
    (`app.utils.tan`/`app.utils.pan`), never verified against the Income
    Tax e-filing portal.
    """

    __tablename__ = "tds_profiles"
    __table_args__ = (Index("ix_tds_profiles_company_unique", "company_id", unique=True),)

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tan: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    pan: Mapped[str] = mapped_column(String(10), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deductor_type: Mapped[DeductorType] = mapped_column(
        Enum(DeductorType, native_enum=False, length=15),
        default=DeductorType.COMPANY,
        nullable=False,
    )
    state_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    state_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[TDSProfileStatus] = mapped_column(
        Enum(TDSProfileStatus, native_enum=False, length=10),
        default=TDSProfileStatus.ACTIVE,
        nullable=False,
    )
