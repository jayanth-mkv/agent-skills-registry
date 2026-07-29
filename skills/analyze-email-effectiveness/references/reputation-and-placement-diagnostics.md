# Reputation and inbox-placement diagnostics

Use this reference for “Will this land in spam?”, sudden delivery drops, receiver-specific filtering, throttling, blocks, or reputation recovery. There is no universal reputation lookup or content-only placement score.

## Define the observed failure

First distinguish:

| Observation | Meaning | First evidence |
| --- | --- | --- |
| SMTP hard rejection | Receiver did not accept the message | Full SMTP enhanced status, text, receiver, IP, time |
| SMTP temporary deferral/throttling | Receiver requested retry | Retry history, queues, exact 4xx response and duration |
| ESP says delivered | Destination server accepted it | ESP event and response; folder is still unknown |
| Seed arrived in spam | One controlled mailbox/client observation | Seed design, provider/account age, message identity and time |
| User says “went to spam” | Useful but anecdotal placement evidence | Raw received message and account/provider context |
| Provider dashboard shows degradation | Receiver-generated aggregate signal | Dashboard scope, denominator, date and affected stream |
| Low opens | Ambiguous engagement/measurement signal | Click/downstream events, privacy/client mix, placement evidence |
| No message received | Could be block, suppression, queue, typo or filtering | Sender log, suppression lookup, SMTP event and recipient |

Never describe server acceptance as inbox delivery. Never infer placement from open rate alone.

## Keep reputation identities separate

Receivers can assess several overlapping units:

- connecting IP and IP range;
- dedicated versus shared pool;
- HELO/EHLO and PTR identity;
- Header From/DMARC Organizational Domain;
- DKIM `d=` domain and selector behavior;
- envelope/return-path domain;
- link, redirect and asset domains;
- campaign/list/feedback identifiers;
- sender/user relationship and recipient-specific engagement;
- content/template, attachment and behavioral patterns.

A “domain is good” conclusion is incomplete unless the evidence says which identity, receiver, stream and time window it covers. On shared infrastructure, provider/neighbor behavior can affect IP evidence while domain evidence remains distinct.

## Evidence ladder

Use the strongest available receiver-specific layers:

1. **SMTP transaction evidence** — exact status code/text, receiving MX, IP, attempt/retry time.
2. **Mailbox-provider dashboards** — compliance, spam complaints, authentication, delivery errors, feedback-loop data.
3. **Complaint/FBL and ESP events** — complaints, hard/soft bounces, suppressions, deferrals and accepted events with stable event definitions.
4. **DMARC aggregate reports** — receiver-observed source/alignment trends; run `scripts/parse_dmarc_reports.py`.
5. **Sender inventory/change log** — domains, selectors, IP pools, vendors, stream, volume, acquisition source and deployment changes.
6. **Controlled placement tests** — repeated, representative seeds across providers plus real-recipient outcome evidence.
7. **Blocklist evidence** — exact IP/domain/list, listing reason/time and whether the receiver actually uses it.
8. **Message/DNS review** — necessary configuration and quality context, but weak direct placement evidence.

Preserve raw exports, date/time zone, denominator, provider scope, domain/IP/stream and comparison period.

## Current receiver requirements

These are operational summaries checked 2026-07-29; verify the linked primary source during each audit.

### Gmail

[Google’s email sender guidelines](https://support.google.com/mail/answer/81126) distinguish all senders from senders of roughly 5,000 or more messages to personal Gmail accounts in one day.

For all senders, review SPF or DKIM, valid forward/reverse DNS, TLS, RFC 5322 formatting and user-reported spam below the stated 0.3% requirement. Bulk senders additionally need SPF and DKIM, DMARC, alignment, one-click unsubscribe for marketing/subscribed messages and timely opt-out processing. Google recommends staying below 0.1% spam and avoiding 0.3% or higher.

[Postmaster Tools dashboards](https://support.google.com/mail/answer/14668346) are receiver evidence for personal Gmail traffic. Note:

- data is delayed and can take longer than 24 hours;
- low volume can produce privacy-driven gaps;
- some dashboards rely on DKIM-authenticated traffic;
- complaint rate uses Gmail’s provider-specific denominator and can look deceptively low when mail is already filtered;
- compliance status can aggregate subdomains into a primary-domain result;
- dashboard recovery can lag a configuration change by days.

Use current Compliance, Deliverability analysis, Authentication, Spam Rate, Feedback Loop, Encryption and Delivery Errors views. Do not transpose Gmail rates onto another provider.

### Yahoo and AOL

[Yahoo Sender Requirements & Recommendations](https://senders.yahooinc.com/best-practices/) require authentication, valid forward/reverse DNS, standards-conforming mail and complaint control for all senders; bulk senders must also use SPF and DKIM, publish DMARC, support alignment, provide RFC 8058 one-click plus a visible body unsubscribe, honor unsubscribe within two days, and separate marketing from transactional streams.

[Yahoo’s Complaint Feedback Loop](https://senders.yahooinc.com/complaint-feedback-loop/) is DKIM-domain based. Enroll the applicable signing domains through Sender Hub or verify that the ESP processes the reports, then suppress complainants promptly. Absence of a feedback report is not proof of no complaints.

### Outlook.com, Hotmail and Live

[Microsoft’s high-volume sender requirements](https://techcommunity.microsoft.com/blog/microsoftdefenderforoffice365blog/strengthening-email-ecosystem-outlook%E2%80%99s-new-requirements-for-high%E2%80%90volume-senders/4399730) apply SPF, DKIM and DMARC expectations to domains sending more than 5,000 messages per day to Outlook.com consumer services. Also review valid sender/reply addresses, unsubscribe and transparent list practices.

Use [Smart Network Data Services](https://substrate.office.com/ip-domain-management-snds/snds) for eligible IP-level traffic data and [Outlook.com sender support](https://support.microsoft.com/en-us/outlook/sender-support-in-outlook-com) for troubleshooting/escalation routes. Confirm whether the operator or ESP owns SNDS/JMRP access, especially on shared IPs.

### iCloud Mail

[Apple’s iCloud Mail postmaster guidance](https://support.apple.com/en-us/102322) requires explicit subscription for bulk mail, immediate unsubscribe, standards conformance, reverse DNS, stable identities/infrastructure, separation of marketing and transactional streams, SPF/DKIM use, and a published DMARC policy; it also describes escalation evidence.

Apple does not expose the same public dashboard model as Gmail. Use SMTP responses, controlled recipient evidence, authentication, list/complaint data and the documented postmaster escalation route.

## Complaint and list-quality diagnosis

Review:

- acquisition source and exact promise shown at collection;
- confirmed address/opt-in evidence where applicable;
- age since collection and last meaningful action;
- sudden imports, merges, re-permission campaigns or old CRM sources;
- role, typo, disposable and invalid-address handling;
- hard-bounce, complaint, unsubscribe and global-suppression behavior;
- frequency cap, preference center and cross-brand/cross-product scope;
- inactive-recipient policy and bounded re-engagement exit;
- spikes by form, partner, affiliate, campaign, segment or salesperson.

Complaint reduction is primarily an expectation and audience problem, not a subject-line word problem. Never recommend hiding unsubscribe, rotating identities to outrun reputation, or continuing to nonresponders indefinitely.

## Volume and infrastructure changes

Correlate the incident with:

- new IP/domain/subdomain/DKIM selector/return-path/link domain;
- ESP or IP-pool migration;
- sharp volume, cadence or destination-mix change;
- marketing/transactional stream mixing;
- new list source or materially broader eligibility;
- authentication, DNS, template, redirect or landing-page change;
- retry behavior and queue backlog;
- compromised credentials, unauthorized sender or DKIM replay.

“Warm-up” should mean predictable scaling to wanted recipients while monitoring receiver evidence. It is not a technique for bypassing enforcement or rehabilitating unwanted lists. New domain/IP volume should follow demonstrated demand; do not manufacture engagement.

## SMTP response analysis

Record the complete response because the same numeric code can have receiver-specific meaning:

```text
timestamp
recipient provider and receiving MX
connecting IP / HELO / MAIL FROM / Header From / DKIM d=
SMTP basic + enhanced code
verbatim response text and provider help URL
attempt number, retry interval, final state
message/campaign/stream identifier
```

Group by provider, code, IP, domain, stream and hour. Separate policy blocks, authentication failures, rate limits, mailbox/full/user errors and infrastructure faults. Do not repeatedly retry permanent 5xx failures. Preserve evidence before changing multiple variables.

## Controlled placement tests

Seed tests are directional:

- use multiple established controlled accounts per relevant provider;
- send the production MIME through the production stream;
- preserve raw delivered messages and folder labels;
- repeat over time and include controls;
- do not train the mailbox during the test unless that behavior is part of the protocol;
- compare with real-recipient SMTP, complaint and downstream outcome data.

Small seed panels are not representative of individualized filtering, recipient history, corporate gateways or global placement. A seed vendor’s synthetic score is not a receiver verdict.

## Blocklists and reputation sites

For a listing, record exact queried IP/domain, list, result, time, published reason and delisting requirements. Use authoritative list operators such as the [Spamhaus checker](https://check.spamhaus.org/) rather than aggregator screenshots when possible.

A listing matters only in context:

- domain versus IP listing;
- shared versus dedicated infrastructure;
- production versus unrelated inbound host;
- active receiver usage;
- local policy and time lag;
- false positive or stale cache possibility.

Do not query unknown sites with sensitive addresses, message bodies or tracking tokens. Never promise delisting or placement from a single lookup.

## Causal triage

Work in this order:

1. Confirm the event and its denominator.
2. Identify affected receiver, stream, domain, DKIM identity and IP.
3. Compare onset with sender/list/infrastructure changes.
4. Inspect exact SMTP responses and provider dashboards.
5. Verify suppressions, complaints, acquisition and volume.
6. Validate message authentication using real received evidence plus DNS.
7. Analyze DMARC reports against the sender inventory.
8. Use controlled placement/content tests only to distinguish remaining hypotheses.
9. Change one causal layer at a time where possible and monitor the same evidence.

## Recovery plan

Prioritize:

1. stop unauthorized, compromised, surprising or clearly unwanted traffic;
2. honor complaints/unsubscribes and repair suppression propagation;
3. remove invalid sources and pause the affected acquisition path;
4. fix material authentication/identity/format errors with safe key/DNS rotation;
5. isolate transactional and marketing streams without disguising identity;
6. resume only to recently wanted, well-understood cohorts at supportable volume;
7. verify receiver-specific recovery over an appropriate window;
8. document the cause, control and recurrence monitor.

Recovery can lag remediation. Do not claim a fixed recovery duration.

## Placement verdict format

```markdown
## Verdict
[High/medium/low confidence; affected providers/streams; what is actually known.]

## Evidence
| Layer | Identity/provider/window | Observation | Strength |

## Most likely causes
1. [Cause]
   - Supports:
   - Contradicts/unknown:
   - Discriminating next check:

## Immediate containment
- [reversible action]

## Remediation and verification
- [owner, change, evidence to confirm, rollback concern]

## Cannot conclude
- [placement/reputation claim still unsupported]
```
