#!/usr/bin/env python3
"""Assert that skills CLI --list output contains every repository skill."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
FOUND = re.compile(r"\bFound\s+(\d+)\s+skills?\b", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Captured output from skills add . --list")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    if not args.output.is_file():
        print(f"ERROR: discovery output not found: {args.output}", file=sys.stderr)
        return 2

    expected = sorted(path.parent.name for path in (root / "skills").glob("*/SKILL.md"))
    if not expected:
        print("ERROR: repository contains no skills to discover", file=sys.stderr)
        return 1

    text = ANSI.sub("", args.output.read_text(encoding="utf-8", errors="replace"))
    errors: list[str] = []

    found = FOUND.search(text)
    if found is None:
        errors.append("skills CLI output did not report a discovered skill count")
    elif int(found.group(1)) != len(expected):
        errors.append(
            f"skills CLI reported {found.group(1)} skill(s), but repository contains {len(expected)}"
        )

    for name in expected:
        if not re.search(rf"(?<![a-z0-9-]){re.escape(name)}(?![a-z0-9-])", text):
            errors.append(f"skills CLI did not list: {name}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"CLI discovered all {len(expected)} skill(s): {', '.join(expected)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
