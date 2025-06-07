"""Configuration for Snowflake connection and tables."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class SnowflakeConfig:
    """Snowflake connection configuration.
    
    Credentials can be provided directly or via environment variables:
    - SNOWFLAKE_USER
    - SNOWFLAKE_PASSWORD
    - SNOWFLAKE_ACCOUNT
    - SNOWFLAKE_WAREHOUSE
    - SNOWFLAKE_DATABASE
    - SNOWFLAKE_SCHEMA
    - SNOWFLAKE_ROLE
    """
    account: str
    warehouse: str
    database: str
    schema: str
    role: str = "ANALYST_ROLE"
    
    # Authentication options
    username: Optional[str] = None
    password: Optional[str] = None
    private_key_path: Optional[str] = None  # For key-pair authentication
    
    # Connection settings
    login_timeout: int = 60
    network_timeout: int = 60
    
    @classmethod
    def from_env(cls) -> 'SnowflakeConfig':
        """Create config from environment variables."""
        return cls(
            account=os.environ.get('SNOWFLAKE_ACCOUNT', ''),
            warehouse=os.environ.get('SNOWFLAKE_WAREHOUSE', ''),
            database=os.environ.get('SNOWFLAKE_DATABASE', ''),
            schema=os.environ.get('SNOWFLAKE_SCHEMA', ''),
            role=os.environ.get('SNOWFLAKE_ROLE', 'ANALYST_ROLE'),
            username=os.environ.get('SNOWFLAKE_USER'),
            password=os.environ.get('SNOWFLAKE_PASSWORD'),
            private_key_path=os.environ.get('SNOWFLAKE_PRIVATE_KEY_PATH')
        )


@dataclass
class TableConfig:
    """Configuration for Snowflake table names and schemas."""
    
    # Core tables
    security_master_table: str = "SECURITY_MASTER"
    historical_analytics_table: str = "HISTORICAL_BOND_ANALYTICS" 
    treasury_rates_table: str = "TREASURY_RATES"
    sofr_rates_table: str = "SOFR_SWAP_RATES"
    
    # Optional tables
    call_schedule_table: Optional[str] = "CALL_SCHEDULES"
    rating_history_table: Optional[str] = "RATING_HISTORY"
    issuer_table: Optional[str] = "ISSUER_MASTER"
    
    # Column mappings (if different from expected)
    column_mappings: Optional[dict] = None
    
    def __post_init__(self):
        """Set default column mappings if not provided."""
        if self.column_mappings is None:
            self.column_mappings = {
                # Security master mappings
                'cusip': 'CUSIP',
                'isin': 'ISIN',
                'ticker': 'TICKER',
                'issuer_name': 'ISSUER_NAME',
                'maturity_date': 'MATURITY_DATE',
                'issue_date': 'ISSUE_DATE',
                'coupon_rate': 'COUPON_RATE',
                'coupon_frequency': 'COUPON_FREQUENCY',
                'day_count': 'DAY_COUNT_CONVENTION',
                'bond_type': 'BOND_TYPE',
                'switch_date': 'SWITCH_DATE',
                'float_index': 'FLOAT_INDEX', 
                'float_spread': 'FLOAT_SPREAD',
                'outstanding_amount': 'OUTSTANDING_AMOUNT',
                
                # Analytics mappings
                'price_date': 'PRICE_DATE',
                'bid_price': 'BID_PRICE',
                'mid_price': 'MID_PRICE',
                'ask_price': 'ASK_PRICE',
                'bid_yield': 'BID_YIELD',
                'mid_yield': 'MID_YIELD',
                'ask_yield': 'ASK_YIELD',
                'g_spread': 'G_SPREAD',
                'benchmark_spread': 'BENCHMARK_SPREAD',
                'oas': 'OAS',
                'duration': 'DURATION',
                'convexity': 'CONVEXITY',
                'dv01': 'DV01',
                
                # Curve mappings
                'curve_date': 'CURVE_DATE',
                'tenor': 'TENOR',
                'rate': 'RATE'
            }