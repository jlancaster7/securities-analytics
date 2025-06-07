"""SOFR curve data loader."""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from securities_analytics.curves.sofr.data_models import (
    SOFRCurveData,
    SOFRCurvePoint,
    TenorUnit
)


class SOFRCurveLoader:
    """Load SOFR curve data from various sources."""
    
    @staticmethod
    def parse_tenor(tenor_string: str) -> tuple[int, TenorUnit]:
        """Parse tenor string into value and unit.
        
        Args:
            tenor_string: Tenor like "ON", "1W", "3M", "2Y"
            
        Returns:
            Tuple of (value, unit)
        """
        if tenor_string == "ON":
            return 0, TenorUnit.OVERNIGHT
            
        # Extract numeric part and unit
        import re
        match = re.match(r'^(\d+)([DWMY])$', tenor_string)
        if not match:
            raise ValueError(f"Invalid tenor format: {tenor_string}")
            
        value = int(match.group(1))
        unit_char = match.group(2)
        
        unit_map = {
            'D': TenorUnit.DAYS,
            'W': TenorUnit.WEEKS,
            'M': TenorUnit.MONTHS,
            'Y': TenorUnit.YEARS
        }
        
        if unit_char not in unit_map:
            raise ValueError(f"Unknown tenor unit: {unit_char}")
            
        return value, unit_map[unit_char]
    
    @classmethod
    def load_from_csv(cls, file_path: str, curve_date: Optional[datetime] = None) -> SOFRCurveData:
        """Load SOFR curve from CSV file.
        
        Args:
            file_path: Path to CSV file
            curve_date: Curve date (defaults to today)
            
        Returns:
            SOFRCurveData object
        """
        if curve_date is None:
            curve_date = datetime.now().date()
        elif isinstance(curve_date, datetime):
            curve_date = curve_date.date()
            
        points = []
        
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tenor_string = row['Tenor']
                tenor_value, tenor_unit = cls.parse_tenor(tenor_string)
                
                # Convert yield from percent to decimal
                rate = float(row['Yield']) / 100.0
                
                point = SOFRCurvePoint(
                    tenor_string=tenor_string,
                    tenor_value=tenor_value,
                    tenor_unit=tenor_unit,
                    rate=rate,
                    description=row['Description'],
                    cusip=row.get('CUSIP'),
                    source=row.get('Source'),
                    update_time=cls._parse_update_time(row.get('Update'))
                )
                points.append(point)
        
        return SOFRCurveData(
            curve_date=curve_date,
            points=points
        )
    
    @staticmethod
    def _parse_update_time(update_str: Optional[str]) -> Optional[datetime]:
        """Parse update time string."""
        if not update_str:
            return None
            
        # Handle different formats
        try:
            # Try full date format first
            return datetime.strptime(update_str, "%m/%d/%Y")
        except ValueError:
            # Try time only format
            try:
                # For time-only strings, return None
                if ":" in update_str:
                    return None
                return None
            except ValueError:
                return None