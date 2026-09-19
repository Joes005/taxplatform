from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.income_tax_enums import TaxpayerType, TaxRegime
from app.models.mixins import MONEY, RATE, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.types import GUID

if TYPE_CHECKING:
    pass


class IncomeTaxRuleSet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One versioned bundle of tax law for one (assessment year, taxpayer
    type, regime) combination (PHASE8 §13, §98) — platform-wide
    configuration, never company-scoped, the same shape `TDSSection`/
    `TDSRule` already use for TDS law. Slabs/rebate/surcharge are child
    rows so a future year's rules never overwrite this year's — a new
    `IncomeTaxRuleSet` row is created instead, and `TaxComputationSnapshot`
    always records which `rule_set_id`/version it used (PHASE8 §71).

    Seeded rule sets are explicitly documented, illustrative sample data
    (PHASE8 §88) — never assumed to be authoritative current tax law; a
    real deployment must load its own verified slab/rebate/surcharge
    figures from an official source before this is used for anything
    beyond development/demo.
    """

    __tablename__ = "income_tax_rule_sets"
    __table_args__ = (
        Index(
            "ix_income_tax_rule_sets_unique_version",
            "assessment_year",
            "taxpayer_type",
            "tax_regime",
            "version",
            unique=True,
        ),
    )

    assessment_year: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    taxpayer_type: Mapped[TaxpayerType] = mapped_column(
        Enum(TaxpayerType, native_enum=False, length=15), nullable=False, index=True
    )
    tax_regime: Mapped[TaxRegime] = mapped_column(
        Enum(TaxRegime, native_enum=False, length=15), nullable=False, index=True
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cess_rate: Mapped[Decimal] = mapped_column(RATE, default=Decimal("4.00"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    slabs: Mapped[list["IncomeTaxSlab"]] = relationship(
        "IncomeTaxSlab", back_populates="rule_set", cascade="all, delete-orphan", order_by="IncomeTaxSlab.order_index"
    )
    rebate_rules: Mapped[list["IncomeTaxRebateRule"]] = relationship(
        "IncomeTaxRebateRule", back_populates="rule_set", cascade="all, delete-orphan"
    )
    surcharge_rules: Mapped[list["IncomeTaxSurchargeRule"]] = relationship(
        "IncomeTaxSurchargeRule",
        back_populates="rule_set",
        cascade="all, delete-orphan",
        order_by="IncomeTaxSurchargeRule.order_index",
    )
    deduction_rules: Mapped[list["IncomeTaxDeductionRule"]] = relationship(
        "IncomeTaxDeductionRule", back_populates="rule_set", cascade="all, delete-orphan"
    )


class IncomeTaxSlab(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "income_tax_slabs"
    __table_args__ = (Index("ix_income_tax_slabs_rule_set", "rule_set_id"),)

    rule_set_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("income_tax_rule_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lower_limit: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    upper_limit: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    rate: Mapped[Decimal] = mapped_column(RATE, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    rule_set: Mapped["IncomeTaxRuleSet"] = relationship("IncomeTaxRuleSet", back_populates="slabs")


class IncomeTaxRebateRule(UUIDPrimaryKeyMixin, Base):
    """Section 87A-style rebate: if taxable income is within
    `maximum_income`, the rebate is the smaller of the tax otherwise
    payable and `maximum_rebate` — never a fixed amount applied
    unconditionally."""

    __tablename__ = "income_tax_rebate_rules"
    __table_args__ = (Index("ix_income_tax_rebate_rules_rule_set", "rule_set_id"),)

    rule_set_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("income_tax_rule_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    maximum_income: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    maximum_rebate: Mapped[Decimal] = mapped_column(MONEY, nullable=False)

    rule_set: Mapped["IncomeTaxRuleSet"] = relationship("IncomeTaxRuleSet", back_populates="rebate_rules")


class IncomeTaxSurchargeRule(UUIDPrimaryKeyMixin, Base):
    """A marginal-income threshold and the surcharge rate applying above
    it. Computed as a flat rate on the whole tax once a threshold is
    crossed — marginal relief (the rule that caps the surcharge so it
    never exceeds the excess income over the threshold) is intentionally
    NOT implemented; `IncomeTaxComputationService` instead emits a
    `WARNING` validation item near a threshold so a human verifies it
    (PHASE8 §15, §76)."""

    __tablename__ = "income_tax_surcharge_rules"
    __table_args__ = (Index("ix_income_tax_surcharge_rules_rule_set", "rule_set_id"),)

    rule_set_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("income_tax_rule_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    income_threshold: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    rate: Mapped[Decimal] = mapped_column(RATE, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    rule_set: Mapped["IncomeTaxRuleSet"] = relationship("IncomeTaxRuleSet", back_populates="surcharge_rules")


class IncomeTaxDeductionRule(UUIDPrimaryKeyMixin, Base):
    """Eligibility configuration for one deduction section under one rule
    set (PHASE8 §18-19) — `DeductionService` computes `eligible_amount =
    min(claimed_amount, max_amount)` and rejects a claim outright if the
    section isn't allowed under the computation's regime, rather than
    trusting whatever amount the client sends."""

    __tablename__ = "income_tax_deduction_rules"
    __table_args__ = (
        Index("ix_income_tax_deduction_rules_unique", "rule_set_id", "section_code", unique=True),
    )

    rule_set_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("income_tax_rule_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_code: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    max_amount: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    allowed_in_old_regime: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allowed_in_new_regime: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    rule_set: Mapped["IncomeTaxRuleSet"] = relationship("IncomeTaxRuleSet", back_populates="deduction_rules")
