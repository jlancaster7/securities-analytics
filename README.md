# Fixed Income Analytics Service

A comprehensive fixed income analytics service built on top of QuantLib, designed for production use in pricing and analyzing bonds. The service includes full support for fix-to-float bonds and a complete market data abstraction layer.

## 🎯 Key Features

- **Multiple Bond Types**: Fixed rate, floating rate, and fix-to-float bonds
- **Comprehensive Analytics**: Price, yield, duration, convexity, DV01, and spread calculations
- **Market Data Framework**: Flexible data provider interface with mock data for testing
- **Production Ready**: Type hints, error handling, caching, and extensive test coverage
- **QuantLib Integration**: Built on the industry-standard QuantLib library

## 📁 Architecture Overview

```
securities_analytics/
├── bonds/                      # Bond implementations and analytics
│   ├── base/                   # Abstract base classes
│   │   ├── bond.py            # AbstractBond base class
│   │   └── scheduler.py       # Schedule generation interface
│   ├── fixed_rate_bullets/     # Fixed rate bond implementations
│   │   └── vanilla/           # Standard fixed-rate bonds
│   ├── fix_to_float/          # Fix-to-float bond implementation
│   │   ├── bond.py            # FixToFloatBond class
│   │   └── schedulers/        # Dual schedule generation
│   └── analytics/             # Analytics calculations
│       └── spreads.py         # G-spread, benchmark spread, z-spread
├── market_data/               # Market data service framework
│   ├── data_models.py         # Rating, Sector, BondReference, etc.
│   └── service.py             # DataProvider interface & MarketDataService
├── models/                    # Financial models
│   └── hull_white/            # Hull-White model implementation
└── utils/                     # Utility functions
    ├── data_imports/          # Curve and data loading utilities
    └── dates/                 # Date manipulation helpers
```

## 🚀 Quick Start

### Installation

1. **Install Python 3.8+**
   ```bash
   python --version  # Verify installation
   ```

2. **Install Poetry**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Clone and Install Dependencies**
   ```bash
   git clone <repository-url>
   cd fixed-income-analytics-service
   poetry install
   ```

### Basic Usage

```python
from datetime import datetime
import QuantLib as ql
from securities_analytics.market_data import MarketDataService
from securities_analytics.bonds.fix_to_float.bond import FixToFloatBond

# Initialize market data service
market_service = MarketDataService()

# Get market curves
sofr_handle = market_service.get_sofr_curve_handle()
treasury_curve = market_service.get_treasury_curve()

# Create SOFR index
sofr_index = ql.OvernightIndex(
    "SOFR", 1, ql.USDCurrency(),
    ql.UnitedStates(ql.UnitedStates.GovernmentBond),
    ql.Actual360(), sofr_handle
)

# Create fix-to-float bond
bond = FixToFloatBond(
    face_value=1000000,
    maturity_date=datetime(2034, 3, 15),
    switch_date=datetime(2027, 3, 15),
    fixed_rate=0.045,
    floating_spread=0.01,
    settlement_date=datetime(2024, 3, 15),
    floating_index=sofr_index,
)

# Calculate analytics
clean_price = bond.clean_price(sofr_handle)
duration = bond.duration(sofr_handle)
print(f"Price: {clean_price:.3f}, Duration: {duration:.2f}")
```

## 📋 Core Components

### Bond Classes

#### AbstractBond
Base class providing common bond functionality:
- Day count convention mapping (ACT365, ACT360, 30/360, ACTACT)
- Settlement date handling
- QuantLib integration setup

#### FixedRateQLBond
Standard fixed-rate bond implementation:
- Yield calculations (YTM, YTC, YTW)
- Duration and convexity
- Clean/dirty price conversions
- Optional callable features

#### FixToFloatBond
Bonds that transition from fixed to floating rate:
- Dual schedule generation (fixed and floating periods)
- Support for different payment frequencies
- SOFR-based floating legs
- Callable fix-to-float support

### Analytics

#### BondSpreadCalculator
Calculates various spread measures:
- **G-Spread**: Linear interpolation of treasury curve
- **Benchmark Spread**: Using tenor step-down rules
- **Z-Spread**: Parallel shift to discount curve
- Support for callable bonds using yield-to-worst

### Market Data Service

#### DataProvider Interface
Abstract interface for data sources:
```python
class DataProvider(ABC):
    def get_treasury_curve(self) -> Dict[float, float]
    def get_sofr_curve(self) -> Dict[float, float]
    def get_bond_quote(self, cusip: str) -> MarketQuote
    def get_bond_reference(self, cusip: str) -> BondReference
```

#### MockDataProvider
Realistic test data generation:
- Treasury curves with proper term structure
- SOFR curves (5-10bps below treasuries)
- Credit spreads by rating/sector
- ~30-40 bond universe with 20% fix-to-float

## 🧪 Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=securities_analytics

# Run specific test modules
poetry run pytest tests/bonds/fix_to_float/
poetry run pytest tests/market_data/
```

### Test Coverage
- **81 total tests** (78 passing, 3 skipped)
- Fix-to-float bonds: 22 tests
- Market data service: 45 tests
- Existing functionality: 14 tests

## 📊 Market Data Integration

To integrate with your data sources, implement the `DataProvider` interface:

```python
from securities_analytics.market_data import DataProvider

class YourDataProvider(DataProvider):
    def get_treasury_curve(self) -> Dict[float, float]:
        # Return your treasury curve data
        pass
    
    def get_bond_quote(self, cusip: str) -> MarketQuote:
        # Return market quote for bond
        pass
    
    # Implement other required methods...

# Use your provider
market_service = MarketDataService(provider=YourDataProvider())
```

## 📚 Documentation

- [Technical Guide](TECHNICAL_GUIDE.md) - Detailed implementation documentation
- [Integration Guide](INTEGRATION_GUIDE.md) - Step-by-step data integration
- [Roadmap](ROADMAP.md) - Future enhancements and project direction

## ⚡ Performance Tips

1. **Use Caching**: The MarketDataService includes built-in caching
2. **Batch Operations**: Process multiple bonds together to reuse curves
3. **Parallel Processing**: Use multiprocessing for large portfolios

## 🛠️ Development

### Dependencies
- **QuantLib-Python** (1.35): Core pricing library
- **pandas** (2.2.3): Data manipulation
- **httpx** (0.28.1): HTTP client for data fetching
- **loguru** (0.7.3): Logging
- **orjson** (3.10.12): Fast JSON parsing
- **quantlib-stubs** (1.35.2): Type hints for QuantLib

### Code Style
- Type hints throughout for better IDE support
- Comprehensive docstrings
- Following PEP 8 guidelines
- Extensive error handling

## 🐛 Known Issues

- Some fix-to-float integration tests are skipped due to date handling complexities
- These can be resolved by ensuring proper evaluation date setup in production

## 📝 License

This project is proprietary. All rights reserved.

## 🙏 Acknowledgments

- Built on [QuantLib](https://www.quantlib.org/) - The open-source library for quantitative finance
- Inspired by industry best practices in fixed income analytics

---

# 🚀 Happy Bond Pricing!