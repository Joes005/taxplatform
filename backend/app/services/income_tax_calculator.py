"""Pure tax-arithmetic functions (PHASE8 §31-35, §97) — no DB access, no
side effects, so they can be unit tested directly against explicit rule
fixtures (PHASE8 §78) rather than through the full computation service.
Every figure here comes from a caller-supplied `IncomeTaxRuleSet`; nothing
in this module hard-codes a slab, rebate, surcharge, or cess value.
"""

from decimal import Decimal

from app.models.income_tax_rule_set import IncomeTaxRebateRule, IncomeTaxRuleSet, IncomeTaxSlab, IncomeTaxSurchargeRule
from app.services.accounting_calculation_service import round_money

ZERO = Decimal("0")


def compute_slab_tax(taxable_income: Decimal, slabs: list[IncomeTaxSlab]) -> Decimal:
    """Standard progressive-slab tax: each slab taxes only the portion of
    income actually falling within its own [lower_limit, upper_limit)
    band, at that band's own rate."""
    if taxable_income <= ZERO or not slabs:
        return ZERO

    tax = ZERO
    for slab in sorted(slabs, key=lambda s: s.order_index):
        if taxable_income <= slab.lower_limit:
            continue
        band_top = slab.upper_limit if slab.upper_limit is not None else taxable_income
        band_top = min(band_top, taxable_income)
        band_amount = band_top - slab.lower_limit
        if band_amount <= ZERO:
            continue
        tax += band_amount * slab.rate / Decimal("100")
    return round_money(tax)


def compute_rebate(taxable_income: Decimal, tax_before_rebate: Decimal, rebate_rules: list[IncomeTaxRebateRule]) -> Decimal:
    """Section 87A-style: if taxable income is within a rule's
    `maximum_income`, the rebate is the smaller of the tax otherwise
    payable and that rule's `maximum_rebate`. The first matching rule
    wins — a rule set should not configure more than one applicable
    rebate for the same income level."""
    for rule in rebate_rules:
        if taxable_income <= rule.maximum_income:
            return round_money(min(tax_before_rebate, rule.maximum_rebate))
    return ZERO


def compute_surcharge(
    taxable_income: Decimal, tax_after_rebate: Decimal, surcharge_rules: list[IncomeTaxSurchargeRule]
) -> tuple[Decimal, bool]:
    """Flat-rate surcharge once a threshold is crossed — no marginal
    relief (see `IncomeTaxSurchargeRule`'s own docstring). Returns
    `(surcharge_amount, threshold_crossed)` so the caller can raise a
    `WARNING` validation item whenever a surcharge actually applies,
    prompting a human to check marginal relief manually."""
    applicable_rate = ZERO
    crossed = False
    for rule in sorted(surcharge_rules, key=lambda r: r.income_threshold):
        if taxable_income > rule.income_threshold:
            applicable_rate = rule.rate
            crossed = True
    if not crossed:
        return ZERO, False
    return round_money(tax_after_rebate * applicable_rate / Decimal("100")), True


def compute_cess(base_tax: Decimal, cess_rate: Decimal) -> Decimal:
    return round_money(base_tax * cess_rate / Decimal("100"))


def compute_gross_tax_liability(
    taxable_income: Decimal, rule_set: IncomeTaxRuleSet
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, bool]:
    """Runs the full slab -> rebate -> surcharge -> cess sequence and
    returns `(tax_before_rebate, rebate, surcharge, cess,
    gross_tax_liability, surcharge_applied)`."""
    tax_before_rebate = compute_slab_tax(taxable_income, rule_set.slabs)
    rebate = compute_rebate(taxable_income, tax_before_rebate, rule_set.rebate_rules)
    tax_after_rebate = tax_before_rebate - rebate
    surcharge, surcharge_applied = compute_surcharge(taxable_income, tax_after_rebate, rule_set.surcharge_rules)
    cess = compute_cess(tax_after_rebate + surcharge, rule_set.cess_rate)
    gross_tax_liability = round_money(tax_after_rebate + surcharge + cess)
    return tax_before_rebate, rebate, surcharge, cess, gross_tax_liability, surcharge_applied
