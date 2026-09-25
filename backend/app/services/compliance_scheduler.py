import asyncio
import logging
import uuid
from typing import Any

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.company import Company
from app.services.compliance_task_service import ComplianceTaskService

logger = logging.getLogger("compliance.scheduler")


async def sweep_all_companies_overdue() -> dict[str, int]:
    """Sweeps overdue compliance tasks for all active companies in a fresh session."""
    results: dict[str, int] = {}
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(Company.id).where(Company.is_active.is_(True))
            res = await session.execute(stmt)
            company_ids = [row[0] for row in res.all()]

            task_service = ComplianceTaskService(session)
            for cid in company_ids:
                try:
                    swept = await task_service.sweep_overdue(cid, current_user=None)
                    if swept > 0:
                        results[str(cid)] = swept
                except Exception as ex:
                    logger.warning("Error sweeping overdue tasks for company %s: %s", cid, ex)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Error during global compliance overdue sweep")
            raise
    return results


async def periodic_compliance_sweep(interval_seconds: int = 3600) -> None:
    """Background coroutine that periodically sweeps overdue compliance tasks across all companies."""
    logger.info("Compliance overdue scheduler started (interval=%ds)", interval_seconds)
    try:
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                logger.info("Running scheduled compliance overdue sweep...")
                swept_dict = await sweep_all_companies_overdue()
                total_swept = sum(swept_dict.values())
                logger.info("Scheduled compliance sweep complete: %d tasks marked overdue across %d companies", total_swept, len(swept_dict))
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Error during scheduled compliance sweep cycle: %s", e)
    except asyncio.CancelledError:
        logger.info("Compliance overdue scheduler shut down gracefully")
