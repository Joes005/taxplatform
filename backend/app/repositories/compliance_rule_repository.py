import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_enums import ComplianceCategory, ComplianceModule
from app.models.compliance_rule import ComplianceRule


class ComplianceRuleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, rule: ComplianceRule) -> ComplianceRule:
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def get_by_id(self, rule_id: uuid.UUID) -> ComplianceRule | None:
        return await self.db.get(ComplianceRule, rule_id)

    async def get_by_id_visible_to_company(self, rule_id: uuid.UUID, company_id: uuid.UUID) -> ComplianceRule | None:
        result = await self.db.execute(
            select(ComplianceRule).where(
                ComplianceRule.id == rule_id,
                or_(ComplianceRule.company_id == company_id, ComplianceRule.company_id.is_(None)),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_version(self, code: str, company_id: uuid.UUID) -> ComplianceRule | None:
        """The active rule a company should use for `code` — a
        company-specific override (if one exists) always wins over the
        platform-wide default, the same `company_id`-override precedence
        `TDSRule` already uses."""
        override_result = await self.db.execute(
            select(ComplianceRule)
            .where(ComplianceRule.code == code, ComplianceRule.company_id == company_id, ComplianceRule.is_active.is_(True))
            .order_by(ComplianceRule.version.desc())
        )
        override = override_result.scalars().first()
        if override is not None:
            return override

        default_result = await self.db.execute(
            select(ComplianceRule)
            .where(ComplianceRule.code == code, ComplianceRule.company_id.is_(None), ComplianceRule.is_active.is_(True))
            .order_by(ComplianceRule.version.desc())
        )
        return default_result.scalars().first()

    async def list_visible_to_company(
        self,
        company_id: uuid.UUID,
        *,
        category: ComplianceCategory | None = None,
        module: ComplianceModule | None = None,
        active_only: bool = False,
    ) -> list[ComplianceRule]:
        query = select(ComplianceRule).where(
            or_(ComplianceRule.company_id == company_id, ComplianceRule.company_id.is_(None))
        )
        if category is not None:
            query = query.where(ComplianceRule.category == category)
        if module is not None:
            query = query.where(ComplianceRule.module == module)
        if active_only:
            query = query.where(ComplianceRule.is_active.is_(True))
        result = await self.db.execute(query.order_by(ComplianceRule.code, ComplianceRule.version.desc()))
        return list(result.scalars().all())

    async def next_version(self, code: str, company_id: uuid.UUID | None) -> int:
        from sqlalchemy import func

        company_filter = (
            ComplianceRule.company_id.is_(None) if company_id is None else ComplianceRule.company_id == company_id
        )
        result = await self.db.execute(
            select(func.max(ComplianceRule.version)).where(ComplianceRule.code == code, company_filter)
        )
        current_max = result.scalar_one_or_none()
        return (current_max or 0) + 1
