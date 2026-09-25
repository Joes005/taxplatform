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


def compute_marginal_relief(
    taxable_income: Decimal,
    tax_after_rebate: Decimal,
    flat_surcharge: Decimal,
    threshold: Decimal,
    prior_threshold_rate: Decimal,
    slabs: list[IncomeTaxSlab],
    rebate_rules: list[IncomeTaxRebateRule] | None = None,
) -> Decimal:
    """Calculates statutory marginal relief on surcharge under Indian Income Tax law.

    The total tax + surcharge payable on taxable income exceeding a threshold
    shall not exceed:
    (Total tax + surcharge payable on income equal to threshold) + (Taxable Income - Threshold).

    Any excess over this cap is granted as marginal relief and deducted from surcharge.
    """
    if taxable_income <= threshold or flat_surcharge <= ZERO or not slabs:
        return ZERO

    excess_income = taxable_income - threshold

    # 1. Tax at the threshold income
    tax_at_threshold = compute_slab_tax(threshold, slabs)
    rebate_at_threshold = compute_rebate(threshold, tax_at_threshold, rebate_rules or [])
    net_tax_at_threshold = tax_at_threshold - rebate_at_threshold

    # 2. Surcharge at the threshold income (if the threshold itself was subject to an earlier surcharge bracket)
    surcharge_at_threshold = ZERO
    if prior_threshold_rate > ZERO:
        surcharge_at_threshold = round_money(net_tax_at_threshold * prior_threshold_rate / Decimal("100"))

    total_tax_at_threshold = net_tax_at_threshold + surcharge_at_threshold

    # 3. Maximum permissible tax + surcharge under marginal relief
    max_permissible_tax = total_tax_at_threshold + excess_income

    # 4. Tax + flat surcharge without relief
    total_tax_without_relief = tax_after_rebate + flat_surcharge

    # 5. Marginal relief is the excess
    if total_tax_without_relief > max_permissible_tax:
        relief = round_money(total_tax_without_relief - max_permissible_tax)
        return min(flat_surcharge, max(ZERO, relief))
    return ZERO


def compute_surcharge(
    taxable_income: Decimal,
    tax_after_rebate: Decimal,
    surcharge_rules: list[IncomeTaxSurchargeRule],
    slabs: list[IncomeTaxSlab] | None = None,
    rebate_rules: list[IncomeTaxRebateRule] | None = None,
) -> tuple[Decimal, bool]:
    """Calculates surcharge once an income threshold is crossed, applying statutory
    marginal relief when slabs are provided.

    Returns (surcharge_amount, threshold_crossed).
    """
    applicable_rule: IncomeTaxSurchargeRule | None = None
    prior_rate = ZERO
    sorted_rules = sorted(surcharge_rules, key=lambda r: r.income_threshold)

    for rule in sorted_rules:
        if taxable_income > rule.income_threshold:
            prior_rate = applicable_rule.rate if applicable_rule else ZERO
            applicable_rule = rule

    if applicable_rule is None:
        return ZERO, False

    flat_surcharge = round_money(tax_after_rebate * applicable_rule.rate / Decimal("100"))

    if slabs:
        relief = compute_marginal_relief(
            taxable_income=taxable_income,
            tax_after_rebate=tax_after_rebate,
            flat_surcharge=flat_surcharge,
            threshold=applicable_rule.income_threshold,
            prior_threshold_rate=prior_rate,
            slabs=slabs,
            rebate_rules=rebate_rules,
        )
        final_surcharge = max(ZERO, round_money(flat_surcharge - relief))
        return final_surcharge, True

    return flat_surcharge, True


def compute_cess(base_tax: Decimal, cess_rate: Decimal) -> Decimal:
    return round_money(base_tax * cess_rate / Decimal("100"))


def compute_gross_tax_liability(
    taxable_income: Decimal, rule_set: IncomeTaxRuleSet
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, bool]:
    """Runs the full slab -> rebate -> surcharge (with marginal relief) -> cess
    sequence and returns `(tax_before_rebate, rebate, surcharge, cess,
    gross_tax_liability, surcharge_applied)`."""
    tax_before_rebate = compute_slab_tax(taxable_income, rule_set.slabs)
    rebate = compute_rebate(taxable_income, tax_before_rebate, rule_set.rebate_rules)
    tax_after_rebate = tax_before_rebate - rebate
    surcharge, surcharge_applied = compute_surcharge(
        taxable_income,
        tax_after_rebate,
        rule_set.surcharge_rules,
        slabs=rule_set.slabs,
        rebate_rules=rule_set.rebate_rules,
    )
    cess = compute_cess(tax_after_rebate + surcharge, rule_set.cess_rate)
    gross_tax_liability = round_money(tax_after_rebate + surcharge + cess)
    return tax_before_rebate, rebate, surcharge, cess, gross_tax_liability, surcharge_applied

