import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.membership import CompanyMembership, MembershipStatus


class MembershipRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, membership_id: uuid.UUID) -> CompanyMembership | None:
        return await self.db.get(CompanyMembership, membership_id)

    async def get_active_membership(
        self, *, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> CompanyMembership | None:
        """The core tenant-isolation primitive: is this user an active member
        of this company? Every company-scoped operation must go through here
        rather than trusting a company_id supplied by the client.
        """
        result = await self.db.execute(
            select(CompanyMembership)
            .options(joinedload(CompanyMembership.role), joinedload(CompanyMembership.company))
            .where(
                CompanyMembership.user_id == user_id,
                CompanyMembership.company_id == company_id,
                CompanyMembership.status == MembershipStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[CompanyMembership]:
        result = await self.db.execute(
            select(CompanyMembership)
            .options(joinedload(CompanyMembership.company), joinedload(CompanyMembership.role))
            .where(
                CompanyMembership.user_id == user_id,
                CompanyMembership.status == MembershipStatus.ACTIVE,
            )
        )
        return list(result.unique().scalars().all())

    async def list_for_company(
        self, company_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[CompanyMembership], int]:
        base_query = select(CompanyMembership).where(CompanyMembership.company_id == company_id)

        count_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            base_query.options(joinedload(CompanyMembership.user), joinedload(CompanyMembership.role))
            .order_by(CompanyMembership.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.unique().scalars().all())
        return items, total

    async def count_active_admins(self, company_id: uuid.UUID, admin_role_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(CompanyMembership)
            .where(
                CompanyMembership.company_id == company_id,
                CompanyMembership.role_id == admin_role_id,
                CompanyMembership.status == MembershipStatus.ACTIVE,
            )
        )
        return result.scalar_one()

    async def get_for_user_in_company(
        self, *, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> CompanyMembership | None:
        result = await self.db.execute(
            select(CompanyMembership)
            .options(joinedload(CompanyMembership.role), joinedload(CompanyMembership.user))
            .where(
                CompanyMembership.user_id == user_id,
                CompanyMembership.company_id == company_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, membership: CompanyMembership) -> CompanyMembership:
        self.db.add(membership)
        await self.db.flush()
        return membership
