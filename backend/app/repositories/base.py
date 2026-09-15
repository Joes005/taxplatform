import uuid
from typing import Generic, TypeVar

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class CompanyScopedRepository(Generic[ModelT]):
    """Shared CRUD shape for simple, flat, company-scoped master data
    (Ledger, Customer, Vendor, ProductService): get-by-id, search+paginate,
    create. Every method takes company_id explicitly and filters by it —
    the tenant-isolation guarantee every repository in this codebase makes.
    Entities with real business logic (invoices, journals, imports) get
    their own repository rather than being forced through this shape.
    """

    model: type[ModelT]
    search_fields: tuple[str, ...] = ()

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id_for_company(
        self, entity_id: uuid.UUID, company_id: uuid.UUID
    ) -> ModelT | None:
        result = await self.db.execute(
            select(self.model).where(
                self.model.id == entity_id, self.model.company_id == company_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self,
        company_id: uuid.UUID,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ModelT], int]:
        query = select(self.model).where(self.model.company_id == company_id)

        if is_active is not None:
            query = query.where(self.model.is_active == is_active)
        if search and self.search_fields:
            pattern = f"%{search}%"
            query = query.where(
                or_(*(getattr(self.model, field).ilike(pattern) for field in self.search_fields))
            )

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        result = await self.db.execute(
            query.order_by(self.model.name.asc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
