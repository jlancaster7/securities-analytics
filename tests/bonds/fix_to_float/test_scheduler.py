from datetime import datetime

import pytest
import QuantLib as ql

from securities_analytics.bonds.fix_to_float.schedulers.scheduler import (
    FixToFloatScheduleGenerator,
)


class TestFixToFloatScheduleGenerator:
    """Test suite for fix-to-float bond schedule generation."""
    
    @pytest.fixture
    def basic_scheduler(self):
        """Create a basic fix-to-float scheduler for testing."""
        return FixToFloatScheduleGenerator(
            issue_date=datetime(2024, 1, 15),
            switch_date=datetime(2027, 1, 15),  # 3 years fixed
            maturity_date=datetime(2034, 1, 15),  # 10 years total
            fixed_frequency=2,  # Semiannual
            floating_frequency=4,  # Quarterly
            calendar=ql.UnitedStates(ql.UnitedStates.GovernmentBond),
            business_day_convention=ql.Following,
        )
    
    def test_fixed_schedule_generation(self, basic_scheduler):
        """Test that fixed schedule is generated correctly."""
        fixed_schedule = basic_scheduler.generate_fixed_schedule()
        
        # Should have semiannual payments from issue to switch
        # 3 years * 2 payments/year = 6 periods + 1 for start date
        assert len(fixed_schedule) == 7
        
        # First date should be issue date (adjusted for business day)
        # Jan 15, 2024 is MLK Day, so it adjusts to Jan 16
        assert fixed_schedule[0] == ql.Date(16, 1, 2024)
        
        # Last date should be switch date
        assert fixed_schedule[-1] == ql.Date(15, 1, 2027)
        
        # Check spacing is approximately 6 months
        for i in range(1, len(fixed_schedule)):
            days_diff = fixed_schedule[i] - fixed_schedule[i-1]
            assert 175 <= days_diff <= 190  # ~6 months
    
    def test_floating_schedule_generation(self, basic_scheduler):
        """Test that floating schedule is generated correctly."""
        floating_schedule = basic_scheduler.generate_floating_schedule()
        
        # Should have quarterly payments from switch to maturity
        # 7 years * 4 payments/year = 28 periods + 1 for start date
        assert len(floating_schedule) == 29
        
        # First date should be switch date
        assert floating_schedule[0] == ql.Date(15, 1, 2027)
        
        # Last date should be maturity date (adjusted for business day)
        # Jan 15, 2034 is Sunday, Jan 16 is MLK Day, so it adjusts to Jan 17 
        assert floating_schedule[-1] == ql.Date(17, 1, 2034)
        
        # Check spacing is approximately 3 months
        for i in range(1, len(floating_schedule)):
            days_diff = floating_schedule[i] - floating_schedule[i-1]
            assert 85 <= days_diff <= 95  # ~3 months
    
    def test_combined_schedule_generation(self, basic_scheduler):
        """Test that combined schedule merges both periods correctly."""
        combined_schedule = basic_scheduler.generate()
        
        # Should have all unique dates from both schedules
        # Note: switch date appears in both, so total is less than sum
        assert len(combined_schedule) > 0
        
        # First date should be issue date (adjusted for business day)
        assert combined_schedule[0] == ql.Date(16, 1, 2024)
        
        # Last date should be maturity date (adjusted for business day)
        assert combined_schedule[-1] == ql.Date(17, 1, 2034)
        
        # Dates should be in order
        for i in range(1, len(combined_schedule)):
            assert combined_schedule[i] > combined_schedule[i-1]
    
    def test_business_day_adjustment(self):
        """Test that schedules respect business day conventions."""
        # Create scheduler with dates that fall on weekends
        scheduler = FixToFloatScheduleGenerator(
            issue_date=datetime(2024, 1, 13),  # Saturday
            switch_date=datetime(2027, 1, 16),  # Saturday
            maturity_date=datetime(2034, 1, 14),  # Saturday
            fixed_frequency=2,
            floating_frequency=4,
            calendar=ql.UnitedStates(ql.UnitedStates.GovernmentBond),
            business_day_convention=ql.Following,
        )
        
        fixed_schedule = scheduler.generate_fixed_schedule()
        
        # All dates should be business days
        calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
        for i in range(len(fixed_schedule)):
            assert calendar.isBusinessDay(fixed_schedule[i])
    
    def test_different_frequencies(self):
        """Test scheduler with different payment frequencies."""
        # Annual fixed, monthly floating
        scheduler = FixToFloatScheduleGenerator(
            issue_date=datetime(2024, 1, 15),
            switch_date=datetime(2026, 1, 15),  # 2 years fixed
            maturity_date=datetime(2029, 1, 15),  # 5 years total
            fixed_frequency=1,  # Annual
            floating_frequency=12,  # Monthly
            calendar=ql.UnitedStates(ql.UnitedStates.GovernmentBond),
            business_day_convention=ql.Following,
        )
        
        fixed_schedule = scheduler.generate_fixed_schedule()
        floating_schedule = scheduler.generate_floating_schedule()
        
        # 2 years annual = 2 periods + 1 start
        assert len(fixed_schedule) == 3
        
        # 3 years monthly = 36 periods + 1 start
        assert len(floating_schedule) == 37
    
    def test_very_short_fixed_period(self):
        """Test scheduler with very short fixed period."""
        scheduler = FixToFloatScheduleGenerator(
            issue_date=datetime(2024, 1, 15),
            switch_date=datetime(2024, 7, 15),  # 6 months fixed
            maturity_date=datetime(2034, 1, 15),  # 10 years total
            fixed_frequency=2,  # Semiannual
            floating_frequency=4,  # Quarterly
            calendar=ql.UnitedStates(ql.UnitedStates.GovernmentBond),
            business_day_convention=ql.Following,
        )
        
        fixed_schedule = scheduler.generate_fixed_schedule()
        
        # Should have just 2 dates (start and end)
        assert len(fixed_schedule) == 2
        assert fixed_schedule[0] == ql.Date(16, 1, 2024)  # Adjusted from Jan 15 (holiday)
        assert fixed_schedule[1] == ql.Date(15, 7, 2024)  # July 15 is a Monday
    
    def test_frequency_mapping(self, basic_scheduler):
        """Test that frequency integers map correctly to QuantLib enums."""
        assert basic_scheduler._map_frequency(1) == ql.Annual
        assert basic_scheduler._map_frequency(2) == ql.Semiannual
        assert basic_scheduler._map_frequency(4) == ql.Quarterly
        assert basic_scheduler._map_frequency(12) == ql.Monthly
        
        # Test default behavior
        assert basic_scheduler._map_frequency(999) == ql.Annual