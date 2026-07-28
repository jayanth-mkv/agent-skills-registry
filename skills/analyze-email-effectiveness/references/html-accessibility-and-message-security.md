# Message structure, HTML, accessibility, and security

Use this reference for raw `.eml`, source/rendered HTML, screenshots, MIME, one-click unsubscribe, links, attachments, privacy, localization, client rendering, or accessibility. Observable signals are not security or compliance verdicts.

## Preserve the artifact chain

Different artifacts answer different questions:

| Artifact | What it can establish | What it misses |
| --- | --- | --- |
| Source template | Authoring logic, tokens and intended markup | ESP transforms, final headers, recipient rendering |
| Rendered pre-send MIME | Final parts/headers before transport | Provider rewriting and received results |
| Pristine received `.eml` | Actual headers, MIME, receiver additions and content | Other clients/accounts and earlier SMTP envelope unless logged |
| Client screenshot | Visual result in one viewport/theme/account | Hidden semantics, headers, other clients |
| Browser preview | Basic layout/content | Email-client CSS, image proxying and mailbox UI |

Record which one was inspected. When debugging, diff source -> rendered MIME -> received MIME -> client render instead of assuming the template was sent unchanged.

## Run the inspector

```bash
python scripts/inspect_email.py received.eml --format json
python scripts/inspect_email.py received.eml \
  --trusted-authserv-id inbound.example.net \
  --format json
python scripts/inspect_email.py template.html \
  --subject "Subject" \
  --preview "Preview" \
  --format json
```

The helper reports facts and review candidates:

- byte size, MIME parts, parser defects and attachments;
- From/Reply-To/Return-Path identity hints and claimed DKIM selectors;
- `Authentication-Results` with explicit trust-boundary status;
- list and feedback headers;
- RFC 8058 inspectable structure and claimed DKIM header coverage;
- languages, direction, headings, tables, viewport, linked stylesheets and active tags;
- image alt treatment and one-pixel candidates;
- link domains/schemes, URL-like label mismatches, shorteners, punycode, userinfo and bare IPs;
- invisible/bidirectional Unicode controls;
- attachment filename, media type, size, SHA-256 and review reasons.

It does not execute HTML, open URLs, render clients, scan malware, verify DKIM, test unsubscribe endpoints, infer intent, or expose URL query/fragment tokens in its report.

## RFC 5322 and MIME review

Inspect the final message, not only HTML:

- exactly one syntactically usable From identity for DMARC processing;
- Date and From fields, and a stable Message-ID for diagnostics;
- valid line folding and encoded headers;
- correct MIME-Version and Content-Type boundaries;
- `multipart/alternative` order and coherent plain/HTML equivalents;
- declared charset versus actual bytes;
- transfer encoding and attachment disposition/filename;
- no malformed nesting, truncation or accidental source/template leakage;
- consistent subject, preheader and visible first content.

Use [RFC 5322](https://www.rfc-editor.org/rfc/rfc5322.html), [RFC 2045](https://www.rfc-editor.org/rfc/rfc2045.html), and [RFC 2046](https://www.rfc-editor.org/rfc/rfc2046.html) for format questions. Parser acceptance is not full conformance, and conformance does not guarantee client rendering.

## Authentication result trust

[RFC 8601](https://www.rfc-editor.org/rfc/rfc8601.html) makes `Authentication-Results` meaningful only across an established administrative trust boundary. A sender can insert a forged header before delivery.

For analysis:

1. identify the receiving service/account that produced the raw message;
2. identify its documented or locally configured `authserv-id`;
3. supply only those IDs using `--trusted-authserv-id`;
4. distinguish the receiver’s newest trusted result from older or external headers;
5. treat ARC headers as claims until the ARC chain and trusted sealer policy are validated.

[RFC 8617](https://www.rfc-editor.org/rfc/rfc8617.html) ARC can preserve upstream authentication evidence through intermediaries, but ARC does not automatically override local policy or make original content trustworthy.

## One-click unsubscribe

For applicable subscription/marketing mail, inspect both provider requirements and [RFC 8058](https://www.rfc-editor.org/rfc/rfc8058.html).

Inspectable structure requires:

- one `List-Unsubscribe` field containing at least one HTTPS URI; optional non-HTTP/S URIs may coexist;
- one `List-Unsubscribe-Post` field with exactly `List-Unsubscribe=One-Click`;
- at least one **valid** DKIM signature whose `h=` covers both fields.

Operational review also requires:

- an opaque/hard-to-forge recipient-and-list identifier;
- an HTTPS POST that completes without cookies, HTTP authorization or other prior context;
- no HTTPS redirect;
- correct handling of both permitted POST encodings;
- prompt, durable and scope-correct suppression across vendors/streams;
- idempotent behavior and safe handling of repeated/automated requests;
- a visible body unsubscribe or preference path where provider/law expects it.

The inspector can confirm field counts, HTTPS syntax, exact POST value and *claimed* `h=` coverage. It cannot prove a valid covering signature, POST behavior or suppression propagation.

Never expose unsubscribe tokens in reports or open recipient-specific URLs casually. A GET may unsubscribe, validate an address or leak data.

## HTML rendering review

### Structural resilience

- meaningful content and action remain available when images are blocked;
- responsive behavior works at narrow widths and zoom;
- reading order matches the DOM and visual order;
- layout tables are distinguished with `role="presentation"` or `role="none"`;
- data tables use appropriate headers/relationships;
- external stylesheets, scripts, forms, iframes, video and unsupported interactive elements have fallbacks or are removed;
- URLs and assets remain HTTPS and stable through the production redirect chain;
- long URLs, names, translations, prices and dynamic content do not break layout;
- plain-text alternative preserves essential facts, action and opt-out information;
- payload and image dimensions are proportionate to the job.

Tables and inline styles remain common for email compatibility, but do not assume universal client behavior. Validate the actual production MIME in the user’s meaningful client/device matrix. [Can I email](https://www.caniemail.com/) is useful empirical compatibility data, not a normative standard or substitute for testing.

### Dark mode

Test light/dark variants in actual clients:

- foreground/background contrast after automatic color transformation;
- logos/icons with transparent backgrounds and sufficient edge separation;
- CSS color-scheme support and fallbacks;
- images containing text or fixed backgrounds;
- link and button state visibility;
- forced-color/high-contrast modes where relevant.

Do not declare dark-mode support from metadata alone; clients transform colors differently.

## Accessibility review

Use [WCAG 2.2](https://www.w3.org/TR/WCAG22/) principles as the baseline while accounting for email-client limitations:

- informative images have concise equivalent alt text;
- decorative images use empty alt;
- critical content is not image-only;
- language and direction are declared where supported;
- headings are meaningful and hierarchical;
- links and buttons describe purpose without relying on surrounding layout;
- visual order, source order and keyboard/focus order agree;
- color is not the only cue;
- text and interactive controls have adequate contrast, size, spacing and zoom behavior;
- motion/flashing is avoided or controllable;
- status, error, deadline and security instructions use plain language;
- localization, screen readers and high-contrast modes are included in the test matrix.

Do not count an empty alt as missing: it is correct for decorative content. Do not treat every table as a data table. Report what the artifact shows and what still needs assistive-technology/client testing.

## Link and destination integrity

For every meaningful link, compare:

```text
visible label
-> HTML href
-> tracking/redirect domain
-> final destination
-> TLS/domain ownership
-> page promise, login state and mobile behavior
```

Flag for review:

- label names one domain while href uses another;
- URL userinfo obscures the real host;
- bare IP, punycode/homograph risk, URL shortener or unrelated domain;
- insecure HTTP or unsupported scheme;
- open redirects or multi-hop tracking;
- query parameters containing recipient data, bearer tokens or secrets;
- CTA lands on a different product/action/price;
- expired, region-blocked, authenticated or broken destinations.

Do not automatically follow signed, one-time, unsubscribe, password-reset or recipient-specific links. Redact query and fragment values in reports. If live navigation is authorized, use a controlled account and record each redirect without completing state-changing actions.

## Unicode and identity deception

Invisible and bidirectional controls can be legitimate for right-to-left text but can also alter display. Review them in:

- From display name;
- subject and preview;
- URL-like link labels;
- filenames and attachment descriptions;
- security/action instructions.

Also compare display name, From, Reply-To, return-path, DKIM domain and linked domains. A different Reply-To or link domain can be legitimate; require business/provider evidence before calling it deceptive.

## Attachments and active content

Treat filename and media type as untrusted metadata. Review:

- executable/script, macro-enabled Office and archive extensions;
- extension/media-type mismatch or double extension;
- nested/password-protected archives;
- unusual size, unexpected attachment for the message job and social-engineering language;
- SHA-256 against an approved artifact inventory or authorized malware scanner;
- document links that request credentials or active content.

Never open or execute an untrusted attachment during an audit. The helper’s `malicious: null` is deliberate: extension/type signals cannot establish malware.

Security and service messages should not put secrets, full reset tokens, sensitive diagnoses, account balances or regulated data in subject/preheader because lock screens, notifications, logs and forwarding can expose them.

## Tracking and privacy

Inventory:

- remote images and one-pixel candidates;
- per-recipient links and parameters;
- third-party asset, analytics and redirect domains;
- disclosed purpose, consent/legal basis and retention;
- vendor/subprocessor and cross-border implications;
- whether the same outcome can be measured with less data.

[Apple Mail Privacy Protection](https://www.apple.com/legal/privacy/data/en/mail-privacy-protection/) can privately download remote content regardless of engagement, weakening opens, device/location and time-to-open inference. Other image proxies and security scanners add similar noise. Prefer downstream first-party events and clearly defined privacy-preserving measures.

## Client test matrix

Choose clients from actual audience data. At minimum vary:

- major receiver/webmail families;
- desktop and mobile apps;
- iOS/Android and relevant OS versions;
- light, dark and high-contrast/forced-color modes;
- images blocked and slow/offline loading;
- screen reader/keyboard/zoom where relevant;
- plain-text and forwarding/reply behavior;
- long localized content and RTL when supported.

For each defect capture client/version, viewport/theme, account type, raw Message-ID, screenshot, expected/actual behavior and severity. Avoid claiming “works everywhere.”

## Handoff

Report:

- artifact stage and hash/source;
- observed MIME/HTML/accessibility/security evidence;
- one-click structural versus operational status;
- trusted/untrusted authentication-result boundaries;
- client tests performed and untested matrix;
- sensitive links/tokens redacted;
- prioritized fix with fallback and verification method;
- unknowns that require rendering, endpoint, malware or receiver testing.
