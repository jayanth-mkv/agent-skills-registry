# Copy, persuasion, and conversion analysis

Use this reference for the From/subject/preview envelope, opening, message structure, offer, proof, CTA, voice, personalization, and landing-page continuity.

## Analyze the complete promise chain

```text
sender recognition
-> subject promise
-> preview extension
-> first-screen fulfillment
-> body argument/service facts
-> CTA expectation
-> destination/action
-> post-action confirmation
```

Any break can create confusion, abandonment or complaints even when individual lines are polished.

## From, subject, and preview

Judge the trio on:

- **recognition:** does the displayed sender match the relationship and brand?
- **truth:** does the body immediately fulfill the implied promise?
- **relevance:** is value, consequence or required action specific?
- **distinction:** does preview add context rather than repeat the subject?
- **priority:** is urgency real, explained and proportionate?
- **privacy:** would lock-screen display expose sensitive facts?
- **resilience:** does essential meaning survive truncation without relying on one universal character count?

Flag fake `Re:`/`Fwd:`, deceptive order/security claims, invented deadlines, undisclosed sender identity, ambiguous “action required,” bait-and-switch curiosity and subject/body mismatch.

Generate alternatives around distinct hypotheses—direct outcome, concrete detail, credible curiosity, reassurance—not random synonyms.

## Opening

The first visible content should answer, in the order appropriate to the family:

1. Why am I receiving this?
2. What happened or why does it matter now?
3. What should I know or do?

Security/service messages lead with verified event and safe action. Marketing messages lead with recipient relevance/value. Outreach leads with honest identity and specific reason for contact.

Remove throat-clearing, brand autobiography, vague pleasantries and personalization that only proves database access.

## Message architecture

A common structure:

```text
context or outcome
-> useful detail / mechanism / proof
-> objection or reassurance
-> one primary action
-> required secondary/service information
```

Adapt it:

- **security:** verified event -> consequence -> safe action -> alternate support;
- **receipt/confirmation:** result -> essential details -> status/next step -> help;
- **onboarding:** promised outcome -> smallest value event -> guidance -> help;
- **education/nurture:** useful insight -> mechanism/example -> implication -> low-friction next step;
- **promotion:** relevant outcome -> offer/proof/terms -> objection -> CTA;
- **renewal/dunning:** account/status -> deadline/consequence -> resolution -> support;
- **feedback:** why their input matters -> effort/privacy -> request -> closure expectation;
- **outreach:** who/why them -> plausible problem/value -> evidence -> easy reply/decline.

If the email cannot name one dominant recipient decision, reassess whether it should be one message.

## Audience-message-offer fit

Audit:

- eligibility and problem specificity;
- desired outcome and real urgency source;
- mechanism or reason to believe;
- evidence near the point of doubt;
- differentiation from alternatives, including doing nothing;
- who is not a fit;
- offer contents, eligibility, price, renewal, limits and expiration;
- value versus requested effort/risk;
- language matching relationship, expertise and awareness;
- destination access, device, locale, currency and account state.

A feature is not a benefit until its recipient consequence is clear. A benefit is not credible until supported by mechanism, proof or relevant experience.

## Proof and claims

Classify each material claim:

| Claim | Evidence needed |
| --- | --- |
| Product behavior | Current product/source-of-truth documentation |
| Quantitative outcome | Defined measure, population, window and source |
| Customer quote/logo | Approval, accurate attribution and permitted use |
| Scarcity/deadline | Real inventory/policy/time-zone evidence |
| Security/privacy | Reviewed technical/legal statement |
| Comparison/superlative | Current, like-for-like substantiation |
| Personalization | Reliable first-party context and safe fallback |

Do not invent proof, testimonials, referrals, customer status, activity, urgency or exclusivity. Replace unsupported certainty with a verifiable statement or placeholder.

## Personalization

Meaningful personalization changes relevance, content, timing or next action. Audit:

- source and freshness;
- whether the person expects this use;
- fallback for missing/incorrect values;
- role/account/locale/time-zone correctness;
- sensitive inference or creepy specificity;
- consistency across subject, body and destination;
- whether a human could explain why the data was used.

`Hi {{first_name}}` is token substitution, not evidence of fit. Do not reveal private behavior in subject/preheader or use unverifiable “I noticed” claims.

## CTA and friction

A strong primary CTA:

- describes the resulting action/value;
- matches the stage and promised destination;
- requests an appropriate commitment;
- is visually and verbally dominant;
- has reassurance near the relevant objection;
- remains understandable as text and outside styling;
- has a working fallback/support path when the action is critical.

Inspect:

- competing primary actions;
- vague labels such as “Learn more” without context;
- destination, redirects, price/terms and account/login state;
- form length, mobile usability, performance and localization;
- expired event/offer or already-completed action;
- risk of accidental/state-changing clicks;
- back path, confirmation and error recovery.

Secondary navigation, social links and preferences should not visually compete with the job.

## Voice and trust

Check:

- stable sender identity and appropriate From name;
- clear reply/support expectations;
- accurate terms and transparent sponsorship/advertising;
- tone proportional to security, loss, money, health or urgency;
- human language without forced intimacy;
- no shame, threat, coercion or manufactured fear;
- no euphemism that hides cost, renewal, data use or consequence;
- consistency with actual product/support experience.

Concise is not automatically clear. Keep detail necessary for informed action and remove detail that serves the sender rather than the decision.

## Scannability and accessibility

- front-load context and outcome;
- use descriptive headings and link text;
- keep paragraphs decision-sized;
- make lists parallel and purposeful;
- explain jargon/acronyms for the audience;
- put critical text outside images;
- preserve logical reading order;
- support long names, localization and RTL;
- make errors, deadlines and security instructions explicit.

Use [html-accessibility-and-message-security.md](html-accessibility-and-message-security.md) for markup, clients, dark mode, alt treatment and security review. Readability formulas are weak proxies; inspect actual audience language and task completion.

## Rewrite method

1. State the current strategic problem in one sentence.
2. Define recipient state before and after.
3. List verified facts, required content, prohibited claims and unknowns.
4. Choose one message architecture.
5. Rewrite From/subject/preview together.
6. Fulfill that promise in the opening.
7. Support one main decision with proof, terms and reassurance.
8. Make CTA/destination continuity explicit.
9. Preserve service, accessibility, identity and opt-out content.
10. Re-audit the result against the message job and sequence.

When information is missing, use visible placeholders such as `[verified deadline]`; never silently fabricate.

## Variant design

Each variant should test one causal idea:

- outcome framing versus mechanism framing;
- direct offer versus objection-first;
- social proof versus product proof;
- smaller activation step versus full commitment;
- plain-text personal style versus designed editorial style, when audience and job justify it.

Keep sender, audience, offer, timing, destination and all non-hypothesis content stable. Define the primary job metric and harm guardrails before writing variants.

## Finding format

```text
Observed words/layout/destination
-> recipient interpretation at this lifecycle state
-> likely decision friction or trust effect
-> specific revision
-> evidence needed to verify
```
