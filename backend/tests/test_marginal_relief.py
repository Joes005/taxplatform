from decimal import Decimal
import pytest

from app.models.income_tax_enums import TaxRegime, TaxpayerType
from app.models.income_tax_rule_set import (
    IncomeTaxRebateRule,
    IncomeTaxRuleSet,
    IncomeTaxSlab,
    IncomeTaxSurchargeRule,
)
from app.services.income_tax_calculator import (
    compute_gross_tax_liability,
    compute_marginal_relief,
    compute_slab_tax,
    compute_surcharge,
)


def _build_test_rule_set(regime: TaxRegime = TaxRegime.OLD_REGIME) -> IncomeTaxRuleSet:
    rule_set = IncomeTaxRuleSet(
        assessment_year="2025-26",
        taxpayer_type=TaxpayerType.INDIVIDUAL,
        tax_regime=regime,
        effective_from="2025-04-01",
        cess_rate=Decimal("4.00"),
    )
    if regime == TaxRegime.OLD_REGIME:
        rule_set.slabs = [
            IncomeTaxSlab(lower_limit=Decimal("0"), upper_limit=Decimal("250000"), rate=Decimal("0"), order_index=0),
            IncomeTaxSlab(lower_limit=Decimal("250000"), upper_limit=Decimal("500000"), rate=Decimal("5"), order_index=1),
            IncomeTaxSlab(lower_limit=Decimal("500000"), upper_limit=Decimal("1000000"), rate=Decimal("20"), order_index=2),
            IncomeTaxSlab(lower_limit=Decimal("1000000"), upper_limit=None, rate=Decimal("30"), order_index=3),
        ]
        rule_set.rebate_rules = [
            IncomeTaxRebateRule(maximum_income=Decimal("500000"), maximum_rebate=Decimal("12500")),
        ]
        rule_set.surcharge_rules = [
            IncomeTaxSurchargeRule(income_threshold=Decimal("5000000"), rate=Decimal("10"), order_index=0),
            IncomeTaxSurchargeRule(income_threshold=Decimal("10000000"), rate=Decimal("15"), order_index=1),
            IncomeTaxSurchargeRule(income_threshold=Decimal("20000000"), rate=Decimal("25"), order_index=2),
            IncomeTaxSurchargeRule(income_threshold=Decimal("50000000"), rate=Decimal("37"), order_index=3),
        ]
    else:
        rule_set.slabs = [
            IncomeTaxSlab(lower_limit=Decimal("0"), upper_limit=Decimal("400000"), rate=Decimal("0"), order_index=0),
            IncomeTaxSlab(lower_limit=Decimal("400000"), upper_limit=Decimal("800000"), rate=Decimal("5"), order_index=1),
            IncomeTaxSlab(lower_limit=Decimal("800000"), upper_limit=Decimal("1200000"), rate=Decimal("10"), order_index=2),
            IncomeTaxSlab(lower_limit=Decimal("1200000"), upper_limit=Decimal("1600000"), rate=Decimal("15"), order_index=3),
            IncomeTaxSlab(lower_limit=Decimal("1600000"), upper_limit=Decimal("2000000"), rate=Decimal("20"), order_index=4),
            IncomeTaxSlab(lower_limit=Decimal("2000000"), upper_limit=Decimal("2400000"), rate=Decimal("25"), order_index=5),
            IncomeTaxSlab(lower_limit=Decimal("2400000"), upper_limit=None, rate=Decimal("30"), order_index=6),
        ]
        rule_set.rebate_rules = [
            IncomeTaxRebateRule(maximum_income=Decimal("1200000"), maximum_rebate=Decimal("60000")),
        ]
        rule_set.surcharge_rules = [
            IncomeTaxSurchargeRule(income_threshold=Decimal("5000000"), rate=Decimal("10"), order_index=0),
            IncomeTaxSurchargeRule(income_threshold=Decimal("10000000"), rate=Decimal("15"), order_index=1),
            IncomeTaxSurchargeRule(income_threshold=Decimal("20000000"), rate=Decimal("25"), order_index=2),
        ]
    return rule_set


class TestMarginalReliefOldRegime:
    def test_below_threshold_no_surcharge(self):
        rule_set = _build_test_rule_set(TaxRegime.OLD_REGIME)
        income = Decimal("4900000")
        (
            tax_before_rebate,
            rebate,
            surcharge,
            cess,
            gross,
            applied,
        ) = compute_gross_tax_liability(income, rule_set)

        assert not applied
        assert surcharge == Decimal("0")
        assert rebate == Decimal("0")

    def test_at_threshold_no_surcharge(self):
        rule_set = _build_test_rule_set(TaxRegime.OLD_REGIME)
        income = Decimal("5000000")
        (
            tax_before_rebate,
            rebate,
            surcharge,
            cess,
            gross,
            applied,
        ) = compute_gross_tax_liability(income, rule_set)

        assert not applied
        assert surcharge == Decimal("0")
        # Tax on 50L = 12500 (5%) + 100000 (20%) + 1200000 (30% on 40L) = 1312500
        assert tax_before_rebate == Decimal("1312500.00")

    def test_slightly_above_threshold_50l_marginal_relief(self):
        rule_set = _build_test_rule_set(TaxRegime.OLD_REGIME)
        # Income is Rs 50,10,000 (Rs 10,000 above Rs 50L)
        income = Decimal("5010000")
        (
            tax_before_rebate,
            rebate,
            surcharge,
            cess,
            gross,
            applied,
        ) = compute_gross_tax_liability(income, rule_set)

        assert applied
        tax_at_50l = Decimal("1312500.00")
        excess_income = Decimal("10000.00")
        max_tax_and_surcharge = tax_at_50l + excess_income

        # Tax + surcharge must NOT exceed tax_at_50l + excess_income
        assert tax_before_rebate - rebate + surcharge == max_tax_and_surcharge
        # Tax before surcharge is 13,12,500 + 30% of 10,000 = 13,15,500
        assert tax_before_rebate == Decimal("1315500.00")
        # Therefore relieved surcharge = 13,22,500 - 13,15,500 = 7,000
        assert surcharge == Decimal("7000.00")

    def test_moderately_above_threshold_50l_marginal_relief(self):
        rule_set = _build_test_rule_set(TaxRegime.OLD_REGIME)
        # Income is Rs 51,00,000 (Rs 1,00,000 above Rs 50L)
        income = Decimal("5100000")
        (
            tax_before_rebate,
            rebate,
            surcharge,
            cess,
            gross,
            applied,
        ) = compute_gross_tax_liability(income, rule_set)

        assert applied
        tax_at_50l = Decimal("1312500.00")
        excess_income = Decimal("100000.00")
        max_tax_and_surcharge = tax_at_50l + excess_income

        assert tax_before_rebate - rebate + surcharge == max_tax_and_surcharge
        assert tax_before_rebate == Decimal("1342500.00")
        assert surcharge == Decimal("70000.00")

    def test_high_income_relief_phases_out(self):
        rule_set = _build_test_rule_set(TaxRegime.OLD_REGIME)
        # At Rs 60,00,000 (Rs 10L above 50L), excess income is Rs 10L,
        # which is larger than the flat surcharge, so marginal relief is 0.
        income = Decimal("6000000")
        (
            tax_before_rebate,
            rebate,
            surcharge,
            cess,
            gross,
            applied,
        ) = compute_gross_tax_liability(income, rule_set)

        assert applied
        # Tax before surcharge = 13,12,500 + 30% of 10L = 16,12,500
        assert tax_before_rebate == Decimal("1612500.00")
        # Full 10% flat surcharge = 1,61,250
        assert surcharge == Decimal("161250.00")

    def test_second_threshold_1_crore_marginal_relief(self):
        rule_set = _build_test_rule_set(TaxRegime.OLD_REGIME)
        # Income Rs 1,00,50,000 (Rs 50,000 above 1 Crore)
        income = Decimal("10050000")
        (
            tax_before_rebate,
            rebate,
            surcharge,
            cess,
            gross,
            applied,
        ) = compute_gross_tax_liability(income, rule_set)

        assert applied
        # At 1 Cr: tax = 28,12,500, surcharge (10%) = 2,81,250 => total at 1Cr = 30,93,750
        tax_and_surcharge_at_1cr = Decimal("3093750.00")
        excess_income = Decimal("50000.00")
        max_permissible = tax_and_surcharge_at_1cr + excess_income

        # Tax + surcharge cannot exceed 30,93,750 + 50,000 = 31,43,750
        assert tax_before_rebate - rebate + surcharge == max_permissible


class TestMarginalReliefNewRegime:
    def test_new_regime_slightly_above_50l(self):
        rule_set = _build_test_rule_set(TaxRegime.NEW_REGIME)
        income = Decimal("5020000")
        (
            tax_before_rebate,
            rebate,
            surcharge,
            cess,
            gross,
            applied,
        ) = compute_gross_tax_liability(income, rule_set)

        assert applied
        # Calculate tax at 50L under new regime
        tax_at_50l = compute_slab_tax(Decimal("5000000"), rule_set.slabs)
        excess_income = Decimal("20000.00")
        max_tax_and_surcharge = tax_at_50l + excess_income

        assert tax_before_rebate - rebate + surcharge == max_tax_and_surcharge
