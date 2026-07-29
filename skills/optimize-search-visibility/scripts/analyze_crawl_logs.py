#!/usr/bin/env python3
"""Analyze owned HTTP access-log exports for claimed crawler behavior.

The analyzer is local-only, uses the Python standard library, redacts query
values, and never treats a user-agent match as verified crawler identity.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import re
import sys
import tempfile
import urllib.parse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Iterator, TextIO
from pathlib import Path

VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"
DEFAULT_MAX_LINE_CHARS = 1_000_000
DEFAULT_BOT_PATTERNS = (
    ("google-search", r"\bgooglebot\b"),
    ("bing-search", r"\bbingbot\b"),
    ("openai-search", r"\boai-searchbot\b"),
    ("openai-user-fetch", r"\bchatgpt-user\b"),
    ("openai-training", r"\bgptbot\b"),
    ("perplexity-search", r"\bperplexitybot\b"),
    ("perplexity-user-fetch", r"\bperplexity-user\b"),
    ("anthropic-crawler", r"\bclaudebot\b"),
    ("anthropic-user-fetch", r"\bclaude-user\b"),
    ("apple-search", r"\bapplebot\b"),
    ("duckduckgo-search", r"\bduckduckbot\b"),
    ("yandex-search", r"\byandexbot\b"),
    ("baidu-search", r"\bbaiduspider\b"),
    ("generic-claimed-crawler", r"(?:bot|crawler|spider|slurp|archiver|fetcher)"),
)
COMBINED_RE = re.compile(
    r"^(?P<remote>\S+)\s+\S+\s+\S+\s+"
    r"\[(?P<time>[^\]]+)\]\s+"
    r'"(?P<request>[^"]*)"\s+'
    r"(?P<status>\d{3}|-)\s+(?P<bytes>\d+|-)"
    r'(?:\s+"(?P<referer>[^"]*)"\s+"(?P<ua>[^"]*)")?'
    r"(?P<tail>.*)$"
)
VHOST_COMBINED_RE = re.compile(
    r"^(?P<host>\S+)\s+(?P<remote>\S+)\s+\S+\s+\S+\s+"
    r"\[(?P<time>[^\]]+)\]\s+"
    r'"(?P<request>[^"]*)"\s+'
    r"(?P<status>\d{3}|-)\s+(?P<bytes>\d+|-)"
    r'(?:\s+"(?P<referer>[^"]*)"\s+"(?P<ua>[^"]*)")?'
    r"(?P<tail>.*)$"
)
COMMON_TIME_FORMATS = (
    "%d/%b/%Y:%H:%M:%S %z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%d %H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
)
TIME_BANDS_MS = (100, 250, 500, 1_000, 2_500, 5_000, 10_000)
STATIC_EXTENSIONS = {
    ".avif",
    ".css",
    ".eot",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".m4a",
    ".m4v",
    ".map",
    ".mp3",
    ".mp4",
    ".ogg",
    ".otf",
    ".pdf",
    ".png",
    ".svg",
    ".ttf",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
    ".xml",
}
CARDINALITY_BUCKET = "(other-after-cardinality-cap)"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return ""
    return str(value).strip()


def to_int(value: Any) -> int | None:
    text = as_text(value).replace(",", "")
    if not text or text == "-":
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError, OverflowError):
        return None


def to_float(value: Any) -> float | None:
    text = as_text(value).replace(",", "")
    if not text or text == "-":
        return None
    try:
        number = float(text)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def nested_value(record: dict[str, Any], path: str) -> Any:
    current: Any = record
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def first_value(record: dict[str, Any], paths: Iterable[str]) -> Any:
    for path in paths:
        value = nested_value(record, path)
        if value is not None and as_text(value):
            return value
    return None


def parse_timestamp(value: Any) -> datetime | None:
    text = as_text(value)
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass
    for pattern in COMMON_TIME_FORMATS:
        try:
            parsed = datetime.strptime(text, pattern)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def normalized_record(record: dict[str, Any]) -> dict[str, Any]:
    return {normalize_header(str(key)): value for key, value in record.items()}


@dataclass
class LogRecord:
    timestamp: datetime | None
    method: str
    target: str
    status: int | None
    bytes_sent: int | None
    user_agent: str
    host: str = ""
    response_ms: float | None = None
    content_type: str = ""
    cache_status: str = ""


def record_from_mapping(record: dict[str, Any]) -> LogRecord:
    normalized = normalized_record(record)
    timestamp = first_value(
        record,
        (
            "@timestamp",
            "timestamp",
            "time",
            "datetime",
            "date",
            "request.time",
            "httpRequest.requestTime",
        ),
    )
    if timestamp is None:
        timestamp = first_value(
            normalized, ("timestamp", "time", "datetime", "date", "time_local")
        )
    method = first_value(
        record,
        (
            "method",
            "request_method",
            "http.method",
            "request.method",
            "httpRequest.requestMethod",
        ),
    )
    if method is None:
        method = first_value(normalized, ("method", "request_method", "cs_method"))
    target = first_value(
        record,
        (
            "target",
            "url",
            "uri",
            "path",
            "request_uri",
            "http.target",
            "request.url",
            "httpRequest.requestUrl",
        ),
    )
    if target is None:
        target = first_value(
            normalized,
            (
                "target",
                "url",
                "uri",
                "path",
                "request_uri",
                "cs_uri_stem",
            ),
        )
    status = first_value(
        record,
        ("status", "status_code", "http.status_code", "httpRequest.status"),
    )
    if status is None:
        status = first_value(normalized, ("status", "status_code", "sc_status"))
    bytes_sent = first_value(
        record,
        (
            "bytes",
            "bytes_sent",
            "body_bytes_sent",
            "response.size",
            "httpRequest.responseSize",
        ),
    )
    if bytes_sent is None:
        bytes_sent = first_value(
            normalized,
            ("bytes", "bytes_sent", "body_bytes_sent", "sc_bytes"),
        )
    user_agent = first_value(
        record,
        (
            "user_agent",
            "ua",
            "http_user_agent",
            "http.user_agent",
            "request.user_agent",
            "httpRequest.userAgent",
        ),
    )
    if user_agent is None:
        user_agent = first_value(
            normalized, ("user_agent", "ua", "http_user_agent", "cs_user_agent")
        )
    host = first_value(
        record,
        (
            "host",
            "hostname",
            "http_host",
            "http.host",
            "request.host",
            "httpRequest.host",
        ),
    )
    if host is None:
        host = first_value(normalized, ("host", "hostname", "http_host", "cs_host"))
    content_type = first_value(
        record, ("content_type", "response.content_type", "http.response_content_type")
    )
    if content_type is None:
        content_type = first_value(
            normalized, ("content_type", "response_content_type", "sc_content_type")
        )
    cache_status = first_value(
        record, ("cache_status", "upstream_cache_status", "response.cache_status")
    )
    if cache_status is None:
        cache_status = first_value(
            normalized, ("cache_status", "upstream_cache_status", "x_cache")
        )

    response_ms_value = first_value(
        record,
        (
            "response_time_ms",
            "request_time_ms",
            "duration_ms",
            "latency_ms",
        ),
    )
    if response_ms_value is None:
        response_ms_value = first_value(
            normalized,
            ("response_time_ms", "request_time_ms", "duration_ms", "latency_ms"),
        )
    response_ms = to_float(response_ms_value)
    if response_ms is None:
        response_seconds_value = first_value(
            record,
            (
                "response_time",
                "request_time",
                "upstream_response_time",
                "latency_seconds",
            ),
        )
        if response_seconds_value is None:
            response_seconds_value = first_value(
                normalized,
                (
                    "response_time",
                    "request_time",
                    "upstream_response_time",
                    "latency_seconds",
                ),
            )
        response_seconds = to_float(response_seconds_value)
        response_ms = response_seconds * 1_000 if response_seconds is not None else None

    return LogRecord(
        timestamp=parse_timestamp(timestamp),
        method=as_text(method).upper(),
        target=as_text(target),
        status=to_int(status),
        bytes_sent=to_int(bytes_sent),
        user_agent=as_text(user_agent),
        host=as_text(host).casefold(),
        response_ms=response_ms,
        content_type=as_text(content_type).casefold(),
        cache_status=as_text(cache_status).casefold(),
    )


def record_from_combined(line: str, time_field: str) -> LogRecord | None:
    match = COMBINED_RE.match(line) or VHOST_COMBINED_RE.match(line)
    if not match:
        return None
    data = match.groupdict()
    request_parts = data.get("request", "").split()
    method = request_parts[0].upper() if request_parts else ""
    target = request_parts[1] if len(request_parts) >= 2 else ""
    response_ms: float | None = None
    if time_field != "none":
        tail_parts = data.get("tail", "").strip().split()
        tail_number = to_float(tail_parts[-1]) if tail_parts else None
        if tail_number is not None:
            response_ms = (
                tail_number * 1_000 if time_field == "seconds" else tail_number
            )
    return LogRecord(
        timestamp=parse_timestamp(data.get("time")),
        method=method,
        target=target,
        status=to_int(data.get("status")),
        bytes_sent=to_int(data.get("bytes")),
        user_agent=as_text(data.get("ua")),
        host=as_text(data.get("host")).casefold(),
        response_ms=response_ms,
    )


def open_text(path: Path, encoding: str) -> TextIO:
    if path.suffix.casefold() == ".gz":
        return gzip.open(path, "rt", encoding=encoding, errors="replace", newline="")
    return path.open("r", encoding=encoding, errors="replace", newline="")


def detect_format(path: Path, encoding: str) -> str:
    with open_text(path, encoding) as handle:
        for line in handle:
            stripped = line.lstrip("\ufeff").strip()
            if not stripped:
                continue
            if stripped.startswith("{"):
                return "jsonl"
            dialect = "\t" if "\t" in stripped and "," not in stripped else ","
            if dialect in stripped:
                headers = {
                    normalize_header(item)
                    for item in next(csv.reader([stripped], delimiter=dialect))
                }
                if headers.intersection(
                    {
                        "status",
                        "status_code",
                        "sc_status",
                        "user_agent",
                        "http_user_agent",
                        "cs_user_agent",
                        "request_uri",
                    }
                ):
                    return "tsv" if dialect == "\t" else "csv"
            return "combined"
    return "combined"


def iter_records(
    path: Path,
    input_format: str,
    encoding: str,
    max_line_chars: int,
    combined_time_field: str,
) -> Iterator[tuple[int, LogRecord | None, str]]:
    selected = detect_format(path, encoding) if input_format == "auto" else input_format
    if selected in {"csv", "tsv"}:
        delimiter = "\t" if selected == "tsv" else ","
        with open_text(path, encoding) as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            if not reader.fieldnames:
                yield 1, None, "missing CSV header"
                return
            for line_number, row in enumerate(reader, start=2):
                if any(len(as_text(value)) > max_line_chars for value in row.values()):
                    yield line_number, None, "field exceeds --max-line-chars"
                    continue
                yield line_number, record_from_mapping(dict(row)), ""
        return

    with open_text(path, encoding) as handle:
        for line_number, line in enumerate(handle, start=1):
            if len(line) > max_line_chars:
                yield line_number, None, "line exceeds --max-line-chars"
                continue
            stripped = line.lstrip("\ufeff").strip()
            if not stripped:
                continue
            if selected == "jsonl":
                try:
                    value = json.loads(stripped)
                except json.JSONDecodeError:
                    yield line_number, None, "invalid JSON"
                    continue
                if not isinstance(value, dict):
                    yield line_number, None, "JSON value is not an object"
                    continue
                yield line_number, record_from_mapping(value), ""
            else:
                record = record_from_combined(stripped, combined_time_field)
                if record is None:
                    yield line_number, None, "line does not match common/combined format"
                else:
                    yield line_number, record, ""


def parse_bot_patterns(
    custom_patterns: list[str], use_defaults: bool
) -> list[tuple[str, re.Pattern[str]]]:
    raw_patterns: list[tuple[str, str]] = []
    for item in custom_patterns:
        if "=" not in item:
            raise ValueError("--bot-pattern must use FAMILY=REGEX")
        family, pattern = item.split("=", 1)
        family = family.strip()
        if not family or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", family):
            raise ValueError(f"invalid bot family: {family!r}")
        if not pattern:
            raise ValueError(f"empty regex for bot family {family!r}")
        raw_patterns.append((family, pattern))
    if use_defaults:
        raw_patterns.extend(DEFAULT_BOT_PATTERNS)
    if not raw_patterns:
        raise ValueError("at least one bot pattern is required")

    compiled: list[tuple[str, re.Pattern[str]]] = []
    seen: set[str] = set()
    for family, pattern in raw_patterns:
        if family in seen:
            raise ValueError(f"duplicate bot family: {family}")
        try:
            compiled.append((family, re.compile(pattern, re.IGNORECASE)))
        except re.error as exc:
            raise ValueError(f"invalid regex for {family}: {exc}") from exc
        seen.add(family)
    return compiled


def claimed_family(
    user_agent: str, patterns: list[tuple[str, re.Pattern[str]]]
) -> str | None:
    for family, pattern in patterns:
        if pattern.search(user_agent):
            return family
    return None


def split_target(target: str) -> tuple[str, list[str]]:
    if not target:
        return "", []
    value = target
    if "://" not in value:
        value = "https://placeholder.invalid" + (
            value if value.startswith("/") else "/" + value
        )
    try:
        parts = urllib.parse.urlsplit(value)
    except ValueError:
        return "", []
    path = parts.path or "/"
    while "//" in path:
        path = path.replace("//", "/")
    try:
        query_names = sorted(
            {
                key
                for key, _ in urllib.parse.parse_qsl(
                    parts.query, keep_blank_values=True, strict_parsing=False
                )
                if key
            }
        )
    except ValueError:
        query_names = []
    return path, query_names


def path_group(path: str, depth: int) -> str:
    if not path:
        return "(missing)"
    parts = [part for part in path.split("/") if part]
    if not parts:
        return "/"
    selected = "/" + "/".join(parts[:depth])
    return selected + ("/*" if len(parts) > depth else "")


def content_cohort(path: str, content_type: str) -> str:
    lowered_type = content_type.casefold()
    if lowered_type:
        if "html" in lowered_type:
            return "html"
        if "image" in lowered_type:
            return "image"
        if "javascript" in lowered_type or "css" in lowered_type:
            return "script-style"
        if "json" in lowered_type or "xml" in lowered_type:
            return "data-feed"
        if "video" in lowered_type or "audio" in lowered_type:
            return "media"
    suffix = Path(path.casefold()).suffix
    if suffix in STATIC_EXTENSIONS:
        if suffix in {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".avif"}:
            return "image"
        if suffix in {".js", ".css", ".map"}:
            return "script-style"
        if suffix in {".xml"}:
            return "data-feed"
        if suffix in {".mp3", ".mp4", ".m4a", ".m4v", ".ogg", ".webm"}:
            return "media"
        return "asset"
    return "page-like"


@dataclass
class TimingStats:
    count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0
    bands: Counter[str] = field(default_factory=Counter)

    def add(self, milliseconds: float | None) -> None:
        if milliseconds is None:
            return
        self.count += 1
        self.total_ms += milliseconds
        self.max_ms = max(self.max_ms, milliseconds)
        for threshold in TIME_BANDS_MS:
            if milliseconds <= threshold:
                self.bands[f"at_or_below_{threshold}ms"] += 1
                break
        else:
            self.bands["above_10000ms"] += 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "samples": self.count,
            "mean_ms": round(self.total_ms / self.count, 2) if self.count else None,
            "max_ms": round(self.max_ms, 2) if self.count else None,
            "bands": dict(sorted(self.bands.items())),
        }


@dataclass
class FamilyStats:
    requests: int = 0
    bytes_sent: int = 0
    status_codes: Counter[int] = field(default_factory=Counter)
    status_classes: Counter[str] = field(default_factory=Counter)
    methods: Counter[str] = field(default_factory=Counter)
    days: Counter[str] = field(default_factory=Counter)
    hosts: Counter[str] = field(default_factory=Counter)
    paths: Counter[str] = field(default_factory=Counter)
    path_groups: Counter[str] = field(default_factory=Counter)
    content_cohorts: Counter[str] = field(default_factory=Counter)
    query_parameters: Counter[str] = field(default_factory=Counter)
    cache_statuses: Counter[str] = field(default_factory=Counter)
    timing: TimingStats = field(default_factory=TimingStats)


def top_items(counter: Counter[Any], limit: int) -> list[dict[str, Any]]:
    return [
        {"value": value, "requests": count}
        for value, count in sorted(
            counter.items(), key=lambda item: (-item[1], str(item[0]))
        )[:limit]
    ]


def increment_bounded(counter: Counter[Any], key: Any, limit: int) -> bool:
    if key in counter or len(counter) < limit:
        counter[key] += 1
        return False
    counter[CARDINALITY_BUCKET] += 1
    return True


def markdown_code(value: Any) -> str:
    text = as_text(value).replace("\r", " ").replace("\n", " ")
    text = text.replace("|", r"\|").replace("`", "'")
    return f"`{text}`"


def load_audit_paths(path: Path) -> set[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read --audit-json: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("pages"), list):
        raise ValueError("--audit-json must be output from audit_site.py")
    paths: set[str] = set()
    for page in data["pages"]:
        if not isinstance(page, dict):
            continue
        raw_url = as_text(page.get("url"))
        try:
            parsed = urllib.parse.urlsplit(raw_url)
        except ValueError:
            continue
        if parsed.path:
            paths.add(parsed.path)
    return paths


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    csv.field_size_limit(args.max_line_chars)
    patterns = parse_bot_patterns(args.bot_pattern, not args.no_default_bots)
    audit_paths = load_audit_paths(Path(args.audit_json)) if args.audit_json else set()
    family_stats: defaultdict[str, FamilyStats] = defaultdict(FamilyStats)
    parse_errors: Counter[str] = Counter()
    file_stats: list[dict[str, Any]] = []
    all_bot_paths: Counter[str] = Counter()
    bot_error_paths: Counter[str] = Counter()
    bot_redirect_paths: Counter[str] = Counter()
    bot_query_paths: Counter[str] = Counter()
    totals: Counter[str] = Counter()
    first_time: datetime | None = None
    last_time: datetime | None = None
    stop = False

    for input_name in args.inputs:
        path = Path(input_name)
        if not path.is_file():
            raise ValueError(f"input file does not exist: {path}")
        selected_format = (
            detect_format(path, args.encoding)
            if args.input_format == "auto"
            else args.input_format
        )
        current = Counter()
        for line_number, record, error in iter_records(
            path,
            args.input_format,
            args.encoding,
            args.max_line_chars,
            args.combined_time_field,
        ):
            totals["lines_considered"] += 1
            current["lines_considered"] += 1
            if totals["lines_considered"] > args.max_lines:
                totals["lines_considered"] -= 1
                current["lines_considered"] -= 1
                totals["max_lines_reached"] = 1
                stop = True
                break
            if record is None:
                totals["parse_failures"] += 1
                current["parse_failures"] += 1
                parse_errors[error or "unknown parse error"] += 1
                continue
            if not record.target or record.status is None:
                totals["incomplete_records"] += 1
                current["incomplete_records"] += 1
                continue
            totals["records_parsed"] += 1
            current["records_parsed"] += 1
            if record.timestamp:
                first_time = (
                    record.timestamp
                    if first_time is None
                    else min(first_time, record.timestamp)
                )
                last_time = (
                    record.timestamp
                    if last_time is None
                    else max(last_time, record.timestamp)
                )

            family = claimed_family(record.user_agent, patterns)
            if family is None:
                totals["noncrawler_records"] += 1
                current["noncrawler_records"] += 1
                if not args.include_non_crawlers:
                    continue
                family = "unclassified-client"
            else:
                totals["claimed_crawler_records"] += 1
                current["claimed_crawler_records"] += 1

            path_value, query_names = split_target(record.target)
            if not path_value:
                totals["invalid_targets"] += 1
                current["invalid_targets"] += 1
                continue
            stats = family_stats[family]
            stats.requests += 1
            stats.bytes_sent += record.bytes_sent or 0
            stats.status_codes[record.status] += 1
            status_class = f"{record.status // 100}xx"
            stats.status_classes[status_class] += 1
            stats.methods[record.method or "(missing)"] += 1
            if record.timestamp and increment_bounded(
                stats.days,
                record.timestamp.date().isoformat(),
                args.max_unique_values,
            ):
                totals["cardinality_overflow_events"] += 1
            if increment_bounded(
                stats.hosts,
                record.host or "(not logged)",
                args.max_unique_values,
            ):
                totals["cardinality_overflow_events"] += 1
            if increment_bounded(
                stats.paths, path_value, args.max_unique_values
            ):
                totals["cardinality_overflow_events"] += 1
            if increment_bounded(
                stats.path_groups,
                path_group(path_value, args.path_depth),
                args.max_unique_values,
            ):
                totals["cardinality_overflow_events"] += 1
            stats.content_cohorts[content_cohort(path_value, record.content_type)] += 1
            stats.cache_statuses[record.cache_status or "(not logged)"] += 1
            stats.timing.add(record.response_ms)
            for parameter in query_names:
                if increment_bounded(
                    stats.query_parameters, parameter, args.max_unique_values
                ):
                    totals["cardinality_overflow_events"] += 1

            if family != "unclassified-client":
                for counter, should_increment in (
                    (all_bot_paths, True),
                    (bot_query_paths, bool(query_names)),
                    (bot_error_paths, record.status >= 400),
                    (bot_redirect_paths, 300 <= record.status < 400),
                ):
                    if should_increment and increment_bounded(
                        counter, path_value, args.max_unique_values
                    ):
                        totals["cardinality_overflow_events"] += 1
        file_stats.append(
            {
                "file": path.name,
                "format": selected_format,
                **dict(sorted(current.items())),
            }
        )
        if stop:
            break

    families: dict[str, Any] = {}
    for family, stats in sorted(
        family_stats.items(), key=lambda item: (-item[1].requests, item[0])
    ):
        families[family] = {
            "identity": "claimed-by-user-agent-not-verified",
            "requests": stats.requests,
            "bytes_sent": stats.bytes_sent,
            "status_codes": {
                str(key): value for key, value in sorted(stats.status_codes.items())
            },
            "status_classes": dict(sorted(stats.status_classes.items())),
            "methods": dict(sorted(stats.methods.items())),
            "days": dict(sorted(stats.days.items())),
            "top_hosts": top_items(stats.hosts, args.top),
            "top_paths": top_items(stats.paths, args.top),
            "top_path_groups": top_items(stats.path_groups, args.top),
            "content_cohorts": dict(sorted(stats.content_cohorts.items())),
            "query_parameters": top_items(stats.query_parameters, args.top),
            "cache_statuses": dict(sorted(stats.cache_statuses.items())),
            "response_timing": stats.timing.as_dict(),
        }

    inventory_comparison: dict[str, Any] | None = None
    if audit_paths:
        observed = set(all_bot_paths) - {CARDINALITY_BUCKET}
        inventory_comparison = {
            "audit_paths": len(audit_paths),
            "bot_observed_paths": len(observed),
            "audit_paths_not_observed": sorted(audit_paths - observed)[: args.top],
            "observed_paths_not_in_audit": top_items(
                Counter(
                    {
                        path: count
                        for path, count in all_bot_paths.items()
                        if path not in audit_paths
                    }
                ),
                args.top,
            ),
            "caveat": (
                "Absence only applies to the supplied log window and audit sample; "
                "it does not prove a crawler never requested the path."
            ),
        }

    parsed = totals["records_parsed"]
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": "analyze_crawl_logs.py",
        "tool_version": VERSION,
        "generated_at": utc_now(),
        "configuration": {
            "inputs": [Path(item).name for item in args.inputs],
            "input_format": args.input_format,
            "encoding": args.encoding,
            "max_lines": args.max_lines,
            "max_line_chars": args.max_line_chars,
            "max_unique_values": args.max_unique_values,
            "path_depth": args.path_depth,
            "include_non_crawlers": args.include_non_crawlers,
            "combined_time_field": args.combined_time_field,
            "default_bot_patterns": not args.no_default_bots,
            "custom_bot_families": [
                item.split("=", 1)[0] for item in args.bot_pattern
            ],
            "query_values_stored": False,
        },
        "coverage": {
            **dict(sorted(totals.items())),
            "parse_success_rate": round(parsed / totals["lines_considered"], 6)
            if totals["lines_considered"]
            else None,
            "first_timestamp_utc": first_time.isoformat() if first_time else None,
            "last_timestamp_utc": last_time.isoformat() if last_time else None,
            "files": file_stats,
            "parse_failure_reasons": dict(sorted(parse_errors.items())),
        },
        "families": families,
        "cross_family": {
            "top_error_paths": top_items(bot_error_paths, args.top),
            "top_redirect_paths": top_items(bot_redirect_paths, args.top),
            "top_query_paths": top_items(bot_query_paths, args.top),
            "unique_claimed_crawler_paths": len(all_bot_paths),
        },
        "audit_inventory_comparison": inventory_comparison,
        "limitations": [
            "User-agent matches are claims, not verified crawler identities.",
            "Access logs show requests, not indexing, ranking, citation, or user value.",
            "Query parameter names are counted; query values are never stored.",
            (
                "Common/combined formats do not expose every host, content type, "
                "cache, or timing field."
            ),
            (
                "Timestamp parsing normalizes known offsets to UTC; unparseable "
                "timestamps are omitted from date trends."
            ),
            (
                "Capped or incomplete log exports can make low-frequency and "
                "absence conclusions unreliable."
            ),
            (
                "High-cardinality counters are capped; overflow is grouped and "
                "reported in coverage."
            ),
        ],
    }


def markdown_report(analysis: dict[str, Any]) -> str:
    coverage = analysis["coverage"]
    lines = [
        "# Claimed crawler log analysis",
        "",
        f"- Generated: {analysis['generated_at']}",
        f"- Parsed: {coverage.get('records_parsed', 0)} records from "
        f"{coverage.get('lines_considered', 0)} considered lines",
        f"- Claimed crawler records: {coverage.get('claimed_crawler_records', 0)}",
        f"- Parse failures: {coverage.get('parse_failures', 0)}",
        f"- UTC range: {coverage.get('first_timestamp_utc') or 'unknown'} to "
        f"{coverage.get('last_timestamp_utc') or 'unknown'}",
        "",
        "> Crawler families are inferred from user-agent text and are not identity-verified. "
        "Logs show requests, not indexing, ranking, citations, or business outcomes.",
        "",
        "## Families",
        "",
        "| Claimed family | Requests | 2xx | 3xx | 4xx | 5xx | Mean response |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for family, data in analysis["families"].items():
        status = data["status_classes"]
        mean = data["response_timing"]["mean_ms"]
        lines.append(
            f"| {family} | {data['requests']} | {status.get('2xx', 0)} | "
            f"{status.get('3xx', 0)} | {status.get('4xx', 0)} | "
            f"{status.get('5xx', 0)} | "
            f"{f'{mean:.2f} ms' if mean is not None else 'not logged'} |"
        )

    for family, data in analysis["families"].items():
        lines.extend(
            [
                "",
                f"## {family}",
                "",
                "### Top path groups",
                "",
                "| Path group | Requests |",
                "| --- | ---: |",
            ]
        )
        for item in data["top_path_groups"]:
            lines.append(
                f"| {markdown_code(item['value'])} | {item['requests']} |"
            )
        if data["query_parameters"]:
            lines.extend(
                [
                    "",
                    "### Query parameter names",
                    "",
                    "| Parameter | Requests |",
                    "| --- | ---: |",
                ]
            )
            for item in data["query_parameters"]:
                lines.append(
                    f"| {markdown_code(item['value'])} | {item['requests']} |"
                )

    lines.extend(
        [
            "",
            "## Cross-family leads",
            "",
            "### Error paths",
            "",
            "| Path | Requests |",
            "| --- | ---: |",
        ]
    )
    for item in analysis["cross_family"]["top_error_paths"]:
        lines.append(f"| {markdown_code(item['value'])} | {item['requests']} |")

    lines.extend(
        [
            "",
            "### Redirect paths",
            "",
            "| Path | Requests |",
            "| --- | ---: |",
        ]
    )
    for item in analysis["cross_family"]["top_redirect_paths"]:
        lines.append(f"| {markdown_code(item['value'])} | {item['requests']} |")

    comparison = analysis.get("audit_inventory_comparison")
    if comparison:
        lines.extend(
            [
                "",
                "## Crawl-inventory comparison",
                "",
                f"- Audit paths: {comparison['audit_paths']}",
                f"- Claimed-crawler paths observed: {comparison['bot_observed_paths']}",
                f"- Caveat: {comparison['caveat']}",
                "",
                "### Audit paths not observed in this log window",
                "",
            ]
        )
        lines.extend(
            f"- {markdown_code(path)}"
            for path in comparison["audit_paths_not_observed"]
        )

    lines.extend(
        [
            "",
            "## Next evidence",
            "",
            (
                "- Verify consequential crawler identities using current provider "
                "and infrastructure guidance."
            ),
            (
                "- Join path cohorts to intended canonical/index state, sitemaps, "
                "business priority, and deployment history."
            ),
            (
                "- Inspect repeated errors, redirects, query patterns, slow "
                "cohorts, and unexpected inventory directly."
            ),
            (
                "- Compare equivalent log windows after a controlled fix; do not "
                "infer indexing from requests."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("inputs", nargs="+", help="Owned access-log files; .gz supported")
    parser.add_argument(
        "--input-format",
        choices=("auto", "combined", "jsonl", "csv", "tsv"),
        default="auto",
        help="Input format",
    )
    parser.add_argument("--encoding", default="utf-8", help="Input text encoding")
    parser.add_argument(
        "--combined-time-field",
        choices=("none", "seconds", "milliseconds"),
        default="none",
        help="Interpret the final combined-log field as response time",
    )
    parser.add_argument(
        "--bot-pattern",
        action="append",
        default=[],
        metavar="FAMILY=REGEX",
        help="Prepend a custom claimed-crawler user-agent pattern",
    )
    parser.add_argument(
        "--no-default-bots",
        action="store_true",
        help="Use only custom --bot-pattern values",
    )
    parser.add_argument(
        "--include-non-crawlers",
        action="store_true",
        help="Include unmatched clients as an unclassified family",
    )
    parser.add_argument(
        "--audit-json",
        help="Optional audit_site.py JSON for path-inventory comparison",
    )
    parser.add_argument(
        "--path-depth",
        type=int,
        default=2,
        help="Path segments retained in grouped paths",
    )
    parser.add_argument(
        "--top", type=int, default=25, help="Maximum rows in each top list"
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=5_000_000,
        help="Maximum non-empty data lines considered across inputs",
    )
    parser.add_argument(
        "--max-line-chars",
        type=int,
        default=DEFAULT_MAX_LINE_CHARS,
        help="Reject oversized input lines or fields",
    )
    parser.add_argument(
        "--max-unique-values",
        type=int,
        default=100_000,
        help="Maximum distinct values retained per high-cardinality counter",
    )
    parser.add_argument("--output", default="-", help="JSON output path, or -")
    parser.add_argument("--markdown", help="Optional Markdown report path, or -")
    parser.add_argument("--version", action="version", version=VERSION)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not 1 <= args.path_depth <= 20:
        raise ValueError("--path-depth must be between 1 and 20")
    if not 1 <= args.top <= 1_000:
        raise ValueError("--top must be between 1 and 1000")
    if not 1 <= args.max_lines <= 100_000_000:
        raise ValueError("--max-lines must be between 1 and 100000000")
    if not 1_024 <= args.max_line_chars <= 100_000_000:
        raise ValueError("--max-line-chars must be between 1024 and 100000000")
    if not 100 <= args.max_unique_values <= 1_000_000:
        raise ValueError("--max-unique-values must be between 100 and 1000000")
    if len(args.inputs) > 1_000:
        raise ValueError("at most 1000 input files are supported")
    if len(args.bot_pattern) > 1_000:
        raise ValueError("at most 1000 custom bot patterns are supported")
    if args.output == "-" and args.markdown == "-":
        raise ValueError("JSON and Markdown cannot both use stdout")
    try:
        "".encode(args.encoding)
    except LookupError as exc:
        raise ValueError(f"unknown encoding: {args.encoding}") from exc


def main() -> int:
    args = parse_args()
    try:
        validate_args(args)
        analysis = analyze(args)
        json_text = json.dumps(analysis, indent=2, ensure_ascii=False) + "\n"
        if args.output == "-":
            sys.stdout.write(json_text)
        else:
            write_atomic(Path(args.output), json_text)
            print(
                f"Wrote {args.output}: "
                f"{analysis['coverage'].get('records_parsed', 0)} records, "
                f"{analysis['coverage'].get('claimed_crawler_records', 0)} "
                "claimed-crawler records",
                file=sys.stderr,
            )
        if args.markdown:
            report = markdown_report(analysis)
            if args.markdown == "-":
                sys.stdout.write(report)
            else:
                write_atomic(Path(args.markdown), report)
                print(f"Wrote {args.markdown}", file=sys.stderr)
        return 0
    except (ValueError, OSError, csv.Error) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2


if __name__ == "__main__":
    exit_code = main()
    raise SystemExit(exit_code)
