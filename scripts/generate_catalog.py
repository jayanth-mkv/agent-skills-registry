#!/usr/bin/env python3
"""Generate the README skill catalog from SKILL.md frontmatter."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
START = "<!-- catalog:start -->"
END = "<!-- catalog:end -->"
REPOSITORY = "jayanth-mkv/agent-skills-registry"


def metadata(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path} has no frontmatter")
    end = lines[1:].index("---") + 1
    result: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip("\"'")
    return result


def catalog() -> str:
    rows = [
        "| Skill | What it does | Install |",
        "| --- | --- | --- |",
    ]
    for skill_file in sorted((ROOT / "skills").glob("*/SKILL.md")):
        item = metadata(skill_file)
        name = item["name"]
        summary = item["description"].split(" Use when", 1)[0].rstrip(".").replace("|", "\\|")
        command = f"npx skills@latest add {REPOSITORY} --skill {name}"
        rows.append(
            f"| [`{name}`](skills/{name}/SKILL.md) | {summary}. | `{command}` |"
        )
    return START + "\n" + "\n".join(rows) + "\n" + END


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if README catalog is stale")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not README.is_file():
        print("ERROR: README.md does not exist", file=sys.stderr)
        return 1

    text = README.read_text(encoding="utf-8")
    replacement = catalog()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        print("ERROR: README catalog markers are missing", file=sys.stderr)
        return 1

    updated = pattern.sub(replacement, text)
    if args.check:
        if updated != text:
            print("ERROR: README skill catalog is stale; run python scripts/generate_catalog.py")
            return 1
        print("README skill catalog is current")
        return 0

    README.write_text(updated, encoding="utf-8")
    print("Updated README skill catalog")
    return 0


if __name__ == "__main__":
    sys.exit(main())
