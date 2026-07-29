---
name: analyze-email-effectiveness
description: Evidence-led analysis of individual emails, campaigns, sequences, programs, portfolios, and sending domains across lifecycle position, audience-message-offer fit, copy and conversion, MIME and HTML quality, accessibility, message security, consent, compliance, DNS and authentication, receiver reputation, inbox-placement evidence, DMARC reports, performance, and experiments. Use when Codex needs to audit, critique, compare, diagnose, score, or improve marketing, lifecycle, newsletter, outreach, product, notification, security, or transactional email from copy, screenshots, HTML, RFC 5322 messages, DNS, provider dashboards, event exports, or campaign metrics.
---

# Analyze Email Effectiveness

Determine what an email is trying to do, whether it belongs there, and what evidence explains the result. Diagnose before rewriting.

This is an analysis skill. Do not build sending infrastructure, send messages, alter DNS, enroll addresses, or deploy campaigns unless the user separately asks for that work.

## Non-negotiable evidence rules

- Separate **observed**, **reported**, **inferred**, and **unknown** facts.
- Never turn DNS syntax, a content heuristic, or a seed test into a universal “spam score.”
- Treat accepted, delivered, inboxed, displayed, opened, clicked, replied, converted, and retained as different outcomes.
- A published SPF/DKIM/DMARC record does not prove that a real message authenticated or reached the inbox.
- Failed DKIM selector guesses never prove DKIM is absent. Prefer exact `d=` and `s=` values from a current raw message or provider configuration.
- Trust `Authentication-Results` only inside a user-identified receiver boundary. Header text copied from an arbitrary message can be forged.
- Treat opens as weak engagement evidence when privacy prefetching or image proxies operate. Treat clicks as potentially scanner-generated until downstream behavior or bot filtering supports them.
- Verify current provider rules and laws from primary sources at task time. Record source, jurisdiction/provider, and date checked.
- Do not help conceal unwanted mail, evade filters, fabricate familiarity, use scraped/purchased audiences, or bypass opt-outs.

## Route the task

| Request | Evidence to prefer | Use |
| --- | --- | --- |
| Single-email critique or rewrite | Copy, screenshot, HTML, destination, audience and goal | [copy-and-conversion.md](references/copy-and-conversion.md) |
| Lifecycle or sequence audit | Trigger, state, each step, branches, exits, metrics | [positioning-and-lifecycle.md](references/positioning-and-lifecycle.md) |
| Program, portfolio, or competitor audit | Message inventory, eligibility, journeys, cadence, identities, owners and comparable public artifacts | [program-and-portfolio-audit.md](references/program-and-portfolio-audit.md) |
| Raw-message or HTML inspection | Original `.eml` or final rendered HTML | `scripts/inspect_email.py` and [html-accessibility-and-message-security.md](references/html-accessibility-and-message-security.md) |
| Authentication or domain audit | Raw received message, live DNS, sender inventory, IP/HELO | `scripts/audit_email_dns.py` and [email-dns-and-authentication.md](references/email-dns-and-authentication.md) |
| “Will this land in spam?” | Receiver dashboards, SMTP responses, complaints, ESP events, DMARC reports, controlled placement tests | [reputation-and-placement-diagnostics.md](references/reputation-and-placement-diagnostics.md) |
| DMARC aggregate-report diagnosis | Original XML, gzip, or zip reports plus authorized-source inventory | `scripts/parse_dmarc_reports.py` |
| Metrics or A/B test | Counts, denominators, exposure unit, window, assignment and guardrails | `scripts/analyze_email_experiment.py` and [measurement-and-experiments.md](references/measurement-and-experiments.md) |
| Consent or legal/provider review | Recipient/sender locations, purpose, relationship, source, consent and suppression evidence | [consent-and-compliance.md](references/consent-and-compliance.md) |

Use the smallest set of references needed, but use every row implicated by the request.

## Build an evidence packet

Capture what is available:

- sender, promoted entity, product, offer, verified claims, brand rules, and prohibited claims;
- recipient segment, relationship, source, consent evidence, awareness, objections, and reason to expect the message;
- message family, business goal, recipient job, trigger, frequency, prior/next step, branches, and exit;
- From name/address, Reply-To, subject, preview, body, CTA, footer, destination, and rendered clients;
- raw `.eml`, Header From, Return-Path/`MAIL FROM`, DKIM signatures, trusted receiver results, sending IP, HELO, and provider;
- sent, accepted, delivered, bounced, deferred, complained, unsubscribed, clicked, replied, converted, revenue, and exact denominators/windows;
- receiver-domain split, list source/age, suppression policy, domain/IP/stream, provider-dashboard evidence, and change history;
- control/variant assignment, sample size, exposure unit, attribution window, and guardrails.

Do not block a useful audit on missing context. Mark affected conclusions `unknown`, state what evidence would resolve them, and continue with the observable layers.

## Run deterministic inspection

Run paths from the skill directory, or use full paths.

### Message, HTML, links, and attachment evidence

```bash
python scripts/inspect_email.py path/to/received.eml --format json
python scripts/inspect_email.py path/to/received.eml \
  --trusted-authserv-id inbound.example.net \
  --format json
python scripts/inspect_email.py path/to/email.html \
  --subject "Subject" \
  --preview "Preview" \
  --format json
```

The inspector inventories MIME, headers, claimed DKIM identities, RFC 8058 one-click structure, trusted-boundary labels, links, deceptive-destination signals, Unicode controls, HTML features, accessibility evidence, tracking-pixel candidates, attachments, and hashes. Its findings are review signals, not maliciousness, consent, authentication, or placement verdicts.

### DNS, identity, and transport evidence

```bash
python -m pip install -r scripts/requirements.txt
python scripts/audit_email_dns.py example.com \
  --message path/to/received.eml \
  --sending-ip 192.0.2.25 \
  --helo-domain mail.example.com \
  --format json
```

If no raw message exists, supply known identities:

```bash
python scripts/audit_email_dns.py example.com \
  --header-from-domain example.com \
  --mail-from-domain bounce.example.com \
  --dkim selector@example.com \
  --sending-ip 192.0.2.25 \
  --org-domain example.com \
  --format json
```

Candidate DKIM discovery is enabled by default and uses bounded common/provider-informed probes. It reports positive records only and remains explicitly non-exhaustive. Use `--no-discover-dkim` for strict exact-selector work, `--fixture` for reproducible offline checks, `--query NAME:TYPE` for provider-specific names, and `--fetch-mta-sts` only when authenticated HTTPS retrieval is needed. `--org-domain` is a legacy/public-suffix compatibility comparison; current DMARC discovery uses the RFC 9989 DNS Tree Walk.

The DNS helper is read-only. It checks apex/inbound inventory, MX/Null MX, SPF dependency risk, DKIM keys/CNAMEs, current and legacy DMARC interpretation, BIMI, MTA-STS, TLS-RPT, DNSSEC signals, DANE/TLSA, PTR/forward confirmation, HELO, and custom records. It does not prove live authentication, reputation, or placement.

### DMARC aggregate evidence

```bash
python scripts/parse_dmarc_reports.py reports/ --format json
python scripts/parse_dmarc_reports.py report.xml.gz another-report.zip
```

The bounded parser accepts RFC 9990 and legacy aggregate XML, safely handles gzip/zip inputs, rejects DTD/entity declarations, deduplicates reports, and summarizes alignment, disposition, source IPs, selectors, and largest failures. Map sources against a separately maintained authorized-sender inventory before calling them legitimate or abusive.

### Experiment evidence

```bash
python scripts/analyze_email_experiment.py compare \
  --control-successes 420 --control-total 10000 \
  --variant-successes 470 --variant-total 10000 \
  --confidence 0.95 --format json

python scripts/analyze_email_experiment.py plan \
  --baseline-rate 0.04 --absolute-mde 0.005 \
  --confidence 0.95 --power 0.80 --format json
```

The helper reports effect size, uncertainty, a fixed-horizon two-sided test, and approximate balanced sample size. It cannot repair biased assignment, repeated peeking, clustering, attribution errors, bot traffic, or an irrelevant metric.

## Classify before judging

Assign and explain:

1. **Message family** — security, authentication, receipt, confirmation, account/service, product notification, digest, onboarding, activation, education, nurture, editorial newsletter, announcement, event, survey/feedback, review/referral, promotion, cart/browse recovery, renewal, retention, expansion, advocacy, re-engagement, win-back, sales outreach, fundraising, recruiting, or mixed.
2. **Lifecycle position** — acquisition, awareness, consideration, activation, conversion, adoption, retention, expansion, advocacy, reactivation, or service.
3. **Audience awareness** — unaware, problem-aware, solution-aware, product-aware, or most-aware.
4. **Primary job** — protect, verify, confirm, inform, reassure, educate, motivate one action, recover attention, deepen use, collect input, or complete service.

Use [positioning-and-lifecycle.md](references/positioning-and-lifecycle.md) for message-specific expectations, sequence state transitions, triggers, branches, exits, and cross-channel handoffs.

## Analyze in layers

### 1. Position, expectation, and necessity

Determine why this recipient should care now, why the message belongs at this stage, what state change it owns, whether nearby messages duplicate or contradict it, and what happens if it is removed. If an internal label conflicts with recipient-visible content, report both; mixed promotion inherits marketing expectations.

### 2. Audience-message-offer fit

Test relevance, promise, proof, mechanism, differentiation, objections, requested effort, personalization basis, and tone. Evaluate subject, preview, opening, body, CTA, and landing page as one promise chain. Never invent testimonials, scarcity, statistics, or recipient knowledge.

### 3. Content, rendering, accessibility, and security

Assess first-screen clarity, hierarchy, reading order, informative/decorative alt treatment, meaningful links, text alternative, localization/RTL, narrow screens, dark mode, client fallbacks, payload, attachments, redirects, Unicode controls, and secret exposure. Distinguish conformance evidence from actual rendering in tested clients. Use [html-accessibility-and-message-security.md](references/html-accessibility-and-message-security.md).

### 4. Identity, authentication, and transport

Keep these identities separate:

- Header From -> DMARC policy/alignment and BIMI;
- Return-Path or SMTP `MAIL FROM` -> SPF;
- each validated DKIM `d=`/`s=` -> DKIM and DMARC alignment;
- connecting IP and HELO -> SPF transaction, PTR/forward DNS, reputation;
- recipient policy domain -> inbound MX, MTA-STS, TLS-RPT, and DANE.

Report current RFC 9989 DMARC interpretation and any legacy receiver compatibility difference. A DMARC pass requires an actually authenticated aligned SPF or DKIM identifier. See [email-dns-and-authentication.md](references/email-dns-and-authentication.md).

### 5. Reputation and placement

Do not answer “inbox or spam?” from DNS alone. Triangulate:

```text
receiver SMTP response and provider dashboards
-> complaint/feedback-loop and ESP event evidence
-> DMARC/source authentication trends
-> list provenance, suppressions, volume and stream changes
-> controlled placement tests
-> message/content review
```

Separate domain, DKIM `d=`, IP, shared-pool, URL/domain, and campaign/list signals. Interpret each receiver independently. Use [reputation-and-placement-diagnostics.md](references/reputation-and-placement-diagnostics.md).

### 6. Consent, preference, and compliance

Classify purpose from the recipient’s perspective. Review source, consent/legal-basis evidence, identity, postal/contact disclosure, unsubscribe, preference scope, suppression, retention, processors, and recipient jurisdiction. A valid address is not permission. Provider rules and law are distinct. Use [consent-and-compliance.md](references/consent-and-compliance.md), and escalate jurisdiction-specific legal conclusions.

### 7. Performance and experiments

Trace:

```text
eligible -> sent -> accepted -> delivered -> receiver-observed placement
-> reliable engagement -> destination action -> conversion -> retained value
```

Use counts and explicit denominators. Segment by receiver, source, lifecycle state, domain/IP/stream, cohort, locale, device/client, template, and offer when sample size permits. Locate the largest decision-relevant loss, list rival causes, and specify the next discriminating evidence. Use [measurement-and-experiments.md](references/measurement-and-experiments.md).

## Score without false precision

Score only supported dimensions; use `N/A` for missing evidence.

| Score | Anchor |
| --- | --- |
| 1 | Contradictory, deceptive, broken, or materially harmful to the job |
| 2 | Major weakness likely to block understanding, trust, delivery, or action |
| 3 | Workable but generic, incomplete, fragile, or friction-heavy |
| 4 | Strong, specific, coherent, tested, and well matched to context |
| 5 | Exceptional evidence-backed fit with no material weakness found |

Typical dimensions: lifecycle fit; audience/offer fit; subject-preview continuity; clarity; proof; CTA/destination; trust; accessibility/technical quality; authentication evidence; consent/suppression evidence; measurement readiness. Do not average unlike dimensions into a universal grade. Rank findings by impact, confidence, effort, and reversibility.

## Improve only after diagnosis

When changes are requested:

1. Preserve verified facts, required service content, brand constraints, and opt-out/legal content.
2. State the strategic change before new copy.
3. Fix the highest-leverage evidence-backed issue first.
4. Rewrite the full subject-preview-opening-body-CTA path when needed.
5. Label assumptions and placeholders.
6. Make each variant test one distinct hypothesis.
7. Do not promise performance or placement improvement.
8. Recommend DNS/provider changes as reviewed proposals; never imply they were deployed.

## Deliver the audit

Use [analysis-outputs.md](references/analysis-outputs.md). Lead with:

- executive verdict and confidence;
- classification and intended recipient state change;
- evidence inventory with collection time/source;
- what works;
- prioritized `evidence -> impact -> recommendation -> confidence` findings;
- scorecard with `N/A`;
- placement/authentication conclusion by evidence layer, not a spam score;
- unknowns and exact next evidence needed;
- rewritten copy, remediation sequence, or experiment only when requested;
- current sources and date checked for provider, protocol, or legal claims.
