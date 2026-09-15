import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.types import GUID

# Shared numeric column types for accounting data. Monetary values are
# always Decimal in Python and NUMERIC in Postgres — never float, which
# cannot represent currency exactly. MONEY matches rupee-and-paise amounts;
# RATE covers tax percentages (up to 999.99%); QUANTITY allows fractional
# quantities (e.g. 2.5 kg).
MONEY = Numeric(18, 2)
RATE = Numeric(5, 2)
QUANTITY = Numeric(18, 3)


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
