from datetime import datetime
from typing import Any

import QuantLib as ql

from ....utils.dates.utils import to_ql_date
from ...base.scheduler import BondScheduleGenerator


class FixToFloatScheduleGenerator(BondScheduleGenerator):
    """
    A schedule generator for fix-to-float bonds that creates two separate schedules:
    1. Fixed rate schedule from issue to switch date
    2. Floating rate schedule from switch date to maturity
    """

    def __init__(
        self,
        issue_date: datetime,
        switch_date: datetime,
        maturity_date: datetime,
        fixed_frequency: int,
        floating_frequency: int,
        calendar: ql.Calendar,
        business_day_convention=ql.Following,
        date_generation=ql.DateGeneration.Forward,
        end_of_month: bool = False,
    ) -> None:
        self.issue_date_ql: ql.Date = to_ql_date(issue_date)
        self.switch_date_ql: ql.Date = to_ql_date(switch_date)
        self.maturity_date_ql: ql.Date = to_ql_date(maturity_date)
        self.fixed_frequency: int = fixed_frequency
        self.floating_frequency: int = floating_frequency
        self.calendar: ql.Calendar = calendar
        self.business_day_convention: Any = business_day_convention
        self.date_generation: Any = date_generation
        self.end_of_month: bool = end_of_month
        self.fixed_frequency_ql: Any = self._map_frequency(fixed_frequency)
        self.floating_frequency_ql: Any = self._map_frequency(floating_frequency)

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
        """
        Generate a combined schedule for the entire bond life.
        This is useful for certain QuantLib functions that expect a single schedule.
        """
        # For the combined schedule, we need to merge fixed and floating periods
        # This is complex, so we'll create it by combining dates from both schedules
        fixed_schedule = self.generate_fixed_schedule()
        floating_schedule = self.generate_floating_schedule()
        
        # Get all unique dates from both schedules
        all_dates = []
        for i in range(len(fixed_schedule)):
            date = fixed_schedule[i]
            if date <= self.switch_date_ql:
                all_dates.append(date)
        
        for i in range(len(floating_schedule)):
            date = floating_schedule[i]
            if date > self.switch_date_ql and date not in all_dates:
                all_dates.append(date)
        
        # Sort dates and create a new schedule
        all_dates.sort()
        return ql.Schedule(all_dates, self.calendar, self.business_day_convention)

    def generate_fixed_schedule(self) -> ql.Schedule:
        """Generate schedule for the fixed rate period only."""
        return ql.Schedule(
            self.issue_date_ql,
            self.switch_date_ql,
            ql.Period(self.fixed_frequency_ql),
            self.calendar,
            self.business_day_convention,
            self.business_day_convention,
            self.date_generation,
            self.end_of_month,
        )

    def generate_floating_schedule(self) -> ql.Schedule:
        """Generate schedule for the floating rate period only."""
        return ql.Schedule(
            self.switch_date_ql,
            self.maturity_date_ql,
            ql.Period(self.floating_frequency_ql),
            self.calendar,
            self.business_day_convention,
            self.business_day_convention,
            self.date_generation,
            self.end_of_month,
        )