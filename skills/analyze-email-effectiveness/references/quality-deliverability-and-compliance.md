# Quality, deliverability, and compliance triage

Use this reference as the cross-layer checklist. Route into the specialized reference instead of collapsing everything into “spam.”

## Evidence boundaries

| Layer | Artifact can show | Stronger evidence needed |
| --- | --- | --- |
| Strategy/copy | Promise, hierarchy, CTA, visible expectation | Audience research, offer/destination and sequence |
| MIME/HTML | Parts, headers, links, attachments, markup signals | Production raw message and client tests |
| Authentication | Claimed identities in raw headers | DNS plus trusted receiver or cryptographic results |
| Placement/reputation | Almost nothing from content alone | SMTP, provider dashboard, complaint, ESP and controlled tests |
| Consent/compliance | Visible identity/opt-out language | Source, consent, jurisdiction and suppression records |
| Performance | Supplied counts/rates | Stable definitions, denominators, assignment and downstream events |

Use `unknown`, not `fail`, for missing evidence.

## Routing

- DNS, SPF, DKIM, DMARC, BIMI, PTR, DNSSEC, MTA-STS, TLS-RPT or DANE -> [email-dns-and-authentication.md](email-dns-and-authentication.md)
- Raw message, one-click, HTML, client rendering, accessibility, links, attachments or privacy -> [html-accessibility-and-message-security.md](html-accessibility-and-message-security.md)
- Inbox/spam, block, deferral, receiver dashboard, complaint or recovery -> [reputation-and-placement-diagnostics.md](reputation-and-placement-diagnostics.md)
- Address source, cold outreach, consent, unsubscribe, legal basis or jurisdiction -> [consent-and-compliance.md](consent-and-compliance.md)
- Rates, attribution, diagnosis or experiments -> [measurement-and-experiments.md](measurement-and-experiments.md)

## Integrated review

### Expectation and audience

- recognizable sender and reason for receiving;
- documented source, collection promise and relationship;
- correct segment, lifecycle state and frequency;
- bounded re-engagement and explicit exits;
- no purchased, scraped, appended or unexplained list;
- complaint, unsubscribe and inactivity suppression.

### Message and destination

- truthful From/subject/preview/body continuity;
- one clear job and dominant action;
- proof, terms and urgency supported;
- destination matches CTA, product, price and expected login state;
- no hidden or obstructed opt-out;
- essential service content not contaminated by dominant promotion.

### Technical artifact

- valid final MIME with text alternative;
- meaningful content when images are blocked;
- accessibility and localization evidence;
- stable HTTPS destinations and reviewed redirect chain;
- no unexpected active content, deceptive link labels, Unicode controls or risky attachments;
- RFC 8058 structure where applicable.

### Identity and authentication

- exact Header From, MAIL FROM, DKIM `d=`/`s=`, IP and HELO identified;
- SPF/DKIM result plus DMARC alignment from real receiver evidence;
- current RFC 9989 policy discovery and legacy compatibility considered;
- every active source represented in inventory/reports;
- PTR/forward confirmation for outbound IPs;
- DNS/keys rotated safely without breaking active senders.

### Reputation and operations

- receiver-specific SMTP and dashboard evidence;
- complaints/bounces/deferrals by provider and stream;
- domain, IP, shared pool, DKIM and link identities separated;
- change-point review for volume, list, ESP, pool, template and DNS;
- controlled placement evidence interpreted directionally;
- no identity rotation, engagement manufacturing or filter evasion.

### Measurement

- counts, denominator and window for every rate;
- provider-specific definitions retained;
- opens/clicks corrected or caveated for privacy proxies/scanners;
- downstream job metric and guardrails;
- comparable cohorts or randomized assignment;
- effect size and uncertainty, not significance alone.

## Triage order

When results are poor:

1. confirm whether the symptom is rejection, deferral, accepted delivery, placement, engagement or conversion;
2. isolate provider, stream, domain/DKIM identity, IP, cohort and onset;
3. contain compromised, nonconsensual or high-complaint sources;
4. inspect SMTP/provider/suppression evidence;
5. verify real-message authentication and DNS configuration;
6. inspect message/destination/accessibility quality;
7. analyze list expectation, offer and lifecycle fit;
8. run a controlled test only after measurement and operational faults are addressed.

## Anti-patterns

Do not:

- produce a trigger-word spam score;
- say MX records identify outbound senders;
- say a guessed selector’s NXDOMAIN means no DKIM;
- claim `p=reject` means every receiver rejects failures;
- treat a DMARC pass as safety, quality or inbox placement;
- treat opens as people or clicks as humans without qualification;
- recommend hiding unsubscribe or moving unwanted traffic to fresh domains/IPs;
- call address validation consent;
- use a legal footer as proof of legal compliance;
- promise a fixed “warm-up” or reputation-recovery schedule.

## Final finding format

For each material issue:

```text
layer + identity/provider/scope
-> observed evidence and source/time
-> impact on the email's actual job
-> recommendation and owner
-> verification evidence
-> confidence and remaining unknowns
```
