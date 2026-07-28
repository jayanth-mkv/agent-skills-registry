# Implementation and measurement

Use this reference to convert findings into safe repository changes, acceptance tests, experiments, monitoring, and stakeholder handoffs.

## Contents

1. [Implementation contract](#implementation-contract)
2. [Trace the source of truth](#trace-the-source-of-truth)
3. [Change patterns](#change-patterns)
4. [Validation pyramid](#validation-pyramid)
5. [Experiments](#experiments)
6. [Monitoring](#monitoring)
7. [Tickets and handoff](#tickets-and-handoff)

## Implementation contract

Before editing, state:

```text
Finding IDs:
Affected cohort/templates:
Authorized environments:
Intended behavior:
Source-of-truth files/systems:
Dependencies and owners:
Change risk:
Rollback:
Acceptance tests:
Leading indicators:
Outcome window:
```

Diagnosis-only requests do not authorize changes. A request to “fix” or “implement” does authorize normal in-scope repository edits and verification, but not publishing, production changes, account actions, or URL submissions unless stated.

## Trace the source of truth

Search in this order:

1. route/controller and response middleware;
2. shared layout/head/SEO component;
3. CMS/content model and data source;
4. schema/feed generator;
5. sitemap/robots/redirect configuration;
6. build-time or edge/CDN transforms;
7. generated static output;
8. deployment configuration and tests.

Fix the generator or shared rule. Do not hand-edit emitted files unless they are the actual maintained source.

Map one representative URL from request to source data to generated HTML to deployed response. Preserve existing unrelated work and conventions.

## Change patterns

### Titles and descriptions

- Derive from page-specific data with an intentional fallback chain.
- Escape content and prevent duplicate brand suffixes.
- Keep titles accurate and distinct by purpose.
- Permit intentional description omission when the page cannot provide a useful unique summary.
- Test missing, unusually long, localized, and special-character inputs.

### Canonicals

- Generate absolute URLs from a trusted public base URL.
- Strip only parameters covered by the approved policy.
- Preserve meaningful variants.
- Avoid environment/staging hosts.
- Emit one raw-source canonical and keep client code from changing it.
- Test base, variant, parameter, pagination, locale, and error cases.

### Robots/index directives

- Express policy by environment and page lifecycle.
- Default safely for unknown content states.
- Test generic and crawler-specific directives.
- Keep robots.txt and `noindex` roles distinct.
- Add a production guard that detects accidental sitewide blocking when appropriate.

### Redirects

- Use a version-controlled map or deterministic rule.
- Detect chains, loops, duplicate sources, wildcard collisions, external/open redirects, and invalid destinations.
- Preserve query strings only when intentionally required.
- Test old high-value URLs, malformed input, deleted content, and destination status/canonical.

### Sitemaps

- Generate from the authoritative inventory.
- Include only preferred, eligible URLs.
- Partition by meaningful cohort and protocol limits.
- Set `lastmod` from substantive content changes.
- Exclude staging, search results, invalid facets, redirects, errors, and `noindex` URLs.
- Test XML syntax, escaping, host, count, and sample URL state.

### Hreflang

- Generate complete clusters from a locale mapping.
- Validate supported codes, absolute URLs, self-reference, reciprocity, canonical agreement, and reachable alternates.
- Choose one maintained implementation method unless the architecture requires another.
- Test missing translations and market-specific fallback behavior.

### Structured data

- Generate from the same facts shown on the page.
- Omit properties with no truthful value rather than inventing fallbacks.
- Use stable identifiers and valid JSON serialization.
- Keep type selection page-specific.
- Test syntax, required properties, visible-data agreement, error pages, localization, price/inventory/date changes, and currently supported feature rules.

### Internal links

- Add links where they help the user continue a task.
- Use canonical destinations and meaningful anchors.
- Avoid creating link loops, duplicate UI, or enormous sitewide blocks.
- Test crawlable `href`, access, localization, and destination status.

### Content changes

- Preserve verified facts, tone, legal/compliance requirements, and existing useful sections.
- Mark claims requiring SME or legal approval.
- Add genuinely new evidence; do not paraphrase competitors.
- Update dates only for substantive changes.
- Recheck links, media rights, structured data, CTA, and localization.

### Performance

- Identify the metric and root cause before changing code.
- Set a budget by representative template/device.
- Optimize discovery, payload, execution, rendering, or layout at the source.
- Protect accessibility and product behavior.
- Use repeatable lab conditions and monitor field data after release.

## Validation pyramid

### 1. Static tests

Check:

- configuration syntax;
- generated metadata/schema fixtures;
- URL normalization and redirect rules;
- sitemap/hreflang output;
- forbidden staging values;
- unit tests for edge cases;
- lint/type/build.

### 2. Local integration

Render representative pages and inspect:

- response status/headers;
- raw HTML;
- canonical/directives/alternates;
- primary content and links;
- JSON-LD parsing;
- mobile viewport and accessibility;
- error/empty/loading states.

### 3. Preview/staging

Run the same checks through the deployed stack, including CDN/edge/cache. Keep staging access controlled and verify controls cannot be promoted accidentally.

### 4. Production smoke test

After authorized deployment, test a small critical set immediately:

- homepage;
- priority template examples;
- old redirect URLs;
- locale/variant examples;
- sitemap and robots;
- conversion path;
- analytics events.

### 5. Search processing

Monitor recrawl, indexed version, selected canonical, enhancement reports, query/page performance, and outcomes. Search-engine processing lag is not a failed deployment test.

### Before/after crawl

Use identical crawler version and options. Compare:

- requested/fetched/blocked/failed counts;
- status and redirect changes;
- indexability/canonical changes;
- sitemap and crawl inventory;
- broken links;
- metadata/schema/parity changes;
- issue cohorts;
- unexpected regressions.

The bundled comparison script compares deterministic snapshots but cannot judge whether every change was intended.

## Experiments

### Choose an experiment when

- causality is uncertain;
- change can be isolated to a coherent cohort;
- enough impressions/outcomes exist;
- risk is acceptable;
- a stable control or time-series method is possible.

### Design

```text
Decision:
Hypothesis:
Eligible population:
Unit of assignment:
Control:
Treatment:
Primary metric:
Guardrails:
Minimum practical effect:
Analysis window:
Seasonality/contamination risks:
Stop and rollback:
Owner:
```

Prefer randomized template/page cohorts where valid. If randomization is impossible, use phased rollout, matched cohorts, interrupted time series, or repeated observations and lower the causal confidence.

Do not evaluate a title test solely by average position. Include clicks and qualified outcomes; ensure treatment does not change intent or page eligibility.

### Decision

Predefine:

- ship;
- iterate;
- stop;
- roll back;
- extend because data is insufficient.

Do not keep a losing or harmful variant because it “might need more time” after the stop rule is met.

## Monitoring

### Release monitoring

For 24–72 hours depending on risk:

- availability/status/error rate;
- redirect behavior;
- crawl access/directives;
- rendered output;
- analytics/conversions;
- performance/error monitoring;
- crawler logs for critical cohorts.

### Weekly

- GSC clicks/impressions/CTR by key segment;
- unexpected queries or hacked-content signals;
- new crawl/index/template errors;
- sitemap status;
- priority landing-page conversions;
- critical Business Profile/Merchant Center issues where applicable.

### Monthly/quarterly

- portfolio winners/losers and decays;
- index inventory by intended state;
- content accuracy/review queue;
- internal-link and orphan-candidate cohorts;
- Core Web Vitals field cohorts;
- AI citation/answer prompt panel;
- link/mention acquisition and losses;
- roadmap outcomes and experiment decisions.

### Alerts

Every alert needs:

- metric and exact scope;
- threshold and comparison baseline;
- minimum volume;
- delay/debounce;
- owner and response time;
- diagnostic runbook;
- false-positive notes;
- escalation and rollback authority.

Avoid property-wide percentage alerts with no minimum volume.

## Tickets and handoff

### Implementation ticket

```text
Title:
Finding/evidence:
Affected URL pattern/template:
User and business impact:
Current behavior:
Expected behavior:
Implementation notes:
Out of scope:
Dependencies:
Risk and rollback:
Acceptance tests:
Analytics/monitoring:
Owner:
Decision date:
```

### Content ticket

```text
Audience/job:
Existing page and role:
Demand/SERP evidence:
Unique angle and expert inputs:
Claims/sources to verify:
Sections to add/change/remove:
Internal links:
Media/schema/accessibility:
CTA and next experience:
Acceptance criteria:
Performance/conversion measure:
Reviewer and review date:
```

### Stakeholder report

Lead with:

1. what is happening;
2. why it matters;
3. what evidence supports it;
4. what should happen next;
5. who owns it and when;
6. how success/failure will be known;
7. uncertainty and risk.

Keep the reproducible technical appendix separate from the executive summary, but ensure every summary claim links to its evidence.
