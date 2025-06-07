import pytest
from datetime import datetime
import QuantLib as ql

from securities_analytics.bonds.floating_rate.bond import FloatingRateBond


class TestFloatingRateBond:
    """Test suite for FloatingRateBond class."""
    
    @pytest.fixture
    def setup_market_data(self):
        """Set up common market data for tests."""
        # Set evaluation date
        eval_date = ql.Date(15, 3, 2024)
        ql.Settings.instance().evaluationDate = eval_date
        
        # Create a flat forward curve for testing
        forward_rate = 0.05
        day_count = ql.Actual360()
        calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
        
        flat_curve = ql.FlatForward(
            2,  # settlement days
            calendar,
            forward_rate,
            day_count
        )
        curve_handle = ql.YieldTermStructureHandle(flat_curve)
        
        return {
            'eval_date': eval_date,
            'curve_handle': curve_handle,
            'calendar': calendar,
            'day_count': day_count,
        }
    
    @pytest.fixture
    def create_libor_index(self, setup_market_data):
        """Create a LIBOR index for testing."""
        curve_handle = setup_market_data['curve_handle']
        libor_3m = ql.USDLibor(ql.Period('3M'), curve_handle)
        return libor_3m
    
    @pytest.fixture
    def create_sofr_index(self, setup_market_data):
        """Create a SOFR index for testing."""
        curve_handle = setup_market_data['curve_handle']
        sofr = ql.OvernightIndex(
            "SOFR",
            1,  # settlement days
            ql.USDCurrency(),
            ql.UnitedStates(ql.UnitedStates.GovernmentBond),
            ql.Actual360(),
            curve_handle
        )
        return sofr
    
    def test_floating_rate_bond_creation_libor(self, setup_market_data, create_libor_index):
        """Test creation of a floating rate bond with LIBOR index."""
        bond = FloatingRateBond(
            face_value=1000000,
            maturity_date=datetime(2029, 3, 15),
            floating_index=create_libor_index,
            spread=0.01,  # 100 bps
            settlement_date=datetime(2024, 3, 15),
            day_count="ACT360",
            settlement_days=2,
            frequency=4,  # Quarterly
        )
        
        assert bond is not None
        assert bond.face_value == 1000000
        assert bond.spread == 0.01
        assert bond.frequency == 4
    
    def test_floating_rate_bond_creation_sofr(self, setup_market_data, create_sofr_index):
        """Test creation of a floating rate bond with SOFR index."""
        bond = FloatingRateBond(
            face_value=1000000,
            maturity_date=datetime(2029, 3, 15),
            floating_index=create_sofr_index,
            spread=0.0075,  # 75 bps
            settlement_date=datetime(2024, 3, 15),
            day_count="ACT360",
            settlement_days=2,
            frequency=4,  # Quarterly
        )
        
        assert bond is not None
        assert bond.face_value == 1000000
        assert bond.spread == 0.0075
        assert isinstance(bond.floating_index, ql.OvernightIndex)
    
    def test_clean_price_calculation(self, setup_market_data, create_libor_index):
        """Test clean price calculation for floating rate bond."""
        curve_handle = setup_market_data['curve_handle']
        
        bond = FloatingRateBond(
            face_value=1000000,
            maturity_date=datetime(2029, 3, 15),
            floating_index=create_libor_index,
            spread=0.01,
            settlement_date=datetime(2024, 3, 15),
            day_count="ACT360",
            settlement_days=2,
        )
        
        clean_price = bond.clean_price(curve_handle)
        
        # With a flat curve and spread, price should be close to par
        # but slightly above due to the positive spread
        assert clean_price > 99
        assert clean_price < 105
    
    def test_dirty_price_calculation(self, setup_market_data, create_libor_index):
        """Test dirty price calculation for floating rate bond."""
        curve_handle = setup_market_data['curve_handle']
        
        bond = FloatingRateBond(
            face_value=1000000,
            maturity_date=datetime(2029, 3, 15),
            floating_index=create_libor_index,
            spread=0.01,
            settlement_date=datetime(2024, 3, 15),
            day_count="ACT360",
            settlement_days=2,
        )
        
        dirty_price = bond.dirty_price(curve_handle)
        clean_price = bond.clean_price(curve_handle)
        
        # Dirty price should be >= clean price (includes accrued interest)
        assert dirty_price >= clean_price
    
    def test_yield_to_maturity(self, setup_market_data, create_libor_index):
        """Test yield to maturity calculation."""
        bond = FloatingRateBond(
            face_value=1000000,
            maturity_date=datetime(2029, 3, 15),
            floating_index=create_libor_index,
            spread=0.01,
            settlement_date=datetime(2024, 3, 15),
            day_count="ACT360",
            settlement_days=2,
        )
        
        market_price = 101.5
        ytm = bond.yield_to_maturity(market_price)
        
        # YTM should be reasonable
        assert ytm > 0
        assert ytm < 0.2  # Less than 20%
    
    def test_duration_calculation(self, setup_market_data, create_libor_index):
        """Test duration calculation for floating rate bond."""
        curve_handle = setup_market_data['curve_handle']
        
        bond = FloatingRateBond(
            face_value=1000000,
            maturity_date=datetime(2029, 3, 15),
            floating_index=create_libor_index,
            spread=0.01,
            settlement_date=datetime(2024, 3, 15),
            day_count="ACT360",
            settlement_days=2,
        )
        
        duration = bond.duration(curve_handle)
        
        # Floating rate bonds have duration related to their spread risk
        # and time to next reset. With 5 years to maturity, duration
        # should be positive but lower than comparable fixed rate bonds
        assert duration > 0
        assert duration < 6  # Lower than fixed rate bonds of same maturity
    
    def test_convexity_calculation(self, setup_market_data, create_libor_index):
        """Test convexity calculation for floating rate bond."""
        curve_handle = setup_market_data['curve_handle']
        
        bond = FloatingRateBond(
            face_value=1000000,
            maturity_date=datetime(2029, 3, 15),
            floating_index=create_libor_index,
            spread=0.01,
            settlement_date=datetime(2024, 3, 15),
            day_count="ACT360",
            settlement_days=2,
        )
        
        convexity = bond.convexity(curve_handle)
        
        # Convexity should be positive
        assert convexity > 0
        assert convexity < 50  # Lower than comparable fixed rate bonds
    
    def test_dv01_calculation(self, setup_market_data, create_libor_index):
        """Test DV01 calculation for floating rate bond."""
        curve_handle = setup_market_data['curve_handle']
        
        bond = FloatingRateBond(
            face_value=1000000,
            maturity_date=datetime(2029, 3, 15),
            floating_index=create_libor_index,
            spread=0.01,
            settlement_date=datetime(2024, 3, 15),
            day_count="ACT360",
            settlement_days=2,
        )
        
        dv01 = bond.dv01(curve_handle)
        
        # DV01 should show sensitivity to yield changes
        # For a $1M face value bond, DV01 should be reasonable
        assert abs(dv01) > 0  # Should have some sensitivity
        assert abs(dv01) < 5000  # But not too large
    
    def test_cashflows(self, setup_market_data, create_libor_index):
        """Test cashflow generation for floating rate bond."""
        bond = FloatingRateBond(
            face_value=1000000,
            maturity_date=datetime(2026, 3, 15),  # Shorter maturity for testing
            floating_index=create_libor_index,
            spread=0.01,
            settlement_date=datetime(2024, 3, 15),
            day_count="ACT360",
            settlement_days=2,
            frequency=4,  # Quarterly
        )
        
        cashflows = bond.get_cashflows()
        
        # Should have quarterly payments plus redemption
        # 2 years * 4 payments/year + 1 redemption = 9 cashflows
        assert len(cashflows) >= 8
        assert len(cashflows) <= 10  # Allow for some date adjustment
        
        # Last cashflow should be the redemption (face value)
        last_cf_amount = cashflows[-1][1]
        assert last_cf_amount == 1000000  # Face value redemption
    
    def test_floating_with_caps_and_floors(self, setup_market_data, create_libor_index):
        """Test floating rate bond with caps and floors."""
        bond = FloatingRateBond(
            face_value=1000000,
            maturity_date=datetime(2029, 3, 15),
            floating_index=create_libor_index,
            spread=0.01,
            settlement_date=datetime(2024, 3, 15),
            day_count="ACT360",
            settlement_days=2,
            caps=[0.08],  # 8% cap
            floors=[0.02],  # 2% floor
        )
        
        assert bond is not None
        assert bond.caps == [0.08]
        assert bond.floors == [0.02]
    
    def test_floating_with_gearing(self, setup_market_data, create_libor_index):
        """Test floating rate bond with gearing (leverage)."""
        bond = FloatingRateBond(
            face_value=1000000,
            maturity_date=datetime(2029, 3, 15),
            floating_index=create_libor_index,
            spread=0.01,
            settlement_date=datetime(2024, 3, 15),
            day_count="ACT360",
            settlement_days=2,
            gearings=[1.5],  # 1.5x the index rate
        )
        
        assert bond is not None
        assert bond.gearings == [1.5]
    
    def test_callable_floating_rate_bond(self, setup_market_data, create_libor_index):
        """Test callable floating rate bond."""
        bond = FloatingRateBond(
            face_value=1000000,
            maturity_date=datetime(2029, 3, 15),
            floating_index=create_libor_index,
            spread=0.01,
            settlement_date=datetime(2024, 3, 15),
            day_count="ACT360",
            settlement_days=2,
            next_call_date=datetime(2027, 3, 15),
            call_price=100.0,
        )
        
        assert bond is not None
        assert bond.next_call_date == datetime(2027, 3, 15)
        assert bond.call_price == 100.0
    
    def test_spread_calculator_compatibility(self, setup_market_data, create_libor_index):
        """Test that floating rate bond works with spread calculator."""
        from securities_analytics.bonds.analytics.spreads import BondSpreadCalculator
        
        curve_handle = setup_market_data['curve_handle']
        
        bond = FloatingRateBond(
            face_value=1000000,
            maturity_date=datetime(2029, 3, 15),
            floating_index=create_libor_index,
            spread=0.01,
            settlement_date=datetime(2024, 3, 15),
            day_count="ACT360",
            settlement_days=2,
        )
        
        # Create treasury curve
        treasury_curve = {
            0.25: 0.045,
            0.5: 0.046,
            1.0: 0.047,
            2.0: 0.048,
            3.0: 0.049,
            5.0: 0.050,
            7.0: 0.051,
            10.0: 0.052,
        }
        
        # Should be able to create spread calculator
        calculator = BondSpreadCalculator(
            bond=bond,
            treasury_curve=treasury_curve,
            original_benchmark_tenor=5,
        )
        
        assert calculator is not None
        assert calculator.bond == bond