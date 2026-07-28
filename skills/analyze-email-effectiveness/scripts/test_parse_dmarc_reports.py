#!/usr/bin/env python3
"""Tests for parse_dmarc_reports.py."""

from __future__ import annotations

import gzip
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from parse_dmarc_reports import (
    DmarcReportError,
    analyze_paths,
    parse_dmarc_report_xml,
    payloads_from_file,
)


SAMPLE_REPORT = b"""\
<feedback xmlns="urn:ietf:params:xml:ns:dmarc-2.0">
  <version>1.0</version>
  <report_metadata>
    <org_name>Receiver Example</org_name>
    <email>dmarc@example.net</email>
    <report_id>report-123</report_id>
    <date_range><begin>1700000000</begin><end>1700086399</end></date_range>
    <generator>Example 1.0</generator>
  </report_metadata>
  <policy_published>
    <domain>example.com</domain>
    <p>reject</p>
    <testing>n</testing>
    <discovery_method>treewalk</discovery_method>
  </policy_published>
  <record>
    <row>
      <source_ip>192.0.2.10</source_ip>
      <count>100</count>
      <policy_evaluated>
        <disposition>pass</disposition><dkim>pass</dkim><spf>fail</spf>
      </policy_evaluated>
    </row>
    <identifiers>
      <envelope_from>bounce.example.com</envelope_from>
      <header_from>example.com</header_from>
    </identifiers>
    <auth_results>
      <dkim><domain>example.com</domain><selector>news</selector><result>pass</result></dkim>
      <spf><domain>bounce.example.com</domain><scope>mfrom</scope><result>pass</result></spf>
    </auth_results>
  </record>
  <record>
    <row>
      <source_ip>198.51.100.20</source_ip>
      <count>20</count>
      <policy_evaluated>
        <disposition>reject</disposition><dkim>fail</dkim><spf>fail</spf>
      </policy_evaluated>
    </row>
    <identifiers>
      <envelope_from>unrelated.example</envelope_from>
      <header_from>example.com</header_from>
    </identifiers>
    <auth_results>
      <dkim><domain>unrelated.example</domain><selector>x</selector><result>fail</result></dkim>
      <spf><domain>unrelated.example</domain><scope>mfrom</scope><result>fail</result></spf>
    </auth_results>
  </record>
</feedback>
"""


class ParseDmarcReportsTests(unittest.TestCase):
    def test_parse_rfc9990_namespace_and_records(self) -> None:
        report = parse_dmarc_report_xml(SAMPLE_REPORT, "sample.xml")
        self.assertEqual(report["namespace"], "urn:ietf:params:xml:ns:dmarc-2.0")
        self.assertEqual(report["policy_published"]["discovery_method"], "treewalk")
        self.assertEqual(len(report["records"]), 2)
        self.assertEqual(report["records"][0]["auth_results"]["dkim"][0]["selector"], "news")

    def test_analyze_gzip_and_skip_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "one.xml.gz"
            second = root / "two.xml"
            first.write_bytes(gzip.compress(SAMPLE_REPORT))
            second.write_bytes(SAMPLE_REPORT)
            report = analyze_paths([str(first), str(second)])
        self.assertEqual(report["inputs"]["valid_unique_reports"], 1)
        self.assertEqual(report["inputs"]["duplicates_skipped"], 1)
        self.assertEqual(report["aggregate"]["messages"]["total"], 120)
        self.assertEqual(report["aggregate"]["messages"]["aligned_pass"], 100)
        self.assertEqual(report["aggregate"]["messages"]["aligned_fail"], 20)

    def test_rejects_doctype(self) -> None:
        malicious = b"<!DOCTYPE feedback [<!ENTITY x SYSTEM 'file:///etc/passwd'>]><feedback/>"
        with self.assertRaises(DmarcReportError):
            parse_dmarc_report_xml(malicious, "bad.xml")
        late_declaration = (
            (b" " * (1024 * 1024 + 1))
            + b"<!DOCTYPE feedback [<!ENTITY x 'expanded'>]><feedback/>"
        )
        with self.assertRaises(DmarcReportError):
            parse_dmarc_report_xml(late_declaration, "late-bad.xml")

    def test_nested_gzip_members_share_one_expansion_budget(self) -> None:
        payload = SAMPLE_REPORT + (b" " * 2048)
        archive_bytes = io.BytesIO()
        with zipfile.ZipFile(archive_bytes, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("one.xml.gz", gzip.compress(payload))
            archive.writestr("two.xml.gz", gzip.compress(payload))
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "reports.zip"
            path.write_bytes(archive_bytes.getvalue())
            with self.assertRaises(DmarcReportError):
                payloads_from_file(
                    path,
                    max_input_bytes=1024 * 1024,
                    max_expanded_bytes=len(payload) + 128,
                    max_members=10,
                )

    def test_cli_json_output(self) -> None:
        script = Path(__file__).with_name("parse_dmarc_reports.py")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.xml"
            path.write_bytes(SAMPLE_REPORT)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    str(path),
                    "--format",
                    "json",
                ],
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        report = json.loads(completed.stdout)
        self.assertEqual(report["analysis_type"], "dmarc_aggregate_reports")


if __name__ == "__main__":
    unittest.main()
