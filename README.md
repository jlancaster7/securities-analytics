# Fixed Income Analytics Service

A comprehensive fixed income analytics service built on top of QuantLib, designed for production use in pricing and analyzing bonds. The service includes full support for fix-to-float bonds and a complete market data abstraction layer.

## 🎯 Key Features

- **Multiple Bond Types**: Fixed rate, floating rate, and fix-to-float bonds
- **Comprehensive Analytics**: Price, yield, duration, convexity, DV01, and spread calculations
- **Market Data Framework**: Flexible data provider interface with mock data for testing
- **Production Ready**: Type hints, error handling, caching, and extensive test coverage
- **QuantLib Integration**: Built on the industry-standard QuantLib library

## 📋 Recent Enhancements

### Fix-to-Float Bond Support
- Complete implementation for bonds that transition from fixed to floating rate
- Separate payment schedules for fixed and floating periods
- Support for different payment frequencies (e.g., semiannual fixed, quarterly floating)
- Integration with existing spread calculator
- Callable fix-to-float bond support

### Market Data Service
- Abstract data provider interface for easy integration with various data sources
- Mock data provider generating realistic test data
- Built-in caching for performance optimization
- QuantLib yield curve handle generation
- Support for treasury curves, SOFR curves, and credit spreads

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

## 📁 Project Structure

```
securities_analytics/
├── bonds/
│   ├── fixed_rate/         # Fixed rate bond implementation
│   ├── fix_to_float/       # Fix-to-float bond implementation
│   └── analytics/          # Spread and analytics calculations
├── market_data/            # Market data service framework
│   ├── data_models.py      # Data structures
│   └── service.py          # Service and provider classes
├── utils/                  # Utility functions
└── tests/                  # Comprehensive test suite
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=securities_analytics

# Run specific test modules
poetry run pytest tests/bonds/fix_to_float/
poetry run pytest tests/market_data/
```

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

- [Project Summary](PROJECT_SUMMARY.md) - Comprehensive overview of all features
- [Integration Guide](INTEGRATION_GUIDE.md) - Step-by-step guide for data integration
- [Fix-to-Float Documentation](FIX_TO_FLOAT_DOCUMENTATION.md) - Detailed fix-to-float bond guide
- [Next Steps](NEXT_STEPS.md) - Roadmap and enhancement ideas

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is proprietary. All rights reserved.

## 🙏 Acknowledgments

- Built on [QuantLib](https://www.quantlib.org/) - The open-source library for quantitative finance
- Inspired by industry best practices in fixed income analytics

## ⚡ Performance Tips

1. **Use Caching**: The MarketDataService includes built-in caching
2. **Batch Operations**: Process multiple bonds together to reuse curves
3. **Parallel Processing**: Use multiprocessing for large portfolios

## 🐛 Known Issues

- Some fix-to-float integration tests are skipped due to date handling complexities
- These can be resolved by ensuring proper evaluation date setup in production

## 📧 Support

For questions or issues:
1. Check the documentation
2. Review the test examples
3. Open an issue with a minimal reproducible example

---

# 🚀 Happy Bond Pricing!