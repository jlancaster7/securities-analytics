import pytest
from datetime import datetime
import QuantLib as ql

from securities_analytics.bonds.floating_rate.schedulers.scheduler import FloatingRateBondScheduleGenerator


class TestFloatingRateBondScheduleGenerator:
    """Test suite for FloatingRateBondScheduleGenerator."""
    
    def test_quarterly_schedule_generation(self):
        """Test quarterly payment schedule generation."""
        scheduler = FloatingRateBondScheduleGenerator(
            issue_date=datetime(2024, 3, 15),
            maturity_date=datetime(2029, 3, 15),
            frequency=4,  # Quarterly
        )
        
        schedule = scheduler.generate()
        
        # Should have approximately 5 years * 4 payments/year + 1 = 21 dates
        assert len(schedule) >= 20
        assert len(schedule) <= 22  # Allow for date adjustments
        
        # First date should be issue date
        first_date = schedule[0]
        assert first_date.year() == 2024
        assert first_date.month() == 3
        
        # Last date should be maturity date
        last_date = schedule[-1]
        assert last_date.year() == 2029
        assert last_date.month() == 3
    
    def test_monthly_schedule_generation(self):
        """Test monthly payment schedule generation."""
        scheduler = FloatingRateBondScheduleGenerator(
            issue_date=datetime(2024, 3, 15),
            maturity_date=datetime(2026, 3, 15),  # 2 years
            frequency=12,  # Monthly
        )
        
        schedule = scheduler.generate()
        
        # Should have approximately 2 years * 12 payments/year + 1 = 25 dates
        assert len(schedule) >= 24
        assert len(schedule) <= 26
    
    def test_semiannual_schedule_generation(self):
        """Test semiannual payment schedule generation."""
        scheduler = FloatingRateBondScheduleGenerator(
            issue_date=datetime(2024, 3, 15),
            maturity_date=datetime(2029, 3, 15),
            frequency=2,  # Semiannual
        )
        
        schedule = scheduler.generate()
        
        # Should have approximately 5 years * 2 payments/year + 1 = 11 dates
        assert len(schedule) >= 10
        assert len(schedule) <= 12
    
    def test_business_day_adjustment(self):
        """Test that business day conventions are applied."""
        # Use a date that falls on weekend
        scheduler = FloatingRateBondScheduleGenerator(
            issue_date=datetime(2024, 3, 16),  # Saturday
            maturity_date=datetime(2025, 3, 16),  # Sunday
            frequency=4,
            business_day_convention=ql.Following,
        )
        
        schedule = scheduler.generate()
        
        # Check that dates are adjusted to business days
        for i in range(len(schedule)):
            date = schedule[i]
            # Following convention should move weekend dates to Monday
            assert date.weekday() not in [ql.Saturday, ql.Sunday]
    
    def test_end_of_month_convention(self):
        """Test end of month convention."""
        scheduler = FloatingRateBondScheduleGenerator(
            issue_date=datetime(2024, 1, 31),  # End of January
            maturity_date=datetime(2025, 1, 31),
            frequency=12,  # Monthly
            end_of_month=True,
        )
        
        schedule = scheduler.generate()
        
        # Check that dates follow end of month convention
        # February should be Feb 28/29, not Jan 31 + 1 month
        feb_date = schedule[1]
        assert feb_date.month() == 2
        assert feb_date.dayOfMonth() in [28, 29]  # Depending on leap year
    
    def test_custom_first_coupon_date(self):
        """Test schedule with custom first coupon date."""
        first_coupon = datetime(2024, 6, 15)
        
        scheduler = FloatingRateBondScheduleGenerator(
            issue_date=datetime(2024, 3, 15),
            maturity_date=datetime(2029, 3, 15),
            frequency=4,
            first_coupon_date=first_coupon,
        )
        
        schedule = scheduler.generate()
        
        # Second date should be the first coupon date
        assert schedule[1].year() == first_coupon.year
        assert schedule[1].month() == first_coupon.month
        assert schedule[1].dayOfMonth() == first_coupon.day
    
    def test_backward_generation_rule(self):
        """Test backward date generation rule."""
        scheduler = FloatingRateBondScheduleGenerator(
            issue_date=datetime(2024, 3, 15),
            maturity_date=datetime(2029, 3, 15),
            frequency=4,
            date_generation_rule=ql.DateGeneration.Backward,
        )
        
        schedule = scheduler.generate()
        
        # Backward generation should ensure the last date is exactly maturity
        last_date = schedule[-1]
        assert last_date.year() == 2029
        assert last_date.month() == 3
        assert last_date.dayOfMonth() == 15
    
    def test_different_calendars(self):
        """Test schedule generation with different calendars."""
        # Test with UK calendar
        scheduler_uk = FloatingRateBondScheduleGenerator(
            issue_date=datetime(2024, 3, 15),
            maturity_date=datetime(2025, 3, 15),
            frequency=4,
            calendar=ql.UnitedKingdom(),
        )
        
        # Test with TARGET calendar
        scheduler_target = FloatingRateBondScheduleGenerator(
            issue_date=datetime(2024, 3, 15),
            maturity_date=datetime(2025, 3, 15),
            frequency=4,
            calendar=ql.TARGET(),
        )
        
        schedule_uk = scheduler_uk.generate()
        schedule_target = scheduler_target.generate()
        
        # Both should generate valid schedules
        assert len(schedule_uk) > 0
        assert len(schedule_target) > 0
        
        # Schedules might differ slightly due to different holiday calendars
        # but should have similar length
        assert abs(len(schedule_uk) - len(schedule_target)) <= 1
    
    def test_tenor_consistency(self):
        """Test that the tenor is properly set based on frequency."""
        scheduler = FloatingRateBondScheduleGenerator(
            issue_date=datetime(2024, 3, 15),
            maturity_date=datetime(2025, 3, 15),
            frequency=4,  # Quarterly
        )
        
        # Check that tenor matches frequency
        assert scheduler.tenor.length() == 3
        assert scheduler.tenor.units() == ql.Months
        
        # Test monthly
        scheduler_monthly = FloatingRateBondScheduleGenerator(
            issue_date=datetime(2024, 3, 15),
            maturity_date=datetime(2025, 3, 15),
            frequency=12,
        )
        
        assert scheduler_monthly.tenor.length() == 1
        assert scheduler_monthly.tenor.units() == ql.Months