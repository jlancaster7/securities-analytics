from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Rating(Enum):
    """Credit rating enumeration."""
    AAA = "AAA"
    AA_PLUS = "AA+"
    AA = "AA"
    AA_MINUS = "AA-"
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    BBB_PLUS = "BBB+"
    BBB = "BBB"
    BBB_MINUS = "BBB-"
    BB_PLUS = "BB+"
    BB = "BB"
    BB_MINUS = "BB-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    CCC_PLUS = "CCC+"
    CCC = "CCC"
    CCC_MINUS = "CCC-"
    CC = "CC"
    C = "C"
    D = "D"
    NR = "NR"  # Not Rated


class Sector(Enum):
    """Corporate bond sectors."""
    FINANCIALS = "Financials"
    INDUSTRIALS = "Industrials"
    UTILITIES = "Utilities"
    ENERGY = "Energy"
    TECHNOLOGY = "Technology"
    HEALTHCARE = "Healthcare"
    CONSUMER_DISCRETIONARY = "Consumer Discretionary"
    CONSUMER_STAPLES = "Consumer Staples"
    MATERIALS = "Materials"
    REAL_ESTATE = "Real Estate"
    TELECOMMUNICATIONS = "Telecommunications"
    OTHER = "Other"


class BondType(Enum):
    """Bond structure types."""
    FIXED_RATE = "Fixed Rate"
    FLOATING_RATE = "Floating Rate"
    FIX_TO_FLOAT = "Fix to Float"
    ZERO_COUPON = "Zero Coupon"
    CALLABLE = "Callable"
    PUTTABLE = "Puttable"
    CONVERTIBLE = "Convertible"


@dataclass
class BondReference:
    """Complete bond reference data."""
    cusip: str
    isin: Optional[str] = None
    ticker: Optional[str] = None
    issuer_name: str = ""
    
    # Structure
    bond_type: BondType = BondType.FIXED_RATE
    face_value: float = 1000.0
    issue_date: Optional[datetime] = None
    maturity_date: Optional[datetime] = None
    
    # Coupon details
    coupon_rate: Optional[float] = None
    coupon_frequency: int = 2  # Semiannual default
    day_count: str = "30/360"
    
    # For fix-to-float
    switch_date: Optional[datetime] = None
    float_index: Optional[str] = None  # e.g., "SOFR", "LIBOR"
    float_spread: Optional[float] = None
    
    # Call/Put features
    call_dates: List[datetime] = field(default_factory=list)
    call_prices: List[float] = field(default_factory=list)
    put_dates: List[datetime] = field(default_factory=list)
    put_prices: List[float] = field(default_factory=list)
    
    # Credit info
    rating_sp: Optional[Rating] = None
    rating_moody: Optional[Rating] = None
    rating_fitch: Optional[Rating] = None
    sector: Optional[Sector] = None
    subsector: Optional[str] = None
    
    # Other
    outstanding_amount: Optional[float] = None
    benchmark_treasury: Optional[int] = None  # Original benchmark tenor
    currency: str = "USD"
    country: str = "US"
    
    @property
    def composite_rating(self) -> Rating:
        """Get composite rating from available ratings."""
        ratings = [r for r in [self.rating_sp, self.rating_moody, self.rating_fitch] if r]
        if not ratings:
            return Rating.NR
        # Simple median approach - could be more sophisticated
        return ratings[len(ratings) // 2]


@dataclass
class MarketQuote:
    """Bond market quote data."""
    cusip: str
    timestamp: datetime
    
    # Pricing
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    mid_price: Optional[float] = None
    last_price: Optional[float] = None
    
    # Yields
    bid_yield: Optional[float] = None
    ask_yield: Optional[float] = None
    mid_yield: Optional[float] = None
    
    # Spreads
    bid_spread: Optional[float] = None  # To benchmark
    ask_spread: Optional[float] = None
    mid_spread: Optional[float] = None
    z_spread: Optional[float] = None
    oas: Optional[float] = None
    
    # Volume
    volume: Optional[float] = None
    trade_count: Optional[int] = None
    
    # Source info
    source: str = "COMPOSITE"
    quality: str = "INDICATIVE"  # FIRM, INDICATIVE, STALE


@dataclass
class CreditCurve:
    """Credit spread curve by rating and sector."""
    rating: Rating
    sector: Sector
    timestamp: datetime
    currency: str = "USD"
    
    # Spread curve: tenor -> spread (in bps)
    spreads: Dict[float, float] = field(default_factory=dict)
    
    def get_spread(self, tenor: float) -> float:
        """Get interpolated spread for given tenor."""
        if tenor in self.spreads:
            return self.spreads[tenor]
        
        # Linear interpolation
        tenors = sorted(self.spreads.keys())
        if tenor <= tenors[0]:
            return self.spreads[tenors[0]]
        if tenor >= tenors[-1]:
            return self.spreads[tenors[-1]]
        
        for i in range(len(tenors) - 1):
            if tenors[i] <= tenor <= tenors[i + 1]:
                t1, t2 = tenors[i], tenors[i + 1]
                s1, s2 = self.spreads[t1], self.spreads[t2]
                weight = (tenor - t1) / (t2 - t1)
                return s1 + weight * (s2 - s1)
        
        return self.spreads[tenors[-1]]


@dataclass
class MarketSnapshot:
    """Complete market data snapshot."""
    timestamp: datetime
    
    # Curves
    treasury_curve: Dict[float, float] = field(default_factory=dict)  # tenor -> yield
    sofr_curve: Dict[float, float] = field(default_factory=dict)      # tenor -> rate
    
    # Credit spreads by rating and sector
    credit_curves: Dict[Tuple[Rating, Sector], CreditCurve] = field(default_factory=dict)
    
    # Individual bond quotes
    bond_quotes: Dict[str, MarketQuote] = field(default_factory=dict)  # cusip -> quote
    
    # Index levels
    index_levels: Dict[str, float] = field(default_factory=dict)  # index_name -> level
    
    # Market conditions
    vix: Optional[float] = None
    move_index: Optional[float] = None
    dollar_index: Optional[float] = None