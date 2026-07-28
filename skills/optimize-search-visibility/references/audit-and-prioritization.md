# Audit and prioritization model

Use this reference to plan coverage, grade evidence, control sampling, and turn observations into work that can be verified.

## Contents

1. [Audit contract](#audit-contract)
2. [Coverage map](#coverage-map)
3. [Evidence grades](#evidence-grades)
4. [Sampling](#sampling)
5. [Finding record](#finding-record)
6. [Severity and priority](#severity-and-priority)
7. [Scoring](#scoring)
8. [Report shape](#report-shape)

## Audit contract

Write this at the start of a substantial audit:

```text
Decision:
Primary business outcome:
Priority audiences / markets:
Properties and environments:
Included page types:
Excluded areas:
Evidence available:
Crawl and data windows:
Known changes or incidents:
Deliverables:
Implementation authority:
```

An audit is complete when it covers the agreed decision and clearly reports limitations. It is not complete merely because a checklist was exhausted.

## Coverage map

Mark each applicable area `Assessed`, `Sampled`, `Not assessed`, or `Not applicable`.

| Area | Minimum evidence | Typical questions |
| --- | --- | --- |
| Availability | HTTP/TLS/DNS samples | Can users and crawlers fetch the intended host and URLs? |
| Crawl control | robots.txt plus tested URLs | Are important resources allowed and waste controlled? |
| Index control | meta/X-Robots, canonicals, GSC | Which URLs are eligible, selected, excluded, or conflicting? |
| Discovery | sitemaps, nav, link graph, logs | Can important URLs be found and recrawled efficiently? |
| URL system | patterns, parameters, redirects | Are duplicate and legacy variants intentionally resolved? |
| Rendering | raw/rendered comparisons | Is primary content and metadata available without fragile interaction? |
| Architecture | templates, depth, hubs, orphan candidates | Does the site express priority and relationships? |
| Page experience | field and lab data, mobile samples | Can users load, interact, read, and complete tasks? |
| On-page | titles, headings, snippets, media | Does each page clearly represent its purpose? |
| Content | inventory, intent, accuracy, originality | Does content satisfy a real audience better than alternatives? |
| Structured data | markup, visible content, supported rules | Is eligible markup valid, truthful, and maintained? |
| Internal links | graph, anchors, placement | Are discovery, context, and priority reinforced? |
| External authority | relevant mentions/links/reputation | Is the site credibly known in its topic or market? |
| Search demand | queries, SERPs, audience research | Are opportunities based on actual needs and attainable fit? |
| Search performance | GSC/Bing/rank data | Where are visibility, CTR, and landing pages changing? |
| Business outcomes | analytics/CRM/revenue | Does organic visibility create qualified value? |
| AI search | eligibility, crawlers, citations, referrals | Is content available, cited accurately, and useful after the click? |
| Governance | owners, release process, monitoring | Can improvements survive future changes? |
| Specialist branch | vertical-specific evidence | Do local, international, commerce, publishing, or pSEO rules apply? |

## Evidence grades

Use evidence labels in the report:

| Grade | Meaning | Examples |
| --- | --- | --- |
| A — first-party observed | Direct, reproducible evidence from owned systems | GSC data, logs, repository, rendered page, controlled test |
| B — primary external | Current platform or standards evidence | Official search documentation, CrUX, supported validator |
| C — independent observed | Reproducible third-party observation | SERP sample, crawl from this audit, backlink-provider sample |
| D — inferred | Plausible explanation supported indirectly by evidence | Cause hypothesis, intent classification, opportunity estimate |
| E — supplied/unverified | Context provided but not independently checked | Stakeholder claim, old audit, undocumented release date |

Record source, URL or artifact, collection date, window, segment, and known limits. A high-severity claim should normally have grade A or B evidence, or be worded as a hypothesis requiring a test.

### Triangulate consequential diagnoses

For broad traffic loss or a high-risk change, seek at least two independent signals:

- GSC plus analytics or conversions;
- crawl plus URL Inspection;
- raw source plus rendered DOM;
- deployment history plus affected template cohort;
- ranking loss plus index/coverage or SERP change;
- vendor backlink data plus manual verification.

Agreement raises confidence. Disagreement is itself a finding to investigate.

## Sampling

### Build a stratified sample

Include:

- homepage and main navigation destinations;
- highest-value and highest-traffic landing pages;
- each shared page template and directory;
- recent, deep, orphan-candidate, parameterized, paginated, and redirected URLs;
- indexed and excluded examples from GSC;
- mobile and desktop representatives;
- each locale/store/location for specialist sites;
- both strong and weak performers.

Do not sample only URLs already known to be broken.

### Report coverage honestly

For every dataset state:

- total known population, when available;
- pages requested, fetched, rendered, blocked, failed, or skipped;
- sitemap URLs discovered and limits applied;
- date and time;
- user agent and crawl delay;
- whether subdomains, query strings, non-HTML resources, and external links were included;
- which first-party exports were truncated or sampled.

Use “0 issues observed in N tested URLs,” not “the site has no issues.”

### Scale by template

If 80,000 URLs share 12 templates, investigate the templates and URL-generating rules, then validate a stratified URL sample. Avoid turning 80,000 instances of one defect into 80,000 separate recommendations.

## Finding record

Use this structure in Markdown or JSON:

```yaml
id: TECH-CANON-001
title: Product parameter pages declare inconsistent canonicals
status: open
area: index-control
severity: high
scope:
  population: "product URLs with ?color="
  observed: "42 of 50 sampled"
evidence:
  grade: A
  observation: "Raw HTML canonical points to the parameter URL; sitemap lists base URL."
  sources:
    - "site-audit.json, collected 2026-07-29"
confidence: high
business_value: high
reach: high
effort: medium
change_risk: high
hypothesis: "Conflicting canonical signals are fragmenting consolidation."
recommendation: "Emit the selected base product canonical from the shared template."
owner: web-platform
dependencies:
  - "Confirm indexable variant policy with merchandising."
acceptance:
  - "All tested indexable variants return one absolute 200 canonical."
  - "Canonical target is indexable and present in the sitemap."
rollback: "Restore prior template and remove new cache entry."
leading_indicator: "Google-selected canonical agrees on inspected sample."
outcome_metric: "Impressions/clicks consolidate to base product cohort."
falsifier: "Google already selects base URLs and cohort performance is unaffected."
```

### Observation versus interpretation

Keep these separate:

- Observation: “37 of 50 product pages omit a canonical element.”
- Interpretation: “This may increase ambiguity among parameter variants.”
- Recommendation: “Define the intended variant policy and emit consistent signals.”

Avoid stating “Google is confused” unless a first-party result demonstrates canonical disagreement.

## Severity and priority

### Severity

| Level | Definition | Examples |
| --- | --- | --- |
| Blocker | Prevents the agreed audit or a business-critical search surface from functioning | Production host unavailable; entire intended site accidentally `noindex` |
| High | Strong evidence of material loss or a defect across high-value scope | Broken migration redirects; important template cannot render primary content |
| Medium | Meaningful but non-blocking loss/opportunity with credible reach | weak internal discovery across a priority cluster; invalid eligible product markup |
| Low | Limited reach, low business value, or maintenance issue | isolated stale snippet; minor sitemap hygiene |
| Opportunity | New growth or learning option rather than a defect | original research asset; new image-search coverage |

Reserve “manual action,” “penalty,” and “security incident” for evidence from the relevant report or an equivalent confirmed source.

### Priority

Prioritize through judgment, not an unexplained formula:

```text
dependency first
then expected reach × business value × confidence
tempered by effort × change risk × time-to-signal
```

Use these fields:

- **Reach:** isolated URL / template / directory / property.
- **Business value:** relation to revenue, leads, retention, support cost, or strategic audience.
- **Confidence:** high / medium / low, based on evidence and rival explanations.
- **Effort:** small / medium / large, including coordination.
- **Change risk:** low / medium / high, including index loss and rollback difficulty.
- **Time-to-signal:** deployment, recrawl, index, ranking, and business windows.

Fix dependencies before downstream polish. One shared template repair can outrank hundreds of hand-edited snippets.

### Avoid priority inflation

These are not automatically high severity:

- title or meta description length outside a tool’s heuristic;
- missing meta descriptions;
- multiple or out-of-order headings;
- absent optional structured data;
- low text count without page-purpose context;
- “toxic” link scores from a vendor;
- a page appearing for the same query as another page;
- a single lab-performance run;
- `llms.txt` absence;
- blocked training crawlers when that matches the owner’s policy.

## Scoring

Prefer a decision dashboard over a universal score. Report status by area, affected scope, evidence coverage, and trend.

If the user explicitly wants a score:

1. Define the decision it supports.
2. Publish categories, weights, thresholds, and evidence requirements.
3. Mark unavailable inputs as unavailable; never convert them to zero.
4. Separate eligibility gates from optimization points.
5. Display sample and confidence beside the score.
6. Keep the score comparable only under the same rubric and crawl configuration.
7. Never call it a Google, Bing, or AI-platform score.

Example:

```text
Technical readiness: 74/100
Coverage: 8 of 9 applicable areas; 240/18,400 known URLs sampled
Confidence: medium
Not assessed: server logs
Rubric version: 1.0
```

## Report shape

Use:

1. Decision and executive diagnosis.
2. Scope, evidence, coverage, and limitations.
3. Baseline and validated strengths.
4. Findings ordered by dependency and priority.
5. Affected templates/URL cohorts.
6. Immediate containment and quick wins.
7. Foundational roadmap and growth experiments.
8. Implementation tickets and acceptance tests.
9. Measurement, monitoring, and decision rules.
10. Assumptions, rejected causes, unknowns, and sources.

Every recommendation should answer: what changes, where, why here, who owns it, what could break, and how success will be verified.
