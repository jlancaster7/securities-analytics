from datetime import datetime, timedelta

import pytest
import QuantLib as ql

from securities_analytics.bonds.analytics.spreads import BondSpreadCalculator
from securities_analytics.bonds.fix_to_float.bond import FixToFloatBond
from securities_analytics.market_data.data_models import BondType, Rating, Sector
from securities_analytics.market_data.service import MarketDataService


class TestMarketDataIntegration:
    """Test integration of market data service with bond analytics."""
    
    @pytest.fixture
    def market_service(self):
        """Create market data service."""
        # Set evaluation date to today
        ql.Settings.instance().evaluationDate = ql.Date.todaysDate()
        return MarketDataService()
    
    @pytest.mark.skip(reason="Fix-to-float bond date handling needs work")
    def test_price_fix_to_float_with_market_data(self, market_service):
        """Test pricing fix-to-float bonds using market data service."""
        # Get SOFR curve from market service
        sofr_handle = market_service.get_sofr_curve_handle()
        
        # Create SOFR index
        sofr_index = ql.OvernightIndex(
            "SOFR", 1, ql.USDCurrency(),
            ql.UnitedStates(ql.UnitedStates.GovernmentBond),
            ql.Actual360(), sofr_handle
        )
        
        # Create fix-to-float bond with future settlement date
        bond = FixToFloatBond(
            face_value=1000000,  # $1MM
            maturity_date=datetime(2034, 2, 15),
            switch_date=datetime(2027, 2, 15),
            fixed_rate=0.045,
            floating_spread=0.01,
            settlement_date=datetime.now() + timedelta(days=2),  # Future date to avoid negative time
            day_count="ACT360",
            settlement_days=2,
            floating_index=sofr_index,
        )
        
        # Price using market curves
        clean_price = bond.clean_price(sofr_handle)
        dirty_price = bond.dirty_price(sofr_handle)
        
        # Should get reasonable prices
        assert 90 < clean_price < 110
        assert dirty_price >= clean_price  # Includes accrued interest
        
        # Calculate analytics
        duration = bond.duration(sofr_handle)
        convexity = bond.convexity(sofr_handle)
        
        assert 0 < duration < 20  # Reasonable duration
        assert convexity > 0
    
    @pytest.mark.skip(reason="Fix-to-float bond date handling needs work")
    def test_spread_calculation_with_market_curves(self, market_service):
        """Test spread calculations using market treasury curve."""
        # Get curves from market service
        treasury_curve = market_service.get_treasury_curve()
        sofr_handle = market_service.get_sofr_curve_handle()
        
        # Create SOFR index
        sofr_index = ql.OvernightIndex(
            "SOFR", 1, ql.USDCurrency(),
            ql.UnitedStates(ql.UnitedStates.GovernmentBond),
            ql.Actual360(), sofr_handle
        )
        
        # Create fix-to-float bond
        bond = FixToFloatBond(
            face_value=100,
            maturity_date=datetime(2034, 2, 15),
            switch_date=datetime(2027, 2, 15),
            fixed_rate=0.05,  # 5% fixed
            floating_spread=0.015,  # 150bps over SOFR
            settlement_date=datetime.now() + timedelta(days=2),  # Future date
            day_count="ACT360",
            settlement_days=2,
            floating_index=sofr_index,
        )
        
        # Create spread calculator
        calculator = BondSpreadCalculator(
            bond=bond,
            treasury_curve=treasury_curve,
            original_benchmark_tenor=10,
        )
        
        # Get model price
        model_price = bond.clean_price(sofr_handle)
        
        # Calculate spreads at discount
        market_price = model_price * 0.98
        spreads = calculator.spread_from_price(market_price)
        
        assert spreads["g_spread"] > 0  # Should have positive spread at discount
        assert spreads["spread_to_benchmark"] > 0
        
        # Test reverse calculation
        target_spread = 0.02  # 200bps
        calc_price = calculator.price_from_spread(target_spread, which_spread="g_spread")
        assert 80 < calc_price < 120
    
    def test_find_and_analyze_fix_to_float_bonds(self, market_service):
        """Test finding fix-to-float bonds in universe and analyzing them."""
        # Get all bonds
        all_bonds = market_service.get_bond_universe()
        
        # Find fix-to-float bonds
        fix_to_float_cusips = []
        for cusip in all_bonds:
            bond_ref = market_service.get_bond_reference(cusip)
            if bond_ref.bond_type == BondType.FIX_TO_FLOAT:
                fix_to_float_cusips.append(cusip)
        
        # Should have some fix-to-float bonds
        assert len(fix_to_float_cusips) > 0
        
        # Analyze first fix-to-float bond
        cusip = fix_to_float_cusips[0]
        bond_ref = market_service.get_bond_reference(cusip)
        quote = market_service.get_bond_quote(cusip)
        
        # Verify fix-to-float specific fields
        assert bond_ref.switch_date is not None
        assert bond_ref.float_index == "SOFR"
        assert bond_ref.float_spread is not None
        
        # Get credit spread for this bond
        credit_spread = market_service.get_credit_spread(
            bond_ref.composite_rating,
            bond_ref.sector,
            tenor=5.0
        )
        
        # Total spread should reflect credit risk
        assert credit_spread > 0
        
        # Quote should be reasonable
        assert 90 < quote.mid_price < 110
        assert quote.volume > 0
    
    def test_sector_analysis_with_market_data(self, market_service):
        """Test analyzing bonds by sector using market data."""
        sectors_to_analyze = [Sector.TECHNOLOGY, Sector.FINANCIALS, Sector.ENERGY]
        
        sector_stats = {}
        
        for sector in sectors_to_analyze:
            bonds = market_service.get_bond_universe(sectors=[sector])
            
            if not bonds:
                continue
            
            # Calculate average price and spread for sector
            prices = []
            spreads = []
            
            for cusip in bonds[:5]:  # Sample first 5 bonds
                quote = market_service.get_bond_quote(cusip)
                bond_ref = market_service.get_bond_reference(cusip)
                
                prices.append(quote.mid_price)
                
                # Get credit spread
                credit_spread = market_service.get_credit_spread(
                    bond_ref.composite_rating,
                    sector,
                    tenor=5.0
                )
                spreads.append(credit_spread)
            
            sector_stats[sector] = {
                "avg_price": sum(prices) / len(prices),
                "avg_spread": sum(spreads) / len(spreads),
                "bond_count": len(bonds)
            }
        
        # Should have data for multiple sectors
        assert len(sector_stats) >= 2
        
        # Different sectors should have different characteristics
        # Energy typically trades wider than tech
        if Sector.ENERGY in sector_stats and Sector.TECHNOLOGY in sector_stats:
            assert sector_stats[Sector.ENERGY]["avg_spread"] > \
                   sector_stats[Sector.TECHNOLOGY]["avg_spread"]
    
    @pytest.mark.skip(reason="Fix-to-float bond date handling needs work")
    def test_create_custom_bond_with_market_curves(self, market_service):
        """Test creating and pricing a custom bond with market curves."""
        # Get curves
        sofr_handle = market_service.get_sofr_curve_handle()
        treasury_curve = market_service.get_treasury_curve()
        
        # Get credit spread for A-rated tech company
        credit_spread = market_service.get_credit_spread(
            Rating.A,
            Sector.TECHNOLOGY,
            tenor=10.0
        )
        
        # Create SOFR index
        sofr_index = ql.OvernightIndex(
            "SOFR", 1, ql.USDCurrency(),
            ql.UnitedStates(ql.UnitedStates.GovernmentBond),
            ql.Actual360(), sofr_handle
        )
        
        # Create custom fix-to-float with credit spread
        bond = FixToFloatBond(
            face_value=1000000,
            maturity_date=datetime(2034, 2, 15),
            switch_date=datetime(2029, 2, 15),  # 5 years fixed
            fixed_rate=0.045 + credit_spread/10000,  # Treasury + credit spread
            floating_spread=0.005 + credit_spread/10000,  # SOFR + credit spread
            settlement_date=datetime.now() + timedelta(days=2),  # Future date
            day_count="ACT360",
            settlement_days=2,
            floating_index=sofr_index,
        )
        
        # Price bond
        clean_price = bond.clean_price(sofr_handle)
        
        # Calculate spread back to treasury
        calculator = BondSpreadCalculator(
            bond=bond,
            treasury_curve=treasury_curve,
            original_benchmark_tenor=10,
        )
        
        spreads = calculator.spread_from_price(clean_price)
        
        # G-spread should be close to input credit spread
        # (Some difference due to bond structure)
        g_spread_bps = spreads["g_spread"] * 10000
        assert abs(g_spread_bps - credit_spread) < 50  # Within 50bps