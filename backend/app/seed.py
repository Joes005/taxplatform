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
    GSTTaxRate,
    Permission,
    Role,
    RolePermission,
    TDSRule,
    TDSSection,
    User,
)

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
        await seed_super_admin(db)
        await db.commit()
    logger.info("Seed complete.")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
