# Fixed Income Analytics Service - Repository Overview

## Project Summary

This repository contains a Python-based fixed income analytics service built on top of QuantLib, specifically designed for calculating bond analytics, spreads, and option-adjusted measures. The project is structured as a modular Python package that provides comprehensive bond pricing and analytics capabilities.

**Package Name**: `securities-analytics`  
**Version**: 0.1.0  
**Python Requirements**: Python 3.11+  
**Primary Dependencies**: QuantLib, pandas, fire, httpx, loguru, orjson

## Architecture Overview

### Core Structure

```
fixed-income-analytics-service/
├── securities_analytics/         # Main package directory
│   ├── bonds/                   # Bond-related modules
│   │   ├── base/               # Abstract base classes
│   │   ├── fixed_rate_bullets/ # Fixed rate bond implementations
│   │   └── analytics/          # Spread and analytics calculations
│   ├── models/                 # Financial models (Hull-White)
│   └── utils/                  # Utility functions
│       ├── data_imports/       # Curve and data loading
│       └── dates/              # Date manipulation utilities
└── tests/                      # Test suite with sample data
```

## Key Components

### 1. Bond Classes (`securities_analytics/bonds/`)

#### Base Classes
- **`AbstractBond`** (`base/bond.py`): Abstract base class defining common bond parameters
  - Handles face value, coupon rate, settlement, day count conventions
  - Provides day count mapping (ACT365, ACT360, 30/360, ACTACT)
  - Sets QuantLib evaluation date

- **`BondScheduleGenerator`** (`base/scheduler.py`): Abstract interface for generating bond schedules

#### Fixed Rate Bond Implementations

- **`FixedRateQLBond`** (`fixed_rate_bullets/vanilla/bond.py`): Standard fixed-rate bond
  - Supports both callable and non-callable bonds
  - Calculates YTM, YTC, YTW (yield to worst)
  - Provides duration and convexity calculations
  - Handles clean/dirty price conversions
  - Optional call feature support with separate schedule

- **`CallableFixedRateQLBond`** (`fixed_rate_bullets/callable/bond.py`): Advanced callable bond implementation
  - Uses QuantLib's CallableFixedRateBond with proper callability schedule
  - Supports Hull-White model pricing engine for option valuation
  - Calculates OAS (Option-Adjusted Spread)
  - Provides effective duration and convexity (option-adjusted)
  - Monthly call frequency from first call date to maturity

- **`FixedRateBondScheduleGenerator`** (`fixed_rate_bullets/schedulers/scheduler.py`): 
  - Generates payment schedules for fixed-rate bonds
  - Supports various frequencies (annual, semiannual, quarterly, monthly)
  - Handles business day conventions and calendars

### 2. Analytics (`securities_analytics/bonds/analytics/`)

- **`BondSpreadCalculator`** (`spreads.py`): Comprehensive spread calculations
  - **G-Spread**: Linear interpolation on treasury curve at exact time-to-workout
  - **Spread-to-Benchmark**: Uses custom "round-down" logic for OTR tenor selection
  - Supports both price-from-spread and spread-from-price calculations
  - Configurable workout date logic (earliest call vs maturity)
  - Special logic for 10-year bonds:
    - ≥7.0 years → use 10-year treasury
    - ≥3.0 years → use 5-year treasury
    - ≥2.0 years → use 3-year treasury
    - <2.0 years → use 2-year treasury

### 3. Financial Models (`securities_analytics/models/`)

- **Hull-White 1-Factor Model** (`hullwhite_1f.py`):
  - Calibrates Hull-White model to swaption volatilities
  - Uses Jamshidian engine for swaption pricing
  - Levenberg-Marquardt optimization for parameter fitting
  - Returns calibrated mean reversion (a) and volatility (σ) parameters
  - Integrates with SOFR curve for term structure

### 4. Utilities (`securities_analytics/utils/`)

#### Data Imports (`data_imports/`)
- **`curves.py`**: 
  - `load_and_return_sofr_curve()`: Loads SOFR curve from CSV, returns YieldTermStructureHandle
  - `load_and_return_active_treasury_curve()`: Loads treasury curve, returns dict of tenor→yield
  - Handles date parsing and curve construction with proper interpolation

- **`utils.py`**: 
  - `tenor_to_ql_period()`: Converts tenor strings (e.g., "3M", "5Y") to QuantLib periods
  - Supports ON (overnight), days, weeks, months, and years

#### Date Utilities (`dates/`)
- **`utils.py`**:
  - `to_ql_date()`: Python datetime → QuantLib Date conversion
  - `ql_to_py_date()`: QuantLib Date → Python datetime conversion
  - `generate_list_of_ql_dates()`: Creates sequences of dates with various frequencies
  - `year_difference_rounded()`: Calculates rounded year differences

## Testing Infrastructure

### Test Structure
```
tests/
├── bonds/
│   └── fixed_rate_bullets/
│       ├── test_vanilla.py      # Tests for standard fixed-rate bonds
│       └── test_callable.py     # Tests for callable bonds
├── models/
│   └── test_hullwhite_1f.py    # Hull-White model calibration tests
├── utils/
│   └── data_imports/           # Data import tests
└── data/                       # Sample market data
    ├── active_treasury_curve.csv
    ├── sofr_curve.csv
    └── swaption_vols.csv
```

### Sample Data Files
- **`active_treasury_curve.csv`**: US Treasury curve data with tenors from 1M to 30Y
- **`sofr_curve.csv`**: SOFR forward curve for discounting
- **`swaption_vols.csv`**: Swaption volatility matrix for Hull-White calibration

## Development Setup

### Dependencies
- **Core**: QuantLib (1.37+), pandas, fire, orjson, httpx, loguru
- **Development**: black (formatter), ruff (linter), isort (import sorter), pytest
- **Package Management**: Poetry (2.0+)

### Code Style
- Line length: 100 characters
- Python 3.11 target
- Black formatting with double quotes
- Isort with black profile
- Ruff linting with extended rules (I, F, E, W)

## Key Features

1. **Comprehensive Bond Analytics**
   - Multiple yield calculations (YTM, YTC, YTW)
   - Duration and convexity (both standard and option-adjusted)
   - Clean/dirty price conversions
   - Accrued interest calculations

2. **Advanced Spread Calculations**
   - G-spread with linear interpolation
   - Benchmark spread with custom tenor selection logic
   - Bi-directional calculations (price↔spread)

3. **Option Valuation**
   - Hull-White model integration
   - OAS calculations for callable bonds
   - Effective duration/convexity accounting for embedded options

4. **Flexible Architecture**
   - Abstract base classes for extensibility
   - Modular design for easy component replacement
   - Clear separation of concerns (bonds, models, analytics, utilities)

## Usage Patterns

### Basic Fixed-Rate Bond
```python
from securities_analytics.bonds.fixed_rate_bullets.vanilla.bond import FixedRateQLBond
from datetime import datetime

bond = FixedRateQLBond(
    face_value=100,
    maturity_date=datetime(2032, 8, 19),
    annual_coupon_rate=0.05,
    settlement_date=datetime(2025, 4, 4),
    day_count="ACT365",
    settlement_days=2
)

ytm = bond.yield_to_maturity(market_clean_price=98.5)
```

### Callable Bond with OAS
```python
from securities_analytics.bonds.fixed_rate_bullets.callable.bond import CallableFixedRateQLBond

callable_bond = CallableFixedRateQLBond(
    face_value=100,
    maturity_date=datetime(2033, 1, 25),
    annual_coupon_rate=0.02963,
    settlement_date=datetime.now(),
    day_count="D30360",
    settlement_days=2,
    next_call_date=datetime(2032, 1, 25),
    call_price=100,
    ts_handle=sofr_curve_handle
)

oas = callable_bond.calculate_OAS(clean_market_price=87)
```

### Spread Calculations
```python
from securities_analytics.bonds.analytics.spreads import BondSpreadCalculator

spread_calc = BondSpreadCalculator(
    bond=fixed_bond,
    treasury_curve=treasury_curve,
    original_benchmark_tenor=10,
    use_earliest_call=True
)

spreads = spread_calc.spread_from_price(market_clean_price=98.567)
```

## Future Extensions

The modular architecture supports easy extension for:
- Additional bond types (floating rate, inflation-linked)
- More spread calculation methodologies
- Alternative interest rate models
- Real-time market data integration
- REST API endpoints (httpx is already included)
- Additional analytics (key rate durations, scenario analysis)

## Notes for Developers

1. All QuantLib dates are handled through utility functions for consistency
2. The evaluation date is automatically set in AbstractBond initialization
3. Day count conventions are mapped in the base class
4. Test data files use CSV format for easy modification
5. The project uses Poetry for dependency management - run `poetry install` to set up
6. Run tests with `pytest` after installation
7. Code formatting: `black .` and linting: `ruff check .`