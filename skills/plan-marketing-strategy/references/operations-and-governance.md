# Marketing Operations and Governance

Use this reference to make the strategy executable by a real team without turning the skill into a mandatory software system.

## Contents

1. Operating model
2. Ownership and decisions
3. Work intake and planning
4. Production workflow
5. Tool and automation choices
6. Data and governance
7. Localization, accessibility, and risk
8. Learning and continuity

## 1. Operating model

Design the operating model around the chosen strategy:

- outcomes and planning horizon;
- primary growth engine and supporting capabilities;
- recurring work versus campaigns and experiments;
- internal strengths and constrained resources;
- work that requires product, engineering, sales, support, finance, legal, or leadership;
- work to keep in-house versus contract;
- review and decision cadence.

Do not copy an enterprise org chart into an early-stage team. Combine roles while preserving clear accountability.

## 2. Ownership and decisions

For every initiative name:

- **Accountable:** one person who owns the outcome and decision.
- **Responsible:** people producing the work.
- **Consulted:** required specialist or stakeholder input.
- **Informed:** people affected by the result.

Also define:

- decision that must be made;
- evidence and threshold required;
- approver where authority matters;
- deadline and cost of delay;
- escalation path;
- what can proceed autonomously.

Avoid assigning work to departments without a named owner.

## 3. Work intake and planning

Use one intake record:

```markdown
## Request and desired decision
## Business/customer outcome
## Audience and journey stage
## Evidence and urgency
## Deliverable and definition of done
## Owner, reviewers, and dependencies
## Effort/budget range
## Metric and decision date
## Risk, consent, legal, or brand requirements
```

Triaging rules:

1. Reject or reshape work unrelated to the current constraint or committed outcome.
2. Repair broken customer experience, measurement, or trust before adding volume.
3. Protect mandatory service, legal, security, and accessibility work.
4. Limit work in progress to actual capacity.
5. Reserve bounded capacity for experiments and urgent learning.
6. Record what is displaced when new work enters.

Use a roadmap for choices and a production board for tasks. Do not confuse activity completion with outcome progress.

## 4. Production workflow

Adapt this reusable path:

```text
intake -> evidence -> brief -> produce -> specialist review
-> approve -> QA -> release -> monitor -> readout -> reuse/archive
```

Define:

- entry and exit criteria;
- templates or source artifacts;
- version and source of truth;
- reviewer roles and response times;
- factual, brand, accessibility, privacy, legal, and technical gates;
- release authority and rollback;
- post-release owner;
- retention or deletion of data and assets.

Use checklists for fragile repeatable work, not for strategic judgment.

## 5. Tool and automation choices

Select tools only after defining the workflow and data:

- problem and user;
- required capability;
- source and destination data;
- identity and permissions;
- volume, latency, reliability, and audit needs;
- vendor lock-in and export;
- privacy, residency, security, and retention;
- accessibility and team usability;
- total cost, maintenance, and failure handling.

Prefer the simplest existing tool that meets the decision need. Do not create a mandatory CRM, CDP, automation platform, project system, or context file for a user who does not need one.

Before automating, stabilize the manual decision and edge cases. Add:

- validation before state changes;
- idempotency or deduplication;
- frequency and budget caps;
- human approval for high-impact actions;
- logging and audit trail;
- error queue and owner;
- pause, rollback, and recovery;
- consent and suppression enforcement.

## 6. Data and governance

Document:

- system of record for contacts, accounts, campaigns, consent, orders, revenue, and product events;
- event and field definitions;
- identity and deduplication;
- access roles;
- collection purpose and minimization;
- retention and deletion;
- vendor sharing and exports;
- QA owner and cadence;
- incident response.

Maintain a claim register for important public statements:

| Claim | Evidence/source | Scope/qualification | Approved use | Owner | Review date |
| --- | --- | --- | --- | --- | --- |

Maintain a decision log:

| Decision | Evidence | Assumptions | Owner/date | Review trigger |
| --- | --- | --- | --- | --- |

Do not put secrets, private customer data, or sensitive personal information into general marketing briefs or agent context.

## 7. Localization, accessibility, and risk

Plan localization as market adaptation:

- customer situation, cultural meaning, language, and tone;
- offer, price, currency, tax, fulfillment, and support;
- channels and local discovery;
- claims, consent, privacy, promotions, and sector rules;
- images, examples, names, dates, units, and reading direction;
- local reviewers and escalation.

Use a locale acceptance record:

| Locale/surface | Terminology and meaning reviewer | Claim/policy reviewer | Functional and layout QA | Accessibility and assistive-tech QA | Approved owner/date |
| --- | --- | --- | --- | --- | --- |

Define reading level, tone, terminology, dates, units, currency, fallback language, text expansion, direction, fonts, forms, error states, media alternatives, and support routing before approval. Machine translation or bilingual review alone does not establish market, functional, or accessibility acceptance.

Build accessibility into briefs and QA: semantic structure, keyboard operation, focus, contrast, captions, transcripts, alternative text, readable language, form labels, error recovery, and reduced-motion considerations where relevant.

Prepare risk responses for:

- incorrect or unsubstantiated claim;
- privacy or consent failure;
- discriminatory or culturally harmful creative;
- broken offer, price, checkout, or fulfillment;
- creator/partner misconduct;
- platform enforcement;
- negative customer response;
- security or data incident.

Name monitoring, pause authority, response owner, and correction path before high-reach work.

## 8. Learning and continuity

At each review capture:

- decision and hypothesis;
- what shipped;
- evidence and metric definitions;
- outcome and guardrails;
- qualitative explanation;
- what changed;
- reusable asset or process;
- follow-up owner and review trigger.

Archive stale assets and record expiration for prices, claims, screenshots, benchmarks, platform specs, and legal guidance.

Use a compact quarterly reset:

1. Reconfirm business outcome and customer value.
2. Review journey and segment performance.
3. Identify the new binding constraint.
4. Stop work that no longer serves it.
5. Choose the primary engine, support, and experiments.
6. Reassign capacity and decision ownership.

The goal is organizational learning and better decisions, not a larger marketing bureaucracy.
