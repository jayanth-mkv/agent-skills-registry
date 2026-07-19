#!/usr/bin/env python3
"""Validate common README structure and local asset references."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

MARKDOWN_LINK = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)|(?<!!)\[([^\]]+)\]\(([^)]+)\)")
HTML_LINK = re.compile(r"<(?:img|a)\b[^>]*?\b(?:src|href)=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)
HTML_IMAGE = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)
ALT_ATTRIBUTE = re.compile(r"\balt=[\"']([^\"']*)[\"']", re.IGNORECASE)
FENCE = re.compile(r"^\s*(```|~~~)")
H1 = re.compile(r"^\s*#\s+\S|<h1\b", re.MULTILINE | re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("readme", nargs="?", default="README.md", type=Path)
    parser.add_argument("--repo-root", default=Path("."), type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def clean_target(raw: str) -> str | None:
    target = raw.strip().strip("<>")
    if not target or target.startswith(("#", "mailto:", "data:")):
        return None
    parsed = urlsplit(target)
    if parsed.scheme in {"http", "https"} or target.startswith("//"):
        return None
    return unquote(parsed.path)


def validate(readme: Path, repo_root: Path) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    root = repo_root.resolve()
    path = readme if readme.is_absolute() else root / readme

    if not path.is_file():
        return {"errors": [f"README not found: {path}"], "warnings": []}

    text = path.read_text(encoding="utf-8")
    if not H1.search(text):
        errors.append("README must contain a level-one heading.")

    fences = [match.group(1) for line in text.splitlines() if (match := FENCE.match(line))]
    if len(fences) % 2:
        errors.append("README contains an unbalanced fenced code block.")

    targets: list[str] = []
    for match in MARKDOWN_LINK.finditer(text):
        targets.append(match.group(2) or match.group(4))
    targets.extend(HTML_LINK.findall(text))

    for raw in targets:
        local = clean_target(raw)
        if local is None:
            continue
        candidate = (path.parent / local).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            errors.append(f"Local link escapes repository root: {raw}")
            continue
        if not candidate.exists():
            errors.append(f"Missing local target: {raw}")

    for attributes in HTML_IMAGE.findall(text):
        alt = ALT_ATTRIBUTE.search(attributes)
        if alt is None or not alt.group(1).strip():
            warnings.append("HTML image is missing meaningful alt text.")

    if '<div align="center">' not in text and '<p align="center">' not in text:
        warnings.append("README has no centered identity block.")

    return {"errors": sorted(set(errors)), "warnings": sorted(set(warnings))}


def main() -> int:
    args = parse_args()
    result = validate(args.readme, args.repo_root)
    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        for error in result["errors"]:
            print(f"ERROR: {error}")
        for warning in result["warnings"]:
            print(f"WARN: {warning}")
        print(f"{len(result['errors'])} error(s), {len(result['warnings'])} warning(s)")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
