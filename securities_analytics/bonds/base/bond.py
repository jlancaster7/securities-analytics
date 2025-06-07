import abc
from datetime import datetime

import QuantLib as ql

from ...utils.dates.utils import to_ql_date


class AbstractBond(abc.ABC):
    """
    Abstract Base Class for bonds.
    The intent here is to encapsulate common bond parameters and
    delegate schedule/cashflow generation to specialized classes.
    """

    def __init__(
        self,
        face_value: float,
        annual_coupon_rate: float,
        settlement_date: datetime,
        day_count: str,
        settlement_days: int,
        compounding=ql.Compounded,
        frequency=ql.Semiannual,
        issue_date: datetime | None = None,
    ) -> None:
        self.face_value: float = face_value
        self.annual_coupon_rate: float = annual_coupon_rate
        self.settlement_days: int = settlement_days
        self.day_count: ql.DayCounter = self._map_day_count(day_count)
        self.settlement_date_ql: ql.Date = to_ql_date(settlement_date)
        self.compounding_ql = compounding
        self.frequency_ql = frequency
        # If no explicit issue date, assume it equals the settlement date.
        self.issue_date_ql: ql.Date = (
            to_ql_date(issue_date) if issue_date else self.settlement_date_ql
        )
        # The QuantLib evaluation date should typically be set to the settlement date.
        ql.Settings.instance().evaluationDate = self.settlement_date_ql

    @abc.abstractmethod
    def build_bond(self) -> None:
        """
        Build the bond object (e.g., a QuantLib FixedRateBond).
        Must be overridden by subclasses.
        """

        pass

    def _map_day_count(self, convention: str) -> ql.DayCounter:
        """
        Convert a day-count-convention string to a QuantLib DayCounter.
        """
        c: str = convention.upper()
        if c == "ACT365":
            return ql.Actual365Fixed()
        elif c == "ACT360":
            return ql.Actual360()
        elif c in ["D30360", "30E360"]:
            return ql.Thirty360(ql.Thirty360.BondBasis)
        elif c == "ACTACT":
            return ql.ActualActual(ql.ActualActual.Bond)
        else:
            # Default
            return ql.Actual365Fixed()
