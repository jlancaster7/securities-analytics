from datetime import datetime

import pandas as pd
import QuantLib as ql

from securities_analytics.utils.data_imports.utils import tenor_to_ql_period
from securities_analytics.utils.dates.utils import to_ql_date


def load_and_return_sofr_curve(
    file_path: str, evalulation_date: datetime | None = None
) -> ql.YieldTermStructureHandle:
    # 1. Read the data from Excel
    df: pd.DataFrame = pd.read_csv(file_path)

    # 2. Set your reference (evaluation) date
    if not evalulation_date:
        evalulation_date = datetime.strptime(str(df.loc[0, "Update"]), "%m/%d/%Y")

    evalulation_date_ql: ql.Date = to_ql_date(evalulation_date)

    # 3. Choose calendar, day count convention, etc.
    calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)  # or whatever matches your market
    day_count = ql.Actual365Fixed()

    # 5. Build a list of (Date, Rate) for the ZeroCurve from the Tenor and Rate
    dates: list[ql.Date] = []
    zero_rates: list[float] = []

    for _, row in df.iterrows():
        tenor_str: str = str(row["Tenor"]).strip()  # e.g. "3M", "2Y"
        rate: float = float(row["Yield"]) / 100  # e.g. 0.035 (3.5%)

        period: ql.Period = tenor_to_ql_period(tenor_str)
        # Advance from 'today' by that period
        pillar_date: ql.Date = calendar.advance(evalulation_date_ql, period)

        dates.append(pillar_date)
        zero_rates.append(rate)

    # 6. Create a zero curve and wrap it in a handle
    # Note: ZeroCurve expects strictly ascending dates
    # so you may want to sort them by date before building:
    pairs: list[tuple[ql.Date, float]] = sorted(zip(dates, zero_rates), key=lambda x: x[0])
    sorted_dates, sorted_rates = zip(*pairs)

    zero_curve = ql.ZeroCurve(
        list(sorted_dates),
        list(sorted_rates),
        day_count,
        calendar,
        ql.Linear(),  # Interpolation
        ql.Compounded,  # Compounding convention
        ql.Annual,  # Compounding frequency
    )

    # The yield term structure handle:
    sofr_curve_handle = ql.YieldTermStructureHandle(zero_curve)
    return sofr_curve_handle


def load_and_return_active_treasury_curve(
    file_path: str,
    evaluation_date=datetime.today(),
    day_count=ql.ActualActual(ql.ActualActual.Bond),
) -> dict[float, float]:
    # 1. Read the data from Excel
    df: pd.DataFrame = pd.read_csv(file_path, encoding="ISO-8859-1")
    calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)  # or whatever matches your market
    day_count = ql.Actual365Fixed()

    evaluation_date_ql: ql.Date = to_ql_date(evaluation_date)

    # Prepare the result dictionary
    curve_dict: dict[float, float] = {}

    for _, row in df.iterrows():
        tenor_str: str = str(row["Tenor"]).strip()
        yield_float: float = float(row["Yield"]) / 100
        period: ql.Period = tenor_to_ql_period(tenor_str)
        # Convert Maturity string to a QuantLib Date
        # maturity_dt: datetime = datetime.strptime(maturity_str, "%m/%d/%Y")
        pillar_date: ql.Date = calendar.advance(evaluation_date_ql, period)

        # Compute years to maturity
        # day_count.yearFraction(refDate, maturityDate)
        ttm: float = day_count.yearFraction(evaluation_date_ql, pillar_date)

        # Only store if ttm > 0 (in the future)
        if ttm > 0:
            curve_dict[ttm] = yield_float

    return curve_dict
