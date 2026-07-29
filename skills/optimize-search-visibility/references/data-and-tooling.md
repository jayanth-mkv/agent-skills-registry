# SEO data and tooling operations

Use this reference to choose evidence sources, operate connected tools safely, control query and crawl cost, join data, and make recurring analysis reproducible. A tool is useful only when its data can answer the decision with known coverage and limitations.

## Contents

1. [Start with a data contract](#start-with-a-data-contract)
2. [Route evidence to the right source](#route-evidence-to-the-right-source)
3. [Discover and operate connected tools](#discover-and-operate-connected-tools)
4. [Control access, mutations, and cost](#control-access-mutations-and-cost)
5. [Acquire data reproducibly](#acquire-data-reproducibly)
6. [Operate large performance datasets](#operate-large-performance-datasets)
7. [Normalize and join datasets](#normalize-and-join-datasets)
8. [Evaluate third-party estimates](#evaluate-third-party-estimates)
9. [Build durable reporting](#build-durable-reporting)
10. [Acceptance checklist](#acceptance-checklist)

## Start with a data contract

Before opening a dashboard or calling an API, write:

```text
Decision:
Population or URL cohort:
Metrics and dimensions:
Comparison window and timezone:
Required freshness:
Minimum useful coverage:
Segmentation:
Known exclusions:
Read or mutation authority:
Cost/time budget:
Output and owner:
```

Then define each field. Record whether a metric is a count, sum, ratio, percentile, estimate, sampled value, or model output. State its grain, such as one row per date/query/page/device. This prevents invalid joins and averages.

Do not collect every available field. Acquire the smallest dataset that can confirm or reject the working hypotheses.

## Route evidence to the right source

| Question | Preferred evidence | Useful corroboration | Does not prove |
| --- | --- | --- | --- |
| Can a URL be fetched now? | direct HTTP and rendered checks | crawler, CDN logs | index inclusion |
| Did a search crawler request it? | verified server/CDN logs | crawl statistics | indexing or ranking |
| Is it in a search index? | indexed-version inspection and coverage reports | search result observation | future visibility |
| What queries produced appearances? | first-party search performance data | controlled rank observations | total market demand |
| What happened after the click? | validated analytics and conversion systems | CRM or revenue data | search impressions |
| Is the page fast for users? | field performance data or owned RUM | repeated lab diagnostics | every user's experience |
| Are products eligible and accurate? | page, feed, merchant diagnostics, inventory, checkout | structured-data tests | feature display |
| Is local information accurate? | owned profile and location systems | landing pages and citations | local ranking |
| Are links present? | direct referring-page verification | backlink indexes and logs | endorsement quality |
| Is an answer engine citing the site? | reproducible platform observations | referrals and verified crawler logs | stable future inclusion |

Use implementation evidence—templates, headers, routes, data models, release history—when the question is why an observed state exists or how to fix it safely.

## Discover and operate connected tools

Never assume an integration exposes a particular command.

1. Inventory the capabilities available in the current environment.
2. Inspect each relevant tool's schema, required arguments, default scope, pagination, quotas, and mutation behavior.
3. Select the exact property, account, view, profile, market, or data source.
4. Start with a narrow read-only request and inspect its metadata.
5. Expand with explicit pagination and bounded dates.
6. Cache or store the extracted result so repeated analysis uses the same snapshot.
7. Record tool, operation, parameters excluding secrets, execution time, row count, and warnings.
8. Reconcile a sample against the native interface or another first-party source when the decision is consequential.

Treat capability or authentication errors as evidence gaps. Do not improvise credentials, downgrade security, or silently substitute a different property.

## Control access, mutations, and cost

### Permission boundary

Classify every action:

| Class | Examples | Default |
| --- | --- | --- |
| Read | query performance, inspect a URL, list sitemaps, fetch a public page | allowed when in scope |
| Local transform | aggregate an export, crawl an authorized public site, create a report | allowed with bounded resources |
| Reversible external change | submit a sitemap, update a listing field, request a recrawl | explicit authorization |
| High-risk external change | delete a sitemap, change robots/index controls, publish at scale, disavow links | explicit target-level authorization and rollback |

Preview the intended targets and payload before any external write. Log the confirmed result; do not report an attempted mutation as successful.

### Credential safety

- Use the connected credential store or environment secret mechanism.
- Request the least privilege and smallest property scope.
- Never paste tokens, private keys, or passwords into reports, commands, URLs, or repository files.
- Redact query parameters, cookies, authorization headers, and personal data from stored evidence.
- Rotate or revoke credentials through the owning platform if exposure is suspected.

### Cost and load guardrails

For crawls, APIs, warehouses, and paid data providers:

- estimate pages, rows, requests, bytes scanned, and monetary cost before a broad run;
- begin with a representative sample;
- cap concurrency, retries, pages, date ranges, and dimensions;
- honor rate-limit and retry guidance; use bounded exponential backoff where appropriate;
- avoid repeatedly requesting the same immutable period;
- partition and filter before joining large tables;
- use dry-run or query-cost estimation when available;
- set a stop threshold for unexpected expansion, errors, or spend;
- never launch paid requests or an unbounded site crawl merely to make an audit feel complete.

## Acquire data reproducibly

For every extract preserve a manifest:

```text
source and property/account
operation or report
requested and effective date range
timezone and freshness state
dimensions, filters, search/surface type, aggregation
pagination and row limits
rows returned and any truncation
export timestamp
schema/version
redactions or transformations
checksum or immutable artifact name
```

Use equal comparison windows and aligned weekdays. Keep raw exports read-only, write transformations to new artifacts, and make transformations deterministic.

When a connector is unavailable, request an export with exact fields rather than screenshots. Screenshots are useful for state evidence but poor analytical input.

## Operate large performance datasets

Interactive reports and row-based APIs may omit or truncate detail. For a large property, first determine whether the platform offers a scheduled bulk export to a warehouse.

### Bulk-export workflow

1. Verify the current export schema, data freshness, privacy exclusions, retention, and backfill behavior.
2. Confirm the owning project, region, billing controls, and dataset access.
3. Query only required date partitions and columns.
4. Aggregate metrics before joining high-cardinality dimensions.
5. Calculate ratios from summed numerators and denominators; do not average row-level ratios.
6. Treat anonymous or privacy-protected demand as unobservable detail, not zero demand.
7. Deduplicate reruns according to the export's documented keys and correction behavior.
8. Reconcile several daily totals with the native interface, allowing for documented freshness and aggregation differences.
9. Save query text, bytes processed, row count, and output checksum.
10. Add cost alerts and retention rules before scheduling recurring jobs.

### Safe query shape

Prefer:

```sql
SELECT
  date,
  page_cohort,
  SUM(clicks) AS clicks,
  SUM(impressions) AS impressions,
  SAFE_DIVIDE(SUM(clicks), SUM(impressions)) AS ctr
FROM partitioned_source
WHERE date BETWEEN @start_date AND @end_date
GROUP BY date, page_cohort
```

Adapt syntax to the actual warehouse. Never paste an assumed schema into production. Avoid selecting every column, unbounded date scans, or joining raw query-page rows to another many-to-many table.

### API extraction

When an API is the appropriate source:

- verify current per-request and per-day row limits;
- paginate deterministically;
- split by date or another documented dimension only when necessary;
- keep search types separate;
- detect repeated pages/cursors and stop;
- record incomplete responses and quota failures;
- test whether added dimensions materially reduce returned coverage.

The absence of a row after filtering is not proof of zero activity.

## Normalize and join datasets

### URL identity

Create an explicit normalization policy:

```text
host aliases
protocol policy
default ports
fragments
query parameters to retain, sort, or remove
case sensitivity
percent encoding
trailing slash
redirect destination
declared canonical
```

Preserve the raw URL and normalized key. Do not lowercase paths, remove all parameters, force trailing slashes, or replace URLs with declared canonicals unless site behavior justifies it.

Produce an exception table for collisions where multiple raw URLs map to one key. Validate normalization against routes, redirects, analytics, and canonical policy.

### Grain and joins

- Declare the row grain of both inputs.
- Aggregate to compatible grains before joining.
- Use a calendar table for time comparisons and explicit timezone conversion.
- Track unmatched rows on both sides.
- Preserve source-specific metrics rather than inventing equivalence.
- Version keyword, brand, page-type, locale, and conversion classification rules.
- Join revenue or leads only through approved, privacy-safe identifiers.

For landing-page joins, query strings may matter to analytics attribution even when canonical URLs consolidate search reporting. Keep both views when needed.

### Quality checks

At minimum test:

- schema and type drift;
- duplicate primary keys;
- missing dates or partitions;
- impossible negative counts;
- ratios outside valid bounds;
- sudden row-count changes;
- unknown classification share;
- normalized-URL collisions;
- reconciliation deltas;
- late-arriving or revised data.

Quarantine bad partitions rather than quietly folding them into a report.

## Evaluate third-party estimates

Before using a rank, keyword, backlink, traffic, AI-visibility, local-grid, or crawl provider, record:

```text
decision it supports
coverage: market, language, device, database, date
collection method and freshness
sampling and known blind spots
metric definition
export/API limits
price and request budget
terms and automation constraints
reproducibility
replacement or cross-check source
```

Keep provider-specific metrics in their own columns. Do not merge authority, difficulty, traffic, toxicity, or visibility scores from different providers as though they share a scale. Verify high-impact rows directly.

Paid access does not make an estimate first-party evidence. A vendor's missing URL, link, or keyword does not prove absence.

## Build durable reporting

Separate four layers:

1. **Raw evidence** — immutable exports and crawl/log snapshots.
2. **Modeled tables** — documented transformations, cohorts, and joins.
3. **Decision metrics** — definitions, baselines, thresholds, and uncertainty.
4. **Narrative** — findings, actions, owners, and limits.

For recurring work define:

- schedule and freshness expectation;
- data owner and business owner;
- successful-run and stale-data indicators;
- anomaly thresholds with minimum volume;
- alert destination and response runbook;
- versioned classifications and metric definitions;
- retention, privacy, and access review;
- a changelog for platform, tracking, and site changes.

An alert should identify a cohort and investigation path, not merely announce that a total moved.

## Acceptance checklist

- The data contract names the decision, grain, window, scope, and required freshness.
- Every source has a coverage statement and known limitations.
- Connected capabilities were discovered from actual schemas.
- Reads, local processing, and external mutations stayed within authority.
- Cost, rate, row, crawl, and retry bounds were explicit.
- Raw evidence is immutable and transformations are reproducible.
- Ratios were calculated from aggregated components.
- URL normalization and join collision handling were validated.
- Large extracts are partition-filtered, reconciled, and cost-monitored.
- Provider estimates remain labeled and are not treated as interchangeable.
- Sensitive values and personal data are absent from artifacts.
- The final report states missing data, truncation, freshness, and confidence.
