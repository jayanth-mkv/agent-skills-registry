# Lifecycle and Email

Use this reference to plan permission-aware lifecycle communication across email, text, push, in-product, and coordinated human follow-up. For a detailed audit of an existing email artifact, use `analyze-email-effectiveness` when installed.

## Contents

1. Model the lifecycle
2. Define the program
3. Common programs
4. Design each message
5. Deliverability and technical quality
6. Consent, privacy, and compliance
7. Measurement and testing
8. Cold outreach boundary

## 1. Model the lifecycle

Start from recipient state, not a default cadence:

```text
eligible state + observed trigger
-> message job
-> desired state change
-> next condition
-> branch, suppression, or exit
```

Useful states include prospect, new lead, evaluating, invited, signed up, unactivated, activated, engaged, at-risk, lapsed, renewed, expanded, advocate, and service-only. Adapt them to the business.

Coordinate email with product, website, sales, support, SMS, push, community, and paid media. Do not send an email that duplicates a better in-product action or creates conflicting requests.

Choose the channel from urgency, recipient expectation, message sensitivity, interaction needed, delivery reliability, accessibility, cost, and preference. Do not copy the same cadence into every channel.

## 2. Define the program

Specify:

- audience relationship and reasonable expectation;
- entry trigger and eligibility;
- recipient goal and business goal;
- current awareness, objections, and recent behavior;
- one state change the program should create;
- messages and the distinct job of each;
- timing logic tied to behavior or need;
- branches, frequency rules, suppression, and exit conditions;
- destination and next experience;
- sender identity, reply handling, support, and preference path;
- events, metrics, guardrails, and review cadence.

Use delays as starting hypotheses, not universal best practices. Consider urgency, product complexity, sales cycle, recipient time zone, channel overlap, and message fatigue.

## 3. Common programs

| Program | Entry | Primary job | Important exits/branches |
| --- | --- | --- | --- |
| Welcome or lead delivery | Valid signup/request | Deliver promise and set expectations | Unsubscribe, invalid address, next qualified action |
| Activation/onboarding | Account created or invited | Help recipient reach first value | Activated, stalled behavior, support need, conversion |
| Nurture/evaluation | Permissioned interest | Build understanding, proof, and decision confidence | Sales-ready, purchased, disengaged, disqualified |
| Transactional/service | User action or account event | Confirm, inform, protect, or enable service | Resolution, failure, security escalation |
| Retention/adoption | Use or lifecycle signal | Deepen useful behavior and value | Milestone, inactivity, plan change, support issue |
| Renewal/expansion | Contract or value milestone | Clarify value, decision, and next option | Renewed, downsell, sales conversation, cancel intent |
| At-risk/re-engagement | Meaningful inactivity or risk signal | Restore value or learn preferences | Re-engaged, snoozed, unsubscribed, sunset |
| Feedback/advocacy | Completed value milestone | Learn, review, refer, or contribute | Feedback received, issue found, referral made |
| Newsletter/editorial | Subscribed audience | Deliver recurring expected value | Preference change, inactivity, unsubscribe |

Transactional messages must prioritize the transaction. Do not disguise promotion as essential service communication.

## 4. Design each message

Define:

```text
Message name:
Eligible state and trigger:
Primary job:
Recipient value:
Subject and preview:
Body argument:
Proof or reassurance:
Primary CTA and destination:
Secondary/service actions:
Branch or next condition:
Suppression and exit:
Events and guardrails:
```

Use one dominant job and next action. Make sender and intent recognizable. Ensure the subject, preview, body, CTA, destination, and post-click experience make the same promise.

Prefer clear, specific language over clickbait, false urgency, or information withholding. Personalize from meaningful, accurate context; never fabricate familiarity, activity, or research. Make essential meaning available without images. Use readable hierarchy, descriptive links, adequate contrast, useful alternative text, and a plain-text part when applicable.

## 5. Deliverability and technical quality

Treat these as interacting systems:

- permission and documented list origin;
- expectation, relevance, frequency, complaints, and disengagement;
- sender and domain reputation;
- authentication and alignment where applicable;
- bounce, invalid-recipient, and suppression handling;
- stable identity, domains, links, and reply path;
- accessible, resilient HTML and meaningful text;
- provider requirements and message classification.

Accepted, delivered, inboxed, opened, clicked, replied, converted, and retained are different outcomes. Do not promise inbox placement. Do not use folklore lists of “spam words” as a substitute for expectation and quality.

## 6. Consent, privacy, and compliance

Identify recipient location, sender location, relationship, purpose, data source, and message type before making legal claims. Verify current requirements from primary legal and provider sources when they matter.

At minimum:

- document the lawful and expected audience source;
- provide accurate sender identity and a functional reply/support path;
- honor preferences, opt-outs, suppression, and deletion requirements;
- apply channel-specific consent, quiet-time, sender-registration, disclosure, and content rules;
- collect only necessary data and avoid sensitive inference;
- do not obstruct unsubscribe or make it conditional on login;
- do not repurpose transactional consent for unrelated promotion;
- do not purchase, scrape, or launder audiences;
- do not help evade filters, provider enforcement, or platform limits.

When legal status is uncertain, describe the risk and request qualified review; do not present general guidance as legal advice.

## 7. Measurement and testing

Measure the state change, not just message interaction:

```text
eligible -> sent -> accepted/delivered -> reliable engagement
-> intended action -> experienced value -> retained outcome
```

Define counts, denominators, attribution window, exclusions, bot/privacy filtering, and cohort maturity. Treat opens as a weak diagnostic because privacy proxies and prefetching can distort them.

Segment by entry source, lifecycle state, message family, domain/provider, device/client, cohort, and relevant customer characteristics. Monitor complaints, unsubscribes, bounces, support contacts, fatigue, and downstream quality as guardrails.

Test one decision-relevant hypothesis at a time when possible. Prefer holdouts or behavior outcomes to subject-line vanity wins. Do not claim causality from a before/after rate without considering mix, seasonality, novelty, or instrumentation changes.

## 8. Cold outreach boundary

Use cold outreach only when the user has a legitimate, compliant reason to contact a narrowly relevant business audience. Load the outbound, sales, and revenue-operations reference for account selection, data operations, sequencing, routing, and pipeline design. Require:

- evidence-based account/contact relevance;
- truthful identity and reason for contact;
- an offer proportionate to the interruption;
- accurate personalization;
- low volume, preference respect, suppression, and reply handling;
- jurisdiction and provider-rule verification;
- qualification and sales capacity.

Optimize for useful conversations and recipient respect, not maximum send volume. Refuse scraping, purchased lists, deceptive threading, fake replies, impersonation, evasion, or harassment.
