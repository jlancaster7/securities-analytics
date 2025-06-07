"""Tests for validation metrics."""

import pytest
from datetime import date
import pandas as pd
import numpy as np

from securities_analytics.validation.metrics import (
    ValidationResult, SpreadValidation, RiskValidation,
    ValidationReport, MetricStatistics, ValidationMetrics
)


class TestValidationResult:
    """Test ValidationResult dataclass."""
    
    def test_validation_result_creation(self):
        """Test creating a validation result."""
        result = ValidationResult(
            cusip='912828YK0',
            validation_date=date(2024, 11, 15),
            metric='clean_price',
            model_value=99.75,
            market_value=100.00,
            difference=-0.25,
            percent_diff=-0.25,
            within_tolerance=True,
            tolerance_used=0.50,
            data_source='BLOOMBERG'
        )
        
        assert result.cusip == '912828YK0'
        assert result.absolute_diff == 0.25
        assert result.absolute_percent_diff == 0.25
        assert result.within_tolerance is True
    
    def test_spread_validation(self):
        """Test SpreadValidation composite result."""
        g_spread = ValidationResult(
            cusip='912828YK0',
            validation_date=date(2024, 11, 15),
            metric='g_spread',
            model_value=125.5,
            market_value=126.0,
            difference=-0.5,
            percent_diff=-0.4,
            within_tolerance=True,
            tolerance_used=2.0
        )
        
        benchmark_spread = ValidationResult(
            cusip='912828YK0',
            validation_date=date(2024, 11, 15),
            metric='benchmark_spread',
            model_value=130.0,
            market_value=129.5,
            difference=0.5,
            percent_diff=0.39,
            within_tolerance=True,
            tolerance_used=2.0
        )
        
        spread_val = SpreadValidation(
            cusip='912828YK0',
            validation_date=date(2024, 11, 15),
            g_spread=g_spread,
            benchmark_spread=benchmark_spread
        )
        
        assert spread_val.all_passed is True
        
        # Add a failed validation
        spread_val.z_spread = ValidationResult(
            cusip='912828YK0',
            validation_date=date(2024, 11, 15),
            metric='z_spread',
            model_value=135.0,
            market_value=130.0,
            difference=5.0,
            percent_diff=3.85,
            within_tolerance=False,
            tolerance_used=3.0
        )
        
        assert spread_val.all_passed is False


class TestValidationMetrics:
    """Test ValidationMetrics tolerance handling."""
    
    def test_default_tolerances(self):
        """Test default tolerance values."""
        assert ValidationMetrics.get_tolerance('clean_price') == 0.25
        assert ValidationMetrics.get_tolerance('g_spread') == 0.02
        assert ValidationMetrics.get_tolerance('duration') == 0.02
        assert ValidationMetrics.get_tolerance('unknown_metric') == 0.05  # Default
    
    def test_custom_tolerances(self):
        """Test custom tolerance overrides."""
        custom = {'clean_price': 0.50, 'g_spread': 0.05}
        
        assert ValidationMetrics.get_tolerance('clean_price', custom) == 0.50
        assert ValidationMetrics.get_tolerance('g_spread', custom) == 0.05
        assert ValidationMetrics.get_tolerance('duration', custom) == 0.02  # Uses default
    
    def test_within_tolerance_absolute(self):
        """Test absolute tolerance checking (prices, spreads)."""
        # Price tolerance (absolute)
        assert ValidationMetrics.is_within_tolerance(99.80, 100.00, 'clean_price') is True  # 0.20 < 0.25
        assert ValidationMetrics.is_within_tolerance(99.50, 100.00, 'clean_price') is False  # 0.50 > 0.25
        
        # Spread tolerance (in basis points)
        assert ValidationMetrics.is_within_tolerance(0.0125, 0.0127, 'g_spread') is True  # 2bp = 0.02%
        assert ValidationMetrics.is_within_tolerance(0.0125, 0.0130, 'g_spread') is False  # 5bp > 2bp
    
    def test_within_tolerance_relative(self):
        """Test relative tolerance checking (risk measures)."""
        # Duration (relative)
        assert ValidationMetrics.is_within_tolerance(5.15, 5.00, 'duration') is False  # 3% > 2%
        assert ValidationMetrics.is_within_tolerance(5.05, 5.00, 'duration') is True   # 1% < 2%
        
        # Convexity (relative)
        assert ValidationMetrics.is_within_tolerance(52.5, 50.0, 'convexity') is True  # 5% of 50 = 2.5
        assert ValidationMetrics.is_within_tolerance(55.0, 50.0, 'convexity') is False  # 10% > 5%
        
        # Handle zero market value
        assert ValidationMetrics.is_within_tolerance(0.0, 0.0, 'duration') is True
        assert ValidationMetrics.is_within_tolerance(0.1, 0.0, 'duration') is False


class TestValidationReport:
    """Test ValidationReport generation and statistics."""
    
    def create_sample_results(self) -> list[ValidationResult]:
        """Create sample validation results for testing."""
        results = []
        
        # Mix of passed and failed validations
        test_data = [
            ('912828YK0', 'clean_price', 99.75, 100.00, True),
            ('912828YK0', 'g_spread', 125.5, 126.0, True),
            ('912828YK0', 'duration', 5.10, 5.00, False),  # Failed
            ('38141GXZ2', 'clean_price', 102.50, 102.25, True),
            ('38141GXZ2', 'g_spread', 150.0, 145.0, False),  # Failed
            ('38141GXZ2', 'duration', 4.95, 5.00, True),
        ]
        
        for cusip, metric, model, market, passed in test_data:
            diff = model - market
            pct_diff = (diff / market * 100) if market != 0 else 0
            
            results.append(ValidationResult(
                cusip=cusip,
                validation_date=date(2024, 11, 15),
                metric=metric,
                model_value=model,
                market_value=market,
                difference=diff,
                percent_diff=pct_diff,
                within_tolerance=passed,
                tolerance_used=ValidationMetrics.get_tolerance(metric)
            ))
        
        return results
    
    def test_report_from_results(self):
        """Test creating report from validation results."""
        results = self.create_sample_results()
        report = ValidationReport.from_results(
            results,
            start_date=date(2024, 11, 15),
            end_date=date(2024, 11, 15)
        )
        
        assert report.bonds_validated == 2  # 2 unique CUSIPs
        assert report.total_validations == 6
        assert report.passed_validations == 4
        assert report.failed_validations == 2
        assert report.success_rate == pytest.approx(4/6, rel=1e-3)
        
        # Check failures
        assert len(report.failures) == 2
        assert all(not f.within_tolerance for f in report.failures)
        
        # Check metric statistics
        assert 'clean_price' in report.metric_stats
        assert 'g_spread' in report.metric_stats
        assert 'duration' in report.metric_stats
        
        price_stats = report.metric_stats['clean_price']
        assert price_stats.count == 2
        assert price_stats.passed == 2
        assert price_stats.pass_rate == 1.0
    
    def test_report_to_dataframe(self):
        """Test converting report to DataFrame."""
        results = self.create_sample_results()
        report = ValidationReport.from_results(
            results,
            start_date=date(2024, 11, 15),
            end_date=date(2024, 11, 15)
        )
        
        df = report.to_dataframe()
        
        assert len(df) == 3  # 3 metrics
        assert 'metric' in df.columns
        assert 'pass_rate' in df.columns
        assert 'mae' in df.columns
        
        # Check specific metric
        price_row = df[df['metric'] == 'clean_price'].iloc[0]
        assert price_row['count'] == 2
        assert price_row['pass_rate'] == 1.0
    
    def test_empty_report(self):
        """Test creating report with no results."""
        report = ValidationReport.from_results(
            [],
            start_date=date(2024, 11, 15),
            end_date=date(2024, 11, 15)
        )
        
        assert report.bonds_validated == 0
        assert report.total_validations == 0
        assert report.success_rate == 0.0
        assert len(report.failures) == 0
        assert len(report.metric_stats) == 0


class TestMetricStatistics:
    """Test MetricStatistics calculations."""
    
    def test_metric_statistics_from_dataframe(self):
        """Test calculating statistics from validation results."""
        # Create sample data
        data = []
        for i in range(10):
            error = np.random.normal(0, 0.5)  # Random errors
            data.append({
                'metric': 'clean_price',
                'difference': error,
                'absolute_diff': abs(error),
                'within_tolerance': abs(error) < 0.25
            })
        
        df = pd.DataFrame(data)
        stats = MetricStatistics.from_dataframe(df)
        
        assert stats.metric == 'clean_price'
        assert stats.count == 10
        assert stats.passed >= 0
        assert stats.failed >= 0
        assert stats.passed + stats.failed == 10
        
        # Check statistics
        assert stats.mean_absolute_error >= 0
        assert stats.root_mean_square_error >= stats.mean_absolute_error
        assert stats.max_absolute_error >= stats.mean_absolute_error
        
        # Check percentiles
        assert 0 <= stats.percentiles[25] <= stats.percentiles[50]
        assert stats.percentiles[50] <= stats.percentiles[75]
        assert stats.percentiles[75] <= stats.percentiles[95]