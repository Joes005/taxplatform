"""Reusable validation guards shared by every transactional accounting
service (sales/purchase invoices, notes, payments, receipts, journals).

Kept separate from any one service because these two rules apply
identically everywhere a transaction date is accepted — duplicating them
per-service is exactly the kind of drift that eventually lets one document
type bypass a rule the others enforce.
"""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError, ValidationAppError
from app.models.accounting_period import AccountingPeriod
from app.models.accounting_enums import PeriodStatus
from app.models.financial_year import FinancialYear
from app.repositories.accounting_period_repository import AccountingPeriodRepository


def assert_date_in_financial_year(financial_year: FinancialYear, on_date: date) -> None:
    """§45 — a transaction's date must fall inside its own financial year."""
    if not financial_year.contains(on_date):
        raise ValidationAppError(
            f"Transaction date {on_date.isoformat()} does not fall within financial year "
            f"'{financial_year.name}' ({financial_year.start_date.isoformat()} to "
            f"{financial_year.end_date.isoformat()})",
            code="INVALID_FINANCIAL_YEAR_DATE",
        )


async def assert_period_open(
    db: AsyncSession, *, company_id: uuid.UUID, on_date: date
) -> AccountingPeriod | None:
    """§46 — if an accounting period exists covering `on_date` and it's
    CLOSED or LOCKED, block the transaction. A date with no period defined
    at all is allowed (periods are an opt-in closing mechanism, not a
    mandatory calendar the user must pre-populate).
    """
    period = await AccountingPeriodRepository(db).get_for_date(company_id, on_date)
    if period is not None and period.status in (PeriodStatus.CLOSED, PeriodStatus.LOCKED):
        raise InvalidStateError(
            f"Accounting period '{period.name}' is {period.status.value} and cannot accept "
            f"new or modified transactions",
            code="PERIOD_NOT_OPEN",
        )
    return period
