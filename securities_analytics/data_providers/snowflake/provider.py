"""Snowflake implementation of DataProvider interface."""

from datetime import datetime, date, timedelta
from typing import Dict, Optional, List, Tuple
import pandas as pd
import numpy as np
from loguru import logger

from securities_analytics.market_data import (
    DataProvider, BondReference, MarketQuote, CreditCurve,
    Rating, Sector, BondType
)
from securities_analytics.curves.sofr import (
    SOFRCurveData, SOFRCurvePoint, TenorUnit
)

from .config import SnowflakeConfig, TableConfig
from .connector import SnowflakeConnector
from . import queries


class SnowflakeDataProvider(DataProvider):
    """Data provider that sources from Snowflake database tables.
    
    This provider reads from:
    - Security master for bond reference data
    - Historical analytics for prices and risk measures
    - Treasury rates for government curves
    - SOFR swap rates for forward curves
    """
    
    def __init__(self, connector: SnowflakeConnector, table_config: TableConfig):
        """Initialize with Snowflake connector and table configuration.
        
        Args:
            connector: Snowflake database connector
            table_config: Table names and column mappings
        """
        self.connector = connector
        self.config = table_config
        
    def get_treasury_curve(self, as_of_date: Optional[date] = None) -> Dict[float, float]:
        """Get treasury curve from database.
        
        Args:
            as_of_date: Date for curve (defaults to latest)
            
        Returns:
            Dictionary of tenor_years -> yield
        """
        # TODO: Implement treasury curve query
        # Use LATEST_TREASURY_CURVE_QUERY if as_of_date is None
        # Otherwise use TREASURY_CURVE_QUERY with specific date
        
        # Example implementation:
        # if as_of_date is None:
        #     query = queries.LATEST_TREASURY_CURVE_QUERY.format(
        #         treasury_rates_table=self.config.treasury_rates_table
        #     )
        #     params = {'curve_type': 'CONSTANT_MATURITY'}
        # else:
        #     query = queries.TREASURY_CURVE_QUERY.format(
        #         treasury_rates_table=self.config.treasury_rates_table
        #     )
        #     params = {
        #         'curve_date': as_of_date,
        #         'curve_type': 'CONSTANT_MATURITY'
        #     }
        # 
        # df = self.connector.execute_cached_query(query, params)
        # 
        # # Convert to dict
        # curve = {}
        # for _, row in df.iterrows():
        #     curve[float(row['TENOR_YEARS'])] = float(row['RATE']) / 100.0
        # 
        # return curve
        
        raise NotImplementedError("Treasury curve query not implemented")
    
    def get_sofr_curve(self, as_of_date: Optional[date] = None) -> Dict[float, float]:
        """Get SOFR curve as simple tenor->rate mapping.
        
        Args:
            as_of_date: Date for curve (defaults to latest)
            
        Returns:
            Dictionary of tenor_years -> rate
        """
        # TODO: Convert SOFRCurveData to simple dict
        curve_data = self.get_sofr_curve_data(as_of_date)
        
        curve = {}
        for point in curve_data.points:
            # Convert to years
            if point.tenor_unit == TenorUnit.OVERNIGHT:
                years = 1/365
            elif point.tenor_unit == TenorUnit.DAYS:
                years = point.tenor_value / 365
            elif point.tenor_unit == TenorUnit.WEEKS:
                years = point.tenor_value * 7 / 365
            elif point.tenor_unit == TenorUnit.MONTHS:
                years = point.tenor_value / 12
            elif point.tenor_unit == TenorUnit.YEARS:
                years = point.tenor_value
            else:
                continue
                
            curve[years] = point.rate
            
        return curve
    
    def get_sofr_curve_data(self, as_of_date: Optional[date] = None) -> SOFRCurveData:
        """Get detailed SOFR curve data for advanced analytics.
        
        Args:
            as_of_date: Date for curve (defaults to latest)
            
        Returns:
            SOFRCurveData object with all curve points
        """
        # TODO: Implement SOFR curve query
        # Use LATEST_SOFR_CURVE_QUERY if as_of_date is None
        # Otherwise use SOFR_CURVE_QUERY with specific date
        
        # Example implementation:
        # if as_of_date is None:
        #     query = queries.LATEST_SOFR_CURVE_QUERY.format(
        #         sofr_rates_table=self.config.sofr_rates_table
        #     )
        #     params = {}
        # else:
        #     query = queries.SOFR_CURVE_QUERY.format(
        #         sofr_rates_table=self.config.sofr_rates_table
        #     )
        #     params = {'curve_date': as_of_date}
        # 
        # df = self.connector.execute_cached_query(query, params)
        # 
        # # Convert to SOFRCurvePoint objects
        # points = []
        # for _, row in df.iterrows():
        #     tenor = row['TENOR']
        #     value, unit = self._parse_tenor(tenor)
        #     
        #     point = SOFRCurvePoint(
        #         tenor_string=tenor,
        #         tenor_value=value,
        #         tenor_unit=unit,
        #         rate=float(row['RATE']) / 100.0,
        #         description=row.get('DESCRIPTION', f'SOFR {tenor}'),
        #         cusip=row.get('CUSIP'),
        #         source=row.get('DATA_SOURCE', 'SNOWFLAKE')
        #     )
        #     points.append(point)
        # 
        # curve_date = df.iloc[0]['CURVE_DATE'] if not df.empty else as_of_date
        # return SOFRCurveData(curve_date=curve_date, points=points)
        
        raise NotImplementedError("SOFR curve query not implemented")
    
    def get_bond_quote(self, cusip: str, as_of_date: Optional[date] = None) -> MarketQuote:
        """Get bond market quote from historical analytics.
        
        Args:
            cusip: Bond CUSIP identifier
            as_of_date: Quote date (defaults to latest)
            
        Returns:
            MarketQuote object
        """
        # TODO: Implement quote query
        # query = queries.HISTORICAL_ANALYTICS_QUERY.format(
        #     analytics_table=self.config.historical_analytics_table
        # )
        # 
        # if as_of_date is None:
        #     # Get latest available date for this bond
        #     as_of_date = self._get_latest_price_date(cusip)
        # 
        # params = {
        #     'cusip': cusip,
        #     'price_date': as_of_date
        # }
        # 
        # df = self.connector.execute_cached_query(query, params)
        # 
        # if df.empty:
        #     raise ValueError(f"No quote found for {cusip} on {as_of_date}")
        # 
        # row = df.iloc[0]
        # 
        # return MarketQuote(
        #     cusip=cusip,
        #     timestamp=datetime.combine(row['PRICE_DATE'], datetime.min.time()),
        #     bid_price=float(row['BID_PRICE']) if pd.notna(row['BID_PRICE']) else None,
        #     ask_price=float(row['ASK_PRICE']) if pd.notna(row['ASK_PRICE']) else None,
        #     mid_price=float(row['MID_PRICE']),
        #     last_price=float(row.get('LAST_PRICE')) if 'LAST_PRICE' in row and pd.notna(row['LAST_PRICE']) else None,
        #     bid_yield=float(row['BID_YIELD']) if pd.notna(row['BID_YIELD']) else None,
        #     ask_yield=float(row['ASK_YIELD']) if pd.notna(row['ASK_YIELD']) else None,
        #     mid_yield=float(row['MID_YIELD']) if pd.notna(row['MID_YIELD']) else None,
        #     volume=float(row.get('VOLUME', 0)),
        #     trade_count=int(row.get('TRADE_COUNT', 0)),
        #     source=row.get('DATA_SOURCE', 'SNOWFLAKE'),
        #     quality=row.get('PRICE_QUALITY', 'INDICATIVE')
        # )
        
        raise NotImplementedError("Bond quote query not implemented")
    
    def get_bond_reference(self, cusip: str) -> BondReference:
        """Get bond reference data from security master.
        
        Args:
            cusip: Bond CUSIP identifier
            
        Returns:
            BondReference object
        """
        # TODO: Implement security master query
        # query = queries.SECURITY_MASTER_QUERY.format(
        #     security_master_table=self.config.security_master_table
        # )
        # params = {'cusip': cusip}
        # 
        # df = self.connector.execute_query(query, params)
        # 
        # if df.empty:
        #     raise ValueError(f"Bond {cusip} not found in security master")
        # 
        # row = df.iloc[0]
        # 
        # # Determine bond type
        # bond_type = self._map_bond_type(row['BOND_TYPE'])
        # 
        # # Get call schedule if callable
        # call_dates = []
        # call_prices = []
        # if row.get('IS_CALLABLE'):
        #     call_dates, call_prices = self._get_call_schedule(cusip)
        # 
        # return BondReference(
        #     cusip=cusip,
        #     isin=row.get('ISIN'),
        #     ticker=row.get('TICKER'),
        #     issuer_name=row['ISSUER_NAME'],
        #     bond_type=bond_type,
        #     face_value=float(row.get('FACE_VALUE', 1000)),
        #     issue_date=row['ISSUE_DATE'],
        #     maturity_date=row['MATURITY_DATE'],
        #     coupon_rate=float(row['COUPON_RATE']) / 100.0,
        #     coupon_frequency=int(row.get('COUPON_FREQUENCY', 2)),
        #     day_count=self._map_day_count(row.get('DAY_COUNT_CONVENTION', '30/360')),
        #     # Fix-to-float fields
        #     switch_date=row.get('SWITCH_DATE'),
        #     float_index=row.get('FLOAT_INDEX'),
        #     float_spread=float(row['FLOAT_SPREAD']) / 10000.0 if row.get('FLOAT_SPREAD') else None,
        #     # Callable fields
        #     call_dates=call_dates,
        #     call_prices=call_prices,
        #     # Ratings
        #     rating_sp=self._map_rating(row.get('RATING_SP')),
        #     rating_moody=self._map_rating(row.get('RATING_MOODY')),
        #     rating_fitch=self._map_rating(row.get('RATING_FITCH')),
        #     sector=self._map_sector(row.get('SECTOR')),
        #     outstanding_amount=float(row.get('OUTSTANDING_AMOUNT', 0)),
        #     benchmark_treasury=int(row.get('BENCHMARK_TENOR', 10))
        # )
        
        raise NotImplementedError("Bond reference query not implemented")
    
    def get_credit_curve(self, rating: Rating, sector: Sector, 
                        as_of_date: Optional[date] = None) -> CreditCurve:
        """Get credit spread curve for rating/sector combination.
        
        Args:
            rating: Credit rating
            sector: Industry sector
            as_of_date: Curve date (defaults to latest)
            
        Returns:
            CreditCurve object
        """
        # TODO: Implement credit curve logic
        # This might involve:
        # 1. Query bonds with matching rating/sector
        # 2. Calculate their spreads
        # 3. Build a curve from the spreads
        # 
        # Or if you have a dedicated credit curve table:
        # query = "SELECT * FROM CREDIT_CURVES WHERE RATING = %(rating)s AND SECTOR = %(sector)s"
        
        raise NotImplementedError("Credit curve query not implemented")
    
    def get_historical_analytics(self, cusip: str, 
                               start_date: date,
                               end_date: date) -> pd.DataFrame:
        """Get historical analytics for validation.
        
        Args:
            cusip: Bond CUSIP
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            DataFrame with historical prices and analytics
        """
        query = queries.HISTORICAL_RANGE_QUERY.format(
            base_query=queries.HISTORICAL_ANALYTICS_QUERY.format(
                analytics_table=self.config.historical_analytics_table
            )
        )
        
        params = {
            'cusip': cusip,
            'start_date': start_date,
            'end_date': end_date
        }
        
        # TODO: Execute query and return results
        # return self.connector.execute_cached_query(query, params, ttl=3600)
        
        raise NotImplementedError("Historical analytics query not implemented")
    
    def get_bond_universe(self, as_of_date: Optional[date] = None) -> List[str]:
        """Get list of all active bond CUSIPs.
        
        Args:
            as_of_date: Reference date
            
        Returns:
            List of CUSIP identifiers
        """
        # TODO: Implement universe query
        # query = queries.BOND_UNIVERSE_QUERY.format(
        #     security_master_table=self.config.security_master_table
        # )
        # params = {'as_of_date': as_of_date or date.today()}
        # 
        # df = self.connector.execute_cached_query(query, params, ttl=3600)
        # return df['CUSIP'].tolist()
        
        raise NotImplementedError("Bond universe query not implemented")
    
    # Helper methods
    
    def _parse_tenor(self, tenor: str) -> Tuple[int, TenorUnit]:
        """Parse tenor string like '3M' or '2Y' into value and unit."""
        if tenor.upper() == 'ON':
            return 0, TenorUnit.OVERNIGHT
            
        # Extract numeric and letter parts
        import re
        match = re.match(r'^(\d+)([DWMY])$', tenor.upper())
        if not match:
            raise ValueError(f"Invalid tenor format: {tenor}")
            
        value = int(match.group(1))
        unit_char = match.group(2)
        
        unit_map = {
            'D': TenorUnit.DAYS,
            'W': TenorUnit.WEEKS,
            'M': TenorUnit.MONTHS,
            'Y': TenorUnit.YEARS
        }
        
        return value, unit_map[unit_char]
    
    def _map_bond_type(self, db_type: str) -> BondType:
        """Map database bond type to enum."""
        type_map = {
            'FIXED': BondType.FIXED_RATE,
            'FIX_TO_FLOAT': BondType.FIX_TO_FLOAT,
            'FLOATING': BondType.FLOATING_RATE,
            'CALLABLE': BondType.CALLABLE,
            'ZERO': BondType.ZERO_COUPON,
        }
        return type_map.get(db_type.upper(), BondType.FIXED_RATE)
    
    def _map_rating(self, rating_str: Optional[str]) -> Optional[Rating]:
        """Map database rating to enum."""
        if not rating_str:
            return None
            
        # TODO: Implement full rating mapping
        # This is a simplified example
        rating_map = {
            'AAA': Rating.AAA,
            'AA+': Rating.AA_PLUS,
            'AA': Rating.AA,
            'AA-': Rating.AA_MINUS,
            'A+': Rating.A_PLUS,
            'A': Rating.A,
            'A-': Rating.A_MINUS,
            # Add all other ratings...
        }
        
        return rating_map.get(rating_str.upper(), Rating.NR)
    
    def _map_sector(self, sector_str: Optional[str]) -> Optional[Sector]:
        """Map database sector to enum."""
        if not sector_str:
            return None
            
        sector_map = {
            'FINANCIAL': Sector.FINANCIALS,
            'TECHNOLOGY': Sector.TECHNOLOGY,
            'ENERGY': Sector.ENERGY,
            'UTILITIES': Sector.UTILITIES,
            'CONSUMER': Sector.CONSUMER_DISCRETIONARY,
            'INDUSTRIAL': Sector.INDUSTRIALS,
            'HEALTHCARE': Sector.HEALTHCARE,
            # Add other mappings...
        }
        
        return sector_map.get(sector_str.upper(), Sector.OTHER)
    
    def _map_day_count(self, day_count_str: str) -> str:
        """Map database day count to QuantLib format."""
        dc_map = {
            '30/360': '30/360',
            'ACT/360': 'Actual/360',
            'ACT/365': 'Actual/365 (Fixed)',
            'ACT/ACT': 'Actual/Actual (ICMA)',
            'ACTUAL/360': 'Actual/360',
            'ACTUAL/365': 'Actual/365 (Fixed)',
            'ACTUAL/ACTUAL': 'Actual/Actual (ICMA)',
        }
        return dc_map.get(day_count_str.upper(), '30/360')
    
    def _get_latest_price_date(self, cusip: str) -> date:
        """Get the latest available price date for a bond."""
        # TODO: Implement query to get max price date
        # query = f"SELECT MAX(PRICE_DATE) as latest_date FROM {self.config.historical_analytics_table} WHERE CUSIP = %(cusip)s"
        # df = self.connector.execute_query(query, {'cusip': cusip})
        # return df.iloc[0]['latest_date']
        
        raise NotImplementedError("Latest price date query not implemented")
    
    def _get_call_schedule(self, cusip: str) -> Tuple[List[datetime], List[float]]:
        """Get call schedule for callable bond."""
        # TODO: Implement call schedule query
        # if self.config.call_schedule_table:
        #     query = queries.CALL_SCHEDULE_QUERY.format(
        #         call_schedule_table=self.config.call_schedule_table
        #     )
        #     params = {'cusip': cusip, 'as_of_date': date.today()}
        #     
        #     df = self.connector.execute_query(query, params)
        #     
        #     dates = df['CALL_DATE'].tolist()
        #     prices = df['CALL_PRICE'].tolist()
        #     return dates, prices
        
        return [], []