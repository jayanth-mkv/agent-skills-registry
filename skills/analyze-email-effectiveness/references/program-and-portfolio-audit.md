# Email program, portfolio, and competitive audit

Use this reference when the scope is an entire email program, several campaigns/brands/regions, overlapping journeys, governance, migration readiness, or comparison with competitors.

## Define the portfolio boundary

Record:

- brands, legal entities, products, regions and recipient types;
- service, security, product, marketing, sales and editorial streams;
- sending platforms, business owners and technical owners;
- Header From, DKIM, return-path, tracking/link domains and IP pools;
- acquisition sources, consent systems and suppression authorities;
- lifecycle stages, active journeys and manual/broadcast campaigns;
- reporting systems, metric definitions and retention windows;
- audit window and known launches/incidents.

Do not treat the ESP account as the program boundary. One organization can send through multiple vendors; one vendor account can serve unrelated programs.

## Build the inventory

Use one row per materially distinct message/trigger:

| Field | Capture |
| --- | --- |
| ID/owner | Stable name, brand, team and accountable owner |
| Family/job | Recipient-visible type and one state change |
| Eligibility | Audience, source, consent/basis and exclusions |
| Trigger/cadence | Event, delay, time zone, frequency cap |
| Sequence | Prior/next step, branches, exit and handoff |
| Identity/stream | From, DKIM, return-path, IP/pool, tracking domain |
| Destination | Product/page/action and owner |
| Suppression | Global/local rules and propagation source |
| Measurement | Primary metric, guardrails, denominator/window |
| Artifact | Source/rendered/received version and last review |
| Risk | Accuracy, legal, security, accessibility, reputation |

Sample the final production MIME and destination, not only a design-system mockup.

## Coverage map

Map every meaningful recipient state:

```text
entry/source
-> acquisition/awareness
-> consideration
-> activation
-> conversion
-> adoption/retention
-> expansion/advocacy
-> reactivation or exit
```

For each state identify:

- required service/security communication;
- decision or blocker;
- current message and channel;
- evidence that the message is needed;
- missing, duplicated or contradictory messages;
- product/sales/support handoff;
- success and harm metrics.

A gap is not automatically a reason to add email. Sometimes the correct fix is product UX, support, documentation or suppression.

## Collision analysis

Create a recipient-level timeline across all programs. Check:

- marketing and transactional stream overlap;
- multiple teams targeting the same state;
- campaigns ignoring journey conversion/activation;
- sales automation continuing after a reply;
- renewal/dunning conflicting with support disputes;
- re-engagement colliding with active product use;
- regional time-zone and quiet-hour conflicts;
- global unsubscribe/complaint state losing to local lists;
- frequency caps implemented separately by vendor or brand;
- outdated queued mail after price, inventory, policy or product changes.

Evaluate total contact pressure, not each campaign in isolation.

## Identity and stream governance

Inventory by message family:

| Stream | Header From | DKIM d=/selectors | Return-path | IP/pool | Link domains | Receiver dashboards |
| --- | --- | --- | --- | --- | --- | --- |

Review:

- whether recipient expectations and operational risk justify stream separation;
- stable recognizable identity instead of cosmetic rotation;
- shared/dedicated pool ownership and escalation;
- active/retired selector and vendor offboarding records;
- DMARC source inventory and aggregate-report ownership;
- access to Gmail, Yahoo and Microsoft receiver evidence;
- DNS/key change approval, rollback and verification;
- unauthorized or forgotten senders.

Separation should protect service reliability and clarify operations, not evade reputation or opt-outs.

## Data and suppression lineage

Trace:

```text
collection/source
-> identity resolution
-> consent/preferences
-> eligibility/segmentation
-> ESP sync
-> send/receiver events
-> unsubscribe/complaint/bounce
-> global suppression
-> downstream vendors and queued jobs
```

For every interface document owner, latency, retries, deduplication, failure alert, replay/reconciliation and source of truth. Audit a sample from withdrawal through every sender. Do not infer propagation from a successful preference-center screen.

## Program measurement

Build a KPI tree:

```text
business/recipient outcome
<- lifecycle value event
<- message/sequence incremental effect
<- reliable engagement/destination completion
<- accepted delivery and receiver evidence
<- eligible wanted audience
```

Compare programs only with aligned definitions and maturity windows. Report:

- volume and outcome by family/provider/source/stream;
- complaint, unsubscribe, bounce and suppression trends;
- contribution and cannibalization;
- coverage/redundancy;
- experiment velocity and decision quality;
- operational incidents and recovery time;
- accessibility/content review coverage.

Do not reward volume or open rate without value and harm context.

## Competitive and category analysis

Use lawfully obtained public/subscribed artifacts. For each comparable message, capture:

- audience/relationship and lifecycle assumption;
- positioning, promise, category frame and differentiation;
- proof, offer, terms and objection handling;
- From/subject/preview strategy;
- structure, CTA and destination;
- visual/voice/accessibility patterns;
- cadence visible to the subscribed observer.

Separate observation from inference. A competitor email cannot reveal its performance, audience quality, consent records, deliverability or business strategy. Do not copy proprietary wording/design; synthesize category conventions, gaps and opportunities in the user’s own strategy.

## Migration or vendor-change readiness

Before a platform/domain/IP migration, audit:

- full sender and integration inventory;
- domain ownership and DNS TTL/change plan;
- active DKIM selectors and safe overlap/rotation;
- return-path, tracking and TLS configuration;
- suppression, consent, preference and event-history transfer;
- message/automation parity and paused queues;
- webhook/event semantic differences;
- receiver-dashboard and feedback-loop continuity;
- cohort-based controlled cutover, rollback and monitoring;
- old-vendor shutdown and key/reputation cleanup.

Do not recommend a migration as a reputation reset. Preserve stable wanted identity where appropriate.

## Prioritization

Rank with:

```text
recipient/business impact
x evidence confidence
x affected volume/risk
x reversibility
÷ implementation and coordination cost
```

Contain legal, consent, security, service-delivery and high-complaint risks before copy optimization. Prefer deletion/consolidation when messages have no distinct job.

## Output

```markdown
## Portfolio verdict
[Coverage, largest systemic risk, largest opportunity, confidence.]

## Inventory summary
| Family/stage | Active messages | Volume | Outcome | Guardrail | Owner |

## Coverage and collision map
- Missing state:
- Duplicate/contradictory state:
- Cross-channel/frequency conflict:

## Identity and evidence map
| Stream | Domains/IP | Provider evidence | Risk/unknown |

## Priority roadmap
| Priority | Remove/fix/test | Owner | Dependency | Verification |

## Governance gaps
- [source of truth, review cadence, incident/suppression ownership]
```
