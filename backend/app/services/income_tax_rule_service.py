from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.income_tax_enums import TaxpayerType, TaxRegime
from app.models.income_tax_rule_set import IncomeTaxRuleSet
from app.repositories.income_tax_rule_set_repository import IncomeTaxRuleSetRepository


class IncomeTaxRuleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncomeTaxRuleSetRepository(db)

    async def get_active_rule_set(
        self, *, assessment_year: str, taxpayer_type: TaxpayerType, tax_regime: TaxRegime
    ) -> IncomeTaxRuleSet:
        rule_set = await self.repo.get_active_rule_set(
            assessment_year=assessment_year, taxpayer_type=taxpayer_type, tax_regime=tax_regime
        )
        if rule_set is None:
            raise ValidationAppError(
                f"No active tax rule set configured for AY {assessment_year} / "
                f"{taxpayer_type.value} / {tax_regime.value}",
                code="INCOME_TAX_RULE_SET_NOT_CONFIGURED",
            )
        return rule_set

    async def list_for_assessment_year(self, assessment_year: str) -> list[IncomeTaxRuleSet]:
        return await self.repo.list_for_assessment_year(assessment_year)

    async def get_by_id(self, rule_set_id) -> IncomeTaxRuleSet:
        rule_set = await self.repo.get_by_id(rule_set_id)
        if rule_set is None:
            raise NotFoundError("Tax rule set not found", code="INCOME_TAX_RULE_SET_NOT_FOUND")
        return rule_set
