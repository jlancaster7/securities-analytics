"""Configuration for Snowflake connection and tables."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class SnowflakeConfig:
    """Snowflake connection configuration.
    
    Supports OAuth authentication via environment variables:
    - SNOWFLAKE_ACCOUNT_IDENTIFIER
    - SNOWFLAKE_USER
    - SNOWFLAKE_WAREHOUSE
    - SNOWFLAKE_DATABASE
    - SNOWFLAKE_SCHEMA
    - SNOWFLAKE_ROLE
    """
    account_identifier: str
    user: str
    warehouse: str
    database: str
    schema: str
    role: str = "ANALYST_ROLE"
    
    # OAuth authentication
    authenticator: str = "oauth"
    token: Optional[str] = None  # Will be set by OAuth token provider
    
    # Connection settings
    login_timeout: int = 60
    network_timeout: int = 60
    
    @classmethod
    def from_env(cls) -> 'SnowflakeConfig':
        """Create config from environment variables."""
        return cls(
            account_identifier=os.environ.get('SNOWFLAKE_ACCOUNT_IDENTIFIER', ''),
            user=os.environ.get('SNOWFLAKE_USER', ''),
            warehouse=os.environ.get('SNOWFLAKE_WAREHOUSE', ''),
            database=os.environ.get('SNOWFLAKE_DATABASE', ''),
            schema=os.environ.get('SNOWFLAKE_SCHEMA', ''),
            role=os.environ.get('SNOWFLAKE_ROLE', 'ANALYST_ROLE')
        )


@dataclass
class OAuthConfig:
    """OAuth configuration for Snowflake authentication.
    
    Environment variables:
    - SNOWFLAKE_OAUTH_CLIENT_ID
    - SNOWFLAKE_OAUTH_CLIENT_SECRET
    - SNOWFLAKE_OAUTH_SCOPE
    - SNOWFLAKE_OAUTH_TOKEN_ENDPOINT (optional)
    """
    client_id: str
    client_secret: str
    scope: str
    token_endpoint: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'OAuthConfig':
        """Create OAuth config from environment variables."""
        return cls(
            client_id=os.environ.get('SNOWFLAKE_OAUTH_CLIENT_ID', ''),
            client_secret=os.environ.get('SNOWFLAKE_OAUTH_CLIENT_SECRET', ''),
            scope=os.environ.get('SNOWFLAKE_OAUTH_SCOPE', ''),
            token_endpoint=os.environ.get('SNOWFLAKE_OAUTH_TOKEN_ENDPOINT')
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