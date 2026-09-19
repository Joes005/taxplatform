"""Financial Year -> Assessment Year mapping (PHASE8 §11), computed from
the actual `FinancialYear.end_date` rather than string-slicing its `name`
— the same "derive from the real date, not the label" instinct
`TDSReturnPeriodService.quarter_date_range()` already applies to quarters.
An Indian assessment year always starts the calendar year a financial year
ends in (FY 2025-26, ending 31 Mar 2026, is assessed in AY 2026-27).
"""

from app.models.financial_year import FinancialYear


def assessment_year_for(financial_year: FinancialYear) -> str:
    start_year = financial_year.end_date.year
    return f"{start_year}-{str(start_year + 1)[-2:]}"
