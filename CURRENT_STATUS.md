### Analytics Validation Refactor

**Status:** Completed and merged into `develop`  
**Branch:** `refactor/analytics-validation`

Consolidated repeated analytics input-validation logic into a shared private
validation module while preserving all existing analytics behavior.

#### Shared validation helpers added

- Datetime-index validation
- Positive-integer validation
- Finite real-value validation and normalization
- Portfolio weight-mapping validation

#### Modules migrated

- `returns.py`
- `volatility.py`
- `drawdown.py`
- `sharpe.py`
- `correlation.py`
- `concentration.py`
- `diversification.py`
- `risk_driver.py`

#### Validation boundaries preserved

Specialized validation remains local where behavior intentionally differs,
including:

- Sharpe zero-volatility handling
- Return lower-bound rules
- Portfolio-weight alignment
- Correlation-matrix NaN behavior
- Diversification coverage rules
- Risk-classification thresholds
- Drawdown calculation conventions
- Analytics-engine consistency checks

#### Compatibility preserved

The refactor did not change:

- Public analytics APIs
- Public function signatures
- Analytics formulas
- Result dataclasses or returned structures
- Exception behavior
- Validation order
- Input non-mutation behavior
- Correlation NaN behavior
- Risk-driver ranking behavior

#### Final verification

- Shared validation tests: 116 passed
- Analytics tests: 820 passed
- Full backend tests: 821 passed
- Failed tests: 0
- Manual engine check: passed
- Dependency check: passed
- Public analytics import check: passed
- Python compilation check: passed
- Git whitespace check: passed

## Known Issues and Technical Debt

### Starlette/httpx warning

The backend test suite still produces one existing non-blocking
Starlette/httpx deprecation warning.

This warning is unrelated to the analytics calculations and does not
cause test failures.

## Current Backend Priorities

1. Market-data pipeline
2. Database foundation
3. Schemas and API contracts
4. Analysis service
5. API integration
6. Historical simulator
7. AI agent later
