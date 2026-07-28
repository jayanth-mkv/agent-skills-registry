#!/usr/bin/env python3
"""Compare two audit_site.py JSON snapshots and report deterministic changes.

The comparison identifies observations that appeared, disappeared, or changed.
It cannot determine whether a change was intended or caused search performance.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"
SEVERITY_ORDER = {
    "blocker": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "opportunity": 4,
}
PAGE_FIELDS = (
    "status",
    "fetch_error",
    "redirects",
    "title",
    "descriptions",
    "h1",
    "noindex_observed",
    "canonicals",
    "hreflang",
    "html_lang",
    "viewport",
    "meta_refresh",
    "schema_types",
    "json_ld_invalid",
    "word_count_approx",
    "content_fingerprint",
)
CONFIG_FIELDS = (
    "max_pages",
    "max_depth",
    "max_sitemaps",
    "max_sitemap_urls",
    "max_response_bytes",
    "user_agent",
    "include_subdomains",
    "include_query_urls",
    "sitemaps_enabled",
    "robots_respected",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_audit(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"audit file does not exist: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    if data.get("tool") != "audit_site.py":
        raise ValueError(f"{path} was not created by audit_site.py")
    if not isinstance(data.get("pages"), list) or not isinstance(
        data.get("findings"), list
    ):
        raise ValueError(f"{path} is missing pages or findings arrays")
    if not isinstance(data.get("target"), dict):
        raise ValueError(f"{path} is missing target metadata")
    return data


def normalized_host(audit: dict[str, Any]) -> str:
    root = audit.get("target", {}).get("effective_root", "")
    return (urlsplit(root).hostname or "").casefold()


def page_map(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for page in audit["pages"]:
        url = page.get("url")
        if isinstance(url, str) and url:
            mapped[url] = page
    return mapped


def finding_map(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for item in audit["findings"]:
        finding_id = item.get("id")
        if isinstance(finding_id, str) and finding_id:
            mapped[finding_id] = item
    return mapped


def value_for_display(value: Any, limit: int = 500) -> Any:
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "…"
    if isinstance(value, list) and len(value) > 20:
        return value[:20] + [f"… {len(value) - 20} more"]
    return value


def classify_field_change(field: str, before: Any, after: Any) -> str:
    if field == "status":
        before_bad = before is None or (isinstance(before, int) and before >= 400)
        after_bad = after is None or (isinstance(after, int) and after >= 400)
        if not before_bad and after_bad:
            return "potential-regression"
        if before_bad and not after_bad:
            return "potential-improvement"
    if field == "noindex_observed":
        if not before and after:
            return "requires-intent-review"
        if before and not after:
            return "requires-intent-review"
    if field == "json_ld_invalid":
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            if after > before:
                return "potential-regression"
            if after < before:
                return "potential-improvement"
    if field == "title":
        if before and not after:
            return "potential-regression"
        if not before and after:
            return "potential-improvement"
    return "changed"


def compare_pages(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changes: list[dict[str, Any]] = []
    for url in sorted(set(before) & set(after)):
        old = before[url]
        new = after[url]
        field_changes: list[dict[str, Any]] = []
        for field in PAGE_FIELDS:
            old_value = old.get(field)
            new_value = new.get(field)
            if old_value != new_value:
                field_changes.append(
                    {
                        "field": field,
                        "before": value_for_display(old_value),
                        "after": value_for_display(new_value),
                        "classification": classify_field_change(
                            field, old_value, new_value
                        ),
                    }
                )
        old_internal = sum(1 for item in old.get("links", []) if item.get("url"))
        new_internal = sum(1 for item in new.get("links", []) if item.get("url"))
        if old_internal != new_internal:
            field_changes.append(
                {
                    "field": "parsed_link_count",
                    "before": old_internal,
                    "after": new_internal,
                    "classification": "changed",
                }
            )
        if field_changes:
            changes.append({"url": url, "changes": field_changes})
    return added, removed, changes


def configuration_changes(
    before: dict[str, Any], after: dict[str, Any]
) -> list[dict[str, Any]]:
    old = before.get("configuration", {})
    new = after.get("configuration", {})
    return [
        {"field": field, "before": old.get(field), "after": new.get(field)}
        for field in CONFIG_FIELDS
        if old.get(field) != new.get(field)
    ]


def numeric_summary_delta(
    before: dict[str, Any], after: dict[str, Any]
) -> dict[str, dict[str, float | int]]:
    old = before.get("summary", {})
    new = after.get("summary", {})
    keys = sorted(set(old) & set(new))
    deltas: dict[str, dict[str, float | int]] = {}
    for key in keys:
        old_value = old[key]
        new_value = new[key]
        if (
            isinstance(old_value, (int, float))
            and not isinstance(old_value, bool)
            and isinstance(new_value, (int, float))
            and not isinstance(new_value, bool)
            and math.isfinite(float(old_value))
            and math.isfinite(float(new_value))
        ):
            deltas[key] = {
                "before": old_value,
                "after": new_value,
                "delta": new_value - old_value,
            }
    return deltas


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
    text = str(value if value is not None else "—")
    return text.replace("|", "\\|").replace("\n", " ")


def markdown_report(diff: dict[str, Any], limit: int) -> str:
    lines = [
        f"# Search visibility audit diff: {diff['target']['after']}",
        "",
        f"- Generated: {diff['generated_at']}",
        f"- Before: {diff['inputs']['before']['collected_at']}",
        f"- After: {diff['inputs']['after']['collected_at']}",
        f"- Comparable configuration: {'yes' if not diff['configuration_changes'] else 'no'}",
        "",
        "> A changed crawler observation is not automatically an SEO improvement or "
        "regression. Confirm intent, rendered output, indexed state, and outcomes.",
        "",
        "## Summary",
        "",
        "| Change | Count |",
        "| --- | ---: |",
        f"| New finding instances | {diff['summary']['new_findings']} |",
        f"| Resolved finding instances | {diff['summary']['resolved_findings']} |",
        f"| Added crawled URLs | {diff['summary']['added_pages']} |",
        f"| Removed crawled URLs | {diff['summary']['removed_pages']} |",
        f"| URLs with observed field changes | {diff['summary']['changed_pages']} |",
        "",
    ]
    if diff["configuration_changes"]:
        lines.extend(
            [
                "## Configuration differences",
                "",
                "Coverage changes may be caused by these settings:",
                "",
                "| Field | Before | After |",
                "| --- | --- | --- |",
            ]
        )
        for item in diff["configuration_changes"]:
            lines.append(
                f"| `{item['field']}` | {escape_cell(item['before'])} | "
                f"{escape_cell(item['after'])} |"
            )
        lines.append("")

    lines.extend(
        [
            "## New findings",
            "",
            "| Severity | Code | URL | Observation |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in diff["new_findings"][:limit]:
        lines.append(
            f"| {escape_cell(item.get('severity'))} | `{escape_cell(item.get('code'))}` | "
            f"{escape_cell(item.get('url'))} | {escape_cell(item.get('observation'))} |"
        )
    if len(diff["new_findings"]) > limit:
        lines.append(
            f"| … | … | … | {len(diff['new_findings']) - limit} more in JSON |"
        )

    lines.extend(
        [
            "",
            "## Resolved findings",
            "",
            "| Severity | Code | URL | Previous observation |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in diff["resolved_findings"][:limit]:
        lines.append(
            f"| {escape_cell(item.get('severity'))} | `{escape_cell(item.get('code'))}` | "
            f"{escape_cell(item.get('url'))} | {escape_cell(item.get('observation'))} |"
        )
    if len(diff["resolved_findings"]) > limit:
        lines.append(
            f"| … | … | … | {len(diff['resolved_findings']) - limit} more in JSON |"
        )

    lines.extend(["", "## Changed pages", ""])
    for page in diff["page_changes"][:limit]:
        lines.extend(
            [
                f"### `{page['url']}`",
                "",
                "| Field | Before | After | Classification |",
                "| --- | --- | --- | --- |",
            ]
        )
        for change in page["changes"]:
            lines.append(
                f"| `{change['field']}` | {escape_cell(change['before'])} | "
                f"{escape_cell(change['after'])} | {change['classification']} |"
            )
        lines.append("")
    if len(diff["page_changes"]) > limit:
        lines.append(
            f"_Markdown omits {len(diff['page_changes']) - limit} additional changed "
            "pages; use JSON for the complete diff._"
        )
        lines.append("")

    lines.extend(
        [
            "## Validation",
            "",
            "- Confirm that both crawls used the same scope, limits, robots policy, and environment.",
            "- Review added/removed URLs against crawl-cap and sitemap-order effects.",
            "- Validate high-risk changes in raw HTML, rendered output, headers, and production routes.",
            "- Check indexed-version processing and business outcomes on their own timelines.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("before", help="Earlier audit_site.py JSON")
    parser.add_argument("after", help="Later audit_site.py JSON")
    parser.add_argument(
        "--allow-different-target",
        action="store_true",
        help="Compare different hosts; normally indicates a mistake",
    )
    parser.add_argument(
        "--require-same-config",
        action="store_true",
        help="Fail when discovery-critical crawler settings differ",
    )
    parser.add_argument(
        "--limit", type=int, default=200, help="Maximum items per Markdown section"
    )
    parser.add_argument("--output", default="-", help="JSON path, or - for stdout")
    parser.add_argument("--markdown", help="Optional Markdown summary path")
    parser.add_argument("--version", action="version", version=VERSION)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not 1 <= args.limit <= 100_000:
        raise ValueError("--limit must be between 1 and 100000")
    if args.output == "-" and args.markdown == "-":
        raise ValueError("JSON and Markdown cannot both use stdout")


def run(args: argparse.Namespace) -> dict[str, Any]:
    before_path = Path(args.before)
    after_path = Path(args.after)
    before = load_audit(before_path)
    after = load_audit(after_path)
    before_host = normalized_host(before)
    after_host = normalized_host(after)
    if not args.allow_different_target and before_host != after_host:
        raise ValueError(
            f"audit targets differ ({before_host!r} vs {after_host!r}); "
            "use --allow-different-target only when intentional"
        )

    config_changes = configuration_changes(before, after)
    if args.require_same_config and config_changes:
        fields = ", ".join(item["field"] for item in config_changes)
        raise ValueError(f"discovery-critical configuration differs: {fields}")

    old_pages = page_map(before)
    new_pages = page_map(after)
    added_pages, removed_pages, page_changes = compare_pages(old_pages, new_pages)

    old_findings = finding_map(before)
    new_findings = finding_map(after)
    new_items = [
        new_findings[key] for key in sorted(set(new_findings) - set(old_findings))
    ]
    resolved_items = [
        old_findings[key] for key in sorted(set(old_findings) - set(new_findings))
    ]
    sort_key = lambda item: (
        SEVERITY_ORDER.get(item.get("severity", ""), 9),
        item.get("code", ""),
        item.get("url", ""),
    )
    new_items.sort(key=sort_key)
    resolved_items.sort(key=sort_key)

    page_change_classes = Counter(
        change["classification"]
        for page in page_changes
        for change in page["changes"]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": "compare_site_audits.py",
        "tool_version": VERSION,
        "generated_at": utc_now(),
        "inputs": {
            "before": {
                "path": str(before_path),
                "tool_version": before.get("tool_version"),
                "schema_version": before.get("schema_version"),
                "collected_at": before.get("completed_at"),
            },
            "after": {
                "path": str(after_path),
                "tool_version": after.get("tool_version"),
                "schema_version": after.get("schema_version"),
                "collected_at": after.get("completed_at"),
            },
        },
        "target": {
            "before": before.get("target", {}).get("effective_root"),
            "after": after.get("target", {}).get("effective_root"),
        },
        "configuration_changes": config_changes,
        "summary_deltas": numeric_summary_delta(before, after),
        "summary": {
            "new_findings": len(new_items),
            "resolved_findings": len(resolved_items),
            "added_pages": len(added_pages),
            "removed_pages": len(removed_pages),
            "changed_pages": len(page_changes),
            "page_change_classifications": dict(sorted(page_change_classes.items())),
        },
        "new_findings": new_items,
        "resolved_findings": resolved_items,
        "added_pages": added_pages,
        "removed_pages": removed_pages,
        "page_changes": page_changes,
        "limitations": [
            "Crawler observations depend on scope, ordering, limits, network state, and raw HTML.",
            "Added or removed pages can result from crawl-cap or sitemap-order differences.",
            "Finding disappearance is not proof of search-engine processing or business impact.",
            "Content fingerprints include approximate visible template text.",
            "Intentional noindex, canonical, redirect, and content changes require human review.",
        ],
    }


def main() -> int:
    args = parse_args()
    try:
        validate_args(args)
        diff = run(args)
        json_text = json.dumps(diff, indent=2, ensure_ascii=False) + "\n"
        if args.output == "-":
            sys.stdout.write(json_text)
        else:
            write_atomic(Path(args.output), json_text)
            print(
                f"Wrote {args.output}: {diff['summary']['changed_pages']} changed pages, "
                f"{diff['summary']['new_findings']} new findings",
                file=sys.stderr,
            )
        if args.markdown:
            report = markdown_report(diff, args.limit)
            if args.markdown == "-":
                sys.stdout.write(report)
            else:
                write_atomic(Path(args.markdown), report)
                print(f"Wrote {args.markdown}", file=sys.stderr)
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
