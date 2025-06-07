from re import Match
from typing import Any

import QuantLib as ql


def tenor_to_ql_period(tenor_str: str) -> ql.Period:
    """
    Converts a tenor string like 'ON', '1W', '3M', '3Mo', '5Y', or '5Yr'
    into a QuantLib Period object.
    """
    tenor_str = tenor_str.strip().upper()

    if tenor_str == "ON":
        return ql.Period(1, ql.Days)

    # Normalize unit aliases
    unit_aliases: dict[str, str] = {
        "D": "D",
        "W": "W",
        "M": "MO",
        "MO": "MO",
        "Y": "YR",
        "YR": "YR",
    }

    unit_map: dict[str, Any] = {
        "D": ql.Days,
        "W": ql.Weeks,
        "MO": ql.Months,
        "YR": ql.Years,
    }

    import re

    match: Match[str] | None = re.match(r"(\d+)([A-Z]+)", tenor_str)
    if not match:
        raise ValueError(f"Unrecognized tenor format: {tenor_str}")

    n, unit = match.groups()
    normalized_unit: str | None = unit_aliases.get(unit)
    if normalized_unit is None or normalized_unit not in unit_map:
        raise ValueError(f"Unrecognized unit in tenor: {unit}")

    return ql.Period(int(n), unit_map[normalized_unit])
