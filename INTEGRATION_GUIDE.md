# Integration Guide - Connecting Your Work Data Sources

This guide provides step-by-step instructions for integrating your work data sources with the fixed income analytics service.

## Quick Start

### 1. Create Your Data Provider

Create a new file `work_data_provider.py`:

```python
from datetime import datetime
from typing import Dict, Optional
from securities_analytics.market_data import (
    DataProvider, BondReference, MarketQuote, CreditCurve,
    Rating, Sector, BondType
)

class WorkDataProvider(DataProvider):
    def __init__(self, connection_config):
        """
        Initialize with your work database connections.
        
        Args:
            connection_config: Dict with connection details for:
                - price_db: Historical prices/yields database
                - security_master: Bond reference database  
                - curve_service: Treasury/SOFR curve service
        """
        self.price_db = PriceDatabase(connection_config['price_db'])
        self.sec_master = SecurityMaster(connection_config['security_master'])
        self.curve_service = CurveService(connection_config['curve_service'])
    
    def get_treasury_curve(self) -> Dict[float, float]:
        """Get current treasury curve from your curve service."""
        curve_data = self.curve_service.get_curve('USD_TREASURY', datetime.now())
        
        # Convert to expected format: {tenor_in_years: yield}
        return {
            0.25: curve_data['3M'],
            0.5: curve_data['6M'],
            1.0: curve_data['1Y'],
            2.0: curve_data['2Y'],
            3.0: curve_data['3Y'],
            5.0: curve_data['5Y'],
            7.0: curve_data['7Y'],
            10.0: curve_data['10Y'],
            20.0: curve_data['20Y'],
            30.0: curve_data['30Y'],
        }
    
    def get_sofr_curve(self) -> Dict[float, float]:
        """Get current SOFR curve."""
        curve_data = self.curve_service.get_curve('USD_SOFR', datetime.now())
        return self._convert_curve_format(curve_data)
    
    def get_sofr_curve_data(self) -> 'SOFRCurveData':
        """Get SOFR curve data for advanced analytics."""
        from securities_analytics.curves.sofr import SOFRCurveData, SOFRCurvePoint, TenorUnit
        
        # Get raw curve data from your source
        raw_data = self.curve_service.get_detailed_curve('USD_SOFR', datetime.now())
        
        # Convert to SOFRCurvePoint objects
        points = []
        for tenor, rate, cusip in raw_data:
            # Parse tenor string (e.g., "3M", "2Y")
            value, unit = self._parse_tenor(tenor)
            point = SOFRCurvePoint(
                tenor_string=tenor,
                tenor_value=value,
                tenor_unit=unit,
                rate=rate / 100.0,  # Convert from percent to decimal
                description=f"SOFR {tenor}",
                cusip=cusip,
                source="INTERNAL"
            )
            points.append(point)
        
        return SOFRCurveData(
            curve_date=datetime.now(),
            points=points
        )
    
    def get_bond_quote(self, cusip: str) -> MarketQuote:
        """Get latest market quote from price database."""
        price_data = self.price_db.get_latest_quote(cusip)
        
        return MarketQuote(
            cusip=cusip,
            timestamp=price_data['timestamp'],
            bid_price=price_data['bid_price'],
            ask_price=price_data['ask_price'],
            mid_price=price_data['mid_price'],
            last_price=price_data.get('last_price'),
            bid_yield=price_data.get('bid_yield'),
            ask_yield=price_data.get('ask_yield'),
            mid_yield=price_data.get('mid_yield'),
            volume=price_data.get('volume'),
            trade_count=price_data.get('trade_count'),
            source=price_data.get('source', 'INTERNAL'),
            quality=price_data.get('quality', 'INDICATIVE')
        )
    
    def get_bond_reference(self, cusip: str) -> BondReference:
        """Get bond reference data from security master."""
        bond_data = self.sec_master.get_bond_details(cusip)
        
        # Determine bond type
        bond_type = self._determine_bond_type(bond_data)
        
        # Map credit ratings
        rating_sp = self._map_rating(bond_data.get('sp_rating'))
        rating_moody = self._map_rating(bond_data.get('moodys_rating'))
        rating_fitch = self._map_rating(bond_data.get('fitch_rating'))
        
        return BondReference(
            cusip=cusip,
            isin=bond_data.get('isin'),
            ticker=bond_data.get('ticker'),
            issuer_name=bond_data['issuer_name'],
            bond_type=bond_type,
            face_value=bond_data.get('face_value', 1000),
            issue_date=bond_data['issue_date'],
            maturity_date=bond_data['maturity_date'],
            coupon_rate=bond_data.get('coupon_rate'),
            coupon_frequency=bond_data.get('coupon_frequency', 2),
            day_count=bond_data.get('day_count', '30/360'),
            # Fix-to-float specific fields
            switch_date=bond_data.get('switch_date'),
            float_index=bond_data.get('float_index'),
            float_spread=bond_data.get('float_spread'),
            # Optional features
            call_dates=bond_data.get('call_dates', []),
            call_prices=bond_data.get('call_prices', []),
            # Ratings
            rating_sp=rating_sp,
            rating_moody=rating_moody,
            rating_fitch=rating_fitch,
            sector=self._map_sector(bond_data.get('sector')),
            outstanding_amount=bond_data.get('outstanding_amount'),
            benchmark_treasury=bond_data.get('benchmark_tenor', 10),
        )
    
    def get_credit_curve(self, rating: Rating, sector: Sector) -> CreditCurve:
        """Get credit spread curve for rating/sector combination."""
        # This might come from your curve service or be calculated
        # from bond spreads in your universe
        spreads = self.curve_service.get_credit_spreads(
            rating.value, 
            sector.value,
            datetime.now()
        )
        
        return CreditCurve(
            rating=rating,
            sector=sector,
            timestamp=datetime.now(),
            spreads=spreads  # Should be Dict[float, float] of tenor -> spread
        )
    
    def _determine_bond_type(self, bond_data: dict) -> BondType:
        """Determine bond type from security master data."""
        if bond_data.get('switch_date'):
            return BondType.FIX_TO_FLOAT
        elif bond_data.get('is_callable'):
            return BondType.CALLABLE
        elif bond_data.get('coupon_rate', 0) == 0:
            return BondType.ZERO_COUPON
        else:
            return BondType.FIXED_RATE
    
    def _map_rating(self, rating_str: Optional[str]) -> Optional[Rating]:
        """Map your rating strings to Rating enum."""
        if not rating_str:
            return None
            
        rating_map = {
            'AAA': Rating.AAA,
            'AA+': Rating.AA_PLUS,
            'AA': Rating.AA,
            'AA-': Rating.AA_MINUS,
            # ... add all mappings
        }
        return rating_map.get(rating_str, Rating.NR)
    
    def _map_sector(self, sector_str: Optional[str]) -> Optional[Sector]:
        """Map your sector classifications to Sector enum."""
        if not sector_str:
            return None
            
        sector_map = {
            'Financial': Sector.FINANCIALS,
            'Technology': Sector.TECHNOLOGY,
            'Energy': Sector.ENERGY,
            # ... add your mappings
        }
        return sector_map.get(sector_str, Sector.OTHER)
```

### 2. Initialize the Service

```python
from securities_analytics.market_data import MarketDataService
from your_module import WorkDataProvider

# Configure your data connections
config = {
    'price_db': {
        'host': 'your-price-db-host',
        'database': 'prices',
        'credentials': 'your-credentials'
    },
    'security_master': {
        'host': 'your-secmaster-host',
        'database': 'securities',
        'credentials': 'your-credentials'
    },
    'curve_service': {
        'endpoint': 'your-curve-service-url',
        'api_key': 'your-api-key'
    }
}

# Create provider and service
provider = WorkDataProvider(config)
market_service = MarketDataService(provider=provider)
```

### 3. Use in Your Analytics

```python
import QuantLib as ql
from securities_analytics.bonds.fix_to_float.bond import FixToFloatBond
from securities_analytics.bonds.floating_rate.bond import FloatingRateBond
from securities_analytics.bonds.analytics.spreads import BondSpreadCalculator
from securities_analytics.curves.sofr import SOFRCurve

# Set evaluation date
ql.Settings.instance().evaluationDate = ql.Date.todaysDate()

# Get market data
sofr_handle = market_service.get_sofr_curve_handle()
treasury_curve = market_service.get_treasury_curve()

# For advanced floating rate analytics, create a SOFRCurve
sofr_curve_data = market_service.provider.get_sofr_curve_data()
sofr_curve = SOFRCurve(sofr_curve_data)

# Create SOFR index
sofr_index = ql.OvernightIndex(
    "SOFR", 1, ql.USDCurrency(),
    ql.UnitedStates(ql.UnitedStates.GovernmentBond),
    ql.Actual360(), sofr_handle
)

# Get bond from your universe
cusip = "912828YK0"  # Example
bond_ref = market_service.get_bond_reference(cusip)
market_quote = market_service.get_bond_quote(cusip)

# Create fix-to-float bond if applicable
if bond_ref.bond_type == BondType.FIX_TO_FLOAT:
    bond = FixToFloatBond(
        face_value=bond_ref.face_value,
        maturity_date=bond_ref.maturity_date,
        switch_date=bond_ref.switch_date,
        fixed_rate=bond_ref.coupon_rate,
        floating_spread=bond_ref.float_spread,
        settlement_date=datetime.now() + timedelta(days=2),
        day_count=bond_ref.day_count,
        settlement_days=2,
        floating_index=sofr_index,
        next_call_date=bond_ref.call_dates[0] if bond_ref.call_dates else None,
        call_price=bond_ref.call_prices[0] if bond_ref.call_prices else None,
    )
    
    # Calculate analytics
    model_price = bond.clean_price(sofr_handle)
    print(f"Model Price: {model_price:.3f}")
    print(f"Market Price: {market_quote.mid_price:.3f}")
    print(f"Rich/Cheap: {model_price - market_quote.mid_price:.3f}")
    
    # Calculate spreads
    calculator = BondSpreadCalculator(
        bond=bond,
        treasury_curve=treasury_curve,
        original_benchmark_tenor=bond_ref.benchmark_treasury,
    )
    
    spreads = calculator.spread_from_price(market_quote.mid_price)
    print(f"G-Spread: {spreads['g_spread'] * 10000:.1f} bps")
```

## Data Field Mappings

### Required Fields for Fix-to-Float Bonds

Your security master must provide these fields for fix-to-float bonds:

| Field | Description | Example |
|-------|-------------|---------|
| `switch_date` | Date when bond switches to floating | 2027-03-15 |
| `float_index` | Floating rate index | "SOFR", "TERM_SOFR_3M" |
| `float_spread` | Spread over floating index (decimal) | 0.0125 (125bps) |
| `coupon_rate` | Fixed rate before switch (decimal) | 0.045 (4.5%) |
| `coupon_frequency` | Payments per year during fixed | 2 (semiannual) |
| `float_frequency` | Payments per year during float | 4 (quarterly) |

### Price Database Requirements

Your price database should provide:

| Field | Description | Required |
|-------|-------------|----------|
| `bid_price` | Bid price | Yes |
| `ask_price` | Ask price | Yes |
| `mid_price` | Mid price | Yes |
| `bid_yield` | Bid yield | No |
| `ask_yield` | Ask yield | No |
| `mid_yield` | Mid yield | No |
| `timestamp` | Quote timestamp | Yes |
| `volume` | Trading volume | No |

### Curve Data Format

Treasury and SOFR curves should provide tenor-yield pairs:

```python
{
    0.25: 0.0515,   # 3-month: 5.15%
    0.5: 0.0518,    # 6-month: 5.18%
    1.0: 0.0508,    # 1-year: 5.08%
    2.0: 0.0465,    # 2-year: 4.65%
    # ... etc
}
```

### 4. Using SOFR Curves with Floating Rate Bonds

For floating rate bonds, you can leverage market-based SOFR curves for more accurate forward rate projections:

```python
from securities_analytics.bonds.floating_rate import FloatingRateBond
from securities_analytics.curves.sofr import SOFRCurve

# Load SOFR curve from your data
sofr_curve_data = market_service.provider.get_sofr_curve_data()
sofr_curve = SOFRCurve(sofr_curve_data)

# Or load from CSV file (for testing)
# sofr_curve = SOFRCurve.from_csv('path/to/sofr_curve.csv')

# Create floating rate bond with market curve
floating_bond = FloatingRateBond(
    face_value=1000000,
    maturity_date=datetime(2030, 6, 15),
    floating_index=ql.Sofr(),
    spread=0.0125,  # 125 bps
    settlement_date=datetime.now() + timedelta(days=2),
    day_count="Actual/360",
    settlement_days=2,
    frequency=4,  # Quarterly
    sofr_curve=sofr_curve  # Pass the market curve
)

# Get projected cashflows using forward rates
projected_cashflows = floating_bond.get_projected_cashflows()
for date, amount in projected_cashflows:
    print(f"{date}: ${amount:,.2f}")

# Calculate spread duration
spread_duration = floating_bond.get_spread_duration()
print(f"Spread Duration: {spread_duration:.2f} years")

# Price using market curve
price = floating_bond.clean_price()
print(f"Price (using market curve): {price:.3f}")
```

### 5. SOFR Curve Analytics

The SOFR curve object provides additional analytics capabilities:

```python
# Get forward rates
start = datetime(2026, 1, 1)
end = datetime(2026, 4, 1)
forward_rate = sofr_curve.get_forward_rate(start, end, ql.Compounded)
print(f"3M forward rate starting Jan 2026: {forward_rate*100:.3f}%")

# Get forward curve for a period
forward_curve = sofr_curve.get_forward_curve(
    start_date=datetime(2025, 7, 1),
    end_date=datetime(2027, 7, 1),
    frequency=4  # Quarterly
)

# Plot forward curve
import pandas as pd
import matplotlib.pyplot as plt

df = pd.DataFrame(list(forward_curve.items()), columns=['Date', 'Rate'])
df['Rate'] = df['Rate'] * 100  # Convert to percentage

plt.figure(figsize=(10, 6))
plt.plot(df['Date'], df['Rate'])
plt.xlabel('Date')
plt.ylabel('Forward Rate (%)')
plt.title('SOFR Forward Curve')
plt.grid(True)
plt.show()
```

## Common Integration Patterns

### 1. Batch Processing

```python
def price_bond_universe(market_service, cusip_list):
    """Price all bonds in universe."""
    results = []
    
    for cusip in cusip_list:
        try:
            bond_ref = market_service.get_bond_reference(cusip)
            market_quote = market_service.get_bond_quote(cusip)
            
            # Create appropriate bond type
            if bond_ref.bond_type == BondType.FIX_TO_FLOAT:
                bond = create_fix_to_float(bond_ref, market_service)
            else:
                bond = create_fixed_rate_bond(bond_ref)
            
            # Price and calculate spreads
            model_price = bond.clean_price(get_appropriate_curve(bond_ref))
            
            results.append({
                'cusip': cusip,
                'market_price': market_quote.mid_price,
                'model_price': model_price,
                'difference': model_price - market_quote.mid_price
            })
            
        except Exception as e:
            logging.error(f"Error pricing {cusip}: {e}")
            
    return pd.DataFrame(results)
```

### 2. Real-Time Pricing

```python
def create_pricing_handler(market_service):
    """Create handler for real-time price updates."""
    
    def handle_price_update(cusip: str, new_price: float):
        # Get reference data (cached)
        bond_ref = market_service.get_bond_reference(cusip)
        
        # Create bond and calculate analytics
        bond = create_bond_from_reference(bond_ref, market_service)
        
        # Calculate spreads with new price
        calculator = BondSpreadCalculator(
            bond=bond,
            treasury_curve=market_service.get_treasury_curve(),
            original_benchmark_tenor=bond_ref.benchmark_treasury,
        )
        
        spreads = calculator.spread_from_price(new_price)
        
        # Publish results
        publish_analytics({
            'cusip': cusip,
            'price': new_price,
            'g_spread': spreads['g_spread'] * 10000,
            'duration': bond.duration(get_curve_handle(bond_ref)),
            'timestamp': datetime.now()
        })
    
    return handle_price_update
```

### 3. Historical Analysis

```python
def analyze_historical_spreads(cusip: str, start_date: date, end_date: date):
    """Analyze historical spread evolution."""
    
    # Get bond reference
    bond_ref = market_service.get_bond_reference(cusip)
    
    # Get historical prices
    historical_prices = price_db.get_price_history(cusip, start_date, end_date)
    
    # Get historical treasury curves
    historical_curves = curve_service.get_curve_history(
        'USD_TREASURY', start_date, end_date
    )
    
    results = []
    for date, price in historical_prices.items():
        # Use historical curve for that date
        treasury_curve = historical_curves[date]
        
        # Calculate spread as of historical date
        spread = calculate_historical_spread(
            bond_ref, price, treasury_curve, date
        )
        
        results.append({
            'date': date,
            'price': price,
            'spread': spread * 10000  # Convert to bps
        })
    
    return pd.DataFrame(results)
```

## Testing Your Integration

### 1. Validate Data Mapping

```python
def test_data_mapping():
    """Test that your data maps correctly."""
    test_cusip = "YOUR_TEST_CUSIP"
    
    # Get data from your provider
    bond_ref = provider.get_bond_reference(test_cusip)
    quote = provider.get_bond_quote(test_cusip)
    
    # Validate required fields
    assert bond_ref.cusip == test_cusip
    assert bond_ref.maturity_date > datetime.now()
    assert 0 <= bond_ref.coupon_rate <= 0.20  # Reasonable coupon
    
    # For fix-to-float bonds
    if bond_ref.bond_type == BondType.FIX_TO_FLOAT:
        assert bond_ref.switch_date is not None
        assert bond_ref.float_index in ["SOFR", "TERM_SOFR_3M"]
        assert 0 <= bond_ref.float_spread <= 0.05  # Reasonable spread
    
    print("✓ Data mapping validated")
```

### 2. Test Pricing Pipeline

```python
def test_pricing_pipeline():
    """Test end-to-end pricing."""
    # Get a known bond
    cusip = "YOUR_TEST_CUSIP"
    
    # Create bond and price
    bond_ref = market_service.get_bond_reference(cusip)
    bond = create_bond_from_reference(bond_ref, market_service)
    
    # Price with market curves
    sofr_handle = market_service.get_sofr_curve_handle()
    model_price = bond.clean_price(sofr_handle)
    
    # Compare with market
    market_quote = market_service.get_bond_quote(cusip)
    difference = abs(model_price - market_quote.mid_price)
    
    print(f"Model: {model_price:.3f}, Market: {market_quote.mid_price:.3f}")
    assert difference < 5.0  # Should be within 5 points
    
    print("✓ Pricing pipeline validated")
```

## Troubleshooting

### Common Issues

1. **Missing fix-to-float fields**: Ensure your security master identifies and provides switch_date, float_index, and float_spread for fix-to-float bonds.

2. **Date format issues**: The system expects Python datetime objects. Convert string dates during mapping.

3. **Curve tenor mismatches**: Ensure your curves provide all required tenors or implement interpolation.

4. **Rating mapping**: Make sure all your rating codes map to the Rating enum values.

### Debug Mode

Enable detailed logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('securities_analytics')

# This will show detailed information about data retrieval and calculations
```

## Performance Optimization

1. **Use caching**: The MarketDataService includes caching. Adjust TTLs based on your data update frequency.

2. **Batch operations**: When pricing many bonds, retrieve curves once and reuse.

3. **Parallel processing**: For large universes, consider parallel pricing:

```python
from concurrent.futures import ProcessPoolExecutor

def price_universe_parallel(cusip_list, num_workers=4):
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = executor.map(price_single_bond, cusip_list)
    return list(results)
```

## Snowflake Integration

For Snowflake-specific integration, we provide a complete framework:

```python
from securities_analytics.data_providers.snowflake import (
    SnowflakeConfig, TableConfig, SnowflakeConnector, SnowflakeDataProvider
)

# Configure Snowflake connection
config = SnowflakeConfig.from_env()  # Uses environment variables
connector = SnowflakeConnector(config)
provider = SnowflakeDataProvider(connector, TableConfig())

# Use with market data service
market_service = MarketDataService(provider=provider)
```

### Model Validation

Validate your model outputs against historical data:

```python
from securities_analytics.validation import ModelValidator

validator = ModelValidator(provider, market_service)

# Validate single bond
result = validator.validate_bond_pricing('912828YK0', date(2024, 11, 15))
print(f"Model: {result.model_value:.3f}, Market: {result.market_value:.3f}")

# Batch validation
report = validator.batch_validate(
    cusip_list=['912828YK0', '38141GXZ2'],
    date_range=(date(2024, 11, 1), date(2024, 11, 30))
)
print(f"Success Rate: {report.success_rate:.1%}")
```

See the [Snowflake Validation Guide](docs/SNOWFLAKE_VALIDATION_GUIDE.md) for complete details.

## Next Steps

1. Start with a small subset of bonds to validate the integration
2. Compare model prices with market prices to ensure accuracy
3. Monitor performance and adjust caching as needed
4. Extend to full universe once validated

For questions or issues, refer to the main documentation or the test examples.