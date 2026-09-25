"""Idempotent seed script for roles, permissions, and the bootstrap super admin.

Run with: python -m app.seed
Safe to run multiple times — existing rows are left untouched or updated,
never duplicated.
"""

import asyncio
import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.permissions import PERMISSIONS, ROLE_DESCRIPTIONS, ROLE_PERMISSIONS, RoleCode
from app.core.security import hash_password
from app.models import (
    ComplianceRule,
    GSTTaxRate,
    IncomeTaxDeductionRule,
    IncomeTaxRebateRule,
    IncomeTaxRuleSet,
    IncomeTaxSlab,
    IncomeTaxSurchargeRule,
    Permission,
    Role,
    RolePermission,
    TDSRule,
    TDSSection,
    User,
)
from app.models.compliance_enums import ComplianceCategory, ComplianceFrequency, ComplianceModule, CompliancePriority
from app.models.income_tax_enums import TaxpayerType, TaxRegime

# The standard GST slabs in force since 1 Jul 2017. These are platform-wide
# defaults (company_id=None) a company can use as-is or supplement with its
# own rates — not an authoritative, government-sourced rate table.
DEFAULT_GST_RATES: list[Decimal] = [
    Decimal("0"),
    Decimal("5"),
    Decimal("12"),
    Decimal("18"),
    Decimal("28"),
]
_GST_RATES_EFFECTIVE_FROM = date(2017, 7, 1)

# A small, documented sample of common TDS sections and their standard
# rates — for local development/testing, not an authoritative,
# government-sourced statutory rate table (PHASE5 section 11). Real rates
# change by Finance Act; a production deployment must have a CA configure
# `TDSRule` rows for the sections/rates actually applicable.
_TDS_RULES_EFFECTIVE_FROM = date(2021, 4, 1)
DEFAULT_TDS_SECTIONS: list[dict] = [
    {
        "section_code": "194C",
        "name": "Payment to Contractors",
        "description": "TDS on payment to resident contractors/sub-contractors for work contracts.",
        "payment_nature": "Contractor/sub-contractor payments",
        "rate": Decimal("1"),
        "no_pan_rate": Decimal("20"),
        "threshold_amount": Decimal("30000"),
        "aggregate_threshold_amount": Decimal("100000"),
    },
    {
        "section_code": "194H",
        "name": "Commission or Brokerage",
        "description": "TDS on commission or brokerage payments (excluding insurance commission).",
        "payment_nature": "Commission/brokerage",
        "rate": Decimal("5"),
        "no_pan_rate": Decimal("20"),
        "threshold_amount": Decimal("15000"),
        "aggregate_threshold_amount": None,
    },
    {
        "section_code": "194I",
        "name": "Rent",
        "description": "TDS on rent for plant/machinery/equipment or land/building/furniture.",
        "payment_nature": "Rent",
        "rate": Decimal("10"),
        "no_pan_rate": Decimal("20"),
        "threshold_amount": Decimal("240000"),
        "aggregate_threshold_amount": None,
    },
    {
        "section_code": "194J",
        "name": "Professional or Technical Fees",
        "description": "TDS on fees for professional or technical services, royalty, or director's remuneration.",
        "payment_nature": "Professional/technical fees",
        "rate": Decimal("10"),
        "no_pan_rate": Decimal("20"),
        "threshold_amount": Decimal("30000"),
        "aggregate_threshold_amount": None,
    },
    {
        "section_code": "194Q",
        "name": "Purchase of Goods",
        "description": "TDS on purchase of goods exceeding the aggregate threshold in a financial year.",
        "payment_nature": "Purchase of goods",
        "rate": Decimal("0.1"),
        "no_pan_rate": Decimal("5"),
        "threshold_amount": Decimal("0"),
        "aggregate_threshold_amount": Decimal("5000000"),
    },
]

# One illustrative, explicitly non-authoritative Income Tax rule set per
# regime for AY 2026-27 (FY 2025-26), INDIVIDUAL taxpayers only — the
# same "small, documented sample configuration" precedent as
# DEFAULT_TDS_SECTIONS above (PHASE8 section 88). Real slab/rebate/
# surcharge figures change by Finance Act; a real deployment must have a
# CA configure `IncomeTaxRuleSet` rows (including for COMPANY/LLP/
# PARTNERSHIP/TRUST/HUF, none of which are seeded here) from an official
# source before this is used for anything beyond development/demo.
_INCOME_TAX_RULE_SET_ASSESSMENT_YEAR = "2026-27"
_INCOME_TAX_RULE_SET_EFFECTIVE_FROM = date(2025, 4, 1)

DEFAULT_INCOME_TAX_RULE_SETS: list[dict] = [
    {
        "tax_regime": TaxRegime.NEW_REGIME,
        "cess_rate": Decimal("4.00"),
        "slabs": [
            (Decimal("0"), Decimal("400000"), Decimal("0")),
            (Decimal("400000"), Decimal("800000"), Decimal("5")),
            (Decimal("800000"), Decimal("1200000"), Decimal("10")),
            (Decimal("1200000"), Decimal("1600000"), Decimal("15")),
            (Decimal("1600000"), Decimal("2000000"), Decimal("20")),
            (Decimal("2000000"), Decimal("2400000"), Decimal("25")),
            (Decimal("2400000"), None, Decimal("30")),
        ],
        "rebate": (Decimal("1200000"), Decimal("60000")),
        "surcharge": [
            (Decimal("5000000"), Decimal("10")),
            (Decimal("10000000"), Decimal("15")),
            (Decimal("20000000"), Decimal("25")),
        ],
        "deduction_rules": [
            ("80CCD(2)", "Employer contribution to NPS", None, True, True),
        ],
    },
    {
        "tax_regime": TaxRegime.OLD_REGIME,
        "cess_rate": Decimal("4.00"),
        "slabs": [
            (Decimal("0"), Decimal("250000"), Decimal("0")),
            (Decimal("250000"), Decimal("500000"), Decimal("5")),
            (Decimal("500000"), Decimal("1000000"), Decimal("20")),
            (Decimal("1000000"), None, Decimal("30")),
        ],
        "rebate": (Decimal("500000"), Decimal("12500")),
        "surcharge": [
            (Decimal("5000000"), Decimal("10")),
            (Decimal("10000000"), Decimal("15")),
            (Decimal("20000000"), Decimal("25")),
            (Decimal("50000000"), Decimal("37")),
        ],
        "deduction_rules": [
            ("80C", "Life insurance, PF, ELSS, tuition fees, etc.", Decimal("150000"), True, False),
            ("80D", "Health insurance premium", Decimal("25000"), True, False),
            ("80TTA", "Interest on savings account (non-senior citizen)", Decimal("10000"), True, False),
            ("80TTB", "Interest income (senior citizen)", Decimal("50000"), True, False),
            ("80G", "Donations to eligible charitable institutions", None, True, False),
            ("80CCD(2)", "Employer contribution to NPS", None, True, True),
        ],
    },
]

# A small, documented sample of platform-wide compliance rules (PHASE9
# section 7, 48) — illustrative demo data, not an authoritative statutory
# compliance calendar. A real deployment must have an admin configure
# `ComplianceRule` rows for the deadlines actually applicable.
_COMPLIANCE_RULES_EFFECTIVE_FROM = date(2025, 4, 1)
DEFAULT_COMPLIANCE_RULES: list[dict] = [
    {
        "code": "GSTR3B_MONTHLY",
        "name": "Monthly GSTR-3B Filing",
        "description": "Prepare and review GSTR-3B for the previous month.",
        "category": ComplianceCategory.GST,
        "module": ComplianceModule.GST,
        "frequency": ComplianceFrequency.MONTHLY,
        "due_date_rule": {"type": "DAY_OF_MONTH_AFTER_PERIOD_END", "month_offset": 1, "day": 20},
        "priority": CompliancePriority.HIGH,
    },
    {
        "code": "GSTR1_MONTHLY",
        "name": "Monthly GSTR-1 Filing",
        "description": "Prepare and review GSTR-1 for the previous month.",
        "category": ComplianceCategory.GST,
        "module": ComplianceModule.GST,
        "frequency": ComplianceFrequency.MONTHLY,
        "due_date_rule": {"type": "DAY_OF_MONTH_AFTER_PERIOD_END", "month_offset": 1, "day": 11},
        "priority": CompliancePriority.HIGH,
    },
    {
        "code": "TDS_RETURN_QUARTERLY",
        "name": "Quarterly TDS Return",
        "description": "Prepare, review, and finalize the quarterly TDS return.",
        "category": ComplianceCategory.TDS,
        "module": ComplianceModule.TDS,
        "frequency": ComplianceFrequency.QUARTERLY,
        "due_date_rule": {"type": "DAYS_AFTER_PERIOD_END", "days": 31},
        "priority": CompliancePriority.HIGH,
    },
    {
        "code": "TDS_CHALLAN_MONTHLY",
        "name": "Monthly TDS Challan Deposit Review",
        "description": "Confirm TDS deducted this month has been deposited and reconciled.",
        "category": ComplianceCategory.TDS,
        "module": ComplianceModule.TDS,
        "frequency": ComplianceFrequency.MONTHLY,
        "due_date_rule": {"type": "DAY_OF_MONTH_AFTER_PERIOD_END", "month_offset": 1, "day": 7},
        "priority": CompliancePriority.MEDIUM,
    },
    {
        "code": "BANK_RECONCILIATION_MONTHLY",
        "name": "Monthly Bank Reconciliation",
        "description": "Reconcile every active bank account for the previous month.",
        "category": ComplianceCategory.BANK,
        "module": ComplianceModule.BANK_RECONCILIATION,
        "frequency": ComplianceFrequency.MONTHLY,
        "due_date_rule": {"type": "DAY_OF_MONTH_AFTER_PERIOD_END", "month_offset": 1, "day": 10},
        "priority": CompliancePriority.MEDIUM,
    },
]

logger = logging.getLogger(__name__)


async def seed_permissions(db: AsyncSession) -> dict[str, Permission]:
    result = await db.execute(select(Permission))
    existing = {p.code: p for p in result.scalars().all()}

    for code, module, description in PERMISSIONS:
        if code.value in existing:
            continue
        permission = Permission(code=code.value, module=module, description=description)
        db.add(permission)
        existing[code.value] = permission

    await db.flush()
    return existing


async def seed_roles(db: AsyncSession) -> dict[str, Role]:
    result = await db.execute(select(Role))
    existing = {r.code: r for r in result.scalars().all()}

    for role_code in RoleCode:
        if role_code.value in existing:
            continue
        role = Role(
            code=role_code.value,
            name=role_code.value.replace("_", " ").title(),
            description=ROLE_DESCRIPTIONS[role_code],
            is_system_role=True,
        )
        db.add(role)
        existing[role_code.value] = role

    await db.flush()
    return existing


async def seed_role_permissions(
    db: AsyncSession, roles: dict[str, Role], permissions: dict[str, Permission]
) -> None:
    result = await db.execute(select(RolePermission))
    existing_pairs = {(rp.role_id, rp.permission_id) for rp in result.scalars().all()}

    for role_code, permission_codes in ROLE_PERMISSIONS.items():
        role = roles[role_code.value]
        for permission_code in permission_codes:
            permission = permissions[permission_code.value]
            if (role.id, permission.id) in existing_pairs:
                continue
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
            existing_pairs.add((role.id, permission.id))


async def seed_gst_default_tax_rates(db: AsyncSession) -> None:
    result = await db.execute(select(GSTTaxRate).where(GSTTaxRate.company_id.is_(None)))
    existing_rates = {r.rate for r in result.scalars().all()}

    for rate in DEFAULT_GST_RATES:
        if rate in existing_rates:
            continue
        db.add(
            GSTTaxRate(
                company_id=None,
                rate=rate,
                description=f"Standard {rate}% GST slab",
                effective_from=_GST_RATES_EFFECTIVE_FROM,
            )
        )
    await db.flush()


async def seed_default_tds_sections_and_rules(db: AsyncSession) -> None:
    result = await db.execute(select(TDSSection))
    existing_sections = {s.section_code: s for s in result.scalars().all()}

    for entry in DEFAULT_TDS_SECTIONS:
        section = existing_sections.get(entry["section_code"])
        if section is None:
            section = TDSSection(
                section_code=entry["section_code"],
                name=entry["name"],
                description=entry["description"],
                payment_nature=entry["payment_nature"],
                effective_from=_TDS_RULES_EFFECTIVE_FROM,
            )
            db.add(section)
            await db.flush()
            existing_sections[entry["section_code"]] = section

        rule_result = await db.execute(
            select(TDSRule).where(
                TDSRule.tds_section_id == section.id, TDSRule.company_id.is_(None)
            )
        )
        if rule_result.scalar_one_or_none() is not None:
            continue

        db.add(
            TDSRule(
                tds_section_id=section.id,
                company_id=None,
                rate=entry["rate"],
                no_pan_rate=entry["no_pan_rate"],
                threshold_amount=entry["threshold_amount"],
                aggregate_threshold_amount=entry["aggregate_threshold_amount"],
                effective_from=_TDS_RULES_EFFECTIVE_FROM,
            )
        )
    await db.flush()


async def seed_default_income_tax_rule_sets(db: AsyncSession) -> None:
    ay_configs = [
        ("2026-27", _INCOME_TAX_RULE_SET_EFFECTIVE_FROM),
        ("2027-28", date(2026, 4, 1)),
    ]

    company_rule_sets = [
        {
            "tax_regime": TaxRegime.NEW_REGIME,
            "cess_rate": Decimal("4.00"),
            "slabs": [(Decimal("0"), None, Decimal("22"))],
            "rebate": (Decimal("0"), Decimal("0")),
            "surcharge": [(Decimal("10000000"), Decimal("10"))],
            "deduction_rules": [],
        },
        {
            "tax_regime": TaxRegime.OLD_REGIME,
            "cess_rate": Decimal("4.00"),
            "slabs": [(Decimal("0"), None, Decimal("25"))],
            "rebate": (Decimal("0"), Decimal("0")),
            "surcharge": [(Decimal("10000000"), Decimal("7")), (Decimal("100000000"), Decimal("12"))],
            "deduction_rules": [],
        },
    ]

    all_specs = []
    for ay, eff_from in ay_configs:
        for entry in DEFAULT_INCOME_TAX_RULE_SETS:
            all_specs.append((ay, eff_from, TaxpayerType.INDIVIDUAL, entry))
        for entry in company_rule_sets:
            all_specs.append((ay, eff_from, TaxpayerType.COMPANY, entry))

    for ay, eff_from, tp_type, entry in all_specs:
        existing = await db.execute(
            select(IncomeTaxRuleSet).where(
                IncomeTaxRuleSet.assessment_year == ay,
                IncomeTaxRuleSet.taxpayer_type == tp_type,
                IncomeTaxRuleSet.tax_regime == entry["tax_regime"],
                IncomeTaxRuleSet.version == 1,
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue

        rule_set = IncomeTaxRuleSet(
            assessment_year=ay,
            taxpayer_type=tp_type,
            tax_regime=entry["tax_regime"],
            effective_from=eff_from,
            version=1,
            is_active=True,
            cess_rate=entry["cess_rate"],
            description=(
                f"Illustrative sample rule set for {tp_type.value} ({ay}) — "
                "verify against official CBDT notifications before real use."
            ),
        )
        db.add(rule_set)
        await db.flush()

        for index, (lower, upper, rate) in enumerate(entry["slabs"]):
            db.add(
                IncomeTaxSlab(
                    rule_set_id=rule_set.id, lower_limit=lower, upper_limit=upper, rate=rate, order_index=index
                )
            )

        max_income, max_rebate = entry["rebate"]
        db.add(IncomeTaxRebateRule(rule_set_id=rule_set.id, maximum_income=max_income, maximum_rebate=max_rebate))

        for index, (threshold, rate) in enumerate(entry["surcharge"]):
            db.add(
                IncomeTaxSurchargeRule(
                    rule_set_id=rule_set.id, income_threshold=threshold, rate=rate, order_index=index
                )
            )

        for section_code, description, max_amount, allowed_old, allowed_new in entry["deduction_rules"]:
            db.add(
                IncomeTaxDeductionRule(
                    rule_set_id=rule_set.id,
                    section_code=section_code,
                    description=description,
                    max_amount=max_amount,
                    allowed_in_old_regime=allowed_old,
                    allowed_in_new_regime=allowed_new,
                )
            )

    await db.flush()


async def seed_default_compliance_rules(db: AsyncSession) -> None:
    for entry in DEFAULT_COMPLIANCE_RULES:
        existing = await db.execute(
            select(ComplianceRule).where(
                ComplianceRule.code == entry["code"],
                ComplianceRule.company_id.is_(None),
                ComplianceRule.version == 1,
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue

        db.add(
            ComplianceRule(
                company_id=None,
                code=entry["code"],
                name=entry["name"],
                description=entry["description"],
                category=entry["category"],
                module=entry["module"],
                frequency=entry["frequency"],
                due_date_rule=entry["due_date_rule"],
                priority=entry["priority"],
                effective_from=_COMPLIANCE_RULES_EFFECTIVE_FROM,
                version=1,
                is_active=True,
            )
        )
    await db.flush()


async def seed_super_admin(db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.email == settings.SEED_SUPER_ADMIN_EMAIL.lower()))
    if result.scalar_one_or_none() is not None:
        return

    admin = User(
        email=settings.SEED_SUPER_ADMIN_EMAIL.lower(),
        password_hash=hash_password(settings.SEED_SUPER_ADMIN_PASSWORD),
        first_name=settings.SEED_SUPER_ADMIN_FIRST_NAME,
        last_name=settings.SEED_SUPER_ADMIN_LAST_NAME,
        is_active=True,
        is_verified=True,
        is_platform_super_admin=True,
    )
    db.add(admin)
    logger.info("Seeded platform super admin: %s", admin.email)


async def run_seed() -> None:
    async with AsyncSessionLocal() as db:
        permissions = await seed_permissions(db)
        roles = await seed_roles(db)
        await seed_role_permissions(db, roles, permissions)
        await seed_gst_default_tax_rates(db)
        await seed_default_tds_sections_and_rules(db)
        await seed_default_income_tax_rule_sets(db)
        await seed_default_compliance_rules(db)
        await seed_super_admin(db)
        await db.commit()
    logger.info("Seed complete.")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
