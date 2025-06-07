"""Model validation against historical market data."""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd
import numpy as np
from loguru import logger
import QuantLib as ql

from securities_analytics.bonds.fix_to_float.bond import FixToFloatBond
from securities_analytics.bonds.floating_rate.bond import FloatingRateBond
from securities_analytics.bonds.fixed_rate_bullets.vanilla.bond import FixedRateQLBond
from securities_analytics.bonds.analytics.spreads import BondSpreadCalculator
from securities_analytics.market_data import MarketDataService, BondType
from securities_analytics.data_providers.snowflake.provider import SnowflakeDataProvider

from .metrics import (
    ValidationResult, SpreadValidation, RiskValidation,
    ValidationReport, ValidationMetrics
)


class ModelValidator:
    """Validates model outputs against historical market data.
    
    This validator:
    1. Creates bonds from reference data
    2. Prices them using market curves
    3. Compares model outputs to historical analytics
    4. Generates validation reports
    """
    
    def __init__(self, 
                 data_provider: SnowflakeDataProvider,
                 market_service: Optional[MarketDataService] = None,
                 custom_tolerances: Optional[Dict[str, float]] = None):
        """Initialize validator.
        
        Args:
            data_provider: Snowflake data provider
            market_service: Market data service (creates one if not provided)
            custom_tolerances: Optional custom tolerance overrides
        """
        self.data_provider = data_provider
        self.market_service = market_service or MarketDataService(provider=data_provider)
        self.custom_tolerances = custom_tolerances or {}
        
    def validate_bond_pricing(self, cusip: str, validation_date: date,
                            tolerance: Optional[Dict[str, float]] = None) -> ValidationResult:
        """Validate bond pricing against historical data.
        
        Args:
            cusip: Bond CUSIP
            validation_date: Date to validate
            tolerance: Optional tolerance overrides
            
        Returns:
            ValidationResult for pricing
        """
        try:
            # Set evaluation date
            ql_date = ql.Date(validation_date.day, validation_date.month, validation_date.year)
            ql.Settings.instance().evaluationDate = ql_date
            
            # Get bond reference and create bond object
            bond_ref = self.data_provider.get_bond_reference(cusip)
            bond = self._create_bond(bond_ref, validation_date)
            
            # Get market curves
            treasury_curve = self.data_provider.get_treasury_curve(validation_date)
            
            # Price the bond
            if bond_ref.bond_type in [BondType.FIX_TO_FLOAT, BondType.FLOATING_RATE]:
                # Need SOFR curve for floating bonds
                sofr_handle = self.market_service.get_sofr_curve_handle(validation_date)
                model_price = bond.clean_price(sofr_handle)
            else:
                # Fixed rate bonds can use treasury curve
                curve_handle = self._build_curve_handle(treasury_curve)
                model_price = bond.clean_price(curve_handle)
            
            # Get historical price
            historical_data = self._get_historical_data(cusip, validation_date)
            market_price = historical_data['MID_PRICE']
            
            # Calculate differences
            difference = model_price - market_price
            percent_diff = (difference / market_price) * 100 if market_price != 0 else 0
            
            # Check tolerance
            tol = tolerance or self.custom_tolerances
            tolerance_value = ValidationMetrics.get_tolerance('clean_price', tol)
            within_tolerance = ValidationMetrics.is_within_tolerance(
                model_price, market_price, 'clean_price', tol
            )
            
            return ValidationResult(
                cusip=cusip,
                validation_date=validation_date,
                metric='clean_price',
                model_value=model_price,
                market_value=market_price,
                difference=difference,
                percent_diff=percent_diff,
                within_tolerance=within_tolerance,
                tolerance_used=tolerance_value,
                data_source=historical_data.get('DATA_SOURCE')
            )
            
        except Exception as e:
            logger.error(f"Error validating pricing for {cusip} on {validation_date}: {e}")
            raise
    
    def validate_spreads(self, cusip: str, validation_date: date,
                        tolerance: Optional[Dict[str, float]] = None) -> SpreadValidation:
        """Validate spread calculations against historical data.
        
        Args:
            cusip: Bond CUSIP
            validation_date: Date to validate
            tolerance: Optional tolerance overrides
            
        Returns:
            SpreadValidation results
        """
        try:
            # Set evaluation date
            ql_date = ql.Date(validation_date.day, validation_date.month, validation_date.year)
            ql.Settings.instance().evaluationDate = ql_date
            
            # Get bond and create spread calculator
            bond_ref = self.data_provider.get_bond_reference(cusip)
            bond = self._create_bond(bond_ref, validation_date)
            
            # Get curves
            treasury_curve = self.data_provider.get_treasury_curve(validation_date)
            
            # Create spread calculator
            calculator = BondSpreadCalculator(
                bond=bond,
                treasury_curve=treasury_curve,
                original_benchmark_tenor=bond_ref.benchmark_treasury
            )
            
            # Get market quote for spread calculations
            quote = self.data_provider.get_bond_quote(cusip, validation_date)
            model_spreads = calculator.spread_from_price(quote.mid_price)
            
            # Get historical spreads
            historical_data = self._get_historical_data(cusip, validation_date)
            
            # Validate each spread type
            tol = tolerance or self.custom_tolerances
            
            g_spread_result = self._validate_metric(
                cusip, validation_date, 'g_spread',
                model_spreads['g_spread'] * 10000,  # Convert to bps
                historical_data['G_SPREAD'],
                tol, historical_data.get('DATA_SOURCE')
            )
            
            benchmark_spread_result = self._validate_metric(
                cusip, validation_date, 'benchmark_spread',
                model_spreads['benchmark_spread'] * 10000,
                historical_data['BENCHMARK_SPREAD'],
                tol, historical_data.get('DATA_SOURCE')
            )
            
            # Z-spread if available
            z_spread_result = None
            if 'z_spread' in model_spreads and pd.notna(historical_data.get('Z_SPREAD')):
                z_spread_result = self._validate_metric(
                    cusip, validation_date, 'z_spread',
                    model_spreads['z_spread'] * 10000,
                    historical_data['Z_SPREAD'],
                    tol, historical_data.get('DATA_SOURCE')
                )
            
            # OAS if available (would need option model)
            oas_result = None
            if pd.notna(historical_data.get('OAS')):
                # TODO: Implement OAS calculation with option model
                pass
            
            return SpreadValidation(
                cusip=cusip,
                validation_date=validation_date,
                g_spread=g_spread_result,
                benchmark_spread=benchmark_spread_result,
                z_spread=z_spread_result,
                oas=oas_result
            )
            
        except Exception as e:
            logger.error(f"Error validating spreads for {cusip} on {validation_date}: {e}")
            raise
    
    def validate_risk_measures(self, cusip: str, validation_date: date,
                             tolerance: Optional[Dict[str, float]] = None) -> RiskValidation:
        """Validate risk measures against historical data.
        
        Args:
            cusip: Bond CUSIP
            validation_date: Date to validate
            tolerance: Optional tolerance overrides
            
        Returns:
            RiskValidation results
        """
        try:
            # Set evaluation date
            ql_date = ql.Date(validation_date.day, validation_date.month, validation_date.year)
            ql.Settings.instance().evaluationDate = ql_date
            
            # Get bond
            bond_ref = self.data_provider.get_bond_reference(cusip)
            bond = self._create_bond(bond_ref, validation_date)
            
            # Get appropriate curve
            if bond_ref.bond_type in [BondType.FIX_TO_FLOAT, BondType.FLOATING_RATE]:
                curve_handle = self.market_service.get_sofr_curve_handle(validation_date)
            else:
                treasury_curve = self.data_provider.get_treasury_curve(validation_date)
                curve_handle = self._build_curve_handle(treasury_curve)
            
            # Calculate risk measures
            model_duration = bond.duration(curve_handle)
            model_convexity = bond.convexity(curve_handle)
            model_dv01 = bond.dv01(curve_handle)
            
            # Get historical data
            historical_data = self._get_historical_data(cusip, validation_date)
            
            # Validate each measure
            tol = tolerance or self.custom_tolerances
            
            duration_result = self._validate_metric(
                cusip, validation_date, 'duration',
                model_duration, historical_data['DURATION'],
                tol, historical_data.get('DATA_SOURCE')
            )
            
            convexity_result = self._validate_metric(
                cusip, validation_date, 'convexity',
                model_convexity, historical_data['CONVEXITY'],
                tol, historical_data.get('DATA_SOURCE')
            )
            
            dv01_result = self._validate_metric(
                cusip, validation_date, 'dv01',
                model_dv01, historical_data['DV01'],
                tol, historical_data.get('DATA_SOURCE')
            )
            
            # Spread duration for floating bonds
            spread_duration_result = None
            if hasattr(bond, 'get_spread_duration') and pd.notna(historical_data.get('SPREAD_DURATION')):
                model_spread_dur = bond.get_spread_duration(curve_handle)
                spread_duration_result = self._validate_metric(
                    cusip, validation_date, 'spread_duration',
                    model_spread_dur, historical_data['SPREAD_DURATION'],
                    tol, historical_data.get('DATA_SOURCE')
                )
            
            return RiskValidation(
                cusip=cusip,
                validation_date=validation_date,
                duration=duration_result,
                convexity=convexity_result,
                dv01=dv01_result,
                spread_duration=spread_duration_result
            )
            
        except Exception as e:
            logger.error(f"Error validating risk measures for {cusip} on {validation_date}: {e}")
            raise
    
    def batch_validate(self, cusip_list: List[str],
                      date_range: Tuple[date, date],
                      metrics: List[str] = None) -> ValidationReport:
        """Validate multiple bonds over a date range.
        
        Args:
            cusip_list: List of CUSIPs to validate
            date_range: (start_date, end_date) tuple
            metrics: Specific metrics to validate (default: all)
            
        Returns:
            ValidationReport with all results
        """
        start_date, end_date = date_range
        if metrics is None:
            metrics = ['pricing', 'spreads', 'risk']
        
        all_results = []
        
        # Generate business days in range
        current_date = start_date
        dates_to_validate = []
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:
                dates_to_validate.append(current_date)
            current_date += timedelta(days=1)
        
        # Validate each bond on each date
        for cusip in cusip_list:
            logger.info(f"Validating {cusip}...")
            
            for val_date in dates_to_validate:
                try:
                    # Pricing validation
                    if 'pricing' in metrics:
                        result = self.validate_bond_pricing(cusip, val_date)
                        all_results.append(result)
                    
                    # Spread validation
                    if 'spreads' in metrics:
                        spread_val = self.validate_spreads(cusip, val_date)
                        all_results.extend([
                            spread_val.g_spread,
                            spread_val.benchmark_spread
                        ])
                        if spread_val.z_spread:
                            all_results.append(spread_val.z_spread)
                        if spread_val.oas:
                            all_results.append(spread_val.oas)
                    
                    # Risk validation
                    if 'risk' in metrics:
                        risk_val = self.validate_risk_measures(cusip, val_date)
                        all_results.extend([
                            risk_val.duration,
                            risk_val.convexity,
                            risk_val.dv01
                        ])
                        if risk_val.spread_duration:
                            all_results.append(risk_val.spread_duration)
                    
                except Exception as e:
                    logger.warning(f"Failed to validate {cusip} on {val_date}: {e}")
                    continue
        
        # Generate report
        return ValidationReport.from_results(all_results, start_date, end_date)
    
    def validate_single_date(self, validation_date: date,
                           universe: Optional[List[str]] = None) -> ValidationReport:
        """Validate entire universe on a single date.
        
        Args:
            validation_date: Date to validate
            universe: List of CUSIPs (defaults to all active bonds)
            
        Returns:
            ValidationReport
        """
        if universe is None:
            universe = self.data_provider.get_bond_universe(validation_date)
        
        return self.batch_validate(universe, (validation_date, validation_date))
    
    # Helper methods
    
    def _create_bond(self, bond_ref, validation_date: date):
        """Create appropriate bond object from reference data."""
        # TODO: Implement bond creation logic based on type
        # This would use the bond reference data to create the appropriate
        # bond object (FixToFloatBond, FloatingRateBond, VanillaFixedRateBond)
        
        raise NotImplementedError("Bond creation from reference not implemented")
    
    def _get_historical_data(self, cusip: str, validation_date: date) -> pd.Series:
        """Get historical analytics data for a specific date."""
        df = self.data_provider.get_historical_analytics(
            cusip, validation_date, validation_date
        )
        
        if df.empty:
            raise ValueError(f"No historical data for {cusip} on {validation_date}")
        
        return df.iloc[0]
    
    def _validate_metric(self, cusip: str, validation_date: date,
                        metric: str, model_value: float, market_value: float,
                        tolerance: Dict[str, float], data_source: str) -> ValidationResult:
        """Validate a single metric."""
        difference = model_value - market_value
        percent_diff = (difference / market_value) * 100 if market_value != 0 else 0
        
        tolerance_value = ValidationMetrics.get_tolerance(metric, tolerance)
        within_tolerance = ValidationMetrics.is_within_tolerance(
            model_value, market_value, metric, tolerance
        )
        
        return ValidationResult(
            cusip=cusip,
            validation_date=validation_date,
            metric=metric,
            model_value=model_value,
            market_value=market_value,
            difference=difference,
            percent_diff=percent_diff,
            within_tolerance=within_tolerance,
            tolerance_used=tolerance_value,
            data_source=data_source
        )
    
    def _build_curve_handle(self, treasury_curve: Dict[float, float]) -> ql.YieldTermStructureHandle:
        """Build QuantLib curve handle from treasury curve."""
        # Convert to QuantLib format
        dates = []
        rates = []
        
        ref_date = ql.Settings.instance().evaluationDate
        
        for tenor_years, rate in sorted(treasury_curve.items()):
            date = ref_date + ql.Period(int(tenor_years * 12), ql.Months)
            dates.append(date)
            rates.append(rate)
        
        curve = ql.ZeroCurve(dates, rates, ql.Actual360())
        return ql.YieldTermStructureHandle(curve)