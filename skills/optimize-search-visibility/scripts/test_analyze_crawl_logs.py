#!/usr/bin/env python3
"""Regression tests for analyze_crawl_logs.py."""

from __future__ import annotations

import argparse
import gzip
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import analyze_crawl_logs


def analysis_args(inputs: list[str], **overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "inputs": inputs,
        "input_format": "auto",
        "encoding": "utf-8",
        "combined_time_field": "seconds",
        "bot_pattern": [],
        "no_default_bots": False,
        "include_non_crawlers": False,
        "audit_json": None,
        "path_depth": 2,
        "top": 25,
        "max_lines": 1_000,
        "max_line_chars": 100_000,
        "max_unique_values": 1_000,
        "output": "-",
        "markdown": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class CrawlLogTests(unittest.TestCase):
    def test_mixed_formats_redact_query_values_and_preserve_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            combined = root / "access.log"
            combined.write_text(
                "\n".join(
                    [
                        (
                            '66.249.66.1 - - [29/Jul/2026:10:00:00 +0000] '
                            '"GET /products/widget?color=red&token=secret-value '
                            'HTTP/1.1" 200 1234 "-" '
                            '"Mozilla/5.0 (compatible; Googlebot/2.1)" 0.120'
                        ),
                        (
                            '66.249.66.1 - - [29/Jul/2026:10:01:00 +0000] '
                            '"GET /old-product HTTP/1.1" 301 0 "-" '
                            '"Mozilla/5.0 (compatible; Googlebot/2.1)" 0.030'
                        ),
                        "this is deliberately invalid",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            csv_path = root / "access.csv"
            csv_path.write_text(
                (
                    "timestamp,request_method,request_uri,status,"
                    "body_bytes_sent,http_user_agent,request_time,host\n"
                    "2026-07-29T11:00:00Z,GET,"
                    "/guide?page=2&session=private,200,2000,"
                    "OAI-SearchBot,0.250,www.example.test\n"
                ),
                encoding="utf-8",
            )
            jsonl = root / "access.jsonl"
            jsonl.write_text(
                json.dumps(
                    {
                        "@timestamp": "2026-07-29T12:00:00Z",
                        "http": {
                            "method": "GET",
                            "target": "/docs/a|b`c?utm_source=private",
                            "status_code": 503,
                            "user_agent": "PerplexityBot",
                        },
                        "response": {
                            "size": 3210,
                            "content_type": "text/html",
                        },
                        "response_time_ms": 85,
                        "host": "docs.example.test",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            args = analysis_args([str(combined), str(csv_path), str(jsonl)])
            analyze_crawl_logs.validate_args(args)
            analysis = analyze_crawl_logs.analyze(args)

        serialized = json.dumps(analysis)
        self.assertNotIn("secret-value", serialized)
        self.assertNotIn("private", serialized)
        self.assertEqual(analysis["coverage"]["records_parsed"], 4)
        self.assertEqual(analysis["coverage"]["claimed_crawler_records"], 4)
        self.assertEqual(analysis["coverage"]["parse_failures"], 1)
        self.assertEqual(
            analysis["families"]["google-search"]["response_timing"]["mean_ms"],
            75.0,
        )
        self.assertEqual(
            analysis["families"]["openai-search"]["query_parameters"][0]["value"],
            "page",
        )
        markdown = analyze_crawl_logs.markdown_report(analysis)
        self.assertIn(r"/docs/a\|b'c", markdown)
        self.assertNotIn("private", markdown)

    def test_gzip_input_and_cardinality_cap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "access.log.gz"
            payload = (
                '66.249.66.1 - - [29/Jul/2026:10:00:00 +0000] '
                '"GET / HTTP/1.1" 200 123 "-" "Googlebot" 0.010\n'
            ).encode()
            path.write_bytes(gzip.compress(payload))
            args = analysis_args([str(path)])
            analysis = analyze_crawl_logs.analyze(args)
        self.assertEqual(analysis["coverage"]["records_parsed"], 1)
        self.assertEqual(analysis["coverage"]["claimed_crawler_records"], 1)

        counter: Counter[str] = Counter()
        overflow = sum(
            analyze_crawl_logs.increment_bounded(counter, str(index), 100)
            for index in range(105)
        )
        self.assertEqual(overflow, 5)
        self.assertEqual(counter[analyze_crawl_logs.CARDINALITY_BUCKET], 5)

    def test_requires_at_least_one_pattern(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one bot pattern"):
            analyze_crawl_logs.parse_bot_patterns([], False)


if __name__ == "__main__":
    unittest.main()
