from datetime import datetime

import pytest
import QuantLib as ql

from securities_analytics.bonds.fixed_rate_bullets.callable.bond import CallableFixedRateQLBond
from securities_analytics.utils.data_imports.curves import load_and_return_sofr_curve


def build_callable_bond() -> CallableFixedRateQLBond:
    face_value: float = 100
    annual_coupon_rate: float = 0.02963
    # Set up market/calendar parameters
    settlement_days: int = 2
    settlement_date: datetime = datetime.now()

    issue_date: datetime = datetime(2025, 4, 15)
    issue_date: datetime = datetime(2023, 1, 25)
    maturity_date = datetime(2033, 1, 25)

    day_count = "D30360"

    # Build a schedule generator for the fixed-rate bond until maturity

    call_date = datetime(2032, 1, 25)
    call_price: float = 100

    sofr_curve_handle: ql.YieldTermStructureHandle = load_and_return_sofr_curve(
        file_path="tests/data/sofr_curve.csv"
    )

    callable_bond = CallableFixedRateQLBond(
        face_value=face_value,
        maturity_date=maturity_date,
        annual_coupon_rate=annual_coupon_rate,
        settlement_date=settlement_date,
        day_count=day_count,
        settlement_days=settlement_days,
        next_call_date=call_date,
        call_price=call_price,
        ts_handle=sofr_curve_handle,
        issue_date=issue_date,
    )

    return callable_bond


@pytest.fixture
def callable_bond() -> CallableFixedRateQLBond:
    return build_callable_bond()


def test_clean_price(callable_bond: CallableFixedRateQLBond) -> None:
    clean_price: float = callable_bond.clean_price()
    print(f"Clean Price = {clean_price:.3f}")
    assert clean_price > 0


def test_dirty_price(callable_bond: CallableFixedRateQLBond) -> None:
    dirty_price: float = callable_bond.dirty_price()
    print(f"Dirty Price = {dirty_price:.3f}")
    assert dirty_price >= callable_bond.clean_price()


def test_npv(callable_bond: CallableFixedRateQLBond) -> None:
    npv: float = callable_bond.npv()
    print(f"NPV Price = {npv:.3f}")
    assert npv > 0


def test_yield_to_maturity(callable_bond: CallableFixedRateQLBond) -> None:
    ytm: float = callable_bond.yield_to_maturity()
    print(f"Yield to Maturity = {ytm * 100:.3f}%")
    assert 0 < ytm < 1


def test_duration(callable_bond: CallableFixedRateQLBond) -> None:
    oas_bps = 100
    duration: float = callable_bond.duration(oas=oas_bps / 10000)
    print(f"Duration = {duration:.4f}")
    assert duration > 0


def test_convexity(callable_bond: CallableFixedRateQLBond) -> None:
    oas_bps = 100
    convexity: float = callable_bond.convexity(oas=oas_bps / 10000)
    print(f"Convexity = {convexity:.4f}")
    assert convexity > 0


# Optional: keep one-off runnable support
if __name__ == "__main__":
    bond: CallableFixedRateQLBond = build_callable_bond()
    clean_price: float = bond.clean_price()
    print(f"Clean Price: {bond.clean_price():.3f}")
    print(f"Dirty Price: {bond.dirty_price():.3f}")
    print(f"NPV: {bond.npv():.3f}")
    print(f"Yield to Maturity: {bond.yield_to_maturity() * 100:.3f}%")
    oas = bond.calculate_OAS(87)
    print(f"OAS: {oas * 10000:.4f}")
    print(f"Duration: {bond.duration(oas):.4f}")
    print(f"Convexity: {bond.convexity(oas):.4f}")
