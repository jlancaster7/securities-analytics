from datetime import datetime, timedelta

import pytest

from securities_analytics.market_data.data_models import (
    BondType, Rating, Sector
)
from securities_analytics.market_data.service import MockDataProvider


class TestMockDataProvider:
    """Test MockDataProvider functionality."""
    
    @pytest.fixture
    def provider(self):
        """Create mock data provider."""
        return MockDataProvider()
    
    def test_treasury_curve_generation(self, provider):
        """Test treasury curve generation."""
        curve = provider.get_treasury_curve()
        
        # Check expected tenors
        expected_tenors = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]
        assert set(curve.keys()) == set(expected_tenors)
        
        # Check rates are reasonable (between 3% and 6%)
        for tenor, rate in curve.items():
            assert 0.03 < rate < 0.06
        
        # Check curve shape (generally upward sloping)
        assert curve[30.0] > curve[0.25]  # Long end higher than short end
    
    def test_treasury_curve_randomness(self, provider):
        """Test that treasury curve has some randomness."""
        curve1 = provider.get_treasury_curve()
        curve2 = provider.get_treasury_curve()
        
        # Curves should be different due to random noise
        differences = [abs(curve1[t] - curve2[t]) for t in curve1.keys()]
        assert any(d > 0 for d in differences)
        
        # But differences should be small (within 10bps)
        assert all(d < 0.001 for d in differences)
    
    def test_sofr_curve_generation(self, provider):
        """Test SOFR curve generation."""
        treasury_curve = provider.get_treasury_curve()
        sofr_curve = provider.get_sofr_curve()
        
        # SOFR should have same tenors as treasury
        assert set(sofr_curve.keys()) == set(treasury_curve.keys())
        
        # SOFR should be 5-15bps below treasuries (allowing for randomness)
        for tenor in sofr_curve.keys():
            spread = treasury_curve[tenor] - sofr_curve[tenor]
            assert -0.0005 <= spread <= 0.002  # Allow up to 20bps
    
    def test_credit_curve_generation(self, provider):
        """Test credit curve generation."""
        # Test different rating/sector combinations
        test_cases = [
            (Rating.AAA, Sector.TECHNOLOGY, 10, 100),
            (Rating.BBB, Sector.FINANCIALS, 50, 350),
            (Rating.BB, Sector.ENERGY, 200, 800),
        ]
        
        for rating, sector, min_spread, max_spread in test_cases:
            curve = provider.get_credit_curve(rating, sector)
            
            assert curve.rating == rating
            assert curve.sector == sector
            assert isinstance(curve.timestamp, datetime)
            
            # Check spreads are in expected range (bps)
            for tenor, spread in curve.spreads.items():
                assert min_spread <= spread <= max_spread
            
            # Check term structure (spreads increase with maturity)
            tenors = sorted(curve.spreads.keys())
            spreads = [curve.spreads[t] for t in tenors]
            # Allow for some noise, but general trend should be upward
            assert spreads[-1] > spreads[0]
    
    def test_bond_universe_generation(self, provider):
        """Test bond universe generation."""
        universe = provider._bond_universe
        
        # Should have bonds
        assert len(universe) > 0
        
        # Check expected issuers
        expected_tickers = ["AAPL", "MSFT", "JPM", "XOM", "JNJ", "WMT", "F", "T"]
        found_tickers = set()
        
        for cusip, bond in universe.items():
            # Check CUSIP format (truncated to 9 chars)
            assert len(cusip) == 9
            
            # Check bond has required fields
            assert bond.cusip == cusip
            assert bond.issuer_name
            assert bond.maturity_date > datetime.now()
            assert bond.issue_date < datetime.now()
            assert bond.coupon_rate is None or 0 <= bond.coupon_rate < 0.15  # Reasonable coupon range or None (0 for zero-coupon)
            
            found_tickers.add(bond.ticker)
        
        # Should have bonds from each expected issuer
        for ticker in expected_tickers:
            assert ticker in found_tickers
    
    def test_fix_to_float_bonds_in_universe(self, provider):
        """Test that fix-to-float bonds are generated."""
        universe = provider._bond_universe
        
        fix_to_float_count = sum(
            1 for bond in universe.values() 
            if bond.bond_type == BondType.FIX_TO_FLOAT
        )
        
        # Should have some fix-to-float bonds (roughly 20%)
        assert fix_to_float_count > 0
        assert fix_to_float_count < len(universe)  # Not all bonds
        
        # Check fix-to-float bonds have required fields
        for bond in universe.values():
            if bond.bond_type == BondType.FIX_TO_FLOAT:
                assert bond.switch_date is not None
                assert bond.float_index == "SOFR"
                assert 0.005 <= bond.float_spread <= 0.025
                assert bond.switch_date > datetime.now()  # Not switched yet
    
    def test_bond_quote_generation(self, provider):
        """Test bond quote generation."""
        # Get a bond from the universe
        cusip = list(provider._bond_universe.keys())[0]
        quote = provider.get_bond_quote(cusip)
        
        assert quote.cusip == cusip
        assert isinstance(quote.timestamp, datetime)
        
        # Check price relationships
        assert quote.bid_price < quote.ask_price
        assert quote.bid_price < quote.mid_price < quote.ask_price
        assert abs(quote.last_price - quote.mid_price) < 0.5
        
        # Check yields (inverse relationship with price)
        assert quote.bid_yield > quote.ask_yield  # Lower price = higher yield
        assert quote.bid_yield > quote.mid_yield > quote.ask_yield
        
        # Check volume and trades
        assert 1e6 <= quote.volume <= 1e8
        assert 10 <= quote.trade_count <= 100
    
    def test_bond_quote_pricing_logic(self, provider):
        """Test bond quote pricing reflects credit quality."""
        # Get bonds with different ratings
        aaa_bonds = []
        bbb_bonds = []
        
        for cusip, bond in provider._bond_universe.items():
            if bond.composite_rating == Rating.AAA:
                aaa_bonds.append(cusip)
            elif bond.composite_rating == Rating.BBB:
                bbb_bonds.append(cusip)
        
        # Need at least one of each
        assert len(aaa_bonds) > 0
        assert len(bbb_bonds) > 0
        
        # Compare average prices
        aaa_prices = [provider.get_bond_quote(c).mid_price for c in aaa_bonds[:3]]
        bbb_prices = [provider.get_bond_quote(c).mid_price for c in bbb_bonds[:3]]
        
        # AAA bonds should trade at higher prices (lower yields) on average
        assert sum(aaa_prices) / len(aaa_prices) > sum(bbb_prices) / len(bbb_prices)
    
    def test_bond_reference_retrieval(self, provider):
        """Test bond reference data retrieval."""
        cusip = list(provider._bond_universe.keys())[0]
        bond_ref = provider.get_bond_reference(cusip)
        
        # Should return same object from universe
        assert bond_ref == provider._bond_universe[cusip]
        assert bond_ref.cusip == cusip
    
    def test_unknown_cusip_handling(self, provider):
        """Test handling of unknown CUSIPs."""
        with pytest.raises(ValueError, match="Unknown CUSIP"):
            provider.get_bond_quote("INVALID123")
        
        with pytest.raises(ValueError, match="Unknown CUSIP"):
            provider.get_bond_reference("INVALID456")
    
    def test_callable_bonds_in_universe(self, provider):
        """Test that some bonds are callable."""
        universe = provider._bond_universe
        
        callable_count = sum(
            1 for bond in universe.values() 
            if bond.call_dates and len(bond.call_dates) > 0
        )
        
        # Should have some callable bonds (roughly 30%)
        assert callable_count > 0
        assert callable_count < len(universe)
        
        # Check callable bonds have valid call features
        for bond in universe.values():
            if bond.call_dates:
                assert len(bond.call_dates) == len(bond.call_prices)
                assert all(cd > datetime.now() for cd in bond.call_dates)
                assert all(cp == 100.0 for cp in bond.call_prices)  # Par calls