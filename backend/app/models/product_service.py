from decimal import Decimal

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.accounting_enums import ItemType
from app.models.mixins import RATE, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID


class ProductService(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A sellable/purchasable item. `hsn_sac` is the HSN (goods) or SAC
    (services) classification code GST rates are keyed on — Phase 3 stores
    the applicable rate directly rather than building an HSN-to-rate lookup
    engine, which is future GST-module territory.
    """

    __tablename__ = "products_services"
    __table_args__ = (
        Index("ix_products_services_company_code", "company_id", "code", unique=True),
    )

    company_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    item_type: Mapped[ItemType] = mapped_column(
        Enum(ItemType, native_enum=False, length=10), nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    hsn_sac: Mapped[str | None] = mapped_column(String(20), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tax_rate: Mapped[Decimal] = mapped_column(RATE, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
