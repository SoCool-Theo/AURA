# Aura Historical Scenario Catalogue

## Purpose

Aura's predefined Historical Scenario catalogue supports educational,
deterministic simulations of how a saved portfolio would have behaved during
selected past market conditions. The catalogue is code-owned and uses fixed
historical event periods. Its results are not forecasts, predictions, buy/sell
recommendations, or financial advice.

This reference is intended for developers, reviewers, educators, and future
frontend or AI integration. Aura's deterministic backend remains the source of
all simulation calculations.

## Important Simulation Semantics

- Each scenario stores predefined requested dates representing its historical
  event boundaries.
- Requested dates remain separate from effective dates. A requested boundary
  may be a weekend, holiday, or date without an observation; that does not make
  the requested boundary incorrect.
- Effective dates are the first and last exact common historical observations
  actually used after all saved holdings are aligned.
- Alignment uses only dates shared by every saved holding. Zero-weight
  holdings remain part of this requirement.
- A simulation requires at least three aligned price observations.
- Missing symbols or insufficient aligned history retain Aura's established
  `422` simulation failure behavior.
- Aura does not fabricate or synthesize missing historical data.

## Scenario Summary

| Scenario ID | Display name | Requested start | Requested end | Category |
|---|---|---|---|---|
| `covid-19-shock-2020` | COVID-19 Market Shock | `2020-02-01` | `2020-04-30` | Major market shock |
| `inflation-rate-shock-2022` | 2022 Inflation and Rate Shock | `2022-01-01` | `2022-12-31` | Macroeconomic/rate shock |
| `dot-com-bust-2000-2002` | Dot-Com Bust | `2000-03-10` | `2002-10-09` | Major market crash |
| `global-financial-crisis-2007-2009` | Global Financial Crisis | `2007-10-09` | `2009-03-09` | Financial-system crisis |
| `q4-market-selloff-2018` | Q4 2018 Market Selloff | `2018-10-01` | `2018-12-31` | High-volatility period |

## Individual Scenarios

### COVID-19 Market Shock

- **ID:** `covid-19-shock-2020`
- **Display name:** COVID-19 Market Shock
- **Production description:** A sharp market shock and early recovery period
  during the COVID-19 disruption.
- **Requested period:** `2020-02-01` through `2020-04-30`
- **Category:** Major market shock
- **Historical context:** This period covers the abrupt early-2020 market
  disruption and the beginning of the subsequent recovery.
- **Educational rationale:** Demonstrates how a saved allocation behaves
  through a sudden drawdown and early rebound.
- **Coverage limitation:** The verified backfill observed all 17 current Aura
  symbols beginning before this period, but exact stored coverage and
  common-date alignment are still required. That observation is not a
  permanent provider guarantee.

### 2022 Inflation and Rate Shock

- **ID:** `inflation-rate-shock-2022`
- **Display name:** 2022 Inflation and Rate Shock
- **Production description:** An extended cross-asset stress period associated
  with inflation and rising interest rates.
- **Requested period:** `2022-01-01` through `2022-12-31`
- **Category:** Macroeconomic/rate shock
- **Historical context:** This period represents sustained inflation and
  rising-rate pressure across multiple asset classes during 2022.
- **Educational rationale:** Demonstrates portfolio behavior when a prolonged
  macroeconomic shock can pressure traditionally different asset classes at
  the same time.
- **Coverage limitation:** The verified backfill observed all 17 current Aura
  symbols beginning before this period, but missing stored observations or an
  insufficient exact common-date intersection must still retain the existing
  failure behavior. Provider coverage is not guaranteed permanently.

### Dot-Com Bust

- **ID:** `dot-com-bust-2000-2002`
- **Display name:** Dot-Com Bust
- **Production description:** A prolonged technology-led market decline
  following the dot-com bubble.
- **Requested period:** `2000-03-10` through `2002-10-09`
- **Category:** Major market crash
- **Historical context:** This period represents an extended technology-led
  market decline following the dot-com bubble.
- **Educational rationale:** Demonstrates a prolonged technology-led bubble
  unwind and the portfolio effects of a deep, extended equity drawdown.
- **Coverage limitation:** Only seven of Aura's 17 symbols in the verified
  historical backfill reached `2000-01-03`. Portfolios containing
  later-starting assets may therefore retain the existing
  missing/insufficient-data `422`; Aura does not drop those assets or shorten
  the scenario automatically.

### Global Financial Crisis

- **ID:** `global-financial-crisis-2007-2009`
- **Display name:** Global Financial Crisis
- **Production description:** A severe global market downturn during the
  2007–2009 financial crisis.
- **Requested period:** `2007-10-09` through `2009-03-09`
- **Category:** Financial-system crisis
- **Historical context:** This period represents broad market stress during a
  systemic global financial crisis.
- **Educational rationale:** Demonstrates severe market stress and portfolio
  behavior during a systemic financial crisis.
- **Coverage limitation:** Several later-created Aura assets do not cover this
  period. Existing missing/insufficient-data behavior remains intentional;
  Aura does not fabricate earlier prices, remove holdings, or change the saved
  allocation.

### Q4 2018 Market Selloff

- **ID:** `q4-market-selloff-2018`
- **Display name:** Q4 2018 Market Selloff
- **Production description:** A sharp late-2018 market selloff marked by
  elevated volatility.
- **Requested period:** `2018-10-01` through `2018-12-31`
- **Category:** High-volatility period
- **Historical context:** This period represents a concentrated late-2018
  risk-off episode with elevated market volatility.
- **Educational rationale:** Provides a shorter risk-off and volatility episode
  distinct from the longer 2022 inflation/rate shock.
- **Coverage limitation:** The controlled historical backfill observed all 17
  current Aura symbols beginning by `2017-11-09`, giving this scenario
  materially broader observed coverage. This is verification evidence, not a
  permanent external-provider guarantee.

## Coverage and Interpretation Limits

Historical availability legitimately differs by symbol. An older scenario may
therefore be valid educationally even when one or more later-created assets in
a saved portfolio lack data for that period. Aura preserves the portfolio and
requested event boundaries and applies its existing missing/insufficient-data
failure behavior.

Aura does not resolve missing older coverage through:

- forward filling;
- backward filling;
- interpolation;
- fabricated prices;
- synthesized pre-history;
- silently dropped holdings;
- allocation changes; or
- automatic scenario shortening.

Observed backfill coverage describes a controlled verification run. It is not
a promise of permanent external-provider availability and does not establish
an asset's inception date. Simulation results describe historical behavior for
the saved allocation and available exact common observations; they do not
predict future performance or support investment recommendations.

## Metadata Boundary

Category, educational rationale, extended historical context, and coverage
notes in this reference are documentation-only metadata. They are not fields
in the production scenario definition model, Pydantic schemas, public APIs, or
simulation-history result structures.

The production catalogue remains limited to each scenario's ID, display name,
description, requested start date, and requested end date. This documentation
does not change production compatibility or simulation behavior.
