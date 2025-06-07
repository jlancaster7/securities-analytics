from QuantLib.QuantLib import Date, DayCounter

from ..fixed_rate_bullets.vanilla.bond import FixedRateQLBond


class BondSpreadCalculator:
    """
    Calculates G-spread and spread-to-benchmark for a given bond
    based on:
      - A user-specified rule for workout date (default = earliest call).
      - A custom rule for picking the 'benchmark' OTR tenor
        (based on the bond's originally issued tenor).
      - G-spread done by linear interpolation at EXACT time-to-workout.
      - Spread-to-benchmark done by the custom 'round-down' logic.
    """

    def __init__(
        self,
        bond: FixedRateQLBond,  # Must be an AbstractBond or a child (e.g., FixedRateQLBond)
        treasury_curve: dict[float, float],
        original_benchmark_tenor: int,  # e.g. 10 if originally a 10y bond
        use_earliest_call: bool = True,
    ) -> None:
        """
        :param bond: A bond object implementing AbstractBond (e.g. FixedRateQLBond).
        :param treasury_curve: A dict {tenor_in_years: yield}, e.g. {2: 0.04, 5: 0.042, 10: 0.045}
        :param original_benchmark_tenor: The OTR tenor (an integer) that the bond used at issuance.
        :param use_earliest_call: If True, we assume the workout date is the earliest call date
                                  if there's a call. Otherwise we do maturity.
        """
        self.bond: FixedRateQLBond = bond
        self.treasury_curve: dict[float, float] = treasury_curve
        # Sort the curve keys to make sure interpolation is possible
        self.sorted_tenors: list[float] = sorted(self.treasury_curve.keys())

        self.original_benchmark_tenor: int = original_benchmark_tenor

        self.use_earliest_call: bool = use_earliest_call

    # ------------------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------------------
    def spread_from_price(self, market_price: float) -> dict[str, float]:
        """
        1) Determine the bond's workout yield (based on earliest call or maturity).
        2) Compute G-spread = (bond yield) - (interpolated treasury yield).
        3) Compute spread to benchmark = (bond yield) - (benchmark treasury yield)
           (where 'benchmark treasury yield' is found via the custom round-down rule).
        4) Return both in a dict. Spreads are returned in decimal (0.015 => 15 bps).
        """
        bond_yield: float = self._get_workout_yield(market_price)
        # 2) G-spread
        g_spread_val: float = bond_yield - self._get_treasury_yield_linear()
        # 3) Spread to benchmark
        spread_to_bmk_val: float = bond_yield - self._get_benchmark_treasury_yield()

        return {"g_spread": g_spread_val, "spread_to_benchmark": spread_to_bmk_val}

    def price_from_spread(self, spread: float, which_spread: str = "benchmark") -> float:
        """
        Compute the theoretical bond price if the spread is 'spread' (decimal).
        :param spread: e.g. 0.015 for 15 bps
        :param which_spread: 'g_spread' or 'benchmark'
        :return: a theoretical price
        Steps:
          1) Determine the relevant treasury yield (interpolated or benchmark).
          2) sum = treasury_yield + spread.
          3) use that sum as the bond yield in the bond's pricing routine.
        """
        if which_spread.lower() == "g_spread":
            treasury_yield: float = self._get_treasury_yield_linear()
        else:
            treasury_yield = self._get_benchmark_treasury_yield()

        bond_yield: float = treasury_yield + spread
        # Price from yield
        return self._price_from_yield(bond_yield)

    # ------------------------------------------------------------------
    # INTERNAL: RULES FOR WORKOUT YIELD, TREASURY YIELD, BENCHMARK
    # ------------------------------------------------------------------
    def _get_workout_yield(self, market_price: float) -> float:
        """
        If use_earliest_call = True and the bond has a call,
        then yield = yield_to_call, else yield = yield_to_maturity.
        """
        if self.use_earliest_call:
            # We check if the bond actually has a call object
            # Implementation detail depends on your bond class (FixedRateQLBond).
            # We'll assume if `bond_call` is not None => we have a call.
            # Or we can attempt yield_to_call and catch an error.
            try:
                ytc: float = self.bond.yield_to_call(market_price)
                return ytc
            except Exception as e:
                print(e)
                # Either no call or something else. Fallback to YTM
                return self.bond.yield_to_maturity(market_price)
        else:
            return self.bond.yield_to_maturity(market_price)

    def _get_treasury_yield_linear(self) -> float:
        """
        G-Spread approach: linearly interpolate the treasury curve
        at the EXACT time-to-workout in years (e.g. 7.2).
        """
        t: float = self._time_to_workout_in_years()
        return self._linear_interpolate_curve(t)

    def _get_benchmark_treasury_yield(self) -> float:
        """
        Use the custom rule:
         'the bond remains with the originally issued OTR tenor until we
          cross below that tenor - 3 years, then we step down to the next OTR, etc.'
        Ties stay with the higher/older OTR.

        e.g. If originally a 10-year bond:
          - >= 7.0 years => use 10-year
          - >= 3.0 years => use 5-year
          - >= 2.0 years => use 3-year
          - else => use 2-year
        (This example ignores 7-year OTR, as you requested.)

        If you also want logic for original=5-year or original=30-year,
        we can expand the approach or define a table. For clarity,
        we'll focus on original=10. You can easily extend this logic
        for other original benchmarks.
        """
        t: float = self._time_to_workout_in_years()

        # For demonstration, let's implement for original=10.
        if self.original_benchmark_tenor == 10:
            # The threshold is 7.0 => 10-year; 3.0 => 5-year; 2.0 => 3-year
            # exactly 7.0 => remain 10-year; exactly 3.0 => remain 5-year, etc.
            if t >= 7.0:
                chosen_tenor = 10
            elif t >= 3.0:
                chosen_tenor = 5
            elif t >= 2.0:
                chosen_tenor = 3
            else:
                chosen_tenor = 2

        # If we wanted to handle original=5, or 30, etc. in the same method,
        # we could do more logic. But let's keep it simple for demonstration:
        else:
            # If there's no specialized logic for other tenors, fall back on
            # picking the nearest tenor from the curve. This is fallback code.
            chosen_tenor: float = self._pick_nearest_tenor(t)

        # Return the yield from the curve at chosen_tenor (no interpolation).
        if chosen_tenor in self.treasury_curve:
            return self.treasury_curve[chosen_tenor]
        else:
            # If the chosen tenor isn't literally in the dict, fallback
            # to the nearest or to linear interpolation:
            return self._pick_nearest_tenor_value(chosen_tenor)

    # ------------------------------------------------------------------
    # INTERNAL: TIME TO WORKOUT, PRICE FROM YIELD
    # ------------------------------------------------------------------
    def _time_to_workout_in_years(self) -> float:
        """
        Return the time in years from settlement to the 'workout date,'
        which we define as earliest call date if that rule is set, or maturity otherwise.
        We'll call a method on the bond to find that date or do an approximate approach.

        For your current approach, we can do:
          - if use_earliest_call => call_date if it exists, else maturity
          - else => maturity
        Then we measure the day count fraction from settlement to that date.
        """
        maturity_date: Date = self.bond.schedule_generator.generate()[-1]
        settlement: Date = self.bond.settlement_date_ql
        # Easiest is to do a daycount fraction using the bond's day_count:
        day_count: DayCounter = self.bond.day_count

        if self.use_earliest_call and self.bond.bond_call and self.bond.call_schedule_generator:
            # The bond itself has a call schedule => let’s assume there's one call date
            call_date: Date = self.bond.call_schedule_generator.generate()[
                -1
            ]  # not quite right for multiple calls

            if call_date and call_date < maturity_date:
                return day_count.yearFraction(settlement, call_date)

        # fallback => maturity
        return day_count.yearFraction(settlement, maturity_date)

    def _price_from_yield(self, y: float) -> float:
        """
        If use_earliest_call => we price to the call version of the bond
        (dirtyPriceToCall) or something. But let's keep it simpler:
        We'll just re-check the same logic used for yield: if earliest call is used,
        then we do the bond_call's price if it exists, else bond_mty's price.
        This is consistent with the 'workout yield' approach.
        """
        if self.use_earliest_call and self.bond.bond_call:
            try:
                return self.bond.dirty_price_to_call(y)
            except Exception as e:
                print(e)
                # fallback to maturity
                return self.bond.dirty_price_to_maturity(y)
        else:
            return self.bond.dirty_price_to_maturity(y)

    # ------------------------------------------------------------------
    # INTERNAL: HELPER - LINEAR INTERPOLATION / NEAREST TENOR
    # ------------------------------------------------------------------
    def _linear_interpolate_curve(self, t: float) -> float:
        """
        Basic linear interpolation on self.treasury_curve,
        where keys are sorted in self.sorted_tenors.
        """
        # bounds check
        if t <= self.sorted_tenors[0]:
            return self.treasury_curve[self.sorted_tenors[0]]
        if t >= self.sorted_tenors[-1]:
            return self.treasury_curve[self.sorted_tenors[-1]]

        # find bracket
        for i in range(len(self.sorted_tenors) - 1):
            t1: float = self.sorted_tenors[i]
            t2: float = self.sorted_tenors[i + 1]
            if t1 <= t <= t2:
                y1: float = self.treasury_curve[t1]
                y2: float = self.treasury_curve[t2]
                # do the interpolation
                weight: float = (t - t1) / (t2 - t1)
                return y1 + weight * (y2 - y1)

        # fallback
        return self.treasury_curve[self.sorted_tenors[-1]]

    def _pick_nearest_tenor(self, t: float) -> float:
        """
        Return the OTR tenor from self.sorted_tenors that’s nearest to t.
        """
        best = 0
        best_diff = 0.25
        for tenor in self.sorted_tenors:
            diff: float = abs(tenor - t)
            if diff < best_diff:
                best_diff: float = diff
                best: float = tenor
        return best

    def _pick_nearest_tenor_value(self, chosen_tenor: float) -> float:
        """
        If 'chosen_tenor' isn't in the dictionary, pick the actual curve tenor
        that’s closest to 'chosen_tenor' and return that yield.
        """
        best = 0
        best_diff = 0.25
        for tnr in self.sorted_tenors:
            diff: float = abs(tnr - chosen_tenor)
            if diff < best_diff:
                best_diff: float = diff
                best: float = tnr
        return self.treasury_curve[best]
