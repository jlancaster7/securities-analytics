"""Validation metrics and result structures."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class ValidationResult:
    """Result of validating a single metric."""
    cusip: str
    validation_date: date
    metric: str
    model_value: float
    market_value: float
    difference: float
    percent_diff: float
    within_tolerance: bool
    tolerance_used: float
    data_source: Optional[str] = None
    
    @property
    def absolute_diff(self) -> float:
        """Absolute difference between model and market."""
        return abs(self.difference)
    
    @property
    def absolute_percent_diff(self) -> float:
        """Absolute percentage difference."""
        return abs(self.percent_diff)


@dataclass
class SpreadValidation:
    """Validation results for spread calculations."""
    cusip: str
    validation_date: date
    g_spread: ValidationResult
    benchmark_spread: ValidationResult
    z_spread: Optional[ValidationResult] = None
    oas: Optional[ValidationResult] = None
    
    @property
    def all_passed(self) -> bool:
        """Check if all spread validations passed."""
        results = [self.g_spread, self.benchmark_spread]
        if self.z_spread:
            results.append(self.z_spread)
        if self.oas:
            results.append(self.oas)
        return all(r.within_tolerance for r in results)


@dataclass 
class RiskValidation:
    """Validation results for risk measures."""
    cusip: str
    validation_date: date
    duration: ValidationResult
    convexity: ValidationResult
    dv01: ValidationResult
    spread_duration: Optional[ValidationResult] = None
    
    @property
    def all_passed(self) -> bool:
        """Check if all risk validations passed."""
        results = [self.duration, self.convexity, self.dv01]
        if self.spread_duration:
            results.append(self.spread_duration)
        return all(r.within_tolerance for r in results)


@dataclass
class ValidationReport:
    """Summary report of validation results."""
    start_date: date
    end_date: date
    bonds_validated: int
    total_validations: int
    passed_validations: int
    failed_validations: int
    
    # Summary statistics by metric
    metric_stats: Dict[str, 'MetricStatistics']
    
    # Failed validations for investigation
    failures: List[ValidationResult]
    
    # Overall metrics
    success_rate: float
    mean_absolute_error: float
    root_mean_square_error: float
    max_absolute_error: float
    
    @classmethod
    def from_results(cls, results: List[ValidationResult], 
                    start_date: date, end_date: date) -> 'ValidationReport':
        """Create report from list of validation results."""
        if not results:
            return cls(
                start_date=start_date,
                end_date=end_date,
                bonds_validated=0,
                total_validations=0,
                passed_validations=0,
                failed_validations=0,
                metric_stats={},
                failures=[],
                success_rate=0.0,
                mean_absolute_error=0.0,
                root_mean_square_error=0.0,
                max_absolute_error=0.0
            )
        
        # Calculate statistics
        df = pd.DataFrame([r.__dict__ for r in results])
        # Add computed properties
        df['absolute_diff'] = df['difference'].abs()
        
        bonds_validated = df['cusip'].nunique()
        total_validations = len(results)
        passed = df['within_tolerance'].sum()
        failed = total_validations - passed
        
        # Metric-level statistics
        metric_stats = {}
        for metric in df['metric'].unique():
            metric_df = df[df['metric'] == metric]
            metric_stats[metric] = MetricStatistics.from_dataframe(metric_df)
        
        # Failed validations
        failures = [r for r in results if not r.within_tolerance]
        
        # Overall metrics
        success_rate = passed / total_validations if total_validations > 0 else 0.0
        mae = df['absolute_diff'].mean()
        rmse = np.sqrt((df['difference'] ** 2).mean())
        max_error = df['absolute_diff'].max()
        
        return cls(
            start_date=start_date,
            end_date=end_date,
            bonds_validated=bonds_validated,
            total_validations=total_validations,
            passed_validations=passed,
            failed_validations=failed,
            metric_stats=metric_stats,
            failures=failures,
            success_rate=success_rate,
            mean_absolute_error=mae,
            root_mean_square_error=rmse,
            max_absolute_error=max_error
        )
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert report to DataFrame for analysis."""
        rows = []
        for metric, stats in self.metric_stats.items():
            rows.append({
                'metric': metric,
                'count': stats.count,
                'pass_rate': stats.pass_rate,
                'mean_error': stats.mean_error,
                'mae': stats.mean_absolute_error,
                'rmse': stats.root_mean_square_error,
                'max_error': stats.max_absolute_error,
                'std_error': stats.std_error
            })
        return pd.DataFrame(rows)


@dataclass
class MetricStatistics:
    """Statistics for a specific metric."""
    metric: str
    count: int
    passed: int
    failed: int
    pass_rate: float
    mean_error: float
    mean_absolute_error: float
    root_mean_square_error: float
    max_absolute_error: float
    std_error: float
    percentiles: Dict[int, float]  # 25th, 50th, 75th, 95th percentiles
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> 'MetricStatistics':
        """Calculate statistics from validation results."""
        metric = df['metric'].iloc[0]
        count = len(df)
        passed = df['within_tolerance'].sum()
        failed = count - passed
        
        errors = df['difference']
        abs_errors = df['absolute_diff']
        
        return cls(
            metric=metric,
            count=count,
            passed=passed,
            failed=failed,
            pass_rate=passed / count if count > 0 else 0.0,
            mean_error=errors.mean(),
            mean_absolute_error=abs_errors.mean(),
            root_mean_square_error=np.sqrt((errors ** 2).mean()),
            max_absolute_error=abs_errors.max(),
            std_error=errors.std(),
            percentiles={
                25: abs_errors.quantile(0.25),
                50: abs_errors.quantile(0.50),
                75: abs_errors.quantile(0.75),
                95: abs_errors.quantile(0.95)
            }
        )


class ValidationMetrics:
    """Tolerance levels and metrics configuration."""
    
    # Default tolerances by metric type
    DEFAULT_TOLERANCES = {
        # Prices (in points)
        'clean_price': 0.25,
        'dirty_price': 0.25,
        'model_price': 0.25,
        
        # Yields (in basis points)
        'yield_to_maturity': 0.02,  # 2 bps
        'yield_to_worst': 0.02,
        'yield_to_call': 0.02,
        
        # Spreads (in basis points)  
        'g_spread': 0.02,  # 2 bps
        'benchmark_spread': 0.02,
        'z_spread': 0.03,  # 3 bps (harder to match exactly)
        'oas': 0.05,  # 5 bps (most complex)
        
        # Risk measures
        'duration': 0.02,  # 2% relative
        'modified_duration': 0.02,
        'convexity': 0.05,  # 5% relative
        'dv01': 0.02,  # 2% relative
        'spread_duration': 0.03,  # 3% relative
    }
    
    @classmethod
    def get_tolerance(cls, metric: str, custom_tolerances: Optional[Dict[str, float]] = None) -> float:
        """Get tolerance for a specific metric.
        
        Args:
            metric: Metric name
            custom_tolerances: Optional custom tolerance overrides
            
        Returns:
            Tolerance value
        """
        if custom_tolerances and metric in custom_tolerances:
            return custom_tolerances[metric]
        return cls.DEFAULT_TOLERANCES.get(metric.lower(), 0.05)
    
    @classmethod
    def is_within_tolerance(cls, model_value: float, market_value: float, 
                          metric: str, custom_tolerances: Optional[Dict[str, float]] = None) -> bool:
        """Check if model value is within tolerance of market value.
        
        Args:
            model_value: Value from model
            market_value: Value from market/database
            metric: Metric name
            custom_tolerances: Optional custom tolerances
            
        Returns:
            True if within tolerance
        """
        tolerance = cls.get_tolerance(metric, custom_tolerances)
        
        # For risk measures, use relative tolerance
        if metric.lower() in ['duration', 'modified_duration', 'convexity', 'dv01', 'spread_duration']:
            if market_value == 0:
                return model_value == 0
            relative_diff = abs((model_value - market_value) / market_value)
            return relative_diff <= tolerance
        
        # For prices and spreads, use absolute tolerance
        else:
            # Convert basis points to decimal for yield/spread metrics
            if metric.lower() in ['yield_to_maturity', 'yield_to_worst', 'yield_to_call', 
                                 'g_spread', 'benchmark_spread', 'z_spread', 'oas']:
                tolerance = tolerance / 100.0  # Convert bps to decimal
            
            return abs(model_value - market_value) <= tolerance