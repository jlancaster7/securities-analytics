"""Test validation framework with mock Snowflake data."""

import pytest
from datetime import date, datetime
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock

from securities_analytics.validation import ModelValidator, ValidationResult
from securities_analytics.data_providers.snowflake import SnowflakeDataProvider
from securities_analytics.market_data import BondReference, MarketQuote, BondType, Rating, Sector


class TestValidatorWithMockData:
    """Test the validation framework using mock data."""
    
    @pytest.fixture
    def mock_provider(self):
        """Create a mock Snowflake data provider."""
        provider = Mock(spec=SnowflakeDataProvider)
        
        # Mock treasury curve
        provider.get_treasury_curve.return_value = {
            0.25: 0.0515,   # 3-month
            0.5: 0.0518,    # 6-month
            1.0: 0.0508,    # 1-year
            2.0: 0.0465,    # 2-year
            5.0: 0.0425,    # 5-year
            10.0: 0.0412,   # 10-year
            30.0: 0.0398,   # 30-year
        }
        
        # Mock bond reference for a fixed rate bond
        provider.get_bond_reference.return_value = BondReference(
            cusip='912828YK0',
            issuer_name='US TREASURY',
            bond_type=BondType.FIXED_RATE,
            face_value=1000,
            issue_date=datetime(2020, 11, 15),
            maturity_date=datetime(2030, 11, 15),
            coupon_rate=0.045,  # 4.5%
            coupon_frequency=2,
            day_count='Actual/Actual (ICMA)',
            rating_sp=Rating.AAA,
            sector=Sector.OTHER,  # No GOVERNMENT sector, using OTHER
            benchmark_treasury=10
        )
        
        # Mock market quote
        provider.get_bond_quote.return_value = MarketQuote(
            cusip='912828YK0',
            timestamp=datetime(2024, 11, 15),
            bid_price=99.75,
            ask_price=100.25,
            mid_price=100.00,
            bid_yield=0.0447,
            ask_yield=0.0443,
            mid_yield=0.0445,
            volume=1000000,
            source='MOCK_DATA'
        )
        
        # Mock historical analytics data
        provider.get_historical_analytics.return_value = pd.DataFrame([{
            'CUSIP': '912828YK0',
            'PRICE_DATE': date(2024, 11, 15),
            'MID_PRICE': 100.00,
            'MID_YIELD': 0.0445,
            'G_SPREAD': 33.0,  # basis points
            'BENCHMARK_SPREAD': 33.0,
            'DURATION': 8.15,
            'CONVEXITY': 75.2,
            'DV01': 0.0815,
            'DATA_SOURCE': 'MOCK_ANALYTICS'
        }])
        
        return provider
    
    @pytest.fixture
    def mock_bond(self):
        """Create a mock bond that returns predictable values."""
        bond = Mock()
        
        # Mock pricing methods
        bond.clean_price.return_value = 99.85  # Slightly different from market
        bond.dirty_price.return_value = 101.35
        bond.yield_to_maturity.return_value = 0.0447
        
        # Mock risk measures  
        bond.duration.return_value = 8.20  # Slightly different from market
        bond.convexity.return_value = 74.8
        bond.dv01.return_value = 0.0820
        
        return bond
    
    def test_basic_validation_setup(self, mock_provider):
        """Test that we can create a validator with mock provider."""
        validator = ModelValidator(mock_provider)
        
        assert validator.data_provider == mock_provider
        assert validator.market_service is not None
        assert validator.custom_tolerances == {}
    
    def test_validate_single_metric(self, mock_provider):
        """Test the internal _validate_metric method."""
        validator = ModelValidator(mock_provider)
        
        # Test price validation
        result = validator._validate_metric(
            cusip='912828YK0',
            validation_date=date(2024, 11, 15),
            metric='clean_price',
            model_value=99.85,
            market_value=100.00,
            tolerance={},
            data_source='MOCK'
        )
        
        assert result.cusip == '912828YK0'
        assert result.metric == 'clean_price'
        assert result.model_value == 99.85
        assert result.market_value == 100.00
        assert pytest.approx(result.difference, rel=1e-6) == -0.15
        assert result.within_tolerance is True  # Default tolerance is 0.25
        
        # Test spread validation (in basis points)
        result = validator._validate_metric(
            cusip='912828YK0',
            validation_date=date(2024, 11, 15),
            metric='g_spread',
            model_value=35.0,  # bps
            market_value=33.0,  # bps
            tolerance={},
            data_source='MOCK'
        )
        
        assert result.metric == 'g_spread'
        assert result.difference == 2.0
        assert result.within_tolerance is False  # Default tolerance is 2 bps
    
    def test_validation_with_custom_tolerances(self, mock_provider):
        """Test validation with custom tolerance settings."""
        custom_tolerances = {
            'clean_price': 0.50,  # 50 cents
            'g_spread': 5.0,      # 5 basis points
            'duration': 0.05      # 5% relative
        }
        
        validator = ModelValidator(mock_provider, custom_tolerances=custom_tolerances)
        
        # Now the same spread difference should pass
        # Note: g_spread values should be in decimal (not basis points) for validation
        result = validator._validate_metric(
            cusip='912828YK0',
            validation_date=date(2024, 11, 15),
            metric='g_spread',
            model_value=0.0035,  # 35 bps as decimal
            market_value=0.0033,  # 33 bps as decimal
            tolerance=custom_tolerances,
            data_source='MOCK'
        )
        
        assert result.within_tolerance is True  # 2 bps < 5 bps tolerance
        assert result.tolerance_used == 5.0
    
    def test_get_historical_data(self, mock_provider):
        """Test fetching historical data."""
        validator = ModelValidator(mock_provider)
        
        data = validator._get_historical_data('912828YK0', date(2024, 11, 15))
        
        assert data['CUSIP'] == '912828YK0'
        assert data['MID_PRICE'] == 100.00
        assert data['G_SPREAD'] == 33.0
        assert data['DURATION'] == 8.15
        
        # Verify the provider was called correctly
        mock_provider.get_historical_analytics.assert_called_once_with(
            '912828YK0', date(2024, 11, 15), date(2024, 11, 15)
        )
    
    def test_validation_report_structure(self, mock_provider):
        """Test that validation results can be aggregated into a report."""
        validator = ModelValidator(mock_provider)
        
        # Create some mock validation results
        results = []
        
        # Successful validation
        results.append(ValidationResult(
            cusip='912828YK0',
            validation_date=date(2024, 11, 15),
            metric='clean_price',
            model_value=99.85,
            market_value=100.00,
            difference=-0.15,
            percent_diff=-0.15,
            within_tolerance=True,
            tolerance_used=0.25
        ))
        
        # Failed validation
        results.append(ValidationResult(
            cusip='912828YK0',
            validation_date=date(2024, 11, 15),
            metric='duration',
            model_value=8.50,
            market_value=8.15,
            difference=0.35,
            percent_diff=4.29,
            within_tolerance=False,
            tolerance_used=0.02
        ))
        
        # Check we can access results
        assert len(results) == 2
        assert results[0].within_tolerance is True
        assert results[1].within_tolerance is False
        
        # Summary stats
        passed = sum(1 for r in results if r.within_tolerance)
        failed = sum(1 for r in results if not r.within_tolerance)
        success_rate = passed / len(results)
        
        assert passed == 1
        assert failed == 1
        assert success_rate == 0.5