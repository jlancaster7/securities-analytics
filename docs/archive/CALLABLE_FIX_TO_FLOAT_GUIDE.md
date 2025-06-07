# Callable Fix-to-Float Bond Implementation Guide

## Overview

Callable fix-to-float bonds present unique analytical challenges because they have two key dates that may or may not coincide:
1. **Call Date(s)**: When the issuer can redeem the bond
2. **Switch Date**: When the bond transitions from fixed to floating rate

## Current Implementation Status

### What's Already Implemented
- Basic support for single call date via `next_call_date` and `call_price` parameters
- Integration with spread calculator using `use_earliest_call` flag
- Simplified yield-to-call calculation

### Current Limitations
- Only single call date supported
- `dirty_price_to_call()` returns same as yield-to-maturity (oversimplified)
- No handling of complex scenarios where call date ≠ switch date

## Scenarios to Handle

### Scenario 1: Call Date = Switch Date
This is the simplest case, already partially supported:
```python
bond = FixToFloatBond(
    maturity_date=datetime(2034, 3, 15),
    switch_date=datetime(2027, 3, 15),
    next_call_date=datetime(2027, 3, 15),  # Same as switch
    call_price=100.0,
    # ... other parameters
)
```

### Scenario 2: Call Date Before Switch Date
Bond can be called while still in fixed period:
```python
bond = FixToFloatBond(
    maturity_date=datetime(2034, 3, 15),
    switch_date=datetime(2029, 3, 15),
    next_call_date=datetime(2026, 3, 15),  # 3 years before switch
    call_price=101.0,
    # ... other parameters
)
```

### Scenario 3: Call Date After Switch Date
Bond can be called during floating period:
```python
bond = FixToFloatBond(
    maturity_date=datetime(2034, 3, 15),
    switch_date=datetime(2027, 3, 15),
    next_call_date=datetime(2030, 3, 15),  # 3 years after switch
    call_price=100.0,
    # ... other parameters
)
```

### Scenario 4: Multiple Call Dates
Bond has call schedule spanning both periods:
```python
bond = EnhancedFixToFloatBond(
    maturity_date=datetime(2034, 3, 15),
    switch_date=datetime(2027, 3, 15),
    call_schedule=[
        (datetime(2026, 3, 15), 102.0),  # Before switch
        (datetime(2027, 3, 15), 101.0),  # At switch
        (datetime(2029, 3, 15), 100.5),  # After switch
        (datetime(2031, 3, 15), 100.0),  # After switch
    ],
    # ... other parameters
)
```

## Recommended Enhancements

### 1. Enhanced Bond Class

```python
from typing import List, Tuple

class CallableFixToFloatBond(FixToFloatBond):
    """Enhanced fix-to-float bond with proper callable support."""
    
    def __init__(
        self,
        *args,
        call_schedule: Optional[List[Tuple[datetime, float]]] = None,
        **kwargs
    ):
        # Extract single call from kwargs for backward compatibility
        next_call_date = kwargs.pop('next_call_date', None)
        call_price = kwargs.pop('call_price', None)
        
        super().__init__(*args, **kwargs)
        
        # Build call schedule
        if call_schedule:
            self.call_schedule = sorted(call_schedule, key=lambda x: x[0])
        elif next_call_date and call_price:
            self.call_schedule = [(next_call_date, call_price)]
        else:
            self.call_schedule = []
        
        # Create callable bond if we have calls
        if self.call_schedule:
            self._create_callable_bond()
    
    def _create_callable_bond(self):
        """Create QuantLib callable bond with proper exercise schedule."""
        # Convert call schedule to QuantLib format
        call_dates = []
        call_prices = []
        
        for call_date, call_price in self.call_schedule:
            ql_date = ql.Date(call_date.day, call_date.month, call_date.year)
            call_dates.append(ql_date)
            call_prices.append(call_price)
        
        # Create call schedule
        self.call_schedule_ql = ql.CallabilitySchedule()
        for i, (call_date, call_price) in enumerate(zip(call_dates, call_prices)):
            callability = ql.BondCallability(
                call_price,
                ql.BondCallability.Call,
                call_date
            )
            self.call_schedule_ql.append(callability)
        
        # Create callable bond
        # This is complex - would need to rebuild the composite bond
        # as a CallableFixedRateBond for fixed portion and handle floating separately
    
    def yield_to_call(self, market_clean_price: float, call_index: int = 0) -> float:
        """
        Calculate yield to specific call date.
        
        :param market_clean_price: Market clean price
        :param call_index: Which call date to use (0 = first call)
        :return: Yield to call
        """
        if not self.call_schedule or call_index >= len(self.call_schedule):
            # No calls or invalid index - return YTM
            return self.yield_to_maturity(market_clean_price)
        
        call_date, call_price = self.call_schedule[call_index]
        
        # Determine which period the call falls in
        if call_date <= self.switch_date:
            # Call during fixed period - simpler calculation
            return self._yield_to_call_fixed_period(
                market_clean_price, call_date, call_price
            )
        else:
            # Call during floating period - complex calculation
            return self._yield_to_call_floating_period(
                market_clean_price, call_date, call_price
            )
    
    def _yield_to_call_fixed_period(self, price: float, call_date: datetime, 
                                   call_price: float) -> float:
        """Calculate YTC when call is during fixed period."""
        # Create a fixed rate bond that matures at call date
        # with redemption at call price
        temp_bond = self._create_fixed_bond_to_call(call_date, call_price)
        return temp_bond.bondYield(
            price,
            self.day_count,
            self.compounding_ql,
            self.frequency_ql
        )
    
    def _yield_to_call_floating_period(self, price: float, call_date: datetime,
                                      call_price: float) -> float:
        """Calculate YTC when call is during floating period."""
        # This is complex - need to:
        # 1. Account for all fixed cashflows until switch
        # 2. Project floating cashflows from switch to call
        # 3. Solve for yield that prices correctly
        
        # For now, approximate using the composite bond
        # but with modified maturity
        # This is a simplification - proper implementation would need
        # to create a new composite bond with call date as maturity
        pass
    
    def dirty_price_to_call(self, y: float, call_index: int = 0) -> float:
        """
        Calculate dirty price from yield to specific call.
        
        :param y: Yield to call
        :param call_index: Which call date to use
        :return: Dirty price
        """
        if not self.call_schedule or call_index >= len(self.call_schedule):
            return self.dirty_price_to_maturity(y)
        
        call_date, call_price = self.call_schedule[call_index]
        
        if call_date <= self.switch_date:
            # Fixed period call
            temp_bond = self._create_fixed_bond_to_call(call_date, call_price)
            return temp_bond.dirtyPrice(
                y,
                self.day_count,
                self.compounding_ql,
                self.frequency_ql
            )
        else:
            # Floating period call - complex
            # Would need proper implementation
            raise NotImplementedError(
                "Dirty price to call for floating period not yet implemented"
            )
```

### 2. Enhanced Spread Calculator

```python
class EnhancedBondSpreadCalculator(BondSpreadCalculator):
    """Enhanced spread calculator for callable fix-to-float bonds."""
    
    def __init__(self, *args, call_selection_method: str = "worst", **kwargs):
        """
        :param call_selection_method: How to select call date
            - "worst": Use call date that gives worst yield (yield-to-worst)
            - "first": Use first call date
            - "optimal": Use most likely call date based on economics
        """
        super().__init__(*args, **kwargs)
        self.call_selection_method = call_selection_method
    
    def _get_workout_yield(self, market_price: float) -> float:
        """Get workout yield considering all call dates."""
        if not self.use_earliest_call:
            return self.bond.yield_to_maturity(market_price)
        
        # Check if bond has call schedule
        if hasattr(self.bond, 'call_schedule') and self.bond.call_schedule:
            if self.call_selection_method == "worst":
                return self._get_yield_to_worst(market_price)
            elif self.call_selection_method == "first":
                return self.bond.yield_to_call(market_price, call_index=0)
            elif self.call_selection_method == "optimal":
                return self._get_optimal_call_yield(market_price)
        
        # Fallback to parent implementation
        return super()._get_workout_yield(market_price)
    
    def _get_yield_to_worst(self, market_price: float) -> float:
        """Calculate yield-to-worst across all call dates and maturity."""
        yields = []
        
        # YTM
        yields.append(self.bond.yield_to_maturity(market_price))
        
        # YTC for each call date
        if hasattr(self.bond, 'call_schedule'):
            for i in range(len(self.bond.call_schedule)):
                try:
                    ytc = self.bond.yield_to_call(market_price, call_index=i)
                    yields.append(ytc)
                except:
                    pass
        
        # Return minimum yield (worst for investor)
        return min(yields)
    
    def _get_optimal_call_yield(self, market_price: float) -> float:
        """Determine most likely call date based on economics."""
        # This would implement logic to determine when issuer
        # would most likely call based on:
        # 1. Interest rate environment
        # 2. Call price vs market price
        # 3. Remaining fixed vs floating economics
        # For now, simplified implementation
        return self._get_yield_to_worst(market_price)
```

### 3. Option-Adjusted Spread (OAS) Calculator

```python
class FixToFloatOASCalculator:
    """Calculate OAS for callable fix-to-float bonds."""
    
    def __init__(
        self,
        bond: CallableFixToFloatBond,
        yield_curve: ql.YieldTermStructureHandle,
        volatility: float = 0.10,  # 10% vol
        mean_reversion: float = 0.03,
        num_paths: int = 1000
    ):
        self.bond = bond
        self.yield_curve = yield_curve
        self.volatility = volatility
        self.mean_reversion = mean_reversion
        self.num_paths = num_paths
    
    def calculate_oas(self, market_price: float) -> float:
        """
        Calculate OAS using Monte Carlo simulation.
        
        :param market_price: Market price of bond
        :return: OAS in decimal (0.01 = 100bps)
        """
        # Set up Hull-White model for interest rate simulation
        hw_model = ql.HullWhite(self.yield_curve, self.mean_reversion, self.volatility)
        
        # Monte Carlo engine
        engine = ql.TreeCallableFixedRateBondEngine(hw_model, 40)
        
        # This is simplified - full implementation would:
        # 1. Generate interest rate paths
        # 2. For each path, determine optimal call decision
        # 3. Calculate present value of cashflows considering calls
        # 4. Find OAS that matches market price
        
        # For now, return spread to curve as approximation
        return self.bond.spread_to_curve(market_price, self.yield_curve)
```

## Usage Examples

### Example 1: Bond Callable Before Switch
```python
# Bond switches to floating in 2029, but callable in 2026
bond = CallableFixToFloatBond(
    face_value=1000000,
    maturity_date=datetime(2034, 3, 15),
    switch_date=datetime(2029, 3, 15),  # 5 years to switch
    fixed_rate=0.055,  # 5.5% fixed
    floating_spread=0.015,  # SOFR + 150bps
    settlement_date=datetime(2024, 3, 15),
    floating_index=sofr_index,
    call_schedule=[
        (datetime(2026, 3, 15), 102.0),  # Callable at 102 in 2 years
        (datetime(2028, 3, 15), 101.0),  # Callable at 101 in 4 years
    ]
)

# Calculate yield-to-worst
calculator = EnhancedBondSpreadCalculator(
    bond=bond,
    treasury_curve=treasury_curve,
    use_earliest_call=True,
    call_selection_method="worst"
)

spreads = calculator.spread_from_price(market_price)
```

### Example 2: Bond Callable After Switch
```python
# Bond switches in 2027, callable starting 2030
bond = CallableFixToFloatBond(
    face_value=1000000,
    maturity_date=datetime(2034, 3, 15),
    switch_date=datetime(2027, 3, 15),  # 3 years to switch
    fixed_rate=0.045,  # 4.5% fixed
    floating_spread=0.01,  # SOFR + 100bps
    settlement_date=datetime(2024, 3, 15),
    floating_index=sofr_index,
    call_schedule=[
        (datetime(2030, 3, 15), 100.5),  # Callable at 100.5
        (datetime(2032, 3, 15), 100.0),  # Callable at par
    ]
)
```

## Key Considerations

### 1. Call Decision Logic
- **During Fixed Period**: Issuer likely to call if rates have fallen significantly
- **At Switch Date**: Common call point as issuer can refinance before floating exposure
- **During Floating Period**: Less common but possible if spreads have tightened

### 2. Pricing Complexity
- **Path Dependency**: Optimal call decision depends on rate path
- **Correlation**: Fixed rates and floating rate indices may be correlated
- **Volatility**: Both rate volatility and spread volatility matter

### 3. Risk Measures
- **Effective Duration**: Must consider call probability
- **Convexity**: Negative convexity due to call option
- **Key Rate Durations**: Different sensitivities pre/post switch

## Implementation Priority

1. **Phase 1**: Support multiple call dates with proper yield-to-worst
2. **Phase 2**: Implement proper yield-to-call for floating period calls  
3. **Phase 3**: Add OAS calculation with Monte Carlo
4. **Phase 4**: Sophisticated call prediction models

## Testing Requirements

```python
def test_callable_before_switch():
    """Test bond callable before switch date."""
    bond = CallableFixToFloatBond(
        # ... parameters
        switch_date=datetime(2029, 3, 15),
        call_schedule=[(datetime(2026, 3, 15), 102.0)]
    )
    
    # Price should reflect call possibility
    ytc = bond.yield_to_call(market_price=103.0)
    ytm = bond.yield_to_maturity(market_price=103.0)
    assert ytc < ytm  # YTC lower due to early redemption

def test_callable_after_switch():
    """Test bond callable after switch date."""
    # Complex test ensuring floating cashflows handled correctly
    pass

def test_multiple_calls_yield_to_worst():
    """Test yield-to-worst with multiple call dates."""
    # Ensure we pick the worst yield for investor
    pass
```

## Conclusion

Properly handling callable fix-to-float bonds requires:
1. Support for multiple call dates
2. Different calculation methods for calls during fixed vs floating periods
3. Integration with spread calculators using yield-to-worst
4. Eventually, full OAS implementation for accurate valuation

The current implementation provides a foundation, but needs these enhancements for production use with complex callable fix-to-float structures.