"""SQL query templates for Snowflake data access."""

# Security Master Queries
SECURITY_MASTER_QUERY = """
SELECT 
    CUSIP,
    ISIN,
    TICKER,
    ISSUER_NAME,
    ISSUER_ID,
    MATURITY_DATE,
    ISSUE_DATE,
    DATED_DATE,
    FIRST_COUPON_DATE,
    COUPON_RATE,
    COUPON_FREQUENCY,
    DAY_COUNT_CONVENTION,
    BOND_TYPE,
    CURRENCY,
    FACE_VALUE,
    MINIMUM_DENOMINATION,
    OUTSTANDING_AMOUNT,
    -- Fix-to-float specific fields
    SWITCH_DATE,
    FLOAT_INDEX,
    FLOAT_SPREAD,
    FLOAT_FREQUENCY,
    FLOAT_DAY_COUNT,
    -- Callable fields
    FIRST_CALL_DATE,
    CALL_PRICE,
    CALL_TYPE,
    -- Ratings
    RATING_SP,
    RATING_SP_DATE,
    RATING_MOODY,
    RATING_MOODY_DATE,
    RATING_FITCH,
    RATING_FITCH_DATE,
    -- Classifications
    SECTOR,
    INDUSTRY,
    SUBSECTOR,
    BENCHMARK_TENOR,
    -- Flags
    IS_CALLABLE,
    IS_PUTTABLE,
    IS_SINKABLE,
    IS_CONVERTIBLE,
    HAS_CAPS,
    HAS_FLOORS,
    -- Metadata
    LAST_UPDATED,
    DATA_SOURCE
FROM {security_master_table}
WHERE CUSIP = %(cusip)s
"""

BATCH_SECURITY_QUERY = """
SELECT * FROM (
    {base_query}
) WHERE CUSIP IN ({cusips})
"""

# Historical Analytics Queries
HISTORICAL_ANALYTICS_QUERY = """
SELECT 
    CUSIP,
    PRICE_DATE,
    -- Prices
    BID_PRICE,
    MID_PRICE,
    ASK_PRICE,
    LAST_PRICE,
    -- Yields
    BID_YIELD,
    MID_YIELD,
    ASK_YIELD,
    YIELD_TO_WORST,
    -- Spreads
    G_SPREAD,
    I_SPREAD,
    BENCHMARK_SPREAD,
    OAS,
    ASW_SPREAD,
    Z_SPREAD,
    -- Risk Measures
    DURATION,
    MODIFIED_DURATION,
    CONVEXITY,
    DV01,
    SPREAD_DURATION,
    -- Volume
    VOLUME,
    TRADE_COUNT,
    -- Quality indicators
    DATA_SOURCE,
    PRICE_QUALITY,
    IS_EXECUTABLE
FROM {analytics_table}
WHERE CUSIP = %(cusip)s
  AND PRICE_DATE = %(price_date)s
"""

HISTORICAL_RANGE_QUERY = """
SELECT * FROM (
    {base_query}
) WHERE CUSIP = %(cusip)s
  AND PRICE_DATE BETWEEN %(start_date)s AND %(end_date)s
ORDER BY PRICE_DATE
"""

# Treasury Curve Queries
TREASURY_CURVE_QUERY = """
SELECT 
    CURVE_DATE,
    TENOR,
    TENOR_YEARS,
    RATE,
    CURVE_TYPE,
    IS_INTERPOLATED
FROM {treasury_rates_table}
WHERE CURVE_DATE = %(curve_date)s
  AND CURVE_TYPE = %(curve_type)s
ORDER BY TENOR_YEARS
"""

LATEST_TREASURY_CURVE_QUERY = """
WITH latest_date AS (
    SELECT MAX(CURVE_DATE) as max_date
    FROM {treasury_rates_table}
    WHERE CURVE_TYPE = %(curve_type)s
)
SELECT 
    t.CURVE_DATE,
    t.TENOR,
    t.TENOR_YEARS,
    t.RATE,
    t.CURVE_TYPE
FROM {treasury_rates_table} t
JOIN latest_date ld ON t.CURVE_DATE = ld.max_date
WHERE t.CURVE_TYPE = %(curve_type)s
ORDER BY t.TENOR_YEARS
"""

# SOFR Curve Queries
SOFR_CURVE_QUERY = """
SELECT 
    CURVE_DATE,
    TENOR,
    TENOR_DAYS,
    RATE,
    INSTRUMENT_TYPE,
    CUSIP,
    DESCRIPTION,
    DATA_SOURCE,
    UPDATE_TIME
FROM {sofr_rates_table}
WHERE CURVE_DATE = %(curve_date)s
ORDER BY TENOR_DAYS
"""

LATEST_SOFR_CURVE_QUERY = """
WITH latest_date AS (
    SELECT MAX(CURVE_DATE) as max_date
    FROM {sofr_rates_table}
)
SELECT 
    s.CURVE_DATE,
    s.TENOR,
    s.TENOR_DAYS,
    s.RATE,
    s.INSTRUMENT_TYPE,
    s.CUSIP,
    s.DESCRIPTION
FROM {sofr_rates_table} s
JOIN latest_date ld ON s.CURVE_DATE = ld.max_date
ORDER BY s.TENOR_DAYS
"""

# Call Schedule Queries
CALL_SCHEDULE_QUERY = """
SELECT 
    CUSIP,
    CALL_DATE,
    CALL_PRICE,
    CALL_TYPE,
    IS_WHOLE_CALL,
    NOTICE_DAYS
FROM {call_schedule_table}
WHERE CUSIP = %(cusip)s
  AND CALL_DATE >= %(as_of_date)s
ORDER BY CALL_DATE
"""

# Validation Queries
BOND_UNIVERSE_QUERY = """
SELECT DISTINCT CUSIP
FROM {security_master_table}
WHERE BOND_TYPE IN ('FIXED', 'FIX_TO_FLOAT', 'FLOATING', 'CALLABLE')
  AND MATURITY_DATE > %(as_of_date)s
  AND CURRENCY = 'USD'
"""

DATA_QUALITY_CHECK_QUERY = """
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT CUSIP) as unique_bonds,
    MIN(PRICE_DATE) as earliest_date,
    MAX(PRICE_DATE) as latest_date,
    SUM(CASE WHEN MID_PRICE IS NULL THEN 1 ELSE 0 END) as missing_prices,
    SUM(CASE WHEN G_SPREAD IS NULL THEN 1 ELSE 0 END) as missing_spreads
FROM {analytics_table}
WHERE PRICE_DATE = %(check_date)s
"""