import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.income_tax_enums import TaxpayerType, TaxRegime
from app.models.income_tax_rule_set import IncomeTaxRuleSet


class IncomeTaxRuleSetRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _with_children(self):
        return select(IncomeTaxRuleSet).options(
            selectinload(IncomeTaxRuleSet.slabs),
            selectinload(IncomeTaxRuleSet.rebate_rules),
            selectinload(IncomeTaxRuleSet.surcharge_rules),
            selectinload(IncomeTaxRuleSet.deduction_rules),
        )

    async def get_by_id(self, rule_set_id: uuid.UUID) -> IncomeTaxRuleSet | None:
        result = await self.db.execute(self._with_children().where(IncomeTaxRuleSet.id == rule_set_id))
        return result.scalar_one_or_none()

    async def get_active_rule_set(
        self, *, assessment_year: str, taxpayer_type: TaxpayerType, tax_regime: TaxRegime
    ) -> IncomeTaxRuleSet | None:
        result = await self.db.execute(
            self._with_children()
            .where(
                IncomeTaxRuleSet.assessment_year == assessment_year,
                IncomeTaxRuleSet.taxpayer_type == taxpayer_type,
                IncomeTaxRuleSet.tax_regime == tax_regime,
                IncomeTaxRuleSet.is_active.is_(True),
            )
            .order_by(IncomeTaxRuleSet.version.desc())
        )
        return result.scalars().first()

    async def list_for_assessment_year(self, assessment_year: str) -> list[IncomeTaxRuleSet]:
        result = await self.db.execute(
            self._with_children()
            .where(IncomeTaxRuleSet.assessment_year == assessment_year)
            .order_by(IncomeTaxRuleSet.taxpayer_type, IncomeTaxRuleSet.tax_regime)
        )
        return list(result.scalars().unique().all())
