# Fix-to-Float Bond Implementation Documentation

## Overview

This document describes the implementation of fix-to-float bonds in the securities analytics service. Fix-to-float bonds are hybrid instruments that pay a fixed coupon rate for an initial period, then switch to a floating rate (typically based on an index like SOFR plus a spread) for the remainder of their life.

## Architecture

### Module Structure
```
securities_analytics/bonds/fix_to_float/
├── __init__.py
├── bond.py                    # Main FixToFloatBond class
└── schedulers/
    ├── __init__.py
    └── scheduler.py           # FixToFloatScheduleGenerator
```

### Class Hierarchy
```
AbstractBond (base class)
    └── FixToFloatBond
            ├── Uses: FixToFloatScheduleGenerator
            └── Compatible with: BondSpreadCalculator
```

## Key Components

### 1. FixToFloatScheduleGenerator

Generates separate schedules for fixed and floating periods:

```python
from datetime import datetime
from securities_analytics.bonds.fix_to_float.schedulers.scheduler import FixToFloatScheduleGenerator
import QuantLib as ql

scheduler = FixToFloatScheduleGenerator(
    issue_date=datetime(2024, 1, 15),
    switch_date=datetime(2027, 1, 15),    # 3 years fixed
    maturity_date=datetime(2034, 1, 15),   # 10 years total
    fixed_frequency=2,      # Semiannual during fixed period
    floating_frequency=4,   # Quarterly during floating period
    calendar=ql.UnitedStates(ql.UnitedStates.GovernmentBond),
    business_day_convention=ql.Following,
)

# Generate individual schedules
fixed_schedule = scheduler.generate_fixed_schedule()
floating_schedule = scheduler.generate_floating_schedule()
combined_schedule = scheduler.generate()  # Full bond schedule
```

### 2. FixToFloatBond

The main bond class that combines fixed and floating cashflows:

```python
from securities_analytics.bonds.fix_to_float.bond import FixToFloatBond
import QuantLib as ql

# Create SOFR index
sofr_curve_handle = ql.YieldTermStructureHandle(...)  # Your curve
sofr_index = ql.OvernightIndex(
    "SOFR",
    1,  # fixing days
    ql.USDCurrency(),
    ql.UnitedStates(ql.UnitedStates.GovernmentBond),
    ql.Actual360(),
    sofr_curve_handle
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

## Usage Examples

### Basic Pricing and Analytics

```python
# Price the bond
clean_price = bond.clean_price(yield_curve_handle)
dirty_price = bond.dirty_price(yield_curve_handle)

# Calculate yield (uses forward curve for floating cashflows)
ytm = bond.yield_to_maturity(market_clean_price=98.5, yield_curve_handle)

# Risk measures
duration = bond.duration(yield_curve_handle)
convexity = bond.convexity(yield_curve_handle)

# Spread calculations
z_spread = bond.spread_to_curve(market_clean_price=98.5, yield_curve_handle)
```

### Callable Fix-to-Float Bonds

```python
# Create callable fix-to-float bond
callable_bond = FixToFloatBond(
    face_value=100,
    maturity_date=datetime(2034, 2, 15),
    switch_date=datetime(2027, 2, 15),
    fixed_rate=0.05,           # Higher coupon makes it callable
    floating_spread=0.015,
    settlement_date=datetime(2024, 2, 15),
    day_count="ACT360",
    settlement_days=2,
    floating_index=sofr_index,
    next_call_date=datetime(2027, 2, 15),  # Callable at switch
    call_price=100,
)

# Calculate yield to call
ytc = callable_bond.yield_to_call(market_clean_price=101.5)
```

### Integration with BondSpreadCalculator

The fix-to-float bonds are fully integrated with the existing spread calculator:

```python
from securities_analytics.bonds.analytics.spreads import BondSpreadCalculator

# Load treasury curve
treasury_curve = {
    2: 0.04,    # 2-year: 4%
    5: 0.042,   # 5-year: 4.2%
    10: 0.045,  # 10-year: 4.5%
    # ... more points
}

# Create spread calculator
calculator = BondSpreadCalculator(
    bond=bond,  # Can be FixToFloatBond
    treasury_curve=treasury_curve,
    original_benchmark_tenor=10,
    use_earliest_call=False
)

# Calculate spreads
market_price = 97.5
spreads = calculator.spread_from_price(market_price)
print(f"G-Spread: {spreads['g_spread'] * 10000:.1f} bps")
print(f"Benchmark Spread: {spreads['spread_to_benchmark'] * 10000:.1f} bps")

# Reverse calculation: price from spread
target_spread = 0.015  # 150 bps
price = calculator.price_from_spread(target_spread, which_spread="benchmark")
```

## Implementation Details

### Cashflow Generation

Fix-to-float bonds use QuantLib's leg builders to create cashflows:

1. **Fixed Period**: Uses `ql.FixedRateLeg` for the initial fixed-rate period
2. **Floating Period**: Uses `ql.OvernightLeg` for SOFR-based floating payments
3. **Combined Bond**: Merges cashflows into a single `ql.Bond` object

### Floating Rate Indices

The implementation supports overnight indices (like SOFR):

```python
# SOFR index setup
sofr_index = ql.OvernightIndex(
    "SOFR",
    1,  # fixing days
    ql.USDCurrency(),
    ql.UnitedStates(ql.UnitedStates.GovernmentBond),
    ql.Actual360(),
    yield_curve_handle
)
```

For other indices (like term SOFR or LIBOR replacements), you can use:

```python
# Term rate index
term_index = ql.IborIndex(
    "TermSOFR",
    ql.Period("3M"),
    2,  # settlement days
    ql.USDCurrency(),
    ql.UnitedStates(ql.UnitedStates.GovernmentBond),
    ql.ModifiedFollowing,
    False,  # end of month
    ql.Actual360(),
    yield_curve_handle
)
```

### Analytics Considerations

1. **Yield Calculations**: YTM uses the forward curve to project floating cashflows
2. **Duration**: Reflects both fixed and floating period risks
3. **Convexity**: Accounts for the changing nature of cashflows
4. **Spreads**: Z-spread calculation works seamlessly with the hybrid structure

## Testing

The implementation includes comprehensive tests:

### Unit Tests
- `test_scheduler.py`: Tests schedule generation for various scenarios
- `test_bond.py`: Tests bond creation, pricing, and analytics

### Integration Tests
- `test_spread_integration.py`: Tests compatibility with BondSpreadCalculator

### Test Coverage
- Schedule generation with different frequencies
- Business day adjustments
- Pricing and yield calculations
- Duration and convexity
- Spread calculations
- Callable bonds
- Edge cases (very short fixed periods, zero spreads)

## Best Practices

1. **Always provide a yield curve**: Fix-to-float bonds require a curve for floating rate projections
2. **Set evaluation date**: Ensure QuantLib's evaluation date is set appropriately
3. **Use appropriate indices**: SOFR for USD, €STR for EUR, etc.
4. **Handle callable features**: Many fix-to-float bonds are callable at the switch date

## Limitations and Future Enhancements

### Current Limitations
1. Simplified yield-to-call implementation for callable fix-to-float bonds
2. No support for caps/floors on the floating rate
3. No support for step-up coupons or other exotic features

### Potential Enhancements
1. Support for floating rate caps and floors
2. More sophisticated callable bond pricing
3. Support for averaging methods (arithmetic vs compound) for overnight rates
4. Integration with real-time market data feeds
5. Support for other floating rate conventions

## Example Workflow

Here's a complete example workflow:

```python
from datetime import datetime
import QuantLib as ql
from securities_analytics.bonds.fix_to_float.bond import FixToFloatBond
from securities_analytics.bonds.analytics.spreads import BondSpreadCalculator
from securities_analytics.utils.data_imports.curves import (
    load_and_return_sofr_curve,
    load_and_return_active_treasury_curve
)

# 1. Set up market data
ql.Settings.instance().evaluationDate = ql.Date(15, 2, 2024)
sofr_curve = load_and_return_sofr_curve("path/to/sofr_curve.csv")
treasury_curve = load_and_return_active_treasury_curve("path/to/treasury_curve.csv")

# 2. Create SOFR index
sofr_index = ql.OvernightIndex(
    "SOFR", 1, ql.USDCurrency(),
    ql.UnitedStates(ql.UnitedStates.GovernmentBond),
    ql.Actual360(), sofr_curve
)

# 3. Create fix-to-float bond
bond = FixToFloatBond(
    face_value=1000000,  # $1MM face
    maturity_date=datetime(2034, 3, 15),
    switch_date=datetime(2027, 3, 15),
    fixed_rate=0.0425,  # 4.25% fixed
    floating_spread=0.0095,  # SOFR + 95bps
    settlement_date=datetime(2024, 3, 15),
    day_count="ACT360",
    settlement_days=2,
    floating_index=sofr_index,
)

# 4. Price and analyze
clean_price = bond.clean_price(sofr_curve)
print(f"Clean Price: {clean_price:.3f}")

duration = bond.duration(sofr_curve)
print(f"Modified Duration: {duration:.2f}")

# 5. Calculate spreads
calculator = BondSpreadCalculator(
    bond=bond,
    treasury_curve=treasury_curve,
    original_benchmark_tenor=10,
)

market_price = 98.75
spreads = calculator.spread_from_price(market_price)
print(f"G-Spread: {spreads['g_spread'] * 10000:.1f} bps")
print(f"Spread to Benchmark: {spreads['spread_to_benchmark'] * 10000:.1f} bps")
```

## Conclusion

The fix-to-float bond implementation provides a robust, production-ready solution for analyzing these hybrid instruments. It integrates seamlessly with the existing analytics framework while maintaining the flexibility to handle various market conventions and structural features.