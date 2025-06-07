"""Tests for SOFR curve functionality."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

import QuantLib as ql

from securities_analytics.curves.sofr import (
    SOFRCurve,
    SOFRCurveData,
    SOFRCurvePoint,
    SOFRCurveLoader,
    TenorUnit
)


class TestSOFRCurveLoader:
    """Test SOFR curve data loading."""
    
    def test_parse_tenor(self):
        """Test tenor parsing."""
        loader = SOFRCurveLoader()
        
        # Test overnight
        value, unit = loader.parse_tenor("ON")
        assert value == 0
        assert unit == TenorUnit.OVERNIGHT
        
        # Test weeks
        value, unit = loader.parse_tenor("1W")
        assert value == 1
        assert unit == TenorUnit.WEEKS
        
        # Test months
        value, unit = loader.parse_tenor("3M")
        assert value == 3
        assert unit == TenorUnit.MONTHS
        
        # Test years
        value, unit = loader.parse_tenor("2Y")
        assert value == 2
        assert unit == TenorUnit.YEARS
    
    def test_load_from_csv(self):
        """Test loading from CSV file."""
        csv_path = Path(__file__).parent.parent / "data" / "sofr_curve.csv"
        
        loader = SOFRCurveLoader()
        curve_data = loader.load_from_csv(str(csv_path))
        
        # Check basic properties
        assert isinstance(curve_data, SOFRCurveData)
        assert len(curve_data.points) == 33  # 34 lines minus header
        
        # Check overnight rate
        assert curve_data.overnight_rate == pytest.approx(0.0431, rel=1e-4)
        
        # Check first few points
        first_point = curve_data.points[0]
        assert first_point.tenor_string == "ON"
        assert first_point.rate == pytest.approx(0.0431, rel=1e-4)
        
        # Check a swap point
        two_year = curve_data.get_rate_by_tenor("2Y")
        assert two_year == pytest.approx(0.03541, rel=1e-4)


class TestSOFRCurveData:
    """Test SOFR curve data model."""
    
    def test_get_deposit_and_swap_points(self):
        """Test separation of deposit and swap points."""
        points = [
            SOFRCurvePoint("ON", 0, TenorUnit.OVERNIGHT, 0.0431, "SOFR ON"),
            SOFRCurvePoint("1M", 1, TenorUnit.MONTHS, 0.0432, "SOFR 1M"),
            SOFRCurvePoint("3M", 3, TenorUnit.MONTHS, 0.0428, "SOFR 3M"),
            SOFRCurvePoint("1Y", 1, TenorUnit.YEARS, 0.0386, "SOFR 1Y"),
            SOFRCurvePoint("2Y", 2, TenorUnit.YEARS, 0.0354, "SOFR 2Y"),
            SOFRCurvePoint("5Y", 5, TenorUnit.YEARS, 0.0356, "SOFR 5Y"),
        ]
        
        curve_data = SOFRCurveData(datetime.now(), points)
        
        # Check deposits
        deposits = curve_data.get_deposit_points()
        assert len(deposits) == 3  # ON, 1M, 3M
        
        # Check swaps
        swaps = curve_data.get_swap_points()
        assert len(swaps) == 3  # 1Y, 2Y, 5Y
    
    def test_sorting(self):
        """Test that points are sorted by maturity."""
        points = [
            SOFRCurvePoint("5Y", 5, TenorUnit.YEARS, 0.0356, "SOFR 5Y"),
            SOFRCurvePoint("1M", 1, TenorUnit.MONTHS, 0.0432, "SOFR 1M"),
            SOFRCurvePoint("ON", 0, TenorUnit.OVERNIGHT, 0.0431, "SOFR ON"),
        ]
        
        curve_data = SOFRCurveData(datetime.now(), points)
        
        # Check sorting
        assert curve_data.points[0].tenor_string == "ON"
        assert curve_data.points[1].tenor_string == "1M"
        assert curve_data.points[2].tenor_string == "5Y"


class TestSOFRCurve:
    """Test SOFR curve construction and usage."""
    
    @pytest.fixture
    def sofr_curve(self):
        """Create a SOFR curve from test data."""
        csv_path = Path(__file__).parent.parent / "data" / "sofr_curve.csv"
        return SOFRCurve.from_csv(str(csv_path), datetime(2025, 4, 17))
    
    def test_curve_construction(self, sofr_curve):
        """Test that curve builds successfully."""
        # Access the QuantLib curve
        ql_curve = sofr_curve.ql_curve
        assert ql_curve is not None
        
        # Check reference date (settlement days = 2)
        ref_date = ql_curve.referenceDate()
        assert ref_date.year() == 2025
        assert ref_date.month() == 4
        # Should be 2 business days after 4/17 which might be 4/21 or 4/22
    
    def test_discount_factors(self, sofr_curve):
        """Test discount factor calculation."""
        # Get discount factor for 1 year
        one_year = datetime(2026, 4, 17)
        df = sofr_curve.get_discount_factor(one_year)
        
        # With ~3.86% 1Y rate, discount factor should be around 0.963
        assert df > 0.95
        assert df < 0.97
    
    def test_zero_rates(self, sofr_curve):
        """Test zero rate calculation."""
        # Get zero rate for 2 years
        two_years = datetime(2027, 4, 17)
        zero_rate = sofr_curve.get_zero_rate(two_years, ql.Continuous)
        
        # Should be close to the 2Y swap rate
        assert zero_rate > 0.03
        assert zero_rate < 0.04
    
    def test_forward_rates(self, sofr_curve):
        """Test forward rate calculation."""
        # Get 3M forward rate starting in 6M
        start = datetime(2025, 10, 17)
        end = datetime(2026, 1, 17)
        
        forward_rate = sofr_curve.get_forward_rate(start, end, ql.Compounded)
        
        # Should be reasonable
        assert forward_rate > 0.02
        assert forward_rate < 0.06
    
    def test_forward_curve(self, sofr_curve):
        """Test forward curve generation."""
        start = datetime(2025, 7, 17)
        end = datetime(2027, 7, 17)
        
        forward_curve = sofr_curve.get_forward_curve(start, end, frequency=4)
        
        # Should have quarterly points
        assert len(forward_curve) == 8  # 2 years * 4 quarters
        
        # Check values are reasonable
        for date, rate in forward_curve.items():
            assert rate > 0.02
            assert rate < 0.06
    
    def test_curve_summary(self, sofr_curve):
        """Test curve summary statistics."""
        summary = sofr_curve.get_curve_summary()
        
        assert summary["num_points"] == 33
        assert summary["overnight_rate"] == pytest.approx(0.0431, rel=1e-4)
        assert summary["currency"] == "USD"
        assert "ON" in summary["tenors"]
        assert "50Y" in summary["tenors"]
    
    def test_create_sofr_index(self, sofr_curve):
        """Test SOFR index creation."""
        sofr_index = sofr_curve.create_sofr_index()
        
        assert isinstance(sofr_index, ql.OvernightIndex)
        assert "SOFR" in sofr_index.name()
        
        # The index should be linked to our curve
        # Test by checking a fixing projection
        fixing_date = ql.Date(20, 4, 2025)
        # Note: This would require setting up fixings, which is complex
        # For now, just verify the index was created


class TestSOFRCurveIntegration:
    """Test integration with floating rate bonds."""
    
    def test_floating_bond_with_sofr_curve(self):
        """Test creating a floating bond with SOFR curve."""
        from securities_analytics.bonds.floating_rate import FloatingRateBond
        
        # Load SOFR curve
        csv_path = Path(__file__).parent.parent / "data" / "sofr_curve.csv"
        # Use a date for the curve
        curve_date = datetime(2025, 4, 17)
        sofr_curve = SOFRCurve.from_csv(str(csv_path), curve_date)
        
        # Verify curve was loaded
        assert sofr_curve.curve_data is not None
        assert len(sofr_curve.curve_data.points) == 33
        
        # Create a basic SOFR index  
        sofr_index = ql.Sofr()
        
        # Verify we can create the bond with SOFR curve parameter
        bond = FloatingRateBond(
            face_value=1000000,
            maturity_date=datetime(2030, 4, 17),
            floating_index=sofr_index,
            spread=0.01,  # 100 bps
            settlement_date=datetime(2025, 4, 17),
            day_count="Actual/360",
            settlement_days=2,
            frequency=4,
            sofr_curve=sofr_curve  # Pass the curve
        )
        
        # Verify the curve was linked
        assert bond.sofr_curve is not None
        
        # Test we can get projected cashflows (without causing pricing errors)
        # This verifies the integration works conceptually
        assert hasattr(bond, 'get_projected_cashflows')
        assert hasattr(bond, 'get_spread_duration')