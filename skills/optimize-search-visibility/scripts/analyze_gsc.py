#!/usr/bin/env python3
"""Analyze Google Search Console CSV exports without external dependencies.

The script uses within-export peer groups and matched periods. It does not use
universal CTR targets, call multiple ranking pages "cannibalization," or
pretend that exported rows are complete Search Console totals.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import statistics
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Iterable

VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"

COLUMN_ALIASES = {
    "query": {
        "query",
        "queries",
        "top queries",
        "search query",
        "search queries",
        "requête",
        "requêtes",
        "suchanfrage",
        "suchanfragen",
        "consulta",
        "consultas",
        "pesquisa",
        "pesquisas",
    },
    "page": {
        "page",
        "pages",
        "top pages",
        "url",
        "urls",
        "landing page",
        "landing pages",
        "seite",
        "seiten",
        "página",
        "páginas",
    },
    "clicks": {
        "clicks",
        "click",
        "clics",
        "klicks",
        "cliques",
    },
    "impressions": {
        "impressions",
        "impression",
        "impressionen",
        "impresiones",
        "impressões",
    },
    "ctr": {
        "ctr",
        "average ctr",
        "click-through rate",
        "click through rate",
        "taux de clics",
        "durchschnittliche ctr",
        "ctr medio",
        "ctr média",
    },
    "position": {
        "position",
        "average position",
        "avg position",
        "position moyenne",
        "durchschnittliche position",
        "posición media",
        "posição média",
    },
    "date": {
        "date",
        "day",
        "datum",
        "fecha",
        "data",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold().replace("_", " "))


def canonical_column(value: str) -> str | None:
    normalized = normalize_header(value)
    for canonical, aliases in COLUMN_ALIASES.items():
        if normalized in aliases:
            return canonical
    return None


def parse_number(value: str, *, percentage: bool = False) -> float:
    raw = (value or "").strip().replace("\u00a0", "").replace(" ", "")
    if not raw or raw in {"-", "—", "~"}:
        return 0.0
    is_percent = raw.endswith("%")
    if is_percent:
        raw = raw[:-1]
    raw = raw.replace("−", "-")
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        suffix = raw.rsplit(",", 1)[-1]
        if len(suffix) == 3 and raw.count(",") == 1 and not percentage:
            raw = raw.replace(",", "")
        else:
            raw = raw.replace(",", ".")
    try:
        number = float(raw)
    except ValueError as exc:
        raise ValueError(f"cannot parse numeric value {value!r}") from exc
    if is_percent or (percentage and number > 1):
        number /= 100.0
    if not math.isfinite(number):
        raise ValueError(f"numeric value must be finite: {value!r}")
    return number


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"{path} is not valid UTF-8 or UTF-16 text")


def sniff_dialect(text: str) -> csv.Dialect:
    sample = text[:64_000]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        return csv.excel


@dataclass
class Row:
    query: str
    page: str
    clicks: float
    impressions: float
    ctr: float
    position: float
    has_position: bool

    def key(self, dimensions: tuple[str, ...]) -> tuple[str, ...]:
        values = {"query": self.query, "page": self.page}
        return tuple(values[item] for item in dimensions)


@dataclass
class LoadedExport:
    path: Path
    sha256: str
    columns: dict[str, str]
    dimensions: tuple[str, ...]
    rows_read: int
    rows: list[Row]


def load_export(path: Path) -> LoadedExport:
    if not path.is_file():
        raise ValueError(f"input file does not exist: {path}")
    text = read_text(path)
    reader = csv.DictReader(text.splitlines(), dialect=sniff_dialect(text))
    if not reader.fieldnames:
        raise ValueError(f"{path} has no CSV header")

    columns: dict[str, str] = {}
    for original in reader.fieldnames:
        canonical = canonical_column(original)
        if canonical and canonical not in columns:
            columns[canonical] = original
    missing = {"clicks", "impressions"} - set(columns)
    if missing:
        raise ValueError(
            f"{path} is missing required column(s): {', '.join(sorted(missing))}; "
            f"headers were {reader.fieldnames}"
        )
    dimensions = tuple(item for item in ("query", "page") if item in columns)
    if not dimensions:
        raise ValueError(f"{path} must contain a Query or Page dimension")

    rows: list[Row] = []
    rows_read = 0
    for line_number, raw in enumerate(reader, 2):
        rows_read += 1
        try:
            query = (raw.get(columns.get("query", ""), "") or "").strip()
            page = (raw.get(columns.get("page", ""), "") or "").strip()
            if "query" in dimensions and not query:
                continue
            if "page" in dimensions and not page:
                continue
            clicks = parse_number(raw.get(columns["clicks"], "") or "")
            impressions = parse_number(raw.get(columns["impressions"], "") or "")
            if clicks < 0 or impressions < 0:
                raise ValueError("clicks and impressions must be non-negative")
            if "ctr" in columns:
                ctr = parse_number(
                    raw.get(columns["ctr"], "") or "", percentage=True
                )
            else:
                ctr = clicks / impressions if impressions else 0.0
            if "position" in columns:
                position = parse_number(raw.get(columns["position"], "") or "")
                has_position = True
            else:
                position = 0.0
                has_position = False
            rows.append(
                Row(
                    query=query,
                    page=page,
                    clicks=clicks,
                    impressions=impressions,
                    ctr=ctr,
                    position=position,
                    has_position=has_position,
                )
            )
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
    if not rows:
        raise ValueError(f"{path} contains no usable data rows")
    return LoadedExport(
        path=path,
        sha256=file_hash(path),
        columns=columns,
        dimensions=dimensions,
        rows_read=rows_read,
        rows=rows,
    )


def aggregate_rows(rows: Iterable[Row], dimensions: tuple[str, ...]) -> list[Row]:
    accumulators: dict[tuple[str, ...], dict[str, float]] = {}
    labels: dict[tuple[str, ...], tuple[str, str]] = {}
    for row in rows:
        key = row.key(dimensions)
        item = accumulators.setdefault(
            key,
            {
                "clicks": 0.0,
                "impressions": 0.0,
                "position_weighted": 0.0,
                "position_impressions": 0.0,
            },
        )
        item["clicks"] += row.clicks
        item["impressions"] += row.impressions
        if row.has_position and row.impressions > 0:
            item["position_weighted"] += row.position * row.impressions
            item["position_impressions"] += row.impressions
        labels[key] = (row.query, row.page)
    aggregated: list[Row] = []
    for key, item in accumulators.items():
        query, page = labels[key]
        impressions = item["impressions"]
        position_impressions = item["position_impressions"]
        aggregated.append(
            Row(
                query=query,
                page=page,
                clicks=item["clicks"],
                impressions=impressions,
                ctr=item["clicks"] / impressions if impressions else 0.0,
                position=(
                    item["position_weighted"] / position_impressions
                    if position_impressions
                    else 0.0
                ),
                has_position=bool(position_impressions),
            )
        )
    return aggregated


def row_record(row: Row) -> dict[str, Any]:
    record: dict[str, Any] = {
        "query": row.query or None,
        "page": row.page or None,
        "clicks": round(row.clicks, 4),
        "impressions": round(row.impressions, 4),
        "ctr": round(row.ctr, 8),
    }
    record["position"] = round(row.position, 4) if row.has_position else None
    return record


def summarize(rows: Iterable[Row]) -> dict[str, Any]:
    values = list(rows)
    clicks = sum(row.clicks for row in values)
    impressions = sum(row.impressions for row in values)
    position_weight = sum(
        row.position * row.impressions
        for row in values
        if row.has_position and row.impressions > 0
    )
    position_impressions = sum(
        row.impressions
        for row in values
        if row.has_position and row.impressions > 0
    )
    return {
        "rows": len(values),
        "clicks": round(clicks, 4),
        "impressions": round(impressions, 4),
        "ctr": round(clicks / impressions, 8) if impressions else 0.0,
        "position": (
            round(position_weight / position_impressions, 4)
            if position_impressions
            else None
        ),
    }


def position_band(position: float) -> str:
    if position <= 3:
        return "1-3"
    if position <= 10:
        return "4-10"
    if position <= 20:
        return "11-20"
    if position <= 50:
        return "21-50"
    return "51+"


def compile_brand_pattern(terms: list[str], regex: str | None) -> re.Pattern[str] | None:
    pieces = [re.escape(term.strip()) for term in terms if term.strip()]
    if regex:
        pieces.append(f"(?:{regex})")
    if not pieces:
        return None
    try:
        return re.compile("|".join(pieces), re.IGNORECASE)
    except re.error as exc:
        raise ValueError(f"invalid --brand-regex: {exc}") from exc


def brand_class(query: str, pattern: re.Pattern[str] | None) -> str:
    if not query:
        return "not-available"
    if pattern is None:
        return "unclassified"
    return "brand" if pattern.search(query) else "non-brand"


def segment_summary(
    rows: list[Row], brand_pattern: re.Pattern[str] | None
) -> dict[str, dict[str, Any]]:
    groups: defaultdict[str, list[Row]] = defaultdict(list)
    for row in rows:
        groups[f"brand:{brand_class(row.query, brand_pattern)}"].append(row)
        if row.has_position:
            groups[f"position:{position_band(row.position)}"].append(row)
    return {key: summarize(value) for key, value in sorted(groups.items())}


def ctr_candidates(
    rows: list[Row],
    brand_pattern: re.Pattern[str] | None,
    min_impressions: float,
    min_group_size: int,
    limit: int,
) -> list[dict[str, Any]]:
    peer_groups: defaultdict[tuple[str, str], list[Row]] = defaultdict(list)
    for row in rows:
        if row.has_position and row.impressions >= 10:
            peer_groups[
                (position_band(row.position), brand_class(row.query, brand_pattern))
            ].append(row)
    medians = {
        key: statistics.median(item.ctr for item in values)
        for key, values in peer_groups.items()
        if len(values) >= min_group_size
    }
    candidates: list[dict[str, Any]] = []
    for row in rows:
        if not row.has_position or row.impressions < min_impressions:
            continue
        key = (position_band(row.position), brand_class(row.query, brand_pattern))
        median = medians.get(key)
        if median is None or median <= 0 or row.ctr >= median * 0.8:
            continue
        item = row_record(row)
        item.update(
            {
                "peer_position_band": key[0],
                "peer_query_class": key[1],
                "peer_rows": len(peer_groups[key]),
                "peer_median_ctr": round(median, 8),
                "ctr_gap_to_median": round(median - row.ctr, 8),
                "diagnostic_only": (
                    "Inspect SERP, intent, device/country, title/snippet, and "
                    "result features before proposing a test."
                ),
            }
        )
        candidates.append(item)
    candidates.sort(
        key=lambda item: (
            -(item["impressions"] * item["ctr_gap_to_median"]),
            item["position"] or 999,
        )
    )
    return candidates[:limit]


def near_opportunities(
    rows: list[Row], min_impressions: float, limit: int
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in rows:
        if (
            row.has_position
            and 4 <= row.position <= 20
            and row.impressions >= min_impressions
        ):
            item = row_record(row)
            proximity = max(0.0, (21.0 - row.position) / 17.0)
            item.update(
                {
                    "priority_heuristic": round(row.impressions * proximity, 4),
                    "heuristic_definition": (
                        "impressions × proximity within the 4-20 position band; "
                        "not a click forecast"
                    ),
                }
            )
            candidates.append(item)
    candidates.sort(
        key=lambda item: (-item["priority_heuristic"], -item["impressions"])
    )
    return candidates[:limit]


def overlap_candidates(
    rows: list[Row], min_impressions: float, limit: int
) -> list[dict[str, Any]]:
    by_query: defaultdict[str, list[Row]] = defaultdict(list)
    for row in rows:
        if row.query and row.page:
            by_query[row.query].append(row)
    candidates: list[dict[str, Any]] = []
    for query, values in by_query.items():
        pages = {row.page for row in values}
        total_impressions = sum(row.impressions for row in values)
        if len(pages) < 2 or total_impressions < min_impressions:
            continue
        ordered = sorted(values, key=lambda row: (-row.clicks, -row.impressions))
        top_impressions = max(row.impressions for row in values)
        candidates.append(
            {
                "query": query,
                "distinct_pages": len(pages),
                "total_clicks": round(sum(row.clicks for row in values), 4),
                "total_impressions": round(total_impressions, 4),
                "largest_page_impression_share": round(
                    top_impressions / total_impressions, 8
                )
                if total_impressions
                else 0.0,
                "pages": [row_record(row) for row in ordered],
                "classification": "overlap candidate, not proven cannibalization",
                "required_review": (
                    "Compare intent, page roles, time/device/country trends, "
                    "conversions, content, links, and canonicals."
                ),
            }
        )
    candidates.sort(
        key=lambda item: (-item["total_impressions"], -item["distinct_pages"])
    )
    return candidates[:limit]


def percent_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return (current - previous) / previous


def compare_periods(
    current: list[Row],
    previous: list[Row],
    dimensions: tuple[str, ...],
    min_impressions: float,
    limit: int,
) -> dict[str, Any]:
    current_map = {row.key(dimensions): row for row in current}
    previous_map = {row.key(dimensions): row for row in previous}
    records: list[dict[str, Any]] = []
    for key in sorted(set(current_map) | set(previous_map)):
        now = current_map.get(
            key, Row("", "", 0, 0, 0, 0, False)
        )
        before = previous_map.get(
            key, Row(now.query, now.page, 0, 0, 0, 0, False)
        )
        query = now.query or before.query
        page = now.page or before.page
        click_delta = now.clicks - before.clicks
        impression_delta = now.impressions - before.impressions
        position_delta = (
            now.position - before.position
            if now.has_position and before.has_position
            else None
        )
        records.append(
            {
                "query": query or None,
                "page": page or None,
                "current": row_record(now),
                "previous": row_record(before),
                "click_delta": round(click_delta, 4),
                "click_change": (
                    round(value, 8)
                    if (value := percent_change(now.clicks, before.clicks)) is not None
                    else None
                ),
                "impression_delta": round(impression_delta, 4),
                "impression_change": (
                    round(value, 8)
                    if (
                        value := percent_change(
                            now.impressions, before.impressions
                        )
                    )
                    is not None
                    else None
                ),
                "position_delta_positive_is_worse": (
                    round(position_delta, 4) if position_delta is not None else None
                ),
                "new_row": key not in previous_map,
                "lost_row": key not in current_map,
                "meets_volume_gate": max(
                    now.impressions, before.impressions
                )
                >= min_impressions,
            }
        )
    eligible = [item for item in records if item["meets_volume_gate"]]
    losses = sorted(eligible, key=lambda item: (item["click_delta"], item["impression_delta"]))
    winners = sorted(
        eligible,
        key=lambda item: (-item["click_delta"], -item["impression_delta"]),
    )
    return {
        "current_summary": summarize(current),
        "previous_summary": summarize(previous),
        "top_losses": losses[:limit],
        "top_winners": winners[:limit],
        "matched_or_changed_rows": len(records),
        "rows_meeting_volume_gate": len(eligible),
        "note": (
            "Percent changes are null when the previous value is zero. "
            "New/lost rows may reflect data truncation as well as real change."
        ),
    }


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


def escape_cell(value: Any) -> str:
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def format_percent(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.2f}%"


def markdown_report(analysis: dict[str, Any], limit: int) -> str:
    summary = analysis["summary"]
    lines = [
        "# Search Console export analysis",
        "",
        f"- Generated: {analysis['generated_at']}",
        f"- Dimensions: {', '.join(analysis['dimensions'])}",
        f"- Current rows: {summary['rows']}",
        "- Coverage warning: exported query/page rows can be truncated and omit "
        "anonymized queries; totals are only for loaded rows.",
        "",
        "## Loaded-row summary",
        "",
        "| Clicks | Impressions | CTR | Avg. position |",
        "| ---: | ---: | ---: | ---: |",
        f"| {summary['clicks']:.0f} | {summary['impressions']:.0f} | "
        f"{format_percent(summary['ctr'])} | "
        f"{summary['position'] if summary['position'] is not None else '—'} |",
        "",
    ]

    if analysis.get("comparison"):
        comparison = analysis["comparison"]
        previous = comparison["previous_summary"]
        lines.extend(
            [
                "## Period comparison",
                "",
                "| Period | Clicks | Impressions | CTR | Avg. position |",
                "| --- | ---: | ---: | ---: | ---: |",
                f"| Current | {summary['clicks']:.0f} | {summary['impressions']:.0f} | "
                f"{format_percent(summary['ctr'])} | {summary['position'] or '—'} |",
                f"| Previous | {previous['clicks']:.0f} | "
                f"{previous['impressions']:.0f} | {format_percent(previous['ctr'])} | "
                f"{previous['position'] or '—'} |",
                "",
                "### Top loaded-row losses",
                "",
                "| Query | Page | Click Δ | Impression Δ | Position Δ (+ worse) |",
                "| --- | --- | ---: | ---: | ---: |",
            ]
        )
        for item in comparison["top_losses"][:limit]:
            lines.append(
                f"| {escape_cell(item['query'])} | {escape_cell(item['page'])} | "
                f"{item['click_delta']:.0f} | {item['impression_delta']:.0f} | "
                f"{escape_cell(item['position_delta_positive_is_worse'])} |"
            )
        lines.append("")

    lines.extend(
        [
            "## CTR diagnostic candidates",
            "",
            "These rows fall materially below the within-export median for their "
            "position band and brand class. Inspect the live result before testing.",
            "",
            "| Query | Page | Impressions | Position | CTR | Peer median |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in analysis["ctr_candidates"][:limit]:
        lines.append(
            f"| {escape_cell(item['query'])} | {escape_cell(item['page'])} | "
            f"{item['impressions']:.0f} | {escape_cell(item['position'])} | "
            f"{format_percent(item['ctr'])} | "
            f"{format_percent(item['peer_median_ctr'])} |"
        )

    lines.extend(
        [
            "",
            "## Near-opportunity candidates",
            "",
            "| Query | Page | Impressions | Position | Clicks |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for item in analysis["near_opportunities"][:limit]:
        lines.append(
            f"| {escape_cell(item['query'])} | {escape_cell(item['page'])} | "
            f"{item['impressions']:.0f} | {escape_cell(item['position'])} | "
            f"{item['clicks']:.0f} |"
        )

    if analysis["overlap_candidates"]:
        lines.extend(
            [
                "",
                "## Query/page overlap candidates",
                "",
                "Multiple pages are not automatically cannibalization. Validate intent, "
                "time segments, conversions, content, links, and canonicals.",
                "",
                "| Query | Pages | Impressions | Largest-page share |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for item in analysis["overlap_candidates"][:limit]:
            lines.append(
                f"| {escape_cell(item['query'])} | {item['distinct_pages']} | "
                f"{item['total_impressions']:.0f} | "
                f"{format_percent(item['largest_page_impression_share'])} |"
            )

    lines.extend(
        [
            "",
            "## Required validation",
            "",
            "- Confirm matched date lengths, weekdays, timezone, search type, filters, and final-data state.",
            "- Segment by device, country, page type, query intent, and brand where exports allow.",
            "- Join to landing-page conversions and inspect current SERPs/pages.",
            "- Treat new/lost rows cautiously because Search Console omits some data.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--current", required=True, help="Current-period GSC CSV")
    parser.add_argument("--previous", help="Optional matched previous-period GSC CSV")
    parser.add_argument(
        "--brand-term",
        action="append",
        default=[],
        help="Literal brand/product term; repeat as needed",
    )
    parser.add_argument(
        "--brand-regex",
        help="Optional case-insensitive regex for additional brand-query matching",
    )
    parser.add_argument(
        "--min-impressions",
        type=float,
        default=100,
        help="Minimum loaded-row impressions for candidate analyses",
    )
    parser.add_argument(
        "--min-peer-rows",
        type=int,
        default=5,
        help="Minimum rows needed for a within-export CTR peer median",
    )
    parser.add_argument(
        "--limit", type=int, default=50, help="Maximum rows per diagnostic section"
    )
    parser.add_argument("--output", default="-", help="JSON path, or - for stdout")
    parser.add_argument("--markdown", help="Optional Markdown summary path")
    parser.add_argument("--version", action="version", version=VERSION)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.min_impressions < 0:
        raise ValueError("--min-impressions cannot be negative")
    if not 2 <= args.min_peer_rows <= 10_000:
        raise ValueError("--min-peer-rows must be between 2 and 10000")
    if not 1 <= args.limit <= 10_000:
        raise ValueError("--limit must be between 1 and 10000")
    if args.output == "-" and args.markdown == "-":
        raise ValueError("JSON and Markdown cannot both use stdout")


def run(args: argparse.Namespace) -> dict[str, Any]:
    current_export = load_export(Path(args.current))
    previous_export = load_export(Path(args.previous)) if args.previous else None
    if (
        previous_export
        and previous_export.dimensions != current_export.dimensions
    ):
        raise ValueError(
            "current and previous exports must use the same Query/Page dimensions"
        )
    dimensions = current_export.dimensions
    current = aggregate_rows(current_export.rows, dimensions)
    previous = (
        aggregate_rows(previous_export.rows, dimensions)
        if previous_export
        else None
    )
    brand_pattern = compile_brand_pattern(args.brand_term, args.brand_regex)
    analysis: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "tool": "analyze_gsc.py",
        "tool_version": VERSION,
        "generated_at": utc_now(),
        "inputs": {
            "current": {
                "path": str(current_export.path),
                "sha256": current_export.sha256,
                "rows_read": current_export.rows_read,
                "rows_usable": len(current_export.rows),
                "columns": current_export.columns,
            },
            "previous": (
                {
                    "path": str(previous_export.path),
                    "sha256": previous_export.sha256,
                    "rows_read": previous_export.rows_read,
                    "rows_usable": len(previous_export.rows),
                    "columns": previous_export.columns,
                }
                if previous_export
                else None
            ),
        },
        "dimensions": list(dimensions),
        "configuration": {
            "brand_terms": args.brand_term,
            "brand_regex_supplied": bool(args.brand_regex),
            "min_impressions": args.min_impressions,
            "min_peer_rows": args.min_peer_rows,
            "limit": args.limit,
        },
        "summary": summarize(current),
        "segments": segment_summary(current, brand_pattern),
        "ctr_candidates": ctr_candidates(
            current,
            brand_pattern,
            args.min_impressions,
            args.min_peer_rows,
            args.limit,
        ),
        "near_opportunities": near_opportunities(
            current, args.min_impressions, args.limit
        ),
        "overlap_candidates": overlap_candidates(
            current, args.min_impressions, args.limit
        )
        if dimensions == ("query", "page")
        else [],
        "comparison": (
            compare_periods(
                current,
                previous,
                dimensions,
                args.min_impressions,
                args.limit,
            )
            if previous is not None
            else None
        ),
        "limitations": [
            "Results cover loaded export rows, not guaranteed complete Search Console totals.",
            "Anonymized queries and some detailed rows may be omitted.",
            "Most page performance is assigned to canonical URLs.",
            "Average position is contextual and is not a stable rank.",
            "CTR peers use only this export and require live SERP validation.",
            "Overlap candidates are not proof of cannibalization.",
            "Date windows, search type, filters, device, country, and data state are not encoded in a generic CSV and must be documented separately.",
        ],
    }
    return analysis


def main() -> int:
    args = parse_args()
    try:
        validate_args(args)
        analysis = run(args)
        json_text = json.dumps(analysis, indent=2, ensure_ascii=False) + "\n"
        if args.output == "-":
            sys.stdout.write(json_text)
        else:
            write_atomic(Path(args.output), json_text)
            print(
                f"Wrote {args.output}: {analysis['summary']['rows']} aggregated rows",
                file=sys.stderr,
            )
        if args.markdown:
            report = markdown_report(analysis, args.limit)
            if args.markdown == "-":
                sys.stdout.write(report)
            else:
                write_atomic(Path(args.markdown), report)
                print(f"Wrote {args.markdown}", file=sys.stderr)
        return 0
    except (ValueError, OSError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
