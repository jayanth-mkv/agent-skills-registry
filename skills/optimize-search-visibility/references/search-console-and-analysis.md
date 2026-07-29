# Search Console and performance analysis

Use this reference for Google Search Console, analytics, Bing data, URL Inspection, crawl logs, traffic drops, CTR analysis, content opportunities, and candidate page conflicts.

## Contents

1. [Interpretation rules](#interpretation-rules)
2. [Data acquisition](#data-acquisition)
3. [Large-property exports](#large-property-exports)
4. [Baseline and segmentation](#baseline-and-segmentation)
5. [Performance workflows](#performance-workflows)
6. [Indexing workflows](#indexing-workflows)
7. [AI citation reports](#ai-citation-reports)
8. [Traffic-drop diagnosis](#traffic-drop-diagnosis)
9. [Analytics and conversion](#analytics-and-conversion)
10. [Logs, rank, and backlink data](#logs-rank-and-backlink-data)
11. [Reporting requirements](#reporting-requirements)

## Interpretation rules

### Keep the systems distinct

- Search Console measures Google search appearances and clicks, not website sessions.
- Analytics measures tracked visits and behavior, subject to consent, blocking, implementation, and attribution.
- Rank trackers observe selected queries, locales, devices, and times.
- Crawl tools observe what their crawler fetched, not what Google indexed.
- URL Inspection API reports Google’s indexed version, not a live indexability test.
- Vendor keyword and backlink metrics are provider-specific estimates.

Do not force these systems to reconcile exactly. Explain likely reasons for discrepancies.

### Search Console limitations

Account for:

- anonymized queries omitted for privacy;
- top-row/data truncation, especially with query/page detail;
- most page data assigned to canonical URLs;
- property-vs-page aggregation changing clicks, impressions, CTR, and position;
- average position not representing a stable rank;
- result personalization, location, device, and time;
- recent/preliminary data changing;
- different search types requiring separate analysis;
- API row, quota, and load limits;
- bulk exports excluding anonymized query detail and following their own freshness/schema rules;
- chart totals exceeding visible/exported table rows;
- regex/filtering changing totals because anonymous rows are excluded.

Always record property, search type, dimensions, filters, aggregation, date window, timezone, data state, and export method.

## Data acquisition

### Prefer read-only connected access

If a connected GSC integration exists:

1. Inspect available tool schemas.
2. List properties and select the exact domain or URL-prefix property.
3. Use read-only performance, sitemap, and indexed-version inspection methods.
4. Paginate within documented limits.
5. Cache/reuse the same extracted data during the analysis.
6. Respect quotas; page+query requests and long ranges can be expensive.
7. Do not request indexing or modify sitemaps unless explicitly authorized.

Never ask the user to paste OAuth tokens, client secrets, or service-account keys.

### Use exports when no connector exists

Request only the exports needed:

- Queries;
- Pages;
- Query × Page for candidate overlap;
- Dates for trends;
- Country and Device for segmentation;
- Search appearance via its supported workflow;
- separate Web, Image, Video, News, Discover, or Google News exports where relevant;
- Page Indexing and sitemap exports;
- URL Inspection results for a stratified sample.

For the bundled analyzer, export CSV with common headers such as:

```text
Query, Page, Clicks, Impressions, CTR, Position
```

It also accepts common localized/case variants documented in `--help`. Provide matched current and previous windows when comparing performance.

### Choose fair windows

- Compare equal-length windows and aligned weekdays.
- Use year-over-year or modeled seasonal context where seasonality matters.
- Annotate launches, migrations, tracking changes, incidents, campaigns, holidays, and search updates.
- Exclude incomplete days unless the task is real-time incident response.
- Use longer windows for sparse data and shorter windows for clear incidents.

## Large-property exports

Interactive interfaces and row APIs may not return all detailed rows for a large property. When the platform provides a scheduled warehouse export, use it for repeatable cohort analysis while preserving the documented privacy exclusions.

Before relying on one:

1. verify the current schema, export start date, freshness, correction behavior, privacy exclusions, retention, and backfill limits;
2. confirm property identity, destination project/dataset, region, billing controls, and least-privilege access;
3. query only required date partitions and columns;
4. aggregate clicks and impressions before calculating CTR or joining high-cardinality data;
5. keep site-level and URL-level grains distinct;
6. reconcile several daily totals against the native report using the same search type and aggregation;
7. save query text, parameters, bytes processed, row count, run time, and output checksum;
8. monitor missing partitions, late data, duplicate keys, schema drift, and unexpected cost.

Do not join raw query-page-device-country rows directly to another many-to-many dataset. First aggregate to the decision's declared grain. Treat absent anonymized query detail as unknown, not zero.

For a one-time narrow question, a bounded API or export may be cheaper and clearer than warehouse setup. Use the source-selection and cost controls in [data-and-tooling.md](data-and-tooling.md).

## Baseline and segmentation

Start with totals, then segment until the change is localized:

```text
property
-> search type
-> country
-> device
-> brand/non-brand query class
-> directory/page type/template
-> query intent/topic
-> search appearance
-> individual query-page pairs
```

Build a ledger:

| Segment | Clicks | Impressions | CTR | Position | Conversions | Change | Coverage note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |

Avoid averaging ratios incorrectly. Aggregate clicks and impressions, then calculate CTR. Treat average position as impression-weighted and contextual.

## Performance workflows

### Winners and losers

For current versus previous matched windows:

1. Aggregate by page and query separately.
2. Compute absolute and relative changes in clicks/impressions.
3. Require a minimum baseline before emphasizing percentages.
4. Rank by business impact, not percentage alone.
5. Segment brand, device, country, and page type.
6. Inspect changed SERPs and changed pages.
7. Link each change to deployments, content updates, index status, and conversion outcomes.

Report new/lost rows separately from rows with calculable percentage changes.

### CTR opportunities

Do not use one universal CTR benchmark.

1. Group comparable rows by approximate position band, device, query class, country, and result type.
2. Establish the site’s own median or modeled baseline when sample size permits.
3. Find high-impression rows below their comparable baseline.
4. Inspect the live SERP, title/snippet generation, intent, brand, rich features, and query ambiguity.
5. Propose a test with a stable cohort and decision window.

CTR can fall when impressions expand to new/lower positions; interpret clicks and qualified outcomes together.

### Near-opportunity pages

Use positions as broad bands, not precise rank:

- 1–3: defend and improve qualified CTR/conversion;
- 4–10: assess intent, evidence, internal links, presentation, and SERP features;
- 11–20: evaluate whether the page truly fits and whether improvement is attainable;
- beyond 20: prioritize only with strong audience/business fit or evidence of movement.

High impressions plus modest average position can reflect broad, mixed query coverage. Inspect query-page detail.

### Candidate page overlap

Multiple pages for one query is not automatically cannibalization. Treat it as a candidate only when:

- pages serve materially the same intent/job;
- visibility alternates or splits over time;
- neither page establishes a stable role;
- internal/canonical signals conflict;
- consolidation/repositioning would improve user choice;
- conversions/backlinks do not justify distinct pages.

For each candidate compare:

- query and intent;
- URLs/page types;
- date trend and devices/countries;
- clicks, impressions, CTR, average position;
- landing-page conversions;
- content overlap and unique value;
- internal links, canonicals, and SERP result type.

Possible actions: keep both, differentiate, link/hub, merge, redirect, canonicalize true duplicates, or retire. Never select a destination by position alone.

### Content decay

Look for sustained comparable-window declines rather than one noisy period. Check:

- lost impressions versus lost CTR;
- query/intent shifts;
- SERP feature and competitor changes;
- stale or incorrect information;
- product availability/price changes;
- index/canonical/render problems;
- internal-link or navigation changes;
- seasonality and demand loss;
- changes in conversion despite lower traffic.

Refresh only when the page’s audience job still matters.

### Brand and non-brand

Build brand regex from verified names, products, domains, and common misspellings. Because query filtering omits anonymized rows, label branded share as an approximation.

Analyze:

- brand demand and reputation;
- non-brand discovery;
- navigational leakage;
- product/category growth;
- unexpected or hacked queries.

### Forecasts and opportunity estimates

Use ranges and make assumptions explicit:

```text
incremental clicks = eligible impressions × plausible CTR change
qualified outcomes = incremental clicks × observed landing-page outcome rate
```

Use site/cohort observations, not invented industry averages. Do not present the result as guaranteed.

## Indexing workflows

### Build an index sample

Include:

- top organic landing pages;
- high-value pages with zero/low GSC visibility;
- newest and recently changed pages;
- each template and sitemap;
- redirected/canonicalized/noindex/blocked examples;
- pages flagged by Page Indexing;
- parameter/facet/locale/product/location examples;
- pages with discrepancies between crawl and GSC.

### Inspect the indexed version

For each URL capture:

- verdict and coverage state;
- last crawl time and crawling user agent;
- page-fetch and robots state;
- indexing state;
- declared and Google-selected canonical;
- known sitemap/referring URLs;
- rich-result findings where returned.

The API cannot test the live URL. Pair it with a current HTTP/raw/rendered check and record the difference.

### Categorize by intended state

Create an intent matrix:

| URL cohort | Intended crawl? | Intended index? | Intended canonical | Sitemap? | Observed state | Action |
| --- | --- | --- | --- | --- | --- | --- |

An excluded utility URL can be correct. An indexed URL is not automatically valuable. Judge against the intended portfolio.

### Sitemap cohorts

Use separate sitemaps by meaningful template or lifecycle when this improves diagnosis. Compare submitted, read, discovered, indexed, and traffic outcomes. Do not use sitemap inclusion as proof of index eligibility.

## AI citation reports

Some webmaster platforms expose first-party reports about citations or grounding in their AI search experiences. Availability, names, metrics, and definitions can change; verify the current official documentation and actual property interface at execution time.

When available, capture:

- property, date window, market/surface, freshness, and report status;
- total citation events under the platform's definition;
- cited URL/page activity;
- example grounding or source-selection queries when exposed;
- changes by page cohort and topic;
- whether the report is complete, sampled, rounded, or privacy-filtered.

Keep these concepts separate:

- a citation event is not necessarily a click;
- a cited page count is not an index-coverage count;
- a grounding query is not automatically equivalent to an ordinary search query;
- citation frequency does not reveal placement, authority, sentiment, or ranking unless the platform explicitly reports it;
- report changes can reflect product rollout, reporting changes, or prompt mix as well as site changes.

Corroborate with reproducible manual or approved-API observations, verified crawler logs, raw referral data, and qualified outcomes. Preserve the platform's own metric names and definitions rather than converting them into an invented “AI visibility score.”

## Traffic-drop diagnosis

### First establish the incident

Record:

- exact start and shape: sudden/gradual, sustained/recovered;
- metrics affected: impressions, clicks, sessions, conversions, revenue;
- channels/search types/markets/devices/page types affected;
- tracking and consent changes;
- releases, migrations, outages, security events, and manual actions;
- seasonality, demand, SERP, and competitor context.

### Diagnose by signal shape

| Pattern | Investigate first |
| --- | --- |
| Analytics drops, GSC stable | analytics/consent/tagging/channel attribution |
| GSC impressions drop broadly | eligibility, demand, major site/algorithm/SERP change |
| Impressions stable, clicks drop | CTR, result presentation, SERP features, intent |
| One directory/template drops | release, render, canonical, internal links, content change |
| One country/device drops | localization, mobile, geo/CDN, SERP changes |
| Indexed pages fall | directives, canonicals, status, crawl/server, quality cohorts |
| Conversion falls, traffic stable | landing experience, offer, tracking, audience mix |
| Branded demand falls | brand/market demand, reputation, campaign changes |

Treat public search updates as one hypothesis, not a default explanation. Correlate timing and affected cohorts, then test site-specific causes.

### Recovery plan

Prioritize:

1. containment of confirmed technical or security loss;
2. measurement repair;
3. reversible fixes with direct evidence;
4. cohort tests for uncertain content/intent causes;
5. longer-term product/content/authority work.

Do not make simultaneous mass changes that destroy causal learning unless an active blocker demands it.

## Analytics and conversion

Join GSC landing pages to analytics using normalized canonical URLs and documented rules. Measure:

- organic entrances/sessions/users;
- meaningful engagement tied to page purpose;
- conversions and assisted outcomes;
- revenue, qualified leads, or activation;
- device/country/new-returning differences;
- landing-to-next-step paths;
- page speed and error experience.

Check:

- tags fire on intended templates;
- consent-mode changes;
- cross-domain/referral exclusions;
- channel grouping and UTMs;
- bot/internal traffic filters;
- timezone/currency;
- conversion definition/version;
- sampling or thresholding.

Traffic is not the end goal. A lower-volume, higher-qualified cohort may be an improvement.

## Logs, rank, and backlink data

### Server/CDN logs

Analyze an owned local export with:

```bash
python scripts/analyze_crawl_logs.py access.log \
  --output crawl-log-analysis.json \
  --markdown crawl-log-analysis.md
```

The bundled analyzer treats user-agent matches as claimed crawler families, redacts query values by default, and reports parsing coverage. Verify crawler identity using current provider guidance and infrastructure evidence where consequential.

Segment requests by host, verified or claimed crawler, status, path/template, content type, response time, cache result, and date. Look for repeated errors, redirected/noncanonical targets, parameter traps, stale inventory, blocked resources, and important cohorts with little observed crawling. Use logs to test crawl behavior; logs do not prove indexing.

### Rank trackers

Record provider, query set, location, language, device, frequency, and SERP-feature handling. Use rank data for controlled cohorts, not as a complete demand measure.

### Backlinks

Record provider and crawl date. Compare referring pages/domains, relevance, placement, destination, anchors, lost/new history, and verified availability. Keep proprietary authority/toxicity scores provider-specific. Manually inspect high-impact links.

## Reporting requirements

For each performance table state:

- exact date windows and timezone;
- property and search type;
- dimensions, filters, and aggregation;
- current/final data state;
- row and privacy limitations;
- minimum-volume rules;
- whether percentages are comparable;
- currency/conversion definition where used.

For each recommendation state the affected segment, observation, plausible cause, rival explanation, action, expected leading signal, outcome metric, decision window, and stop/rollback rule.
