from datetime import datetime
from typing import Optional, Union, List

import QuantLib as ql

from ..base.bond import AbstractBond
from .schedulers.scheduler import FloatingRateBondScheduleGenerator
from securities_analytics.curves.sofr import SOFRCurve


class FloatingRateBond(AbstractBond):
    """
    A floating rate bond that pays coupons based on a reference index plus a spread.
    
    This implementation supports various floating rate indices including LIBOR, SOFR,
    and other overnight indices.
    """

    def __init__(
        self,
        face_value: float,
        maturity_date: datetime,
        floating_index: Union[ql.IborIndex, ql.OvernightIndex],
        spread: float,  # Spread over index (in decimal, e.g., 0.01 for 100bps)
        settlement_date: datetime,
        day_count: str,
        settlement_days: int,
        frequency: int = 4,  # Quarterly payments typical for floaters
        compounding=ql.Compounded,
        frequency_ql=ql.Quarterly,
        calendar=ql.UnitedStates(ql.UnitedStates.GovernmentBond),
        issue_date: Optional[datetime] = None,
        business_day_convention=ql.Following,
        fixing_days: int = 2,
        gearings: Optional[List[float]] = None,  # Multipliers for the index
        caps: Optional[List[float]] = None,  # Cap rates
        floors: Optional[List[float]] = None,  # Floor rates
        in_arrears: bool = True,  # Whether payments are in arrears
        # Optional callable features
        next_call_date: Optional[datetime] = None,
        call_price: Optional[float] = None,
        # Optional market curve for forward projections
        sofr_curve: Optional[SOFRCurve] = None,
    ) -> None:
        """
        Initialize a floating rate bond.
        
        :param face_value: The notional/par value of the bond
        :param maturity_date: Final maturity date
        :param floating_index: The reference index (e.g., SOFR, LIBOR)
        :param spread: Spread over the index (e.g., 0.01 for 100bps)
        :param settlement_date: Settlement date
        :param day_count: Day count convention string
        :param settlement_days: Number of settlement days
        :param frequency: Payment frequency (default quarterly)
        :param compounding: Compounding convention
        :param frequency_ql: QuantLib frequency
        :param calendar: Business calendar
        :param issue_date: Issue date (defaults to settlement date)
        :param business_day_convention: Business day adjustment
        :param fixing_days: Days before payment for fixing
        :param gearings: Optional multipliers for the index rate
        :param caps: Optional cap rates
        :param floors: Optional floor rates
        :param in_arrears: Whether payments are in arrears
        :param next_call_date: Optional call date
        :param call_price: Optional call price
        :param sofr_curve: Optional SOFR curve for forward rate projections
        """
        # Initialize parent class (use 0.0 for coupon rate as it's floating)
        super().__init__(
            face_value=face_value,
            annual_coupon_rate=0.0,  # Not used for floating bonds
            settlement_date=settlement_date,
            day_count=day_count,
            settlement_days=settlement_days,
            compounding=compounding,
            frequency=frequency_ql,
            issue_date=issue_date,
        )
        
        self.maturity_date = maturity_date
        self.floating_index = floating_index
        self.spread = spread
        self.frequency = frequency
        self.calendar = calendar
        self.business_day_convention = business_day_convention
        self.fixing_days = fixing_days
        self.gearings = gearings
        self.caps = caps
        self.floors = floors
        self.in_arrears = in_arrears
        
        # Callable features
        self.next_call_date = next_call_date
        self.call_price = call_price
        
        # Market curve for forward projections
        self.sofr_curve = sofr_curve
        
        # Build the bond
        self.build_bond()
        
        # Set up pricer for floating coupons
        self._setup_pricer()
        
        # Link market curve if provided
        if self.sofr_curve:
            self._link_market_curve()
    
    def build_bond(self) -> None:
        """
        Build the QuantLib FloatingRateBond object.
        """
        # Create the schedule
        scheduler = FloatingRateBondScheduleGenerator(
            issue_date=self.issue_date_ql.to_date() if hasattr(self.issue_date_ql, 'to_date') else datetime(
                self.issue_date_ql.year(), 
                self.issue_date_ql.month(), 
                self.issue_date_ql.dayOfMonth()
            ),
            maturity_date=self.maturity_date,
            frequency=self.frequency,
            calendar=self.calendar,
            business_day_convention=self.business_day_convention,
        )
        
        schedule = scheduler.generate()
        
        # For traditional IBOR indices, use the native FloatingRateBond
        if isinstance(self.floating_index, ql.IborIndex) and not isinstance(self.floating_index, ql.OvernightIndex):
            self.bond = ql.FloatingRateBond(
                self.settlement_days,  # settlementDays
                self.face_value,       # faceAmount
                schedule,              # schedule
                self.floating_index,   # index
                self.day_count,        # paymentDayCounter
                self.business_day_convention,  # paymentConvention
                self.fixing_days,      # fixingDays
                self.gearings or [1.0],  # gearings
                [self.spread],         # spreads
                self.caps or [],       # caps
                self.floors or [],     # floors
                self.in_arrears,       # inArrears
                100.0,                 # redemption
                self.issue_date_ql,    # issueDate
            )
        else:
            # For overnight indices, we need to use the leg-based approach
            if isinstance(self.floating_index, ql.OvernightIndex):
                # Use OvernightLeg for overnight indices like SOFR
                floating_leg = ql.OvernightLeg(
                    [self.face_value],  # nominals
                    schedule,           # schedule
                    self.floating_index,  # index
                    self.day_count,     # paymentDayCounter
                    self.business_day_convention,  # paymentConvention
                    self.gearings or [1.0],  # gearings
                    [self.spread],      # spreads
                    True,               # telescopicValueDates
                )
            else:
                # Fallback to IborLeg for other cases
                floating_leg = ql.IborLeg(
                    nominals=[self.face_value],
                    schedule=schedule,
                    index=self.floating_index,
                    paymentDayCounter=self.day_count,
                    paymentConvention=self.business_day_convention,
                    fixingDays=[self.fixing_days],
                    gearings=self.gearings or [1.0],
                    spreads=[self.spread],
                    caps=self.caps or [],
                    floors=self.floors or [],
                    isInArrears=self.in_arrears,
                )
            
            # Add redemption at maturity
            redemption_leg = [ql.Redemption(self.face_value, schedule[-1])]
            
            # Combine legs
            all_cashflows = list(floating_leg) + redemption_leg
            
            # Create the bond
            self.bond = ql.Bond(
                self.settlement_days,
                self.calendar,
                self.issue_date_ql,
                all_cashflows,
            )
    
    def _setup_pricer(self) -> None:
        """
        Set up pricer for floating rate coupons.
        """
        if isinstance(self.floating_index, ql.IborIndex) and not isinstance(self.floating_index, ql.OvernightIndex):
            # Create a simple pricer for IBOR coupons (not needed for overnight indices)
            volatility = 0.0  # Zero volatility for simple pricing
            vol_structure = ql.ConstantOptionletVolatility(
                self.settlement_days,
                self.calendar,
                self.business_day_convention,
                volatility,
                self.day_count
            )
            pricer = ql.BlackIborCouponPricer(ql.OptionletVolatilityStructureHandle(vol_structure))
            
            # Set the pricer for all floating coupons in the bond
            ql.setCouponPricer(self.bond.cashflows(), pricer)
    
    def _link_market_curve(self) -> None:
        """
        Link market curve to the floating index for forward rate projections.
        """
        if self.sofr_curve and isinstance(self.floating_index, ql.OvernightIndex):
            # We need to rebuild the bond with the curve-linked index
            # Create a new SOFR index linked to the market curve
            self.floating_index = self.sofr_curve.create_sofr_index()
            # Rebuild the bond with the new index
            self.build_bond()
    
    def clean_price(self, yield_curve_handle: Optional[ql.YieldTermStructureHandle] = None) -> float:
        """
        Calculate the clean price of the floating rate bond.
        
        :param yield_curve_handle: Optional yield curve for discounting
        :return: Clean price
        """
        if yield_curve_handle:
            engine = ql.DiscountingBondEngine(yield_curve_handle)
            self.bond.setPricingEngine(engine)
        elif self.sofr_curve:
            # Use market curve if available
            curve_handle = ql.YieldTermStructureHandle(self.sofr_curve.ql_curve)
            engine = ql.DiscountingBondEngine(curve_handle)
            self.bond.setPricingEngine(engine)
        else:
            # If no curve provided, create a default one
            flat_curve = ql.FlatForward(
                self.settlement_date_ql,
                0.05,  # Default 5% rate
                self.day_count
            )
            engine = ql.DiscountingBondEngine(ql.YieldTermStructureHandle(flat_curve))
            self.bond.setPricingEngine(engine)
        
        return self.bond.cleanPrice()
    
    def dirty_price(self, yield_curve_handle: Optional[ql.YieldTermStructureHandle] = None) -> float:
        """
        Calculate the dirty price of the floating rate bond.
        
        :param yield_curve_handle: Optional yield curve for discounting
        :return: Dirty price
        """
        if yield_curve_handle:
            engine = ql.DiscountingBondEngine(yield_curve_handle)
            self.bond.setPricingEngine(engine)
        elif self.sofr_curve:
            # Use market curve if available
            curve_handle = ql.YieldTermStructureHandle(self.sofr_curve.ql_curve)
            engine = ql.DiscountingBondEngine(curve_handle)
            self.bond.setPricingEngine(engine)
        else:
            # If no curve provided, create a default one
            flat_curve = ql.FlatForward(
                self.settlement_date_ql,
                0.05,  # Default 5% rate
                self.day_count
            )
            engine = ql.DiscountingBondEngine(ql.YieldTermStructureHandle(flat_curve))
            self.bond.setPricingEngine(engine)
        
        return self.bond.dirtyPrice()
    
    def yield_to_maturity(self, market_price: float) -> float:
        """
        Calculate yield to maturity for the floating rate bond.
        Note: This uses the current forward curve for projecting future cashflows.
        
        :param market_price: Current market price
        :return: Yield to maturity
        """
        return self.bond.bondYield(
            market_price,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql,
        )
    
    def duration(self, yield_curve_handle: ql.YieldTermStructureHandle) -> float:
        """
        Calculate modified duration.
        
        :param yield_curve_handle: Yield curve for discounting
        :return: Modified duration
        """
        engine = ql.DiscountingBondEngine(yield_curve_handle)
        self.bond.setPricingEngine(engine)
        
        clean_price = self.bond.cleanPrice()
        ytm = self.bond.bondYield(
            clean_price,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql,
        )
        
        return ql.BondFunctions.duration(
            self.bond,
            ytm,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql,
            ql.Duration.Modified,
        )
    
    def convexity(self, yield_curve_handle: ql.YieldTermStructureHandle) -> float:
        """
        Calculate convexity.
        
        :param yield_curve_handle: Yield curve for discounting
        :return: Convexity
        """
        engine = ql.DiscountingBondEngine(yield_curve_handle)
        self.bond.setPricingEngine(engine)
        
        clean_price = self.bond.cleanPrice()
        ytm = self.bond.bondYield(
            clean_price,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql,
        )
        
        return ql.BondFunctions.convexity(
            self.bond,
            ytm,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql,
        )
    
    def dv01(self, yield_curve_handle: ql.YieldTermStructureHandle) -> float:
        """
        Calculate DV01 (dollar value of one basis point).
        
        :param yield_curve_handle: Yield curve for discounting
        :return: DV01
        """
        engine = ql.DiscountingBondEngine(yield_curve_handle)
        self.bond.setPricingEngine(engine)
        
        # Get the yield first
        clean_price = self.bond.cleanPrice()
        ytm = self.bond.bondYield(
            clean_price,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql,
        )
        
        # Calculate BPV using yield
        return ql.BondFunctions.basisPointValue(
            self.bond,
            ytm,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql,
        )
    
    def get_cashflows(self) -> List[tuple]:
        """
        Get all cashflows of the bond.
        
        :return: List of (date, amount) tuples
        """
        cashflows = []
        for cf in self.bond.cashflows():
            try:
                date = cf.date()
                amount = cf.amount()
                cashflows.append((date, amount))
            except RuntimeError:
                # If amount() fails, try to get a reasonable estimate
                date = cf.date()
                if hasattr(cf, 'nominal'):
                    # For coupon payments, estimate based on nominal and rate
                    amount = cf.nominal() * 0.01  # Rough estimate
                else:
                    # For other cashflows (like redemption)
                    amount = self.face_value
                cashflows.append((date, amount))
        
        return cashflows
    
    # Methods for spread calculator compatibility
    def dirty_price_to_maturity(self, yield_curve_handle: ql.YieldTermStructureHandle) -> float:
        """For compatibility with spread calculator."""
        return self.dirty_price(yield_curve_handle)
    
    def dirty_price_to_call(self, yield_curve_handle: ql.YieldTermStructureHandle) -> float:
        """For compatibility with spread calculator. Returns dirty price for now."""
        # TODO: Implement proper callable floating rate bond pricing
        return self.dirty_price(yield_curve_handle)
    
    def get_projected_cashflows(self) -> List[tuple]:
        """
        Get projected cashflows using market curve for forward rates.
        
        :return: List of (date, projected_amount) tuples
        """
        if not self.sofr_curve:
            # Fall back to regular cashflows
            return self.get_cashflows()
        
        cashflows = []
        
        for cf in self.bond.cashflows():
            date = cf.date()
            py_date = datetime(date.year(), date.month(), date.dayOfMonth())
            
            # Check if this is a floating coupon
            if hasattr(cf, 'isFloatingRateCoupon') and cf.isFloatingRateCoupon():
                # Get the accrual period
                start_date = cf.accrualStartDate()
                end_date = cf.accrualEndDate()
                
                # Convert to Python dates
                py_start = datetime(start_date.year(), start_date.month(), start_date.dayOfMonth())
                py_end = datetime(end_date.year(), end_date.month(), end_date.dayOfMonth())
                
                # Get forward rate from market curve
                forward_rate = self.sofr_curve.get_forward_rate(py_start, py_end, ql.Compounded)
                
                # Apply gearing and spread
                gearing = cf.gearing() if hasattr(cf, 'gearing') else 1.0
                spread = cf.spread() if hasattr(cf, 'spread') else self.spread
                
                # Calculate projected amount
                nominal = cf.nominal()
                year_fraction = self.day_count.yearFraction(start_date, end_date)
                amount = nominal * (gearing * forward_rate + spread) * year_fraction
                
                cashflows.append((py_date, amount))
            else:
                # For fixed cashflows (like redemption)
                amount = cf.amount()
                cashflows.append((py_date, amount))
        
        return cashflows
    
    def get_spread_duration(self, yield_curve_handle: Optional[ql.YieldTermStructureHandle] = None) -> float:
        """
        Calculate spread duration (sensitivity to spread changes).
        
        :param yield_curve_handle: Optional yield curve
        :return: Spread duration
        """
        # Use provided curve or market curve
        if not yield_curve_handle and self.sofr_curve:
            yield_curve_handle = ql.YieldTermStructureHandle(self.sofr_curve.ql_curve)
        elif not yield_curve_handle:
            # Create default curve
            flat_curve = ql.FlatForward(
                self.settlement_date_ql,
                0.05,
                self.day_count
            )
            yield_curve_handle = ql.YieldTermStructureHandle(flat_curve)
        
        # Calculate base price
        engine = ql.DiscountingBondEngine(yield_curve_handle)
        self.bond.setPricingEngine(engine)
        base_price = self.bond.dirtyPrice()
        
        # Calculate price with 1bp spread shift
        # This is approximate - ideally we'd rebuild the bond with new spread
        spread_shift = 0.0001  # 1 basis point
        
        # Estimate spread duration
        # For floating rate bonds, spread duration ≈ time to next reset for the floating portion
        # Plus the PV-weighted average life for the spread component
        
        # Simple approximation: spread duration ≈ modified duration * (spread / (index_rate + spread))
        mod_duration = self.duration(yield_curve_handle)
        
        # Estimate average index rate (use overnight rate if available)
        if self.sofr_curve:
            index_rate = self.sofr_curve.curve_data.overnight_rate
        else:
            index_rate = 0.04  # Default assumption
        
        spread_duration = mod_duration * (self.spread / (index_rate + self.spread))
        
        return spread_duration