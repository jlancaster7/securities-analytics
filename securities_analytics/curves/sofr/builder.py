"""SOFR curve builder using QuantLib."""

from datetime import datetime
from typing import List, Optional

import QuantLib as ql

from securities_analytics.curves.sofr.data_models import SOFRCurveData, SOFRCurvePoint


class SOFRCurveBuilder:
    """Build SOFR curves using QuantLib bootstrapping."""
    
    def __init__(self, calendar: Optional[ql.Calendar] = None):
        """Initialize builder.
        
        Args:
            calendar: Calendar for date calculations (defaults to US calendar)
        """
        self.calendar = calendar or ql.UnitedStates(ql.UnitedStates.SOFR)
        self.day_count = ql.Actual360()  # Standard for SOFR
        self.settlement_days = 2
        
    def build_curve(self, curve_data: SOFRCurveData) -> ql.YieldTermStructure:
        """Build bootstrapped SOFR curve from market data.
        
        Args:
            curve_data: SOFR curve data points
            
        Returns:
            QuantLib yield term structure
        """
        # Set evaluation date
        ql_date = ql.Date(
            curve_data.curve_date.day,
            curve_data.curve_date.month,
            curve_data.curve_date.year
        )
        ql.Settings.instance().evaluationDate = ql_date
        
        # Create rate helpers
        helpers = []
        
        # Add deposit rate helpers for short end
        deposit_points = curve_data.get_deposit_points()
        for point in deposit_points:
            helper = self._create_deposit_helper(point)
            if helper:
                helpers.append(helper)
        
        # Add swap rate helpers for long end
        swap_points = curve_data.get_swap_points()
        sofr_index = ql.Sofr()
        for point in swap_points:
            helper = self._create_swap_helper(point, sofr_index)
            if helper:
                helpers.append(helper)
        
        # Build curve
        curve = ql.PiecewiseLogCubicDiscount(
            self.settlement_days,
            self.calendar,
            helpers,
            self.day_count
        )
        
        # Enable extrapolation
        curve.enableExtrapolation()
        
        return curve
    
    def _create_deposit_helper(self, point: SOFRCurvePoint) -> Optional[ql.RateHelper]:
        """Create deposit rate helper."""
        try:
            quote = ql.QuoteHandle(ql.SimpleQuote(point.rate))
            
            # For overnight, use special handling
            if point.tenor_unit.value == "ON":
                tenor = ql.Period(1, ql.Days)
            else:
                tenor = point.ql_period
            
            helper = ql.DepositRateHelper(
                quote,
                tenor,
                self.settlement_days,
                self.calendar,
                ql.ModifiedFollowing,
                True,  # End of month
                self.day_count
            )
            
            return helper
            
        except Exception as e:
            print(f"Warning: Failed to create deposit helper for {point.tenor_string}: {e}")
            return None
    
    def _create_swap_helper(self, point: SOFRCurvePoint, index: ql.OvernightIndex) -> Optional[ql.RateHelper]:
        """Create OIS swap rate helper."""
        try:
            quote = ql.QuoteHandle(ql.SimpleQuote(point.rate))
            tenor = point.ql_period
            
            helper = ql.OISRateHelper(
                self.settlement_days,
                tenor,
                quote,
                index
            )
            
            return helper
            
        except Exception as e:
            print(f"Warning: Failed to create swap helper for {point.tenor_string}: {e}")
            return None
    
    def build_forward_curve(self, curve_data: SOFRCurveData) -> ql.YieldTermStructure:
        """Build forward curve suitable for floating rate projections.
        
        This creates a curve that can be used for projecting future SOFR fixings.
        
        Args:
            curve_data: SOFR curve data points
            
        Returns:
            QuantLib yield term structure for forward projections
        """
        # Build the standard curve
        curve = self.build_curve(curve_data)
        
        # For forward projections, we may want to apply convexity adjustments
        # For now, return the standard curve
        return curve
    
    def get_forward_rates(self, curve: ql.YieldTermStructure, 
                         start_date: datetime,
                         end_date: datetime,
                         frequency: int = 4) -> List[tuple[datetime, float]]:
        """Get forward rates from curve.
        
        Args:
            curve: QuantLib yield curve
            start_date: Start date for forward rates
            end_date: End date for forward rates  
            frequency: Payment frequency (4=quarterly)
            
        Returns:
            List of (date, forward_rate) tuples
        """
        # Convert dates
        ql_start = ql.Date(start_date.day, start_date.month, start_date.year)
        ql_end = ql.Date(end_date.day, end_date.month, end_date.year)
        
        # Create schedule
        tenor = ql.Period(int(12/frequency), ql.Months)
        schedule = ql.Schedule(
            ql_start,
            ql_end,
            tenor,
            self.calendar,
            ql.ModifiedFollowing,
            ql.ModifiedFollowing,
            ql.DateGeneration.Forward,
            False
        )
        
        # Calculate forward rates
        forward_rates = []
        
        for i in range(1, len(schedule)):
            start = schedule[i-1]
            end = schedule[i]
            
            # Calculate forward rate
            forward_rate = curve.forwardRate(
                start, 
                end,
                self.day_count,
                ql.Compounded,
                ql.Annual
            ).rate()
            
            # Convert date
            py_date = datetime(end.year(), end.month(), end.dayOfMonth())
            forward_rates.append((py_date, forward_rate))
            
        return forward_rates