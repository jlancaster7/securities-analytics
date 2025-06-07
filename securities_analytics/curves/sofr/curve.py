"""Main SOFR curve interface."""

from datetime import datetime
from typing import Optional, Dict, Any

import QuantLib as ql

from securities_analytics.curves.sofr.builder import SOFRCurveBuilder
from securities_analytics.curves.sofr.data_models import SOFRCurveData
from securities_analytics.curves.sofr.loader import SOFRCurveLoader


class SOFRCurve:
    """High-level interface for SOFR curve operations."""
    
    def __init__(self, curve_data: Optional[SOFRCurveData] = None):
        """Initialize SOFR curve.
        
        Args:
            curve_data: Optional curve data (can be set later)
        """
        self.curve_data = curve_data
        self.builder = SOFRCurveBuilder()
        self._ql_curve: Optional[ql.YieldTermStructure] = None
        
    @classmethod
    def from_csv(cls, file_path: str, curve_date: Optional[datetime] = None) -> 'SOFRCurve':
        """Create SOFR curve from CSV file.
        
        Args:
            file_path: Path to CSV file
            curve_date: Curve date (defaults to today)
            
        Returns:
            SOFRCurve instance
        """
        loader = SOFRCurveLoader()
        curve_data = loader.load_from_csv(file_path, curve_date)
        return cls(curve_data)
    
    @property
    def ql_curve(self) -> ql.YieldTermStructure:
        """Get or build QuantLib curve."""
        if self._ql_curve is None:
            if self.curve_data is None:
                raise ValueError("No curve data available")
            self._ql_curve = self.builder.build_curve(self.curve_data)
        return self._ql_curve
    
    def get_discount_factor(self, date: datetime) -> float:
        """Get discount factor for a given date.
        
        Args:
            date: Target date
            
        Returns:
            Discount factor
        """
        ql_date = ql.Date(date.day, date.month, date.year)
        return self.ql_curve.discount(ql_date)
    
    def get_zero_rate(self, date: datetime, compounding: int = ql.Continuous) -> float:
        """Get zero rate for a given date.
        
        Args:
            date: Target date
            compounding: Compounding convention
            
        Returns:
            Zero rate
        """
        ql_date = ql.Date(date.day, date.month, date.year)
        return self.ql_curve.zeroRate(
            ql_date,
            self.builder.day_count,
            compounding
        ).rate()
    
    def get_forward_rate(self, start_date: datetime, end_date: datetime,
                        compounding: int = ql.Continuous) -> float:
        """Get forward rate between two dates.
        
        Args:
            start_date: Start date
            end_date: End date
            compounding: Compounding convention
            
        Returns:
            Forward rate
        """
        ql_start = ql.Date(start_date.day, start_date.month, start_date.year)
        ql_end = ql.Date(end_date.day, end_date.month, end_date.year)
        
        return self.ql_curve.forwardRate(
            ql_start,
            ql_end,
            self.builder.day_count,
            compounding
        ).rate()
    
    def get_forward_curve(self, start_date: datetime, end_date: datetime,
                         frequency: int = 4) -> Dict[datetime, float]:
        """Get forward curve for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            frequency: Payment frequency (4=quarterly)
            
        Returns:
            Dictionary of date -> forward rate
        """
        forward_rates = self.builder.get_forward_rates(
            self.ql_curve,
            start_date,
            end_date,
            frequency
        )
        return dict(forward_rates)
    
    def get_curve_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the curve.
        
        Returns:
            Dictionary with curve statistics
        """
        if self.curve_data is None:
            return {}
            
        return {
            "curve_date": self.curve_data.curve_date,
            "num_points": len(self.curve_data.points),
            "overnight_rate": self.curve_data.overnight_rate,
            "tenors": [p.tenor_string for p in self.curve_data.points],
            "min_rate": min(p.rate for p in self.curve_data.points),
            "max_rate": max(p.rate for p in self.curve_data.points),
            "currency": self.curve_data.currency
        }
    
    def create_sofr_index(self) -> ql.OvernightIndex:
        """Create SOFR index linked to this curve.
        
        Returns:
            QuantLib SOFR index
        """
        # Create a relinkable handle for the curve
        curve_handle = ql.RelinkableYieldTermStructureHandle()
        curve_handle.linkTo(self.ql_curve)
        
        # Create SOFR index with our curve
        sofr = ql.Sofr(curve_handle)
        
        return sofr