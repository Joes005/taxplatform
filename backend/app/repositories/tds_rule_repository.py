import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tds_rule import TDSRule


class TDSRuleRepository:
    """Rules visible to a company are its own (`company_id == company_id`)
    plus the platform-wide sample rules (`company_id IS NULL`) — never
    another company's rules, mirroring `GSTTaxRateRepository`."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, rule: TDSRule) -> TDSRule:
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def get_by_id_for_company(
        self, rule_id: uuid.UUID, company_id: uuid.UUID
    ) -> TDSRule | None:
        result = await self.db.execute(
            select(TDSRule).where(
                TDSRule.id == rule_id,
                or_(TDSRule.company_id == company_id, TDSRule.company_id.is_(None)),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        tds_section_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        as_of: date | None = None,
    ) -> list[TDSRule]:
        query = select(TDSRule).where(
            or_(TDSRule.company_id == company_id, TDSRule.company_id.is_(None))
        )
        if tds_section_id is not None:
            query = query.where(TDSRule.tds_section_id == tds_section_id)
        if is_active is not None:
            query = query.where(TDSRule.is_active == is_active)
        if as_of is not None:
            query = query.where(
                TDSRule.effective_from <= as_of,
                or_(TDSRule.effective_to.is_(None), TDSRule.effective_to >= as_of),
            )
        result = await self.db.execute(query.order_by(TDSRule.effective_from.desc()))
        return list(result.scalars().all())

    async def find_effective_rule(
        self,
        company_id: uuid.UUID,
        *,
        tds_section_id: uuid.UUID,
        deductee_type,
        as_of: date,
    ) -> TDSRule | None:
        """The rule this section actually applies with on `as_of`: prefers
        a company-specific rule over a platform-wide default, and a rule
        scoped to the deductee's type over one that applies to all types.
        Never returns more than one — the caller decides what to do with
        "no matching rule" (PHASE5 section 3: that's REVIEW_REQUIRED, not
        a fallback guess).
        """
        query = select(TDSRule).where(
            TDSRule.tds_section_id == tds_section_id,
            TDSRule.is_active.is_(True),
            or_(TDSRule.company_id == company_id, TDSRule.company_id.is_(None)),
            TDSRule.effective_from <= as_of,
            or_(TDSRule.effective_to.is_(None), TDSRule.effective_to >= as_of),
            or_(TDSRule.deductee_type.is_(None), TDSRule.deductee_type == deductee_type),
        )
        result = await self.db.execute(query)
        candidates = list(result.scalars().all())
        if not candidates:
            return None

        def _rank(rule: TDSRule) -> tuple[int, int]:
            # Company-specific beats platform-wide; deductee-type-specific
            # beats "applies to all types".
            return (0 if rule.company_id is not None else 1, 0 if rule.deductee_type else 1)

        return sorted(candidates, key=_rank)[0]
