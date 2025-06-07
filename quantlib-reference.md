# QuantLib Python Reference Guide

## Table of Contents

1. [Basics and Settings](#basics-and-settings)
2. [Bonds](#bonds)
3. [Indexes](#indexes)
4. [Pricing Engines](#pricing-engines)
5. [Pricing Models](#pricing-models)
6. [Term Structures](#term-structures)
7. [Stochastic Processes](#stochastic-processes)
8. [Cash Flows, Legs and Interest Rates](#cash-flows-legs-and-interest-rates)
9. [Practical Examples](#practical-examples)

---

## Basics and Settings

### Import and Initial Setup

```python
import QuantLib as ql
```

### Setting Evaluation Date

The evaluation date is the date on which you want to value an instrument.

```python
# Set the evaluation date
today = ql.Date(15, 6, 2020)
ql.Settings.instance().evaluationDate = today

# Alternative method
today = ql.Date(15, 12, 2021)
ql.Settings.instance().setEvaluationDate(today)
```

### Creating Basic Term Structures

```python
# Basic parameters
settlementDays = 2
calendar = ql.UnitedStates()
forwardRate = 0.05
dayCounter = ql.Actual360()

# Construct flat forward rate term structure
flatForwardTermStructure = ql.FlatForward(settlementDays, calendar, forwardRate, dayCounter)

# Get reference date and max date
reference_date = flatForwardTermStructure.referenceDate()
max_date = flatForwardTermStructure.maxDate()
```

### Arrays and Matrices

```python
# Create arrays
empty_array = ql.Array()
filled_array = ql.Array(size, value)
incremental_array = ql.Array(size, value, increment)

# Create matrices
empty_matrix = ql.Matrix()
sized_matrix = ql.Matrix(rows, columns)
filled_matrix = ql.Matrix(rows, columns, value)

# Matrix operations
A = ql.Matrix(3, 3)
A[0][0] = 0.2
A[0][1] = 8.4
# ... etc
```

### Observable Pattern

```python
# Create observer
flag = None
def raiseFlag():
    global flag
    flag = 1

me = ql.SimpleQuote(0.0)
obs = ql.Observer(raiseFlag)
obs.registerWith(me)
me.setValue(3.14)  # This triggers the observer
```

### Quotes

```python
# Simple Quote
simple_quote = ql.SimpleQuote(0.01)
simple_quote.value()
simple_quote.setValue(0.05)
simple_quote.isValid()

# Derived Quote
base_quote = ql.SimpleQuote(0.06)
derived = ql.DerivedQuote(ql.QuoteHandle(base_quote), lambda x: 10*x)

# Composite Quote
quote1 = ql.SimpleQuote(0.02)
quote2 = ql.SimpleQuote(0.03)
composite = ql.CompositeQuote(
    ql.QuoteHandle(quote1), 
    ql.QuoteHandle(quote2), 
    lambda x,y: x+y
)
```

---

## Bonds

### Basic Bond Types

#### Zero Coupon Bond

```python
bond = ql.ZeroCouponBond(
    settlementDays=2,
    calendar=ql.TARGET(),
    faceAmount=100,
    maturityDate=ql.Date(20, 6, 2020)
)
```

#### Fixed Rate Bond

```python
# Method 1: With explicit parameters
bond = ql.FixedRateBond(
    settlementDays=2,
    calendar=ql.TARGET(),
    faceAmount=100.0,
    startDate=ql.Date(15, 12, 2019),
    maturityDate=ql.Date(15, 12, 2024),
    tenor=ql.Period('1Y'),
    coupons=[0.05],
    paymentConvention=ql.ActualActual(ql.ActualActual.Bond)
)

# Method 2: With schedule
schedule = ql.MakeSchedule(
    ql.Date(15, 12, 2019), 
    ql.Date(15, 12, 2024), 
    ql.Period('1Y')
)
bond = ql.FixedRateBond(
    settlementDays=2,
    faceAmount=100.0,
    schedule=schedule,
    coupons=[0.05],
    paymentConvention=ql.ActualActual(ql.ActualActual.Bond)
)
```

#### Floating Rate Bond

```python
schedule = ql.MakeSchedule(
    ql.Date(15, 6, 2020), 
    ql.Date(15, 6, 2022), 
    ql.Period('6m')
)
index = ql.Euribor6M()
bond = ql.FloatingRateBond(
    settlementDays=2,
    faceAmount=100,
    schedule=schedule,
    index=index,
    dayCounter=ql.Actual360(),
    spreads=[0.01]
)
```

#### Amortizing Bonds

```python
# Amortizing Fixed Rate Bond
notionals = [100, 100, 100, 50]
schedule = ql.MakeSchedule(
    ql.Date(25, 1, 2018), 
    ql.Date(25, 1, 2022), 
    ql.Period('1y')
)
bond = ql.AmortizingFixedRateBond(
    settlementDays=0,
    notionals=notionals,
    schedule=schedule,
    coupons=[0.03],
    accrualDayCounter=ql.Thirty360(ql.Thirty360.USA)
)

# Amortizing Floating Rate Bond
notionals = [100, 50]
schedule = ql.MakeSchedule(
    ql.Date(15, 6, 2020), 
    ql.Date(15, 6, 2022), 
    ql.Period('1Y')
)
index = ql.Euribor6M()
bond = ql.AmortizingFloatingRateBond(
    settlementDays=2,
    notionals=notionals,
    schedule=schedule,
    index=index,
    dayCounter=ql.ActualActual(ql.ActualActual.Bond)
)
```

#### Callable Bond

```python
schedule = ql.MakeSchedule(
    ql.Date(15, 6, 2020), 
    ql.Date(15, 6, 2022), 
    ql.Period('1Y')
)
putCallSchedule = ql.CallabilitySchedule()

call_price = ql.BondPrice(100, ql.BondPrice.Clean)
putCallSchedule.append(
    ql.Callability(call_price, ql.Callability.Call, ql.Date(15, 6, 2021))
)

bond = ql.CallableFixedRateBond(
    settlementDays=2,
    faceAmount=100,
    schedule=schedule,
    coupons=[0.01],
    accrualDayCounter=ql.Actual360(),
    paymentConvention=ql.ModifiedFollowing,
    redemption=100,
    issueDate=ql.Date(15, 6, 2020),
    putCallSchedule=putCallSchedule
)
```

### Bond Analytics

```python
# Create a bond and pricing engine
bond = ql.FixedRateBond(...)
crv = ql.FlatForward(2, ql.TARGET(), 0.04, ql.Actual360())
yts = ql.YieldTermStructureHandle(crv)
engine = ql.DiscountingBondEngine(yts)
bond.setPricingEngine(engine)

# Price calculations
clean_price = bond.cleanPrice()
dirty_price = bond.dirtyPrice()
npv = bond.NPV()

# Yield calculations
bond_yield = bond.bondYield(ql.Actual360(), ql.Compounded, ql.Annual)
bond_yield_from_price = bond.bondYield(100, ql.Actual360(), ql.Compounded, ql.Annual)

# Cash flow analysis
start_date = ql.BondFunctions.startDate(bond)
maturity_date = ql.BondFunctions.maturityDate(bond)
accrual_days = ql.BondFunctions.accruedDays(bond)
accrued_amount = ql.BondFunctions.accruedAmount(bond)

# Risk measures
duration = ql.BondFunctions.duration(bond, yts)
convexity = ql.BondFunctions.convexity(bond, yts)
bps = ql.BondFunctions.bps(bond, yts)

# Z-spread
z_spread = ql.BondFunctions.zSpread(bond, 101, crv, ql.Actual360(), ql.Compounded, ql.Annual)
```

---

## Indexes

### Interest Rate Indexes

#### IborIndex

```python
# Custom IborIndex
custom_index = ql.IborIndex(
    familyName='MyIndex',
    tenor=ql.Period('6m'),
    settlementDays=2,
    currency=ql.EURCurrency(),
    fixingCalendar=ql.TARGET(),
    convention=ql.ModifiedFollowing,
    endOfMonth=True,
    dayCounter=ql.Actual360()
)

# Pre-defined indexes
euribor6m = ql.Euribor6M()
usd_libor = ql.USDLibor(ql.Period('6M'))
```

#### OvernightIndex

```python
overnight_index = ql.OvernightIndex(
    name='CNYRepo7D',
    fixingDays=1,
    currency=ql.CNYCurrency(),
    calendar=ql.China(),
    dayCounter=ql.Actual365Fixed()
)

# Pre-defined overnight indexes
eonia = ql.Eonia()
```

#### SwapIndex

```python
# Create swap index
swap_index = ql.EuriborSwapIsdaFixA(ql.Period('10Y'))

# With custom yield term structure
yts = ql.YieldTermStructureHandle(...)
swap_index_custom = ql.EuriborSwapIsdaFixA(ql.Period('10Y'), yts)
```

### Index Fixings

```python
# Add fixings to an index
index = ql.Euribor3M()
index.clearFixings()
index.addFixing(ql.Date(17, 7, 2018), -0.003)
index.addFixings([ql.Date(12, 7, 2018), ql.Date(13, 7, 2018)], [-0.003, -0.003])

# Check if fixing date is valid
is_valid = index.isValidFixingDate(ql.Date(25, 12, 2019))

# Get fixing calendar
calendar = index.fixingCalendar()
```

---

## Pricing Engines

### Bond Pricing Engines

```python
# Discounting Bond Engine
crv = ql.FlatForward(ql.Date().todaysDate(), 0.04875825, ql.Actual365Fixed())
yts = ql.YieldTermStructureHandle(crv)
engine = ql.DiscountingBondEngine(yts)

# Black Callable Fixed Rate Bond Engine
vol = ql.QuoteHandle(ql.SimpleQuote(0.55))
engine = ql.BlackCallableFixedRateBondEngine(vol, yts)

# Tree Callable Fixed Rate Engine
model = ql.Vasicek()
engine = ql.TreeCallableFixedRateBondEngine(model, 10, yts)
```

### Cap/Floor Pricing Engines

```python
# Black Cap Floor Engine
vols = ql.QuoteHandle(ql.SimpleQuote(0.547295))
engine = ql.BlackCapFloorEngine(yts, vols)

# Bachelier Cap Floor Engine
vols = ql.QuoteHandle(ql.SimpleQuote(0.00547295))
engine = ql.BachelierCapFloorEngine(yts, vols)

# Analytic Cap Floor Engine
model = ql.HullWhite(yts)
engine = ql.AnalyticCapFloorEngine(model, yts)

# Tree Cap Floor Engine
model = ql.HullWhite(yts)
engine = ql.TreeCapFloorEngine(model, 60, yts)
```

### Swap Pricing Engines

```python
# Discounting Swap Engine
yts = ql.YieldTermStructureHandle(ql.FlatForward(2, ql.TARGET(), 0.05, ql.Actual360()))
engine = ql.DiscountingSwapEngine(yts)
```

### Swaption Pricing Engines

```python
# Black Swaption Engine
vol_quote = ql.QuoteHandle(ql.SimpleQuote(0.55))
engine = ql.BlackSwaptionEngine(yts, vol_quote)

# Bachelier Swaption Engine
vol_quote = ql.QuoteHandle(ql.SimpleQuote(0.0055))
engine = ql.BachelierSwaptionEngine(yts, vol_quote)

# Hull-White Swaption Engines
model = ql.HullWhite(yts)
fd_engine = ql.FdHullWhiteSwaptionEngine(model)
tree_engine = ql.TreeSwaptionEngine(model, 10)
jamshidian_engine = ql.JamshidianSwaptionEngine(model, yts)

# G2 Swaption Engines
model = ql.G2(yts)
fd_engine = ql.FdG2SwaptionEngine(model)
g2_engine = ql.G2SwaptionEngine(model, 4, 4)
```

### Option Pricing Engines

#### Vanilla Options

```python
# Create process
today = ql.Date().todaysDate()
spot = ql.QuoteHandle(ql.SimpleQuote(100))
riskFreeTS = ql.YieldTermStructureHandle(ql.FlatForward(today, 0.05, ql.Actual365Fixed()))
dividendTS = ql.YieldTermStructureHandle(ql.FlatForward(today, 0.01, ql.Actual365Fixed()))
volatility = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, ql.NullCalendar(), 0.1, ql.Actual365Fixed()))
process = ql.BlackScholesMertonProcess(spot, dividendTS, riskFreeTS, volatility)

# Analytic European Engine
engine = ql.AnalyticEuropeanEngine(process)

# Monte Carlo European Engine
engine = ql.MCEuropeanEngine(process, "pseudorandom", timeSteps=2, requiredSamples=100000)

# Finite Difference Engine
engine = ql.FdBlackScholesVanillaEngine(process, tGrid=2000, xGrid=200)

# American Engine
engine = ql.MCAmericanEngine(process, "pseudorandom", timeSteps=200, requiredSamples=100000)
```

#### Heston Model Engines

```python
# Create Heston process
v0, kappa, theta, rho, sigma = 0.005, 0.8, 0.008, 0.2, 0.1
hestonProcess = ql.HestonProcess(riskFreeTS, dividendTS, spot, v0, kappa, theta, sigma, rho)
hestonModel = ql.HestonModel(hestonProcess)

# Analytic Heston Engine
engine = ql.AnalyticHestonEngine(hestonModel)

# MC European Heston Engine
engine = ql.MCEuropeanHestonEngine(hestonProcess, "pseudorandom", timeSteps=2, requiredSamples=100000)

# FD Heston Vanilla Engine
engine = ql.FdHestonVanillaEngine(hestonModel, tGrid=100, xGrid=100, vGrid=50)
```

#### Asian Options

```python
# Analytic Engines
engine = ql.AnalyticDiscreteGeometricAveragePriceAsianEngine(process)
engine = ql.AnalyticContinuousGeometricAveragePriceAsianEngine(process)

# Monte Carlo Engines
engine = ql.MCDiscreteGeometricAPEngine(process, "pseudorandom", requiredSamples=100000)
engine = ql.MCDiscreteArithmeticAPEngine(process, "pseudorandom", requiredSamples=100000)

# Finite Difference Engine
engine = ql.FdBlackScholesAsianEngine(process, tGrid=100, xGrid=100, aGrid=50)

# Turnbull-Wakeman Engine
engine = ql.TurnbullWakemanAsianEngine(process)
```

#### Barrier Options

```python
# Create process
spotHandle = ql.QuoteHandle(ql.SimpleQuote(100))
flatRateTs = ql.YieldTermStructureHandle(ql.FlatForward(today, 0.05, ql.Actual365Fixed()))
flatVolTs = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, ql.UnitedStates(), 0.2, ql.Actual365Fixed()))
bsm = ql.BlackScholesProcess(spotHandle, flatRateTs, flatVolTs)

# Binomial Barrier Engine
engine = ql.BinomialBarrierEngine(bsm, 'crr', 200)

# Analytic Barrier Engine
engine = ql.AnalyticBarrierEngine(bsm)

# FD Barrier Engines
engine = ql.FdBlackScholesBarrierEngine(bsm)
engine = ql.FdBlackScholesRebateEngine(bsm)

# Double Barrier Engines
engine = ql.AnalyticDoubleBarrierEngine(bsm)
engine = ql.AnalyticDoubleBarrierBinaryEngine(bsm)
```

---

## Pricing Models

### Equity Models

#### Heston Model

```python
# Standard Heston Model
today = ql.Date().todaysDate()
riskFreeTS = ql.YieldTermStructureHandle(ql.FlatForward(today, 0.05, ql.Actual365Fixed()))
dividendTS = ql.YieldTermStructureHandle(ql.FlatForward(today, 0.01, ql.Actual365Fixed()))
s0 = ql.QuoteHandle(ql.SimpleQuote(100))

v0, kappa, theta, sigma, rho = 0.005, 0.6, 0.01, 0.4, -0.15
hestonProcess = ql.HestonProcess(riskFreeTS, dividendTS, s0, v0, kappa, theta, sigma, rho)
hestonModel = ql.HestonModel(hestonProcess)

# Piecewise Time-Dependent Heston Model
times = [1.0, 2.0, 3.0]
grid = ql.TimeGrid(times)

# Time-dependent parameters
theta_values = [0.010, 0.015, 0.02]
kappa_values = [0.600, 0.500, 0.400]
sigma_values = [0.400, 0.350, 0.300]
rho_values = [-0.15, -0.10, 0.00]

# Create parameter structures
kappaTS = ql.PiecewiseConstantParameter(times[:-1], ql.PositiveConstraint())
thetaTS = ql.PiecewiseConstantParameter(times[:-1], ql.PositiveConstraint())
rhoTS = ql.PiecewiseConstantParameter(times[:-1], ql.BoundaryConstraint(-1.0, 1.0))
sigmaTS = ql.PiecewiseConstantParameter(times[:-1], ql.PositiveConstraint())

# Set parameters
for i, time in enumerate(times):
    kappaTS.setParam(i, kappa_values[i])
    thetaTS.setParam(i, theta_values[i])
    rhoTS.setParam(i, rho_values[i])
    sigmaTS.setParam(i, sigma_values[i])

hestonModelPTD = ql.PiecewiseTimeDependentHestonModel(
    riskFreeTS, dividendTS, s0, v0, thetaTS, kappaTS, sigmaTS, rhoTS, grid
)
```

### Short Rate Models

#### One Factor Models

```python
# Vasicek Model
vasicek = ql.Vasicek(r0=0.05, a=0.1, b=0.05, sigma=0.01, lambda_=0.0)

# Hull-White Model
hull_white = ql.HullWhite(yts, a=0.1, sigma=0.01)

# Black-Karasinski Model
black_karasinski = ql.BlackKarasinski(yts, a=0.1, sigma=0.1)

# GSR Model
times = [1, 2, 3, 4, 5, 6, 7, 8, 9]
sigmas = [0.01] * 10
reversion = 0.01
gsr = ql.GsrProcess(times, sigmas, [reversion])
```

#### Two Factor Models

```python
# G2 Model
g2 = ql.G2(yts, a=0.1, sigma=0.01, b=0.1, eta=0.01, rho=-0.75)
```

---

## Term Structures

### Yield Term Structures

#### Flat Forward

```python
# Different constructors
flat_forward = ql.FlatForward(ql.Date(15, 6, 2020), ql.QuoteHandle(ql.SimpleQuote(0.05)), ql.Actual360())
flat_forward = ql.FlatForward(2, ql.TARGET(), 0.05, ql.Actual360())
```

#### Discount Curve

```python
dates = [ql.Date(7, 5, 2019), ql.Date(7, 5, 2020), ql.Date(7, 5, 2021)]
discount_factors = [1, 0.99, 0.98]
dayCounter = ql.Actual360()
curve = ql.DiscountCurve(dates, discount_factors, dayCounter)
```

#### Zero Curve

```python
dates = [ql.Date(31, 12, 2019), ql.Date(31, 12, 2020), ql.Date(31, 12, 2021)]
zeros = [0.01, 0.02, 0.03]

# Different interpolation methods
zero_curve = ql.ZeroCurve(dates, zeros, ql.ActualActual(), ql.TARGET())
log_linear_zero = ql.LogLinearZeroCurve(dates, zeros, ql.ActualActual(), ql.TARGET())
cubic_zero = ql.CubicZeroCurve(dates, zeros, ql.ActualActual(), ql.TARGET())
natural_cubic = ql.NaturalCubicZeroCurve(dates, zeros, ql.ActualActual(), ql.TARGET())
log_cubic = ql.LogCubicZeroCurve(dates, zeros, ql.ActualActual(), ql.TARGET())
monotonic_cubic = ql.MonotonicCubicZeroCurve(dates, zeros, ql.ActualActual(), ql.TARGET())
```

#### Bootstrapped Curves

```python
# Create rate helpers
helpers = []
helpers.append(ql.DepositRateHelper(0.05, ql.Euribor6M()))
helpers.append(ql.SwapRateHelper(0.06, ql.EuriborSwapIsdaFixA(ql.Period('1y'))))

# Bootstrap curve
curve = ql.PiecewiseLogLinearDiscount(ql.Date(15, 6, 2020), helpers, ql.Actual360())

# Other bootstrap methods
log_cubic_discount = ql.PiecewiseLogCubicDiscount(ql.Date(15, 6, 2020), helpers, ql.Actual360())
linear_zero = ql.PiecewiseLinearZero(ql.Date(15, 6, 2020), helpers, ql.Actual360())
cubic_zero = ql.PiecewiseCubicZero(ql.Date(15, 6, 2020), helpers, ql.Actual360())
linear_forward = ql.PiecewiseLinearForward(ql.Date(15, 6, 2020), helpers, ql.Actual360())
```

#### Fitted Bond Curves

```python
# Create bond helpers
bond_helpers = []
# ... populate bond_helpers

# Fitting methods
nelson_siegel = ql.NelsonSiegelFitting()
svensson = ql.SvenssonFitting()
simple_poly = ql.SimplePolynomialFitting(2)
exponential_splines = ql.ExponentialSplinesFitting()
cubic_bsplines = ql.CubicBSplinesFitting([-30.0, -20.0, 0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0])

# Create fitted curve
fitted_curve = ql.FittedBondDiscountCurve(
    bondSettlementDate, 
    bond_helpers, 
    dayCounter, 
    nelson_siegel
)
```

### Volatility Term Structures

#### Black Volatility

```python
# Constant volatility
constant_vol = ql.BlackConstantVol(
    ql.Date().todaysDate(), 
    ql.TARGET(), 
    0.2, 
    ql.Actual360()
)

# Variance curve
dates = [ql.Date(20, 12, 2013), ql.Date(17, 1, 2014), ql.Date(21, 3, 2014)]
vols = [0.145, 0.156, 0.165]
var_curve = ql.BlackVarianceCurve(ql.Date(30, 9, 2013), dates, vols, ql.Actual360())

# Variance surface
strikes = [1650.0, 1660.0, 1670.0]
vol_matrix = ql.Matrix(len(strikes), len(dates))
# ... populate vol_matrix
var_surface = ql.BlackVarianceSurface(
    ql.Date(30, 9, 2013),
    ql.TARGET(),
    dates,
    strikes,
    vol_matrix,
    ql.ActualActual()
)
```

#### Local Volatility

```python
# Local constant vol
local_const_vol = ql.LocalConstantVol(ql.Date().todaysDate(), 0.2, ql.Actual360())

# Local vol surface
black_vol_ts = ql.BlackVolTermStructureHandle(constant_vol)
rates_ts = ql.YieldTermStructureHandle(ql.FlatForward(today, 0.02, ql.Actual365Fixed()))
dividend_ts = ql.YieldTermStructureHandle(ql.FlatForward(today, 0.05, ql.Actual365Fixed()))
local_vol = ql.LocalVolSurface(black_vol_ts, rates_ts, dividend_ts, 100)

# No-exception local vol surface (with override value)
no_except_local_vol = ql.NoExceptLocalVolSurface(
    black_vol_ts, rates_ts, dividend_ts, 100, 
    illegalVolOverride=0.25
)
```

#### Cap/Floor Volatility

```python
# Constant optionlet volatility
const_optionlet_vol = ql.ConstantOptionletVolatility(
    settlementDays=2,
    cal=ql.TARGET(),
    bdc=ql.ModifiedFollowing,
    volatility=0.55,
    dc=ql.Actual365Fixed()
)

# Cap/floor term vol curve
option_tenors = [ql.Period('1y'), ql.Period('2y'), ql.Period('3y')]
vols = [0.55, 0.60, 0.65]
cap_floor_curve = ql.CapFloorTermVolCurve(
    settlementDate=ql.Date().todaysDate(),
    calendar=ql.TARGET(),
    bdc=ql.ModifiedFollowing,
    optionTenors=option_tenors,
    vols=vols
)

# Cap/floor term vol surface
expiries = [ql.Period('9y'), ql.Period('10y'), ql.Period('12y')]
strikes = [0.015, 0.02, 0.025]
vol_data = [[1.0, 0.792, 0.6873], [0.9301, 0.7401, 0.6403], [0.7926, 0.6424, 0.5602]]
cap_floor_surface = ql.CapFloorTermVolSurface(
    settlementDate=ql.Date().todaysDate(),
    calendar=ql.TARGET(),
    bdc=ql.ModifiedFollowing,
    expiries=expiries,
    strikes=strikes,
    vol_data=vol_data
)

# Optionlet stripper
index = ql.Euribor6M()
optionlet_stripper = ql.OptionletStripper1(cap_floor_surface, index)
stripped_optionlet_vol = ql.StrippedOptionletAdapter(optionlet_stripper)
```

#### Swaption Volatility

```python
# Constant swaption volatility
const_swaption_vol = ql.ConstantSwaptionVolatility(
    settlementDays=2,
    cal=ql.TARGET(),
    bdc=ql.ModifiedFollowing,
    volatility=ql.QuoteHandle(ql.SimpleQuote(0.55)),
    dc=ql.ActualActual()
)

# Swaption volatility matrix
swap_tenors = [ql.Period('1Y'), ql.Period('2Y'), ql.Period('3Y'), ql.Period('5Y'), ql.Period('10Y')]
option_tenors = [ql.Period('1M'), ql.Period('3M'), ql.Period('6M'), ql.Period('1Y'), ql.Period('2Y')]
normal_vols = ql.Matrix(len(option_tenors), len(swap_tenors))
# ... populate normal_vols

swaption_vol_matrix = ql.SwaptionVolatilityMatrix(
    ql.TARGET(),
    ql.ModifiedFollowing,
    option_tenors,
    swap_tenors,
    normal_vols,
    ql.ActualActual(),
    False,
    ql.Normal
)
```

### SABR Model

```python
# SABR parameters
alpha, beta, nu, rho = 1.63, 0.6, 3.3, 0.00002

# SABR smile section
sabr_smile = ql.SabrSmileSection(17/365, 120, [alpha, beta, nu, rho])

# SABR volatility functions
vol = ql.sabrVolatility(strike=106, forward=120, expiryTime=17/365, 
                        alpha=alpha, beta=beta, nu=nu, rho=rho)

shifted_vol = ql.shiftedSabrVolatility(strike=106, forward=120, expiryTime=17/365,
                                        alpha=alpha, beta=beta, nu=nu, rho=rho, shift=50)

floch_kennedy_vol = ql.sabrFlochKennedyVolatility(strike=0.01, forward=0.01, expiryTime=5,
                                                   alpha=0.01, beta=0.01, nu=0.01, rho=0.01)
```

### Credit Term Structures

```python
# Flat hazard rate
pd_curve = ql.FlatHazardRate(
    settlementDays=2,
    calendar=ql.TARGET(),
    hazardRate=ql.QuoteHandle(ql.SimpleQuote(0.05)),
    dayCounter=ql.Actual360()
)

# Piecewise flat hazard rate
recovery_rate = 0.4
settlement_date = ql.Date().todaysDate()
yts = ql.FlatForward(2, ql.TARGET(), 0.05, ql.Actual360())

# Create CDS helpers
cds_tenors = [ql.Period(6, ql.Months), ql.Period(1, ql.Years), ql.Period(2, ql.Years)]
cds_spreads = [26.65, 37.22, 53.17]  # in basis points

cds_helpers = []
for spread, tenor in zip(cds_spreads, cds_tenors):
    helper = ql.SpreadCdsHelper(
        spread / 10000.0,
        tenor,
        0,
        ql.TARGET(),
        ql.Quarterly,
        ql.Following,
        ql.DateGeneration.TwentiethIMM,
        ql.Actual360(),
        recovery_rate,
        ql.YieldTermStructureHandle(yts)
    )
    cds_helpers.append(helper)

pd_curve = ql.PiecewiseFlatHazardRate(settlement_date, cds_helpers, ql.Thirty360())

# Survival probability curve
today = ql.Date().todaysDate()
dates = [today + ql.Period(n, ql.Years) for n in range(11)]
survival_probs = [1.0, 0.9941, 0.9826, 0.9674, 0.9488, 0.9246, 0.8945, 0.8645, 0.83484, 0.80614, 0.7784]
surv_curve = ql.SurvivalProbabilityCurve(dates, survival_probs, ql.Actual360(), ql.TARGET())
surv_curve.enableExtrapolation()
```

---

## Stochastic Processes

### Basic Processes

```python
# Geometric Brownian Motion
gbm = ql.GeometricBrownianMotionProcess(initialValue=100, mu=0.01, sigma=0.2)

# Ornstein-Uhlenbeck Process
ou = ql.ExtendedOrnsteinUhlenbeckProcess(speed=1.0, sigma=0.1, x0=0.0, 
                                          function=lambda x: 0.0)

# Ornstein-Uhlenbeck with Jumps
ou_base = ql.ExtendedOrnsteinUhlenbeckProcess(speed=1.0, sigma=0.1, x0=0.0, 
                                               function=lambda x: 0.0)
ou_jumps = ql.ExtOUWithJumpsProcess(ou_base, x1=0.0, beta=4.0, 
                                     jumpIntensity=1.0, eta=4.0)
```

### Equity Processes

```python
# Setup common parameters
today = ql.Date().todaysDate()
spot = ql.QuoteHandle(ql.SimpleQuote(100))
risk_free = ql.YieldTermStructureHandle(ql.FlatForward(today, 0.05, ql.Actual365Fixed()))
dividend = ql.YieldTermStructureHandle(ql.FlatForward(today, 0.01, ql.Actual365Fixed()))
vol = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, ql.NullCalendar(), 0.2, ql.Actual365Fixed()))

# Black-Scholes Process
bs_process = ql.BlackScholesProcess(spot, risk_free, vol)

# Black-Scholes-Merton Process
bsm_process = ql.BlackScholesMertonProcess(spot, dividend, risk_free, vol)

# Generalized Black-Scholes Process
gbs_process = ql.GeneralizedBlackScholesProcess(spot, dividend, risk_free, vol)

# Black Process (for futures/forwards)
black_process = ql.BlackProcess(spot, risk_free, vol)

# Merton Jump Diffusion Process
jump_intensity = ql.QuoteHandle(ql.SimpleQuote(1.0))
jump_vol = ql.QuoteHandle(ql.SimpleQuote(0.1))
mean_log_jump = ql.QuoteHandle(ql.SimpleQuote(-jump_vol.value()**2))
merton_process = ql.Merton76Process(spot, dividend, risk_free, vol, 
                                    jump_intensity, mean_log_jump, jump_vol)

# Variance Gamma Process
vg_process = ql.VarianceGammaProcess(spot, dividend, risk_free, 
                                     sigma=0.2, nu=1, theta=1)
```

### FX Processes

```python
# Garman-Kohlhagen Process
domestic_rate = ql.YieldTermStructureHandle(ql.FlatForward(today, 0.03, ql.Actual365Fixed()))
foreign_rate = ql.YieldTermStructureHandle(ql.FlatForward(today, 0.01, ql.Actual365Fixed()))
gk_process = ql.GarmanKohlagenProcess(spot, foreign_rate, domestic_rate, vol)
```

### Stochastic Volatility Processes

```python
# Heston Process
v0, kappa, theta, sigma, rho = 0.005, 0.8, 0.008, 0.1, 0.2
heston_process = ql.HestonProcess(risk_free, dividend, spot, v0, kappa, theta, sigma, rho)

# Heston SLV Process (Stochastic Local Vol)
# First create local vol surface...
# Then calibrate leverage function...
# leverage_fct = ...
# heston_slv = ql.HestonSLVProcess(heston_process, leverage_fct, mixingFactor=0.9)
```

### Interest Rate Processes

```python
# Hull-White Process
hw_process = ql.HullWhiteProcess(risk_free, a=0.001, sigma=0.1)

# Hull-White Forward Process
hw_fwd_process = ql.HullWhiteForwardProcess(risk_free, a=0.001, sigma=0.1)

# GSR Process
times = list(range(1, 10))
sigmas = [0.01] * 10
gsr_process = ql.GsrProcess(times, sigmas, [0.01])

# G2 Process
# g2_process = ql.G2Process(...)
```

### Multi-Asset Processes

```python
# Create individual processes
spots = [100., 100., 100., 100., 100.]
vols = [0.1, 0.12, 0.13, 0.09, 0.11]
correlation_matrix = [
    [1.0,  0.1, -0.1,  0.0,  0.0],
    [0.1,  1.0,  0.0,  0.0,  0.2],
    [-0.1, 0.0,  1.0,  0.0,  0.0],
    [0.0,  0.0,  0.0,  1.0, 0.15],
    [0.0,  0.2,  0.0, 0.15,  1.0]
]

processes = []
for spot, vol in zip(spots, vols):
    process = ql.BlackScholesMertonProcess(
        ql.QuoteHandle(ql.SimpleQuote(spot)),
        dividend,
        risk_free,
        ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, ql.NullCalendar(), vol, ql.Actual365Fixed()))
    )
    processes.append(process)

# Create multi-asset process
multi_process = ql.StochasticProcessArray(processes, correlation_matrix)
```

---

## Cash Flows, Legs and Interest Rates

### Interest Rates

```python
# Create interest rate object
rate = ql.InterestRate(0.05, ql.Actual360(), ql.Compounded, ql.Annual)

# Common operations
rate_value = rate.rate()
day_counter = rate.dayCounter()
discount_factor = rate.discountFactor(1.0)  # for 1 year
discount_factor = rate.discountFactor(ql.Date(15, 6, 2020), ql.Date(15, 6, 2021))
compound_factor = rate.compoundFactor(ql.Date(15, 6, 2020), ql.Date(15, 6, 2021))

# Equivalent rate with different conventions
equiv_rate = rate.equivalentRate(
    ql.Actual360(), 
    ql.Compounded, 
    ql.Semiannual, 
    ql.Date(15, 6, 2020), 
    ql.Date(15, 6, 2021)
)

# Implied rate from compound factor
implied_rate = ql.InterestRate.impliedRate(
    compound=1.05,
    resultDC=ql.Actual360(),
    comp=ql.Continuous,
    freq=ql.Annual,
    d1=ql.Date(15, 6, 2020),
    d2=ql.Date(15, 6, 2021)
)
```

### Cash Flows

```python
# Simple cash flow
cf = ql.SimpleCashFlow(amount=105, date=ql.Date(15, 6, 2020))

# Redemption
redemption = ql.Redemption(amount=100, date=ql.Date(15, 6, 2020))

# Amortizing payment
amortizing = ql.AmortizingPayment(amount=100, date=ql.Date(15, 6, 2020))
```

### Coupons

```python
# Fixed rate coupon
fixed_coupon = ql.FixedRateCoupon(
    paymentDate=ql.Date(15, 6, 2020),
    nominal=100.0,
    rate=0.05,
    dayCounter=ql.Actual360(),
    startDate=ql.Date(15, 12, 2019),
    endDate=ql.Date(15, 6, 2020)
)

# Floating rate coupon
index = ql.Euribor6M()
floating_coupon = ql.IborCoupon(
    paymentDate=ql.Date(15, 6, 2021),
    nominal=100.0,
    startDate=ql.Date(15, 12, 2020),
    endDate=ql.Date(15, 6, 2021),
    fixingDays=2,
    index=index
)

# Overnight indexed coupon
overnight_coupon = ql.OvernightIndexedCoupon(
    paymentDate=ql.Date(15, 9, 2020),
    nominal=100,
    startDate=ql.Date(15, 6, 2020),
    endDate=ql.Date(15, 9, 2020),
    overnightIndex=ql.Eonia()
)

# CMS coupon
swap_index = ql.EuriborSwapIsdaFixA(ql.Period("2Y"))
cms_coupon = ql.CmsCoupon(
    paymentDate=ql.Date(15, 6, 2021),
    nominal=100.0,
    startDate=ql.Date(15, 12, 2020),
    endDate=ql.Date(15, 6, 2021),
    fixingDays=2,
    swapIndex=swap_index
)

# CMS spread coupon
swap_index_10y = ql.EuriborSwapIsdaFixA(ql.Period("10Y"))
swap_index_2y = ql.EuriborSwapIsdaFixA(ql.Period("2Y"))
spread_index = ql.SwapSpreadIndex("CMS 10Y-2Y", swap_index_10y, swap_index_2y)
cms_spread_coupon = ql.CmsSpreadCoupon(
    paymentDate=ql.Date(15, 6, 2021),
    nominal=100.0,
    startDate=ql.Date(15, 12, 2020),
    endDate=ql.Date(15, 6, 2021),
    fixingDays=2,
    spreadIndex=spread_index
)
```

### Legs

```python
# Create a simple leg from cash flows
cf1 = ql.SimpleCashFlow(5.0, ql.Date().todaysDate() + 365)
cf2 = ql.SimpleCashFlow(5.0, ql.Date().todaysDate() + 365*2)
cf3 = ql.SimpleCashFlow(105.0, ql.Date().todaysDate() + 365*3)
simple_leg = ql.Leg([cf1, cf2, cf3])

# Fixed rate leg
schedule = ql.MakeSchedule(ql.Date(15, 6, 2020), ql.Date(15, 6, 2021), ql.Period('6M'))
fixed_leg = ql.FixedRateLeg(
    schedule=schedule,
    dayCount=ql.Actual360(),
    nominals=[100.0],
    couponRates=[0.05]
)

# Floating rate leg
index = ql.Euribor3M()
floating_leg = ql.IborLeg(
    nominals=[100],
    schedule=schedule,
    index=index,
    paymentDayCounter=ql.Actual360(),
    paymentConvention=ql.ModifiedFollowing,
    fixingDays=[2],
    gearings=[1],
    spreads=[0]
)

# Overnight leg
overnight_index = ql.Eonia()
overnight_leg = ql.OvernightLeg(
    nominals=[100],
    schedule=schedule,
    overnightIndex=overnight_index,
    paymentDayCounter=ql.Actual360(),
    paymentConvention=ql.Following,
    gearings=[1],
    spreads=[0],
    telescopicValueDates=True
)
```

### Pricers

```python
# Black Ibor Coupon Pricer
volatility = 0.10
vol_structure = ql.ConstantOptionletVolatility(
    2, ql.TARGET(), ql.Following, volatility, ql.Actual360()
)
pricer = ql.BlackIborCouponPricer(ql.OptionletVolatilityStructureHandle(vol_structure))

# Set pricer for all coupons in a leg
ql.setCouponPricer(floating_leg, pricer)

# Linear TSR Pricer
swaption_vol = ql.ConstantSwaptionVolatility(
    0, ql.TARGET(), ql.ModifiedFollowing, 
    ql.QuoteHandle(ql.SimpleQuote(0.2)), ql.Actual365Fixed()
)
mean_reversion = ql.QuoteHandle(ql.SimpleQuote(0.01))
tsr_pricer = ql.LinearTsrPricer(
    ql.SwaptionVolatilityStructureHandle(swaption_vol), 
    mean_reversion
)
```

### Cash Flow Analysis Functions

```python
# Create a sample leg
schedule = ql.MakeSchedule(ql.Date(15, 6, 2020), ql.Date(15, 6, 2023), ql.Period('6M'))
leg = ql.FixedRateLeg(schedule, ql.Actual360(), [100.0], [0.05])

# Date inspectors
start_date = ql.CashFlows.startDate(leg)
maturity_date = ql.CashFlows.maturityDate(leg)

# Cash flow inspectors
prev_cf_date = ql.CashFlows.previousCashFlowDate(leg, True, ql.Date(15, 12, 2020))
next_cf_date = ql.CashFlows.nextCashFlowDate(leg, True, ql.Date(15, 12, 2020))

# Valuation with yield term structure
yts = ql.YieldTermStructureHandle(ql.FlatForward(ql.Date(15, 1, 2020), 0.04, ql.Actual360()))
npv = ql.CashFlows.npv(leg, yts, True)
bps = ql.CashFlows.bps(leg, yts, True)
atm_rate = ql.CashFlows.atmRate(leg, yts, True)

# Valuation with interest rate
rate = ql.InterestRate(0.03, ql.ActualActual(), ql.Compounded, ql.Annual)
npv_rate = ql.CashFlows.npv(leg, rate, True)
bps_rate = ql.CashFlows.bps(leg, rate, True)
bpv = ql.CashFlows.basisPointValue(leg, rate, True)

# Duration and convexity
simple_duration = ql.CashFlows.duration(leg, rate, ql.Duration.Simple, False)
macaulay_duration = ql.CashFlows.duration(leg, rate, ql.Duration.Macaulay, False)
modified_duration = ql.CashFlows.duration(leg, rate, ql.Duration.Modified, False)
convexity = ql.CashFlows.convexity(leg, rate, False)

# Yield calculations
yield_rate = ql.CashFlows.yieldRate(
    leg, 
    npv, 
    ql.Actual360(), 
    ql.Compounded, 
    ql.Annual, 
    True,
    settlementDate=ql.Date(15, 6, 2020),
    npvDate=ql.Date(15, 6, 2020),
    accuracy=1e-10,
    maxIterations=100,
    guess=0.04
)

# Z-spread
z_spread = ql.CashFlows.zSpread(
    leg, 
    npv, 
    yts, 
    ql.Actual360(), 
    ql.Compounded, 
    ql.Annual, 
    True
)
```

---

## Practical Examples

### Pricing Caps

```python
import QuantLib as ql
import pandas as pd

# Set valuation date
ql.Settings.instance().evaluationDate = ql.Date(1, 1, 2022)

# Create curves
dates = [ql.Date(1, 1, 2022), ql.Date(1, 1, 2023), ql.Date(1, 1, 2024)]
discount_factors = [1, 0.965, 0.94]
discount_curve = ql.DiscountCurve(dates, discount_factors, ql.Actual360())
discount_handle = ql.YieldTermStructureHandle(discount_curve)

# Create cap schedule
start_date = ql.Date(1, 1, 2022)
end_date = start_date + ql.Period(12, ql.Months)
schedule = ql.Schedule(
    start_date, end_date, ql.Period(3, ql.Months),
    ql.Sweden(), ql.ModifiedFollowing, ql.ModifiedFollowing,
    ql.DateGeneration.Backward, False
)

# Create index and cap
index = ql.IborIndex(
    "MyIndex", ql.Period("3m"), 0, ql.SEKCurrency(),
    ql.Sweden(), ql.ModifiedFollowing, False, ql.Actual360(),
    discount_handle
)
ibor_leg = ql.IborLeg([1e6], schedule, index)
cap = ql.Cap(ibor_leg, [0.025])

# Price with constant volatility
volatility = ql.QuoteHandle(ql.SimpleQuote(0.5))
engine = ql.BlackCapFloorEngine(discount_handle, volatility)
cap.setPricingEngine(engine)
cap_npv = cap.NPV()

# Create volatility surface
expiries = [ql.Period("3M"), ql.Period("6M"), ql.Period("9M"), ql.Period("1Y")]
strikes = [0.010, 0.025, 0.03]
black_vols = [
    [0.98, 0.792, 0.6873],
    [0.9301, 0.7401, 0.6403],
    [0.7926, 0.6424, 0.5602],
    [0.7126, 0.6024, 0.4902]
]

vol_surface = ql.CapFloorTermVolSurface(
    0, ql.Sweden(), ql.ModifiedFollowing,
    expiries, strikes, black_vols, ql.Actual360()
)

# Strip optionlets and price
optionlet_surf = ql.OptionletStripper1(vol_surface, index)
ovs_handle = ql.OptionletVolatilityStructureHandle(
    ql.StrippedOptionletAdapter(optionlet_surf)
)
engine_vol = ql.BlackCapFloorEngine(discount_handle, ovs_handle)
cap.setPricingEngine(engine_vol)
cap_npv_vol = cap.NPV()
```

### Vanilla Swap Pricing

```python
# Create yield curve
yts = ql.RelinkableYieldTermStructureHandle()
instruments = [
    ('depo', '6M', 0.025),
    ('swap', '1Y', 0.031),
    ('swap', '2Y', 0.032),
    ('swap', '3Y', 0.035)
]

helpers = []
index = ql.Euribor6M(yts)
for instrument, tenor, rate in instruments:
    if instrument == 'depo':
        helpers.append(ql.DepositRateHelper(rate, index))
    elif instrument == 'swap':
        swap_index = ql.EuriborSwapIsdaFixA(ql.Period(tenor))
        helpers.append(ql.SwapRateHelper(rate, swap_index))

curve = ql.PiecewiseLogCubicDiscount(2, ql.TARGET(), helpers, ql.Actual365Fixed())
yts.linkTo(curve)

# Create swap
engine = ql.DiscountingSwapEngine(yts)
tenor = ql.Period('2y')
fixed_rate = 0.05
forward_start = ql.Period("2D")

swap = ql.MakeVanillaSwap(
    tenor, index, fixed_rate, forward_start,
    nominal=10e6, pricingEngine=engine
)

# Get results
fair_rate = swap.fairRate()
npv = swap.NPV()

# Analyze cash flows
fixed_leg_cf = pd.DataFrame([{
    'date': cf.date(),
    'amount': cf.amount()
} for cf in swap.leg(0)])

floating_leg_cf = pd.DataFrame([{
    'accrualStart': cf.accrualStartDate(),
    'accrualEnd': cf.accrualEndDate(),
    'rate': cf.rate(),
    'amount': cf.amount()
} for cf in map(ql.as_coupon, swap.leg(1))])
```

### Building a Yield Curve

```python
import matplotlib.pyplot as plt

# Create zero curve
dates = [ql.Date(15, 6, 2020), ql.Date(15, 6, 2021), ql.Date(15, 6, 2022)]
zeros = [0.01, 0.02, 0.03]
curve = ql.ZeroCurve(dates, zeros, ql.ActualActual(), ql.TARGET())

# Extract nodes for plotting
nodes = curve.nodes()
plot_dates = [dt.to_date() for dt, rate in nodes]
plot_rates = [rate for dt, rate in nodes]

plt.plot(plot_dates, plot_rates, marker='o')
plt.xlabel('Date')
plt.ylabel('Zero Rate')
plt.title('Zero Curve')
plt.show()
```

### Gearing in Swaps

```python
# Create basic setup
yts = ql.YieldTermStructureHandle(ql.FlatForward(2, ql.TARGET(), 0.05, ql.Actual360()))
engine = ql.DiscountingSwapEngine(yts)
index = ql.USDLibor(ql.Period('6M'), yts)

schedule = ql.MakeSchedule(ql.Date(15, 6, 2021), ql.Date(15, 6, 2023), ql.Period('6M'))
nominal = [10e6]

# Standard swap
fixed_leg = ql.FixedRateLeg(schedule, index.dayCounter(), nominal, [0.05])
floating_leg = ql.IborLeg(nominal, schedule, index)
swap = ql.Swap(fixed_leg, floating_leg)
swap.setPricingEngine(engine)
standard_npv = swap.legNPV(1)

# Swap with gearing
geared_floating_leg = ql.IborLeg(nominal, schedule, index, gearings=[0.7])
geared_swap = ql.Swap(fixed_leg, geared_floating_leg)
geared_swap.setPricingEngine(engine)
geared_npv = geared_swap.legNPV(1)

# Non-standard swap with gearing
swap_type = ql.VanillaSwap.Payer
num_dates = len(schedule) - 1
gearing = [0.7] * num_dates
spread = [0.0] * num_dates
fixed_rates = [0.05] * num_dates
nominals = nominal * num_dates

ns_swap = ql.NonstandardSwap(
    swap_type, nominals, nominals,
    schedule, fixed_rates, index.dayCounter(),
    schedule, index, gearing, spread, index.dayCounter()
)
ns_swap.setPricingEngine(engine)
ns_npv = ns_swap.legNPV(1)
```