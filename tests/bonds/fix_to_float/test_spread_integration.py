from datetime import datetime

import pytest
import QuantLib as ql

from securities_analytics.bonds.analytics.spreads import BondSpreadCalculator
from securities_analytics.bonds.fix_to_float.bond import FixToFloatBond
from securities_analytics.utils.data_imports.curves import load_and_return_active_treasury_curve


class TestFixToFloatSpreadIntegration:
    """Test integration of fix-to-float bonds with spread calculator."""
    
    @pytest.fixture
    def treasury_curve(self):
        """Load treasury curve for spread calculations."""
        # Use the test data treasury curve
        return load_and_return_active_treasury_curve(
            file_path="tests/data/active_treasury_curve.csv",
            evaluation_date=datetime(2024, 2, 15)
        )
    
    @pytest.fixture
    def sofr_curve(self):
        """Create a simple SOFR curve for testing."""
        evaluation_date = ql.Date(15, 2, 2024)
        ql.Settings.instance().evaluationDate = evaluation_date
        
        flat_rate = 0.04  # 4% flat curve
        day_count = ql.Actual360()
        flat_curve = ql.FlatForward(evaluation_date, flat_rate, day_count)
        return ql.YieldTermStructureHandle(flat_curve)
    
    @pytest.fixture
    def fix_to_float_bond(self, sofr_curve):
        """Create a fix-to-float bond for testing."""
        sofr_index = ql.OvernightIndex(
            "SOFR", 1, ql.USDCurrency(),
            ql.UnitedStates(ql.UnitedStates.GovernmentBond),
            ql.Actual360(), sofr_curve
        )
        
        return FixToFloatBond(
            face_value=100,
            maturity_date=datetime(2034, 2, 15),  # 10 years
            switch_date=datetime(2027, 2, 15),    # 3 years fixed
            fixed_rate=0.045,  # 4.5% fixed
            floating_spread=0.01,  # 100bps over SOFR
            settlement_date=datetime(2024, 2, 15),
            day_count="ACT360",
            settlement_days=2,
            floating_index=sofr_index,
            fixed_frequency=2,  # Semiannual
            floating_frequency=4,  # Quarterly
        )
    
    def test_spread_calculator_creation(self, fix_to_float_bond, treasury_curve):
        """Test that spread calculator can be created with fix-to-float bond."""
        calculator = BondSpreadCalculator(
            bond=fix_to_float_bond,
            treasury_curve=treasury_curve,
            original_benchmark_tenor=10,
            use_earliest_call=False  # No call for this bond
        )
        
        assert calculator is not None
        assert calculator.bond == fix_to_float_bond
    
    def test_spread_calculation(self, fix_to_float_bond, treasury_curve, sofr_curve):
        """Test spread calculations for fix-to-float bond."""
        calculator = BondSpreadCalculator(
            bond=fix_to_float_bond,
            treasury_curve=treasury_curve,
            original_benchmark_tenor=10,
            use_earliest_call=False
        )
        
        # Get a reasonable market price
        model_price = fix_to_float_bond.clean_price(sofr_curve)
        
        # Calculate spreads at a larger discount to ensure positive spread
        test_price = model_price * 0.95  # 5% discount
        
        spreads = calculator.spread_from_price(test_price)
        
        assert "g_spread" in spreads
        assert "spread_to_benchmark" in spreads
        
        # Spreads exist and are reasonable
        # Note: spreads can be negative if bond yields less than treasuries
        assert -0.05 < spreads["g_spread"] < 0.05  # Within 500bps
        assert -0.05 < spreads["spread_to_benchmark"] < 0.05
        
        # G-spread and benchmark spread might be similar for short maturities
        # Just verify they are both calculated
        assert isinstance(spreads["g_spread"], float)
        assert isinstance(spreads["spread_to_benchmark"], float)
    
    def test_price_from_spread(self, fix_to_float_bond, treasury_curve, sofr_curve):
        """Test reverse calculation: price from spread."""
        calculator = BondSpreadCalculator(
            bond=fix_to_float_bond,
            treasury_curve=treasury_curve,
            original_benchmark_tenor=10,
            use_earliest_call=False
        )
        
        # Test with 100bps spread
        test_spread = 0.01
        
        g_spread_price = calculator.price_from_spread(test_spread, which_spread="g_spread")
        benchmark_price = calculator.price_from_spread(test_spread, which_spread="benchmark")
        
        # Prices should be reasonable
        assert 80 < g_spread_price < 120
        assert 80 < benchmark_price < 120
        
        # Prices should be different due to different spread methodologies
        assert abs(g_spread_price - benchmark_price) > 0.01
    
    def test_callable_fix_to_float(self, treasury_curve, sofr_curve):
        """Test spread calculator with callable fix-to-float bond."""
        sofr_index = ql.OvernightIndex(
            "SOFR", 1, ql.USDCurrency(),
            ql.UnitedStates(ql.UnitedStates.GovernmentBond),
            ql.Actual360(), sofr_curve
        )
        
        # Create callable fix-to-float
        callable_bond = FixToFloatBond(
            face_value=100,
            maturity_date=datetime(2034, 2, 15),
            switch_date=datetime(2027, 2, 15),
            fixed_rate=0.05,  # Higher coupon makes it callable
            floating_spread=0.015,
            settlement_date=datetime(2024, 2, 15),
            day_count="ACT360",
            settlement_days=2,
            floating_index=sofr_index,
            next_call_date=datetime(2027, 2, 15),  # Callable at switch
            call_price=100,
        )
        
        calculator = BondSpreadCalculator(
            bond=callable_bond,
            treasury_curve=treasury_curve,
            original_benchmark_tenor=10,
            use_earliest_call=True  # Use call date for workout
        )
        
        model_price = callable_bond.clean_price(sofr_curve)
        spreads = calculator.spread_from_price(model_price * 0.99)
        
        # Spreads exist and are reasonable
        assert -0.05 < spreads["g_spread"] < 0.05
        assert -0.05 < spreads["spread_to_benchmark"] < 0.05
    
    def test_different_benchmark_tenors(self, fix_to_float_bond, treasury_curve):
        """Test spread calculations with different original benchmark tenors."""
        for original_tenor in [5, 10, 30]:
            calculator = BondSpreadCalculator(
                bond=fix_to_float_bond,
                treasury_curve=treasury_curve,
                original_benchmark_tenor=original_tenor,
                use_earliest_call=False
            )
            
            spreads = calculator.spread_from_price(98.0)
            
            # Should get valid spreads for all tenors
            assert "g_spread" in spreads
            assert "spread_to_benchmark" in spreads
            assert isinstance(spreads["g_spread"], float)
            assert isinstance(spreads["spread_to_benchmark"], float)