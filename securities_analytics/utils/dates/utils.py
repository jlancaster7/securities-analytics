from datetime import datetime
from typing import Any

import QuantLib as ql


def to_ql_date(dt: datetime) -> ql.Date:
    """Convert Python datetime to QuantLib Date."""
    return ql.Date(dt.day, dt.month, dt.year)


def ql_to_py_date(ql_dt: ql.Date) -> datetime:
    return datetime(ql_dt.year(), ql_dt.month(), ql_dt.dayOfMonth())


def year_difference_rounded(start_date: datetime, end_date: datetime) -> int:
    days_in_year = 365.25  # accounting for leap years
    delta_days: int = (end_date - start_date).days
    return round(delta_days / days_in_year)


def generate_list_of_ql_dates(
    start_date: datetime,
    end_date: datetime,
    frequency: str = "monthly",
    calendar: ql.Calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond),
    business_day_convention: Any = ql.Following,
    end_of_month: bool = False,
) -> list[ql.Date]:
    """
    Generate a list of QL.Date objects from 'start_date' up to but not including 'end_date'
    at the given 'frequency' (daily, weekly, monthly, etc.).

    :param start_date: Python datetime of the first potential date in the sequence.
    :param end_date: Python datetime of final cutoff date
                     (dates are generated strictly before this date).
    :param frequency: e.g., "daily", "weekly", "monthly", "quarterly", etc.
    :param calendar: QL calendar used for date arithmetic.
    :param business_day_convention: e.g. ql.Following or ql.ModifiedFollowing.
    :param end_of_month: If True, use end-of-month logic for monthly or quarterly stepping.

    :return: A list of QL.Date objects (strictly before 'end_date').
    """
    freq_map = {
        "daily": ql.Period(1, ql.Days),
        "weekly": ql.Period(1, ql.Weeks),
        "monthly": ql.Period(1, ql.Months),
        "quarterly": ql.Period(3, ql.Months),
        "semiannual": ql.Period(6, ql.Months),
        "annual": ql.Period(1, ql.Years),
    }
    if frequency not in freq_map:
        raise ValueError(f"Unsupported frequency: {frequency}")

    period = freq_map[frequency]

    # Convert Python datetimes to QL.Date
    ql_current = ql.Date(start_date.day, start_date.month, start_date.year)
    ql_end = ql.Date(end_date.day, end_date.month, end_date.year)

    # If start is >= end, return empty
    if ql_current >= ql_end:
        return []

    date_list = []

    while ql_current < ql_end:
        # Adjust to business day convention
        ql_adjusted = calendar.adjust(ql_current, business_day_convention)

        # If adjusted is still before 'end_date', we keep it
        if ql_adjusted < ql_end:
            date_list.append(ql_adjusted)

        # Step forward
        if end_of_month and frequency in ("monthly", "quarterly", "semiannual", "annual"):
            ql_current = calendar.advance(ql_current, period, business_day_convention, end_of_month)
        else:
            ql_current = calendar.advance(ql_current, period, business_day_convention)

    return date_list
