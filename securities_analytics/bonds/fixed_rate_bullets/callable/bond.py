from datetime import datetime
from typing import Any

import QuantLib as ql

from ....utils.dates.utils import generate_list_of_ql_dates, ql_to_py_date
from ...base.bond import AbstractBond
from ..schedulers.scheduler import FixedRateBondScheduleGenerator


class CallableFixedRateQLBond(AbstractBond):
    """
    A bond class that uses QuantLib.CallableFixedRateBond to represent
    a bond with embedded call options. Unlike a simple 'call schedule generator',
    here we build a proper CallabilitySchedule and rely on QuantLib's native
    callable bond framework.

    NOTE: By default, we attach a plain DiscountingBondEngine, which does
    NOT correctly value the call option. For a proper option valuation,
    attach a TreeCallableFixedRateBondEngine or an equivalent model-based engine.
    """

    def __init__(
        self,
        face_value: float,
        maturity_date: datetime,
        annual_coupon_rate: float,
        settlement_date: datetime,
        day_count: str,
        settlement_days: int,
        next_call_date: datetime,
        call_price: float,
        ts_handle: ql.YieldTermStructureHandle | None = None,
        hw_a: float = 0.03,
        hw_s: float = 0.011,
        hw_grid_points: int = 100,
        compounding=ql.Compounded,
        frequency=2,
        calendar=ql.UnitedStates(ql.UnitedStates.GovernmentBond),
        issue_date: datetime | None = None,
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
        :param call_dates_and_prices: A list of (call_date, call_price) pairs.
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
            frequency=2,  # Semiannual coupons
            calendar=calendar,
            business_day_convention=ql.Following,
        )
        self.maturity_date: ql.Date = self.schedule_generator.generate()[-1]

        self.next_call_date: datetime | None = next_call_date
        self.call_price: float | None = call_price

        self.call_dates: list[ql.Date] = generate_list_of_ql_dates(
            start_date=self.next_call_date,
            end_date=ql_to_py_date(self.maturity_date),
            frequency="monthly",
            calendar=ql.UnitedStates(ql.UnitedStates.GovernmentBond),
            business_day_convention=ql.Following,
            end_of_month=False,
        )
        self.call_dates_and_prices: list[tuple[ql.Date, float]] = [
            (d, self.call_price) for d in self.call_dates
        ]

        self.business_day_convention: Any = business_day_convention

        if ts_handle:
            self.ts_handle: ql.YieldTermStructureHandle = ts_handle
        else:
            flat_curve = ql.FlatForward(
                self.settlement_date_ql,
                0.03,  # say 3% just as an example
                self.day_count,
            )
            self.ts_handle = ql.YieldTermStructureHandle(flat_curve)

        self.hw_a: float = hw_a
        self.hw_s: float = hw_s
        self.hw_grid_points: int = hw_grid_points

        # We will build the QL.CallableFixedRateBond in build_bond()
        self.engine = None
        self.callable_bond = None

        self.build_bond()

    def build_bond(self) -> None:
        """
        Builds the QuantLib.CallableFixedRateBond object and
        attaches a simple discounting engine (ignoring optionality).
        """
        # 1) Generate the schedule for final maturity
        schedule: ql.Schedule = self.schedule_generator.generate()

        # 2) Construct a CallabilitySchedule from call_dates_and_prices
        callability_schedule = ql.CallabilitySchedule()
        for cd, px in self.call_dates_and_prices:
            ql_call_date: ql.Date = cd
            # Create a call object with price = px

            call_price_handle = ql.BondPrice(px, ql.BondPrice.Clean)
            # The second arg is the type: Call or Put
            this_call = ql.Callability(call_price_handle, ql.Callability.Call, ql_call_date)
            callability_schedule.append(this_call)

        # 3) Build the QuantLib.CallableFixedRateBond
        #    Pay attention to callability schedule arg in the constructor.
        #    Typically, we do: settlementDays, couponSchedule, dayCounter, etc.
        self.callable_bond = ql.CallableFixedRateBond(
            self.settlement_days,  # settlement days
            self.face_value,  # faceAmount
            schedule,  # coupon schedule
            [self.annual_coupon_rate],  # coupon rates
            self.day_count,  # dayCounter
            self.business_day_convention,
            self.face_value,  # redemption
            self.issue_date_ql,  # issue date
            callability_schedule,  # call schedule
            # By default, QuantLib assumes European-style calls if multiple call dates
            # The constructor can handle that automatically if we specify more arguments.
        )

        model = ql.HullWhite(self.ts_handle, self.hw_a, self.hw_s)
        engine = ql.TreeCallableFixedRateBondEngine(model, self.hw_grid_points)

        self.callable_bond.setPricingEngine(engine)

    # -------------------------------------------------------------------------
    # BASIC PRICE / YIELD CALCULATIONS (Ignoring optionality in the engine)
    # -------------------------------------------------------------------------
    def clean_price(self) -> float:
        """
        Return the bond's clean price from the current engine.
        With a discounting engine, this is the price ignoring the optionality.
        """
        if not self.callable_bond:
            raise ValueError(
                "The Bond has not yet been generated. An error must have occurred in the init."
            )

        return self.callable_bond.cleanPrice()

    def dirty_price(self) -> float:
        """
        Return the bond's dirty price from the current engine.
        """
        if not self.callable_bond:
            raise ValueError(
                "The Bond has not yet been generated. An error must have occurred in the init."
            )
        return self.callable_bond.dirtyPrice()

    def npv(self) -> float:
        """
        Return the bond's full NPV from the current engine.
        """
        if not self.callable_bond:
            raise ValueError(
                "The Bond has not yet been generated. An error must have occurred in the init."
            )
        return self.callable_bond.NPV()

    def yield_to_maturity(self) -> float:
        """
        In theory, you can compute a 'yield' from the clean price ignoring the call.
        This is not a proper 'yield to call' or an option-adjusted measure.
        It's just the yield for the full final maturity ignoring optionality.
        """
        if not self.callable_bond:
            raise ValueError(
                "The Bond has not yet been generated. An error must have occurred in the init."
            )
        cprice: float = self.clean_price()
        # bondYield can fail if the bond is too close to par or
        # if there's some weird daycount issue. Typically it works fine though.
        return self.callable_bond.bondYield(
            cprice, self.day_count, self.compounding_ql, self.frequency_ql
        )

    def calculate_OAS(self, clean_market_price: float):
        if not self.callable_bond:
            raise ValueError(
                "The Bond has not yet been generated. An error must have occurred in the init."
            )
        cprice = self.callable_bond.OAS(
            clean_market_price,
            self.ts_handle,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql,
            self.settlement_date_ql,
        )

        return cprice

    def price_with_OAS(self, oas: float) -> float:
        """
        Given an OAS (option-adjusted spread), return the bond's clean price.
        This uses QuantLib's built-in callable bond functionality.
        """
        if not self.callable_bond:
            raise ValueError("The Bond has not yet been generated.")
        # Use the 'cleanPrice(spread, ...)' overload:
        return self.callable_bond.cleanPrice(
            oas,
            self.ts_handle,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql,
            self.settlement_date_ql,  # optional if you have a QL Date for settlement
        )

    # -------------------------------------------------------------------------
    # FUTURE HOOKS FOR MODEL-BASED ENGINE
    # -------------------------------------------------------------------------
    def set_pricing_engine(self, engine: ql.PricingEngine) -> None:
        """
        Let the user attach a more appropriate engine, e.g.
        TreeCallableFixedRateBondEngine for actual embedded option valuation.
        """
        if not self.callable_bond:
            raise ValueError(
                "The Bond has not yet been generated. An error must have occurred in the init."
            )
        self.callable_bond.setPricingEngine(engine)

    def duration(
        self,
        oas: float,
    ) -> float:
        """
        :param oas: Option Adjusted Spread
        Effective Duartion accounting for the bonds option.
        """
        if not self.callable_bond:
            raise ValueError(
                "The Bond has not yet been generated. An error must have occurred in the init."
            )
        return self.callable_bond.effectiveDuration(
            oas,
            self.ts_handle,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql,
        )

    def convexity(self, oas: float) -> float:
        """
        :param oas: Option Adjusted Spread
        Effective Convexity accounting for the bonds option.
        """
        if not self.callable_bond:
            raise ValueError(
                "The Bond has not yet been generated. An error must have occurred in the init."
            )
        return self.callable_bond.effectiveConvexity(
            oas,
            self.ts_handle,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql,
        )
