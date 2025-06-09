"""Example of Snowflake integration with OAuth authentication.

This example shows how to set up the Snowflake data provider using OAuth
authentication instead of username/password.

Required environment variables:
- SNOWFLAKE_ACCOUNT_IDENTIFIER: Your Snowflake account identifier
- SNOWFLAKE_USER: Your Snowflake username
- SNOWFLAKE_WAREHOUSE: Data warehouse to use
- SNOWFLAKE_DATABASE: Database name
- SNOWFLAKE_SCHEMA: Schema name
- SNOWFLAKE_ROLE: Role to use (optional)
- SNOWFLAKE_OAUTH_CLIENT_ID: OAuth client ID
- SNOWFLAKE_OAUTH_CLIENT_SECRET: OAuth client secret
- SNOWFLAKE_OAUTH_SCOPE: OAuth scope for Snowflake access
- SNOWFLAKE_OAUTH_TOKEN_ENDPOINT: Token endpoint URL (optional)
"""

import os
from datetime import date
from securities_analytics.data_providers.snowflake import (
    SnowflakeConfig, OAuthConfig, SnowflakeConnector, 
    SnowflakeDataProvider, TableConfig
)
from securities_analytics.market_data import MarketDataService
from securities_analytics.validation import ModelValidator


def setup_oauth_provider():
    """Set up Snowflake data provider with OAuth authentication."""
    
    # Create configurations from environment
    snowflake_config = SnowflakeConfig.from_env()
    oauth_config = OAuthConfig.from_env()
    
    # Or create manually
    # snowflake_config = SnowflakeConfig(
    #     account_identifier="myaccount.us-east-1",
    #     user="myuser@company.com",
    #     warehouse="COMPUTE_WH",
    #     database="MARKET_DATA",
    #     schema="BONDS",
    #     role="ANALYST_ROLE"
    # )
    
    # oauth_config = OAuthConfig(
    #     client_id="your-client-id",
    #     client_secret="your-client-secret",
    #     scope="session:role:ANALYST_ROLE"
    # )
    
    # Create connector with OAuth
    connector = SnowflakeConnector(snowflake_config, oauth_config)
    
    # Optional: customize table configuration
    table_config = TableConfig(
        security_master_table="SECURITY_MASTER",
        historical_analytics_table="BOND_ANALYTICS_DAILY",
        treasury_rates_table="TREASURY_CURVES",
        sofr_rates_table="SOFR_SWAP_RATES"
    )
    
    # Create data provider
    provider = SnowflakeDataProvider(connector, table_config)
    
    # Alternative: use convenience method
    # provider = SnowflakeDataProvider.from_oauth_config(
    #     snowflake_config, oauth_config, table_config
    # )
    
    return provider


def main():
    """Example usage of OAuth-enabled Snowflake provider."""
    
    # Set up provider with OAuth
    provider = setup_oauth_provider()
    
    # Create market data service
    market_service = MarketDataService(provider=provider)
    
    # Example 1: Get treasury curve
    try:
        treasury_curve = provider.get_treasury_curve()
        print("Treasury Curve:")
        for tenor, yield_val in sorted(treasury_curve.items()):
            print(f"  {tenor}Y: {yield_val*100:.3f}%")
    except NotImplementedError:
        print("Treasury curve fetching not implemented yet")
    
    # Example 2: Get bond reference data
    cusip = "912828YK0"
    try:
        bond_ref = provider.get_bond_reference(cusip)
        print(f"\nBond Reference for {cusip}:")
        print(f"  Issuer: {bond_ref.issuer_name}")
        print(f"  Maturity: {bond_ref.maturity_date}")
        print(f"  Coupon: {bond_ref.coupon_rate*100:.3f}%")
    except NotImplementedError:
        print(f"Bond reference fetching not implemented yet")
    
    # Example 3: Model validation
    validator = ModelValidator(provider, market_service)
    
    try:
        # Validate pricing for a specific date
        validation_result = validator.validate_bond_pricing(
            cusip=cusip,
            validation_date=date(2024, 11, 15)
        )
        
        print(f"\nValidation Result:")
        print(f"  Model Price: {validation_result.model_value:.3f}")
        print(f"  Market Price: {validation_result.market_value:.3f}")
        print(f"  Difference: {validation_result.difference:.3f}")
        print(f"  Within Tolerance: {validation_result.within_tolerance}")
        
    except NotImplementedError:
        print("Validation not available until Snowflake connection is implemented")
    
    # Example 4: Batch validation with custom tolerances
    custom_tolerances = {
        'clean_price': 0.50,  # 50 cents
        'g_spread': 0.0005,   # 5 basis points (as decimal)
        'duration': 0.05      # 5% relative tolerance
    }
    
    validator_custom = ModelValidator(
        provider, 
        market_service,
        custom_tolerances=custom_tolerances
    )
    
    # Would validate multiple bonds over a date range
    # report = validator_custom.batch_validate(
    #     cusip_list=['912828YK0', '38141GXZ2'],
    #     date_range=(date(2024, 11, 1), date(2024, 11, 30))
    # )


if __name__ == "__main__":
    # Ensure OAuth credentials are set
    required_oauth_vars = [
        'SNOWFLAKE_OAUTH_CLIENT_ID',
        'SNOWFLAKE_OAUTH_CLIENT_SECRET', 
        'SNOWFLAKE_OAUTH_SCOPE'
    ]
    
    missing_vars = [var for var in required_oauth_vars if not os.environ.get(var)]
    
    if missing_vars:
        print("Missing required OAuth environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these environment variables before running.")
    else:
        main()