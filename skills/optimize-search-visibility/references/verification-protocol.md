# Verification protocol

Use this protocol whenever a recommendation depends on a rule, feature, threshold, crawler behavior, API limitation, reporting definition, or policy that may change.

## Authority order

Resolve conflicts in this order:

1. applicable law, contract, security, privacy, and explicit user constraints;
2. current official platform or standards documentation;
3. first-party site measurements and reproducible tests;
4. independent research with a transparent method;
5. practitioner or vendor guidance;
6. unsupported claims and generic checklists.

Never turn a heuristic into a platform requirement.

## Live verification workflow

1. Name the exact claim that needs verification.
2. Open the current official documentation for the affected platform or standard.
3. Confirm product, feature, market, language, device, account, and rollout scope.
4. Check current eligibility rules, exclusions, quotas, aggregation behavior, and deprecation notices.
5. Record the verification date in the user-facing work product when the fact materially affects a decision.
6. Compare the documented behavior with a representative live test or first-party measurement when possible.
7. Classify the result as confirmed, observed, inferred, disputed, or unknown.
8. Convert an unconfirmed claim into a hypothesis with a test, or remove it.

Do not rely on search-result snippets, cached summaries, memory, or a vendor checklist for consequential platform claims.

## Rules that always require a freshness check

- crawl directives, crawler identities, user-agent tokens, and access behavior;
- indexing, canonicalization, rendering, and mobile processing guidance;
- structured-data eligibility, required properties, and supported result types;
- search and answer-feature eligibility, controls, and reporting behavior;
- performance thresholds, field-data windows, and diagnostic tooling;
- webmaster, merchant, local, analytics, advertising, and inspection APIs;
- rate limits, row limits, aggregation, anonymization, freshness, and retention;
- submission protocols, sitemap behavior, and URL-notification support;
- spam, abuse, review, link, content, automation, and generative-content policies;
- browser, accessibility, privacy, consent, security, and regulatory requirements.

## Evidence rules

- Prefer first-party measurements over third-party estimates.
- Preserve raw evidence or a reproducible query whenever privacy and access rules allow.
- State the collection time, scope, environment, user agent, filters, caps, failures, and exclusions.
- Separate raw HTML from rendered output and lab measurements from field measurements.
- Separate discovery, crawl, index processing, ranking, presentation, traffic, and conversion.
- Treat Search Console-style reports as aggregated and potentially incomplete rather than exhaustive event logs.
- Treat URL-inspection results as a platform-observed indexed state, not necessarily the current live page.
- Treat structured data as eligibility markup that must match visible content, not a ranking guarantee.
- Treat experimental files or conventions as experiments until a target platform explicitly documents support.
- Distinguish ordinary search crawlers, answer/search crawlers, training crawlers, and user-triggered fetchers.

## Change protocol

When verified guidance changes:

1. identify the narrow rule and affected workflow;
2. remove the superseded claim instead of retaining both versions;
3. update the smallest relevant reference or script;
4. add or revise an acceptance test;
5. run the skill, script, catalog, and discovery validators;
6. forward-test the changed path on a realistic task;
7. state any remaining uncertainty in the resulting user work product.

## Guardrails

- Reject fixed keyword density, magic word counts, and universal CTR targets.
- Treat heading counts and snippet lengths as presentation heuristics, not ranking laws.
- Treat multi-page query overlap as an investigation candidate, not automatic cannibalization.
- Keep field Core Web Vitals distinct from lab proxies.
- Avoid invented composite “citability” scores or passage-length guarantees.
- Never promise rankings, traffic, citations, rich results, or a numeric uplift.
- Require affected scope, evidence, confidence, owner, acceptance test, falsifier, risk, and rollback for material recommendations.
