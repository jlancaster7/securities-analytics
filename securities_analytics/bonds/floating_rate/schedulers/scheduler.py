from datetime import datetime
from typing import Optional

import QuantLib as ql

from ...base.scheduler import BondScheduleGenerator


class FloatingRateBondScheduleGenerator(BondScheduleGenerator):
    """
    Schedule generator for floating rate bonds.
    Creates a single schedule for the entire life of the bond.
    """

    def __init__(
        self,
        issue_date: datetime,
        maturity_date: datetime,
        frequency: int = 4,  # Quarterly payments typical for floaters
        calendar: ql.Calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond),
        business_day_convention: int = ql.Following,
        end_of_month: bool = False,
        date_generation_rule: int = ql.DateGeneration.Backward,
        first_coupon_date: Optional[datetime] = None,
        next_to_last_coupon_date: Optional[datetime] = None,
    ):
        """
        Initialize the floating rate bond schedule generator.
        
        :param issue_date: Bond issue date
        :param maturity_date: Bond maturity date
        :param frequency: Payment frequency (default quarterly)
        :param calendar: QuantLib calendar
        :param business_day_convention: Business day adjustment
        :param end_of_month: Whether to use end of month convention
        :param date_generation_rule: How to generate dates
        :param first_coupon_date: Optional first coupon date
        :param next_to_last_coupon_date: Optional penultimate coupon date
        """
        super().__init__()
        
        # Store parameters
        self.issue_date = issue_date
        self.maturity_date = maturity_date
        self.frequency = frequency
        self.calendar = calendar
        self.business_day_convention = business_day_convention
        self.end_of_month = end_of_month
        self.date_generation_rule = date_generation_rule
        self.first_coupon_date = first_coupon_date
        self.next_to_last_coupon_date = next_to_last_coupon_date
        
        # Convert dates to QuantLib dates
        self.issue_date_ql = ql.Date(issue_date.day, issue_date.month, issue_date.year)
        self.maturity_date_ql = ql.Date(maturity_date.day, maturity_date.month, maturity_date.year)
        
        # Map frequency to tenor
        self.tenor = self._map_frequency_to_tenor(frequency)
    
    def _map_frequency_to_tenor(self, frequency: int) -> ql.Period:
        """Map payment frequency to QuantLib Period."""
        if frequency == 1:
            return ql.Period(1, ql.Years)
        elif frequency == 2:
            return ql.Period(6, ql.Months)
        elif frequency == 4:
            return ql.Period(3, ql.Months)
        elif frequency == 12:
            return ql.Period(1, ql.Months)
        else:
            # Default to quarterly
            return ql.Period(3, ql.Months)

    def generate(self) -> ql.Schedule:
        """
        Generate the payment schedule for the floating rate bond.
        
        :return: QuantLib Schedule object
        """
        # Convert Python dates to QuantLib dates
        first_date = (
            ql.Date(
                self.first_coupon_date.day,
                self.first_coupon_date.month,
                self.first_coupon_date.year,
            )
            if self.first_coupon_date
            else ql.Date()
        )
        
        penultimate_date = (
            ql.Date(
                self.next_to_last_coupon_date.day,
                self.next_to_last_coupon_date.month,
                self.next_to_last_coupon_date.year,
            )
            if self.next_to_last_coupon_date
            else ql.Date()
        )

        # Create the schedule
        schedule = ql.Schedule(
            self.issue_date_ql,
            self.maturity_date_ql,
            self.tenor,
            self.calendar,
            self.business_day_convention,
            self.business_day_convention,  # termination date convention
            self.date_generation_rule,
            self.end_of_month,
            first_date,
            penultimate_date,
        )
        
        return schedule