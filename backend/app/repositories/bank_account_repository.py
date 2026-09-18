import uuid

from sqlalchemy import func, or_, select

from app.models.bank_account import BankAccount
from app.repositories.base import CompanyScopedRepository


class BankAccountRepository(CompanyScopedRepository[BankAccount]):
    model = BankAccount
    search_fields = ("bank_name", "account_name", "account_number_masked")

    # Overridden because the shared CompanyScopedRepository.list_for_company
    # orders by `self.model.name`, a column BankAccount doesn't have
    # (it's `account_name` here) — everything else about the base
    # implementation applies unchanged.
    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[BankAccount], int]:
        query = select(BankAccount).where(BankAccount.company_id == company_id)
        if is_active is not None:
            query = query.where(BankAccount.is_active == is_active)
        if search and self.search_fields:
            pattern = f"%{search}%"
            query = query.where(
                or_(*(getattr(BankAccount, field).ilike(pattern) for field in self.search_fields))
            )

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        result = await self.db.execute(
            query.order_by(BankAccount.account_name.asc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
