from datetime import datetime

import pytest

from securities_analytics.market_data.data_models import (
    BondReference, BondType, CreditCurve, MarketQuote,
    MarketSnapshot, Rating, Sector
)


class TestDataModels:
    """Test market data model classes."""
    
    def test_rating_enum(self):
        """Test Rating enumeration."""
        assert Rating.AAA.value == "AAA"
        assert Rating.BB_PLUS.value == "BB+"
        assert Rating.NR.value == "NR"
        
        # Test all ratings are unique
        all_ratings = [r.value for r in Rating]
        assert len(all_ratings) == len(set(all_ratings))
    
    def test_sector_enum(self):
        """Test Sector enumeration."""
        assert Sector.FINANCIALS.value == "Financials"
        assert Sector.TECHNOLOGY.value == "Technology"
        
        # Test all sectors are unique
        all_sectors = [s.value for s in Sector]
        assert len(all_sectors) == len(set(all_sectors))
    
    def test_bond_type_enum(self):
        """Test BondType enumeration."""
        assert BondType.FIXED_RATE.value == "Fixed Rate"
        assert BondType.FIX_TO_FLOAT.value == "Fix to Float"
        assert BondType.CALLABLE.value == "Callable"
    
    def test_bond_reference_creation(self):
        """Test BondReference creation and properties."""
        bond = BondReference(
            cusip="912828XQ8",
            ticker="T",
            issuer_name="US Treasury",
            bond_type=BondType.FIXED_RATE,
            face_value=1000,
            issue_date=datetime(2020, 1, 15),
            maturity_date=datetime(2030, 1, 15),
            coupon_rate=0.025,
            rating_sp=Rating.AAA,
            rating_moody=Rating.AAA,
            rating_fitch=Rating.AAA,
            sector=Sector.OTHER,
        )
        
        assert bond.cusip == "912828XQ8"
        assert bond.ticker == "T"
        assert bond.coupon_frequency == 2  # Default
        assert bond.day_count == "30/360"  # Default
        assert bond.composite_rating == Rating.AAA
    
    def test_bond_reference_composite_rating(self):
        """Test composite rating calculation."""
        # All same ratings
        bond = BondReference(
            cusip="TEST123",
            rating_sp=Rating.AA,
            rating_moody=Rating.AA,
            rating_fitch=Rating.AA,
        )
        assert bond.composite_rating == Rating.AA
        
        # Mixed ratings - should return median
        bond2 = BondReference(
            cusip="TEST456",
            rating_sp=Rating.AA,
            rating_moody=Rating.A,
            rating_fitch=Rating.BBB,
        )
        assert bond2.composite_rating == Rating.A
        
        # No ratings
        bond3 = BondReference(cusip="TEST789")
        assert bond3.composite_rating == Rating.NR
    
    def test_fix_to_float_bond_reference(self):
        """Test fix-to-float specific fields."""
        bond = BondReference(
            cusip="FTF123",
            bond_type=BondType.FIX_TO_FLOAT,
            issue_date=datetime(2024, 1, 15),
            maturity_date=datetime(2034, 1, 15),
            switch_date=datetime(2027, 1, 15),
            coupon_rate=0.045,
            float_index="SOFR",
            float_spread=0.01,
        )
        
        assert bond.bond_type == BondType.FIX_TO_FLOAT
        assert bond.switch_date == datetime(2027, 1, 15)
        assert bond.float_index == "SOFR"
        assert bond.float_spread == 0.01
    
    def test_market_quote_creation(self):
        """Test MarketQuote creation."""
        quote = MarketQuote(
            cusip="TEST123",
            timestamp=datetime.now(),
            bid_price=99.5,
            ask_price=99.75,
            mid_price=99.625,
            last_price=99.65,
            bid_yield=0.045,
            ask_yield=0.044,
            mid_yield=0.0445,
            volume=1e7,
            trade_count=50,
        )
        
        assert quote.cusip == "TEST123"
        assert quote.bid_price == 99.5
        assert quote.ask_price == 99.75
        assert quote.mid_price == 99.625
        assert quote.source == "COMPOSITE"  # Default
        assert quote.quality == "INDICATIVE"  # Default
    
    def test_credit_curve_creation(self):
        """Test CreditCurve creation and interpolation."""
        curve = CreditCurve(
            rating=Rating.A,
            sector=Sector.TECHNOLOGY,
            timestamp=datetime.now(),
            spreads={
                1.0: 50,   # 50bps at 1Y
                5.0: 100,  # 100bps at 5Y
                10.0: 150, # 150bps at 10Y
            }
        )
        
        assert curve.rating == Rating.A
        assert curve.sector == Sector.TECHNOLOGY
        assert curve.currency == "USD"  # Default
        
        # Test exact points
        assert curve.get_spread(1.0) == 50
        assert curve.get_spread(5.0) == 100
        assert curve.get_spread(10.0) == 150
        
        # Test interpolation
        assert curve.get_spread(3.0) == 75  # Linear between 1Y and 5Y
        assert curve.get_spread(7.5) == 125  # Linear between 5Y and 10Y
        
        # Test extrapolation
        assert curve.get_spread(0.5) == 50  # Below range
        assert curve.get_spread(15.0) == 150  # Above range
    
    def test_credit_curve_interpolation_edge_cases(self):
        """Test credit curve interpolation edge cases."""
        # Single point curve
        curve = CreditCurve(
            rating=Rating.BBB,
            sector=Sector.ENERGY,
            timestamp=datetime.now(),
            spreads={5.0: 200}
        )
        
        assert curve.get_spread(1.0) == 200
        assert curve.get_spread(5.0) == 200
        assert curve.get_spread(10.0) == 200
    
    def test_market_snapshot_creation(self):
        """Test MarketSnapshot creation."""
        snapshot = MarketSnapshot(
            timestamp=datetime.now(),
            treasury_curve={
                1.0: 0.04,
                5.0: 0.042,
                10.0: 0.045,
            },
            sofr_curve={
                1.0: 0.038,
                5.0: 0.04,
                10.0: 0.043,
            }
        )
        
        assert len(snapshot.treasury_curve) == 3
        assert snapshot.treasury_curve[5.0] == 0.042
        assert len(snapshot.sofr_curve) == 3
        assert snapshot.sofr_curve[1.0] == 0.038
        
        # Default empty dicts
        assert snapshot.credit_curves == {}
        assert snapshot.bond_quotes == {}
        assert snapshot.index_levels == {}