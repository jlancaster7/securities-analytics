# Technical Guide - Fixed Income Analytics Service

This guide provides comprehensive technical documentation for the fixed income analytics service, covering fix-to-float bonds, callable bonds, and the market data framework.

## Table of Contents

1. [Fix-to-Float Bonds](#fix-to-float-bonds)
2. [Callable Fix-to-Float Bonds](#callable-fix-to-float-bonds)
3. [Market Data Service](#market-data-service)
4. [Analytics and Calculations](#analytics-and-calculations)
5. [Best Practices](#best-practices)
6. [QuantLib Reference](#quantlib-reference)

## Fix-to-Float Bonds

### Overview

Fix-to-float bonds are hybrid instruments that pay a fixed coupon rate for an initial period, then switch to a floating rate (typically SOFR + spread) for the remainder of their life.

### Architecture

```
fix_to_float/
├── bond.py                    # Main FixToFloatBond class
└── schedulers/
    └── scheduler.py           # FixToFloatScheduleGenerator
```

### Implementation Details

#### Schedule Generation

The `FixToFloatScheduleGenerator` creates separate schedules for fixed and floating periods:

```python
scheduler = FixToFloatScheduleGenerator(
    issue_date=datetime(2024, 1, 15),
    switch_date=datetime(2027, 1, 15),    # 3 years fixed
    maturity_date=datetime(2034, 1, 15),   # 10 years total
    fixed_frequency=2,      # Semiannual during fixed period
    floating_frequency=4,   # Quarterly during floating period
    calendar=ql.UnitedStates(ql.UnitedStates.GovernmentBond),
    business_day_convention=ql.Following,
)

fixed_schedule = scheduler.generate_fixed_schedule()
floating_schedule = scheduler.generate_floating_schedule()
```

*For more details on QuantLib schedule generation patterns, see the [QuantLib Reference Guide](quantlib-reference.md#bonds).*

#### Bond Creation

The `FixToFloatBond` class creates a composite QuantLib bond:

```python
# Create SOFR index
sofr_index = ql.OvernightIndex(
    "SOFR", 1, ql.USDCurrency(),
    ql.UnitedStates(ql.UnitedStates.GovernmentBond),
    ql.Actual360(), sofr_curve_handle
)

# Create fix-to-float bond
bond = FixToFloatBond(
    face_value=100,
    maturity_date=datetime(2034, 2, 15),
    switch_date=datetime(2027, 2, 15),
    fixed_rate=0.045,           # 4.5% fixed rate
    floating_spread=0.01,       # 100bps over SOFR
    settlement_date=datetime(2024, 2, 15),
    day_count="ACT360",
    settlement_days=2,
    floating_index=sofr_index,
    fixed_frequency=2,          # Semiannual fixed payments
    floating_frequency=4,       # Quarterly floating payments
)
```

### Cashflow Structure

1. **Fixed Period**: Standard fixed-rate coupons using `ql.FixedRateLeg`
2. **Floating Period**: Overnight index-based coupons using `ql.OvernightLeg`
3. **Principal**: Single redemption at maturity

*For comprehensive examples of leg construction and cash flow analysis, see the [QuantLib Reference Guide](quantlib-reference.md#cash-flows-legs-and-interest-rates).*

### Analytics Support

All standard bond analytics are supported:
- **Pricing**: Clean/dirty price with appropriate curve
- **Yield**: YTM using forward curve for floating cashflows
- **Duration**: Modified and Macaulay duration
- **Convexity**: Accounting for hybrid structure
- **DV01**: Dollar value of basis point
- **Spreads**: G-spread, benchmark spread, Z-spread

## Callable Fix-to-Float Bonds

### Current Implementation

Basic support exists for single call date:

```python
bond = FixToFloatBond(
    # ... standard parameters ...
    next_call_date=datetime(2027, 2, 15),
    call_price=100.0,
)
```

### Limitations and Enhancements Needed

#### Current Limitations
1. Only single call date supported
2. `dirty_price_to_call()` returns same as YTM (oversimplified)
3. No sophisticated handling when call date ≠ switch date

#### Scenarios to Handle

**Scenario 1: Call Date = Switch Date**
```python
# Most common - issuer can refinance at rate transition
maturity_date=datetime(2034, 3, 15),
switch_date=datetime(2027, 3, 15),
next_call_date=datetime(2027, 3, 15),  # Same as switch
```

**Scenario 2: Call Date < Switch Date**
```python
# Bond callable while still paying fixed rate
switch_date=datetime(2029, 3, 15),
next_call_date=datetime(2026, 3, 15),  # Before switch
```

**Scenario 3: Call Date > Switch Date**
```python
# Bond callable during floating period
switch_date=datetime(2027, 3, 15),
next_call_date=datetime(2030, 3, 15),  # After switch
```

### Recommended Enhancement: Multiple Call Support

```python
class CallableFixToFloatBond(FixToFloatBond):
    def __init__(self, *args, 
                 call_schedule: List[Tuple[datetime, float]] = None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.call_schedule = sorted(call_schedule, key=lambda x: x[0])
    
    def yield_to_worst(self, market_price: float) -> float:
        """Calculate worst yield across all call scenarios."""
        yields = [self.yield_to_maturity(market_price)]
        
        for call_date, call_price in self.call_schedule:
            ytc = self.yield_to_call(market_price, call_date, call_price)
            yields.append(ytc)
        
        return min(yields)  # Worst for investor
```

## Market Data Service

### Architecture

The market data service provides a flexible framework for integrating various data sources:

```
market_data/
├── data_models.py    # Core data structures
└── service.py        # Service and provider classes
```

### Data Models

#### Enumerations
```python
class Rating(Enum):
    AAA = "AAA"
    AA_PLUS = "AA+"
    # ... etc

class Sector(Enum):
    FINANCIALS = "Financials"
    TECHNOLOGY = "Technology"
    # ... etc

class BondType(Enum):
    FIXED_RATE = "Fixed Rate"
    FIX_TO_FLOAT = "Fix to Float"
    # ... etc
```

#### Core Data Structures

**BondReference**: Complete bond metadata
```python
@dataclass
class BondReference:
    cusip: str
    issuer_name: str
    maturity_date: datetime
    coupon_rate: float
    # Fix-to-float specific
    switch_date: Optional[datetime]
    float_index: Optional[str]
    float_spread: Optional[float]
    # ... many more fields
```

**MarketQuote**: Real-time pricing
```python
@dataclass
class MarketQuote:
    cusip: str
    bid_price: float
    ask_price: float
    mid_price: float
    bid_yield: float
    ask_yield: float
    # ... volume, trade count, etc
```

**CreditCurve**: Spread curves by rating/sector
```python
@dataclass
class CreditCurve:
    rating: Rating
    sector: Sector
    spreads: Dict[float, float]  # tenor -> spread
    
    def get_spread(self, tenor: float) -> float:
        """Interpolated spread for any tenor."""
```

### Service Layer

#### DataProvider Interface
```python
class DataProvider(ABC):
    @abstractmethod
    def get_treasury_curve(self) -> Dict[float, float]:
        """Get current treasury curve."""
        pass
    
    @abstractmethod
    def get_bond_quote(self, cusip: str) -> MarketQuote:
        """Get current market quote."""
        pass
    
    # ... other required methods
```

#### MarketDataService
Main service with caching:
```python
class MarketDataService:
    def __init__(self, provider: DataProvider = None):
        self.provider = provider or MockDataProvider()
        self._cache = {}
        self._cache_ttl = timedelta(seconds=60)
    
    def get_sofr_curve_handle(self) -> ql.YieldTermStructureHandle:
        """Get QuantLib curve handle for SOFR."""
        curve_data = self.get_sofr_curve()
        return self._build_curve_handle(curve_data)
```

### Mock Data Provider

Generates realistic test data:
- Treasury curves with proper term structure
- SOFR curves 5-10bps below treasuries
- Credit spreads varying by rating and sector
- Bond universe with ~30-40 bonds
- 20% of bonds are fix-to-float structures

## Analytics and Calculations

### Spread Calculations

The `BondSpreadCalculator` supports multiple spread types:

#### G-Spread
Linear interpolation of treasury curve at bond's maturity:
```python
def _get_treasury_yield_linear(self) -> float:
    t = self._time_to_workout_in_years()
    return self._linear_interpolate_curve(t)
```

#### Benchmark Spread
Uses tenor step-down rules:
- Original 10Y bond: stays 10Y until <7 years, then 5Y, etc.
- Maintains original benchmark relationship

#### Z-Spread
Parallel shift to curve that reprices bond:
```python
z_spread = ql.BondFunctions.zSpread(
    bond, market_price, curve,
    day_count, compounding, frequency
)
```

*For more advanced spread calculation examples and bond analytics, see the [QuantLib Reference Guide](quantlib-reference.md#bonds).*

### Risk Measures

#### Duration
- **Modified Duration**: Price sensitivity to yield changes
- **Macaulay Duration**: Weighted average time to cashflows
- Both account for fix-to-float structure

#### Convexity
Second-order price sensitivity:
```python
convexity = ql.BondFunctions.convexity(
    bond, yield, day_count, compounding, frequency
)
```

#### DV01
Dollar value of one basis point:
```python
dv01 = bond.dv01(yield_curve_handle)
```

## Best Practices

### Date Handling
1. Always set QuantLib evaluation date:
   ```python
   ql.Settings.instance().evaluationDate = ql.Date.todaysDate()
   ```
2. Use consistent date conventions across bonds
3. Handle holidays with appropriate calendars

### Curve Construction
1. Ensure sufficient tenor points for interpolation
2. Use appropriate day count for each curve
3. Consider curve bootstrapping for accuracy

### Performance Optimization
1. Cache market data appropriately
2. Reuse curve handles when pricing multiple bonds
3. Consider parallel processing for large portfolios

### Error Handling
1. Validate input parameters
2. Handle missing market data gracefully
3. Provide meaningful error messages

### Testing
1. Test edge cases (very short maturity, at switch date)
2. Verify against known good prices
3. Test with realistic market data

## Common Issues and Solutions

### Issue: Negative time error in QuantLib
**Solution**: Ensure settlement date is after evaluation date

### Issue: Floating leg pricing seems wrong
**Solution**: Verify index fixing history is properly set

### Issue: Z-spread calculation fails
**Solution**: Check that market price is within reasonable bounds

### Issue: Duration seems too high/low
**Solution**: Verify yield curve is properly constructed

## SOFR Curve Construction

The service includes advanced SOFR curve construction capabilities for accurate forward rate projections in floating rate bonds:

### Architecture

```
curves/
└── sofr/
    ├── data_models.py    # Data structures for curve points
    ├── loader.py         # CSV and data loading
    ├── builder.py        # QuantLib curve construction
    └── curve.py          # High-level interface
```

### Components

#### Data Models (`data_models.py`)
- **`SOFRCurvePoint`**: Individual curve point with tenor and rate
- **`SOFRCurveData`**: Complete curve data with helper methods
- **`TenorUnit`**: Enum for tenor specifications (ON, Days, Weeks, Months, Years)

#### Curve Loader (`loader.py`)
Loads SOFR curve data from various sources:
```python
loader = SOFRCurveLoader()
curve_data = loader.load_from_csv('path/to/sofr_curve.csv')
```

Features:
- Parses tenor strings (e.g., "3M", "2Y", "ON")
- Converts yields from percent to decimal
- Handles various date formats

#### Curve Builder (`builder.py`)
Bootstraps SOFR curves using QuantLib:
```python
builder = SOFRCurveBuilder()
ql_curve = builder.build_curve(curve_data)
```

Process:
1. Creates deposit rate helpers for short tenors (ON to 1Y)
2. Creates OIS swap rate helpers for long tenors (1Y+)
3. Bootstraps using `PiecewiseLogCubicDiscount`
4. Enables extrapolation for long-dated instruments

#### Main Interface (`curve.py`)
High-level `SOFRCurve` class:
```python
# Load from CSV
sofr_curve = SOFRCurve.from_csv('tests/data/sofr_curve.csv')

# Get discount factors
df = sofr_curve.get_discount_factor(datetime(2026, 4, 17))

# Get forward rates
forward_rate = sofr_curve.get_forward_rate(
    start_date=datetime(2026, 1, 1),
    end_date=datetime(2026, 4, 1),
    compounding=ql.Compounded
)

# Create SOFR index linked to curve
sofr_index = sofr_curve.create_sofr_index()
```

### Integration with Floating Rate Bonds

The `FloatingRateBond` class accepts an optional `sofr_curve` parameter for market-based forward projections:

```python
from securities_analytics.bonds.floating_rate import FloatingRateBond
from securities_analytics.curves.sofr import SOFRCurve

# Load market curve
sofr_curve = SOFRCurve.from_csv('sofr_data.csv')

# Create floating rate bond with market curve
bond = FloatingRateBond(
    face_value=1000000,
    maturity_date=datetime(2030, 6, 15),
    floating_index=ql.Sofr(),
    spread=0.0125,  # 125 bps
    settlement_date=datetime.now(),
    day_count="Actual/360",
    settlement_days=2,
    frequency=4,
    sofr_curve=sofr_curve  # Market-based projections
)

# Get projected cashflows using forward rates
cashflows = bond.get_projected_cashflows()

# Calculate spread duration
spread_duration = bond.get_spread_duration()
```

### Key Features

1. **Forward Rate Projections**: Uses bootstrapped curve for accurate forward rate calculations
2. **Spread Duration**: Calculates sensitivity to spread changes
3. **Cashflow Projections**: Projects floating cashflows using market-implied forward rates
4. **Flexible Data Loading**: Supports CSV files and custom data formats

## QuantLib Reference

For comprehensive QuantLib documentation and examples covering all the patterns used in this service, refer to our [QuantLib Reference Guide](quantlib-reference.md). This guide contains detailed examples for:

- **Bonds**: Fixed rate, floating rate, callable, amortizing, and zero-coupon bonds
- **Indexes**: IBOR, overnight, and swap indexes with fixing management
- **Pricing Engines**: Bond engines, option engines, and model-specific engines
- **Term Structures**: Yield curves, volatility surfaces, and credit curves
- **Cash Flows**: Coupons, legs, and cash flow analysis functions
- **Practical Examples**: Complete pricing workflows and curve construction

The reference guide is particularly useful for:
1. Understanding QuantLib parameter names and signatures
2. Finding examples for specific bond structures
3. Learning about different interpolation methods
4. Exploring advanced analytics and risk measures

## Future Enhancements

1. **Option-Adjusted Spread (OAS)**: Monte Carlo pricing for callables
2. **Key Rate Durations**: Sensitivity to specific curve points
3. **Credit-Adjusted Pricing**: Incorporate credit curves
4. **Real-time Updates**: Streaming price integration
5. **Historical Analysis**: Backtesting capabilities