#!/usr/bin/env python3
"""Deterministic tests for audit_email_dns.py."""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from audit_email_dns import (
    AuditOptions,
    DNSAnswer,
    FixtureResolver,
    dmarc_tree_walk_targets,
    mx_matches_pattern,
    parse_mta_sts_policy,
    read_message_evidence,
    rsa_public_key_bits,
    run_audit,
)


def der_length(length: int) -> bytes:
    if length < 128:
        return bytes([length])
    encoded = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(encoded)]) + encoded


def der_tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + der_length(len(value)) + value


def rsa_pkcs1_key(bits: int) -> bytes:
    modulus = b"\x00" + b"\x80" + (b"\x00" * (bits // 8 - 1))
    exponent = b"\x01\x00\x01"
    return der_tlv(0x30, der_tlv(0x02, modulus) + der_tlv(0x02, exponent))


def answer(
    name: str,
    rtype: str,
    *values: str,
    ad: bool | None = None,
    status: str = "ok",
) -> DNSAnswer:
    return DNSAnswer(
        name=name,
        rtype=rtype,
        status=status,
        values=list(values),
        ttl=300 if status == "ok" else None,
        ad=ad,
    )


def resolver_from(*answers: DNSAnswer) -> FixtureResolver:
    return FixtureResolver({(item.name, item.rtype): item for item in answers})


def default_options(**overrides: object) -> AuditOptions:
    values: dict[str, object] = {
        "domain": "example.com",
        "header_from_domain": "example.com",
        "mail_from_domain": "bounce.example.com",
        "org_domain": "example.com",
        "dkim_identities": [("news", "example.com")],
        "discover_dkim": True,
        "message_evidence": None,
        "bimi_selectors": ["default"],
        "sending_ips": ["192.0.2.25"],
        "helo_domain": "mail.example.com",
        "custom_queries": [],
        "max_spf_depth": 12,
        "fetch_mta_sts": False,
        "mta_sts_policy_text": (
            "version: STSv1\n"
            "mode: enforce\n"
            "mx: mx1.example.com\n"
            "max_age: 604800\n"
        ),
        "timeout": 1.0,
        "max_http_bytes": 1024,
        "allow_private_fetch": False,
    }
    values.update(overrides)
    return AuditOptions(**values)  # type: ignore[arg-type]


class AuditEmailDNSTests(unittest.TestCase):
    def healthy_resolver(self) -> FixtureResolver:
        rsa_value = base64.b64encode(rsa_pkcs1_key(2048)).decode()
        tlsa_hash = "ab" * 32
        return resolver_from(
            answer("example.com", "A", "192.0.2.10"),
            answer("example.com", "MX", "10 mx1.example.com."),
            answer("example.com", "NS", "ns1.example.net."),
            answer("example.com", "SOA", "ns1.example.net. hostmaster.example.com. 1 3600 600 86400 300"),
            answer("example.com", "CAA", '0 issue "letsencrypt.org"'),
            answer("example.com", "DS", "12345 13 2 " + ("cd" * 32), ad=True),
            answer("example.com", "DNSKEY", "257 3 13 AAAA", ad=True),
            answer("mx1.example.com", "A", "192.0.2.20"),
            answer("_25._tcp.mx1.example.com", "TLSA", f"3 1 1 {tlsa_hash}", ad=True),
            answer(
                "bounce.example.com",
                "TXT",
                "v=spf1 include:_spf.vendor.example -all",
            ),
            answer("_spf.vendor.example", "TXT", "v=spf1 ip4:192.0.2.0/24 -all"),
            answer(
                "news._domainkey.example.com",
                "TXT",
                f"v=DKIM1; k=rsa; p={rsa_value}",
            ),
            answer(
                "_dmarc.example.com",
                "TXT",
                "v=DMARC1; p=reject; rua=mailto:dmarc@example.com; adkim=s; aspf=r",
            ),
            answer(
                "default._bimi.example.com",
                "TXT",
                "v=BIMI1; l=https://assets.example.com/brand.svg; "
                "a=https://assets.example.com/mark.pem",
            ),
            answer("_mta-sts.example.com", "TXT", "v=STSv1; id=2026072901"),
            answer("mta-sts.example.com", "A", "192.0.2.30"),
            answer(
                "_smtp._tls.example.com",
                "TXT",
                "v=TLSRPTv1; rua=mailto:tls-reports@example.com",
            ),
            answer("click.example.com", "CNAME", "tracking.vendor.example."),
            answer("25.2.0.192.in-addr.arpa", "PTR", "mail.example.com."),
            answer("mail.example.com", "A", "192.0.2.25"),
        )

    def test_comprehensive_fixture_covers_advanced_surfaces(self) -> None:
        report = run_audit(
            self.healthy_resolver(),
            default_options(custom_queries=[("click.example.com", "CNAME")]),
            max_queries=200,
        )
        codes = {finding["code"] for finding in report["findings"]}
        self.assertEqual(report["summary"]["error"], 0)
        self.assertEqual(report["analysis"]["dkim"][0]["rsa_bits"], 2048)
        self.assertEqual(report["analysis"]["dmarc"]["effective_policy"], "reject")
        self.assertEqual(len(report["analysis"]["spf"]["graph"]), 2)
        self.assertEqual(report["analysis"]["mta_sts"]["policy"]["mode"], "enforce")
        self.assertEqual(
            report["analysis"]["tlsrpt"]["rua"],
            ["mailto:tls-reports@example.com"],
        )
        self.assertEqual(
            report["analysis"]["custom_queries"][0]["values"],
            ["tracking.vendor.example."],
        )
        self.assertIn("dnssec_ad_signal", codes)
        self.assertIn("dane_tlsa_secure_signal", codes)
        self.assertTrue(
            report["analysis"]["sending_hosts"]["ips"][0]["ptr"][0]["forward_confirmed"]
        )

    def test_spf_expansion_flags_budget_voids_and_cycle(self) -> None:
        root_terms = " ".join(f"include:i{index}.example.net" for index in range(12))
        records = [
            answer("example.com", "MX", "0 ."),
            answer("bounce.example.com", "TXT", f"v=spf1 {root_terms} -all"),
            answer("_dmarc.example.com", "TXT", "v=DMARC1; p=none"),
        ]
        for index in range(8):
            records.append(answer(f"i{index}.example.net", "TXT", "v=spf1 -all"))
        records.append(
            answer("i8.example.net", "TXT", "v=spf1 include:bounce.example.com -all")
        )
        options = default_options(
            dkim_identities=[],
            sending_ips=[],
            helo_domain=None,
            mta_sts_policy_text=None,
        )
        report = run_audit(resolver_from(*records), options, max_queries=200)
        codes = {finding["code"] for finding in report["findings"]}
        self.assertIn("spf_lookup_budget_risk", codes)
        self.assertIn("spf_void_lookup_risk", codes)
        self.assertIn("spf_cycle", codes)
        self.assertGreater(report["analysis"]["spf"]["static_lookup_terms"], 10)

    def test_malformed_records_and_ptr_mismatch_are_detected(self) -> None:
        weak_key = base64.b64encode(rsa_pkcs1_key(512)).decode()
        resolver = resolver_from(
            answer("example.com", "MX", "0 .", "10 mx.example.com."),
            answer("mx.example.com", "A", "192.0.2.10"),
            answer("bounce.example.com", "TXT", "v=spf1 +all", "v=spf1 -all"),
            answer(
                "news._domainkey.example.com",
                "TXT",
                f"v=DKIM1; k=rsa; p={weak_key}",
            ),
            answer("_dmarc.example.com", "TXT", "v=DMARC1; p=invalid; pct=120"),
            answer("25.2.0.192.in-addr.arpa", "PTR", "mail.example.com."),
            answer("mail.example.com", "A", "192.0.2.99"),
        )
        report = run_audit(
            resolver,
            default_options(mta_sts_policy_text=None),
            max_queries=200,
        )
        codes = {finding["code"] for finding in report["findings"]}
        self.assertIn("null_mx_conflict", codes)
        self.assertIn("spf_multiple_records", codes)
        self.assertIn("dkim_rsa_too_small", codes)
        self.assertIn("dmarc_policy", codes)
        self.assertIn("dmarc_legacy_pct", codes)
        self.assertIn("dmarc_legacy_tags", codes)
        self.assertIn("ptr_forward_mismatch", codes)

    def test_mta_sts_parser_and_single_label_wildcard_matching(self) -> None:
        policy, errors = parse_mta_sts_policy(
            "version: STSv1\nmode: testing\nmx: *.example.net\nmax_age: 86400\n"
        )
        self.assertEqual(errors, [])
        self.assertEqual(policy["max_age"], 86400)
        self.assertTrue(mx_matches_pattern("mx.example.net", "*.example.net"))
        self.assertFalse(mx_matches_pattern("a.mx.example.net", "*.example.net"))
        _, bad_errors = parse_mta_sts_policy(
            "version: STSv1\nmode: enforce\nmax_age: forever\n"
        )
        self.assertTrue(any("max_age" in error for error in bad_errors))
        self.assertTrue(any("mx field" in error for error in bad_errors))

    def test_rsa_der_bit_length(self) -> None:
        self.assertEqual(rsa_public_key_bits(rsa_pkcs1_key(1024)), 1024)
        self.assertEqual(rsa_public_key_bits(rsa_pkcs1_key(2048)), 2048)

    def test_fixture_follows_provider_dkim_cname(self) -> None:
        rsa_value = base64.b64encode(rsa_pkcs1_key(2048)).decode()
        resolver = resolver_from(
            answer("example.com", "MX", "0 ."),
            answer("example.com", "TXT", "v=spf1 -all"),
            answer("_dmarc.example.com", "TXT", "v=DMARC1; p=reject"),
            answer(
                "news._domainkey.example.com",
                "CNAME",
                "news.keys.provider.example.",
            ),
            answer(
                "news.keys.provider.example",
                "TXT",
                f"v=DKIM1; k=rsa; p={rsa_value}",
            ),
        )
        report = run_audit(
            resolver,
            default_options(
                mail_from_domain="example.com",
                sending_ips=[],
                helo_domain=None,
                mta_sts_policy_text=None,
            ),
            max_queries=200,
        )
        dkim = report["analysis"]["dkim"][0]
        self.assertEqual(dkim["cname"], ["news.keys.provider.example."])
        self.assertEqual(dkim["rsa_bits"], 2048)
        self.assertNotIn(
            "dkim_key_missing",
            {finding["code"] for finding in report["findings"]},
        )

    def test_deep_dmarc_tree_walk_is_bounded_to_eight_queries(self) -> None:
        domain = "a.b.c.d.e.f.g.h.i.j.k.example.com"
        targets = dmarc_tree_walk_targets(domain)
        self.assertEqual(len(targets), 8)
        self.assertEqual(targets[0], domain)
        self.assertEqual(targets[1], "g.h.i.j.k.example.com")
        self.assertEqual(targets[-1], "com")

    def test_dmarc_psd_and_nonexistent_subdomain_policy_are_applied(self) -> None:
        resolver = resolver_from(
            answer("ghost.giant.bank.example", "MX", "0 ."),
            answer("ghost.giant.bank.example", "TXT", "v=spf1 -all"),
            answer("ghost.giant.bank.example", "A", status="nxdomain"),
            answer(
                "_dmarc.giant.bank.example",
                "TXT",
                "v=DMARC1; p=reject; np=reject; t=y",
            ),
            answer(
                "_dmarc.bank.example",
                "TXT",
                "v=DMARC1; p=reject; psd=y",
            ),
        )
        report = run_audit(
            resolver,
            default_options(
                domain="ghost.giant.bank.example",
                header_from_domain="ghost.giant.bank.example",
                mail_from_domain="mail.giant.bank.example",
                org_domain=None,
                dkim_identities=[],
                discover_dkim=False,
                sending_ips=[],
                helo_domain=None,
                mta_sts_policy_text=None,
            ),
            max_queries=200,
        )
        dmarc = report["analysis"]["dmarc"]
        self.assertEqual(dmarc["tree_walk"]["organizational_domain"], "giant.bank.example")
        self.assertEqual(dmarc["policy_source"], "giant.bank.example")
        self.assertEqual(dmarc["effective_policy_tag"], "np")
        self.assertEqual(dmarc["requested_policy"], "reject")
        self.assertEqual(dmarc["effective_policy"], "quarantine")
        self.assertEqual(dmarc["test_mode"], "y")

    def test_dmarc_psd_n_marks_organizational_boundary(self) -> None:
        resolver = resolver_from(
            answer("a.mail.example.com", "MX", "0 ."),
            answer("a.mail.example.com", "TXT", "v=spf1 -all"),
            answer(
                "_dmarc.mail.example.com",
                "TXT",
                "v=DMARC1; p=quarantine; psd=n",
            ),
        )
        report = run_audit(
            resolver,
            default_options(
                domain="a.mail.example.com",
                header_from_domain="a.mail.example.com",
                mail_from_domain="a.mail.example.com",
                org_domain=None,
                dkim_identities=[],
                discover_dkim=False,
                sending_ips=[],
                helo_domain=None,
                mta_sts_policy_text=None,
            ),
            max_queries=200,
        )
        dmarc = report["analysis"]["dmarc"]
        self.assertEqual(dmarc["tree_walk"]["organizational_domain"], "mail.example.com")
        self.assertEqual(dmarc["policy_source"], "mail.example.com")

    def test_provider_evidence_discovers_zmail_without_claiming_enumeration(self) -> None:
        rsa_value = base64.b64encode(rsa_pkcs1_key(2048)).decode()
        resolver = resolver_from(
            answer("example.com", "MX", "10 mx.zoho.com."),
            answer("example.com", "TXT", "v=spf1 include:zoho.com -all"),
            answer("zoho.com", "TXT", "v=spf1 -all"),
            answer("_dmarc.example.com", "TXT", "v=DMARC1; p=none"),
            answer(
                "zmail._domainkey.example.com",
                "TXT",
                f"v=DKIM1; k=rsa; p={rsa_value}",
            ),
        )
        report = run_audit(
            resolver,
            default_options(
                mail_from_domain="example.com",
                dkim_identities=[],
                sending_ips=[],
                helo_domain=None,
                mta_sts_policy_text=None,
            ),
            max_queries=200,
        )
        discovery = report["analysis"]["dkim_discovery"]
        self.assertIn(
            {"selector": "zmail", "domain": "example.com"},
            discovery["found_identities"],
        )
        self.assertFalse(discovery["exhaustive"])
        self.assertTrue(
            any("Zoho-hosted" in hint["label"] for hint in discovery["provider_hints"])
        )

    def test_unsuccessful_selector_discovery_never_claims_dkim_missing(self) -> None:
        resolver = resolver_from(
            answer("example.com", "MX", "0 ."),
            answer("example.com", "TXT", "v=spf1 -all"),
            answer("_dmarc.example.com", "TXT", "v=DMARC1; p=none"),
        )
        report = run_audit(
            resolver,
            default_options(
                mail_from_domain="example.com",
                dkim_identities=[],
                sending_ips=[],
                helo_domain=None,
                mta_sts_policy_text=None,
            ),
            max_queries=200,
        )
        codes = {finding["code"] for finding in report["findings"]}
        self.assertIn("dkim_candidate_discovery_inconclusive", codes)
        self.assertNotIn("dkim_key_missing", codes)

    def test_message_evidence_derives_claimed_identities(self) -> None:
        raw = (
            b"From: Team <hello@example.com>\r\n"
            b"Return-Path: <bounce@mail.example.com>\r\n"
            b"DKIM-Signature: v=1; a=rsa-sha256; d=sign.example.com; s=zmail;\r\n"
            b" h=from:subject; bh=x; b=y\r\n"
            b"Subject: Update\r\n\r\nHello\r\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "received.eml"
            path.write_bytes(raw)
            evidence = read_message_evidence(path, 1024 * 1024)
        self.assertEqual(evidence["header_from_domains"], ["example.com"])
        self.assertEqual(evidence["mail_from_domain"], "mail.example.com")
        self.assertEqual(
            evidence["dkim_identities"],
            [{"selector": "zmail", "domain": "sign.example.com"}],
        )
        self.assertIn("does not trust Authentication-Results", evidence["trust_boundary"])

    def test_cli_offline_fixture_is_machine_readable_and_report_only_by_default(self) -> None:
        fixture = {
            "records": {
                "example.com|MX": ["0 ."],
                "example.com|TXT": ["v=spf1 -all"],
                "_dmarc.example.com|TXT": ["v=DMARC1; p=reject"],
            }
        }
        script = Path(__file__).with_name("audit_email_dns.py")
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_path = Path(temp_dir) / "dns.json"
            fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "example.com",
                    "--fixture",
                    str(fixture_path),
                    "--org-domain",
                    "example.com",
                    "--format",
                    "json",
                ],
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        report = json.loads(completed.stdout)
        self.assertEqual(report["audit_type"], "email_dns_evidence")
        self.assertEqual(report["resolver"], "offline JSON fixture")
        self.assertGreater(report["summary"]["query_count"], 0)


if __name__ == "__main__":
    unittest.main()
