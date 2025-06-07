from datetime import datetime
from typing import Any

import QuantLib as ql

from ...base.bond import AbstractBond
from ..schedulers.scheduler import FixedRateBondScheduleGenerator


class FixedRateQLBond(AbstractBond):
    """
    A concrete bond class for fixed rate bonds.
    Uses a schedule generator to build the bond cashflow schedule.
    Optionally supports a call feature via a second schedule.
    """

    def __init__(
        self,
        face_value: float,
        maturity_date: datetime,
        annual_coupon_rate: float,
        settlement_date: datetime,
        day_count: str,
        settlement_days: int,
        compounding=ql.Compounded,
        frequency=ql.Semiannual,
        calendar=ql.UnitedStates(ql.UnitedStates.GovernmentBond),
        issue_date: datetime | None = None,
        # Optional call feature parameters:
        next_call_date: datetime | None = None,
        call_price: float | None = None,
        business_day_convention=ql.Following,
    ) -> None:
        """
        :param face_value: The notional / par value of the bond.
        :maturity_date: Maturity datetime of the bond.
        :param annual_coupon_rate: Annual coupon (e.g., 0.05 for 5%).
        :param settlement_date: Settlement date as a Python datetime.
        :param day_count: A string for day count (e.g., 'ACT365'), converted to a QL.DayCounter in AbstractBond.
        :param settlement_days: # of business days for settlement.
        :param compounding: QL compounding convention (default: Compounded).
        :param frequency: QL frequency (Semiannual, Annual, etc.).
        :param calendar: QL Calendar
        :param issue_date: Optional. If None, we assume settlement date as the issue date.
        :param next_call_date: the first date in which the bond can be called.
        :param call_price: the price at which the bond can be called.
        :param business_day_convention: e.g., ql.Following, ql.ModifiedFollowing, etc.
        """
        super().__init__(
            face_value,
            annual_coupon_rate,
            settlement_date,
            day_count,
            settlement_days,
            compounding,
            frequency,
            issue_date,
        )
        self.schedule_generator = FixedRateBondScheduleGenerator(
            issue_date=issue_date or settlement_date,
            maturity_date=maturity_date,
            frequency=2,
            calendar=calendar,
            business_day_convention=ql.Following,
        )
        if next_call_date:
            self.call_schedule_generator = FixedRateBondScheduleGenerator(
                issue_date=issue_date or settlement_date,
                maturity_date=next_call_date,
                frequency=2,
                calendar=calendar,
                business_day_convention=ql.Following,
            )
        self.call_price: float | None = call_price
        self.business_day_convention: Any = business_day_convention

        # Build both the full (maturity) bond and optionally the callable bond.
        self.bond_mty = None
        self.bond_call = None
        self.build_bond()

    def build_bond(self) -> None:
        """Build the QuantLib FixedRateBond objects."""
        # Generate schedule for full maturity
        schedule: ql.Schedule = self.schedule_generator.generate()
        self.bond_mty = ql.FixedRateBond(
            self.settlement_days,
            self.face_value,
            schedule,
            [self.annual_coupon_rate],
            self.day_count,
            self.business_day_convention,
            self.face_value,
            self.issue_date_ql,
        )
        # Build callable bond if a call schedule generator is provided
        if self.call_schedule_generator:
            call_schedule: ql.Schedule = self.call_schedule_generator.generate()
            redemption: float = self.call_price if self.call_price is not None else self.face_value
            self.bond_call = ql.FixedRateBond(
                self.settlement_days,
                self.face_value,
                call_schedule,
                [self.annual_coupon_rate],
                self.day_count,
                self.business_day_convention,
                redemption,
                self.issue_date_ql,
            )

    def dirty_price_to_maturity(self, y: float) -> float:
        """
        Price from yield for final maturity bond (includes accrued interest).
        """
        if not self.bond_mty:
            raise ValueError("Bond has not been generated.")
        return self.bond_mty.dirtyPrice(
            y,  # yield
            self.day_count,
            self.compounding_ql,
            self.frequency_ql,
        )

    def dirty_price_to_call(
        self,
        y: float,
    ) -> float:
        """
        Price from yield if we assume call occurs on the next_call_date.
        """
        if self.bond_call is None:
            raise ValueError("No call bond object. Call date/price may not be set.")
        return self.bond_call.dirtyPrice(
            y,  # yield
            self.day_count,
            self.compounding_ql,
            self.frequency_ql,
        )

    def yield_to_maturity(self, market_clean_price: float) -> float:
        """
        Compute the yield-to-maturity (annualized) given a market clean price.
        """
        if not self.bond_mty:
            raise ValueError("Bond has not been generated.")
        return self.bond_mty.bondYield(
            market_clean_price, self.day_count, self.compounding_ql, self.frequency_ql
        )

    def yield_to_call(self, market_clean_price: float) -> float:
        """
        Compute the yield-to-call (annualized) given a market clean price.
        """
        if not self.bond_call:
            raise ValueError("No call schedule provided for this bond.")
        return self.bond_call.bondYield(
            market_clean_price, self.day_count, self.compounding_ql, self.frequency_ql
        )

    def yield_to_worst(self, market_clean_price: float) -> float:
        """
        Return the lower of yield-to-maturity and yield-to-call.
        """
        ytm: float = self.yield_to_maturity(market_clean_price)
        if self.bond_call:
            ytc: float = self.yield_to_call(market_clean_price)
            return min(ytm, ytc)
        return ytm

    def duration(self, y: float, workout_type: str = "maturity") -> float:
        """
        Compute the (modified) duration.
        """
        if workout_type == "maturity":
            return ql.BondFunctions.duration(
                self.bond_mty,
                y,
                self.day_count,
                self.compounding_ql,
                self.frequency_ql,
                ql.Duration.Modified,
            )
        elif workout_type == "call" and not self.bond_call:
            return ql.BondFunctions.duration(
                self.bond_call,
                y,
                self.day_count,
                self.compounding_ql,
                self.frequency_ql,
                ql.Duration.Modified,
            )

        else:
            raise ValueError("No call schedule provided for this bond.")

    def convexity(
        self,
        y: float,
        workout_type: str = "maturity",
        compounding=ql.Compounded,
        frequency=ql.Semiannual,
    ) -> float:
        """
        Compute the convexity.
        """
        if workout_type == "maturity":
            return ql.BondFunctions.convexity(
                self.bond_mty, y, self.day_count, compounding, frequency
            )
        elif workout_type == "call" and not self.bond_call:
            return ql.BondFunctions.convexity(
                self.bond_call, y, self.day_count, compounding, frequency
            )
        else:
            raise ValueError("No call schedule provided for this bond.")
