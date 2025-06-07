# Snowflake Integration Guide

This guide helps you integrate the fixed income analytics service with your Snowflake database at work.

## Quick Start

### 1. Install Snowflake Connector

First, install the Snowflake Python connector:

```bash
poetry add snowflake-connector-python
```

### 2. Set Environment Variables

Configure your Snowflake credentials:

```bash
export SNOWFLAKE_ACCOUNT='your_account'
export SNOWFLAKE_WAREHOUSE='your_warehouse'
export SNOWFLAKE_DATABASE='MARKET_DATA'
export SNOWFLAKE_SCHEMA='BONDS'
export SNOWFLAKE_USER='your_username'
export SNOWFLAKE_PASSWORD='your_password'
export SNOWFLAKE_ROLE='ANALYST_ROLE'
```

### 3. Run Integration Example

```python
from securities_analytics.data_providers.snowflake import (
    SnowflakeConfig, TableConfig, SnowflakeConnector, SnowflakeDataProvider
)
from securities_analytics.market_data import MarketDataService

# Configure connection
config = SnowflakeConfig.from_env()
table_config = TableConfig()

# Create provider
connector = SnowflakeConnector(config)
provider = SnowflakeDataProvider(connector, table_config)

# Use with market data service
market_service = MarketDataService(provider=provider)
```

## Implementation Status

### ✅ Completed
- Snowflake connector framework with connection pooling
- Query caching for performance
- Data provider interface implementation
- SQL query templates for all data types
- Model validation framework
- Comprehensive error handling

### 🚧 To Implement
1. **Actual Snowflake Connection** (`connector.py:connect()`)
   - Add snowflake.connector.connect() call
   - Implement connection pooling
   - Add retry logic

2. **Query Execution** (`connector.py:execute_query()`)
   - Execute SQL with parameters
   - Handle result conversion to DataFrame
   - Implement proper error handling

3. **Data Loading Methods** (`provider.py`)
   - `get_treasury_curve()` - Load treasury rates
   - `get_sofr_curve_data()` - Load SOFR swap rates
   - `get_bond_reference()` - Load from security master
   - `get_bond_quote()` - Load from analytics table

4. **Bond Creation** (`validator.py:_create_bond()`)
   - Map bond type to appropriate class
   - Handle fix-to-float specifics
   - Create SOFR index for floating bonds

## Expected Table Schemas

### SECURITY_MASTER
```sql
CREATE TABLE SECURITY_MASTER (
    CUSIP VARCHAR(9) PRIMARY KEY,
    ISIN VARCHAR(12),
    TICKER VARCHAR(20),
    ISSUER_NAME VARCHAR(255),
    MATURITY_DATE DATE,
    ISSUE_DATE DATE,
    COUPON_RATE NUMBER(10,6),  -- In percent
    COUPON_FREQUENCY INTEGER,
    DAY_COUNT_CONVENTION VARCHAR(20),
    BOND_TYPE VARCHAR(20),  -- 'FIXED', 'FIX_TO_FLOAT', 'FLOATING', etc.
    -- Fix-to-float fields
    SWITCH_DATE DATE,
    FLOAT_INDEX VARCHAR(20),  -- 'SOFR', 'TERM_SOFR_3M', etc.
    FLOAT_SPREAD NUMBER(10,4),  -- In basis points
    -- Ratings
    RATING_SP VARCHAR(10),
    RATING_MOODY VARCHAR(10),
    RATING_FITCH VARCHAR(10),
    -- Other fields...
);
```

### BOND_ANALYTICS_DAILY
```sql
CREATE TABLE BOND_ANALYTICS_DAILY (
    CUSIP VARCHAR(9),
    PRICE_DATE DATE,
    BID_PRICE NUMBER(10,6),
    MID_PRICE NUMBER(10,6),
    ASK_PRICE NUMBER(10,6),
    BID_YIELD NUMBER(10,8),
    MID_YIELD NUMBER(10,8),
    ASK_YIELD NUMBER(10,8),
    G_SPREAD NUMBER(10,4),      -- In basis points
    BENCHMARK_SPREAD NUMBER(10,4),
    Z_SPREAD NUMBER(10,4),
    OAS NUMBER(10,4),
    DURATION NUMBER(10,6),
    CONVEXITY NUMBER(10,6),
    DV01 NUMBER(10,6),
    PRIMARY KEY (CUSIP, PRICE_DATE)
);
```

### TREASURY_CURVES
```sql
CREATE TABLE TREASURY_CURVES (
    CURVE_DATE DATE,
    TENOR VARCHAR(10),  -- '3M', '2Y', '10Y', etc.
    TENOR_YEARS NUMBER(10,4),  -- Numeric years
    RATE NUMBER(10,8),  -- In decimal (0.05 = 5%)
    CURVE_TYPE VARCHAR(20),  -- 'CONSTANT_MATURITY', 'ON_THE_RUN'
    PRIMARY KEY (CURVE_DATE, TENOR, CURVE_TYPE)
);
```

### SOFR_CURVES
```sql
CREATE TABLE SOFR_CURVES (
    CURVE_DATE DATE,
    TENOR VARCHAR(10),  -- 'ON', '1W', '3M', '2Y', etc.
    TENOR_DAYS INTEGER,  -- Days to maturity
    RATE NUMBER(10,8),  -- In decimal
    INSTRUMENT_TYPE VARCHAR(20),  -- 'DEPOSIT', 'FUTURES', 'SWAP'
    CUSIP VARCHAR(12),  -- Optional instrument CUSIP
    PRIMARY KEY (CURVE_DATE, TENOR)
);
```

## Validation Workflow

### 1. Single Bond Validation
```python
from securities_analytics.validation import ModelValidator

validator = ModelValidator(provider, market_service)

# Validate pricing
result = validator.validate_bond_pricing('912828YK0', date(2024, 11, 15))
print(f"Model: {result.model_value:.3f}, Market: {result.market_value:.3f}")
print(f"Within tolerance: {result.within_tolerance}")
```

### 2. Batch Validation
```python
# Validate multiple bonds over date range
report = validator.batch_validate(
    cusip_list=['912828YK0', '38141GXZ2', '38259PAC9'],
    date_range=(date(2024, 11, 1), date(2024, 11, 30)),
    metrics=['pricing', 'spreads', 'risk']
)

print(f"Success rate: {report.success_rate:.1%}")
print(f"Mean absolute error: {report.mean_absolute_error:.3f}")
```

### 3. Custom Tolerances
```python
# Set custom validation tolerances
custom_tolerances = {
    'clean_price': 0.50,     # 50 cents
    'g_spread': 0.03,        # 3 basis points
    'duration': 0.02,        # 2% relative
    'convexity': 0.05        # 5% relative
}

validator = ModelValidator(provider, market_service, custom_tolerances)
```

## Performance Tips

1. **Use Query Caching**: The connector includes caching with configurable TTL
   ```python
   df = connector.execute_cached_query(query, params, ttl=300)  # 5 min cache
   ```

2. **Batch Queries**: Load multiple bonds at once
   ```python
   cusips = ['CUSIP1', 'CUSIP2', 'CUSIP3']
   query = f"SELECT * FROM SECURITY_MASTER WHERE CUSIP IN ({','.join(['%s']*len(cusips))})"
   ```

3. **Connection Pooling**: Reuse connections
   ```python
   with connector:  # Automatically connects/disconnects
       data1 = connector.execute_query(query1)
       data2 = connector.execute_query(query2)
   ```

## Testing Without Snowflake

To test the integration logic without Snowflake access:

1. Create mock data matching your schemas
2. Implement a MockSnowflakeConnector
3. Test the data transformation logic

```python
class MockSnowflakeConnector(SnowflakeConnector):
    def execute_query(self, query: str, params: Dict = None) -> pd.DataFrame:
        # Return mock data based on query
        if "SECURITY_MASTER" in query:
            return pd.DataFrame({
                'CUSIP': ['912828YK0'],
                'ISSUER_NAME': ['US TREASURY'],
                'MATURITY_DATE': [datetime(2034, 11, 15)],
                'COUPON_RATE': [4.5],
                # ... other fields
            })
        # ... handle other queries
```

## Next Steps

1. **Implement Connection Logic**: Add actual Snowflake connection code
2. **Map Your Schema**: Adjust column names in `TableConfig` if different
3. **Test with Sample Data**: Validate with a few known bonds first
4. **Performance Tuning**: Optimize queries and caching based on usage
5. **Production Deployment**: Set up proper credentials management

## Support

For issues or questions:
- Check query logs for debugging
- Verify table schemas match expectations
- Test individual components in isolation
- Use the validation framework to identify discrepancies