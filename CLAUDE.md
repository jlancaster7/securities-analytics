# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
```bash
# Run all tests
poetry run pytest

# Run specific test module
poetry run pytest tests/bonds/fix_to_float/
poetry run pytest tests/market_data/

# Run with coverage report
poetry run pytest --cov=securities_analytics

# Run a single test
poetry run pytest tests/bonds/fix_to_float/test_bond.py::test_fix_to_float_bond_creation
```

### Code Quality
```bash
# Format code with Black (100 char line length)
poetry run black .

# Lint with Ruff
poetry run ruff check .

# Sort imports
poetry run isort .

# Run all formatting and linting
poetry run black . && poetry run isort . && poetry run ruff check .
```

### Dependencies
```bash
# Install all dependencies
poetry install

# Add a new dependency
poetry add <package-name>

# Update dependencies
poetry update
```

## Architecture Overview

### Bond Class Hierarchy
The system uses an abstract base class pattern where all bonds inherit from `AbstractBond`:
- `AbstractBond` provides day count mapping, settlement handling, and QuantLib setup
- `FixedRateQLBond` implements standard fixed-rate bonds with optional callable features
- `FixToFloatBond` uses a composite approach, creating separate fixed and floating legs

### Fix-to-Float Implementation
Fix-to-float bonds are implemented using QuantLib's composite bond approach:
1. `FixToFloatScheduleGenerator` creates two separate schedules (fixed period and floating period)
2. Fixed leg uses `ql.FixedRateLeg` with semiannual payments
3. Floating leg uses `ql.OvernightLeg` (not `ql.IborLeg`) for SOFR-based payments
4. The bond combines both legs into a single `ql.Bond` object

### Market Data Pattern
The system uses a provider pattern for market data abstraction:
- `DataProvider` is an abstract interface defining required data methods
- `MockDataProvider` generates realistic test data (~30-40 bonds, 20% fix-to-float)
- `MarketDataService` wraps providers and adds caching (60-second TTL)
- Custom providers implement the interface to connect real data sources

### Spread Calculations
`BondSpreadCalculator` accepts any `AbstractBond` type and calculates:
- G-spread: Linear interpolation of treasury curve at bond's maturity
- Benchmark spread: Uses tenor step-down rules (10Y → 5Y → 2Y as bond ages)
- Z-spread: Parallel shift to yield curve using `ql.BondFunctions.zSpread`

## Critical Technical Details

### QuantLib Evaluation Date
**Always set the evaluation date before any pricing operations:**
```python
ql.Settings.instance().evaluationDate = ql.Date(15, 3, 2024)
```
This affects all date-based calculations and must be consistent across operations.

### SOFR Index Creation
For fix-to-float bonds, create SOFR index with proper curve handle:
```python
sofr_index = ql.OvernightIndex(
    "SOFR", 1, ql.USDCurrency(),
    ql.UnitedStates(ql.UnitedStates.GovernmentBond),
    ql.Actual360(), sofr_curve_handle
)
```

### Yield Curve Handles
Spread calculations require `YieldTermStructureHandle`:
```python
curve = ql.FlatForward(2, ql.TARGET(), 0.05, ql.Actual360())
handle = ql.YieldTermStructureHandle(curve)
```

## Testing Notes

### Test Organization
- `tests/bonds/fix_to_float/`: Fix-to-float bond tests (22 tests)
- `tests/market_data/`: Market data service tests (45 tests)
- `tests/bonds/fixed_rate_bullets/`: Fixed rate bond tests
- `tests/bonds/analytics/`: Spread calculation tests

### Known Issues
- 3 fix-to-float integration tests are skipped due to date handling complexities
- These tests involve edge cases around switch dates and can be resolved with proper evaluation date setup

### Mock Data Characteristics
- Treasury curve: Upward sloping from 3M to 30Y
- SOFR curve: 5-10bps below treasury rates
- Credit spreads: Vary by rating (AAA: 20-30bps, BBB: 100-150bps)
- Bond universe: ~30-40 bonds across sectors, 20% are fix-to-float

## Common Patterns

### Creating a Fix-to-Float Bond
```python
bond = FixToFloatBond(
    face_value=1000000,
    maturity_date=datetime(2034, 3, 15),
    switch_date=datetime(2027, 3, 15),  # 3 years fixed
    fixed_rate=0.045,                   # 4.5% fixed
    floating_spread=0.01,               # SOFR + 100bps
    settlement_date=datetime(2024, 3, 15),
    floating_index=sofr_index,
    fixed_frequency=2,                  # Semiannual
    floating_frequency=4,               # Quarterly
)
```

### Calculating Spreads
```python
calculator = BondSpreadCalculator(
    bond=bond,
    market_price=98.5,
    treasury_curve=market_service.get_treasury_curve(),
    spread_curve_handle=treasury_curve_handle,
)
g_spread = calculator.g_spread()
z_spread = calculator.z_spread()
```