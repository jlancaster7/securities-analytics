from datetime import datetime

import pytest

from securities_analytics.bonds.analytics.spreads import BondSpreadCalculator
from securities_analytics.bonds.fixed_rate_bullets.vanilla.bond import FixedRateQLBond
from securities_analytics.utils.data_imports.curves import load_and_return_active_treasury_curve


def build_test_spread_calc(
    settlement_date=datetime(2025, 4, 4),
) -> tuple[FixedRateQLBond, BondSpreadCalculator]:
    issue_date: datetime = settlement_date
    maturity_date = datetime(2032, 8, 19)
    call_date = datetime(2031, 8, 19)
    day_count = "ACT365"

    fixed_bond = FixedRateQLBond(
        face_value=100,
        maturity_date=maturity_date,
        annual_coupon_rate=0.061,
        settlement_date=settlement_date,
        day_count=day_count,
        settlement_days=2,
        issue_date=issue_date,
        next_call_date=call_date,
        call_price=100,
    )

    treasury_curve: dict[float, float] = load_and_return_active_treasury_curve(
        file_path="tests/data/active_treasury_curve.csv"
    )

    spread_calc = BondSpreadCalculator(
        bond=fixed_bond,
        treasury_curve=treasury_curve,
        original_benchmark_tenor=10,
        use_earliest_call=True,
    )

    return fixed_bond, spread_calc


@pytest.fixture
def bond_and_spread() -> tuple[FixedRateQLBond, BondSpreadCalculator]:
    return build_test_spread_calc()


def test_yields(bond_and_spread: tuple[FixedRateQLBond, BondSpreadCalculator]) -> None:
    bond, _ = bond_and_spread
    market_clean_price = 98.567

    ytm: float = bond.yield_to_maturity(market_clean_price)
    ytc: float = bond.yield_to_call(market_clean_price)
    ytw: float = bond.yield_to_worst(market_clean_price)

    print(f"YTM = {ytm:.5f}, YTC = {ytc:.5f}, YTW = {ytw:.5f}")

    assert 0 < ytm < 1
    assert 0 < ytc < 1
    assert 0 < ytw < 1
    assert ytw <= min(ytm, ytc)


def test_spread_from_price(bond_and_spread: tuple[FixedRateQLBond, BondSpreadCalculator]) -> None:
    _, spread_calc = bond_and_spread
    market_clean_price = 98.567

    result: dict[str, float] = spread_calc.spread_from_price(market_clean_price)
    g_spread: float = result["g_spread"]
    spread_to_benchmark: float = result["spread_to_benchmark"]

    print(f"G-Spread: {g_spread * 1e4:.2f} bps")
    print(f"Spread to Benchmark: {spread_to_benchmark * 1e4:.2f} bps")

    assert 0 < g_spread < 0.1
    assert 0 < spread_to_benchmark < 0.1


def test_price_from_g_spread(bond_and_spread: tuple[FixedRateQLBond, BondSpreadCalculator]) -> None:
    _, spread_calc = bond_and_spread
    desired_spread = 0.025356  # 100 bps

    theoretical_price: float = spread_calc.price_from_spread(
        desired_spread, which_spread="g_spread"
    )
    print(f"Theoretical Price (G-Spread 100bps): {theoretical_price:.3f}")
    assert theoretical_price > 0


def test_price_from_benchmark_spread(
    bond_and_spread: tuple[FixedRateQLBond, BondSpreadCalculator],
) -> None:
    _, spread_calc = bond_and_spread
    desired_spread = 0.026084  # 120.84 bps

    theoretical_price: float = spread_calc.price_from_spread(
        desired_spread, which_spread="benchmark"
    )
    print(f"Theoretical Price (Benchmark Spread 120.84bps): {theoretical_price:.3f}")
    assert theoretical_price > 0


if __name__ == "__main__":
    bond, spread_calc = build_test_spread_calc()
    market_clean_price = 97.506
    print(f"Price:    {market_clean_price}")

    ytm: float = bond.yield_to_maturity(market_clean_price)
    ytc: float = bond.yield_to_call(market_clean_price)
    ytw: float = bond.yield_to_worst(market_clean_price)

    print(f"YTM = {ytm * 100:.2f}%, YTC = {ytc * 100:.2f}%, YTW = {ytw * 100:.2f}%")

    result: dict[str, float] = spread_calc.spread_from_price(market_clean_price)
    g_spread: float = result["g_spread"]
    spread_to_benchmark: float = result["spread_to_benchmark"]

    print(f"G-Spread: {g_spread * 10000:.2f} bps")
    print(f"Spread to Benchmark: {spread_to_benchmark * 10000:.2f} bps")

    desired_spread = 0.025223

    theoretical_price: float = spread_calc.price_from_spread(
        desired_spread, which_spread="g_spread"
    )
    print(f"Theoretical Price (G-Spread 252.23bps): {theoretical_price:.3f}")

    desired_spread = 0.026478

    theoretical_price: float = spread_calc.price_from_spread(
        desired_spread, which_spread="benchmark"
    )
    print(f"Theoretical Price (Benchmark Spread 264.78bps): {theoretical_price:.3f}")
