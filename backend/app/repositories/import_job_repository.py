import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_job import ImportError, ImportJob, ImportRow


class ImportJobRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, job: ImportJob) -> ImportJob:
        self.db.add(job)
        await self.db.flush()
        return job

    async def get_by_id_for_company(self, job_id: uuid.UUID, company_id: uuid.UUID) -> ImportJob | None:
        result = await self.db.execute(
            select(ImportJob).where(ImportJob.id == job_id, ImportJob.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def list_for_company(
        self, company_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[ImportJob], int]:
        query = select(ImportJob).where(ImportJob.company_id == company_id)
        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(ImportJob.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def add_row(self, row: ImportRow) -> ImportRow:
        self.db.add(row)
        return row

    async def add_error(self, error: ImportError) -> ImportError:
        self.db.add(error)
        return error

    async def list_rows(
        self, job_id: uuid.UUID, *, status: str | None = None, offset: int = 0, limit: int = 20
    ) -> tuple[list[ImportRow], int]:
        query = select(ImportRow).where(ImportRow.import_job_id == job_id)
        if status is not None:
            query = query.where(ImportRow.status == status)
        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(ImportRow.row_number.asc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def list_all_rows(self, job_id: uuid.UUID) -> list[ImportRow]:
        result = await self.db.execute(
            select(ImportRow).where(ImportRow.import_job_id == job_id).order_by(ImportRow.row_number.asc())
        )
        return list(result.scalars().all())

    async def list_errors(
        self, job_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[ImportError], int]:
        query = select(ImportError).where(ImportError.import_job_id == job_id)
        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(ImportError.row_number.asc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
