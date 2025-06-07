# Fix-to-Float Bond Implementation Plan

## Overview
This document outlines the implementation plan for adding fix-to-float bond support to the securities analytics service. Fix-to-float bonds pay a fixed coupon rate for an initial period, then switch to a floating rate (typically SOFR + spread) for the remaining life of the bond.

## Implementation Strategy

### Phase 1: Basic Cashflow Generation (Foundation)
**Goal**: Create the core infrastructure for generating combined fixed and floating cashflows.

**Tasks**:
1. ✅ Create directory structure (`securities_analytics/bonds/fix_to_float/`)
2. ✅ Implement `FixToFloatScheduleGenerator` 
   - Separate schedule generation for fixed and floating periods
   - Combined schedule generation for full bond life
3. Create comprehensive unit tests for the scheduler
4. Implement basic `FixToFloatBond` class
   - Inherit from `AbstractBond`
   - Generate cashflows using `ql.FixedRateLeg` and `ql.IborLeg`
   - Create combined `ql.Bond` object

**Success Criteria**:
- Scheduler correctly generates payment dates for both periods
- Bond object successfully creates combined cashflows
- All existing tests continue to pass

### Phase 2: Pricing and Yield Calculations
**Goal**: Implement core pricing functionality for fix-to-float bonds.

**Tasks**:
1. Implement clean/dirty price calculations
   - Use `ql.DiscountingBondEngine` with yield curve
   - Handle floating rate projections from forward curve
2. Implement spread calculations
   - Z-spread using `ql.BondFunctions.zSpread()`
   - Discount margin (DM) for floating rate bonds
3. Handle yield calculations appropriately
   - Document limitations of YTM for fix-to-float bonds
   - Implement where sensible, provide alternatives where not

**Success Criteria**:
- Accurate pricing given a yield curve
- Spread calculations match market conventions
- Clear documentation of calculation methodologies

### Phase 3: Risk Analytics
**Goal**: Implement duration, convexity, and other risk measures.

**Tasks**:
1. Implement duration calculation
   - Use `ql.BondFunctions.duration()` 
   - Account for floating rate reset risk
2. Implement convexity calculation
   - Use `ql.BondFunctions.convexity()`
3. Add DV01/PV01 calculations
4. Create tests comparing analytics to known values

**Success Criteria**:
- Duration reflects both fixed and floating period risks
- Analytics are consistent with market practices
- Comprehensive test coverage

### Phase 4: Integration with Existing Framework
**Goal**: Ensure fix-to-float bonds work seamlessly with existing analytics.

**Tasks**:
1. Extend `BondSpreadCalculator` to handle fix-to-float bonds
   - Adapt workout date logic for bonds that switch
   - Handle spread calculations appropriately
2. Ensure callable fix-to-float bonds are supported
   - Common structure: callable at or after switch date
3. Update documentation and examples
4. Performance testing with realistic portfolios

**Success Criteria**:
- Fix-to-float bonds work with all existing analytics
- No performance degradation
- Clear examples for users

## Technical Design Decisions

### 1. Cashflow Generation Approach
- **Decision**: Use composite approach with `ql.FixedRateLeg` + `ql.IborLeg`
- **Rationale**: 
  - Leverages existing QuantLib functionality
  - Clear separation of fixed/floating logic
  - Easier to maintain and debug

### 2. Floating Rate Index
- **Decision**: Support both `ql.OvernightIndex` (SOFR) and `ql.IborIndex` (LIBOR)
- **Implementation**:
  ```python
  # For SOFR (overnight index)
  sofr_index = ql.OvernightIndex(
      "SOFR", 1, ql.USDCurrency(), 
      ql.UnitedStates(ql.UnitedStates.GovernmentBond),
      ql.Actual360(), ts_handle
  )
  
  # For term rates (if needed)
  term_sofr = ql.IborIndex(
      "TermSOFR", ql.Period("3M"), 2, ql.USDCurrency(),
      ql.UnitedStates(ql.UnitedStates.GovernmentBond),
      ql.ModifiedFollowing, False, ql.Actual360(), ts_handle
  )
  ```

### 3. Analytics Approach
- **Decision**: Use QuantLib's `BondFunctions` where possible
- **Special Handling**:
  - Duration: Account for floating rate resets
  - Spreads: Focus on Z-spread and discount margin
  - YTM: Document limitations, provide alternatives

### 4. Testing Strategy
- **Unit Tests**: Each component tested in isolation
- **Integration Tests**: Full workflow from creation to analytics
- **Regression Tests**: Ensure no impact on existing functionality
- **Market Data Tests**: Validate against real market examples

## Risk Mitigation

### 1. Maintain Backward Compatibility
- No changes to existing bond classes
- All existing tests must continue to pass
- New functionality is additive only

### 2. Performance Considerations
- Profile performance impact
- Optimize cashflow generation if needed
- Consider caching for repeated calculations

### 3. Edge Cases
- Bonds switching on non-business days
- Very short fixed or floating periods
- Negative rates scenarios
- Missing rate fixings

## Definition of Done

Each phase is complete when:
1. All code is implemented and documented
2. Comprehensive tests are written and passing
3. Integration with existing code is verified
4. Performance impact is measured and acceptable
5. Documentation is updated with examples

## Timeline Estimate

- Phase 1: 2-3 hours (Basic structure and cashflows)
- Phase 2: 2-3 hours (Pricing and spreads)
- Phase 3: 2-3 hours (Risk analytics)
- Phase 4: 1-2 hours (Integration and polish)

Total: 8-11 hours of focused development

## Next Steps

1. Create test file structure
2. Implement failing tests for Phase 1
3. Build minimal implementation to pass tests
4. Iterate through each phase