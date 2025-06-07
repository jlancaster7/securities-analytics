import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

import QuantLib as ql

from .data_models import (
    BondReference, BondType, CreditCurve, MarketQuote, 
    MarketSnapshot, Rating, Sector
)


class DataProvider(ABC):
    """Abstract base class for data providers."""
    
    @abstractmethod
    def get_treasury_curve(self) -> Dict[float, float]:
        """Get current treasury curve."""
        pass
    
    @abstractmethod
    def get_sofr_curve(self) -> Dict[float, float]:
        """Get current SOFR curve."""
        pass
    
    @abstractmethod
    def get_credit_curve(self, rating: Rating, sector: Sector) -> CreditCurve:
        """Get credit spread curve for rating/sector."""
        pass
    
    @abstractmethod
    def get_bond_quote(self, cusip: str) -> MarketQuote:
        """Get current market quote for bond."""
        pass
    
    @abstractmethod
    def get_bond_reference(self, cusip: str) -> BondReference:
        """Get bond reference data."""
        pass


class MockDataProvider(DataProvider):
    """Mock data provider for testing and development."""
    
    def __init__(self):
        self.base_date = datetime.now()
        self._bond_universe = self._generate_mock_universe()
    
    def get_treasury_curve(self) -> Dict[float, float]:
        """Generate realistic treasury curve."""
        # Base curve with typical shape
        base_curve = {
            0.25: 0.0380,   # 3M
            0.5: 0.0385,    # 6M
            1.0: 0.0390,    # 1Y
            2.0: 0.0395,    # 2Y
            3.0: 0.0400,    # 3Y
            5.0: 0.0410,    # 5Y
            7.0: 0.0420,    # 7Y
            10.0: 0.0435,   # 10Y
            20.0: 0.0465,   # 20Y
            30.0: 0.0475,   # 30Y
        }
        
        # Add some random noise (±5bps)
        return {
            tenor: rate + random.uniform(-0.0005, 0.0005)
            for tenor, rate in base_curve.items()
        }
    
    def get_sofr_curve(self) -> Dict[float, float]:
        """Generate SOFR curve (slightly below treasuries)."""
        treasury_curve = self.get_treasury_curve()
        # SOFR typically 5-10bps below treasuries
        return {
            tenor: rate - random.uniform(0.0005, 0.0010)
            for tenor, rate in treasury_curve.items()
        }
    
    def get_credit_curve(self, rating: Rating, sector: Sector) -> CreditCurve:
        """Generate credit spread curve based on rating and sector."""
        # Base spreads by rating (in bps)
        rating_spreads = {
            Rating.AAA: 20,
            Rating.AA_PLUS: 30,
            Rating.AA: 40,
            Rating.AA_MINUS: 50,
            Rating.A_PLUS: 60,
            Rating.A: 75,
            Rating.A_MINUS: 90,
            Rating.BBB_PLUS: 110,
            Rating.BBB: 135,
            Rating.BBB_MINUS: 165,
            Rating.BB_PLUS: 250,
            Rating.BB: 350,
            Rating.BB_MINUS: 450,
            Rating.B_PLUS: 550,
            Rating.B: 650,
            Rating.B_MINUS: 750,
        }
        
        # Sector adjustments
        sector_multipliers = {
            Sector.FINANCIALS: 1.1,
            Sector.ENERGY: 1.2,
            Sector.UTILITIES: 0.9,
            Sector.TECHNOLOGY: 1.05,
            Sector.HEALTHCARE: 0.95,
            Sector.CONSUMER_STAPLES: 0.85,
            Sector.REAL_ESTATE: 1.15,
        }
        
        base_spread = rating_spreads.get(rating, 200)
        sector_mult = sector_multipliers.get(sector, 1.0)
        
        # Generate curve with term structure
        tenors = [0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30]
        spreads = {}
        
        for tenor in tenors:
            # Spreads typically increase with maturity
            term_mult = 1.0 + 0.02 * (tenor - 5)  # 2% per year from 5Y
            spread = base_spread * sector_mult * term_mult
            # Add noise
            spread += random.uniform(-5, 5)
            spreads[tenor] = max(10, spread)  # Floor at 10bps
        
        return CreditCurve(
            rating=rating,
            sector=sector,
            timestamp=datetime.now(),
            spreads=spreads
        )
    
    def get_bond_quote(self, cusip: str) -> MarketQuote:
        """Generate mock bond quote."""
        if cusip not in self._bond_universe:
            raise ValueError(f"Unknown CUSIP: {cusip}")
        
        bond_ref = self._bond_universe[cusip]
        
        # Calculate theoretical price based on rating/sector
        base_price = 100.0
        
        # Adjust for credit quality
        rating_adjustments = {
            Rating.AAA: 2.0,
            Rating.AA: 1.5,
            Rating.A: 1.0,
            Rating.BBB: -0.5,
            Rating.BB: -3.0,
            Rating.B: -5.0,
        }
        
        rating_adj = 0
        for r, adj in rating_adjustments.items():
            if bond_ref.composite_rating.value.startswith(r.value[:1]):
                rating_adj = adj
                break
        
        # Adjust for maturity
        years_to_maturity = (bond_ref.maturity_date - datetime.now()).days / 365.25
        maturity_adj = -0.1 * max(0, years_to_maturity - 5)  # Longer = lower price
        
        # Adjust for coupon
        if bond_ref.coupon_rate:
            coupon_adj = (bond_ref.coupon_rate - 0.04) * 20  # 20x duration assumption
        else:
            coupon_adj = 0
        
        mid_price = base_price + rating_adj + maturity_adj + coupon_adj
        mid_price += random.uniform(-0.5, 0.5)  # Add noise
        
        # Create bid/ask spread
        spread_bps = 10 if bond_ref.composite_rating.value.startswith('A') else 25
        half_spread = spread_bps / 100 / 2
        
        # Calculate yields (simplified)
        mid_yield = 0.04 + (100 - mid_price) / 100 * 0.01  # Rough approximation
        
        return MarketQuote(
            cusip=cusip,
            timestamp=datetime.now(),
            bid_price=mid_price - half_spread,
            ask_price=mid_price + half_spread,
            mid_price=mid_price,
            last_price=mid_price + random.uniform(-half_spread, half_spread),
            bid_yield=mid_yield + 0.0005,
            ask_yield=mid_yield - 0.0005,
            mid_yield=mid_yield,
            volume=random.uniform(1e6, 1e8),
            trade_count=random.randint(10, 100),
            source="MOCK",
            quality="INDICATIVE"
        )
    
    def get_bond_reference(self, cusip: str) -> BondReference:
        """Get mock bond reference data."""
        if cusip not in self._bond_universe:
            raise ValueError(f"Unknown CUSIP: {cusip}")
        return self._bond_universe[cusip]
    
    def _generate_mock_universe(self) -> Dict[str, BondReference]:
        """Generate a universe of mock bonds."""
        universe = {}
        
        # Generate some sample bonds
        issuers = [
            ("AAPL", "Apple Inc", Sector.TECHNOLOGY, Rating.AA_PLUS),
            ("MSFT", "Microsoft Corp", Sector.TECHNOLOGY, Rating.AAA),
            ("JPM", "JPMorgan Chase", Sector.FINANCIALS, Rating.A_MINUS),
            ("XOM", "Exxon Mobil", Sector.ENERGY, Rating.AA_MINUS),
            ("JNJ", "Johnson & Johnson", Sector.HEALTHCARE, Rating.AAA),
            ("WMT", "Walmart Inc", Sector.CONSUMER_STAPLES, Rating.AA),
            ("F", "Ford Motor", Sector.CONSUMER_DISCRETIONARY, Rating.BB_PLUS),
            ("T", "AT&T Inc", Sector.TELECOMMUNICATIONS, Rating.BBB),
        ]
        
        for ticker, issuer_name, sector, rating in issuers:
            # Generate 3-5 bonds per issuer
            num_bonds = random.randint(3, 5)
            
            for i in range(num_bonds):
                cusip = f"{ticker:<4}{i:03d}00"[:9]  # Ensure 9 character CUSIP with padding
                
                # Vary maturity from 2 to 30 years
                years_to_maturity = random.choice([2, 3, 5, 7, 10, 15, 20, 30])
                maturity_date = datetime.now() + timedelta(days=365.25 * years_to_maturity)
                
                # Issue date 1-5 years ago
                years_since_issue = random.uniform(1, min(5, years_to_maturity - 1))
                issue_date = datetime.now() - timedelta(days=365.25 * years_since_issue)
                
                # Determine bond type (20% chance of fix-to-float)
                is_fix_to_float = random.random() < 0.2
                
                if is_fix_to_float:
                    # Fix-to-float parameters
                    years_to_switch = random.choice([3, 5, 7])
                    switch_date = issue_date + timedelta(days=365.25 * years_to_switch)
                    
                    # Only valid if switch hasn't happened yet
                    if switch_date > datetime.now():
                        bond_type = BondType.FIX_TO_FLOAT
                        float_index = "SOFR"
                        float_spread = random.uniform(0.005, 0.025)  # 50-250bps
                    else:
                        bond_type = BondType.FIXED_RATE
                        switch_date = None
                        float_index = None
                        float_spread = None
                else:
                    bond_type = BondType.FIXED_RATE
                    switch_date = None
                    float_index = None
                    float_spread = None
                
                # Coupon rate based on issue date and rating
                base_rate = 0.03 + (years_to_maturity / 100)
                credit_spread = (ord(rating.value[0]) - ord('A')) * 0.005
                coupon_rate = base_rate + credit_spread + random.uniform(-0.005, 0.005)
                coupon_rate = round(coupon_rate * 8) / 8  # Round to nearest 1/8%
                coupon_rate = min(coupon_rate, 0.12)  # Cap at 12%
                
                # 30% chance of being callable
                if random.random() < 0.3:
                    # First call date 3-5 years from issue
                    first_call_years = random.choice([3, 5])
                    first_call_date = issue_date + timedelta(days=365.25 * first_call_years)
                    
                    if first_call_date > datetime.now():
                        call_dates = [first_call_date]
                        call_prices = [100.0]  # Par call
                    else:
                        call_dates = []
                        call_prices = []
                else:
                    call_dates = []
                    call_prices = []
                
                bond = BondReference(
                    cusip=cusip,
                    ticker=ticker,
                    issuer_name=issuer_name,
                    bond_type=bond_type,
                    face_value=1000.0,
                    issue_date=issue_date,
                    maturity_date=maturity_date,
                    coupon_rate=coupon_rate,
                    coupon_frequency=2,
                    day_count="30/360",
                    switch_date=switch_date,
                    float_index=float_index,
                    float_spread=float_spread,
                    call_dates=call_dates,
                    call_prices=call_prices,
                    rating_sp=rating,
                    rating_moody=rating,
                    rating_fitch=rating,
                    sector=sector,
                    outstanding_amount=random.uniform(5e8, 2e9),
                    benchmark_treasury=10 if years_to_maturity >= 7 else 5,
                )
                
                universe[cusip] = bond
        
        return universe


class MarketDataService:
    """Main market data service that aggregates data from multiple providers."""
    
    def __init__(self, provider: Optional[DataProvider] = None):
        self.provider = provider or MockDataProvider()
        self._cache: Dict[str, Tuple[datetime, Any]] = {}
        self._cache_ttl = timedelta(seconds=60)  # 1 minute cache
    
    def get_market_snapshot(self) -> MarketSnapshot:
        """Get complete market snapshot."""
        return MarketSnapshot(
            timestamp=datetime.now(),
            treasury_curve=self.get_treasury_curve(),
            sofr_curve=self.get_sofr_curve(),
        )
    
    def get_treasury_curve(self) -> Dict[float, float]:
        """Get current treasury curve."""
        return self._get_cached_or_fetch("treasury_curve", self.provider.get_treasury_curve)
    
    def get_sofr_curve(self) -> Dict[float, float]:
        """Get current SOFR curve."""
        return self._get_cached_or_fetch("sofr_curve", self.provider.get_sofr_curve)
    
    def get_treasury_curve_handle(self) -> ql.YieldTermStructureHandle:
        """Get QuantLib yield curve handle for treasuries."""
        curve_data = self.get_treasury_curve()
        return self._build_curve_handle(curve_data)
    
    def get_sofr_curve_handle(self) -> ql.YieldTermStructureHandle:
        """Get QuantLib yield curve handle for SOFR."""
        curve_data = self.get_sofr_curve()
        return self._build_curve_handle(curve_data)
    
    def get_credit_spread(self, rating: Rating, sector: Sector, tenor: float) -> float:
        """Get credit spread for specific rating/sector/tenor."""
        cache_key = f"credit_{rating.value}_{sector.value}"
        curve = self._get_cached_or_fetch(
            cache_key, 
            lambda: self.provider.get_credit_curve(rating, sector)
        )
        return curve.get_spread(tenor)
    
    def get_bond_quote(self, cusip: str) -> MarketQuote:
        """Get current market quote for bond."""
        cache_key = f"quote_{cusip}"
        return self._get_cached_or_fetch(
            cache_key,
            lambda: self.provider.get_bond_quote(cusip)
        )
    
    def get_bond_reference(self, cusip: str) -> BondReference:
        """Get bond reference data."""
        cache_key = f"ref_{cusip}"
        # Reference data has longer TTL (1 hour)
        return self._get_cached_or_fetch(
            cache_key,
            lambda: self.provider.get_bond_reference(cusip),
            ttl=timedelta(hours=1)
        )
    
    def get_bond_universe(self, 
                         sectors: Optional[List[Sector]] = None,
                         ratings: Optional[List[Rating]] = None,
                         min_outstanding: Optional[float] = None) -> List[str]:
        """Get list of bonds matching criteria."""
        # In real implementation, this would query a database
        # For now, return all bonds from mock provider
        if isinstance(self.provider, MockDataProvider):
            cusips = []
            for cusip, bond in self.provider._bond_universe.items():
                if sectors and bond.sector not in sectors:
                    continue
                if ratings and bond.composite_rating not in ratings:
                    continue
                if min_outstanding and (bond.outstanding_amount or 0) < min_outstanding:
                    continue
                cusips.append(cusip)
            return cusips
        return []
    
    def _get_cached_or_fetch(self, key: str, fetch_func: Callable[[], Any], 
                            ttl: Optional[timedelta] = None) -> Any:
        """Get from cache or fetch from provider."""
        ttl = ttl or self._cache_ttl
        
        if key in self._cache:
            cached_time, cached_data = self._cache[key]
            if datetime.now() - cached_time < ttl:
                return cached_data
        
        # Fetch fresh data
        data = fetch_func()
        self._cache[key] = (datetime.now(), data)
        return data
    
    def _build_curve_handle(self, curve_data: Dict[float, float]) -> ql.YieldTermStructureHandle:
        """Build QuantLib curve handle from rate data."""
        # Get or set evaluation date
        eval_date = ql.Settings.instance().evaluationDate
        if eval_date == ql.Date():  # Not set
            eval_date = ql.Date.todaysDate()
            ql.Settings.instance().evaluationDate = eval_date
        
        # Convert to QuantLib format
        dates = []
        rates = []
        
        calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
        
        for tenor, rate in sorted(curve_data.items()):
            # Calculate date from tenor
            period = ql.Period(int(tenor * 12), ql.Months)
            date = calendar.advance(eval_date, period)
            dates.append(date)
            rates.append(rate)
        
        # Build curve
        curve = ql.ZeroCurve(dates, rates, ql.Actual365Fixed(), calendar)
        return ql.YieldTermStructureHandle(curve)
    
    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()


# Example usage and integration points for real data sources
class BloombergDataProvider(DataProvider):
    """Example Bloomberg data provider (requires Bloomberg API)."""
    
    def __init__(self, bloomberg_api):
        self.api = bloomberg_api
    
    def get_treasury_curve(self) -> Dict[float, float]:
        # Example Bloomberg API call
        # return self.api.get_curve("YCGT0025 Index")
        raise NotImplementedError("Implement with actual Bloomberg API")
    
    def get_sofr_curve(self) -> Dict[float, float]:
        # return self.api.get_curve("YCSW0023 Index")
        raise NotImplementedError("Implement with actual Bloomberg API")
    
    def get_credit_curve(self, rating: Rating, sector: Sector) -> CreditCurve:
        # Map to Bloomberg credit curves
        # return self.api.get_credit_curve(f"C{rating.value}{sector.value}")
        raise NotImplementedError("Implement with actual Bloomberg API")
    
    def get_bond_quote(self, cusip: str) -> MarketQuote:
        # return self.api.get_quote(f"/cusip/{cusip}")
        raise NotImplementedError("Implement with actual Bloomberg API")
    
    def get_bond_reference(self, cusip: str) -> BondReference:
        # return self.api.get_reference_data(f"/cusip/{cusip}")
        raise NotImplementedError("Implement with actual Bloomberg API")