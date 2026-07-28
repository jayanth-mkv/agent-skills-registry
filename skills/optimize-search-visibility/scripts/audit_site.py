#!/usr/bin/env python3
"""Crawl one website safely and emit reproducible, evidence-oriented SEO data.

The crawler uses only the Python standard library. Its findings are heuristics
for investigation, not statements about a search engine's index or rankings.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import io
import ipaddress
import json
import os
import re
import socket
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"
DEFAULT_USER_AGENT = "AgentSkillsSEOAudit/1.0"
DEFAULT_MAX_BYTES = 5_000_000
WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
SPACE_RE = re.compile(r"\s+")
SITEMAP_RE = re.compile(r"^\s*sitemap\s*:\s*(\S+)\s*$", re.IGNORECASE)
NOINDEX_RE = re.compile(r"(?:^|[\s,;])noindex(?:$|[\s,;])", re.IGNORECASE)
CANONICAL_HEADER_RE = re.compile(
    r"<([^>]+)>\s*;\s*rel\s*=\s*(?:\"canonical\"|'canonical'|canonical)",
    re.IGNORECASE,
)
HTTP_EQUIV_REFRESH_RE = re.compile(r"^\s*\d+\s*;\s*url\s*=", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def clean_text(value: str) -> str:
    return SPACE_RE.sub(" ", html.unescape(value or "")).strip()


def normalize_url(raw: str, base: str | None = None) -> str | None:
    value = clean_text(raw)
    if not value:
        return None
    if base:
        value = urllib.parse.urljoin(base, value)
    elif "://" not in value:
        value = "https://" + value
    try:
        parts = urllib.parse.urlsplit(value)
    except ValueError:
        return None
    if parts.scheme.casefold() not in {"http", "https"} or not parts.hostname:
        return None
    host = parts.hostname.casefold()
    try:
        port = parts.port
    except ValueError:
        return None
    default_port = (parts.scheme.casefold() == "http" and port == 80) or (
        parts.scheme.casefold() == "https" and port == 443
    )
    port_text = "" if port is None or default_port else f":{port}"
    path = parts.path or "/"
    return urllib.parse.urlunsplit(
        (parts.scheme.casefold(), host + port_text, path, parts.query, "")
    )


def without_query(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def host_without_www(host: str) -> str:
    return host[4:] if host.casefold().startswith("www.") else host


def has_noindex(*values: str) -> bool:
    return any(NOINDEX_RE.search(value or "") for value in values)


def stable_finding_id(code: str, url: str, detail: str = "") -> str:
    digest = hashlib.sha1(f"{code}\0{url}\0{detail}".encode("utf-8")).hexdigest()[:10]
    return f"{code.upper().replace('_', '-')}-{digest}"


def write_atomic(path: Path, text: str) -> None:
    parent = path.resolve().parent
    if not parent.is_dir():
        raise ValueError(f"output directory does not exist: {parent}")
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=parent, delete=False, newline="\n"
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.replace(temporary, path)


@dataclass
class SafetyPolicy:
    initial_host: str
    include_subdomains: bool = False
    allow_private: bool = False
    allow_nonstandard_port: bool = False
    allowed_hosts: set[str] = field(default_factory=set)
    dns_cache: dict[str, list[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.initial_host = self.initial_host.casefold()
        self.allowed_hosts.add(self.initial_host)

    @property
    def root_host(self) -> str:
        return host_without_www(self.initial_host)

    def host_in_scope(self, host: str) -> bool:
        candidate = host.casefold()
        if candidate in self.allowed_hosts:
            return True
        if host_without_www(candidate) == self.root_host:
            return True
        if self.include_subdomains and (
            candidate == self.root_host or candidate.endswith("." + self.root_host)
        ):
            return True
        return False

    def add_allowed_host(self, host: str) -> None:
        if self.host_in_scope(host):
            self.allowed_hosts.add(host.casefold())

    def validate(self, url: str, require_scope: bool = True) -> str:
        normalized = normalize_url(url)
        if not normalized:
            raise ValueError(f"invalid HTTP(S) URL: {url!r}")
        parts = urllib.parse.urlsplit(normalized)
        if parts.username or parts.password:
            raise ValueError("URLs containing credentials are not allowed")
        try:
            port = parts.port
        except ValueError as exc:
            raise ValueError(f"invalid URL port: {url!r}") from exc
        if (
            port not in {None, 80, 443}
            and not self.allow_nonstandard_port
        ):
            raise ValueError(
                f"non-standard port {port} is blocked; use --allow-nonstandard-port "
                "only for a host you control"
            )
        host = parts.hostname or ""
        if require_scope and not self.host_in_scope(host):
            raise ValueError(f"redirect or request left crawl scope: {normalized}")
        self._validate_addresses(host, port or (443 if parts.scheme == "https" else 80))
        return normalized

    def _validate_addresses(self, host: str, port: int) -> None:
        if host in self.dns_cache:
            addresses = self.dns_cache[host]
        else:
            try:
                infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            except socket.gaierror as exc:
                raise ValueError(f"DNS resolution failed for {host}: {exc}") from exc
            addresses = sorted({item[4][0].split("%", 1)[0] for item in infos})
            self.dns_cache[host] = addresses
        if not addresses:
            raise ValueError(f"DNS returned no addresses for {host}")
        if self.allow_private:
            return
        for address in addresses:
            parsed = ipaddress.ip_address(address)
            if not parsed.is_global:
                raise ValueError(
                    f"{host} resolves to non-public address {address}; "
                    "use --allow-private only for a host you control"
                )


class RecordingRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, policy: SafetyPolicy) -> None:
        super().__init__()
        self.policy = policy
        self.chain: list[dict[str, Any]] = []

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        target = normalize_url(newurl, req.full_url)
        if not target:
            raise urllib.error.URLError(f"invalid redirect target: {newurl!r}")
        try:
            target = self.policy.validate(target, require_scope=True)
        except ValueError as exc:
            raise urllib.error.URLError(str(exc)) from exc
        self.chain.append({"from": req.full_url, "status": code, "to": target})
        return super().redirect_request(req, fp, code, msg, headers, target)


@dataclass
class FetchResult:
    requested_url: str
    final_url: str
    status: int | None
    headers: dict[str, str]
    body: bytes
    redirects: list[dict[str, Any]]
    elapsed_ms: int
    truncated: bool
    error: str | None


class Fetcher:
    def __init__(
        self,
        policy: SafetyPolicy,
        user_agent: str,
        timeout: float,
        max_bytes: int,
    ) -> None:
        self.policy = policy
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_bytes = max_bytes

    def fetch(self, url: str, accept: str = "text/html,*/*;q=0.8") -> FetchResult:
        started = time.monotonic()
        try:
            safe_url = self.policy.validate(url, require_scope=True)
        except ValueError as exc:
            return FetchResult(
                url, url, None, {}, b"", [], 0, False, str(exc)
            )
        redirect_handler = RecordingRedirectHandler(self.policy)
        opener = urllib.request.build_opener(redirect_handler)
        request = urllib.request.Request(
            safe_url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": accept,
                "Accept-Encoding": "identity",
            },
            method="GET",
        )
        response: Any = None
        error: str | None = None
        try:
            response = opener.open(request, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            response = exc
            error = f"HTTP {exc.code}: {exc.reason}"
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            elapsed = int((time.monotonic() - started) * 1000)
            return FetchResult(
                safe_url,
                safe_url,
                None,
                {},
                b"",
                list(redirect_handler.chain),
                elapsed,
                False,
                str(exc),
            )

        try:
            raw = response.read(self.max_bytes + 1)
            truncated = len(raw) > self.max_bytes
            body = raw[: self.max_bytes]
            headers = {key.casefold(): value for key, value in response.headers.items()}
            final_url = normalize_url(response.geturl()) or safe_url
            status = int(response.getcode())
        except (OSError, ValueError) as exc:
            body = b""
            truncated = False
            headers = {}
            final_url = safe_url
            status = None
            error = str(exc)
        finally:
            try:
                response.close()
            except Exception:
                pass
        elapsed = int((time.monotonic() - started) * 1000)
        return FetchResult(
            safe_url,
            final_url,
            status,
            headers,
            body,
            list(redirect_handler.chain),
            elapsed,
            truncated,
            error,
        )


class SEOHTMLParser(HTMLParser):
    HIDDEN_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.in_title = False
        self.meta: list[dict[str, str]] = []
        self.links: list[dict[str, Any]] = []
        self.images: list[dict[str, Any]] = []
        self.headings: list[dict[str, str]] = []
        self.canonicals: list[str] = []
        self.hreflang: list[dict[str, str]] = []
        self.json_ld_blocks: list[str] = []
        self.html_lang = ""
        self.base_href = ""
        self.refresh = ""
        self.text_parts: list[str] = []
        self._hidden_depth = 0
        self._heading: dict[str, Any] | None = None
        self._anchor: dict[str, Any] | None = None
        self._json_ld_depth = 0
        self._json_ld_parts: list[str] = []

    @staticmethod
    def attrs_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key.casefold(): value or "" for key, value in attrs}

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        name = tag.casefold()
        data = self.attrs_dict(attrs)
        if name == "html" and not self.html_lang:
            self.html_lang = data.get("lang", "")
        if name == "title":
            self.in_title = True
        if name in self.HIDDEN_TEXT_TAGS:
            self._hidden_depth += 1
        if name == "meta":
            self.meta.append(data)
            if data.get("http-equiv", "").casefold() == "refresh":
                self.refresh = data.get("content", "")
        elif name == "base" and not self.base_href:
            self.base_href = data.get("href", "")
        elif name == "link":
            rel = {part.casefold() for part in data.get("rel", "").split()}
            if "canonical" in rel and data.get("href"):
                self.canonicals.append(data["href"])
            if "alternate" in rel and data.get("hreflang") and data.get("href"):
                self.hreflang.append(
                    {"lang": data["hreflang"], "href": data["href"]}
                )
        elif name == "a":
            self._anchor = {
                "href": data.get("href", ""),
                "rel": data.get("rel", ""),
                "text_parts": [],
            }
        elif name == "img":
            self.images.append(
                {
                    "src": data.get("src", ""),
                    "alt_present": "alt" in data,
                    "alt": data.get("alt", ""),
                    "width": data.get("width", ""),
                    "height": data.get("height", ""),
                    "loading": data.get("loading", ""),
                    "role": data.get("role", ""),
                }
            )
        elif name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading = {"level": name, "parts": []}
        elif name == "script" and data.get("type", "").casefold().split(";", 1)[0].strip() == (
            "application/ld+json"
        ):
            self._json_ld_depth = 1
            self._json_ld_parts = []

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        name = tag.casefold()
        if name == "title":
            self.in_title = False
        if name == "a" and self._anchor is not None:
            self.links.append(
                {
                    "href": self._anchor["href"],
                    "rel": self._anchor["rel"],
                    "text": clean_text(" ".join(self._anchor["text_parts"])),
                }
            )
            self._anchor = None
        if (
            self._heading is not None
            and name == self._heading["level"]
        ):
            self.headings.append(
                {
                    "level": self._heading["level"],
                    "text": clean_text(" ".join(self._heading["parts"])),
                }
            )
            self._heading = None
        if name == "script" and self._json_ld_depth:
            self.json_ld_blocks.append("".join(self._json_ld_parts).strip())
            self._json_ld_depth = 0
            self._json_ld_parts = []
        if name in self.HIDDEN_TEXT_TAGS and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self._anchor is not None:
            self._anchor["text_parts"].append(data)
        if self._heading is not None:
            self._heading["parts"].append(data)
        if self._json_ld_depth:
            self._json_ld_parts.append(data)
        if self._hidden_depth == 0:
            cleaned = clean_text(data)
            if cleaned:
                self.text_parts.append(cleaned)


def meta_values(parser: SEOHTMLParser, key: str, value: str) -> list[str]:
    wanted_key = key.casefold()
    wanted_value = value.casefold()
    return [
        item.get("content", "")
        for item in parser.meta
        if item.get(wanted_key, "").casefold() == wanted_value
    ]


def decode_body(body: bytes, content_type: str) -> str:
    charset_match = re.search(r"charset\s*=\s*['\"]?([^;'\"\s]+)", content_type, re.I)
    charset = charset_match.group(1) if charset_match else "utf-8"
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def extract_schema_types(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        type_value = value.get("@type")
        if isinstance(type_value, str):
            found.append(type_value)
        elif isinstance(type_value, list):
            found.extend(item for item in type_value if isinstance(item, str))
        for nested in value.values():
            found.extend(extract_schema_types(nested))
    elif isinstance(value, list):
        for nested in value:
            found.extend(extract_schema_types(nested))
    return found


def parse_page(result: FetchResult, source: str, depth: int) -> dict[str, Any]:
    content_type = result.headers.get("content-type", "")
    page: dict[str, Any] = {
        "requested_url": result.requested_url,
        "url": result.final_url,
        "source": source,
        "depth": depth,
        "status": result.status,
        "redirects": result.redirects,
        "elapsed_ms": result.elapsed_ms,
        "content_type": content_type,
        "bytes_read": len(result.body),
        "truncated": result.truncated,
        "fetch_error": result.error,
        "headers": {
            key: result.headers.get(key, "")
            for key in (
                "x-robots-tag",
                "content-language",
                "link",
                "cache-control",
                "strict-transport-security",
                "content-security-policy",
                "x-content-type-options",
                "referrer-policy",
            )
            if result.headers.get(key)
        },
    }
    looks_like_html = "html" in content_type.casefold() or (
        not content_type
        and re.search(br"<(?:!doctype\s+html|html)\b", result.body[:4096], re.IGNORECASE)
        is not None
    )
    if not result.status or not looks_like_html or not result.body:
        page["is_html"] = False
        return page

    parser = SEOHTMLParser()
    document = decode_body(result.body, content_type)
    try:
        parser.feed(document)
        parser.close()
    except Exception as exc:
        page["parse_error"] = str(exc)
    page["is_html"] = True

    resolution_base = normalize_url(parser.base_href, result.final_url) or result.final_url
    title = clean_text(" ".join(parser.title_parts))
    descriptions = meta_values(parser, "name", "description")
    generic_robots = meta_values(parser, "name", "robots")
    googlebot_robots = meta_values(parser, "name", "googlebot")
    viewport = meta_values(parser, "name", "viewport")
    canonicals = [
        target
        for target in (
            normalize_url(raw, resolution_base) for raw in parser.canonicals
        )
        if target
    ]
    header_canonicals = [
        target
        for target in (
            normalize_url(raw, result.final_url)
            for raw in CANONICAL_HEADER_RE.findall(result.headers.get("link", ""))
        )
        if target
    ]
    hreflang = [
        {"lang": item["lang"], "href": target}
        for item in parser.hreflang
        if (target := normalize_url(item["href"], resolution_base))
    ]

    links: list[dict[str, Any]] = []
    for item in parser.links:
        target = normalize_url(item["href"], resolution_base)
        if target:
            links.append(
                {
                    "url": target,
                    "text": item["text"],
                    "rel": item["rel"],
                }
            )

    images: list[dict[str, Any]] = []
    for image in parser.images:
        record = dict(image)
        record["url"] = normalize_url(image["src"], resolution_base)
        images.append(record)

    schema_types: list[str] = []
    invalid_json_ld = 0
    for block in parser.json_ld_blocks:
        if not block:
            invalid_json_ld += 1
            continue
        try:
            schema_types.extend(extract_schema_types(json.loads(block)))
        except (json.JSONDecodeError, TypeError):
            invalid_json_ld += 1

    visible_text = clean_text(" ".join(parser.text_parts))
    words = WORD_RE.findall(visible_text)
    fingerprint_source = " ".join(word.casefold() for word in words)
    fingerprint = (
        hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
        if fingerprint_source
        else ""
    )
    x_robots = result.headers.get("x-robots-tag", "")

    page.update(
        {
            "title": title,
            "title_characters": len(title),
            "descriptions": descriptions,
            "description_characters": len(descriptions[0]) if descriptions else 0,
            "meta_robots": generic_robots,
            "googlebot_robots": googlebot_robots,
            "x_robots_tag": x_robots,
            "noindex_observed": has_noindex(
                *generic_robots, *googlebot_robots, x_robots
            ),
            "canonicals": canonicals + header_canonicals,
            "hreflang": hreflang,
            "headings": parser.headings,
            "h1": [
                item["text"] for item in parser.headings if item["level"] == "h1"
            ],
            "html_lang": parser.html_lang,
            "viewport": viewport,
            "meta_refresh": parser.refresh,
            "links": links,
            "images": images,
            "json_ld_blocks": len(parser.json_ld_blocks),
            "json_ld_invalid": invalid_json_ld,
            "schema_types": sorted(set(schema_types)),
            "word_count_approx": len(words),
            "content_fingerprint": fingerprint,
            "text_sample": visible_text[:500],
            "indexable_by_observed_directives": (
                result.status == 200 and not has_noindex(
                    *generic_robots, *googlebot_robots, x_robots
                )
            ),
        }
    )
    return page


def fetch_robots(
    fetcher: Fetcher, root_url: str, user_agent: str
) -> tuple[dict[str, Any], urllib.robotparser.RobotFileParser | None, list[str]]:
    parts = urllib.parse.urlsplit(root_url)
    robots_url = urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, "/robots.txt", "", "")
    )
    result = fetcher.fetch(robots_url, "text/plain,*/*;q=0.5")
    text = decode_body(
        result.body, result.headers.get("content-type", "text/plain; charset=utf-8")
    )
    sitemaps = [
        normalize_url(match.group(1), robots_url)
        for line in text.splitlines()
        if (match := SITEMAP_RE.match(line))
    ]
    sitemaps = [item for item in sitemaps if item]
    parser: urllib.robotparser.RobotFileParser | None = None
    if result.status and 200 <= result.status < 300:
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(text.splitlines())
    record = {
        "url": robots_url,
        "status": result.status,
        "fetch_error": result.error,
        "bytes_read": len(result.body),
        "sitemaps_declared": sitemaps,
        "user_agent_tested": user_agent,
        "note": (
            "Parsed and enforced for this crawl."
            if parser
            else "Not available for parsing; crawl continued with this limitation."
        ),
    }
    return record, parser, sitemaps


def discover_sitemaps(
    fetcher: Fetcher,
    root_url: str,
    declared: list[str],
    max_sitemaps: int,
    max_urls: int,
    delay: float,
) -> tuple[list[dict[str, Any]], list[str]]:
    parts = urllib.parse.urlsplit(root_url)
    candidates = declared + [
        urllib.parse.urlunsplit((parts.scheme, parts.netloc, "/sitemap.xml", "", "")),
        urllib.parse.urlunsplit(
            (parts.scheme, parts.netloc, "/sitemap_index.xml", "", "")
        ),
    ]
    queue: deque[str] = deque()
    queued: set[str] = set()
    for item in candidates:
        normalized = normalize_url(item)
        if normalized and normalized not in queued:
            queue.append(normalized)
            queued.add(normalized)

    records: list[dict[str, Any]] = []
    urls: list[str] = []
    seen_urls: set[str] = set()
    while queue and len(records) < max_sitemaps and len(urls) < max_urls:
        sitemap_url = queue.popleft()
        result = fetcher.fetch(sitemap_url, "application/xml,text/xml,*/*;q=0.5")
        record: dict[str, Any] = {
            "url": sitemap_url,
            "status": result.status,
            "fetch_error": result.error,
            "bytes_read": len(result.body),
            "truncated": result.truncated,
            "type": "unknown",
            "locations": 0,
        }
        if result.status and 200 <= result.status < 300 and result.body:
            try:
                xml_body = result.body
                if sitemap_url.casefold().endswith(".gz") or "gzip" in result.headers.get(
                    "content-type", ""
                ).casefold():
                    with gzip.GzipFile(fileobj=io.BytesIO(result.body)) as archive:
                        xml_body = archive.read(fetcher.max_bytes + 1)
                    if len(xml_body) > fetcher.max_bytes:
                        record["decompressed_truncated"] = True
                        xml_body = xml_body[: fetcher.max_bytes]
                root = ET.fromstring(xml_body)
                kind = local_name(root.tag)
                record["type"] = kind
                locations = [
                    clean_text(node.text or "")
                    for node in root.iter()
                    if local_name(node.tag) == "loc" and clean_text(node.text or "")
                ]
                record["locations"] = len(locations)
                if kind == "sitemapindex":
                    for location in locations:
                        normalized = normalize_url(location, sitemap_url)
                        if normalized and normalized not in queued:
                            try:
                                fetcher.policy.validate(normalized, require_scope=True)
                            except ValueError:
                                continue
                            queue.append(normalized)
                            queued.add(normalized)
                elif kind == "urlset":
                    for location in locations:
                        normalized = normalize_url(location, sitemap_url)
                        if not normalized or normalized in seen_urls:
                            continue
                        try:
                            fetcher.policy.validate(normalized, require_scope=True)
                        except ValueError:
                            continue
                        seen_urls.add(normalized)
                        urls.append(normalized)
                        if len(urls) >= max_urls:
                            break
                else:
                    record["parse_error"] = f"unexpected root element: {kind}"
            except ET.ParseError as exc:
                record["parse_error"] = str(exc)
        records.append(record)
        if delay:
            time.sleep(delay)
    return records, urls


def finding(
    code: str,
    severity: str,
    category: str,
    url: str,
    observation: str,
    *,
    detail: str = "",
    scope: str = "page",
    confidence: str = "high",
    caveat: str = "",
) -> dict[str, str]:
    return {
        "id": stable_finding_id(code, url, detail),
        "code": code,
        "severity": severity,
        "category": category,
        "url": url,
        "scope": scope,
        "confidence": confidence,
        "observation": observation,
        "caveat": caveat,
    }


def build_findings(
    pages: list[dict[str, Any]],
    sitemap_urls: set[str],
    inbound: Counter[str],
    root_url: str,
    query_urls: set[str],
    robots_record: dict[str, Any],
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    findings: list[dict[str, str]] = []
    page_by_url = {page["url"]: page for page in pages}

    title_groups: defaultdict[str, list[str]] = defaultdict(list)
    description_groups: defaultdict[str, list[str]] = defaultdict(list)
    fingerprint_groups: defaultdict[str, list[str]] = defaultdict(list)
    for page in pages:
        url = page["url"]
        status = page.get("status")
        if status is None:
            findings.append(
                finding(
                    "fetch_failed",
                    "high",
                    "availability",
                    url,
                    f"Fetch failed: {page.get('fetch_error') or 'unknown error'}.",
                )
            )
            continue
        if status >= 500:
            findings.append(
                finding(
                    "server_error",
                    "high",
                    "availability",
                    url,
                    f"Returned HTTP {status}.",
                )
            )
        elif status >= 400:
            findings.append(
                finding(
                    "client_error",
                    "medium",
                    "availability",
                    url,
                    f"Returned HTTP {status}.",
                    caveat="Severity depends on whether this URL is intentionally absent.",
                )
            )
        if page.get("truncated"):
            findings.append(
                finding(
                    "response_truncated",
                    "medium",
                    "rendering",
                    url,
                    "Response exceeded the configured byte limit; analysis is partial.",
                )
            )
        if not page.get("is_html"):
            continue

        title = page.get("title", "")
        if not title:
            findings.append(
                finding(
                    "missing_title",
                    "medium",
                    "on-page",
                    url,
                    "No non-empty HTML title was observed in the fetched source.",
                )
            )
        else:
            title_groups[title.casefold()].append(url)
            if len(title) > 70:
                findings.append(
                    finding(
                        "long_title_heuristic",
                        "low",
                        "presentation",
                        url,
                        f"Title is {len(title)} characters; it may be rewritten or truncated.",
                        caveat="Character count is a presentation heuristic, not a ranking rule.",
                    )
                )

        descriptions = page.get("descriptions", [])
        if not descriptions or not clean_text(descriptions[0]):
            findings.append(
                finding(
                    "missing_description",
                    "low",
                    "presentation",
                    url,
                    "No non-empty meta description was observed.",
                    caveat="Search systems may generate a snippet from page content.",
                )
            )
        else:
            description_groups[clean_text(descriptions[0]).casefold()].append(url)

        h1 = page.get("h1", [])
        if not h1:
            findings.append(
                finding(
                    "missing_h1",
                    "low",
                    "structure",
                    url,
                    "No H1 was observed in the fetched source.",
                    caveat="Treat as a clarity/accessibility lead, not a ranking emergency.",
                )
            )
        elif len(h1) > 1:
            findings.append(
                finding(
                    "multiple_h1",
                    "low",
                    "structure",
                    url,
                    f"{len(h1)} H1 elements were observed.",
                    caveat="Multiple H1s are not automatically a Google Search defect.",
                )
            )

        canonicals = page.get("canonicals", [])
        if len(canonicals) > 1:
            findings.append(
                finding(
                    "multiple_canonicals",
                    "high",
                    "index-control",
                    url,
                    f"{len(canonicals)} canonical targets were observed: {canonicals[:3]}.",
                )
            )
        elif not canonicals and status == 200:
            findings.append(
                finding(
                    "missing_canonical",
                    "low",
                    "index-control",
                    url,
                    "No HTML or HTTP canonical was observed.",
                    caveat="A self-canonical can reinforce consistency but is not mandatory.",
                )
            )
        elif canonicals:
            target_host = urllib.parse.urlsplit(canonicals[0]).hostname or ""
            page_host = urllib.parse.urlsplit(url).hostname or ""
            if target_host.casefold() != page_host.casefold():
                findings.append(
                    finding(
                        "cross_host_canonical",
                        "medium",
                        "index-control",
                        url,
                        f"Canonical points to another host: {canonicals[0]}.",
                        caveat="This can be intentional for syndication or consolidation.",
                    )
                )

        if page.get("noindex_observed"):
            findings.append(
                finding(
                    "noindex_observed",
                    "low",
                    "index-control",
                    url,
                    "A noindex directive was observed in meta or HTTP headers.",
                    caveat="Validate against the intended index state before treating as a defect.",
                )
            )
        if page.get("meta_refresh") and HTTP_EQUIV_REFRESH_RE.search(
            page["meta_refresh"]
        ):
            findings.append(
                finding(
                    "meta_refresh",
                    "medium",
                    "url-control",
                    url,
                    f"Meta refresh observed: {page['meta_refresh'][:160]}.",
                )
            )
        if not page.get("viewport"):
            findings.append(
                finding(
                    "missing_viewport",
                    "medium",
                    "mobile",
                    url,
                    "No viewport meta tag was observed.",
                )
            )
        if not page.get("html_lang"):
            findings.append(
                finding(
                    "missing_html_lang",
                    "low",
                    "accessibility",
                    url,
                    "The HTML element has no language attribute.",
                    caveat="This is primarily an accessibility and language-processing lead.",
                )
            )
        invalid_json_ld = int(page.get("json_ld_invalid", 0))
        if invalid_json_ld:
            findings.append(
                finding(
                    "invalid_json_ld",
                    "medium",
                    "structured-data",
                    url,
                    f"{invalid_json_ld} JSON-LD block(s) could not be parsed as JSON.",
                )
            )

        missing_alt = [
            image
            for image in page.get("images", [])
            if not image.get("alt_present")
            and image.get("role", "").casefold() not in {"presentation", "none"}
        ]
        if missing_alt:
            findings.append(
                finding(
                    "image_alt_missing",
                    "low",
                    "images",
                    url,
                    f"{len(missing_alt)} image(s) omit the alt attribute.",
                    caveat="Decorative images should normally use alt=\"\" rather than omit alt.",
                )
            )
        unsized = [
            image
            for image in page.get("images", [])
            if image.get("url") and (not image.get("width") or not image.get("height"))
        ]
        if unsized:
            findings.append(
                finding(
                    "image_dimensions_missing",
                    "low",
                    "performance",
                    url,
                    f"{len(unsized)} image(s) omit width or height attributes.",
                    caveat="CSS aspect-ratio or other layout reservations may still prevent shifts.",
                )
            )

        if page.get("source") == "sitemap" and inbound[url] == 0 and url != root_url:
            findings.append(
                finding(
                    "orphan_candidate",
                    "medium",
                    "discovery",
                    url,
                    "Found in a sitemap but no inbound internal link was observed in the crawl.",
                    caveat="This is only a candidate because the crawl is capped and scoped.",
                )
            )
        if int(page.get("depth", 0)) > 4:
            findings.append(
                finding(
                    "deep_url_candidate",
                    "low",
                    "architecture",
                    url,
                    f"First observed at crawl depth {page['depth']}.",
                    caveat="There is no universal click-depth threshold; assess business importance.",
                )
            )

        fingerprint = page.get("content_fingerprint", "")
        if fingerprint and int(page.get("word_count_approx", 0)) >= 20:
            fingerprint_groups[fingerprint].append(url)

    for normalized_title, urls in title_groups.items():
        if normalized_title and len(urls) > 1:
            for url in urls:
                findings.append(
                    finding(
                        "duplicate_title",
                        "medium",
                        "on-page",
                        url,
                        f"Same title observed on {len(urls)} crawled pages.",
                        detail=normalized_title,
                        scope="crawl-sample",
                        caveat="Duplicate titles can indicate unclear page roles but do not prove duplicate content.",
                    )
                )
    for normalized_description, urls in description_groups.items():
        if normalized_description and len(urls) > 1:
            for url in urls:
                findings.append(
                    finding(
                        "duplicate_description",
                        "low",
                        "presentation",
                        url,
                        f"Same meta description observed on {len(urls)} crawled pages.",
                        detail=normalized_description,
                        scope="crawl-sample",
                    )
                )

    duplicate_groups: list[dict[str, Any]] = []
    for fingerprint, urls in fingerprint_groups.items():
        if len(urls) > 1:
            duplicate_groups.append(
                {"fingerprint": fingerprint, "urls": sorted(urls), "count": len(urls)}
            )
            for url in urls:
                findings.append(
                    finding(
                        "exact_text_duplicate",
                        "medium",
                        "content",
                        url,
                        f"Normalized visible text exactly matches {len(urls) - 1} other crawled page(s).",
                        detail=fingerprint,
                        scope="crawl-sample",
                        caveat="Templates and navigation are included in the approximate text extraction.",
                    )
                )

    for source in pages:
        source_url = source["url"]
        for link in source.get("links", []):
            target = link["url"]
            target_page = page_by_url.get(target) or page_by_url.get(without_query(target))
            if not target_page:
                continue
            status = target_page.get("status")
            if status and status >= 400:
                findings.append(
                    finding(
                        "broken_internal_link",
                        "high" if status >= 500 else "medium",
                        "internal-links",
                        source_url,
                        f"Internal link points to {target}, which returned HTTP {status}.",
                        detail=target,
                    )
                )
            elif target_page.get("redirects"):
                findings.append(
                    finding(
                        "redirected_internal_link",
                        "low",
                        "internal-links",
                        source_url,
                        f"Internal link points to a redirecting URL: {target}.",
                        detail=target,
                    )
                )

    for sitemap_url in sorted(sitemap_urls):
        page = page_by_url.get(sitemap_url)
        if not page:
            continue
        if page.get("status") != 200 or page.get("noindex_observed"):
            findings.append(
                finding(
                    "sitemap_url_not_index_eligible",
                    "medium",
                    "sitemaps",
                    sitemap_url,
                    "Sitemap URL did not return a 200 index-eligible HTML state in this crawl.",
                    caveat="Confirm the intended state and Google-selected canonical.",
                )
            )
        canonicals = page.get("canonicals", [])
        if canonicals and canonicals[0] != sitemap_url:
            findings.append(
                finding(
                    "sitemap_canonical_mismatch",
                    "medium",
                    "sitemaps",
                    sitemap_url,
                    f"Sitemap URL canonicalizes to {canonicals[0]}.",
                )
            )

    if query_urls:
        findings.append(
            finding(
                "query_urls_discovered",
                "opportunity",
                "url-system",
                root_url,
                f"{len(query_urls)} internal query-string URL(s) were discovered.",
                scope="crawl-sample",
                caveat="They were not fetched unless --include-query-urls was used; define facet/parameter policy.",
            )
        )
    if robots_record.get("status") is None or (
        robots_record.get("status") and robots_record["status"] >= 400
    ):
        findings.append(
            finding(
                "robots_unavailable",
                "low",
                "crawl-control",
                robots_record["url"],
                f"robots.txt was not parsed (status {robots_record.get('status')}).",
                caveat="A robots.txt file is not required to allow crawling; review server behavior and intended policy.",
            )
        )

    severity_order = {
        "blocker": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
        "opportunity": 4,
    }
    findings.sort(
        key=lambda item: (
            severity_order.get(item["severity"], 9),
            item["code"],
            item["url"],
        )
    )
    duplicate_groups.sort(key=lambda item: (-item["count"], item["urls"][0]))
    return findings, duplicate_groups


def markdown_report(audit: dict[str, Any], max_findings: int) -> str:
    summary = audit["summary"]
    lines = [
        f"# Search visibility crawl: {audit['target']['effective_root']}",
        "",
        f"- Collected: {audit['started_at']} to {audit['completed_at']}",
        f"- Tool: audit_site.py {audit['tool_version']}",
        f"- Coverage: {summary['pages_fetched']} fetched; "
        f"{summary['html_pages']} HTML; {summary['blocked_by_robots']} robots-blocked; "
        f"{summary['fetch_failures']} fetch failures",
        f"- Limits: {audit['configuration']['max_pages']} pages, "
        f"depth {audit['configuration']['max_depth']}, "
        f"{audit['configuration']['max_response_bytes']} bytes/response",
        "",
        "> This is a capped crawler snapshot. It does not report a search engine's index, "
        "rankings, rendered mobile view, field performance, or business outcomes.",
        "",
        "## Coverage",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
    ]
    coverage_fields = [
        ("Pages requested", "pages_requested"),
        ("Pages fetched", "pages_fetched"),
        ("HTML pages", "html_pages"),
        ("Robots-blocked URLs", "blocked_by_robots"),
        ("Fetch failures", "fetch_failures"),
        ("Sitemap URLs discovered", "sitemap_urls_discovered"),
        ("Internal links observed", "internal_links_observed"),
        ("External links observed", "external_links_observed"),
        ("Query URLs discovered", "query_urls_discovered"),
    ]
    for label, key in coverage_fields:
        lines.append(f"| {label} | {summary[key]} |")

    lines.extend(
        [
            "",
            "## Finding counts",
            "",
            "| Severity | Count |",
            "| --- | ---: |",
        ]
    )
    for severity in ("blocker", "high", "medium", "low", "opportunity"):
        lines.append(
            f"| {severity.title()} | {summary['findings_by_severity'].get(severity, 0)} |"
        )

    lines.extend(["", "## Finding types", "", "| Code | Count |", "| --- | ---: |"])
    for code, count in sorted(
        summary["findings_by_code"].items(), key=lambda item: (-item[1], item[0])
    ):
        lines.append(f"| `{code}` | {count} |")

    lines.extend(["", "## Findings", ""])
    displayed = audit["findings"][:max_findings]
    for item in displayed:
        lines.extend(
            [
                f"### {item['severity'].title()}: {item['code']}",
                "",
                f"- URL: `{item['url']}`",
                f"- Observation: {item['observation']}",
                f"- Confidence: {item['confidence']}; scope: {item['scope']}",
            ]
        )
        if item.get("caveat"):
            lines.append(f"- Caveat: {item['caveat']}")
        lines.append("")
    remaining = len(audit["findings"]) - len(displayed)
    if remaining > 0:
        lines.append(
            f"_Markdown output omits {remaining} additional finding instances; "
            "use the JSON output for the complete evidence._"
        )
        lines.append("")

    lines.extend(
        [
            "## Next evidence",
            "",
            "- Validate priority findings in raw and rendered HTML on representative templates.",
            "- Compare crawl inventory with CMS, sitemap, Search Console, analytics, and logs.",
            "- Use field data for Core Web Vitals and first-party outcomes for prioritization.",
            "- Define intended index/canonical state before changing directives or redirects.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("url", help="Public HTTP(S) URL to start from")
    parser.add_argument(
        "--max-pages", type=int, default=200, help="Maximum fetched page responses"
    )
    parser.add_argument(
        "--max-depth", type=int, default=10, help="Maximum internal-link crawl depth"
    )
    parser.add_argument(
        "--max-sitemaps", type=int, default=20, help="Maximum sitemap files to fetch"
    )
    parser.add_argument(
        "--max-sitemap-urls",
        type=int,
        default=10_000,
        help="Maximum in-scope sitemap URLs to retain",
    )
    parser.add_argument(
        "--max-response-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help="Maximum bytes read from any response",
    )
    parser.add_argument("--timeout", type=float, default=20.0, help="Seconds per request")
    parser.add_argument(
        "--delay", type=float, default=0.5, help="Delay between requests in seconds"
    )
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument(
        "--include-subdomains",
        action="store_true",
        help="Allow crawling subdomains below the initial root",
    )
    parser.add_argument(
        "--include-query-urls",
        action="store_true",
        help="Fetch query-string URLs; can greatly expand crawl space",
    )
    parser.add_argument(
        "--no-sitemaps",
        action="store_true",
        help="Skip sitemap discovery and sampling",
    )
    parser.add_argument(
        "--ignore-robots",
        action="store_true",
        help="Ignore robots.txt only in an owned, controlled test environment",
    )
    parser.add_argument(
        "--allow-private",
        action="store_true",
        help="Allow private/loopback/reserved addresses for an owned test environment",
    )
    parser.add_argument(
        "--allow-nonstandard-port",
        action="store_true",
        help="Allow ports other than 80/443 for an owned test environment",
    )
    parser.add_argument(
        "--output",
        default="-",
        help="JSON output path, or - for stdout",
    )
    parser.add_argument("--markdown", help="Optional Markdown summary path")
    parser.add_argument(
        "--max-markdown-findings",
        type=int,
        default=200,
        help="Maximum finding instances in Markdown (JSON always contains all)",
    )
    parser.add_argument("--version", action="version", version=VERSION)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not 1 <= args.max_pages <= 10_000:
        raise ValueError("--max-pages must be between 1 and 10000")
    if not 0 <= args.max_depth <= 100:
        raise ValueError("--max-depth must be between 0 and 100")
    if not 0 <= args.max_sitemaps <= 1_000:
        raise ValueError("--max-sitemaps must be between 0 and 1000")
    if not 0 <= args.max_sitemap_urls <= 1_000_000:
        raise ValueError("--max-sitemap-urls must be between 0 and 1000000")
    if not 1_024 <= args.max_response_bytes <= 100_000_000:
        raise ValueError("--max-response-bytes must be between 1024 and 100000000")
    if not 0.1 <= args.timeout <= 300:
        raise ValueError("--timeout must be between 0.1 and 300")
    if not 0 <= args.delay <= 60:
        raise ValueError("--delay must be between 0 and 60")
    if not 1 <= args.max_markdown_findings <= 100_000:
        raise ValueError("--max-markdown-findings must be between 1 and 100000")
    if args.output == "-" and args.markdown == "-":
        raise ValueError("JSON and Markdown cannot both use stdout")
    if not clean_text(args.user_agent):
        raise ValueError("--user-agent cannot be empty")


def run(args: argparse.Namespace) -> dict[str, Any]:
    started_at = utc_now()
    seed = normalize_url(args.url)
    if not seed:
        raise ValueError("start URL must be a valid HTTP(S) URL")
    seed_parts = urllib.parse.urlsplit(seed)
    initial_host = seed_parts.hostname or ""
    policy = SafetyPolicy(
        initial_host=initial_host,
        include_subdomains=args.include_subdomains,
        allow_private=args.allow_private,
        allow_nonstandard_port=args.allow_nonstandard_port,
    )
    seed = policy.validate(seed, require_scope=True)
    fetcher = Fetcher(
        policy=policy,
        user_agent=args.user_agent,
        timeout=args.timeout,
        max_bytes=args.max_response_bytes,
    )

    first = fetcher.fetch(seed)
    if first.status is None:
        raise RuntimeError(f"could not fetch start URL: {first.error}")
    final_host = urllib.parse.urlsplit(first.final_url).hostname or initial_host
    policy.add_allowed_host(final_host)
    effective_root = first.final_url

    robots_record, robots_parser, declared_sitemaps = fetch_robots(
        fetcher, effective_root, args.user_agent
    )
    if args.delay:
        time.sleep(args.delay)

    sitemap_records: list[dict[str, Any]] = []
    sitemap_url_list: list[str] = []
    if not args.no_sitemaps and args.max_sitemaps and args.max_sitemap_urls:
        sitemap_records, sitemap_url_list = discover_sitemaps(
            fetcher,
            effective_root,
            declared_sitemaps,
            args.max_sitemaps,
            args.max_sitemap_urls,
            args.delay,
        )

    linked_queue: deque[tuple[str, int, str]] = deque(
        [(first.requested_url, 0, "seed")]
    )
    sitemap_queue: deque[tuple[str, int, str]] = deque(
        (url, 0, "sitemap") for url in sitemap_url_list
    )
    queued: set[str] = {first.requested_url, *sitemap_url_list}
    fetched_requested: set[str] = set()
    requested_count = 0
    blocked: list[str] = []
    pages: list[dict[str, Any]] = []
    query_urls: set[str] = set()
    internal_edges: list[dict[str, str]] = []
    external_edges: list[dict[str, str]] = []
    inbound: Counter[str] = Counter()
    linked_since_sitemap = 0

    while len(pages) < args.max_pages and (linked_queue or sitemap_queue):
        if linked_queue and (not sitemap_queue or linked_since_sitemap < 4):
            current_url, depth, source = linked_queue.popleft()
            linked_since_sitemap += 1
        else:
            current_url, depth, source = sitemap_queue.popleft()
            linked_since_sitemap = 0
        if current_url in fetched_requested:
            continue
        fetched_requested.add(current_url)
        requested_count += 1
        if (
            not args.ignore_robots
            and robots_parser is not None
            and not robots_parser.can_fetch(args.user_agent, current_url)
        ):
            blocked.append(current_url)
            continue

        if current_url == first.requested_url and not pages:
            result = first
        else:
            result = fetcher.fetch(current_url)
        page = parse_page(result, source=source, depth=depth)
        pages.append(page)
        final_page_url = page["url"]
        fetched_requested.add(final_page_url)
        queued.add(final_page_url)
        policy.add_allowed_host(
            urllib.parse.urlsplit(final_page_url).hostname or initial_host
        )

        if page.get("is_html") and depth < args.max_depth:
            for link in page.get("links", []):
                target = link["url"]
                host = urllib.parse.urlsplit(target).hostname or ""
                if policy.host_in_scope(host):
                    internal_edges.append(
                        {
                            "from": final_page_url,
                            "to": target,
                            "text": link.get("text", ""),
                        }
                    )
                    inbound[target] += 1
                    if urllib.parse.urlsplit(target).query:
                        query_urls.add(target)
                        if not args.include_query_urls:
                            continue
                    if target not in queued:
                        linked_queue.append((target, depth + 1, "link"))
                        queued.add(target)
                else:
                    external_edges.append(
                        {
                            "from": final_page_url,
                            "to": target,
                            "text": link.get("text", ""),
                        }
                    )
        if args.delay and len(pages) < args.max_pages:
            time.sleep(args.delay)

    sitemap_urls = set(sitemap_url_list)
    findings, duplicate_groups = build_findings(
        pages,
        sitemap_urls,
        inbound,
        effective_root,
        query_urls,
        robots_record,
    )
    severity_counts = Counter(item["severity"] for item in findings)
    code_counts = Counter(item["code"] for item in findings)
    summary = {
        "pages_requested": requested_count,
        "pages_fetched": len(pages),
        "html_pages": sum(1 for page in pages if page.get("is_html")),
        "blocked_by_robots": len(blocked),
        "fetch_failures": sum(1 for page in pages if page.get("status") is None),
        "sitemap_files_fetched": len(sitemap_records),
        "sitemap_urls_discovered": len(sitemap_urls),
        "internal_links_observed": len(internal_edges),
        "external_links_observed": len(external_edges),
        "query_urls_discovered": len(query_urls),
        "findings_total": len(findings),
        "findings_by_severity": dict(sorted(severity_counts.items())),
        "findings_by_code": dict(sorted(code_counts.items())),
        "exact_text_duplicate_groups": len(duplicate_groups),
        "coverage_limit_reached": len(pages) >= args.max_pages,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": "audit_site.py",
        "tool_version": VERSION,
        "started_at": started_at,
        "completed_at": utc_now(),
        "target": {
            "requested": seed,
            "effective_root": effective_root,
            "initial_host": initial_host,
            "allowed_hosts": sorted(policy.allowed_hosts),
        },
        "configuration": {
            "max_pages": args.max_pages,
            "max_depth": args.max_depth,
            "max_sitemaps": args.max_sitemaps,
            "max_sitemap_urls": args.max_sitemap_urls,
            "max_response_bytes": args.max_response_bytes,
            "timeout": args.timeout,
            "delay": args.delay,
            "user_agent": args.user_agent,
            "include_subdomains": args.include_subdomains,
            "include_query_urls": args.include_query_urls,
            "sitemaps_enabled": not args.no_sitemaps,
            "robots_respected": not args.ignore_robots,
            "allow_private": args.allow_private,
            "allow_nonstandard_port": args.allow_nonstandard_port,
        },
        "robots": robots_record,
        "sitemaps": sitemap_records,
        "summary": summary,
        "blocked_urls": sorted(blocked),
        "query_urls_discovered": sorted(query_urls),
        "pages": pages,
        "internal_links": internal_edges,
        "external_links": external_edges,
        "duplicate_text_groups": duplicate_groups,
        "findings": findings,
        "limitations": [
            "Capped, same-site HTTP crawler; coverage is not exhaustive.",
            "HTML parsing uses raw responses and does not execute JavaScript.",
            "Word counts and text fingerprints include some template text.",
            "The crawler does not report a search engine index or rankings.",
            "External link destinations are recorded but not fetched.",
            "Heuristic findings require page-purpose and first-party validation.",
        ],
    }


def main() -> int:
    args = parse_args()
    try:
        validate_args(args)
        audit = run(args)
        json_text = json.dumps(audit, indent=2, ensure_ascii=False) + "\n"
        if args.output == "-":
            sys.stdout.write(json_text)
        else:
            write_atomic(Path(args.output), json_text)
            print(
                f"Wrote {args.output}: {audit['summary']['pages_fetched']} pages, "
                f"{audit['summary']['findings_total']} finding instances",
                file=sys.stderr,
            )
        if args.markdown:
            report = markdown_report(audit, args.max_markdown_findings)
            if args.markdown == "-":
                sys.stdout.write(report)
            else:
                write_atomic(Path(args.markdown), report)
                print(f"Wrote {args.markdown}", file=sys.stderr)
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
