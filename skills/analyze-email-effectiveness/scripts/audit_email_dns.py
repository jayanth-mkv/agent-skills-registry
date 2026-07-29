#!/usr/bin/env python3
"""Audit email-related DNS, authentication, identity, and transport-policy evidence."""

from __future__ import annotations

import argparse
import base64
import binascii
import ipaddress
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

DOMAIN_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
DNS_LABEL = re.compile(r"^[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9_])?$")
RECORD_TYPE = re.compile(r"^(?:[A-Z][A-Z0-9-]{0,15}|TYPE[0-9]{1,5})$")
SPF_LOOKUP_MECHANISMS = {"include", "a", "mx", "ptr", "exists"}
SPF_MECHANISMS = SPF_LOOKUP_MECHANISMS | {"all", "ip4", "ip6"}
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}
MAX_POLICY_BYTES = 1024 * 1024
MAX_MESSAGE_BYTES = 10 * 1024 * 1024
DMARC_POLICY_VALUES = {"none", "quarantine", "reject"}
DMARC_CURRENT_TAGS = {"v", "p", "t", "psd", "np", "sp", "adkim", "aspf", "rua", "ruf", "fo"}
DMARC_LEGACY_TAGS = {"pct", "rf", "ri"}
COMMON_DKIM_SELECTORS = (
    "default",
    "dkim",
    "google",
    "k1",
    "k2",
    "mail",
    "s1",
    "s2",
    "selector1",
    "selector2",
    "smtp",
    "zmail",
)
DKIM_PROVIDER_FINGERPRINTS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("Google-hosted mail hint", ("google.com", "googlemail.com"), ("google",)),
    (
        "Microsoft-hosted mail hint",
        ("outlook.com", "protection.outlook.com", "onmicrosoft.com"),
        ("selector1", "selector2"),
    ),
    (
        "Zoho-hosted mail hint",
        ("zoho.com", "zoho.eu", "zoho.in", "zohomail.com"),
        ("zmail", "zoho"),
    ),
    ("Fastmail-hosted mail hint", ("messagingengine.com",), ("fm1", "fm2", "fm3")),
    (
        "Proton-hosted mail hint",
        ("protonmail.ch", "protonmail.com"),
        ("protonmail", "protonmail2", "protonmail3"),
    ),
    ("SendGrid authorization hint", ("sendgrid.net",), ("s1", "s2")),
    ("Mailchimp authorization hint", ("mcsv.net", "mandrillapp.com"), ("k1", "k2", "mandrill")),
)


class AuditError(ValueError):
    """Raised for invalid inputs or an unusable resolver."""


@dataclass
class DNSAnswer:
    name: str
    rtype: str
    status: str
    values: list[str] = field(default_factory=list)
    ttl: int | None = None
    ad: bool | None = None
    error: str | None = None


@dataclass
class Finding:
    severity: str
    code: str
    summary: str
    evidence: str | None = None
    action: str | None = None


class ResolverBackend(Protocol):
    description: str

    def query(self, name: str, rtype: str) -> DNSAnswer:
        """Return a normalized DNS answer."""


def normalize_domain(value: str, label: str = "domain") -> str:
    candidate = value.strip().rstrip(".")
    if not candidate:
        raise AuditError(f"{label} cannot be empty")
    try:
        ascii_name = candidate.encode("idna").decode("ascii").casefold()
    except UnicodeError as exc:
        raise AuditError(f"invalid {label}: {value!r}") from exc
    if len(ascii_name) > 253:
        raise AuditError(f"{label} exceeds 253 characters: {value!r}")
    labels = ascii_name.split(".")
    if any(not DOMAIN_LABEL.fullmatch(part) for part in labels):
        raise AuditError(f"invalid {label}: {value!r}")
    return ascii_name


def normalize_dns_name(value: str, label: str = "DNS name") -> str:
    candidate = value.strip().rstrip(".")
    if not candidate:
        raise AuditError(f"{label} cannot be empty")
    try:
        ascii_name = candidate.encode("idna").decode("ascii").casefold()
    except UnicodeError as exc:
        raise AuditError(f"invalid {label}: {value!r}") from exc
    if len(ascii_name) > 253 or any(not DNS_LABEL.fullmatch(part) for part in ascii_name.split(".")):
        raise AuditError(f"invalid {label}: {value!r}")
    return ascii_name


def normalize_selector(value: str, label: str = "selector") -> str:
    selector = normalize_dns_name(value, label)
    if "." in selector:
        raise AuditError(f"{label} must be one DNS label: {value!r}")
    return selector


def normalize_record_type(value: str) -> str:
    record_type = value.strip().upper()
    if not RECORD_TYPE.fullmatch(record_type):
        raise AuditError(f"invalid DNS record type: {value!r}")
    return record_type


def answer_has_data(answer: DNSAnswer) -> bool:
    return answer.status == "ok" and bool(answer.values)


class FixtureResolver:
    """Resolve records from a deterministic JSON fixture without network access."""

    description = "offline JSON fixture"

    def __init__(self, records: dict[tuple[str, str], DNSAnswer]) -> None:
        self.records = records

    @classmethod
    def from_file(cls, path: Path) -> "FixtureResolver":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AuditError(f"cannot read DNS fixture {path}: {exc}") from exc
        source = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(source, dict):
            raise AuditError("fixture must contain an object named 'records'")

        records: dict[tuple[str, str], DNSAnswer] = {}
        for raw_key, raw_value in source.items():
            if not isinstance(raw_key, str) or "|" not in raw_key:
                raise AuditError(f"fixture record key must be NAME|TYPE: {raw_key!r}")
            raw_name, raw_type = raw_key.rsplit("|", 1)
            name = normalize_dns_name(raw_name, "fixture DNS name")
            rtype = normalize_record_type(raw_type)
            if isinstance(raw_value, list):
                spec: dict[str, Any] = {"status": "ok", "values": raw_value}
            elif isinstance(raw_value, str):
                spec = {"status": "ok", "values": [raw_value]}
            elif isinstance(raw_value, dict):
                spec = raw_value
            else:
                raise AuditError(f"fixture value for {raw_key!r} must be an object, string, or list")

            status = str(spec.get("status", "ok")).casefold()
            if status not in {"ok", "nodata", "nxdomain", "error"}:
                raise AuditError(f"unsupported fixture status for {raw_key!r}: {status!r}")
            values = spec.get("values", [])
            if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
                raise AuditError(f"fixture values for {raw_key!r} must be strings")
            ttl = spec.get("ttl")
            if ttl is not None and (not isinstance(ttl, int) or ttl < 0):
                raise AuditError(f"fixture ttl for {raw_key!r} must be a non-negative integer")
            ad = spec.get("ad")
            if ad is not None and not isinstance(ad, bool):
                raise AuditError(f"fixture ad for {raw_key!r} must be boolean")
            records[(name, rtype)] = DNSAnswer(
                name=name,
                rtype=rtype,
                status=status,
                values=list(values),
                ttl=ttl,
                ad=ad,
                error=str(spec["error"]) if spec.get("error") else None,
            )
        return cls(records)

    def query(self, name: str, rtype: str) -> DNSAnswer:
        key = (normalize_dns_name(name), normalize_record_type(rtype))
        answer = self.records.get(key)
        if answer is not None:
            return DNSAnswer(**asdict(answer))
        if key[1] != "CNAME":
            current = key[0]
            visited = {current}
            for _ in range(8):
                cname = self.records.get((current, "CNAME"))
                if not cname or not answer_has_data(cname) or len(cname.values) != 1:
                    break
                try:
                    current = normalize_dns_name(cname.values[0], "fixture CNAME target")
                except AuditError:
                    break
                if current in visited:
                    return DNSAnswer(
                        name=key[0],
                        rtype=key[1],
                        status="error",
                        error="CNAME loop in fixture",
                    )
                visited.add(current)
                target = self.records.get((current, key[1]))
                if target is not None:
                    copied = DNSAnswer(**asdict(target))
                    copied.name = key[0]
                    return copied
        return DNSAnswer(name=key[0], rtype=key[1], status="nodata", ad=None)


class LiveResolver:
    """Resolve records with dnspython, imported only for live analysis."""

    def __init__(self, timeout: float, nameserver: str | None = None, tcp: bool = False) -> None:
        try:
            import dns.flags
            import dns.resolver
        except ImportError as exc:
            raise AuditError(
                "live DNS requires dnspython; run "
                "'python -m pip install -r scripts/requirements.txt'"
            ) from exc

        self._dns_flags = dns.flags
        self._dns_resolver = dns.resolver
        self._resolver = dns.resolver.Resolver(configure=True)
        self._resolver.timeout = timeout
        self._resolver.lifetime = timeout
        self._resolver.use_edns(edns=0, ednsflags=dns.flags.DO, payload=1232)
        self.tcp = tcp
        if nameserver:
            try:
                ipaddress.ip_address(nameserver)
            except ValueError as exc:
                raise AuditError("--resolver must be an IPv4 or IPv6 address") from exc
            self._resolver.nameservers = [nameserver]
        transport = "TCP" if tcp else "UDP with TCP fallback"
        server = nameserver or "system resolver"
        self.description = f"dnspython via {server} ({transport})"

    def query(self, name: str, rtype: str) -> DNSAnswer:
        normalized_name = normalize_dns_name(name)
        normalized_type = normalize_record_type(rtype)
        try:
            answer = self._resolver.resolve(
                normalized_name,
                normalized_type,
                search=False,
                tcp=self.tcp,
                raise_on_no_answer=False,
            )
            response = getattr(answer, "response", None)
            ad = bool(response and response.flags & self._dns_flags.AD)
            rrset = getattr(answer, "rrset", None)
            if rrset is None:
                return DNSAnswer(
                    name=normalized_name,
                    rtype=normalized_type,
                    status="nodata",
                    ad=ad,
                )
            values: list[str] = []
            for rdata in answer:
                if normalized_type == "TXT" and hasattr(rdata, "strings"):
                    values.append(b"".join(rdata.strings).decode("utf-8", errors="replace"))
                else:
                    values.append(rdata.to_text())
            return DNSAnswer(
                name=normalized_name,
                rtype=normalized_type,
                status="ok",
                values=values,
                ttl=rrset.ttl,
                ad=ad,
            )
        except self._dns_resolver.NXDOMAIN:
            return DNSAnswer(name=normalized_name, rtype=normalized_type, status="nxdomain")
        except self._dns_resolver.NoAnswer:
            return DNSAnswer(name=normalized_name, rtype=normalized_type, status="nodata")
        except (
            self._dns_resolver.LifetimeTimeout,
            self._dns_resolver.NoNameservers,
            OSError,
        ) as exc:
            return DNSAnswer(
                name=normalized_name,
                rtype=normalized_type,
                status="error",
                error=f"{type(exc).__name__}: {exc}",
            )
        except Exception as exc:  # dnspython record-specific exceptions vary by type.
            return DNSAnswer(
                name=normalized_name,
                rtype=normalized_type,
                status="error",
                error=f"{type(exc).__name__}: {exc}",
            )


@dataclass
class AuditContext:
    resolver: ResolverBackend
    max_queries: int
    records: dict[tuple[str, str], DNSAnswer] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    def query(self, name: str, rtype: str) -> DNSAnswer:
        normalized_name = normalize_dns_name(name)
        normalized_type = normalize_record_type(rtype)
        key = (normalized_name, normalized_type)
        if key in self.records:
            return self.records[key]
        if len(self.records) >= self.max_queries:
            raise AuditError(f"DNS query limit exceeded ({self.max_queries})")
        answer = self.resolver.query(normalized_name, normalized_type)
        self.records[key] = answer
        if answer.status == "error":
            self.add(
                "warning",
                "dns_query_error",
                f"{normalized_type} query failed for {normalized_name}.",
                answer.error,
                "Re-run against another trusted resolver and preserve the timestamped response.",
            )
        return answer

    def add(
        self,
        severity: str,
        code: str,
        summary: str,
        evidence: str | None = None,
        action: str | None = None,
    ) -> None:
        self.findings.append(Finding(severity, code, summary, evidence, action))

    def add_once(
        self,
        severity: str,
        code: str,
        summary: str,
        evidence: str | None = None,
        action: str | None = None,
    ) -> None:
        candidate = Finding(severity, code, summary, evidence, action)
        if candidate not in self.findings:
            self.findings.append(candidate)


def parse_tag_record(record: str) -> tuple[dict[str, str], list[str], list[str]]:
    tags: dict[str, str] = {}
    order: list[str] = []
    errors: list[str] = []
    for fragment in record.split(";"):
        part = fragment.strip()
        if not part:
            continue
        if "=" not in part:
            errors.append(f"tag has no '=': {part!r}")
            continue
        raw_key, value = part.split("=", 1)
        key = raw_key.strip().casefold()
        if not key or not re.fullmatch(r"[a-z][a-z0-9_.-]*", key):
            errors.append(f"invalid tag name: {raw_key!r}")
            continue
        if key in tags:
            errors.append(f"duplicate tag: {key}")
            continue
        tags[key] = value.strip()
        order.append(key)
    return tags, order, errors


def versioned_txt(answer: DNSAnswer, version: str) -> list[str]:
    prefix = f"v={version}".casefold()
    return [value for value in answer.values if value.strip().casefold().startswith(prefix)]


def parse_mx_values(values: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    parsed: list[dict[str, Any]] = []
    errors: list[str] = []
    for value in values:
        parts = value.strip().split(None, 1)
        if len(parts) != 2:
            errors.append(f"invalid MX RDATA: {value!r}")
            continue
        try:
            preference = int(parts[0])
        except ValueError:
            errors.append(f"invalid MX preference: {value!r}")
            continue
        exchange_text = parts[1].strip()
        if exchange_text == ".":
            exchange = "."
        else:
            try:
                exchange = normalize_domain(exchange_text, "MX exchange")
            except AuditError as exc:
                errors.append(str(exc))
                continue
        if not 0 <= preference <= 65535:
            errors.append(f"MX preference outside 0..65535: {value!r}")
            continue
        parsed.append({"preference": preference, "exchange": exchange})
    return parsed, errors


def parse_tlsa(value: str) -> str | None:
    parts = value.split()
    if len(parts) != 4:
        return "TLSA RDATA must contain usage, selector, matching type, and association data"
    try:
        usage, selector, matching = (int(parts[index]) for index in range(3))
    except ValueError:
        return "TLSA usage, selector, and matching type must be integers"
    if usage not in range(4):
        return "TLSA certificate usage must be 0..3"
    if selector not in range(2):
        return "TLSA selector must be 0 or 1"
    if matching not in range(3):
        return "TLSA matching type must be 0..2"
    association = parts[3]
    if not association or len(association) % 2 or not re.fullmatch(r"[0-9A-Fa-f]+", association):
        return "TLSA association data must be non-empty hexadecimal"
    if matching == 1 and len(association) != 64:
        return "TLSA SHA-256 association data must contain 64 hexadecimal characters"
    if matching == 2 and len(association) != 128:
        return "TLSA SHA-512 association data must contain 128 hexadecimal characters"
    return None


def audit_inventory(ctx: AuditContext, domain: str) -> dict[str, Any]:
    answers = {
        rtype: ctx.query(domain, rtype)
        for rtype in ("A", "AAAA", "MX", "NS", "SOA", "CAA", "DS", "DNSKEY", "CDS", "CDNSKEY")
    }
    mx_records, mx_errors = parse_mx_values(answers["MX"].values)
    for error in mx_errors:
        ctx.add("error", "mx_syntax", "An MX record is malformed.", error)

    null_mx = [record for record in mx_records if record["exchange"] == "."]
    ordinary_mx = [record for record in mx_records if record["exchange"] != "."]
    if null_mx:
        valid_null = (
            len(mx_records) == 1
            and null_mx[0]["preference"] == 0
            and not ordinary_mx
        )
        if valid_null:
            ctx.add(
                "info",
                "null_mx",
                f"{domain} explicitly declares that it accepts no inbound mail.",
                "MX 0 .",
            )
        else:
            ctx.add(
                "error",
                "null_mx_conflict",
                "Null MX is combined with another or non-zero MX record.",
                ", ".join(answers["MX"].values),
                "Use exactly one 'MX 0 .' record for Null MX, or remove it and publish ordinary MX records.",
            )
    elif not ordinary_mx:
        if answer_has_data(answers["A"]) or answer_has_data(answers["AAAA"]):
            ctx.add(
                "info",
                "implicit_mx",
                f"{domain} has no MX record; SMTP may fall back to the apex address.",
                "RFC 5321 implicit MX behavior applies.",
                "Publish explicit MX or Null MX so inbound-mail intent is unambiguous.",
            )
        else:
            ctx.add(
                "warning",
                "no_inbound_route",
                f"{domain} has neither an ordinary MX nor an apex address for implicit MX.",
                action="Confirm whether the domain is intentionally unable to receive mail.",
            )

    hosts: list[dict[str, Any]] = []
    for record in ordinary_mx:
        host = record["exchange"]
        a_answer = ctx.query(host, "A")
        aaaa_answer = ctx.query(host, "AAAA")
        cname_answer = ctx.query(host, "CNAME")
        tlsa_answer = ctx.query(f"_25._tcp.{host}", "TLSA")
        host_data = {
            **record,
            "a": a_answer.values,
            "aaaa": aaaa_answer.values,
            "cname": cname_answer.values,
            "tlsa": tlsa_answer.values,
            "tlsa_ad": tlsa_answer.ad,
        }
        hosts.append(host_data)
        if answer_has_data(cname_answer):
            ctx.add(
                "warning",
                "mx_is_cname",
                f"MX host {host} is an alias.",
                ", ".join(cname_answer.values),
                "Publish a canonical host name in MX and place address records on that host.",
            )
        if not answer_has_data(a_answer) and not answer_has_data(aaaa_answer):
            ctx.add(
                "error",
                "mx_has_no_address",
                f"MX host {host} has no observed A or AAAA address.",
                action="Correct the MX target or its address records.",
            )
        if answer_has_data(tlsa_answer):
            for value in tlsa_answer.values:
                error = parse_tlsa(value)
                if error:
                    ctx.add("error", "tlsa_syntax", f"TLSA for {host} is malformed.", f"{value}: {error}")
            if tlsa_answer.ad:
                ctx.add(
                    "info",
                    "dane_tlsa_secure_signal",
                    f"A TLSA RRset for {host} carried the resolver's AD signal.",
                    "DANE still depends on trusting this validating resolver and the full DNSSEC chain.",
                )
            else:
                ctx.add(
                    "warning",
                    "dane_tlsa_not_validated",
                    f"TLSA records exist for {host}, but this response did not carry AD.",
                    action="Validate the TLSA RRset through a trusted DNSSEC validator before treating DANE as active.",
                )

    ds = answers["DS"]
    dnskey = answers["DNSKEY"]
    if answer_has_data(ds) and answer_has_data(dnskey):
        if ds.ad and dnskey.ad:
            ctx.add(
                "info",
                "dnssec_ad_signal",
                f"DS and DNSKEY answers for {domain} carried the resolver's AD signal.",
                "AD is resolver-provided evidence, not independent local validation by this script.",
            )
        else:
            ctx.add(
                "warning",
                "dnssec_records_unvalidated",
                f"DS and DNSKEY records were observed for {domain} without AD on both answers.",
                action="Use a trusted validating resolver or a dedicated DNSSEC validator to verify the chain.",
            )
    elif answer_has_data(ds) != answer_has_data(dnskey):
        ctx.add(
            "warning",
            "dnssec_incomplete_signal",
            f"Only one of DS or DNSKEY was observed for {domain}.",
            action="Validate the delegation and zone-signing chain with a DNSSEC-aware diagnostic.",
        )
    else:
        ctx.add(
            "info",
            "dnssec_not_observed",
            f"No DS/DNSKEY deployment was established for {domain} by this snapshot.",
            "Authenticated denial and resolver trust were not independently validated.",
        )

    return {
        "apex": {rtype.casefold(): asdict(answer) for rtype, answer in answers.items()},
        "mx": {
            "records": mx_records,
            "null_mx": bool(null_mx),
            "hosts": hosts,
        },
    }


def spf_mechanism_target(core: str, mechanism: str, current_domain: str) -> str | None:
    remainder = core[len(mechanism) :]
    if not remainder or remainder.startswith("/"):
        return current_domain
    if not remainder.startswith(":"):
        return None
    target = remainder[1:].split("/", 1)[0]
    return target or None


def audit_spf(ctx: AuditContext, domain: str, max_depth: int) -> dict[str, Any]:
    graph: list[dict[str, Any]] = []
    visited: set[str] = set()
    stack: list[str] = []
    lookup_terms = 0
    void_candidates: set[str] = set()
    macros_seen: set[str] = set()

    def probe_target(current: str, mechanism: str, core: str) -> None:
        target_text = spf_mechanism_target(core, mechanism, current)
        if not target_text:
            ctx.add("error", "spf_syntax", f"SPF {mechanism} mechanism is malformed.", core)
            return
        if "%{" in target_text:
            macros_seen.add(target_text)
            return
        try:
            target = normalize_dns_name(target_text, f"SPF {mechanism} target")
        except AuditError as exc:
            ctx.add("error", "spf_target", str(exc), core)
            return
        if mechanism == "a":
            if not answer_has_data(ctx.query(target, "A")) and not answer_has_data(ctx.query(target, "AAAA")):
                void_candidates.add(f"a:{target}")
        elif mechanism == "mx":
            mx_answer = ctx.query(target, "MX")
            mx_values, _ = parse_mx_values(mx_answer.values)
            if not mx_values:
                void_candidates.add(f"mx:{target}")
            if len(mx_values) > 10:
                ctx.add(
                    "warning",
                    "spf_mx_fanout",
                    f"SPF MX expansion for {target} exposes more than 10 MX records.",
                    f"{len(mx_values)} MX records observed.",
                )
        elif mechanism == "exists":
            if not answer_has_data(ctx.query(target, "A")):
                void_candidates.add(f"exists:{target}")

    def walk(current: str, depth: int, via: str) -> None:
        nonlocal lookup_terms
        if current in stack:
            cycle = " -> ".join(stack + [current])
            ctx.add(
                "error",
                "spf_cycle",
                "SPF include/redirect recursion contains a cycle.",
                cycle,
                "Remove the recursive dependency before relying on this SPF policy.",
            )
            return
        if current in visited:
            return
        if depth > max_depth:
            ctx.add(
                "warning",
                "spf_depth_limit",
                f"SPF dependency expansion stopped beyond depth {max_depth}.",
                current,
                "Increase --max-spf-depth if this is an intentional deep dependency graph.",
            )
            return

        visited.add(current)
        stack.append(current)
        answer = ctx.query(current, "TXT")
        records = versioned_txt(answer, "spf1")
        node: dict[str, Any] = {
            "domain": current,
            "via": via,
            "records": records,
            "lookup_terms": [],
            "dependencies": [],
        }
        graph.append(node)
        if not records:
            severity = "warning" if depth == 0 else "error"
            ctx.add(
                severity,
                "spf_missing" if depth == 0 else "spf_dependency_missing",
                f"No SPF policy was found at {current}.",
                f"Reached via {via}.",
                "Confirm the envelope-sender identity and every include/redirect target.",
            )
            if depth:
                void_candidates.add(f"{via}:{current}")
            stack.pop()
            return
        if len(records) > 1:
            ctx.add(
                "error",
                "spf_multiple_records",
                f"{current} publishes multiple SPF policies.",
                f"{len(records)} records start with v=spf1.",
                "Publish one SPF TXT record; multiple records cause SPF permerror.",
            )
            stack.pop()
            return

        record = records[0]
        terms = record.split()
        redirect_targets: list[str] = []
        terminal_all: tuple[str, int] | None = None
        reachable = True
        known_modifiers: set[str] = set()

        for index, raw_term in enumerate(terms[1:], start=1):
            if "=" in raw_term:
                modifier, value = raw_term.split("=", 1)
                modifier = modifier.casefold()
                if modifier in known_modifiers:
                    ctx.add("error", "spf_duplicate_modifier", f"SPF modifier {modifier}= is duplicated.", record)
                known_modifiers.add(modifier)
                if modifier == "redirect":
                    if not value:
                        ctx.add("error", "spf_redirect_syntax", "SPF redirect has an empty target.", record)
                        continue
                    if not reachable:
                        continue
                    lookup_terms += 1
                    node["lookup_terms"].append(raw_term)
                    if "%{" in value:
                        macros_seen.add(value)
                    else:
                        try:
                            target = normalize_dns_name(value, "SPF redirect target")
                        except AuditError as exc:
                            ctx.add("error", "spf_target", str(exc), raw_term)
                        else:
                            redirect_targets.append(target)
                            node["dependencies"].append({"type": "redirect", "domain": target})
                continue

            qualifier = "+"
            core = raw_term
            if raw_term[:1] in {"+", "-", "~", "?"}:
                qualifier, core = raw_term[0], raw_term[1:]
            mechanism = core.split(":", 1)[0].split("/", 1)[0].casefold()
            if mechanism not in SPF_MECHANISMS:
                ctx.add("error", "spf_unknown_mechanism", f"Unknown SPF mechanism {mechanism!r}.", raw_term)
                continue
            if not reachable:
                ctx.add(
                    "warning",
                    "spf_unreachable_term",
                    "An SPF mechanism appears after an all mechanism and is unreachable.",
                    raw_term,
                )
                continue
            if mechanism in SPF_LOOKUP_MECHANISMS:
                lookup_terms += 1
                node["lookup_terms"].append(raw_term)
            if mechanism in {"ip4", "ip6"}:
                if ":" not in core:
                    ctx.add("error", "spf_ip_syntax", f"SPF {mechanism} has no network.", raw_term)
                else:
                    network = core.split(":", 1)[1]
                    try:
                        parsed_network = ipaddress.ip_network(network, strict=False)
                        expected = 4 if mechanism == "ip4" else 6
                        if parsed_network.version != expected:
                            raise ValueError("address family does not match mechanism")
                    except ValueError as exc:
                        ctx.add("error", "spf_ip_syntax", f"Invalid SPF {mechanism} network.", f"{raw_term}: {exc}")
            elif mechanism == "include":
                if ":" not in core or not core.split(":", 1)[1]:
                    ctx.add("error", "spf_include_syntax", "SPF include has no target.", raw_term)
                else:
                    target_text = core.split(":", 1)[1]
                    if "%{" in target_text:
                        macros_seen.add(target_text)
                    else:
                        try:
                            target = normalize_dns_name(target_text, "SPF include target")
                        except AuditError as exc:
                            ctx.add("error", "spf_target", str(exc), raw_term)
                        else:
                            node["dependencies"].append({"type": "include", "domain": target})
            elif mechanism in {"a", "mx", "exists"}:
                probe_target(current, mechanism, core)
            elif mechanism == "ptr":
                ctx.add(
                    "warning",
                    "spf_ptr",
                    "The SPF ptr mechanism is slow, fragile, and explicitly discouraged by RFC 7208.",
                    raw_term,
                    "Replace it with bounded ip4/ip6, include, a, or mx authorization where appropriate.",
                )
            elif mechanism == "all":
                if ":" in core or "/" in core:
                    ctx.add("error", "spf_all_syntax", "SPF all mechanism has invalid arguments.", raw_term)
                terminal_all = (qualifier, index)
                reachable = False
                if qualifier == "+":
                    ctx.add(
                        "error",
                        "spf_permissive_all",
                        "SPF +all authorizes every sender.",
                        record,
                        "Replace +all with a policy matching the actual sending infrastructure.",
                    )
                elif qualifier == "?":
                    ctx.add(
                        "warning",
                        "spf_neutral_all",
                        "SPF ?all makes no authorization assertion for unmatched senders.",
                        record,
                    )

        if len(redirect_targets) > 1:
            ctx.add("error", "spf_multiple_redirects", "SPF contains multiple redirect modifiers.", record)
        if terminal_all is None and not redirect_targets:
            ctx.add(
                "warning",
                "spf_no_terminal_policy",
                f"SPF at {current} has neither all nor redirect.",
                record,
                "Confirm that the implicit neutral result is intentional.",
            )

        dependencies = list(node["dependencies"])
        for dependency in dependencies:
            walk(dependency["domain"], depth + 1, dependency["type"])
        stack.pop()

    walk(domain, 0, "root")
    if lookup_terms > 10:
        ctx.add(
            "warning",
            "spf_lookup_budget_risk",
            "The expanded SPF graph exposes more than 10 DNS-querying terms.",
            f"{lookup_terms} terms observed across statically explored reachable branches.",
            "Evaluate real SMTP identities and paths with an RFC 7208-compliant SPF evaluator; simplify if any path exceeds 10.",
        )
    if len(void_candidates) > 2:
        ctx.add(
            "warning",
            "spf_void_lookup_risk",
            "The static SPF probe observed more than two potential void lookup terms.",
            ", ".join(sorted(void_candidates)),
            "Confirm with a transaction-aware SPF evaluator; RFC 7208 recommends a limit of two void lookups.",
        )
    if macros_seen:
        ctx.add(
            "info",
            "spf_macros_not_expanded",
            "SPF contains macro-dependent domains that this static audit did not expand.",
            ", ".join(sorted(macros_seen)),
            "Evaluate with the real client IP, sender, HELO, receiver, and timestamp.",
        )
    return {
        "domain": domain,
        "graph": graph,
        "static_lookup_terms": lookup_terms,
        "potential_void_terms": sorted(void_candidates),
        "macros": sorted(macros_seen),
        "is_transaction_evaluation": False,
    }


def read_der_tlv(data: bytes, offset: int) -> tuple[int, bytes, int]:
    if offset >= len(data):
        raise ValueError("truncated DER tag")
    tag = data[offset]
    offset += 1
    if offset >= len(data):
        raise ValueError("truncated DER length")
    first = data[offset]
    offset += 1
    if first & 0x80:
        count = first & 0x7F
        if count == 0 or count > 4 or offset + count > len(data):
            raise ValueError("invalid DER length")
        length = int.from_bytes(data[offset : offset + count], "big")
        offset += count
    else:
        length = first
    end = offset + length
    if end > len(data):
        raise ValueError("truncated DER value")
    return tag, data[offset:end], end


def rsa_public_key_bits(raw: bytes) -> int:
    outer_tag, outer, outer_end = read_der_tlv(raw, 0)
    if outer_tag != 0x30 or outer_end != len(raw):
        raise ValueError("public key is not one complete DER SEQUENCE")
    first_tag, first_value, first_end = read_der_tlv(outer, 0)
    if first_tag == 0x02:
        modulus = first_value
    elif first_tag == 0x30:
        bit_tag, bit_value, bit_end = read_der_tlv(outer, first_end)
        if bit_tag != 0x03 or bit_end != len(outer) or not bit_value or bit_value[0] != 0:
            raise ValueError("invalid SubjectPublicKeyInfo BIT STRING")
        key_tag, key_sequence, key_end = read_der_tlv(bit_value[1:], 0)
        if key_tag != 0x30 or key_end != len(bit_value) - 1:
            raise ValueError("invalid RSA public-key SEQUENCE")
        modulus_tag, modulus, _ = read_der_tlv(key_sequence, 0)
        if modulus_tag != 0x02:
            raise ValueError("RSA modulus is not an INTEGER")
    else:
        raise ValueError("unsupported RSA DER structure")
    modulus = modulus.lstrip(b"\x00")
    if not modulus:
        raise ValueError("empty RSA modulus")
    return int.from_bytes(modulus, "big").bit_length()


def decode_public_key(value: str) -> bytes:
    compact = re.sub(r"\s+", "", value)
    padding = "=" * ((4 - len(compact) % 4) % 4)
    try:
        return base64.b64decode(compact + padding, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"invalid base64 public key: {exc}") from exc


def dkim_discovery_plan(
    domain: str,
    inventory: dict[str, Any],
    spf: dict[str, Any],
) -> dict[str, Any]:
    evidence: list[str] = []
    for record in inventory.get("mx", {}).get("records", []):
        exchange = str(record.get("exchange", "")).casefold()
        if exchange and exchange != ".":
            evidence.append(f"MX {exchange}")
    for node in spf.get("graph", []):
        node_domain = str(node.get("domain", "")).casefold()
        if node_domain:
            evidence.append(f"SPF domain {node_domain}")
        evidence.extend(f"SPF {str(record).casefold()}" for record in node.get("records", []))

    haystack = "\n".join(evidence)
    selectors = set(COMMON_DKIM_SELECTORS)
    hints: list[dict[str, Any]] = []
    for label, fingerprints, provider_selectors in DKIM_PROVIDER_FINGERPRINTS:
        matches = sorted({fingerprint for fingerprint in fingerprints if fingerprint in haystack})
        if not matches:
            continue
        selectors.update(provider_selectors)
        hints.append(
            {
                "label": label,
                "matched_fingerprints": matches,
                "candidate_selectors": list(provider_selectors),
            }
        )
    return {
        "domain": domain,
        "candidate_selectors": sorted(selectors),
        "provider_hints": hints,
        "evidence": evidence,
    }


def discover_dkim_identities(
    ctx: AuditContext,
    plan: dict[str, Any],
) -> tuple[list[tuple[str, str]], dict[str, Any]]:
    domain = str(plan["domain"])
    found: list[tuple[str, str]] = []
    probes: list[dict[str, Any]] = []
    for selector in plan["candidate_selectors"]:
        name = f"{selector}._domainkey.{domain}"
        cname = ctx.query(name, "CNAME")
        txt = ctx.query(name, "TXT")
        candidates: list[str] = []
        for value in txt.values:
            tags, _, _ = parse_tag_record(value)
            if "p" in tags or "k" in tags or tags.get("v", "").casefold() == "dkim1":
                candidates.append(value)
        positive = bool(cname.values or candidates)
        if positive:
            found.append((selector, domain))
            probes.append(
                {
                    "selector": selector,
                    "domain": domain,
                    "name": name,
                    "cname": cname.values,
                    "records": candidates,
                }
            )

    if found:
        ctx.add(
            "info",
            "dkim_candidate_discovery_found",
            f"Bounded candidate probing found {len(found)} DKIM selector record(s) for {domain}.",
            ", ".join(selector for selector, _ in found),
            "Confirm which selectors actively sign current mail using provider configuration or a received message.",
        )
    else:
        ctx.add(
            "info",
            "dkim_candidate_discovery_inconclusive",
            f"Bounded candidate probing found no DKIM records for {domain}.",
            f"{len(plan['candidate_selectors'])} common/provider-informed selector names were checked.",
            "Do not interpret this as DKIM absence; extract d= and s= from a current received message or provider configuration.",
        )
    return found, {
        "enabled": True,
        "domain": domain,
        "provider_hints": plan["provider_hints"],
        "candidate_selectors": plan["candidate_selectors"],
        "positive_probes": probes,
        "found_identities": [
            {"selector": selector, "domain": identity_domain}
            for selector, identity_domain in found
        ],
        "exhaustive": False,
    }


def audit_dkim(ctx: AuditContext, identities: list[tuple[str, str]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if not identities:
        ctx.add(
            "info",
            "dkim_selectors_not_supplied",
            "No DKIM selector/domain pair was supplied, so DKIM DNS keys were not checked.",
            action="Extract every active d= and s= pair from trusted DKIM-Signature headers or provider configuration.",
        )
        return results

    for selector, domain in identities:
        name = f"{selector}._domainkey.{domain}"
        cname_answer = ctx.query(name, "CNAME")
        answer = ctx.query(name, "TXT")
        candidates: list[tuple[str, dict[str, str], list[str], list[str]]] = []
        for value in answer.values:
            tags, order, errors = parse_tag_record(value)
            if "p" in tags or "k" in tags or tags.get("v", "").casefold() == "dkim1":
                candidates.append((value, tags, order, errors))
        item: dict[str, Any] = {
            "selector": selector,
            "domain": domain,
            "name": name,
            "cname": cname_answer.values,
            "records": [candidate[0] for candidate in candidates],
        }
        results.append(item)
        if not candidates:
            ctx.add(
                "warning",
                "dkim_key_missing",
                f"No DKIM key record was found for {selector}@{domain}.",
                name,
                "Confirm the selector is active and query the exact d= domain.",
            )
            continue
        if len(candidates) > 1:
            ctx.add(
                "error",
                "dkim_multiple_keys",
                f"Multiple DKIM key records were found for {selector}@{domain}.",
                f"{len(candidates)} candidate TXT records.",
                "Publish one key record per selector.",
            )
            continue

        record, tags, order, errors = candidates[0]
        item["tags"] = tags
        for error in errors:
            ctx.add("error", "dkim_tag_syntax", f"DKIM key {selector}@{domain} is malformed.", error)
        if "v" in tags and (tags["v"].casefold() != "dkim1" or order[:1] != ["v"]):
            ctx.add(
                "error",
                "dkim_version",
                f"DKIM key {selector}@{domain} has an invalid or misplaced version tag.",
                record,
            )
        if "p" not in tags:
            ctx.add("error", "dkim_public_key_missing", f"DKIM key {selector}@{domain} has no p= tag.", record)
            continue
        if not tags["p"]:
            ctx.add(
                "warning",
                "dkim_key_revoked",
                f"DKIM key {selector}@{domain} is revoked with an empty p= value.",
                action="Confirm no active sender still signs with this selector.",
            )
            item["revoked"] = True
            continue

        key_type = tags.get("k", "rsa").casefold()
        item["key_type"] = key_type
        try:
            key_bytes = decode_public_key(tags["p"])
            item["key_bytes"] = len(key_bytes)
            if key_type == "rsa":
                bits = rsa_public_key_bits(key_bytes)
                item["rsa_bits"] = bits
                if bits < 1024:
                    ctx.add(
                        "error",
                        "dkim_rsa_too_small",
                        f"DKIM RSA key {selector}@{domain} is below 1024 bits.",
                        f"{bits} bits.",
                        "Rotate to an RSA key of at least 1024 bits; RFC 8301 recommends at least 2048.",
                    )
                elif bits < 2048:
                    ctx.add(
                        "warning",
                        "dkim_rsa_legacy_size",
                        f"DKIM RSA key {selector}@{domain} is {bits} bits.",
                        "RFC 8301 permits 1024 bits but recommends at least 2048.",
                        "Plan a tested selector rotation to a 2048-bit key where DNS/provider limits permit.",
                    )
            elif key_type == "ed25519":
                if len(key_bytes) != 32:
                    ctx.add(
                        "error",
                        "dkim_ed25519_length",
                        f"DKIM Ed25519 key {selector}@{domain} is not 32 bytes.",
                        f"{len(key_bytes)} decoded bytes.",
                    )
            else:
                ctx.add(
                    "warning",
                    "dkim_unknown_key_type",
                    f"DKIM key {selector}@{domain} uses unrecognized k={key_type}.",
                    action="Verify the key type against the current DKIM key-type registry and receiver support.",
                )
        except ValueError as exc:
            ctx.add(
                "error",
                "dkim_public_key_invalid",
                f"DKIM public key {selector}@{domain} could not be decoded.",
                str(exc),
            )

        hashes = {value.strip().casefold() for value in tags.get("h", "sha256").split(":") if value.strip()}
        if "sha256" not in hashes:
            ctx.add(
                "error",
                "dkim_sha256_not_allowed",
                f"DKIM key {selector}@{domain} does not allow SHA-256.",
                f"h={tags.get('h', '')}",
            )
        services = {value.strip().casefold() for value in tags.get("s", "*").split(":") if value.strip()}
        if "*" not in services and "email" not in services:
            ctx.add(
                "error",
                "dkim_service_excludes_email",
                f"DKIM key {selector}@{domain} does not permit the email service.",
                f"s={tags.get('s', '')}",
            )
        flags = {value.strip().casefold() for value in tags.get("t", "").split(":") if value.strip()}
        if "y" in flags:
            ctx.add("info", "dkim_testing_flag", f"DKIM key {selector}@{domain} has the testing flag t=y.")
    return results


def parse_report_uris(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def uri_destination_domain(uri: str) -> str | None:
    parsed = urlsplit(uri)
    if parsed.scheme.casefold() == "mailto":
        address = parsed.path.split("!", 1)[0]
        if "@" not in address:
            return None
        try:
            return normalize_domain(address.rsplit("@", 1)[1], "report destination")
        except AuditError:
            return None
    if parsed.hostname:
        try:
            return normalize_domain(parsed.hostname, "report destination")
        except AuditError:
            return None
    return None


def same_organizational_domain(candidate: str, org_domain: str | None) -> bool | None:
    if org_domain is None:
        return None
    return candidate == org_domain or candidate.endswith(f".{org_domain}")


def legacy_alignment_status(
    candidate: str,
    header_from: str,
    mode: str,
    org_domain: str | None,
) -> bool | None:
    if candidate == header_from:
        return True
    if mode == "s":
        return False
    if org_domain:
        return same_organizational_domain(candidate, org_domain) and same_organizational_domain(
            header_from, org_domain
        )
    return None


def dmarc_record_candidates(answer: DNSAnswer) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for record in answer.values:
        tags, order, errors = parse_tag_record(record)
        if order[:1] == ["v"] and tags.get("v") == "DMARC1":
            candidates.append(
                {
                    "record": record,
                    "tags": tags,
                    "order": order,
                    "syntax_errors": errors,
                }
            )
    return candidates


def dmarc_tree_walk_targets(domain: str) -> list[str]:
    labels = domain.split(".")
    targets = [domain]
    if len(labels) >= 8:
        current = labels[-7:]
    else:
        current = labels[1:]
    while current:
        targets.append(".".join(current))
        current = current[1:]
    return targets


def child_below(domain: str, ancestor: str) -> str | None:
    domain_labels = domain.split(".")
    ancestor_labels = ancestor.split(".")
    if len(domain_labels) <= len(ancestor_labels):
        return None
    if domain_labels[-len(ancestor_labels) :] != ancestor_labels:
        return None
    return ".".join(domain_labels[-(len(ancestor_labels) + 1) :])


def dmarc_tree_walk(ctx: AuditContext, domain: str) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    targets = dmarc_tree_walk_targets(domain)
    for target in targets:
        name = f"_dmarc.{target}"
        answer = ctx.query(name, "TXT")
        candidates = dmarc_record_candidates(answer)
        selected = candidates[0] if len(candidates) == 1 else None
        entry: dict[str, Any] = {
            "domain": target,
            "name": name,
            "candidate_count": len(candidates),
            "records": [item["record"] for item in candidates],
            "selected": selected,
        }
        entries.append(entry)
        if len(candidates) > 1:
            ctx.add_once(
                "error",
                "dmarc_multiple_records",
                f"Multiple DMARC policy records were returned at {name}; RFC 9989 discards them at this Tree Walk node.",
                f"{len(candidates)} records begin with a valid v=DMARC1 tag.",
                "Publish exactly one DMARC policy record at this DNS name.",
            )
        if selected and selected["tags"].get("psd", "").casefold() in {"y", "n"}:
            break

    valid_entries = [entry for entry in entries if entry["selected"]]
    organizational_domain = domain
    selection_reason = "No valid DMARC record occurred in the Tree Walk; RFC 9989 defaults to the starting domain."
    for entry in valid_entries:
        if entry["selected"]["tags"].get("psd", "").casefold() == "n":
            organizational_domain = entry["domain"]
            selection_reason = f"{entry['name']} declares psd=n."
            break
        if (
            entry["domain"] != domain
            and entry["selected"]["tags"].get("psd", "").casefold() == "y"
        ):
            organizational_domain = child_below(domain, entry["domain"]) or domain
            selection_reason = (
                f"{entry['name']} declares psd=y; the Organizational Domain is one label below it."
            )
            break
    else:
        if valid_entries:
            organizational_domain = valid_entries[-1]["domain"]
            selection_reason = (
                "The shallowest DNS name with one valid DMARC record is the Organizational Domain."
            )

    exact = entries[0] if entries and entries[0]["selected"] else None
    policy_entry: dict[str, Any] | None = exact
    policy_source_kind: str | None = "author" if exact else None
    if policy_entry is None:
        policy_entry = next(
            (
                entry
                for entry in valid_entries
                if entry["domain"] == organizational_domain
            ),
            None,
        )
        if policy_entry is not None:
            policy_source_kind = "organizational"
        else:
            policy_entry = next(
                (
                    entry
                    for entry in valid_entries
                    if entry["selected"]["tags"].get("psd", "").casefold() == "y"
                    and (
                        organizational_domain == entry["domain"]
                        or organizational_domain.endswith(f".{entry['domain']}")
                    )
                ),
                None,
            )
            if policy_entry is not None:
                policy_source_kind = "public_suffix"

    return {
        "start_domain": domain,
        "targets": targets,
        "entries": entries,
        "organizational_domain": organizational_domain,
        "organizational_domain_reason": selection_reason,
        "policy_entry": policy_entry,
        "policy_source_kind": policy_source_kind,
        "standard": "RFC 9989 DNS Tree Walk",
    }


def dmarc_uri_valid(uri: str) -> bool:
    try:
        parsed = urlsplit(uri)
    except ValueError:
        return False
    if not parsed.scheme:
        return False
    if parsed.scheme.casefold() == "mailto":
        return uri_destination_domain(uri) is not None
    return bool(parsed.hostname)


def lowered_test_policy(policy_value: str | None) -> str | None:
    if policy_value == "reject":
        return "quarantine"
    if policy_value == "quarantine":
        return "none"
    return policy_value


def audit_dmarc(
    ctx: AuditContext,
    header_from: str,
    expected_org_domain: str | None,
    mail_from: str,
    dkim_domains: list[str],
) -> dict[str, Any]:
    walk_cache: dict[str, dict[str, Any]] = {}

    def walk_for(domain: str) -> dict[str, Any]:
        if domain not in walk_cache:
            walk_cache[domain] = dmarc_tree_walk(ctx, domain)
        return walk_cache[domain]

    header_walk = walk_for(header_from)
    policy_entry = header_walk["policy_entry"]
    source = policy_entry["domain"] if policy_entry else None
    selected = policy_entry["selected"] if policy_entry else None
    records = [selected["record"]] if selected else []
    inherited = bool(source and source != header_from)
    result: dict[str, Any] = {
        "header_from_domain": header_from,
        "standard": "RFC 9989",
        "discovery_method": "treewalk",
        "tree_walk": {
            "targets": [entry["domain"] for entry in header_walk["entries"]],
            "organizational_domain": header_walk["organizational_domain"],
            "organizational_domain_reason": header_walk["organizational_domain_reason"],
        },
        "policy_source": source,
        "policy_source_kind": header_walk["policy_source_kind"],
        "inherited": inherited if source else None,
        "records": records,
        "expected_legacy_organizational_domain": expected_org_domain,
    }
    discovered_org = header_walk["organizational_domain"]
    if expected_org_domain and expected_org_domain != discovered_org:
        ctx.add(
            "info",
            "dmarc_org_methods_differ",
            "The supplied legacy/public-suffix Organizational Domain differs from the RFC 9989 Tree Walk result.",
            f"supplied={expected_org_domain}; treewalk={discovered_org}",
            "Preserve both results when assessing receivers that have not yet adopted RFC 9989.",
        )
    if not records:
        ctx.add(
            "warning",
            "dmarc_missing",
            f"No applicable DMARC policy was discovered for {header_from} by the RFC 9989 DNS Tree Walk.",
            action="Publish and monitor an appropriate DMARC policy at the intended Author or Organizational Domain.",
        )
        result["processing_applicable"] = False
        return result

    record = selected["record"]
    tags = selected["tags"]
    order = selected["order"]
    errors = selected["syntax_errors"]
    result["tags"] = tags
    for error in errors:
        ctx.add("error", "dmarc_tag_syntax", "The DMARC record is malformed.", error)
    if order[:1] != ["v"] or tags.get("v") != "DMARC1":
        ctx.add("error", "dmarc_version", "The DMARC v=DMARC1 tag is missing, invalid, or not first.", record)

    policy = tags.get("p", "").casefold() or "none"
    if "p" not in tags:
        ctx.add(
            "info",
            "dmarc_policy_default",
            f"The DMARC record at {source} omits p=; RFC 9989 treats it as p=none.",
        )
    invalid_assessment_tag = False
    if policy not in DMARC_POLICY_VALUES:
        invalid_assessment_tag = True
        ctx.add("error", "dmarc_policy", "DMARC p= must be none, quarantine, or reject.", f"p={policy}")
    for tag_name in ("sp", "np"):
        value = tags.get(tag_name, "").casefold()
        if value and value not in DMARC_POLICY_VALUES:
            invalid_assessment_tag = True
            ctx.add(
                "error",
                f"dmarc_{tag_name}_policy",
                f"DMARC {tag_name}= must be none, quarantine, or reject.",
                f"{tag_name}={value}",
            )

    test_mode = tags.get("t", "n").casefold()
    if test_mode not in {"y", "n"}:
        ctx.add("error", "dmarc_test_mode", "DMARC t= must be y or n.", f"t={test_mode}")
        test_mode = "n"
    psd = tags.get("psd", "u").casefold()
    if psd not in {"y", "n", "u"}:
        ctx.add("error", "dmarc_psd", "DMARC psd= must be y, n, or u.", f"psd={psd}")
        psd = "u"

    for alignment_tag in ("adkim", "aspf"):
        value = tags.get(alignment_tag, "r").casefold()
        if value not in {"r", "s"}:
            ctx.add("error", f"dmarc_{alignment_tag}", f"DMARC {alignment_tag}= must be r or s.", value)
    if "fo" in tags:
        values = tags["fo"].casefold().split(":")
        if (
            not values
            or any(value not in {"0", "1", "d", "s"} for value in values)
            or len(values) != len(set(values))
            or ({"0", "1"} <= set(values))
        ):
            ctx.add(
                "error",
                "dmarc_fo",
                "DMARC fo= has invalid, duplicate, or mutually exclusive values.",
                tags["fo"],
            )

    legacy_tags = {tag: tags[tag] for tag in sorted(DMARC_LEGACY_TAGS & tags.keys())}
    legacy_pct: int | None = None
    if "pct" in legacy_tags:
        try:
            legacy_pct = int(legacy_tags["pct"])
            if not 0 <= legacy_pct <= 100:
                raise ValueError
        except ValueError:
            legacy_pct = None
            ctx.add(
                "error",
                "dmarc_legacy_pct",
                "Legacy DMARC pct= must be an integer from 0 to 100.",
                legacy_tags["pct"],
            )
    if "ri" in legacy_tags:
        try:
            if int(legacy_tags["ri"]) <= 0:
                raise ValueError
        except ValueError:
            ctx.add(
                "error",
                "dmarc_legacy_ri",
                "Legacy DMARC ri= must be a positive integer.",
                legacy_tags["ri"],
            )
    if legacy_tags:
        ctx.add(
            "info",
            "dmarc_legacy_tags",
            "The record contains tag(s) removed from RFC 9989 and ignored by current-standard processing.",
            ", ".join(f"{tag}={value}" for tag, value in legacy_tags.items()),
            "Retain or change them only after checking interoperability needs for receivers still using RFC 7489-era behavior.",
        )
    result["legacy_tags"] = legacy_tags
    result["legacy_pct"] = legacy_pct
    result["ignored_unknown_tags"] = {
        tag: value
        for tag, value in tags.items()
        if tag not in DMARC_CURRENT_TAGS | DMARC_LEGACY_TAGS
    }

    for uri_tag in ("rua", "ruf"):
        uris = parse_report_uris(tags.get(uri_tag, ""))
        result[uri_tag] = uris
        for uri in uris:
            if not dmarc_uri_valid(uri):
                ctx.add(
                    "warning",
                    "dmarc_report_uri",
                    f"DMARC {uri_tag}= destination is not a syntactically usable URI.",
                    uri,
                    "Correct the URI and verify that intended report generators support its scheme.",
                )
            elif urlsplit(uri).scheme.casefold() != "mailto":
                ctx.add(
                    "info",
                    "dmarc_report_uri_scheme",
                    f"DMARC {uri_tag}= uses a non-mailto scheme that report generators are not required to support.",
                    uri,
                )

    valid_rua = any(dmarc_uri_valid(uri) for uri in result["rua"])
    processing_applicable = True
    policy_fallback = False
    if invalid_assessment_tag:
        if valid_rua:
            policy = "none"
            policy_fallback = True
            ctx.add(
                "warning",
                "dmarc_invalid_policy_reporting_fallback",
                "RFC 9989 treats this invalid assessment policy as p=none because at least one valid rua= URI exists.",
            )
        else:
            processing_applicable = False
            ctx.add(
                "error",
                "dmarc_processing_not_applicable",
                "RFC 9989 applies no DMARC processing because an assessment tag is invalid and no valid rua= URI exists.",
            )
    result["processing_applicable"] = processing_applicable
    result["invalid_policy_reporting_fallback"] = policy_fallback

    author_answer = ctx.query(header_from, "A")
    author_exists: bool | None
    if author_answer.status == "nxdomain":
        author_exists = False
    elif author_answer.status in {"ok", "nodata"}:
        author_exists = True
    else:
        author_exists = None
    result["author_domain_exists"] = author_exists

    requested_policy: str | None = None
    effective_policy_tag: str | None = None
    if processing_applicable:
        if policy_fallback or source == header_from:
            requested_policy = policy
            effective_policy_tag = "p"
        elif author_exists is False and tags.get("np", "").casefold() in DMARC_POLICY_VALUES:
            requested_policy = tags["np"].casefold()
            effective_policy_tag = "np"
        elif author_exists is not False and tags.get("sp", "").casefold() in DMARC_POLICY_VALUES:
            requested_policy = tags["sp"].casefold()
            effective_policy_tag = "sp"
        else:
            requested_policy = policy
            effective_policy_tag = "p"
        if author_exists is None and inherited and "np" in tags:
            ctx.add(
                "warning",
                "dmarc_domain_existence_unknown",
                "A DNS error prevented a definitive choice between inherited sp= and np= policy.",
                f"Header From domain: {header_from}",
            )
            requested_policy = None
            effective_policy_tag = None

    effective_policy = (
        lowered_test_policy(requested_policy) if test_mode == "y" else requested_policy
    )
    result["requested_policy"] = requested_policy
    result["effective_policy_tag"] = effective_policy_tag
    result["test_mode"] = test_mode
    result["effective_policy"] = effective_policy
    result["psd"] = psd

    external_destinations: set[str] = set()
    for uri_tag in ("rua", "ruf"):
        for uri in result.get(uri_tag, []):
            destination = uri_destination_domain(uri)
            if not destination:
                continue
            source_org = walk_for(source)["organizational_domain"]
            destination_org = walk_for(destination)["organizational_domain"]
            if source_org != destination_org:
                external_destinations.add(destination)
    authorizations: list[dict[str, Any]] = []
    for destination in sorted(external_destinations):
        name = f"{source}._report._dmarc.{destination}"
        answer = ctx.query(name, "TXT")
        authorization_records = dmarc_record_candidates(answer)
        authorized = bool(authorization_records)
        authorizations.append(
            {
                "destination": destination,
                "name": name,
                "authorized": authorized,
                "records": [item["record"] for item in authorization_records],
            }
        )
        if not authorized:
            ctx.add(
                "warning",
                "dmarc_external_report_unauthorized",
                f"No DMARC external-report authorization was found for {destination}.",
                name,
                "Confirm that the destination publishes the required authorization record.",
            )
    result["external_report_authorizations"] = authorizations

    adkim = tags.get("adkim", "r").casefold()
    aspf = tags.get("aspf", "r").casefold()
    if adkim not in {"r", "s"}:
        adkim = "r"
    if aspf not in {"r", "s"}:
        aspf = "r"

    def alignment_candidate(candidate: str, mode: str) -> dict[str, Any]:
        if candidate == header_from:
            aligned = True
            candidate_org = discovered_org
        elif mode == "s":
            aligned = False
            candidate_org = None
        else:
            candidate_walk = walk_for(candidate)
            candidate_org = candidate_walk["organizational_domain"]
            aligned = candidate_org == discovered_org
        return {
            "domain": candidate,
            "mode": mode,
            "aligned": aligned,
            "organizational_domain": candidate_org,
            "header_from_organizational_domain": discovered_org,
            "legacy_aligned": legacy_alignment_status(
                candidate,
                header_from,
                mode,
                expected_org_domain,
            ),
            "status": "candidate_only_authentication_result_required",
        }

    result["alignment_candidates"] = {
        "spf": alignment_candidate(mail_from, aspf),
        "dkim": [
            alignment_candidate(domain, adkim)
            for domain in sorted(set(dkim_domains))
        ],
    }
    if requested_policy == "none":
        ctx.add(
            "info",
            "dmarc_monitoring_policy",
            f"DMARC at {source} uses p=none.",
            "This requests reporting/monitoring rather than quarantine or reject.",
        )
    if test_mode == "y":
        ctx.add(
            "info",
            "dmarc_testing_policy",
            f"DMARC at {source} uses t=y testing mode.",
            f"requested={requested_policy!r}; expected applied level={effective_policy!r}",
        )
    return result


def validate_https_url(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme.casefold() == "https" and bool(parsed.hostname) and not parsed.username


def audit_bimi(
    ctx: AuditContext,
    header_from: str,
    selectors: list[str],
    dmarc: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for selector in selectors:
        name = f"{selector}._bimi.{header_from}"
        answer = ctx.query(name, "TXT")
        records = versioned_txt(answer, "BIMI1")
        item: dict[str, Any] = {"selector": selector, "name": name, "records": records}
        results.append(item)
        if not records:
            continue
        if len(records) > 1:
            ctx.add("error", "bimi_multiple_records", f"Multiple BIMI records exist at {name}.")
            continue
        tags, order, errors = parse_tag_record(records[0])
        item["tags"] = tags
        for error in errors:
            ctx.add("error", "bimi_tag_syntax", f"BIMI record {name} is malformed.", error)
        if order[:1] != ["v"] or tags.get("v", "").casefold() != "bimi1":
            ctx.add("error", "bimi_version", f"BIMI version is invalid or not first at {name}.")
        if not tags.get("l"):
            ctx.add("warning", "bimi_logo_missing", f"BIMI record {name} has no non-empty l= logo URL.")
        elif not validate_https_url(tags["l"]):
            ctx.add("error", "bimi_logo_url", f"BIMI l= at {name} is not a valid HTTPS URL.", tags["l"])
        if tags.get("a") and not validate_https_url(tags["a"]):
            ctx.add("error", "bimi_authority_url", f"BIMI a= at {name} is not a valid HTTPS URL.", tags["a"])

        effective = dmarc.get("effective_policy")
        test_mode = dmarc.get("test_mode")
        legacy_pct = dmarc.get("legacy_pct")
        if (
            effective not in {"quarantine", "reject"}
            or test_mode == "y"
            or legacy_pct not in {None, 100}
        ):
            ctx.add(
                "warning",
                "bimi_dmarc_prerequisite",
                f"BIMI is published at {name}, but full DMARC enforcement was not established.",
                (
                    f"RFC 9989 effective policy={effective!r}, t={test_mode!r}, "
                    f"legacy pct={legacy_pct!r}"
                ),
                "Check current mailbox-provider BIMI requirements before expecting logo display.",
            )
        ctx.add(
            "info",
            "bimi_asset_not_fetched",
            f"BIMI DNS syntax was checked at {name}; logo/certificate content was not.",
            action="Validate SVG profile, redirects, content type, certificate chain, trademark claims, and provider eligibility separately.",
        )
    return results


def parse_mta_sts_policy(text: str) -> tuple[dict[str, Any], list[str]]:
    fields: dict[str, Any] = {}
    mx_values: list[str] = []
    errors: list[str] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        if ":" not in raw_line:
            errors.append(f"line {line_number} has no colon")
            continue
        raw_key, raw_value = raw_line.split(":", 1)
        key = raw_key.strip()
        value = raw_value.strip()
        if key == "mx":
            mx_values.append(value)
        elif key in fields:
            errors.append(f"duplicate {key} field")
        else:
            fields[key] = value
    fields["mx"] = mx_values
    if fields.get("version") != "STSv1":
        errors.append("version must be STSv1")
    if fields.get("mode") not in {"enforce", "testing", "none"}:
        errors.append("mode must be enforce, testing, or none")
    try:
        max_age_text = fields.get("max_age", "")
        if not re.fullmatch(r"[0-9]{1,10}", max_age_text) or int(max_age_text) < 0:
            raise ValueError
        fields["max_age"] = int(max_age_text)
    except (TypeError, ValueError):
        errors.append("max_age must be 1..10 decimal digits")
    if fields.get("mode") != "none" and not mx_values:
        errors.append("at least one mx field is required unless mode is none")
    for pattern in mx_values:
        check = pattern[2:] if pattern.startswith("*.") else pattern
        try:
            normalize_domain(check, "MTA-STS mx pattern")
        except AuditError as exc:
            errors.append(str(exc))
    return fields, errors


def mx_matches_pattern(host: str, pattern: str) -> bool:
    host = host.casefold().rstrip(".")
    pattern = pattern.casefold().rstrip(".")
    if not pattern.startswith("*."):
        return host == pattern
    suffix = pattern[2:]
    if not host.endswith(f".{suffix}"):
        return False
    return len(host.split(".")) == len(suffix.split(".")) + 1


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def fetch_mta_sts_policy(domain: str, timeout: float, max_bytes: int) -> tuple[str, dict[str, Any]]:
    url = f"https://mta-sts.{domain}/.well-known/mta-sts.txt"
    request = Request(url, headers={"User-Agent": "analyze-email-effectiveness-dns-audit/1"})
    opener = build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            status = getattr(response, "status", None)
            content_type = response.headers.get_content_type()
            raw = response.read(max_bytes + 1)
    except HTTPError as exc:
        raise AuditError(f"MTA-STS HTTPS returned HTTP {exc.code}; redirects are not followed") from exc
    except (URLError, OSError) as exc:
        raise AuditError(f"MTA-STS HTTPS fetch failed: {exc}") from exc
    if status != 200:
        raise AuditError(f"MTA-STS HTTPS returned HTTP {status}")
    if len(raw) > max_bytes:
        raise AuditError(f"MTA-STS policy exceeds --max-http-bytes ({max_bytes})")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise AuditError("MTA-STS policy is not valid UTF-8") from exc
    return text, {"url": url, "status": status, "content_type": content_type, "bytes": len(raw)}


def audit_mta_sts(
    ctx: AuditContext,
    domain: str,
    mx_hosts: list[str],
    policy_text: str | None,
    fetch_policy: bool,
    timeout: float,
    max_http_bytes: int,
    allow_private_fetch: bool,
) -> dict[str, Any]:
    name = f"_mta-sts.{domain}"
    answer = ctx.query(name, "TXT")
    records = versioned_txt(answer, "STSv1")
    result: dict[str, Any] = {"name": name, "records": records}
    if len(records) > 1:
        ctx.add("error", "mta_sts_multiple_records", f"Multiple MTA-STS TXT records exist at {name}.")
    elif records:
        tags, order, errors = parse_tag_record(records[0])
        result["tags"] = tags
        for error in errors:
            ctx.add("error", "mta_sts_tag_syntax", f"MTA-STS signal at {name} is malformed.", error)
        if order[:1] != ["v"] or tags.get("v", "").casefold() != "stsv1":
            ctx.add("error", "mta_sts_version", f"MTA-STS v=STSv1 is invalid or not first at {name}.")
        if not tags.get("id"):
            ctx.add("error", "mta_sts_id", f"MTA-STS signal at {name} has no non-empty id=.")
    elif fetch_policy:
        ctx.add(
            "warning",
            "mta_sts_signal_missing",
            "MTA-STS HTTPS fetch was requested but no usable TXT signal was found.",
            name,
        )

    policy_host = f"mta-sts.{domain}"
    policy_addresses: list[str] = []
    for rtype in ("A", "AAAA"):
        policy_addresses.extend(ctx.query(policy_host, rtype).values)
    result["policy_host_addresses"] = policy_addresses

    fetched: dict[str, Any] | None = None
    if fetch_policy and policy_text is None and records:
        private_addresses: list[str] = []
        for value in policy_addresses:
            try:
                if not ipaddress.ip_address(value).is_global:
                    private_addresses.append(value)
            except ValueError:
                continue
        if private_addresses and not allow_private_fetch:
            ctx.add(
                "error",
                "mta_sts_private_fetch_blocked",
                "MTA-STS HTTPS fetch was blocked because the policy host resolves to a non-global address.",
                ", ".join(private_addresses),
                "Use --allow-private-fetch only for an explicitly trusted internal target.",
            )
        else:
            try:
                policy_text, fetched = fetch_mta_sts_policy(domain, timeout, max_http_bytes)
            except AuditError as exc:
                ctx.add(
                    "warning",
                    "mta_sts_fetch_failed",
                    f"MTA-STS policy could not be fetched for {domain}.",
                    str(exc),
                    "Check HTTPS status, certificate name/chain, content type, DNS, and policy availability.",
                )
    if fetched:
        result["fetch"] = fetched
        if fetched["content_type"] != "text/plain":
            ctx.add(
                "warning",
                "mta_sts_content_type",
                "MTA-STS HTTPS response is not text/plain.",
                fetched["content_type"],
            )

    if policy_text is not None:
        policy, errors = parse_mta_sts_policy(policy_text)
        result["policy"] = policy
        for error in errors:
            ctx.add("error", "mta_sts_policy_syntax", "The MTA-STS policy is invalid.", error)
        patterns = policy.get("mx", [])
        for host in mx_hosts:
            if patterns and not any(mx_matches_pattern(host, pattern) for pattern in patterns):
                ctx.add(
                    "error",
                    "mta_sts_mx_mismatch",
                    f"MX host {host} is not covered by the MTA-STS policy.",
                    ", ".join(patterns),
                    "Add the intended MX pattern or correct the DNS MX set before enforcing.",
                )
        mode = policy.get("mode")
        if mode == "testing":
            ctx.add("info", "mta_sts_testing", f"MTA-STS for {domain} is in testing mode.")
        elif mode == "none":
            ctx.add("info", "mta_sts_none", f"MTA-STS for {domain} is in none mode.")
    elif records:
        ctx.add(
            "info",
            "mta_sts_policy_not_checked",
            f"MTA-STS signaling exists for {domain}, but the HTTPS policy body was not checked.",
            action="Use --fetch-mta-sts or --mta-sts-policy-file to validate the policy and MX coverage.",
        )
    return result


def audit_tlsrpt(ctx: AuditContext, domain: str) -> dict[str, Any]:
    name = f"_smtp._tls.{domain}"
    answer = ctx.query(name, "TXT")
    records = versioned_txt(answer, "TLSRPTv1")
    result: dict[str, Any] = {"name": name, "records": records}
    if not records:
        return result
    if len(records) > 1:
        ctx.add("error", "tlsrpt_multiple_records", f"Multiple TLS-RPT records exist at {name}.")
        return result
    tags, order, errors = parse_tag_record(records[0])
    result["tags"] = tags
    for error in errors:
        ctx.add("error", "tlsrpt_tag_syntax", f"TLS-RPT record {name} is malformed.", error)
    if order[:1] != ["v"] or tags.get("v", "").casefold() != "tlsrptv1":
        ctx.add("error", "tlsrpt_version", f"TLS-RPT version is invalid or not first at {name}.")
    uris = parse_report_uris(tags.get("rua", ""))
    result["rua"] = uris
    if not uris:
        ctx.add("error", "tlsrpt_rua_missing", f"TLS-RPT record {name} has no rua= destination.")
    for uri in uris:
        parsed = urlsplit(uri)
        if parsed.scheme.casefold() not in {"mailto", "https"}:
            ctx.add("error", "tlsrpt_uri", f"TLS-RPT rua= uses an unsupported URI scheme.", uri)
        elif parsed.scheme.casefold() == "mailto" and not uri_destination_domain(uri):
            ctx.add("error", "tlsrpt_uri", "TLS-RPT mailto destination is malformed.", uri)
        elif parsed.scheme.casefold() == "https" and not validate_https_url(uri):
            ctx.add("error", "tlsrpt_uri", "TLS-RPT HTTPS destination is malformed.", uri)
    return result


def normalized_address_values(values: list[str]) -> set[str]:
    normalized: set[str] = set()
    for value in values:
        try:
            normalized.add(str(ipaddress.ip_address(value)))
        except ValueError:
            continue
    return normalized


def audit_sending_hosts(
    ctx: AuditContext,
    sending_ips: list[str],
    helo_domain: str | None,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    if not sending_ips:
        ctx.add(
            "info",
            "sending_ip_not_supplied",
            "No sending IP was supplied, so PTR and forward-confirmed reverse DNS were not checked.",
        )
    for ip_text in sending_ips:
        address = ipaddress.ip_address(ip_text)
        reverse_name = address.reverse_pointer
        ptr_answer = ctx.query(reverse_name, "PTR")
        ptr_hosts: list[dict[str, Any]] = []
        if not answer_has_data(ptr_answer):
            ctx.add(
                "error",
                "ptr_missing",
                f"Sending IP {address} has no observed PTR hostname.",
                reverse_name,
                "Configure PTR through the IP owner/provider and confirm forward resolution.",
            )
        for raw_host in ptr_answer.values:
            try:
                host = normalize_domain(raw_host, "PTR hostname")
            except AuditError as exc:
                ctx.add("error", "ptr_hostname", f"PTR for {address} is malformed.", str(exc))
                continue
            a_values = ctx.query(host, "A").values
            aaaa_values = ctx.query(host, "AAAA").values
            forward = normalized_address_values(a_values + aaaa_values)
            confirmed = str(address) in forward
            ptr_hosts.append(
                {
                    "hostname": host,
                    "a": a_values,
                    "aaaa": aaaa_values,
                    "forward_confirmed": confirmed,
                }
            )
            if not confirmed:
                ctx.add(
                    "error",
                    "ptr_forward_mismatch",
                    f"PTR hostname {host} does not resolve forward to sending IP {address}.",
                    f"Observed addresses: {', '.join(sorted(forward)) or 'none'}",
                    "Make PTR and forward A/AAAA agree for the actual outbound SMTP IP.",
                )
        results.append({"ip": str(address), "reverse_name": reverse_name, "ptr": ptr_hosts})

    helo_result: dict[str, Any] | None = None
    if helo_domain:
        a_values = ctx.query(helo_domain, "A").values
        aaaa_values = ctx.query(helo_domain, "AAAA").values
        helo_addresses = normalized_address_values(a_values + aaaa_values)
        supplied = {str(ipaddress.ip_address(value)) for value in sending_ips}
        helo_result = {
            "domain": helo_domain,
            "a": a_values,
            "aaaa": aaaa_values,
            "matches_supplied_ip": sorted(helo_addresses & supplied),
        }
        if sending_ips and not helo_addresses.intersection(supplied):
            ctx.add(
                "warning",
                "helo_forward_mismatch",
                f"HELO/EHLO name {helo_domain} does not resolve to a supplied sending IP.",
                f"HELO addresses: {', '.join(sorted(helo_addresses)) or 'none'}",
                "Confirm the real SMTP HELO and outbound IP set before changing DNS.",
            )
    return {"ips": results, "helo": helo_result}


def audit_custom_queries(ctx: AuditContext, queries: list[tuple[str, str]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for name, rtype in queries:
        results.append(asdict(ctx.query(name, rtype)))
    return results


@dataclass
class AuditOptions:
    domain: str
    header_from_domain: str
    mail_from_domain: str
    org_domain: str | None
    dkim_identities: list[tuple[str, str]]
    discover_dkim: bool
    message_evidence: dict[str, Any] | None
    bimi_selectors: list[str]
    sending_ips: list[str]
    helo_domain: str | None
    custom_queries: list[tuple[str, str]]
    max_spf_depth: int
    fetch_mta_sts: bool
    mta_sts_policy_text: str | None
    timeout: float
    max_http_bytes: int
    allow_private_fetch: bool


def run_audit(resolver: ResolverBackend, options: AuditOptions, max_queries: int) -> dict[str, Any]:
    ctx = AuditContext(resolver=resolver, max_queries=max_queries)
    inventory = audit_inventory(ctx, options.domain)
    spf = audit_spf(ctx, options.mail_from_domain, options.max_spf_depth)
    discovered_dkim: list[tuple[str, str]] = []
    if options.discover_dkim:
        discovery_plan = dkim_discovery_plan(options.header_from_domain, inventory, spf)
        discovered_dkim, dkim_discovery = discover_dkim_identities(ctx, discovery_plan)
    else:
        dkim_discovery = {
            "enabled": False,
            "domain": options.header_from_domain,
            "provider_hints": [],
            "candidate_selectors": [],
            "positive_probes": [],
            "found_identities": [],
            "exhaustive": False,
        }
    all_dkim_identities = sorted(set(options.dkim_identities) | set(discovered_dkim))
    if all_dkim_identities or not options.discover_dkim:
        dkim = audit_dkim(ctx, all_dkim_identities)
    else:
        dkim = []
    dmarc = audit_dmarc(
        ctx,
        options.header_from_domain,
        options.org_domain,
        options.mail_from_domain,
        [domain for _, domain in all_dkim_identities],
    )
    bimi = audit_bimi(ctx, options.header_from_domain, options.bimi_selectors, dmarc)
    mx_hosts = [item["exchange"] for item in inventory["mx"]["records"] if item["exchange"] != "."]
    mta_sts = audit_mta_sts(
        ctx,
        options.domain,
        mx_hosts,
        options.mta_sts_policy_text,
        options.fetch_mta_sts,
        options.timeout,
        options.max_http_bytes,
        options.allow_private_fetch,
    )
    tlsrpt = audit_tlsrpt(ctx, options.domain)
    sending_hosts = audit_sending_hosts(ctx, options.sending_ips, options.helo_domain)
    custom = audit_custom_queries(ctx, options.custom_queries)

    counts = {severity: 0 for severity in SEVERITY_ORDER}
    for finding in ctx.findings:
        counts[finding.severity] += 1
    sorted_findings = sorted(
        ctx.findings,
        key=lambda item: (SEVERITY_ORDER[item.severity], item.code, item.summary),
    )
    records = sorted(ctx.records.values(), key=lambda item: (item.name, item.rtype))
    return {
        "schema_version": "2.0",
        "audit_type": "email_dns_evidence",
        "resolver": resolver.description,
        "inputs": {
            "domain": options.domain,
            "header_from_domain": options.header_from_domain,
            "mail_from_domain": options.mail_from_domain,
            "expected_legacy_organizational_domain": options.org_domain,
            "dkim_identities": [
                {"selector": selector, "domain": domain}
                for selector, domain in all_dkim_identities
            ],
            "explicit_or_message_dkim_identities": [
                {"selector": selector, "domain": domain}
                for selector, domain in options.dkim_identities
            ],
            "message_evidence": options.message_evidence,
            "dkim_candidate_discovery": options.discover_dkim,
            "bimi_selectors": options.bimi_selectors,
            "sending_ips": options.sending_ips,
            "helo_domain": options.helo_domain,
        },
        "summary": {"query_count": len(records), **counts},
        "analysis": {
            "inventory_and_mx": inventory,
            "spf": spf,
            "dkim": dkim,
            "dkim_discovery": dkim_discovery,
            "dmarc": dmarc,
            "bimi": bimi,
            "mta_sts": mta_sts,
            "tlsrpt": tlsrpt,
            "sending_hosts": sending_hosts,
            "custom_queries": custom,
        },
        "findings": [asdict(item) for item in sorted_findings],
        "records": [asdict(item) for item in records],
        "limitations": [
            "DNS is a time-specific snapshot; cached and geographically distributed answers can differ.",
            "SPF was statically expanded, not evaluated for a complete SMTP transaction.",
            (
                "DKIM selectors are not enumerable; explicit/message-derived identities and any "
                "positive bounded candidate probes are not an exhaustive selector inventory."
            ),
            "DNS keys and policies do not prove that a real message passed SPF, DKIM, or DMARC.",
            (
                "DMARC policy discovery and current alignment use the RFC 9989 DNS Tree Walk; "
                "receivers still using public-suffix-list logic can reach a different result."
            ),
            "DS/DNSKEY presence is not chain validation; AD reflects the configured resolver's assertion.",
            "MTA-STS/DANE DNS checks do not test live SMTP STARTTLS or the port-25 certificate.",
            "Reputation, blocklists, complaints, consent, inbox placement, and legal compliance are out of scope.",
        ],
    }


def render_text(report: dict[str, Any], show_records: bool = False) -> str:
    summary = report["summary"]
    inputs = report["inputs"]
    lines = [
        f"Email DNS evidence audit: {inputs['domain']}",
        f"Resolver: {report['resolver']}",
        (
            f"Identities: Header From={inputs['header_from_domain']}; "
            f"MAIL FROM={inputs['mail_from_domain']}; "
            "legacy/public-suffix org="
            f"{inputs['expected_legacy_organizational_domain'] or 'not supplied'}"
        ),
        (
            f"Summary: {summary['error']} error(s), {summary['warning']} warning(s), "
            f"{summary['info']} info finding(s), {summary['query_count']} DNS query result(s)"
        ),
        "",
        "Findings:",
    ]
    if report["findings"]:
        for finding in report["findings"]:
            lines.append(f"[{finding['severity'].upper()}] {finding['code']}: {finding['summary']}")
            if finding.get("evidence"):
                lines.append(f"  Evidence: {finding['evidence']}")
            if finding.get("action"):
                lines.append(f"  Action: {finding['action']}")
    else:
        lines.append("No findings.")
    if show_records:
        lines.extend(["", "DNS records:"])
        for answer in report["records"]:
            values = " | ".join(answer["values"]) if answer["values"] else "-"
            lines.append(
                f"{answer['name']} {answer['rtype']} {answer['status']} "
                f"ttl={answer['ttl']} ad={answer['ad']} :: {values}"
            )
    lines.extend(["", "Limits:"])
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines)


def parse_dkim_identity(value: str, default_domain: str) -> tuple[str, str]:
    if "@" in value:
        raw_selector, raw_domain = value.rsplit("@", 1)
        domain = normalize_domain(raw_domain, "DKIM d= domain")
    else:
        raw_selector = value
        domain = default_domain
    return normalize_selector(raw_selector, "DKIM selector"), domain


def parse_custom_query(value: str) -> tuple[str, str]:
    if ":" not in value:
        raise AuditError(f"--query must be NAME:TYPE: {value!r}")
    raw_name, raw_type = value.rsplit(":", 1)
    return normalize_dns_name(raw_name, "custom query name"), normalize_record_type(raw_type)


def message_address_domain(value: str) -> str | None:
    address = parseaddr(value)[1].strip()
    if "@" not in address:
        return None
    try:
        return normalize_domain(address.rsplit("@", 1)[1], "message address domain")
    except AuditError:
        return None


def read_message_evidence(path: Path, max_bytes: int) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise AuditError(f"message is not a file: {path}")
        size = path.stat().st_size
        if size > max_bytes:
            raise AuditError(f"message exceeds --max-message-bytes ({max_bytes})")
        raw = path.read_bytes()
    except OSError as exc:
        raise AuditError(f"cannot read message {path}: {exc}") from exc

    message = BytesParser(policy=policy.default).parsebytes(raw)
    header_from_domains = sorted(
        {
            domain
            for _, address in getaddresses(message.get_all("From", []))
            if (domain := message_address_domain(address))
        }
    )
    return_path = str(message.get("Return-Path", ""))
    mail_from_domain = message_address_domain(return_path)
    dkim_identities: set[tuple[str, str]] = set()
    rejected_signatures: list[str] = []
    for raw_signature in message.get_all("DKIM-Signature", []):
        tags, _, _ = parse_tag_record(str(raw_signature))
        try:
            if tags.get("d") and tags.get("s"):
                dkim_identities.add(
                    (
                        normalize_selector(tags["s"], "message DKIM selector"),
                        normalize_domain(tags["d"], "message DKIM d= domain"),
                    )
                )
        except AuditError as exc:
            rejected_signatures.append(str(exc))
    return {
        "path_name": path.name,
        "bytes": len(raw),
        "header_from_domains": header_from_domains,
        "mail_from_domain": mail_from_domain,
        "dkim_identities": [
            {"selector": selector, "domain": domain}
            for selector, domain in sorted(dkim_identities)
        ],
        "rejected_signature_hints": rejected_signatures,
        "parser_defects": [
            f"{type(defect).__name__}: {defect}"
            for defect in message.defects
        ],
        "trust_boundary": (
            "Header identities and DKIM d=/s= are message claims used to locate evidence; "
            "this audit does not trust Authentication-Results or verify a signature."
        ),
    }


def read_policy_file(path: Path, max_bytes: int) -> str:
    try:
        if not path.is_file():
            raise AuditError(f"MTA-STS policy is not a file: {path}")
        if path.stat().st_size > max_bytes:
            raise AuditError(f"MTA-STS policy exceeds --max-http-bytes ({max_bytes})")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise AuditError(f"cannot read MTA-STS policy {path}: {exc}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("domain", help="Primary domain to inventory and use for inbound transport checks.")
    parser.add_argument("--header-from-domain", help="Visible RFC 5322 From domain. Default: domain.")
    parser.add_argument("--mail-from-domain", help="SMTP MAIL FROM / return-path domain for SPF. Default: domain.")
    parser.add_argument(
        "--org-domain",
        help=(
            "Expected legacy/public-suffix Organizational Domain for compatibility comparison. "
            "Current DMARC discovery uses RFC 9989 Tree Walk automatically."
        ),
    )
    parser.add_argument(
        "--message",
        type=Path,
        help=(
            "Optional received .eml used to derive Header From, Return-Path, and claimed DKIM d=/s= "
            "identities. CLI identity flags take precedence."
        ),
    )
    parser.add_argument(
        "--max-message-bytes",
        type=int,
        default=MAX_MESSAGE_BYTES,
        help=f"Maximum --message size. Default: {MAX_MESSAGE_BYTES}.",
    )
    parser.add_argument(
        "--dkim",
        action="append",
        default=[],
        metavar="SELECTOR[@DOMAIN]",
        help="DKIM selector and optional d= domain. Repeat for every active selector.",
    )
    parser.add_argument(
        "--dkim-domain",
        help="Default d= domain for --dkim entries without @. Default: Header From domain.",
    )
    parser.add_argument(
        "--discover-dkim",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Probe a bounded common/provider-informed selector set on the Header From domain. "
            "Positive results are evidence; negative guesses never prove DKIM absence. Default: enabled."
        ),
    )
    parser.add_argument(
        "--bimi-selector",
        action="append",
        default=[],
        help="BIMI selector. Repeat as needed. Default: default.",
    )
    parser.add_argument("--sending-ip", action="append", default=[], help="Outbound SMTP IPv4/IPv6. Repeat.")
    parser.add_argument("--helo-domain", help="Actual SMTP HELO/EHLO domain to compare with supplied IPs.")
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        metavar="NAME:TYPE",
        help="Additional provider-specific DNS query. Repeat as needed.",
    )
    parser.add_argument("--fixture", type=Path, help="Offline JSON DNS fixture; disables live DNS.")
    parser.add_argument("--resolver", help="Recursive resolver IPv4/IPv6 for live DNS. Default: system resolver.")
    parser.add_argument("--tcp", action="store_true", help="Use DNS over TCP for live queries.")
    parser.add_argument("--timeout", type=float, default=5.0, help="Per-resolution/HTTPS timeout seconds.")
    parser.add_argument("--max-queries", type=int, default=200, help="Maximum unique DNS queries. Default: 200.")
    parser.add_argument("--max-spf-depth", type=int, default=12, help="Maximum SPF dependency depth.")
    mta_group = parser.add_mutually_exclusive_group()
    mta_group.add_argument(
        "--fetch-mta-sts",
        action="store_true",
        help="Explicitly fetch and validate the MTA-STS HTTPS policy; redirects are disabled.",
    )
    mta_group.add_argument(
        "--mta-sts-policy-file",
        type=Path,
        help="Analyze an offline MTA-STS policy body instead of fetching it.",
    )
    parser.add_argument(
        "--allow-private-fetch",
        action="store_true",
        help="Allow explicit MTA-STS HTTPS fetch when DNS returns a non-global IP.",
    )
    parser.add_argument(
        "--max-http-bytes",
        type=int,
        default=MAX_POLICY_BYTES,
        help=f"Maximum MTA-STS HTTPS/file body. Default: {MAX_POLICY_BYTES}.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    parser.add_argument("--show-records", action="store_true", help="Include raw DNS answers in text output.")
    parser.add_argument(
        "--fail-on",
        choices=("never", "error", "warning"),
        default="never",
        help="Return exit 1 at the selected finding threshold. Default: never.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.timeout <= 0:
            raise AuditError("--timeout must be positive")
        if args.max_queries <= 0:
            raise AuditError("--max-queries must be positive")
        if args.max_spf_depth < 0:
            raise AuditError("--max-spf-depth cannot be negative")
        if args.max_http_bytes <= 0:
            raise AuditError("--max-http-bytes must be positive")
        if args.max_message_bytes <= 0:
            raise AuditError("--max-message-bytes must be positive")

        domain = normalize_domain(args.domain)
        message_evidence = (
            read_message_evidence(args.message, args.max_message_bytes)
            if args.message
            else None
        )
        message_from_domains = (
            list(message_evidence["header_from_domains"])
            if message_evidence
            else []
        )
        if args.header_from_domain:
            header_from = normalize_domain(args.header_from_domain, "Header From domain")
        elif len(message_from_domains) == 1:
            header_from = message_from_domains[0]
        elif len(message_from_domains) > 1:
            raise AuditError(
                "--message contains multiple Header From domains; supply --header-from-domain explicitly"
            )
        else:
            header_from = domain
        mail_from = normalize_domain(
            args.mail_from_domain
            or (message_evidence or {}).get("mail_from_domain")
            or domain,
            "MAIL FROM domain",
        )
        org_domain = normalize_domain(args.org_domain, "organizational domain") if args.org_domain else None
        if org_domain and not (
            header_from == org_domain or header_from.endswith(f".{org_domain}")
        ):
            raise AuditError("--org-domain must be the Header From domain or its DNS ancestor")
        default_dkim_domain = normalize_domain(
            args.dkim_domain or header_from,
            "default DKIM domain",
        )
        dkim_identity_set = {
                parse_dkim_identity(value, default_dkim_domain)
                for value in args.dkim
        }
        if message_evidence:
            dkim_identity_set.update(
                (
                    str(item["selector"]),
                    str(item["domain"]),
                )
                for item in message_evidence["dkim_identities"]
            )
        dkim_identities = sorted(dkim_identity_set)
        bimi_selectors = sorted(
            {normalize_selector(value, "BIMI selector") for value in args.bimi_selector}
            or {"default"}
        )
        sending_ips: list[str] = []
        for value in args.sending_ip:
            try:
                sending_ips.append(str(ipaddress.ip_address(value)))
            except ValueError as exc:
                raise AuditError(f"invalid --sending-ip: {value!r}") from exc
        sending_ips = sorted(set(sending_ips))
        helo_domain = normalize_domain(args.helo_domain, "HELO domain") if args.helo_domain else None
        custom_queries = [parse_custom_query(value) for value in args.query]
        policy_text = (
            read_policy_file(args.mta_sts_policy_file, args.max_http_bytes)
            if args.mta_sts_policy_file
            else None
        )
        resolver: ResolverBackend
        if args.fixture:
            resolver = FixtureResolver.from_file(args.fixture)
        else:
            resolver = LiveResolver(args.timeout, args.resolver, args.tcp)
        options = AuditOptions(
            domain=domain,
            header_from_domain=header_from,
            mail_from_domain=mail_from,
            org_domain=org_domain,
            dkim_identities=dkim_identities,
            discover_dkim=args.discover_dkim,
            message_evidence=message_evidence,
            bimi_selectors=bimi_selectors,
            sending_ips=sending_ips,
            helo_domain=helo_domain,
            custom_queries=custom_queries,
            max_spf_depth=args.max_spf_depth,
            fetch_mta_sts=args.fetch_mta_sts,
            mta_sts_policy_text=policy_text,
            timeout=args.timeout,
            max_http_bytes=args.max_http_bytes,
            allow_private_fetch=args.allow_private_fetch,
        )
        report = run_audit(resolver, options, args.max_queries)
    except AuditError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report, args.show_records))

    if args.fail_on == "error" and report["summary"]["error"]:
        return 1
    if args.fail_on == "warning" and (
        report["summary"]["error"] or report["summary"]["warning"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
