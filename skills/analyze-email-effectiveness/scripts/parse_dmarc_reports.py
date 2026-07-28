#!/usr/bin/env python3
"""Safely summarize RFC 9990 and legacy DMARC aggregate XML reports."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree

DEFAULT_MAX_INPUT_BYTES = 25 * 1024 * 1024
DEFAULT_MAX_EXPANDED_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_MEMBERS = 100
DMARC_REPORT_SUFFIXES = (".xml", ".xml.gz", ".gz", ".zip")


class DmarcReportError(ValueError):
    """Raised for unsafe, malformed, or unsupported report input."""


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def direct_child(element: ElementTree.Element, name: str) -> ElementTree.Element | None:
    return next(
        (child for child in element if local_name(child.tag) == name),
        None,
    )


def direct_children(element: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [child for child in element if local_name(child.tag) == name]


def child_text(
    element: ElementTree.Element | None,
    name: str,
    *,
    required: bool = False,
) -> str | None:
    child = direct_child(element, name) if element is not None else None
    value = (child.text or "").strip() if child is not None else ""
    if required and not value:
        raise DmarcReportError(f"required XML element {name!r} is missing or empty")
    return value or None


def parse_nonnegative_integer(value: str | None, label: str) -> int:
    try:
        parsed = int(value or "")
    except ValueError as exc:
        raise DmarcReportError(f"{label} must be an integer") from exc
    if parsed < 0:
        raise DmarcReportError(f"{label} cannot be negative")
    return parsed


def timestamp_text(value: int | None) -> str | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    except (OSError, OverflowError, ValueError):
        return None


def reject_unsafe_xml(raw: bytes) -> None:
    lowered = raw.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise DmarcReportError("XML DTD/entity declarations are not accepted")


def bounded_gzip_decompress(raw: bytes, max_expanded_bytes: int) -> bytes:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            expanded = stream.read(max_expanded_bytes + 1)
    except (OSError, EOFError) as exc:
        raise DmarcReportError(f"invalid gzip payload: {exc}") from exc
    if len(expanded) > max_expanded_bytes:
        raise DmarcReportError(
            f"expanded gzip payload exceeds limit ({max_expanded_bytes} bytes)"
        )
    return expanded


def payloads_from_file(
    path: Path,
    max_input_bytes: int,
    max_expanded_bytes: int,
    max_members: int,
) -> list[tuple[str, bytes]]:
    try:
        if not path.is_file():
            raise DmarcReportError(f"input is not a file: {path}")
        size = path.stat().st_size
        if size > max_input_bytes:
            raise DmarcReportError(
                f"input exceeds --max-input-bytes ({max_input_bytes}): {path}"
            )
        raw = path.read_bytes()
    except OSError as exc:
        raise DmarcReportError(f"cannot read {path}: {exc}") from exc

    if zipfile.is_zipfile(io.BytesIO(raw)):
        payloads: list[tuple[str, bytes]] = []
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                members = [member for member in archive.infolist() if not member.is_dir()]
                if len(members) > max_members:
                    raise DmarcReportError(
                        f"zip contains more than {max_members} file members"
                    )
                total_expanded = 0
                for member in members:
                    if member.flag_bits & 0x1:
                        raise DmarcReportError(
                            f"encrypted zip member is unsupported: {member.filename}"
                        )
                    if member.file_size > max_expanded_bytes:
                        raise DmarcReportError(
                            f"zip member exceeds expanded limit: {member.filename}"
                        )
                    with archive.open(member) as stream:
                        member_raw = stream.read(member.file_size + 1)
                    if len(member_raw) > member.file_size:
                        raise DmarcReportError(
                            f"zip member expanded beyond declared size: {member.filename}"
                        )
                    if member_raw[:2] == b"\x1f\x8b" or member.filename.casefold().endswith(".gz"):
                        remaining = max_expanded_bytes - total_expanded
                        if remaining <= 0:
                            raise DmarcReportError(
                                "combined zip expansion exceeds --max-expanded-bytes"
                            )
                        member_raw = bounded_gzip_decompress(
                            member_raw,
                            remaining,
                        )
                    total_expanded += len(member_raw)
                    if total_expanded > max_expanded_bytes:
                        raise DmarcReportError(
                            "combined zip expansion exceeds --max-expanded-bytes"
                        )
                    payloads.append((f"{path.name}:{member.filename}", member_raw))
        except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
            raise DmarcReportError(f"invalid zip payload: {exc}") from exc
        if not payloads:
            raise DmarcReportError(f"zip contains no file members: {path}")
        return payloads

    if raw[:2] == b"\x1f\x8b" or path.name.casefold().endswith(".gz"):
        return [(path.name, bounded_gzip_decompress(raw, max_expanded_bytes))]
    if len(raw) > max_expanded_bytes:
        raise DmarcReportError(
            f"XML input exceeds --max-expanded-bytes ({max_expanded_bytes})"
        )
    return [(path.name, raw)]


def discover_input_files(values: Iterable[str], max_members: int) -> list[Path]:
    paths: list[Path] = []
    for value in values:
        path = Path(value)
        if path.is_dir():
            matches = sorted(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file()
                and candidate.name.casefold().endswith(DMARC_REPORT_SUFFIXES)
            )
            paths.extend(matches)
        else:
            paths.append(path)
    unique = list(dict.fromkeys(path.resolve() for path in paths))
    if len(unique) > max_members:
        raise DmarcReportError(
            f"input expansion found more than {max_members} files"
        )
    if not unique:
        raise DmarcReportError("no DMARC report files were found")
    return unique


def parse_dmarc_report_xml(raw: bytes, source: str) -> dict[str, Any]:
    reject_unsafe_xml(raw)
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        raise DmarcReportError(f"malformed XML in {source}: {exc}") from exc
    if local_name(root.tag) != "feedback":
        raise DmarcReportError(f"XML root in {source} is not feedback")

    namespace = root.tag[1:].split("}", 1)[0] if root.tag.startswith("{") else None
    metadata = direct_child(root, "report_metadata")
    policy_published = direct_child(root, "policy_published")
    if metadata is None or policy_published is None:
        raise DmarcReportError(
            f"{source} lacks report_metadata or policy_published"
        )

    date_range = direct_child(metadata, "date_range")
    begin = (
        parse_nonnegative_integer(child_text(date_range, "begin", required=True), "date_range begin")
        if date_range is not None
        else None
    )
    end = (
        parse_nonnegative_integer(child_text(date_range, "end", required=True), "date_range end")
        if date_range is not None
        else None
    )
    if begin is not None and end is not None and end < begin:
        raise DmarcReportError(f"{source} date_range end precedes begin")

    report_metadata = {
        "org_name": child_text(metadata, "org_name", required=True),
        "email": child_text(metadata, "email", required=True),
        "extra_contact_info": child_text(metadata, "extra_contact_info"),
        "report_id": child_text(metadata, "report_id", required=True),
        "begin": begin,
        "end": end,
        "begin_utc": timestamp_text(begin),
        "end_utc": timestamp_text(end),
        "generator": child_text(metadata, "generator"),
        "errors": [
            (item.text or "").strip()
            for item in direct_children(metadata, "error")
            if (item.text or "").strip()
        ],
    }
    published = {
        name: child_text(policy_published, name)
        for name in (
            "domain",
            "discovery_method",
            "p",
            "sp",
            "np",
            "fo",
            "adkim",
            "aspf",
            "testing",
            "pct",
        )
        if child_text(policy_published, name) is not None
    }
    if "domain" not in published:
        raise DmarcReportError(f"{source} policy_published lacks domain")

    records: list[dict[str, Any]] = []
    for record_element in direct_children(root, "record"):
        row = direct_child(record_element, "row")
        identifiers = direct_child(record_element, "identifiers")
        auth_results = direct_child(record_element, "auth_results")
        if row is None or identifiers is None or auth_results is None:
            raise DmarcReportError(
                f"{source} contains a record without row, identifiers, or auth_results"
            )
        evaluated = direct_child(row, "policy_evaluated")
        if evaluated is None:
            raise DmarcReportError(
                f"{source} contains a row without policy_evaluated"
            )
        count = parse_nonnegative_integer(
            child_text(row, "count", required=True),
            "record count",
        )
        if count == 0:
            raise DmarcReportError(f"{source} contains a zero-count record")
        source_ip = child_text(row, "source_ip", required=True)
        disposition = child_text(evaluated, "disposition", required=True)
        dkim_aligned = child_text(evaluated, "dkim", required=True)
        spf_aligned = child_text(evaluated, "spf", required=True)
        reasons = []
        for reason_element in direct_children(evaluated, "reason"):
            reasons.append(
                {
                    "type": child_text(reason_element, "type", required=True),
                    "comment": child_text(reason_element, "comment"),
                }
            )

        dkim_results = []
        for item in direct_children(auth_results, "dkim"):
            dkim_results.append(
                {
                    "domain": child_text(item, "domain", required=True),
                    "selector": child_text(item, "selector"),
                    "result": child_text(item, "result", required=True),
                    "human_result": child_text(item, "human_result"),
                }
            )
        spf_results = []
        for item in direct_children(auth_results, "spf"):
            spf_results.append(
                {
                    "domain": child_text(item, "domain", required=True),
                    "scope": child_text(item, "scope"),
                    "result": child_text(item, "result", required=True),
                    "human_result": child_text(item, "human_result"),
                }
            )
        records.append(
            {
                "source_ip": source_ip,
                "count": count,
                "policy_evaluated": {
                    "disposition": disposition.casefold(),
                    "dkim": dkim_aligned.casefold(),
                    "spf": spf_aligned.casefold(),
                    "reasons": reasons,
                },
                "identifiers": {
                    "header_from": child_text(
                        identifiers,
                        "header_from",
                        required=True,
                    ),
                    "envelope_from": child_text(identifiers, "envelope_from"),
                    "envelope_to": child_text(identifiers, "envelope_to"),
                },
                "auth_results": {
                    "dkim": dkim_results,
                    "spf": spf_results,
                },
            }
        )
    if not records:
        raise DmarcReportError(f"{source} contains no record elements")

    return {
        "source": source,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "namespace": namespace,
        "report_version": child_text(root, "version"),
        "metadata": report_metadata,
        "policy_published": published,
        "records": records,
    }


def aggregate_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    dispositions: Counter[str] = Counter()
    header_from_domains: Counter[str] = Counter()
    source_summary: dict[str, dict[str, int]] = defaultdict(
        lambda: {"messages": 0, "aligned_pass": 0, "aligned_fail": 0}
    )
    dkim_auth_results: Counter[str] = Counter()
    spf_auth_results: Counter[str] = Counter()
    total_messages = 0
    aligned_pass = 0
    dkim_aligned_pass = 0
    spf_aligned_pass = 0
    failure_rows: list[dict[str, Any]] = []

    for report in reports:
        for record in report["records"]:
            count = record["count"]
            evaluated = record["policy_evaluated"]
            row_pass = evaluated["dkim"] == "pass" or evaluated["spf"] == "pass"
            total_messages += count
            aligned_pass += count if row_pass else 0
            dkim_aligned_pass += count if evaluated["dkim"] == "pass" else 0
            spf_aligned_pass += count if evaluated["spf"] == "pass" else 0
            dispositions[evaluated["disposition"]] += count
            header_from_domains[record["identifiers"]["header_from"]] += count
            source_item = source_summary[record["source_ip"]]
            source_item["messages"] += count
            source_item["aligned_pass" if row_pass else "aligned_fail"] += count
            for item in record["auth_results"]["dkim"]:
                key = f"{item['domain']}|{item.get('selector') or '-'}|{item['result']}"
                dkim_auth_results[key] += count
            for item in record["auth_results"]["spf"]:
                key = f"{item['domain']}|{item['result']}"
                spf_auth_results[key] += count
            if not row_pass:
                failure_rows.append(
                    {
                        "source": report["source"],
                        "source_ip": record["source_ip"],
                        "count": count,
                        "header_from": record["identifiers"]["header_from"],
                        "envelope_from": record["identifiers"]["envelope_from"],
                        "disposition": evaluated["disposition"],
                        "dkim_aligned": evaluated["dkim"],
                        "spf_aligned": evaluated["spf"],
                        "reasons": evaluated["reasons"],
                        "dkim_auth_results": record["auth_results"]["dkim"],
                        "spf_auth_results": record["auth_results"]["spf"],
                    }
                )

    aligned_fail = total_messages - aligned_pass
    return {
        "messages": {
            "total": total_messages,
            "aligned_pass": aligned_pass,
            "aligned_fail": aligned_fail,
            "aligned_pass_rate": (
                aligned_pass / total_messages if total_messages else None
            ),
            "dkim_aligned_pass": dkim_aligned_pass,
            "dkim_aligned_pass_rate": (
                dkim_aligned_pass / total_messages if total_messages else None
            ),
            "spf_aligned_pass": spf_aligned_pass,
            "spf_aligned_pass_rate": (
                spf_aligned_pass / total_messages if total_messages else None
            ),
        },
        "dispositions": dict(dispositions.most_common()),
        "header_from_domains": dict(header_from_domains.most_common()),
        "source_ips": [
            {"source_ip": source_ip, **counts}
            for source_ip, counts in sorted(
                source_summary.items(),
                key=lambda item: (-item[1]["messages"], item[0]),
            )
        ],
        "dkim_authentication_rows": dict(dkim_auth_results.most_common()),
        "spf_authentication_rows": dict(spf_auth_results.most_common()),
        "failure_rows": sorted(
            failure_rows,
            key=lambda item: (-item["count"], item["source_ip"]),
        ),
    }


def analyze_paths(
    values: Iterable[str],
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
    max_expanded_bytes: int = DEFAULT_MAX_EXPANDED_BYTES,
    max_members: int = DEFAULT_MAX_MEMBERS,
) -> dict[str, Any]:
    if min(max_input_bytes, max_expanded_bytes, max_members) <= 0:
        raise DmarcReportError("all size/member limits must be positive")
    paths = discover_input_files(values, max_members)
    reports: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    duplicates: list[dict[str, str]] = []
    seen_report_ids: dict[tuple[Any, ...], str] = {}

    payload_count = 0
    for path in paths:
        try:
            payloads = payloads_from_file(
                path,
                max_input_bytes,
                max_expanded_bytes,
                max_members,
            )
        except DmarcReportError as exc:
            errors.append({"source": str(path), "error": str(exc)})
            continue
        payload_count += len(payloads)
        if payload_count > max_members:
            raise DmarcReportError(
                f"archive expansion produced more than {max_members} report payloads"
            )
        for source, payload in payloads:
            try:
                report = parse_dmarc_report_xml(payload, source)
            except DmarcReportError as exc:
                errors.append({"source": source, "error": str(exc)})
                continue
            metadata = report["metadata"]
            identity = (
                metadata["org_name"],
                metadata["report_id"],
                metadata["begin"],
                metadata["end"],
            )
            if identity in seen_report_ids:
                duplicates.append(
                    {
                        "source": source,
                        "duplicate_of": seen_report_ids[identity],
                        "report_id": str(metadata["report_id"]),
                    }
                )
                continue
            seen_report_ids[identity] = source
            reports.append(report)

    if not reports:
        raise DmarcReportError(
            "no valid, unique DMARC aggregate reports were parsed"
            + (f"; first error: {errors[0]['error']}" if errors else "")
        )
    namespaces = Counter(report["namespace"] or "none" for report in reports)
    return {
        "schema_version": "1.0",
        "analysis_type": "dmarc_aggregate_reports",
        "inputs": {
            "files": len(paths),
            "payloads": payload_count,
            "valid_unique_reports": len(reports),
            "invalid_payloads": len(errors),
            "duplicates_skipped": len(duplicates),
            "limits": {
                "max_input_bytes": max_input_bytes,
                "max_expanded_bytes": max_expanded_bytes,
                "max_members": max_members,
            },
        },
        "namespaces": dict(namespaces),
        "reports": [
            {
                "source": report["source"],
                "sha256": report["sha256"],
                "namespace": report["namespace"],
                "report_version": report["report_version"],
                "metadata": report["metadata"],
                "policy_published": report["policy_published"],
                "record_count": len(report["records"]),
            }
            for report in reports
        ],
        "aggregate": aggregate_reports(reports),
        "invalid": errors,
        "duplicates": duplicates,
        "limitations": [
            "Aggregate reports describe what participating receivers observed; they are not a complete inventory of all sent mail.",
            "A source IP or domain is not classified as authorized or malicious without an independently maintained sender inventory.",
            "Rows can contain multiple authentication results; weighted authentication-row counts can therefore exceed message totals.",
            "Legacy and RFC 9990 report schemas are parsed namespace-agnostically, but this helper does not perform full XSD validation.",
            "Disposition reflects receiver processing and local overrides, not a direct inbox-versus-spam measurement.",
        ],
    }


def percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.2f}%"


def render_text(report: dict[str, Any]) -> str:
    inputs = report["inputs"]
    messages = report["aggregate"]["messages"]
    lines = [
        "DMARC aggregate report analysis",
        (
            f"Reports: {inputs['valid_unique_reports']} valid unique; "
            f"{inputs['duplicates_skipped']} duplicate(s); "
            f"{inputs['invalid_payloads']} invalid payload(s)"
        ),
        (
            f"Messages represented: {messages['total']}; "
            f"aligned pass {messages['aligned_pass']} ({percent(messages['aligned_pass_rate'])}); "
            f"aligned fail {messages['aligned_fail']}"
        ),
        "Largest failing rows:",
    ]
    for row in report["aggregate"]["failure_rows"][:10]:
        lines.append(
            f"- {row['source_ip']}: {row['count']} message(s), "
            f"Header From={row['header_from']}, disposition={row['disposition']}, "
            f"DKIM={row['dkim_aligned']}, SPF={row['spf_aligned']}"
        )
    if not report["aggregate"]["failure_rows"]:
        lines.append("- None in the supplied reports.")
    lines.append("Limits:")
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="+",
        help="XML, gzip, zip, or directories containing DMARC aggregate reports.",
    )
    parser.add_argument(
        "--max-input-bytes",
        type=int,
        default=DEFAULT_MAX_INPUT_BYTES,
    )
    parser.add_argument(
        "--max-expanded-bytes",
        type=int,
        default=DEFAULT_MAX_EXPANDED_BYTES,
    )
    parser.add_argument(
        "--max-members",
        type=int,
        default=DEFAULT_MAX_MEMBERS,
        help="Maximum discovered files and expanded archive members.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = analyze_paths(
            args.inputs,
            args.max_input_bytes,
            args.max_expanded_bytes,
            args.max_members,
        )
    except DmarcReportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
