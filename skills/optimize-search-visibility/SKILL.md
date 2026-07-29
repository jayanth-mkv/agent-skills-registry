---
name: optimize-search-visibility
description: "Audit, diagnose, plan, implement, and verify end-to-end organic search improvements across crawlability, indexation, information architecture, on-page content, structured data, Core Web Vitals, internal links, authority, Search Console analytics, local, international, ecommerce, programmatic SEO, migrations, traffic drops, and AI-search visibility. Use when Codex needs to analyze a website or page; create or refresh an SEO strategy or content brief; investigate ranking, crawling, indexing, CTR, cannibalization, or traffic-loss problems; inspect GSC or analytics data; compare competitors; prepare or apply technical fixes; monitor regressions; or improve visibility in search and answer engines."
---

# Optimize Search Visibility

Turn search-visibility questions into evidence, fixes, verification, and a measurable learning loop. Cover the whole system, but run only the branches the decision needs.

## Operate by these principles

- Start with the business outcome, priority audience, market, page types, and cost of being wrong.
- Establish crawl and index eligibility before optimizing content that search systems cannot reliably access.
- Separate supplied facts, direct observations, first-party measurements, third-party estimates, inferences, and unknowns.
- Verify time-sensitive rules against current primary documentation before treating them as requirements.
- Prefer first-party data, rendered-page evidence, server evidence, and reproducible tests over generic checklists.
- Distinguish field data from lab data, correlation from causation, eligibility from ranking, and discovery from indexation.
- Treat competitor patterns as observations, not proof that copying them will rank.
- Never promise rankings, traffic, citations, rich results, or a numeric uplift. State uncertainty and a way to test.
- Reject fixed keyword densities, magic word counts, universal character limits, indiscriminate content pruning, and other false precision.
- Do not fabricate expertise, authors, reviews, ratings, dates, statistics, locations, backlinks, or structured-data properties.
- Keep crawls read-only, rate-limited, in scope, and compliant with robots.txt. Never bypass authentication, bot protection, or access controls.
- Never request credentials in chat or write secrets into the project. Prefer connected read-only tools or user-exported data.
- Do not publish, submit URLs, change a Business Profile, disavow links, edit production, or deploy unless the user authorized that action.
- When implementation is requested and a codebase is available, make the smallest coherent fixes and verify them instead of stopping at advice.

## Route the request

| Request | Mode | Default result |
| --- | --- | --- |
| “Audit my whole site” | Full audit | Crawl evidence, sampled live checks, prioritized roadmap, measurement plan |
| “Audit/fix this page” | Page audit | Intent and SERP fit, content/on-page/technical findings, specific revisions |
| “Why did traffic drop?” | Incident diagnosis | Timeline, segmented deltas, competing causes, recovery tests |
| “Use Search Console data” | Performance analysis | Queries/pages/segments, opportunities, losses, candidate conflicts, actions |
| “Build an SEO data/reporting system” | Data operations | Source contract, safe extraction, joins, quality checks, governed reporting |
| “Technical SEO / indexing” | Technical diagnosis | Crawl, render, canonical, directive, sitemap, status, CWV, schema findings |
| “Create a content strategy/brief” | Growth strategy | Demand map, intent clusters, portfolio gaps, briefs, internal-link plan |
| “Improve CTR, landing experience, or conversions” | Search experience | SERP evidence, promise fit, usability, experiment and outcome plan |
| “Improve AI/GEO/AEO visibility” | AI-search analysis | Eligibility, crawler controls, citation evidence, entity/content improvements |
| “Local/international/ecommerce/pSEO” | Specialist audit | Relevant specialist checks plus core foundations |
| “Migrate/redesign this site” | Change control | URL mapping, preflight, launch gates, rollback and monitoring plan |
| “Implement the fixes” | Execution | Scoped code/content changes, tests, before/after evidence |
| “Monitor regressions” | Monitoring | Baseline, deterministic diff, alerts, owners, response rules |

For a narrow request, run the narrow mode. For a broad audit, use the complete workflow. If the user supplied enough context, proceed with labeled assumptions instead of blocking on intake.

## Load only the needed references

- Read [audit-and-prioritization.md](references/audit-and-prioritization.md) for audit coverage, evidence grades, sampling, finding records, severity, and reporting.
- Read [technical-seo.md](references/technical-seo.md) for crawling, indexing, canonicals, directives, sitemaps, redirects, rendering, performance, structured data, images, and large-site checks.
- Read [content-and-authority.md](references/content-and-authority.md) for research, intent, content quality, briefs, refreshes, internal linking, and link earning.
- Read [search-experience-and-serps.md](references/search-experience-and-serps.md) for reproducible SERP observation, query-to-page fit, answer formats, titles/snippets, accessibility, conversion paths, comparisons, tools, and SEO experiments.
- Read [search-console-and-analysis.md](references/search-console-and-analysis.md) before interpreting GSC, analytics, URL Inspection, crawl logs, CTR, “cannibalization,” or traffic changes.
- Read [data-and-tooling.md](references/data-and-tooling.md) before selecting integrations, running paid or high-volume data collection, operating bulk exports, joining sources, or designing recurring reports.
- Read [ai-search.md](references/ai-search.md) for AI features, crawler controls, answer-engine visibility, citations, `llms.txt`, and measurement.
- Read [specialist-playbooks.md](references/specialist-playbooks.md) for local, international, ecommerce, publisher, SaaS, programmatic, UGC, migration, or multi-site work.
- Read [implementation-and-measurement.md](references/implementation-and-measurement.md) before changing code/content or defining tests, tickets, experiments, dashboards, and monitoring.
- Read [verification-protocol.md](references/verification-protocol.md) when checking time-sensitive platform requirements or refreshing operational guidance.

## Execute the core workflow

### 1. Frame the decision and scope

Capture or infer:

- target domain, subdomains, environments, markets, languages, devices, and search surfaces;
- business model, conversion, priority audiences, high-value templates, and known competitors;
- requested outcome, baseline, horizon, constraints, and deliverable;
- access available: public web, repository, GSC, analytics, Bing, Business Profile, rank data, backlinks, logs, or prior audits;
- planned changes, recent releases, migrations, incidents, seasonality, and annotations;
- whether the user wants diagnosis only, an implementation plan, or applied fixes.

State exclusions. “Entire site” still requires crawl caps, sampling, and coverage disclosure; never imply exhaustive coverage when the crawl or data is partial.

### 2. Create an evidence plan

Use the least invasive sources that answer the decision. For multi-source, paid, connected, or recurring work, define the data contract and guardrails in [data-and-tooling.md](references/data-and-tooling.md).

1. **Public evidence** — HTTP responses, raw and rendered HTML, robots.txt, sitemaps, internal links, representative SERPs, supported validators, PageSpeed/CrUX.
2. **First-party evidence** — GSC, analytics, Bing, Business Profile, Merchant Center, server/CDN logs, CMS inventory, conversions, revenue, experiments.
3. **Implementation evidence** — routes, templates, middleware, headers, schema generators, content models, deployment history, tests.
4. **Human evidence** — audience research, support/sales language, editorial expertise, product constraints, incident knowledge.

List unavailable sources and how each gap limits confidence. Do not quietly replace missing field data with a guess.

### 3. Capture a reproducible baseline

Run the bundled crawler for a static, same-host evidence snapshot:

```bash
python scripts/audit_site.py https://example.com \
  --max-pages 200 \
  --output site-audit.json \
  --markdown site-audit.md
```

Use `python scripts/audit_site.py --help` for crawl limits, private-host protection, sitemap controls, delays, and other options. Treat its heuristics as leads, not final verdicts.

Then:

- inspect representative templates in both raw HTML and a rendered browser when JavaScript may change content or metadata;
- sample the homepage, top organic landing pages, conversion pages, hub/category pages, newest pages, deep pages, parameter/faceted URLs, and known problem URLs;
- record date/time, user agent, environment, crawl limits, failed requests, robots exclusions, sitemap coverage, and data freshness;
- capture current metrics and deployment/version identifiers when a before/after comparison will matter.

Do not use a homepage-only review as a site audit. Do not claim that the crawler observed Google’s index.

### 4. Enrich with live and first-party evidence

Before making current platform claims, browse the relevant official documentation and record the verification date.

- If a connected Search Console capability exists, use read-only property, performance, sitemap, and indexed-version inspection methods. Do not assume tool names; inspect the available schemas.
- If no connector exists, ask for appropriate exports and analyze them offline:

```bash
python scripts/analyze_gsc.py \
  --current gsc-current.csv \
  --previous gsc-previous.csv \
  --brand-term example \
  --output gsc-analysis.json \
  --markdown gsc-analysis.md
```

- For owned server/CDN access logs, analyze a local export without exposing query values:

```bash
python scripts/analyze_crawl_logs.py access.log \
  --output crawl-log-analysis.json \
  --markdown crawl-log-analysis.md
```

- Use CrUX or another field source for real-user Core Web Vitals when available. Use Lighthouse/PageSpeed lab results to diagnose causes, not to impersonate field performance.
- Segment Search Console and analytics before interpreting totals: page type, directory, query class, country, device, search type, brand/non-brand, and comparable dates.
- Inspect representative SERPs using [search-experience-and-serps.md](references/search-experience-and-serps.md) for intent, result types, diversity, freshness, promise fit, and competitor coverage. Record locale/device/date and treat rankings as variable observations.
- Use backlink or rank vendors only as estimates; name the provider and never merge incompatible proprietary metrics as if equivalent.

### 5. Diagnose in dependency order

Evaluate these layers:

1. **Availability and eligibility** — DNS/TLS/HTTP, status behavior, crawl access, `noindex`, manual actions/security, canonical conflicts.
2. **Discovery and architecture** — sitemaps, navigation, crawl depth, orphan candidates, internal links, faceting, pagination, URL duplication.
3. **Rendering and experience** — raw/rendered parity, mobile parity, accessibility and agent-interaction blockers, intrusive UI, task completion, CWV field status and lab causes.
4. **Meaning and intent** — page purpose, query/audience fit, content accuracy, originality, demonstrated experience, topical gaps, freshness.
5. **Presentation eligibility** — titles/snippets, images/video, structured data that matches visible content, merchant/local data consistency.
6. **Authority and demand** — brand/entity consistency, relevant mentions and links, reputation, linkable evidence, distribution.
7. **Performance and outcomes** — visibility, CTR, landing-page behavior, conversions, revenue or qualified outcomes, trends and anomalies.
8. **AI-search surfaces** — search eligibility, allowed crawlers, extractable factual passages, citations/mentions, referral quality, answer accuracy.

Open the applicable specialist branch only after checking the shared foundations.

### 6. Turn observations into defensible findings

For every material finding, include:

```text
ID and title
Affected scope and sample size
Direct observation
Evidence source, date, and reproducible check
Why it matters for this site
Severity, reach, business value, confidence, effort, risk
Recommended change and owner
Dependencies and rollback concern
Acceptance test
Leading indicator and outcome metric
What would falsify the diagnosis
```

Use `Blocker`, `High`, `Medium`, `Low`, or `Opportunity` severity from the audit reference. Do not label a missing meta description, extra H1, or absent optional schema as “Critical” without site-specific evidence.

Rank work by dependency, expected reach, business value, confidence, effort, and change risk. Avoid decorative health scores. If a score is requested, expose the rubric, weights, unavailable inputs, and coverage; never present it as a search-engine score.

### 7. Design or apply the fix

Sequence work:

1. Stop active loss and remove access/indexing blockers.
2. Repair measurement and establish a trustworthy baseline.
3. Fix shared templates and architecture before isolated pages.
4. Improve high-value pages and intent coverage.
5. Build differentiated content, internal distribution, and earned authority.
6. Add specialist and AI-search improvements that rest on sound foundations.
7. Monitor, test, and iterate.

For risky changes—robots directives, canonicals, redirects, hreflang, faceting, schema at scale, migrations, mass deletion—require an explicit URL-level design, sample validation, staged rollout where possible, and rollback plan.

When editing a repository, trace the generator or template rather than patching generated output blindly. Preserve unrelated changes. Validate raw HTML, rendered output, headers, routes, and tests in proportion to risk.

### 8. Verify and monitor

Re-run the same crawl configuration after implementation, then compare snapshots:

```bash
python scripts/compare_site_audits.py before.json after.json \
  --output audit-diff.json \
  --markdown audit-diff.md
```

Also verify:

- intended URL/status/redirect/canonical/directive behavior;
- raw/rendered metadata and primary-content parity;
- structured data syntax, eligibility rules, and visible-content agreement;
- internal links, sitemap membership, image/video behavior, mobile templates, and accessibility;
- performance regression budgets and representative field/lab measurements;
- GSC inspection after recrawl, then performance and conversion movement over an appropriate window.

Distinguish deployment success, crawler recrawl, index processing, ranking response, and business impact; they occur on different timelines. Keep monitoring thresholds and response owners explicit.

## Deliver the handoff

Lead with the decision and the highest-leverage next action. Include:

- scope, coverage, sampling, access, timestamps, and limitations;
- executive diagnosis and confidence;
- evidence inventory and baseline;
- validated strengths as well as problems;
- prioritized findings with affected URLs/templates;
- immediate containment, quick wins, foundational fixes, growth work, and monitored experiments;
- implementation tickets with owner, dependency, effort, risk, acceptance test, and rollback;
- measurement definitions, segments, baseline, decision windows, and stop/scale rules;
- assumptions, unknowns, rejected hypotheses, and live facts to re-verify.

Make the result executable. Give exact examples, selectors, routes, queries, rewrite directions, or code changes when evidence supports them. Keep unavailable or unverified sections marked `Not assessed`, never silently scored as failures.

## Final quality gate

- Did the work answer a business decision rather than merely enumerate checks?
- Is every major claim sourced, dated, and labeled by evidence type?
- Are crawl/index/rank/traffic/conversion concepts kept distinct?
- Were raw HTML, rendered output, first-party data, and representative templates used where relevant?
- Are Search Console limitations and date/segment effects reflected?
- Were data grain, cost, permissions, normalization, joins, truncation, and freshness made explicit?
- Does the search result promise continue through an accessible page experience and appropriate next action?
- Were SEO folklore and false precision removed?
- Does every high-priority action have affected scope, an owner, an acceptance test, and a rollback concern?
- Were current platform rules verified from primary sources?
- Are destructive, deceptive, policy-violating, or unauthorized actions excluded?
- Can the next analyst reproduce the baseline and determine whether the work succeeded?
