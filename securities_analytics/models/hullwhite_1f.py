import QuantLib as ql
from pandas import DataFrame

from ..utils.data_imports.utils import tenor_to_ql_period


def calibrate_hull_white_1f(
    ts_handle: ql.YieldTermStructureHandle, swaption_vols: DataFrame
) -> ql.HullWhite:
    """
    The method expects the swaption vols to be decimals, not basis points,
    so make sure to divide the DataFrameby 10000 if you are importing from Bloomberg.
    """
    model = ql.HullWhite(ts_handle)

    engine = ql.JamshidianSwaptionEngine(model)

    index = ql.Sofr(ts_handle)

    fixedLegTenor = ql.Period("1Y")
    fixedLegDayCounter = ql.Actual360()
    floatingLegDayCounter = ql.Actual360()

    swaptions: list[ql.SwaptionHelper] = []

    for maturity in swaption_vols.index:
        for tenor in swaption_vols.columns:
            volatility = ql.QuoteHandle(ql.SimpleQuote(swaption_vols.at[maturity, tenor]))
            helper = ql.SwaptionHelper(
                tenor_to_ql_period(maturity),
                tenor_to_ql_period(tenor),
                volatility,
                index,
                fixedLegTenor,
                fixedLegDayCounter,
                floatingLegDayCounter,
                ts_handle,
                ql.BlackCalibrationHelper.RelativePriceError,
                ql.nullDouble(),
                1.0,
                ql.Normal,
            )
            helper.setPricingEngine(engine)
            swaptions.append(helper)

    optimization_method = ql.LevenbergMarquardt(1.0e-8, 1.0e-8, 1.0e-8)
    end_criteria = ql.EndCriteria(500000, 1000, 1e-6, 1e-8, 1e-8)
    model.calibrate(swaptions, optimization_method, end_criteria)

    return model
