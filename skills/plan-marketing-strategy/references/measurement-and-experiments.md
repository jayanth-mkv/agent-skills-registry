# Measurement and Experiments

Use this reference to define success, repair analytics, interpret results, and design learning that can support a decision.

## Contents

1. Measurement contract
2. Metric tree
3. Event and rate definitions
4. Diagnostic analysis
5. Attribution and incrementality
6. Forecasts and economics
7. Experiment design
8. Readouts and decisions

## 1. Measurement contract

Before execution, document:

- decision the measurement should inform;
- population and eligibility;
- event definition and source of truth;
- numerator, denominator, exclusions, and deduplication;
- time zone, observation window, attribution window, and cohort maturity;
- baseline period and known changes;
- primary outcome, leading indicators, and guardrails;
- segments required for diagnosis;
- owner, QA method, reporting cadence, and decision date.

If instrumentation is broken, make repair part of the plan. Do not recommend scale from unreliable data.

## 2. Metric tree

Connect activity to value:

```text
Business outcome
├── Customer outcome/behavior
│   ├── Journey transition
│   │   ├── Leading signal
│   │   └── Controllable input
└── Guardrails: quality, trust, cost, capacity, retention, accessibility
```

Examples:

- Revenue is influenced by qualified opportunities, win rate, contract value, and sales-cycle time—not impressions alone.
- Subscription growth is influenced by qualified starts, activation, paid conversion, retention, and expansion—not signup volume alone.
- Repeat purchase is influenced by first-order quality, product satisfaction, replenishment timing, and offer relevance—not email opens alone.

Choose one primary outcome for each initiative. Supporting metrics explain why it moved.

## 3. Event and rate definitions

Name events as observed behaviors, not vague states. Define properties and identity rules. Example:

```text
Event: activated_workspace
Occurs when: a new workspace completes [verified value action]
Population: workspaces created in the period, excluding internal/test accounts
Window: within 14 days of creation
Source: product event table
Owner: analytics
```

For every rate, state numerator and denominator:

```text
14-day activation rate =
eligible new workspaces activated within 14 days
/ eligible new workspaces with a mature 14-day window
```

Avoid mixing users, accounts, sessions, leads, orders, and contacts. Explain identity stitching and duplicate handling when relevant.

## 4. Diagnostic analysis

Analyze counts before rates. Compare:

- time periods with comparable seasonality and maturity;
- cohorts by acquisition source, audience, offer, device, geography, or plan;
- new versus returning behavior;
- volume, quality, conversion, value, and retention together;
- median and distribution when averages hide skew;
- operational capacity and follow-up time.

Trace the largest decision-relevant loss. List rival causes and the next analysis or test that distinguishes them. Correlation, assisted conversion, and last-touch assignment do not establish causation.

## 5. Attribution and incrementality

Use attribution to describe paths; use incrementality to estimate what marketing caused.

Clarify:

- question: reporting, optimization, budgeting, or causal impact;
- model and limitations;
- view-through and click-through windows;
- cross-device, offline, dark-social, direct, and consent gaps;
- brand and demand-creation effects;
- channel self-reporting bias;
- overlap among campaigns.

Prefer experiments, geo tests, holdouts, matched comparisons, or triangulation when budget decisions require causal confidence. Do not force all value into one touchpoint.

For a sufficiently large cross-channel portfolio, consider marketing-mix modeling when there is enough time variation, geographic or market detail, spend, outcome history, and specialist capability. Define treatment, outcome, controls, lag, saturation, uncertainty, and confounding. Calibrate or challenge model results with experiments when possible. Optimize for decision-useful causal estimates, not prediction fit alone.

## 6. Forecasts and economics

Forecast with explicit drivers:

```text
reachable qualified volume
× transition rates
× value per successful outcome
- full acquisition and delivery cost
```

Use low/base/high scenarios. Show which inputs are observed versus assumed and run sensitivity on the few variables that dominate the result.

For economics, consider contribution margin, retention, repeat rate, refunds, discounts, sales cost, creative/agency/tool cost, support/fulfillment, and cash timing. Do not use a generic LTV:CAC threshold as a universal rule.

Compare average and marginal return. A channel with strong historical average return may have little profitable room to scale, while a smaller channel may have a better next-unit opportunity.

## 7. Experiment design

Write an experiment card:

```markdown
Decision:
Observation and evidence:
Hypothesis:
Population and eligibility:
Control/comparison:
Change:
Primary outcome:
Guardrails:
Minimum meaningful effect or practical threshold:
Assignment and contamination risks:
Run length and maturity:
Data-quality checks:
Decision rules:
Owner and launch/readout dates:
```

Choose the method based on the decision:

- randomized A/B test for isolatable changes and adequate volume;
- switchback or time-based design for shared environments, with seasonality caution;
- geo or matched-market test for regional media;
- holdout for lifecycle or incrementality;
- qualitative prototype/usability test for comprehension and friction;
- concierge, smoke, or demand test for early assumptions, with truthful representation;
- sequential operational test when randomization is impossible, with weaker causal claims.

### Feasibility and sample planning

Before launching, define:

- randomization and analysis unit;
- baseline rate or variance from a comparable mature population;
- minimum effect that would change the decision;
- false-positive threshold, desired power, and one- or two-sided question;
- number of variants and allocation;
- eligible volume, participation, exclusions, attrition, and conversion maturity;
- clustering, repeated exposure, interference, and contamination;
- planned interim looks and multiple-comparison handling.

Use a verified statistical library or calculator appropriate to the outcome and design. Record its method, inputs, and rounding. For a simple equal-allocation two-proportion test, supply baseline proportion, minimum absolute change, significance threshold, desired power, and test direction; do not confuse a relative uplift with percentage points.

Estimate calendar time:

```text
required analyzed units across arms
/ expected eligible analyzed units per day
+ outcome-maturity and operational buffer
```

Extend for weekly cycles, seasonality, assignment ramp, delayed outcomes, and exclusions. Do not extend a test indefinitely until it wins.

If the test is infeasible, reduce variants, test a larger decision-relevant change, improve measurement, pool only genuinely comparable units, run longer, or choose a qualitative, switchback, geo, matched, or staged design. Do not treat an underpowered null result as proof of no effect.

Do not stop merely when a dashboard turns green. Account for planned horizon, sample ratio mismatch, repeated peeking, novelty, interference, and guardrail harm. Statistical significance does not guarantee meaningful business value.

## 8. Readouts and decisions

Report:

- decision and recommendation;
- what ran versus what was planned;
- data-quality status;
- population, dates, sample/counts, and definitions;
- primary and guardrail results with uncertainty;
- segment differences identified before or after the test;
- plausible mechanisms and alternative explanations;
- limitations;
- continue, change, stop, scale, or rerun decision;
- next learning and owner.

Preserve negative and inconclusive results. A failed hypothesis that changes a decision is useful; a vanity win that cannot change action is not.
