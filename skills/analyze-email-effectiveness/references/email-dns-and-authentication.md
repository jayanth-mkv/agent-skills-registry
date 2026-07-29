# Email DNS, authentication, and transport evidence

Use this reference for sender identity, spoofing protection, DNS-related deliverability risk, branded infrastructure, and inbound transport policy. This workflow is read-only. A proposed record must still be reviewed in the actual sender inventory and change process.

## Identity map

Never assume one domain controls every check.

| Identity | Best evidence | What it governs |
| --- | --- | --- |
| Author/Header From domain | Exactly one RFC 5322 `From:` mailbox domain | DMARC policy and alignment; BIMI |
| SPF domain | SMTP `MAIL FROM`; HELO only when MAIL FROM is null | SPF transaction and DMARC SPF alignment |
| DKIM Signing Domain | `d=` on a DKIM signature that actually validates | DKIM responsibility and DMARC DKIM alignment |
| DKIM selector | `s=` paired with its `d=` | Public-key DNS name |
| Sending host | Connecting IP and HELO/EHLO from receiver/SMTP evidence | PTR, forward confirmation, HELO consistency, IP reputation |
| Recipient policy domain | Domain accepting the message | MX, MTA-STS, TLS-RPT, DANE/TLSA |
| Branded infrastructure | Return-path, tracking, image, link and verification names | Provider-specific CNAME/TXT/A/AAAA evidence |

A visible From domain can pass DMARC through aligned DKIM when the return-path is unaligned. An SPF record can be valid while a particular IP fails. A valid DKIM key can exist while a message is unsigned or its signature fails.

## Preferred workflow

Use the raw message to avoid selector guessing:

```bash
python -m pip install -r scripts/requirements.txt
python scripts/audit_email_dns.py example.com \
  --message received.eml \
  --sending-ip 192.0.2.25 \
  --helo-domain mail.example.com \
  --format json
```

The message contributes claimed Header From, Return-Path, and DKIM `d=`/`s=` identities; it does not make those claims trusted or verify a signature. Add every outbound IP and every active/rotating selector known from receiver results or provider configuration.

Without a raw message:

```bash
python scripts/audit_email_dns.py example.com \
  --header-from-domain news.example.com \
  --mail-from-domain bounce.example.com \
  --dkim current@example.com \
  --dkim rotating@example.com \
  --sending-ip 192.0.2.25 \
  --sending-ip 2001:db8::25 \
  --helo-domain mail.example.com \
  --org-domain example.com \
  --fetch-mta-sts \
  --format json
```

Useful controls:

- `--discover-dkim` / `--no-discover-dkim`: bounded candidate probes; enabled by default;
- `--bimi-selector`: repeat for non-default selectors;
- `--query NAME:TYPE`: provider-specific bounce, tracking, delegation, verification, CAA, SRV, or other records;
- `--fixture zone.json`: offline and reproducible evidence;
- `--mta-sts-policy-file`: inspect captured policy without HTTP;
- `--fetch-mta-sts`: HTTPS fetch with redirects disabled, private-address controls, and a response-size cap;
- `--resolver`, `--tcp`, `--timeout`, `--max-queries`: resolver controls;
- `--fail-on warning|error`: CI policy; normal execution is report-only.

### Fixture format

Keys are `<normalized-name>|<TYPE>`. Missing keys mean no data. CNAME following is bounded.

```json
{
  "records": {
    "example.com|MX": {
      "status": "ok",
      "values": ["10 mx1.example.com."],
      "ttl": 300,
      "ad": true
    },
    "bounce.example.com|TXT": ["v=spf1 include:_spf.example.net -all"],
    "_dmarc.example.com|TXT": ["v=DMARC1; p=reject; rua=mailto:dmarc@example.com"],
    "selector._domainkey.example.com|CNAME": ["selector.keys.provider.example."],
    "selector.keys.provider.example|TXT": ["v=DKIM1; k=rsa; p=BASE64_PUBLIC_KEY"]
  }
}
```

Preserve collection time, recursive resolver, location, TTL and source. A fixture is a snapshot, not a zone-file parser.

## DNS and routing inventory

The helper covers:

- apex A/AAAA, MX, NS, SOA and CAA;
- MX priority, target syntax, addressability and prohibited MX-to-CNAME aliases;
- RFC 7505 Null MX (`0 .`) and conflicts;
- implicit MX behavior when no MX exists;
- custom records for provider delegations and branded subdomains.

MX describes advertised inbound handling. It normally says nothing about outbound marketing infrastructure. CAA limits certificate-authority issuance; it is not an email-authentication control. NS/SOA ownership signals do not prove sender ownership.

## SPF

Check the actual SPF domain, not automatically the Header From domain.

The toolkit analyzes:

- exactly one `v=spf1` policy;
- mechanism/modifier syntax and unreachable terms;
- `ip4`, `ip6`, `a`, `mx`, `include`, `exists`, `redirect`, `all`, deprecated `ptr`, and dangerous `+all`;
- recursive dependency graph, missing targets and cycles;
- static DNS-query-term exposure, void candidates and oversized MX expansion;
- depth and global query safeguards.

[RFC 7208](https://www.rfc-editor.org/rfc/rfc7208.html) limits evaluated DNS-querying terms to 10 and recommends limiting void lookups to two. Static expansion cannot reproduce macro expansion or the exact evaluation path without client IP, HELO, full sender, receiver and time. Treat static budget findings as risk unless a complete transaction evaluator establishes `permerror`.

For a definitive SPF result, obtain the connecting IP, SMTP MAIL FROM (including null sender behavior), HELO, receiver result and timestamp. SPF usually breaks on forwarding; that alone does not establish DMARC failure if aligned DKIM survives.

## DKIM

The exact DNS name is:

```text
<s>._domainkey.<d>
```

The toolkit checks explicit/message-derived identities plus positive bounded candidate discovery:

- direct TXT or provider CNAME targets;
- multiple, absent, revoked or malformed keys;
- version, duplicate tags, service and hash restrictions;
- testing/strict-identity flags;
- RSA DER key size and Ed25519 key length.

Per [RFC 8301](https://www.rfc-editor.org/rfc/rfc8301.html), verifiers must reject RSA keys below 1024 bits and senders should use at least 2048 bits. A 1024-bit record can therefore be valid but legacy-strength. Plan selector rotation based on provider/DNS limits rather than overwriting an active key.

DNS has no selector-list operation. The discovery probe uses common names and provider signals from MX/SPF only to find positives. “No candidate found” is inconclusive. Obtain exact selectors from:

1. a current message received at a controlled mailbox;
2. receiver/provider authentication results inside a trusted boundary;
3. sender configuration or DNS change inventory;
4. DMARC aggregate selector evidence under RFC 9990.

To establish DKIM pass, cryptographically verify the pristine raw message or rely on a trusted receiver result. Merely parsing `DKIM-Signature` or finding its key does not establish pass.

## DMARC: current and compatibility interpretation

[RFC 9989](https://www.rfc-editor.org/rfc/rfc9989.html), published May 2026, is the current Standards Track DMARC specification and obsoletes RFC 7489 and RFC 9091.

Current processing:

- queries the exact Author Domain first;
- uses a bounded DNS Tree Walk, never more than eight policy queries;
- determines Organizational Domain using valid records plus `psd=y` or `psd=n`, not a public suffix list;
- can apply `p`, inherited `sp`, or inherited nonexistent-domain `np`;
- uses `t=y` to lower expected enforcement one level for testing;
- treats omitted `p` as `none`;
- treats invalid assessment tags with a syntactically valid `rua` as a `p=none` reporting fallback; without that report URI, DMARC processing does not apply;
- ignores unknown tags.

`pct`, `rf`, and `ri` were removed from RFC 9989. The toolkit reports them separately because deployed receivers and provider documentation can still use RFC 7489-era behavior. `--org-domain` supplies a legacy/public-suffix expectation solely for comparison. Preserve both conclusions when they differ; do not silently choose the result that looks stronger.

DMARC pass requires either:

```text
SPF pass for the SMTP MAIL FROM identity + required alignment
OR
DKIM pass for at least one d= identity + required alignment
```

Strict alignment requires identical domains. Relaxed alignment uses Organizational Domains discovered by the applicable method. Candidate identity alignment is not an authentication result.

The toolkit also checks:

- record multiplicity and tag syntax;
- `adkim`, `aspf`, `fo`, `rua`, `ruf`, `p`, `sp`, `np`, `psd`, and `t`;
- external report-destination authorization at `<policy-domain>._report._dmarc.<destination>`;
- current effective policy plus legacy-tag interpretation;
- Author Domain existence evidence used for `np`.

DNS errors are different from authenticated nonexistence/no-data. Report transient ambiguity rather than treating it as no policy.

## DMARC aggregate and failure reports

[RFC 9990](https://www.rfc-editor.org/rfc/rfc9990.html) defines current aggregate reporting; [RFC 9991](https://www.rfc-editor.org/rfc/rfc9991.html) defines failure reporting. Current aggregate XML uses the `urn:ietf:params:xml:ns:dmarc-2.0` namespace and can include Tree Walk discovery and DKIM selector fields. Legacy reports remain operationally common.

```bash
python scripts/parse_dmarc_reports.py reports/ --format json
```

For each source/stream:

1. identify owner from a maintained sender/IP/provider inventory;
2. compare Header From, envelope domain, DKIM domain/selector and alignment;
3. separate authorized misconfiguration, forwarding/intermediary effects, unknown source and likely unauthorized use;
4. trend weighted message counts, not just XML row counts;
5. verify changes in later reports and receiver dashboards.

Aggregate reports are sampled receiver observations, not a complete sending inventory, abuse verdict, complaint feed or inbox-placement report. Failure reports can contain personal/message data; minimize access and retention.

## BIMI

The toolkit checks selector TXT syntax, HTTPS `l=`/`a=` locations, and DMARC-policy evidence. Also verify separately:

- current participating-provider eligibility;
- SVG Tiny Portable/Secure profile and response headers;
- redirects and asset availability;
- VMC/CMC certificate chain and mark claims where applicable;
- selector/header behavior and logo display at each provider.

[BIMI Group’s implementation guide](https://bimigroup.org/implementation-guide/) is operational guidance. BIMI is optional, provider-dependent and never substitutes for SPF, DKIM or DMARC. Logo display is not guaranteed.

## Inbound transport policy

These controls primarily protect mail delivered **to** the audited domain:

- [MTA-STS, RFC 8461](https://www.rfc-editor.org/rfc/rfc8461.html): `_mta-sts` signaling plus HTTPS policy and MX matching;
- [TLS-RPT, RFC 8460](https://www.rfc-editor.org/rfc/rfc8460.html): `_smtp._tls` report destination;
- [SMTP DANE, RFC 7672](https://www.rfc-editor.org/rfc/rfc7672.html): DNSSEC-secured TLSA at `_25._tcp.<mx-host>`.

They do not authenticate marketing mail sent from the domain. DNS alone does not prove STARTTLS support, negotiated protocol/cipher or the certificate presented on port 25. MTA-STS and DANE can coexist; receiver support and DNSSEC state matter.

## DNSSEC, PTR and HELO

The toolkit inventories DS, DNSKEY, CDS and CDNSKEY, and records the recursive resolver’s Authenticated Data signal. Presence is not proof of a valid DNSSEC chain. An AD bit is meaningful only through a trusted resolver path or local validation. DANE requires a secure TLSA result.

For every actual outbound IP:

1. query PTR;
2. resolve every returned hostname to A/AAAA;
3. verify the original IP appears;
4. compare the HELO/EHLO name and forward addresses;
5. check ownership/pool and provider dashboard evidence.

PTR is normally controlled by the IP provider. Shared-IP reputation cannot be inferred from one tenant’s domain. Missing sending IPs make the check incomplete.

## Evidence hierarchy and handoff

Prefer:

1. receiver SMTP responses and provider dashboards tied to time/stream;
2. pristine raw message plus trusted boundary results or independent verification;
3. exact SMTP identities and sending IP/HELO;
4. DMARC aggregate/TLS reports and ESP delivery events;
5. live DNS from multiple appropriate resolvers with timestamps/TTL;
6. provider configuration exports;
7. screenshots or copied record values.

Report:

- identities examined and how each was obtained;
- resolver, time, TTL, AD/error status and geographic limitations;
- RFC 9989 result and any legacy interpretation difference;
- exact selectors/IPs covered and missing;
- configuration findings versus real-message results;
- safe remediation order, rollback/rotation concerns and required owner;
- what still needs receiver/provider evidence.

Checked against primary standards and provider materials on 2026-07-29. Re-verify time-sensitive requirements at each audit.
