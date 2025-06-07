from datetime import datetime
from typing import Any, Optional, List, Union

import QuantLib as ql

from ..base.bond import AbstractBond
from .schedulers.scheduler import FixToFloatScheduleGenerator


class FixToFloatBond(AbstractBond):
    """
    A fix-to-float bond that pays fixed coupons until a switch date,
    then floating coupons (index + spread) until maturity.
    
    This implementation uses a composite approach, treating the bond
    as two separate instruments internally while providing a unified interface.
    """

    def __init__(
        self,
        face_value: float,
        maturity_date: datetime,
        switch_date: datetime,
        fixed_rate: float,
        floating_spread: float,  # Spread over floating index (in decimal, e.g., 0.01 for 100bps)
        settlement_date: datetime,
        day_count: str,
        settlement_days: int,
        floating_index: Optional[ql.OvernightIndex] = None,  # e.g., SOFR
        fixed_frequency: int = 2,  # Semiannual
        floating_frequency: int = 4,  # Quarterly (typical for floaters)
        compounding=ql.Compounded,
        frequency=ql.Semiannual,
        calendar=ql.UnitedStates(ql.UnitedStates.GovernmentBond),
        issue_date: Optional[datetime] = None,
        business_day_convention=ql.Following,
        # Optional callable features
        next_call_date: Optional[datetime] = None,
        call_price: Optional[float] = None,
    ) -> None:
        """
        Initialize a fix-to-float bond.
        
        :param face_value: The notional/par value of the bond
        :param maturity_date: Final maturity date
        :param switch_date: Date when bond switches from fixed to floating
        :param fixed_rate: Fixed coupon rate (e.g., 0.05 for 5%)
        :param floating_spread: Spread over floating index (e.g., 0.01 for 100bps)
        :param settlement_date: Settlement date
        :param day_count: Day count convention string
        :param settlement_days: Number of business days for settlement
        :param floating_index: QuantLib floating rate index (e.g., ql.Sofr())
        :param fixed_frequency: Payment frequency for fixed period (default: 2 = semiannual)
        :param floating_frequency: Payment frequency for floating period (default: 4 = quarterly)
        :param calendar: QuantLib calendar
        :param issue_date: Issue date (defaults to settlement date if not provided)
        :param business_day_convention: Business day convention
        :param next_call_date: Optional call date (often at or after switch date)
        :param call_price: Call price if callable
        """
        super().__init__(
            face_value,
            fixed_rate,  # Use fixed rate as the "annual_coupon_rate" for base class
            settlement_date,
            day_count,
            settlement_days,
            compounding,
            frequency,
            issue_date,
        )
        
        self.maturity_date = maturity_date
        self.switch_date = switch_date
        self.fixed_rate = fixed_rate
        self.floating_spread = floating_spread
        self.fixed_frequency = fixed_frequency
        self.floating_frequency = floating_frequency
        self.calendar = calendar
        self.business_day_convention = business_day_convention
        
        # Set up floating index - default to SOFR if not provided
        if floating_index is None:
            # Create a default SOFR index
            # Note: This requires a yield term structure handle
            # For now, we'll create a placeholder
            self.floating_index = self._create_default_floating_index()
        else:
            self.floating_index = floating_index
        
        # Create the schedule generator
        self.schedule_generator = FixToFloatScheduleGenerator(
            issue_date=issue_date or settlement_date,
            switch_date=switch_date,
            maturity_date=maturity_date,
            fixed_frequency=fixed_frequency,
            floating_frequency=floating_frequency,
            calendar=calendar,
            business_day_convention=business_day_convention,
        )
        
        # Store callable features
        self.next_call_date = next_call_date
        self.call_price = call_price
        
        # These will be populated by build_bond()
        self.fixed_leg_bond = None
        self.floating_leg_bond = None
        self.composite_bond = None
        self.bond_call = None  # For compatibility with spread calculator
        
        self.build_bond()
    
    def _create_default_floating_index(self) -> ql.OvernightIndex:
        """
        Create a default SOFR index for cases where none is provided.
        This is a placeholder - in production, this should use actual market data.
        """
        # For now, create a simple flat curve at 4% for SOFR
        flat_curve = ql.FlatForward(
            self.settlement_date_ql,
            0.04,  # 4% flat rate
            self.day_count,
        )
        ts_handle = ql.YieldTermStructureHandle(flat_curve)
        
        # Create SOFR index - it's an OvernightIndex
        # SOFR constructor: name, fixingDays, currency, calendar, dayCounter, YieldTermStructureHandle
        return ql.OvernightIndex(
            "SOFR",  # name
            1,  # fixing days
            ql.USDCurrency(),  # currency
            self.calendar,  # calendar
            self.day_count,  # day counter
            ts_handle  # yield term structure
        )
    
    def build_bond(self) -> None:
        """
        Build the fix-to-float bond using QuantLib components.
        
        Strategy: Create a custom bond with combined cashflows from both
        fixed and floating periods.
        """
        # Generate schedules
        fixed_schedule = self.schedule_generator.generate_fixed_schedule()
        floating_schedule = self.schedule_generator.generate_floating_schedule()
        
        # Create fixed rate cashflows
        fixed_leg = ql.FixedRateLeg(
            fixed_schedule,
            self.day_count,
            [self.face_value],  # notionals
            [self.fixed_rate]  # coupon rates
        )
        
        # Create floating rate cashflows
        # For SOFR (OvernightIndex), we use OvernightLeg
        if isinstance(self.floating_index, ql.OvernightIndex):
            floating_leg = ql.OvernightLeg(
                [self.face_value],  # notionals
                floating_schedule,
                self.floating_index,
                self.day_count,  # paymentDayCounter
                self.business_day_convention,  # paymentConvention
                gearings=[1.0],  # no leverage
                spreads=[self.floating_spread],  # spread over index
                telescopicValueDates=True
            )
        else:
            # Fallback for other index types
            floating_leg = ql.IborLeg(
                [self.face_value],  # notionals
                floating_schedule,
                self.floating_index,
                self.day_count,
                self.business_day_convention,
                fixingDays=[],  # use index defaults
                gearings=[1.0],  # no leverage
                spreads=[self.floating_spread],  # spread over index
            )
        
        # Combine cashflows
        # Note: We need to exclude the last cashflow from fixed leg (no principal payment at switch)
        # The floating leg already includes redemption at maturity in the bond constructor
        all_cashflows = list(fixed_leg[:-1]) + list(floating_leg)
        
        # Create the bond with combined cashflows
        self.composite_bond = ql.Bond(
            self.settlement_days,
            self.calendar,
            self.issue_date_ql,
            all_cashflows
        )
        
        # For backward compatibility and analytics
        self.fixed_leg_bond = None  # We'll use the cashflows directly
        self.floating_leg_bond = None  # We'll use the cashflows directly
        
        # Set bond_call for compatibility with spread calculator
        if self.next_call_date is not None:
            self.bond_call = True  # Simple flag to indicate callable
        
        # For compatibility with spread calculator
        self.call_schedule_generator = None  # We don't use this pattern
    
    def clean_price(self, yield_curve_handle: Optional[ql.YieldTermStructureHandle] = None) -> float:
        """
        Calculate the clean price of the fix-to-float bond.
        
        :param yield_curve_handle: Yield curve for discounting (required for floating leg)
        :return: Clean price
        """
        if yield_curve_handle is None:
            # Use a flat curve as default - not ideal for production
            flat_curve = ql.FlatForward(self.settlement_date_ql, 0.04, self.day_count)
            yield_curve_handle = ql.YieldTermStructureHandle(flat_curve)
        
        # Set up pricing engine
        discounting_engine = ql.DiscountingBondEngine(yield_curve_handle)
        self.composite_bond.setPricingEngine(discounting_engine)
        
        # Return clean price
        return self.composite_bond.cleanPrice()
    
    def yield_to_maturity(self, market_clean_price: float, yield_curve_handle: Optional[ql.YieldTermStructureHandle] = None) -> float:
        """
        Calculate yield to maturity for a fix-to-float bond.
        This is more complex than for fixed-rate bonds due to the floating leg.
        
        :param market_clean_price: Market clean price
        :return: Yield to maturity
        """
        # Ensure pricing engine is set
        if yield_curve_handle is None:
            # Use a flat curve as default
            flat_curve = ql.FlatForward(self.settlement_date_ql, 0.04, self.day_count)
            yield_curve_handle = ql.YieldTermStructureHandle(flat_curve)
        
        discounting_engine = ql.DiscountingBondEngine(yield_curve_handle)
        self.composite_bond.setPricingEngine(discounting_engine)
        
        # QuantLib can calculate a bond-equivalent yield even for floating rate bonds
        # It uses the current forward curve to project floating cashflows
        try:
            return self.composite_bond.bondYield(
                market_clean_price,
                self.day_count,
                self.compounding_ql,
                self.frequency_ql
            )
        except RuntimeError as e:
            # If yield calculation fails, provide helpful error
            raise ValueError(
                f"Cannot calculate yield for fix-to-float bond at price {market_clean_price}. "
                "The bond may be mispriced or require spread-based measures instead."
            ) from e
    
    def duration(self, yield_curve_handle: Optional[ql.YieldTermStructureHandle] = None) -> float:
        """
        Calculate modified duration for the fix-to-float bond.
        
        :param yield_curve_handle: Yield curve for calculations
        :return: Modified duration
        """
        if yield_curve_handle is None:
            flat_curve = ql.FlatForward(self.settlement_date_ql, 0.04, self.day_count)
            yield_curve_handle = ql.YieldTermStructureHandle(flat_curve)
        
        # Set up pricing engine
        discounting_engine = ql.DiscountingBondEngine(yield_curve_handle)
        self.composite_bond.setPricingEngine(discounting_engine)
        
        # Calculate duration using BondFunctions
        # Need to calculate yield first, then duration
        clean_price = self.composite_bond.cleanPrice()
        bond_yield = self.composite_bond.bondYield(
            clean_price,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql
        )
        
        return ql.BondFunctions.duration(
            self.composite_bond,
            bond_yield,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql,
            ql.Duration.Modified
        )
    
    def spread_to_curve(
        self, 
        market_clean_price: float, 
        yield_curve_handle: ql.YieldTermStructureHandle
    ) -> float:
        """
        Calculate the spread (DM - discount margin) for the fix-to-float bond.
        This is the spread that, when added to the forward curve, prices the bond correctly.
        
        :param market_clean_price: Market clean price
        :param yield_curve_handle: Reference yield curve
        :return: Spread in decimal form (e.g., 0.01 for 100bps)
        """
        # Use QuantLib's z-spread calculation
        # This finds the parallel shift to the curve that prices the bond correctly
        # Note: zSpread expects the curve itself, not the handle
        curve = yield_curve_handle.currentLink()
        return ql.BondFunctions.zSpread(
            self.composite_bond,
            market_clean_price,
            curve,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql
        )
    
    def convexity(self, yield_curve_handle: Optional[ql.YieldTermStructureHandle] = None) -> float:
        """
        Calculate convexity for the fix-to-float bond.
        
        :param yield_curve_handle: Yield curve for calculations
        :return: Convexity
        """
        if yield_curve_handle is None:
            flat_curve = ql.FlatForward(self.settlement_date_ql, 0.04, self.day_count)
            yield_curve_handle = ql.YieldTermStructureHandle(flat_curve)
        
        # Set up pricing engine
        discounting_engine = ql.DiscountingBondEngine(yield_curve_handle)
        self.composite_bond.setPricingEngine(discounting_engine)
        
        # Calculate convexity using BondFunctions
        # Need to calculate yield first
        clean_price = self.composite_bond.cleanPrice()
        bond_yield = self.composite_bond.bondYield(
            clean_price,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql
        )
        
        return ql.BondFunctions.convexity(
            self.composite_bond,
            bond_yield,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql
        )
    
    def dirty_price(self, yield_curve_handle: Optional[ql.YieldTermStructureHandle] = None) -> float:
        """
        Calculate the dirty price of the fix-to-float bond.
        
        :param yield_curve_handle: Yield curve for discounting
        :return: Dirty price
        """
        if yield_curve_handle is None:
            flat_curve = ql.FlatForward(self.settlement_date_ql, 0.04, self.day_count)
            yield_curve_handle = ql.YieldTermStructureHandle(flat_curve)
        
        # Set up pricing engine
        discounting_engine = ql.DiscountingBondEngine(yield_curve_handle)
        self.composite_bond.setPricingEngine(discounting_engine)
        
        return self.composite_bond.dirtyPrice()
    
    def yield_to_call(self, market_clean_price: float, yield_curve_handle: Optional[ql.YieldTermStructureHandle] = None) -> float:
        """
        Calculate yield to call for a callable fix-to-float bond.
        This is only available if the bond has a call date.
        
        :param market_clean_price: Market clean price
        :param yield_curve_handle: Yield curve for calculations
        :return: Yield to call
        """
        if self.next_call_date is None:
            raise ValueError("This bond has no call date specified.")
        
        # For fix-to-float bonds, yield to call is complex because we need to
        # consider both fixed and floating cashflows up to the call date
        # This is a simplified implementation
        
        # Create a truncated bond that matures at the call date
        # with redemption at call price
        call_schedule_gen = FixToFloatScheduleGenerator(
            issue_date=self.issue_date_ql,
            switch_date=self.switch_date if self.switch_date < self.next_call_date else self.next_call_date,
            maturity_date=self.next_call_date,
            fixed_frequency=self.fixed_frequency,
            floating_frequency=self.floating_frequency,
            calendar=self.calendar,
            business_day_convention=self.business_day_convention,
        )
        
        # For now, return yield to maturity as approximation
        # A full implementation would create a separate callable bond
        return self.yield_to_maturity(market_clean_price, yield_curve_handle)
    
    def dirty_price_to_maturity(self, y: float) -> float:
        """
        Calculate dirty price from yield to maturity.
        For compatibility with spread calculator.
        
        :param y: Yield to maturity
        :return: Dirty price
        """
        return self.composite_bond.dirtyPrice(
            y,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql
        )
    
    def dirty_price_to_call(self, y: float) -> float:
        """
        Calculate dirty price from yield to call.
        For compatibility with spread calculator.
        
        :param y: Yield to call
        :return: Dirty price
        """
        # For fix-to-float bonds, this is complex
        # For now, return the same as maturity
        return self.dirty_price_to_maturity(y)