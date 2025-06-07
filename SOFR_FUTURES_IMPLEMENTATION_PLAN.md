# SOFR Futures Implementation Plan

## Overview
Enhance the floating rate bond analytics to use market-implied forward rates from SOFR futures and swaps, providing more accurate pricing and risk measures.

## Phase 1: Data Infrastructure (Week 1)

### 1.1 Create SOFR Curve Data Structures
- [ ] Create `SOFRCurvePoint` dataclass for curve points
- [ ] Create `SOFRCurveData` class to hold complete curve
- [ ] Add tenor parsing utilities (ON, 1W, 2M, 3Y, etc.)

### 1.2 SOFR Curve Loader
- [ ] Create `SOFRCurveLoader` to read CSV data
- [ ] Parse tenors into QuantLib periods
- [ ] Convert yields to decimal format
- [ ] Handle different data sources (futures vs swaps)

### 1.3 Curve Building Infrastructure
- [ ] Create `SOFRCurveBuilder` class
- [ ] Implement deposit rate helpers for short end (ON to 3M)
- [ ] Implement swap rate helpers for long end (1Y+)
- [ ] Add futures rate helpers support for future enhancement

## Phase 2: Curve Construction (Week 1-2)

### 2.1 QuantLib Curve Building
- [ ] Build bootstrapped SOFR curve from market data
- [ ] Handle different interpolation methods
- [ ] Add convexity adjustments for futures (when applicable)
- [ ] Implement curve validation and sanity checks

### 2.2 Integration with Market Data Service
- [ ] Add `get_sofr_curve_from_market_data()` method
- [ ] Cache built curves for performance
- [ ] Support real-time updates
- [ ] Add curve quality metrics

## Phase 3: Floating Rate Bond Enhancement (Week 2)

### 3.1 Update FloatingRateBond Class
- [ ] Add optional parameter for market-based curve
- [ ] Modify `build_bond()` to use provided curve
- [ ] Ensure backward compatibility
- [ ] Update pricer setup for market curves

### 3.2 Forward Rate Projection
- [ ] Implement forward rate calculation from curve
- [ ] Add spread duration calculation
- [ ] Improve DV01 calculation accuracy
- [ ] Add key rate duration support

## Phase 4: Analytics Enhancement (Week 2-3)

### 4.1 Advanced Risk Measures
- [ ] Implement partial durations (bucketed risk)
- [ ] Add forward DV01 calculation
- [ ] Create spread risk measures
- [ ] Add curve scenario analysis

### 4.2 Cashflow Projections
- [ ] Project floating cashflows using forward curve
- [ ] Add cashflow sensitivity analysis
- [ ] Implement "what-if" scenarios
- [ ] Create detailed cashflow reports

## Phase 5: Testing & Validation (Week 3)

### 5.1 Unit Tests
- [ ] Test curve construction from CSV
- [ ] Test forward rate calculations
- [ ] Test bond pricing with market curve
- [ ] Test risk measures accuracy

### 5.2 Integration Tests
- [ ] End-to-end pricing workflow
- [ ] Performance benchmarking
- [ ] Curve consistency checks
- [ ] Comparison with market prices

## Phase 6: Documentation & Examples (Week 3-4)

### 6.1 Technical Documentation
- [ ] Document curve construction methodology
- [ ] Explain convexity adjustments
- [ ] Detail forward rate calculations
- [ ] Add troubleshooting guide

### 6.2 Usage Examples
- [ ] Basic SOFR curve construction
- [ ] Floating bond pricing with market data
- [ ] Risk analysis examples
- [ ] Portfolio analytics

## Implementation Priority

1. **Immediate (Today)**: 
   - Create data structures and loader
   - Build basic curve from CSV data
   - Integrate with FloatingRateBond

2. **Short-term (This Week)**:
   - Enhance risk calculations
   - Add comprehensive tests
   - Update documentation

3. **Medium-term (Next Week)**:
   - Add futures support
   - Implement advanced analytics
   - Create production examples

## Key Benefits

1. **Accuracy**: Market-implied rates vs simple interpolation
2. **Consistency**: Align with market pricing
3. **Risk Management**: Better forward risk measures
4. **Flexibility**: Support multiple data sources
5. **Performance**: Cached curve construction

## Success Criteria

- [ ] SOFR curve builds successfully from CSV data
- [ ] Floating bonds price using market curve
- [ ] Risk measures reflect forward curve shape
- [ ] All existing tests continue to pass
- [ ] Performance remains acceptable (<100ms pricing)