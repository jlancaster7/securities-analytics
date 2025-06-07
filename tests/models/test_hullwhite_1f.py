from typing import Any

import pandas as pd
import QuantLib as ql

from securities_analytics.models.hullwhite_1f import calibrate_hull_white_1f
from securities_analytics.utils.data_imports.curves import load_and_return_sofr_curve


def import_swaptions_and_term_structure() -> tuple[ql.YieldTermStructureHandle, pd.DataFrame]:
    # Read the swaption volatilities from the csv file.
    swaption_vols: pd.DataFrame = pd.read_csv("tests/data/swaption_vols.csv")
    swaption_vols.set_index("Expiry", inplace=True)
    swaption_vols = swaption_vols / 10000
    ts_handle: ql.YieldTermStructureHandle = load_and_return_sofr_curve(
        file_path="tests/data/sofr_curve.csv"
    )
    return ts_handle, swaption_vols


if __name__ == "__main__":
    ts_handle, swaption_vols = import_swaptions_and_term_structure()

    calibrated_model: ql.HullWhite = calibrate_hull_white_1f(
        ts_handle=ts_handle, swaption_vols=swaption_vols
    )
    calibrated_model_params: Any = calibrated_model.params()
    print(f"Mean Reversion paramater (a): {calibrated_model_params[0]}")
    print(f"Volatility paramater (s):     {calibrated_model_params[1]}")
