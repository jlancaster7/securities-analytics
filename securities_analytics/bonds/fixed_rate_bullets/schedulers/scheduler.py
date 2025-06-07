from datetime import datetime
from typing import Any

import QuantLib as ql

from ....utils.dates.utils import to_ql_date
from ...base.scheduler import BondScheduleGenerator


class FixedRateBondScheduleGenerator(BondScheduleGenerator):
    """
    A concrete schedule generator for fixed rate bonds.
    """

    def __init__(
        self,
        issue_date: datetime,
        maturity_date: datetime,
        frequency: int,
        calendar: ql.Calendar,
        business_day_convention=ql.Following,
        date_generation=ql.DateGeneration.Forward,
        end_of_month: bool = False,
    ) -> None:
        self.issue_date_ql: ql.Date = to_ql_date(issue_date)
        self.maturity_date_ql: ql.Date = to_ql_date(maturity_date)
        self.frequency: int = frequency
        self.calendar: ql.Calendar = calendar
        self.business_day_convention: Any = business_day_convention
        self.date_generation: Any = date_generation
        self.end_of_month: bool = end_of_month
        self.frequency_ql: Any = self._map_frequency(frequency)

    def _map_frequency(self, freq: int):
        """Map integer frequency to QuantLib Frequency enum."""
        mapping: dict[int, Any] = {
            1: ql.Annual,
            2: ql.Semiannual,
            4: ql.Quarterly,
            12: ql.Monthly,
        }
        return mapping.get(freq, ql.Annual)

    def generate(self) -> ql.Schedule:
        """Generate and return a QuantLib schedule."""
        return ql.Schedule(
            self.issue_date_ql,
            self.maturity_date_ql,
            ql.Period(self.frequency_ql),
            self.calendar,
            self.business_day_convention,
            self.business_day_convention,
            self.date_generation,
            self.end_of_month,
        )
