#!/usr/bin/env python3
"""Tests for inspect_email.py."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import formatdate, make_msgid
from pathlib import Path

from inspect_email import detect_type, inspect_bytes


class InspectEmailTests(unittest.TestCase):
    def test_html_extracts_copy_and_quality_evidence(self) -> None:
        html = b"""
        <!doctype html>
        <html lang="en"><body>
          <h1>Finish setting up your workspace</h1>
          <p>Invite one teammate to unlock shared reviews.</p>
          <a href="https://app.example.com/invite?utm_source=email">Invite a teammate</a>
          <img src="team.png">
          <a href="https://example.com/unsubscribe">Unsubscribe</a>
        </body></html>
        """
        report = inspect_bytes(html, "html", "Your workspace is waiting", "Invite your first teammate")
        self.assertEqual(report["html"]["languages"], ["en"])
        self.assertEqual(report["html"]["images_missing_alt"], 1)
        self.assertEqual(report["links"]["primary_candidates"], 1)
        self.assertEqual(report["body"]["unsubscribe_mentions"], 1)

    def test_eml_extracts_headers_and_mime_parts(self) -> None:
        message = EmailMessage()
        message["Date"] = formatdate(localtime=False)
        message["From"] = "Example <hello@example.com>"
        message["To"] = "User <user@example.net>"
        message["Subject"] = "Your receipt"
        message["Message-ID"] = make_msgid(domain="example.com")
        message.set_content("Thanks for your purchase.")
        message.add_alternative("<html lang='en'><body><p>Thanks for your purchase.</p></body></html>", subtype="html")
        report = inspect_bytes(message.as_bytes(policy=SMTP), "eml")
        self.assertEqual(report["subject"]["text"], "Your receipt")
        self.assertEqual(report["body"]["plain_parts"], 1)
        self.assertEqual(report["body"]["html_parts"], 1)
        self.assertEqual(report["headers"]["from"], "Example <hello@example.com>")
        self.assertEqual(report["identity_hints"]["header_from_domains"], ["example.com"])

    def test_eml_extracts_authentication_identity_hints_without_claiming_pass(self) -> None:
        raw = (
            b"From: News <news@example.com>\r\n"
            b"To: user@example.net\r\n"
            b"Return-Path: <bounce@mail.example.com>\r\n"
            b"Subject: Update\r\n"
            b"DKIM-Signature: v=1; a=rsa-sha256; d=example.com; s=news2026;\r\n"
            b" h=from:to:subject; bh=ignored; b=ignored\r\n"
            b"Authentication-Results: mx.example.net; dkim=pass header.d=example.com;\r\n"
            b" spf=pass smtp.mailfrom=mail.example.com; dmarc=pass\r\n"
            b"\r\n"
            b"Hello.\r\n"
        )
        report = inspect_bytes(raw, "eml")
        self.assertEqual(report["identity_hints"]["mail_from_domain"], "mail.example.com")
        self.assertEqual(
            report["identity_hints"]["dkim_selector_domains"],
            [{"selector": "news2026", "domain": "example.com"}],
        )
        signature = report["headers"]["dkim_signatures"][0]
        self.assertEqual(signature["algorithm"], "rsa-sha256")
        self.assertFalse(signature["body_length_tag_present"])
        self.assertEqual(len(report["headers"]["authentication_results"]), 1)

    def test_one_click_structure_and_authentication_results_trust_boundary(self) -> None:
        raw = (
            b"From: News <news@example.com>\r\n"
            b"To: user@example.net\r\n"
            b"Date: Wed, 29 Jul 2026 12:00:00 +0000\r\n"
            b"Message-ID: <one@example.com>\r\n"
            b"Subject: Update\r\n"
            b"List-Unsubscribe: <https://example.com/unsubscribe/token>, <mailto:leave@example.com>\r\n"
            b"List-Unsubscribe-Post: List-Unsubscribe=One-Click\r\n"
            b"DKIM-Signature: v=1; a=rsa-sha256; d=example.com; s=news;\r\n"
            b" h=from:to:subject:list-unsubscribe:list-unsubscribe-post; bh=x; b=y\r\n"
            b"Authentication-Results: inbound.example.net; dkim=pass header.d=example.com\r\n"
            b"\r\nHello.\r\n"
        )
        untrusted = inspect_bytes(raw, "eml")
        trusted = inspect_bytes(
            raw,
            "eml",
            trusted_authserv_ids={"inbound.example.net"},
        )
        self.assertTrue(trusted["one_click_unsubscribe"]["structurally_ready"])
        self.assertIsNone(trusted["one_click_unsubscribe"]["verified_operational"])
        self.assertEqual(
            untrusted["headers"]["authentication_results"][0]["trust_status"],
            "unverified_boundary",
        )
        self.assertEqual(
            trusted["headers"]["authentication_results"][0]["trust_status"],
            "trusted_by_user",
        )

    def test_security_review_signals_are_evidence_not_verdicts(self) -> None:
        message = EmailMessage()
        message["Date"] = formatdate(localtime=False)
        message["From"] = "Example <hello@example.com>"
        message["To"] = "User <user@example.net>"
        message["Subject"] = "Account\u202Eupdate"
        message["Message-ID"] = make_msgid(domain="example.com")
        message.set_content("Review the attached file.")
        message.add_alternative(
            (
                "<html lang='en'><head><meta name='viewport' content='width=device-width'></head>"
                "<body><a href='https://safe.example.net/path?secret=redacted'>"
                "https://different.example.org/login</a></body></html>"
            ),
            subtype="html",
        )
        message.add_attachment(
            b"MZplaceholder",
            maintype="application",
            subtype="octet-stream",
            filename="invoice.exe",
        )
        report = inspect_bytes(message.as_bytes(policy=SMTP), "eml")
        self.assertEqual(report["unicode_controls"]["subject"]["count"], 1)
        self.assertEqual(report["links"]["display_destination_mismatches"], 1)
        self.assertNotIn(
            "secret=redacted",
            report["links"]["items"][0]["destination"],
        )
        attachment = report["attachment_details"]["items"][0]
        self.assertIn("executable_or_script_extension", attachment["review_reasons"])
        self.assertIsNone(attachment["malicious"])

    def test_type_detection_uses_extension(self) -> None:
        self.assertEqual(detect_type("campaign.eml", "auto", b"anything"), "eml")
        self.assertEqual(detect_type("campaign.html", "auto", b"anything"), "html")

    def test_cli_handles_representative_html(self) -> None:
        script = Path(__file__).with_name("inspect_email.py")
        completed = subprocess.run(
            [
                sys.executable,
                str(script),
                "-",
                "--type",
                "html",
                "--subject",
                "Try the new workflow",
                "--preview",
                "See what changed",
                "--format",
                "json",
            ],
            input=b"<html lang='en'><body><a href='https://example.com/start'>Start now</a></body></html>",
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        report = json.loads(completed.stdout)
        self.assertEqual(report["links"]["primary_candidates"], 1)
        self.assertEqual(report["subject"]["characters"], 20)


if __name__ == "__main__":
    unittest.main()
