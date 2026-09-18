from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tds_return_period import TDSReturnPeriod
from app.schemas.tds_reports import TDSReturnPreparationSummary
from app.services.tds_report_service import TDSReportService


class TDSReturnService:
    """Assembles one quarter's TDS return *preparation* data — never
    submitted anywhere, only collected and handed to
    `TDSReturnSnapshotService` to freeze as a version (PHASE5 section 26).
    """

    def __init__(self, db: AsyncSession) -> None:
        self.reports = TDSReportService(db)

    async def generate_summary(self, period: TDSReturnPeriod) -> TDSReturnPreparationSummary:
        quarterly = await self.reports.quarterly_summary(
            period.company_id, period.period_start, period.period_end
        )
        by_section = await self.reports.section_summary(
            period.company_id, period.period_start, period.period_end
        )
        by_deductee = await self.reports.deductee_summary(
            period.company_id, period.period_start, period.period_end
        )
        challans = await self.reports.challan_summary(period.company_id, period.financial_year_id)

        return TDSReturnPreparationSummary(
            quarterly=quarterly, by_section=by_section, by_deductee=by_deductee, challans=challans
        )
