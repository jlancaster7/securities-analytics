"""Example of Snowflake integration and model validation.

This script demonstrates:
1. Connecting to Snowflake
2. Loading market data
3. Creating and pricing bonds
4. Validating model outputs against historical data
"""

import os
from datetime import date, datetime, timedelta
from loguru import logger
import pandas as pd

# Import our components
from securities_analytics.data_providers.snowflake import (
    SnowflakeConfig, TableConfig, SnowflakeConnector, SnowflakeDataProvider
)
from securities_analytics.market_data import MarketDataService
from securities_analytics.validation import ModelValidator


def setup_snowflake_connection():
    """Set up Snowflake connection using environment variables."""
    # Configuration from environment
    config = SnowflakeConfig.from_env()
    
    # Or configure manually
    # config = SnowflakeConfig(
    #     account='your_account',
    #     warehouse='your_warehouse',
    #     database='MARKET_DATA',
    #     schema='BONDS',
    #     role='ANALYST_ROLE',
    #     username='your_username',
    #     password='your_password'
    # )
    
    # Table configuration
    table_config = TableConfig(
        security_master_table='SECURITY_MASTER',
        historical_analytics_table='BOND_ANALYTICS_DAILY',
        treasury_rates_table='TREASURY_CURVES',
        sofr_rates_table='SOFR_CURVES',
        call_schedule_table='CALL_SCHEDULES'
    )
    
    # Create connector
    connector = SnowflakeConnector(config)
    
    # Create data provider
    provider = SnowflakeDataProvider(connector, table_config)
    
    return provider


def validate_single_bond_example(provider: SnowflakeDataProvider):
    """Example of validating a single bond."""
    logger.info("Validating single bond pricing...")
    
    # Create market data service
    market_service = MarketDataService(provider=provider)
    
    # Create validator
    validator = ModelValidator(provider, market_service)
    
    # Validate a specific bond
    cusip = '912828YK0'  # Example CUSIP
    validation_date = date(2024, 11, 15)
    
    try:
        # Validate pricing
        pricing_result = validator.validate_bond_pricing(cusip, validation_date)
        
        logger.info(f"Pricing Validation for {cusip}:")
        logger.info(f"  Model Price: {pricing_result.model_value:.3f}")
        logger.info(f"  Market Price: {pricing_result.market_value:.3f}")
        logger.info(f"  Difference: {pricing_result.difference:.3f}")
        logger.info(f"  Within Tolerance: {pricing_result.within_tolerance}")
        
        # Validate spreads
        spread_result = validator.validate_spreads(cusip, validation_date)
        
        logger.info(f"\nSpread Validation for {cusip}:")
        logger.info(f"  G-Spread - Model: {spread_result.g_spread.model_value:.1f} bps, "
                   f"Market: {spread_result.g_spread.market_value:.1f} bps")
        logger.info(f"  Benchmark Spread - Model: {spread_result.benchmark_spread.model_value:.1f} bps, "
                   f"Market: {spread_result.benchmark_spread.market_value:.1f} bps")
        
        # Validate risk measures
        risk_result = validator.validate_risk_measures(cusip, validation_date)
        
        logger.info(f"\nRisk Validation for {cusip}:")
        logger.info(f"  Duration - Model: {risk_result.duration.model_value:.2f}, "
                   f"Market: {risk_result.duration.market_value:.2f}")
        logger.info(f"  Convexity - Model: {risk_result.convexity.model_value:.2f}, "
                   f"Market: {risk_result.convexity.market_value:.2f}")
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")


def batch_validation_example(provider: SnowflakeDataProvider):
    """Example of batch validation across multiple bonds and dates."""
    logger.info("Running batch validation...")
    
    # Create validator with custom tolerances
    custom_tolerances = {
        'clean_price': 0.50,  # 50 cents tolerance
        'g_spread': 0.03,     # 3 bps tolerance
        'duration': 0.03      # 3% relative tolerance
    }
    
    market_service = MarketDataService(provider=provider)
    validator = ModelValidator(provider, market_service, custom_tolerances)
    
    # Define universe and date range
    cusip_list = [
        '912828YK0',  # Treasury
        '38141GXZ2',  # Corporate fixed
        '38259PAC9',  # Fix-to-float
        # Add more CUSIPs
    ]
    
    start_date = date(2024, 11, 1)
    end_date = date(2024, 11, 30)
    
    # Run validation
    report = validator.batch_validate(
        cusip_list=cusip_list,
        date_range=(start_date, end_date),
        metrics=['pricing', 'spreads', 'risk']
    )
    
    # Display results
    logger.info(f"\nValidation Report Summary:")
    logger.info(f"  Period: {report.start_date} to {report.end_date}")
    logger.info(f"  Bonds Validated: {report.bonds_validated}")
    logger.info(f"  Total Validations: {report.total_validations}")
    logger.info(f"  Success Rate: {report.success_rate:.1%}")
    logger.info(f"  Mean Absolute Error: {report.mean_absolute_error:.3f}")
    logger.info(f"  Max Absolute Error: {report.max_absolute_error:.3f}")
    
    # Show metric-level statistics
    logger.info("\nMetric Statistics:")
    stats_df = report.to_dataframe()
    print(stats_df.to_string())
    
    # Show failures
    if report.failures:
        logger.warning(f"\nFound {len(report.failures)} validation failures:")
        failures_df = pd.DataFrame([f.__dict__ for f in report.failures[:10]])  # First 10
        print(failures_df[['cusip', 'validation_date', 'metric', 'model_value', 
                          'market_value', 'difference']].to_string())
    
    # Save detailed results
    report_path = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    all_results_df = pd.DataFrame([r.__dict__ for r in report.failures])
    all_results_df.to_csv(report_path, index=False)
    logger.info(f"\nDetailed results saved to {report_path}")


def market_data_example(provider: SnowflakeDataProvider):
    """Example of using Snowflake data with market data service."""
    logger.info("Loading market data from Snowflake...")
    
    # Create market data service
    market_service = MarketDataService(provider=provider)
    
    # Get curves
    as_of_date = date(2024, 11, 15)
    
    try:
        # Get treasury curve
        treasury_curve = provider.get_treasury_curve(as_of_date)
        logger.info(f"Treasury Curve for {as_of_date}:")
        for tenor, rate in sorted(treasury_curve.items()):
            logger.info(f"  {tenor}Y: {rate*100:.3f}%")
        
        # Get SOFR curve
        sofr_curve_data = provider.get_sofr_curve_data(as_of_date)
        logger.info(f"\nSOFR Curve for {as_of_date}:")
        logger.info(f"  Points: {len(sofr_curve_data.points)}")
        logger.info(f"  Overnight Rate: {sofr_curve_data.overnight_rate*100:.3f}%")
        
        # Get bond reference
        cusip = '38259PAC9'  # Example fix-to-float
        bond_ref = provider.get_bond_reference(cusip)
        
        logger.info(f"\nBond Reference for {cusip}:")
        logger.info(f"  Issuer: {bond_ref.issuer_name}")
        logger.info(f"  Type: {bond_ref.bond_type.value}")
        logger.info(f"  Coupon: {bond_ref.coupon_rate*100:.3f}%")
        logger.info(f"  Maturity: {bond_ref.maturity_date}")
        
        if bond_ref.switch_date:
            logger.info(f"  Switch Date: {bond_ref.switch_date}")
            logger.info(f"  Float Index: {bond_ref.float_index}")
            logger.info(f"  Float Spread: {bond_ref.float_spread*10000:.0f} bps")
        
        # Get market quote
        quote = provider.get_bond_quote(cusip, as_of_date)
        logger.info(f"\nMarket Quote for {cusip}:")
        logger.info(f"  Bid: {quote.bid_price:.3f}")
        logger.info(f"  Mid: {quote.mid_price:.3f}")
        logger.info(f"  Ask: {quote.ask_price:.3f}")
        logger.info(f"  Mid Yield: {quote.mid_yield*100:.3f}%")
        
    except Exception as e:
        logger.error(f"Failed to load market data: {e}")


def main():
    """Main entry point."""
    # Set up logging
    logger.add("snowflake_integration.log", rotation="1 day")
    
    try:
        # Set up Snowflake connection
        logger.info("Setting up Snowflake connection...")
        provider = setup_snowflake_connection()
        
        # Test connection
        # with provider.connector as conn:
        #     if conn.test_connection():
        #         logger.info("Snowflake connection successful!")
        #     else:
        #         logger.error("Failed to connect to Snowflake")
        #         return
        
        # Run examples
        market_data_example(provider)
        validate_single_bond_example(provider)
        batch_validation_example(provider)
        
    except Exception as e:
        logger.error(f"Integration failed: {e}")
        raise


if __name__ == "__main__":
    main()