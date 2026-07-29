# Consent, preferences, and compliance analysis

Use this reference for marketing permission, list source, unsubscribe, cold outreach, mixed transactional/promotional mail, jurisdiction-sensitive requirements, or provider-policy compliance. This is an evidence audit, not legal advice.

## Classify before applying rules

Determine from the recipient’s reasonable perspective:

- sender and every entity promoted;
- recipient and sender locations;
- message’s primary and secondary purposes;
- whether the message was requested or triggered by the recipient;
- individual/consumer, sole trader, corporate or other recipient status where relevant;
- existing customer, prospect, member, donor, employee or other relationship;
- address source, collection notice and consent/legal-basis evidence;
- whether promotion is incidental or dominates essential service content.

Internal labels do not control. A receipt with a large upsell can be mixed or commercial. A password reset is not permission for a newsletter. “B2B” does not create a universal exemption.

## Evidence ledger

For each list/recipient cohort, capture:

| Field | Evidence |
| --- | --- |
| Address source | First-party form, checkout, event, partner, CRM, public source, import |
| Collection event | Timestamp/time zone, form/page/version, exact notice and affirmative action |
| Scope | Brand/entity, channel, message purposes, products and frequency represented |
| Relationship | Purchase/service/membership/inquiry and relevant dates |
| Confirmation | Verification/confirmed opt-in event and address-change handling |
| Jurisdiction/status | Recipient location and individual/corporate classification basis |
| Withdrawal | Unsubscribe/objection/complaint time, source and requested scope |
| Suppression | Global/list/brand scope, propagation status, vendor acknowledgement |
| Retention | Why evidence is retained, access, deletion schedule and processors |

Do not call consent “proven” from an `opt_in=true` column without the collection text, scope, time and provenance. Do not publish personal evidence in the audit; aggregate or redact.

## Permission and expectation review

Ask:

1. Did the person actively request this channel and purpose, or does a documented exception apply?
2. Did the named sender/brands and frequency match the collection notice?
3. Is the address still connected to the relationship and current expectation?
4. Can the sender demonstrate the basis?
5. Did a later unsubscribe, objection, complaint or suppression override it?
6. Are affiliates, resellers, sales users and processors applying the same current state?
7. Would a reasonable recipient recognize why they received this message?

Purchased, rented, appended, harvested and unexplained lists are high risk even when a vendor claims they are “compliant.” Address validity and public availability do not establish permission or wantedness.

## Unsubscribe and preference evidence

Inspect both visible experience and machine-readable behavior:

- clear, conspicuous body opt-out appropriate to message type;
- RFC 8058 one-click structure and covering DKIM evidence where required;
- no login, password, survey, fee or unnecessary steps;
- no preselected re-subscription or deceptive confirm-shaming;
- correct brand/list/global scope;
- idempotent processing and explicit success state;
- prompt propagation to ESPs, CRM, CDP, sales tools, affiliates and scheduled jobs;
- suppression before each send, including retries and queued campaigns;
- retained minimal proof of withdrawal without using the suppressed address for marketing;
- controlled, affirmative re-subscription with a new evidence event.

A preference center may offer choices but must not obstruct a full opt-out. Complaint feedback should usually trigger durable suppression even if a separate unsubscribe event is absent.

Use `scripts/inspect_email.py` for inspectable header structure. Do not test a recipient-specific URL without authorization; GET or POST can change state.

## Provider policy versus law

Keep separate columns:

| Layer | Question |
| --- | --- |
| Law/regulation | Is sending/processing permitted and are disclosures/rights satisfied? |
| Mailbox-provider rule | Does the stream meet authentication, complaint and opt-out requirements? |
| Contract/platform rule | Does the ESP/list vendor/customer agreement allow it? |
| Recipient expectation | Is it wanted, recognizable and appropriately timed? |

Meeting one layer does not establish the others. A legally arguable cold message can still violate provider/ESP rules, generate complaints and be inappropriate.

## Jurisdiction routing

The following summaries were checked against primary regulator sources on 2026-07-29. Laws and guidance change; verify the actual recipient/sender facts and current source before a conclusion.

### United States: CAN-SPAM

The [FTC CAN-SPAM compliance guide](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business) applies to commercial email, including business-to-business email. Review:

- accurate header/routing and From/Reply-To information;
- non-deceptive subject;
- required advertisement identification where applicable;
- valid physical postal address;
- clear opt-out and honoring it within the current statutory period;
- responsibility for vendors and messages sent on another entity’s behalf;
- primary-purpose rules for mixed commercial, transactional and other content.

Do not infer consent from CAN-SPAM’s opt-out framework or claim all US privacy/consumer obligations are covered.

### United Kingdom: PECR and data protection

The ICO’s [direct marketing using electronic mail guidance](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guidance-on-direct-marketing-using-electronic-mail/) explains that unsolicited marketing to individual subscribers normally needs valid consent unless a specific soft opt-in applies. Review:

- subscriber type and whether it is genuinely corporate;
- freely given, specific, informed, unambiguous affirmative consent;
- exact sender/purpose/channel scope and evidence;
- product/service soft opt-in conditions and opt-out offered at collection and every message;
- the charitable-purposes soft opt-in introduced through 2025 legislation and reflected in April 2026 guidance, if applicable;
- identity, easy objection/withdrawal and suppression;
- UK GDPR lawful basis, transparency, data minimization and individual business-contact data even where PECR corporate rules differ.

Publicly available contact details are not automatically consent. Sole traders and some partnerships are treated differently from corporate subscribers. Use current ICO examples and obtain counsel for borderline status/basis.

### European Union/EEA

[Article 13 of the ePrivacy Directive](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02002L0058-20091219) sets the electronic-mail direct-marketing framework, while national implementation and regulator interpretation determine practical requirements. GDPR can separately govern personal-data collection, profiling, lawful basis, transparency, processors, international transfers, retention and rights.

Identify every relevant member state and consult its regulator/current law. Do not generalize one country’s soft-opt-in, B2B or enforcement rules across the EU/EEA.

### Canada: CASL

The [CRTC CASL guidance](https://crtc.gc.ca/eng/internet/anti/reg.htm) centers on prior express or qualifying implied consent, sender/contact identification and a working unsubscribe mechanism for commercial electronic messages. Review:

- commercial purpose, including requests for consent;
- express versus time/context-limited implied-consent basis;
- who bears proof and what the consent record contains;
- every person on whose behalf the message is sent;
- unsubscribe function and timely processing;
- cross-border messages received in Canada and applicable exemptions.

Do not treat a business card, inquiry, published business address or existing relationship as blanket permission; apply the detailed CRTC conditions to the facts.

### Australia

The Australian Communications and Media Authority’s [spam compliance guidance](https://www.acma.gov.au/avoid-sending-spam) covers consent, sender identification/contact details and a functional unsubscribe for commercial electronic messages. Review express/inferred consent, address harvesting/list supply, five-business-day unsubscribe handling and responsibility for third parties against current ACMA guidance.

### Other jurisdictions

For any other recipient or sender location:

1. identify the responsible regulator and controlling statute;
2. use primary, current government/regulator sources;
3. distinguish sending rules from data-protection, consumer, sector and employment rules;
4. record translation/localization and local entity/address requirements;
5. escalate uncertainty to qualified counsel.

Do not claim a “global compliant footer.” Requirements depend on purpose, parties, relationship, location, sector and processing.

## Special message classes

### Transactional, service and security

- send only information necessary for the requested transaction/service/security event;
- lead with essential action, deadline and verified context;
- keep promotion absent or clearly subordinate;
- apply marketing suppressions to promotional modules without blocking legally/contractually required service communication;
- avoid exposing secrets or sensitive facts in subject/preheader;
- provide a legitimate support/recovery path.

### Sales outreach

- require documented, reviewable sourcing and relevance;
- never fabricate prior contact, referrals, research or urgency;
- identify the sender and purpose plainly;
- honor objections and opt-outs across sales tools and future sequences;
- apply jurisdiction, provider and ESP restrictions before sending;
- bound frequency and exit on nonresponse.

Do not optimize unwanted scale. If sourcing or permission is unknown, recommend stopping and resolving it.

### Re-engagement and re-permission

- confirm the previous relationship and age;
- use a bounded number of attempts;
- avoid treating nonresponse as renewed consent;
- stop/sunset when the relationship is no longer credible;
- do not email someone who already opted out merely to request opt-in again unless counsel confirms a valid exception.

### Referral, “forward to a friend,” and imported contacts

The referring user cannot normally grant the friend’s consent for the sender. Avoid collecting third-party addresses for marketing without a valid jurisdiction-specific basis. Analyze who instigates the message, what the friend expects and whether any one-time service exemption actually applies.

### Sensitive sectors and minors

Financial, health, education, employment, political, gambling, alcohol and child-directed messages may add sector, age, confidentiality, fairness and recordkeeping duties. Escalate before rewriting claims or recommending targeting.

## Audit output

```markdown
## Scope
- Sender/promoted entities:
- Recipient jurisdictions/status:
- Message classification:
- Sources checked and date:

## Evidence matrix
| Requirement | Evidence | Status | Confidence | Missing proof |

## Highest-risk gaps
1. [Observed gap]
   - Why it matters:
   - Containment:
   - Owner/evidence needed:

## Suppression flow
[collection -> consent ledger -> send eligibility -> unsubscribe/complaint -> global propagation]

## Legal review required
- [fact-sensitive question; do not provide a definitive legal answer]
```
