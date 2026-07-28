# AI-search visibility playbook

Use this reference for Google AI features, ChatGPT search, Perplexity, other answer engines, crawler controls, citation analysis, entity consistency, answer accuracy, and referral measurement.

## Contents

1. [Evidence posture](#evidence-posture)
2. [Eligibility foundations](#eligibility-foundations)
3. [Crawler and content controls](#crawler-and-content-controls)
4. [Content and entity quality](#content-and-entity-quality)
5. [Citation and answer analysis](#citation-and-answer-analysis)
6. [Measurement](#measurement)
7. [Experiments](#experiments)
8. [Myths and unsafe practices](#myths-and-unsafe-practices)

## Evidence posture

“GEO,” “AEO,” “LLMO,” and “AI SEO” are industry labels, not one standardized ranking system. Platforms use different retrieval sources, indexes, models, interfaces, locales, personalization, and update schedules.

At the time of each audit:

1. Read the current official site-owner/search/crawler documentation for every named platform.
2. Record the verification date and exact user-agent/control behavior.
3. Separate documented requirements from observed correlations and proposed experiments.
4. Avoid universal claims based on one platform or vendor study.
5. Do not claim that a page is “optimized for all LLMs.”

For Google AI Overviews and AI Mode, current official guidance says normal Search eligibility and SEO practices apply; no special schema or AI text file is required. Re-verify this before execution.

## Eligibility foundations

Audit in this order:

1. Page is publicly accessible and returns the intended response.
2. Relevant search or answer-engine crawler is allowed by robots and infrastructure.
3. Page is indexed/eligible in the platform’s source system where that is documented.
4. Snippet/content controls permit the desired preview.
5. Important content exists as accessible text and renders reliably.
6. Internal links and sitemaps support discovery.
7. Content is accurate, distinct, current, and trustworthy.
8. Structured data matches visible content.
9. Organization/product/person facts are consistent across authoritative sources.
10. The destination provides value after the citation or click.

AI-search work does not repair a blocked, unindexable, thin, or misleading page.

## Crawler and content controls

### Build a crawler policy matrix

Do not collapse all bots into “AI crawler.” For each platform verify:

| Provider/surface | User agent | Purpose | robots respected? | Desired policy | CDN/WAF result | Verified date/source |
| --- | --- | --- | --- | --- | --- | --- |

Purposes may include:

- traditional search indexing;
- answer/search retrieval;
- model training;
- user-triggered page fetching;
- ads or landing-page validation;
- generic crawling.

One provider can use different tokens for these purposes. A training control may not control search citations, and a user-triggered fetcher may follow different rules.

### OpenAI

Verify current OpenAI publisher/crawler documentation. At the time this reference was written, OpenAI documented `OAI-SearchBot` for search inclusion and distinguished it from other crawler purposes. Check robots.txt and CDN/WAF behavior; an allow rule does not help if infrastructure returns `403`.

### Google AI features

Google documents Googlebot controls for Search AI features and preview controls such as `nosnippet`, `data-nosnippet`, `max-snippet`, and `noindex`. `Google-Extended` governs some other generative-AI uses and is not the Search indexing control. Verify current scope before advising.

### Other platforms

For Perplexity, Anthropic, Microsoft/Bing, Apple, and any named platform, open the current official crawler documentation. Do not rely on a memorized bot list because names and purposes change.

### Test infrastructure

Inspect:

- robots.txt evaluation for the exact token;
- CDN/WAF/bot-management logs;
- status codes and challenge pages;
- rate limits;
- HTML returned to the crawler;
- DNS/IP allowlisting guidance only from the provider’s official source;
- whether policy differs by path.

Never bypass controls to test access. Recommend a policy choice, not blanket access.

### Preview and reuse controls

Explain tradeoffs:

- blocking a crawler can reduce that surface’s access;
- `noindex` can remove search eligibility;
- snippet controls can reduce what is shown or used in supported search experiences;
- legal, licensing, privacy, paywall, and business requirements can outweigh visibility.

Obtain the owner’s decision before changing controls.

### `llms.txt`

Treat `llms.txt` as experimental and platform-dependent:

- check whether the target platform officially documents using it;
- never describe it as an indexation or citation requirement without primary evidence;
- do not let it replace robots.txt, sitemaps, internal links, accessible HTML, or API/product feeds;
- if the owner wants one, keep it concise, accurate, non-secret, maintained, and aligned with canonical public resources;
- measure whether target systems fetch or use it before investing heavily.

## Content and entity quality

### Make content usable and extractable

Optimize for people first:

- answer the promised question directly;
- use descriptive headings and explicit terminology;
- keep factual claims close to evidence and dates;
- distinguish facts, opinions, estimates, and instructions;
- define scope, assumptions, and limitations;
- provide original data, examples, methodology, tools, or first-hand experience;
- use tables/steps only when they improve comprehension;
- keep important facts in accessible text, not image-only or interaction-only UI;
- provide stable anchors and clear page identity;
- maintain accurate update history.

Do not force every answer into a fixed word range. “Citability scores” based only on passage length are heuristics, not platform requirements.

### Strengthen entity consistency

Create a fact ledger for the organization and important entities:

```text
Canonical name:
Aliases:
Official domain:
Description:
Founding/launch facts:
Locations/service area:
People and roles:
Products/categories:
Prices/availability/version:
Official profiles:
Primary evidence URL:
Last verified:
Owner:
```

Reconcile contradictions across the website, Business Profile, Merchant Center, official social profiles, app stores, industry directories, knowledge sources, press materials, and structured data.

Use `sameAs` or entity markup only for genuine identity links. Do not fabricate knowledge-graph entries or edit community resources promotionally.

### Provide source-worthy evidence

Build assets other sources can responsibly cite:

- transparent original research and datasets;
- reproducible benchmarks and methodology;
- expert explanations with verifiable credentials;
- specifications, documentation, changelogs, policies, and pricing;
- calculators, tools, comparisons, and decision frameworks;
- first-party case studies with denominators and limitations;
- high-quality original images/video where relevant.

Distribution and legitimate mentions matter because answer systems may retrieve corroborating sources. Earn coverage; do not manufacture it.

### Structured data

Use currently supported, page-relevant structured data to clarify visible facts and become eligible for documented features. Do not claim special AI schema exists unless the platform publishes one. Keep feeds, Merchant Center, Business Profile, and on-page data synchronized for commerce/local use cases.

## Citation and answer analysis

### Define a prompt panel

Create a versioned set across:

- branded facts and navigation;
- category discovery;
- problems/tasks;
- comparisons and alternatives;
- local or transactional needs;
- expert/high-consideration questions;
- follow-up questions;
- sensitive misinformation risks.

For each prompt record audience, funnel/job stage, language, location, platform, model/mode, account state, and date.

### Capture observations

For each run record:

```text
Prompt ID and exact wording
Platform/model/mode
Date, locale, account/personalization state
Answer present?
Brand mentioned?
Brand position/context/sentiment
Citation/link present?
Exact cited URL and canonical
Claim supported by the cited page?
Competitors/sources cited
Factual errors or outdated facts
Click destination quality
Screenshot/export reference
```

Do not automate against a platform in violation of its terms. Use an approved API, licensed provider, or manual sampling.

### Classify citation gaps

- **Eligibility gap:** source cannot be crawled/indexed/shown.
- **Coverage gap:** source does not answer the prompt’s job.
- **Evidence gap:** content lacks unique, verifiable support.
- **Entity gap:** organization/product facts are inconsistent or unclear.
- **Authority gap:** corroborating sources do not support the claim.
- **Presentation gap:** relevant facts are buried, inaccessible, or ambiguous.
- **Freshness gap:** answer/source is outdated.
- **Measurement gap:** visibility is claimed without reproducible observations.

Recommend a fix only after classifying the gap.

### Monitor answer accuracy

Prioritize harmful errors:

- safety/legal/medical/financial misinformation;
- wrong price, availability, location, eligibility, or product capability;
- impersonation or entity confusion;
- outdated policies;
- unsupported negative claims.

Correct owned sources first, align authoritative profiles/feeds, publish clear evidence, and use any documented platform feedback route. Preserve screenshots and dates. Do not threaten or spam sources.

## Measurement

Use a dashboard with:

- prompt coverage and reproducibility;
- mention rate;
- citation/link rate;
- share of observed citations by topic/platform;
- cited landing pages;
- unsupported or inaccurate answer rate;
- crawler fetches from verified logs;
- referral sessions using documented referrers/UTMs;
- engaged sessions, conversions, revenue/qualified outcomes;
- brand-search and direct-demand trends;
- content/source freshness.

Report sample size and platform volatility. A 50% citation rate from 2 prompts is not a program metric.

Google AI-feature traffic may be included in overall Web performance data rather than exposed as a clean separate segment. Verify current reporting and avoid inventing attribution.

### Referral analysis

Maintain a documented source grouping for known AI referrers, but preserve raw source/medium. Providers can change referrers or open links through browsers/apps. Compare landing quality and conversion rather than traffic alone.

## Experiments

Good experiments change one defensible variable or cohort:

- unblock an intended search crawler on a controlled path;
- improve a page with new first-party evidence;
- correct entity facts across owned sources;
- restructure a buried answer for user clarity;
- add a supported feed or truthful structured data;
- create a superior source asset and distribute it;
- refresh stale pricing/specification pages.

Define:

```text
hypothesis
eligible prompt/page cohort
control or baseline
change
deployment and recrawl dates
leading signals
business outcome
decision window
confounders
stop/rollback rule
```

Citation outputs are stochastic. Repeat observations and preserve the environment details.

## Myths and unsafe practices

Reject:

- guaranteed citations or “rank #1 in ChatGPT” promises;
- fake community participation, fake reviews, or fabricated mentions;
- mass-produced “AI answer blocks” with no new value;
- invented research, statistics, expert quotes, or credentials;
- schema properties that are not visible and true;
- claims that `llms.txt` is universally required;
- blocking/unblocking all AI crawlers without an owner policy;
- interpreting training access as search visibility;
- treating one model answer as a stable ranking;
- copying cited competitors instead of creating better evidence;
- publishing private data to make content “citable”;
- claiming AI referral conversions without validated analytics.

Optimize for accurate discovery and a valuable destination, not for manipulating a model.
