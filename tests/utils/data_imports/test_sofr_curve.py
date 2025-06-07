from datetime import datetime, timedelta

import QuantLib as ql

from securities_analytics.utils.data_imports.curves import load_and_return_sofr_curve
from securities_analytics.utils.dates.utils import to_ql_date


def test_sofr_curve_dict_type() -> None:
    sofr_curve_handle: ql.YieldTermStructureHandle = load_and_return_sofr_curve(
        file_path="tests/data/sofr_curve.csv"
    )
    assert isinstance(sofr_curve_handle, ql.YieldTermStructureHandle)


def test_treasury_curve_not_empty() -> None:
    sofr_curve_handle: ql.YieldTermStructureHandle = load_and_return_sofr_curve(
        file_path="tests/data/sofr_curve.csv"
    )

    def is_handle_populated(handle: ql.YieldTermStructureHandle) -> bool:
        try:
            # Try to get a discount factor, which forces dereferencing the handle
            handle.discount(to_ql_date(datetime.now() + timedelta(days=60)))
            return True
        except RuntimeError:
            return False

    assert is_handle_populated(sofr_curve_handle)


if __name__ == "__main__":
    sofr_curve_handle: ql.YieldTermStructureHandle = load_and_return_sofr_curve(
        file_path="tests/data/sofr_curve.csv"
    )
    assert isinstance(sofr_curve_handle, ql.YieldTermStructureHandle)
