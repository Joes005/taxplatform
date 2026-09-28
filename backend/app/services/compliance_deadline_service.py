"""Pure due-date arithmetic over a `ComplianceRule.due_date_rule` document
(PHASE9 §6-7) — no DB access, no statutory deadline of its own baked in.
Every date this module returns is derived entirely from the rule dict and
the period dates the caller supplies, so it can be unit tested directly
against fixtures (PHASE9 §46) rather than through the full obligation
service.

Supported `due_date_rule` shapes:

- `{"type": "DAYS_AFTER_PERIOD_END", "days": 20}`
  → `period_end + 20 days`
- `{"type": "DAY_OF_MONTH_AFTER_PERIOD_END", "month_offset": 1, "day": 20}`
  → the 20th of the month `month_offset` months after `period_end`'s month
- `{"type": "DAYS_AFTER_START", "days": 30}`
  → `period_start + 30 days` (for `ONE_TIME`/`CUSTOM` rules with no
  natural "period end")
"""

from datetime import date, timedelta
from typing import Any

from app.core.exceptions import ValidationAppError


def _add_months(on_date: date, months: int) -> date:
    total = on_date.month - 1 + months
    year = on_date.year + total // 12
    month = total % 12 + 1
    return date(year, month, 1)


def compute_due_date(due_date_rule: dict[str, Any], *, period_start: date, period_end: date) -> date:
    rule_type = due_date_rule.get("type")

    if rule_type == "DAYS_AFTER_PERIOD_END":
        days = int(due_date_rule["days"])
        return period_end + timedelta(days=days)

    if rule_type == "DAY_OF_MONTH_AFTER_PERIOD_END":
        month_offset = int(due_date_rule.get("month_offset", 1))
        day = int(due_date_rule["day"])
        target_month_start = _add_months(period_end, month_offset)
        next_month_start = _add_months(target_month_start, 1)
        last_day_of_target_month = (next_month_start - timedelta(days=1)).day
        return target_month_start.replace(day=min(day, last_day_of_target_month))

    if rule_type == "DAYS_AFTER_START":
        days = int(due_date_rule["days"])
        return period_start + timedelta(days=days)

    if rule_type == "DAYS_AFTER_MONTH_END":
        days = int(due_date_rule.get("days", 7))
        # End of the month of period_end
        next_m = _add_months(period_end.replace(day=1), 1)
        month_end = next_m - timedelta(days=1)
        return month_end + timedelta(days=days)

    if rule_type == "QUARTER_BASED_OFFSET":
        month_offset = int(due_date_rule.get("month_offset", 1))
        day = int(due_date_rule.get("day", 31))
        target_month_start = _add_months(period_end, month_offset)
        next_month_start = _add_months(target_month_start, 1)
        last_day_of_target_month = (next_month_start - timedelta(days=1)).day
        return target_month_start.replace(day=min(day, last_day_of_target_month))

    if rule_type == "FIXED_DATE_ANNUAL":
        month = int(due_date_rule["month"])
        day = int(due_date_rule["day"])
        year_offset = int(due_date_rule.get("year_offset", 0))
        target_year = period_end.year + year_offset
        # clamp day for February if needed
        if month == 2 and day > 28:
            is_leap = (target_year % 4 == 0 and target_year % 100 != 0) or (target_year % 400 == 0)
            day = 29 if is_leap else 28
        return date(target_year, month, day)

    raise ValidationAppError(
        f"Unsupported due_date_rule type: {rule_type!r}", code="INVALID_DUE_DATE_RULE"
    )
