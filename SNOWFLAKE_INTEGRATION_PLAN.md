# Snowflake Integration Plan

## Overview
Set up Snowflake database integration to source all market data from work databases, including security master, pricing data, and curves. Additionally, create a validation framework to compare model outputs against historical analytics.

## Phase 1: Infrastructure Setup

### 1.1 Snowflake Connector
Create base connector class with connection pooling and error handling:

```python
# securities_analytics/data_providers/snowflake/connector.py
class SnowflakeConnector:
    def __init__(self, config: SnowflakeConfig):
        self.config = config
        self._connection_pool = []
        
    def execute_query(self, query: str, params: Dict = None) -> pd.DataFrame:
        """Execute query and return results as DataFrame"""
        
    def execute_cached_query(self, query: str, params: Dict = None, ttl: int = 300) -> pd.DataFrame:
        """Execute with caching support"""
```

### 1.2 Configuration Management
Secure configuration for database credentials:

```python
# securities_analytics/data_providers/snowflake/config.py
@dataclass
class SnowflakeConfig:
    account: str
    warehouse: str
    database: str
    schema: str
    role: str
    # Credentials from environment or secrets manager
    username: Optional[str] = None
    password: Optional[str] = None
    key_path: Optional[str] = None  # For key-pair auth
```

## Phase 2: Data Tables Mapping

### 2.1 Security Master Table
Expected columns:
- CUSIP, ISIN, TICKER
- ISSUER_NAME, ISSUER_ID
- MATURITY_DATE, DATED_DATE
- COUPON_RATE, COUPON_FREQUENCY
- DAY_COUNT_CONVENTION
- BOND_TYPE (identify fix-to-float, callable, etc.)
- SWITCH_DATE, FLOAT_INDEX, FLOAT_SPREAD (for fix-to-float)
- CALL_SCHEDULE (JSON or separate table)
- RATING_SP, RATING_MOODY, RATING_FITCH
- SECTOR, INDUSTRY
- OUTSTANDING_AMOUNT
- BENCHMARK_TENOR

### 2.2 Historical Securities Analytics Table
Expected columns:
- CUSIP
- PRICE_DATE
- BID_PRICE, MID_PRICE, ASK_PRICE
- BID_YIELD, MID_YIELD, ASK_YIELD
- G_SPREAD, BENCHMARK_SPREAD, OAS
- DURATION, CONVEXITY, DV01
- VOLUME, TRADE_COUNT
- DATA_SOURCE, QUALITY_FLAG

### 2.3 Treasury Rates Table
Expected columns:
- CURVE_DATE
- TENOR (e.g., '3M', '2Y', '10Y')
- RATE
- CURVE_TYPE (ON_THE_RUN, CONSTANT_MATURITY)

### 2.4 SOFR Swap Rates Table
Expected columns:
- CURVE_DATE
- TENOR
- RATE
- INSTRUMENT_TYPE (DEPOSIT, FUTURES, SWAP)
- CUSIP (optional)

## Phase 3: Data Provider Implementation

### 3.1 SnowflakeDataProvider
Main implementation class:

```python
# securities_analytics/data_providers/snowflake/provider.py
class SnowflakeDataProvider(DataProvider):
    def __init__(self, connector: SnowflakeConnector, config: TableConfig):
        self.connector = connector
        self.config = config
        
    def get_bond_reference(self, cusip: str) -> BondReference:
        """Query security master and map to BondReference"""
        
    def get_bond_quote(self, cusip: str, as_of_date: Optional[date] = None) -> MarketQuote:
        """Get latest or historical quote"""
        
    def get_treasury_curve(self, as_of_date: Optional[date] = None) -> Dict[float, float]:
        """Build treasury curve from rates table"""
        
    def get_sofr_curve_data(self, as_of_date: Optional[date] = None) -> SOFRCurveData:
        """Build SOFR curve from swap rates"""
        
    def get_historical_analytics(self, cusip: str, 
                                start_date: date, 
                                end_date: date) -> pd.DataFrame:
        """Get historical analytics for validation"""
```

### 3.2 SQL Query Templates
Parameterized queries for each data type:

```python
# securities_analytics/data_providers/snowflake/queries.py
SECURITY_MASTER_QUERY = """
SELECT 
    CUSIP,
    ISSUER_NAME,
    MATURITY_DATE,
    COUPON_RATE,
    -- ... all fields
FROM {security_master_table}
WHERE CUSIP = %(cusip)s
"""

HISTORICAL_ANALYTICS_QUERY = """
SELECT 
    PRICE_DATE,
    MID_PRICE,
    MID_YIELD,
    G_SPREAD,
    DURATION,
    -- ... all analytics fields
FROM {analytics_table}
WHERE CUSIP = %(cusip)s
  AND PRICE_DATE BETWEEN %(start_date)s AND %(end_date)s
ORDER BY PRICE_DATE
"""
```

## Phase 4: Model Validation Framework

### 4.1 Validation Service
Compare model outputs to historical data:

```python
# securities_analytics/validation/validator.py
class ModelValidator:
    def __init__(self, data_provider: SnowflakeDataProvider):
        self.data_provider = data_provider
        
    def validate_bond_pricing(self, cusip: str, 
                            validation_date: date,
                            tolerance: Dict[str, float]) -> ValidationResult:
        """Compare model price/yield to historical"""
        
    def validate_spreads(self, cusip: str,
                        validation_date: date) -> SpreadValidation:
        """Compare G-spread, benchmark spread calculations"""
        
    def validate_risk_measures(self, cusip: str,
                             validation_date: date) -> RiskValidation:
        """Compare duration, convexity, DV01"""
        
    def batch_validate(self, cusip_list: List[str],
                      date_range: Tuple[date, date]) -> pd.DataFrame:
        """Validate multiple bonds over date range"""
```

### 4.2 Validation Results
Structured results for analysis:

```python
@dataclass
class ValidationResult:
    cusip: str
    validation_date: date
    metric: str
    model_value: float
    market_value: float
    difference: float
    percent_diff: float
    within_tolerance: bool
    
@dataclass
class ValidationReport:
    summary_stats: Dict[str, float]  # MAE, RMSE, etc.
    failed_validations: List[ValidationResult]
    success_rate: float
```

## Phase 5: Testing Strategy

### 5.1 Unit Tests
- Mock Snowflake queries for testing
- Test data mapping logic
- Test error handling

### 5.2 Integration Tests
- Test with sample data matching production schema
- Validate query performance
- Test connection pooling

### 5.3 Validation Tests
- Historical backtesting framework
- Daily validation reports
- Outlier detection

## Phase 6: Implementation Order

1. **Week 1**: 
   - Basic Snowflake connector
   - Configuration management
   - Security master integration

2. **Week 2**:
   - Pricing data integration
   - Treasury and SOFR curves
   - Basic validation framework

3. **Week 3**:
   - Full model validation
   - Backtesting capabilities
   - Performance optimization

4. **Week 4**:
   - Production deployment
   - Monitoring setup
   - Documentation

## Key Considerations

### Performance
- Use connection pooling
- Implement query caching
- Batch queries where possible
- Consider materialized views for curves

### Error Handling
- Graceful handling of missing data
- Fallback mechanisms
- Comprehensive logging

### Security
- Use environment variables or secrets manager
- Implement role-based access
- Audit trail for queries

### Data Quality
- Handle NULL values appropriately
- Validate data types
- Check for stale data
- Flag suspicious values

## Success Metrics

1. **Accuracy**: Model prices within 0.25 points of market
2. **Coverage**: 95%+ of bonds successfully priced
3. **Performance**: Full universe pricing in < 5 minutes
4. **Reliability**: 99.9% uptime for data access

## Next Steps

1. Review and refine table schemas
2. Set up development Snowflake access
3. Create mock data for testing
4. Begin implementation with connector class