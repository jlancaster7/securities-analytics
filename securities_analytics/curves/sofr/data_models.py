"""Data models for SOFR curve construction."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

import QuantLib as ql


class TenorUnit(Enum):
    """Units for tenor specification."""
    OVERNIGHT = "ON"
    DAYS = "D"
    WEEKS = "W"
    MONTHS = "M"
    YEARS = "Y"


@dataclass
class SOFRCurvePoint:
    """Single point on the SOFR curve."""
    tenor_string: str  # e.g., "ON", "1W", "3M", "2Y"
    tenor_value: int  # Numeric value (0 for ON)
    tenor_unit: TenorUnit
    rate: float  # In decimal (4.31% = 0.0431)
    description: str
    cusip: Optional[str] = None
    source: Optional[str] = None
    update_time: Optional[datetime] = None
    
    @property
    def ql_period(self) -> ql.Period:
        """Convert to QuantLib Period."""
        if self.tenor_unit == TenorUnit.OVERNIGHT:
            return ql.Period(1, ql.Days)
        elif self.tenor_unit == TenorUnit.DAYS:
            return ql.Period(self.tenor_value, ql.Days)
        elif self.tenor_unit == TenorUnit.WEEKS:
            return ql.Period(self.tenor_value, ql.Weeks)
        elif self.tenor_unit == TenorUnit.MONTHS:
            return ql.Period(self.tenor_value, ql.Months)
        elif self.tenor_unit == TenorUnit.YEARS:
            return ql.Period(self.tenor_value, ql.Years)
        else:
            raise ValueError(f"Unknown tenor unit: {self.tenor_unit}")
    
    @property
    def days_to_maturity(self) -> int:
        """Approximate days to maturity for sorting."""
        if self.tenor_unit == TenorUnit.OVERNIGHT:
            return 1
        elif self.tenor_unit == TenorUnit.DAYS:
            return self.tenor_value
        elif self.tenor_unit == TenorUnit.WEEKS:
            return self.tenor_value * 7
        elif self.tenor_unit == TenorUnit.MONTHS:
            return self.tenor_value * 30  # Approximate
        elif self.tenor_unit == TenorUnit.YEARS:
            return self.tenor_value * 365  # Approximate
        else:
            return 0


@dataclass
class SOFRCurveData:
    """Complete SOFR curve data."""
    curve_date: datetime
    points: List[SOFRCurvePoint]
    currency: str = "USD"
    
    def __post_init__(self):
        """Sort points by maturity."""
        self.points.sort(key=lambda p: p.days_to_maturity)
    
    @property
    def overnight_rate(self) -> float:
        """Get the overnight SOFR rate."""
        for point in self.points:
            if point.tenor_unit == TenorUnit.OVERNIGHT:
                return point.rate
        raise ValueError("No overnight rate found in curve data")
    
    def get_rate_by_tenor(self, tenor_string: str) -> Optional[float]:
        """Get rate for specific tenor."""
        for point in self.points:
            if point.tenor_string == tenor_string:
                return point.rate
        return None
    
    def get_deposit_points(self) -> List[SOFRCurvePoint]:
        """Get points suitable for deposit rate helpers (typically <= 1Y)."""
        deposits = []
        for point in self.points:
            if (point.tenor_unit in [TenorUnit.OVERNIGHT, TenorUnit.DAYS, TenorUnit.WEEKS] or
                (point.tenor_unit == TenorUnit.MONTHS and point.tenor_value <= 12)):
                deposits.append(point)
        return deposits
    
    def get_swap_points(self) -> List[SOFRCurvePoint]:
        """Get points suitable for swap rate helpers (typically > 1Y)."""
        swaps = []
        for point in self.points:
            if point.tenor_unit == TenorUnit.YEARS and point.tenor_value >= 1:
                swaps.append(point)
        return swaps
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to simple tenor->rate dictionary."""
        return {point.tenor_string: point.rate for point in self.points}