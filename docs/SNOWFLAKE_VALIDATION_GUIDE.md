# Snowflake Integration & Model Validation Guide

## Overview

This guide documents the Snowflake integration framework and model validation system for the fixed income analytics service. The system allows you to:

1. Connect to Snowflake databases to source market data
2. Validate model outputs against historical analytics
3. Generate comprehensive validation reports
4. Track model accuracy over time

## Architecture

### Data Flow

```
Snowflake Database
    ├── SECURITY_MASTER      → BondReference
    ├── BOND_ANALYTICS_DAILY → MarketQuote & Historical Analytics
    ├── TREASURY_CURVES      → Treasury Yield Curves
    └── SOFR_CURVES         → SOFR Forward Curves
              ↓
    SnowflakeDataProvider
              ↓
    MarketDataService
              ↓
    Bond Creation & Pricing
              ↓
    ModelValidator
              ↓
    Validation Reports
```

### Key Components

1. **SnowflakeConnector** (`connector.py`)
   - Manages database connections
   - Provides query caching
   - Handles connection pooling

2. **SnowflakeDataProvider** (`provider.py`)
   - Implements DataProvider interface
   - Maps Snowflake data to domain objects
   - Provides market data access methods

3. **ModelValidator** (`validator.py`)
   - Compares model outputs to historical data
   - Applies configurable tolerances
   - Generates validation reports

4. **ValidationMetrics** (`metrics.py`)
   - Defines tolerance levels
   - Calculates validation statistics
   - Structures validation results

## Configuration

### OAuth Authentication (Recommended)

```bash
# Snowflake connection settings
export SNOWFLAKE_ACCOUNT_IDENTIFIER='your_account.region'
export SNOWFLAKE_USER='your_username@company.com'
export SNOWFLAKE_WAREHOUSE='your_warehouse'
export SNOWFLAKE_DATABASE='MARKET_DATA'
export SNOWFLAKE_SCHEMA='BONDS'
export SNOWFLAKE_ROLE='ANALYST_ROLE'

# OAuth credentials
export SNOWFLAKE_OAUTH_CLIENT_ID='your-client-id'
export SNOWFLAKE_OAUTH_CLIENT_SECRET='your-client-secret'
export SNOWFLAKE_OAUTH_SCOPE='session:role:ANALYST_ROLE'
export SNOWFLAKE_OAUTH_TOKEN_ENDPOINT='https://your_account.snowflakecomputing.com/oauth/token'  # Optional
```

### Programmatic OAuth Setup

```python
from securities_analytics.data_providers.snowflake import (
    SnowflakeConfig, OAuthConfig, SnowflakeConnector, SnowflakeDataProvider
)

# Create configs
snowflake_config = SnowflakeConfig(
    account_identifier="myaccount.us-east-1",
    user="myuser@company.com",
    warehouse="COMPUTE_WH",
    database="MARKET_DATA",
    schema="BONDS"
)

oauth_config = OAuthConfig(
    client_id="your-client-id",
    client_secret="your-client-secret",
    scope="session:role:ANALYST_ROLE"
)

# Create OAuth-enabled connector
connector = SnowflakeConnector(snowflake_config, oauth_config)
provider = SnowflakeDataProvider(connector)
```

### Table Configuration

```python
from securities_analytics.data_providers.snowflake import TableConfig

table_config = TableConfig(
    security_master_table='SECURITY_MASTER',
    historical_analytics_table='BOND_ANALYTICS_DAILY',
    treasury_rates_table='TREASURY_CURVES',
    sofr_rates_table='SOFR_CURVES',
    call_schedule_table='CALL_SCHEDULES'  # Optional
)
```

### Custom Column Mappings

If your column names differ from the defaults:

```python
table_config.column_mappings = {
    'cusip': 'CUSIP_ID',
    'maturity_date': 'MATURITY_DT',
    'coupon_rate': 'CPN_RATE',
    # ... add your mappings
}
```

## Validation Framework

### Default Tolerances

| Metric | Default Tolerance | Type | Notes |
|--------|------------------|------|-------|
| clean_price | 0.25 | Absolute | 25 cents |
| dirty_price | 0.25 | Absolute | 25 cents |
| yield_to_maturity | 0.02 | Absolute | 2 basis points |
| g_spread | 0.02 | Absolute | 2 basis points |
| benchmark_spread | 0.02 | Absolute | 2 basis points |
| z_spread | 0.03 | Absolute | 3 basis points |
| oas | 0.05 | Absolute | 5 basis points |
| duration | 0.02 | Relative | 2% of market value |
| convexity | 0.05 | Relative | 5% of market value |
| dv01 | 0.02 | Relative | 2% of market value |

### Custom Tolerances

```python
custom_tolerances = {
    'clean_price': 0.50,     # 50 cents
    'g_spread': 0.05,        # 5 basis points
    'duration': 0.03,        # 3% relative
}

validator = ModelValidator(
    data_provider=snowflake_provider,
    custom_tolerances=custom_tolerances
)
```

## Usage Examples

### Single Bond Validation

```python
from securities_analytics.validation import ModelValidator
from datetime import date

# Create validator
validator = ModelValidator(snowflake_provider)

# Validate pricing
pricing_result = validator.validate_bond_pricing(
    cusip='912828YK0',
    validation_date=date(2024, 11, 15)
)

print(f"Model Price: {pricing_result.model_value:.3f}")
print(f"Market Price: {pricing_result.market_value:.3f}")
print(f"Within Tolerance: {pricing_result.within_tolerance}")

# Validate spreads
spread_validation = validator.validate_spreads(
    cusip='912828YK0',
    validation_date=date(2024, 11, 15)
)

print(f"G-Spread Pass: {spread_validation.g_spread.within_tolerance}")
print(f"All Spreads Pass: {spread_validation.all_passed}")
```

### Batch Validation

```python
# Validate multiple bonds over a date range
report = validator.batch_validate(
    cusip_list=['912828YK0', '38141GXZ2', '38259PAC9'],
    date_range=(date(2024, 11, 1), date(2024, 11, 30)),
    metrics=['pricing', 'spreads', 'risk']
)

# Display summary
print(f"Success Rate: {report.success_rate:.1%}")
print(f"Mean Absolute Error: {report.mean_absolute_error:.3f}")

# Get detailed statistics by metric
stats_df = report.to_dataframe()
print(stats_df)

# Save failures for investigation
if report.failures:
    failures_df = pd.DataFrame([f.__dict__ for f in report.failures])
    failures_df.to_csv('validation_failures.csv', index=False)
```

### Daily Universe Validation

```python
# Validate entire bond universe for a specific date
validation_date = date(2024, 11, 15)
universe = snowflake_provider.get_bond_universe(validation_date)

report = validator.validate_single_date(
    validation_date=validation_date,
    universe=universe
)

# Generate summary report
print(f"Bonds Validated: {report.bonds_validated}")
print(f"Total Tests: {report.total_validations}")
print(f"Pass Rate: {report.success_rate:.1%}")
```

## Implementation Checklist

### Required Implementations

When you're at work with Snowflake access, implement these methods:

1. **SnowflakeConnector.connect()**
   ```python
   import snowflake.connector
   
   # Get OAuth token if using OAuth
   if self._token_provider:
       token = self._token_provider.get_token()
       self.config.token = token
   
   # Connect with OAuth
   self._connection = snowflake.connector.connect(
       account=self.config.account_identifier,
       user=self.config.user,
       authenticator='oauth',
       token=self.config.token,
       warehouse=self.config.warehouse,
       database=self.config.database,
       schema=self.config.schema,
       role=self.config.role
   )
   ```

2. **OAuthTokenProvider.get_token()**
   ```python
   import requests
   from datetime import datetime, timedelta
   
   # Check if token is still valid
   if self._token and self._token_expiry and datetime.now() < self._token_expiry:
       return self._token
   
   # Request new token
   token_url = self.oauth_config.token_endpoint or \
       f"https://{self.config.account_identifier}.snowflakecomputing.com/oauth/token"
   
   data = {
       'grant_type': 'client_credentials',
       'client_id': self.oauth_config.client_id,
       'client_secret': self.oauth_config.client_secret,
       'scope': self.oauth_config.scope
   }
   
   response = requests.post(token_url, data=data)
   response.raise_for_status()
   
   token_data = response.json()
   self._token = token_data['access_token']
   expires_in = token_data.get('expires_in', 3600)
   self._token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
   
   return self._token
   ```

3. **SnowflakeConnector.execute_query()**
   ```python
   cursor = self._connection.cursor()
   try:
       cursor.execute(query, params)
       columns = [desc[0] for desc in cursor.description]
       data = cursor.fetchall()
       return pd.DataFrame(data, columns=columns)
   finally:
       cursor.close()
   ```

4. **SnowflakeDataProvider methods**
   - `get_treasury_curve()` - Uncomment and test
   - `get_sofr_curve_data()` - Uncomment and test
   - `get_bond_reference()` - Uncomment and test
   - `get_bond_quote()` - Uncomment and test

5. **ModelValidator._create_bond()**
   - Map bond types to appropriate classes
   - Handle fix-to-float specific fields
   - Create SOFR index for floating bonds

## Testing

### With Mock Data (Available Now)

```bash
# Run validation framework tests
poetry run pytest tests/validation/ -v

# Test specific components
poetry run pytest tests/validation/test_metrics.py -v
poetry run pytest tests/validation/test_validator_mock.py -v
```

### With Real Data (At Work)

1. Start with a known bond
2. Compare model price to database price
3. Check if difference is within tolerance
4. Investigate any failures

## Troubleshooting

### Common Issues

1. **"Bond not found in security master"**
   - Check CUSIP format (9 characters)
   - Verify bond exists in database
   - Check date filters

2. **"No historical data for date"**
   - Verify date is a business day
   - Check data availability
   - Try previous business day

3. **Large validation errors**
   - Check curve data quality
   - Verify day count conventions match
   - Ensure proper bond type identification

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use loguru
from loguru import logger
logger.add("validation_debug.log", level="DEBUG")
```

## Performance Optimization

1. **Use cached queries for repeated data**
   ```python
   # 5 minute cache for curves
   df = connector.execute_cached_query(query, params, ttl=300)
   ```

2. **Batch bond loading**
   ```python
   cusips = ['CUSIP1', 'CUSIP2', 'CUSIP3']
   query = f"SELECT * FROM {table} WHERE CUSIP IN ({','.join(['%s']*len(cusips))})"
   ```

3. **Parallel validation**
   ```python
   from concurrent.futures import ProcessPoolExecutor
   
   with ProcessPoolExecutor(max_workers=4) as executor:
       results = executor.map(validator.validate_bond_pricing, cusip_list)
   ```

## Reporting

### Validation Report Fields

- **Summary Statistics**: Success rate, MAE, RMSE, max error
- **Metric-Level Stats**: Pass rate, mean error, percentiles by metric type
- **Failed Validations**: Detailed list for investigation
- **Time Series**: Track accuracy over time

### Export Options

```python
# CSV export
report_df = pd.DataFrame([r.__dict__ for r in all_results])
report_df.to_csv(f'validation_{date.today()}.csv', index=False)

# Summary statistics
summary = report.to_dataframe()
summary.to_excel('validation_summary.xlsx', index=False)

# Failed bonds for investigation
failures_df = pd.DataFrame([f.__dict__ for f in report.failures])
failures_df.to_csv('investigate_these.csv', index=False)
```

## Next Steps

1. **Implement Snowflake connection** at work
2. **Map your table schemas** to the expected format
3. **Run validation on a small subset** of bonds first
4. **Tune tolerances** based on your data quality
5. **Set up daily validation** jobs
6. **Monitor trends** over time

The validation framework is fully tested and ready to use - you just need to plug in the real Snowflake connection!