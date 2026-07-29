#!/usr/bin/env python3
"""Regression tests for audit_site.py."""

from __future__ import annotations

import argparse
import threading
import unittest
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import audit_site


class AuditHandler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:
        port = self.server.server_address[1]
        base = f"http://127.0.0.1:{port}"
        if self.path == "/robots.txt":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"User-agent: *\nAllow: /\n")
            return
        if self.path == "/":
            body = f"""<!doctype html>
<html lang="en"><head>
<title>English page</title>
<meta name="description" content="English description">
<meta name="viewport" content="width=device-width">
<link rel="canonical" href="{base}/">
<link rel="alternate" hreflang="en" href="{base}/">
<link rel="alternate" hreflang="fr" href="{base}/fr">
<link rel="alternate" hreflang="x-default" href="{base}/">
</head><body><h1>English</h1><a href="/fr">French</a></body></html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())
            return
        if self.path == "/fr":
            body = f"""<!doctype html>
<html lang="fr"><head>
<title>Page française</title>
<meta name="description" content="Description française">
<meta name="viewport" content="width=device-width">
<link rel="canonical" href="{base}/fr">
<link rel="alternate" hreflang="fr" href="{base}/fr">
</head><body><h1>Français</h1><a href="/">English</a></body></html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())
            return
        self.send_response(404)
        self.end_headers()


def crawl_args(url: str) -> argparse.Namespace:
    return argparse.Namespace(
        url=url,
        max_pages=10,
        max_depth=3,
        max_sitemaps=0,
        max_sitemap_urls=0,
        max_response_bytes=1_000_000,
        timeout=5.0,
        delay=0,
        user_agent="SEOAuditTest/1.0",
        include_subdomains=False,
        include_query_urls=False,
        no_sitemaps=True,
        ignore_robots=False,
        allow_private=True,
        allow_nonstandard_port=True,
        output="-",
        markdown=None,
        max_markdown_findings=100,
    )


class AuditSiteTests(unittest.TestCase):
    def test_crawl_validates_reciprocal_hreflang(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), AuditHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_address[1]}/"
            args = crawl_args(base)
            audit_site.validate_args(args)
            audit = audit_site.run(args)
        finally:
            server.shutdown()
            server.server_close()

        codes = {item["code"] for item in audit["findings"]}
        self.assertEqual(audit["summary"]["pages_fetched"], 2)
        self.assertEqual(audit["summary"]["pages_with_hreflang"], 2)
        self.assertIn("hreflang_not_reciprocal", codes)
        self.assertNotIn("hreflang_self_reference_missing", codes)

    def test_finding_engine_covers_hreflang_and_mixed_content(self) -> None:
        pages = [
            {
                "requested_url": "https://example.test/en",
                "url": "https://example.test/en",
                "status": 200,
                "is_html": True,
                "source": "link",
                "depth": 0,
                "title": "English",
                "descriptions": ["English"],
                "h1": ["English"],
                "canonicals": ["https://example.test/other"],
                "hreflang": [
                    {"lang": "en_US", "href": "https://example.test/fr"},
                    {"lang": "en_US", "href": "https://example.test/fr"},
                ],
                "viewport": ["width=device-width"],
                "html_lang": "en",
                "images": [
                    {
                        "url": "http://cdn.example.test/image.jpg",
                        "alt_present": True,
                        "width": "100",
                        "height": "100",
                        "role": "",
                    }
                ],
                "links": [
                    {
                        "url": "http://example.test/legacy",
                        "text": "Legacy",
                        "rel": "",
                    }
                ],
            },
            {
                "requested_url": "https://example.test/fr",
                "url": "https://example.test/fr",
                "status": 200,
                "is_html": True,
                "source": "link",
                "depth": 1,
                "title": "French",
                "descriptions": ["French"],
                "h1": ["French"],
                "canonicals": ["https://example.test/fr"],
                "hreflang": [],
                "viewport": ["width=device-width"],
                "html_lang": "fr",
                "noindex_observed": True,
                "images": [],
                "links": [],
            },
        ]
        findings, _ = audit_site.build_findings(
            pages,
            set(),
            Counter(),
            "https://example.test/en",
            set(),
            {"url": "https://example.test/robots.txt", "status": 200},
        )
        codes = {item["code"] for item in findings}
        expected = {
            "duplicate_hreflang_language",
            "hreflang_canonical_conflict",
            "hreflang_not_reciprocal",
            "hreflang_self_reference_missing",
            "hreflang_target_noindex",
            "insecure_image_on_https",
            "insecure_internal_link_on_https",
            "invalid_hreflang_syntax",
        }
        self.assertTrue(expected <= codes, sorted(expected - codes))


if __name__ == "__main__":
    unittest.main()
