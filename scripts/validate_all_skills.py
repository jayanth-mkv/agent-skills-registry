#!/usr/bin/env python3
"""Validate every skill, catalog entry, badge, and discovery-critical invariant."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
RESOURCE_REFERENCE = re.compile(r"`((?:scripts|references|assets)/[^`\n]+)`")
ICON_REFERENCE = re.compile(r"icon_(?:small|large):\s*[\"']([^\"']+)[\"']")
ALLOWED_FRONTMATTER = {"name", "description"}
SKILLS_SCHEMA = "https://skills.sh/schemas/skills.sh.schema.json"
SKILLS_BADGE_IMAGE = "https://skills.sh/b/jayanth-mkv/agent-skills-registry"
SKILLS_BADGE_LINK = "https://skills.sh/jayanth-mkv/agent-skills-registry"


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter delimiter")
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError("missing closing frontmatter delimiter") from exc

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        if key in metadata:
            raise ValueError(f"duplicate frontmatter key: {key}")
        metadata[key] = value.strip().strip("\"'")

    body = "\n".join(lines[end + 1 :]).strip()
    return metadata, text, body


def referenced_paths(skill_file: Path, text: str) -> list[tuple[str, Path]]:
    targets: list[tuple[str, Path]] = []
    for raw in MARKDOWN_LINK.findall(text):
        parsed = urlsplit(raw.strip().strip("<>"))
        if parsed.scheme or raw.startswith(("#", "//")):
            continue
        local = unquote(parsed.path)
        targets.append((raw, (skill_file.parent / local).resolve()))

    for raw in RESOURCE_REFERENCE.findall(text):
        targets.append((raw, (skill_file.parent / raw).resolve()))
    return targets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    return parser.parse_args()


def main() -> int:
    parse_args()
    errors: list[str] = []
    skills_root = SKILLS_DIR.resolve()

    if not SKILLS_DIR.is_dir():
        errors.append("skills/ directory is required")
        skill_files: list[Path] = []
    else:
        case_insensitive = sorted(
            path for path in SKILLS_DIR.rglob("*") if path.is_file() and path.name.casefold() == "skill.md"
        )
        for path in case_insensitive:
            rel_path = path.relative_to(ROOT)
            if path.name != "SKILL.md":
                errors.append(f"{rel_path}: filename must use exact casing SKILL.md")
            if path.parent.parent.resolve() != skills_root:
                errors.append(f"{rel_path}: distributable skills must be direct children of skills/")

        skill_files = sorted(
            path
            for path in case_insensitive
            if path.name == "SKILL.md" and path.parent.parent.resolve() == skills_root
        )

        for child in SKILLS_DIR.iterdir():
            if child.is_dir() and not (child / "SKILL.md").is_file():
                errors.append(f"{child.relative_to(ROOT)}: top-level skill directory is missing SKILL.md")
            elif child.is_file():
                errors.append(f"{child.relative_to(ROOT)}: files are not allowed directly under skills/")

    if not skill_files:
        errors.append("No discoverable skills found under skills/*/SKILL.md.")

    names: set[str] = set()
    for skill_file in skill_files:
        skill_dir = skill_file.parent
        rel = skill_dir.relative_to(ROOT)
        try:
            metadata, text, body = parse_frontmatter(skill_file)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{rel}/SKILL.md: {exc}")
            continue

        unexpected = set(metadata) - ALLOWED_FRONTMATTER
        missing = ALLOWED_FRONTMATTER - set(metadata)
        if unexpected:
            errors.append(f"{rel}/SKILL.md: unsupported frontmatter keys: {sorted(unexpected)}")
        if missing:
            errors.append(f"{rel}/SKILL.md: missing frontmatter keys: {sorted(missing)}")

        name = metadata.get("name", "")
        description = metadata.get("description", "")

        if name in names:
            errors.append(f"{rel}: duplicate skill name: {name}")
        elif name:
            names.add(name)

        if name != skill_dir.name:
            errors.append(f"{rel}: folder and frontmatter name must match")
        if len(name) > 64 or not NAME_PATTERN.fullmatch(name):
            errors.append(f"{rel}: name must be lowercase kebab-case and at most 64 characters")
        if not description or "todo" in description.casefold():
            errors.append(f"{rel}: description must be complete")
        if len(description) > 1024:
            errors.append(f"{rel}: description exceeds the 1024-character specification limit")
        if "use when" not in description.casefold():
            errors.append(f"{rel}: description must include a clear 'Use when' trigger")
        if not body:
            errors.append(f"{rel}/SKILL.md: instruction body must not be empty")
        if len(text.splitlines()) > 500:
            errors.append(f"{rel}/SKILL.md: keep the main skill below 500 lines")
        if "todo" in text.casefold():
            errors.append(f"{rel}/SKILL.md: unresolved TODO found")

        if not (skill_dir / "LICENSE.txt").is_file():
            errors.append(f"{rel}: LICENSE.txt is required")

        agent_yaml = skill_dir / "agents" / "openai.yaml"
        if not agent_yaml.is_file():
            errors.append(f"{rel}: agents/openai.yaml is required")
        else:
            yaml_text = agent_yaml.read_text(encoding="utf-8")
            for key in ("display_name:", "short_description:", "default_prompt:"):
                if key not in yaml_text:
                    errors.append(f"{rel}/agents/openai.yaml: missing {key.rstrip(':')}")
            if ("$" + name) not in yaml_text:
                errors.append(f"{rel}/agents/openai.yaml: default prompt must include $" + name)
            for icon in ICON_REFERENCE.findall(yaml_text):
                icon_path = (skill_dir / icon).resolve()
                try:
                    icon_path.relative_to(skill_dir.resolve())
                except ValueError:
                    errors.append(f"{rel}/agents/openai.yaml: icon path escapes skill directory: {icon}")
                    continue
                if not icon_path.is_file():
                    errors.append(f"{rel}/agents/openai.yaml: missing icon: {icon}")

        readmes = [
            path for path in skill_dir.rglob("*") if path.is_file() and path.stem.casefold() == "readme"
        ]
        if readmes:
            errors.append(f"{rel}: skill directories must not contain README documents")

        for raw, target in referenced_paths(skill_file, text):
            try:
                target.relative_to(skill_dir.resolve())
            except ValueError:
                errors.append(f"{rel}/SKILL.md: local reference escapes skill directory: {raw}")
                continue
            if not target.exists():
                errors.append(f"{rel}/SKILL.md: missing local target: {raw}")

    catalog_path = ROOT / "skills.sh.json"
    grouped: list[str] = []
    if not catalog_path.is_file():
        errors.append("skills.sh.json is required")
    else:
        try:
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            if catalog.get("$schema") != SKILLS_SCHEMA:
                errors.append("skills.sh.json must use the official skills.sh schema URL")
            if catalog.get("notGrouped") != "bottom":
                errors.append("skills.sh.json notGrouped must be 'bottom'")
            groupings = catalog.get("groupings")
            if not isinstance(groupings, list) or not groupings:
                errors.append("skills.sh.json groupings must be a non-empty list")
            else:
                for index, grouping in enumerate(groupings):
                    if not isinstance(grouping, dict):
                        errors.append(f"skills.sh.json grouping {index} must be an object")
                        continue
                    if not isinstance(grouping.get("title"), str) or not grouping["title"].strip():
                        errors.append(f"skills.sh.json grouping {index} needs a title")
                    if not isinstance(grouping.get("description"), str) or not grouping["description"].strip():
                        errors.append(f"skills.sh.json grouping {index} needs a description")
                    group_skills = grouping.get("skills")
                    if not isinstance(group_skills, list) or not all(
                        isinstance(item, str) and item for item in group_skills
                    ):
                        errors.append(f"skills.sh.json grouping {index} needs a string skills list")
                    else:
                        grouped.extend(group_skills)

            grouped_set = set(grouped)
            if len(grouped) != len(grouped_set):
                errors.append("skills.sh.json lists a skill more than once")
            missing_from_catalog = names - grouped_set
            unknown_in_catalog = grouped_set - names
            if missing_from_catalog:
                errors.append(f"skills.sh.json is missing: {sorted(missing_from_catalog)}")
            if unknown_in_catalog:
                errors.append(f"skills.sh.json contains unknown skills: {sorted(unknown_in_catalog)}")
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            errors.append(f"skills.sh.json is invalid: {exc}")

    readme_path = ROOT / "README.md"
    if not readme_path.is_file():
        errors.append("README.md is required")
    else:
        readme = readme_path.read_text(encoding="utf-8")
        if SKILLS_BADGE_IMAGE not in readme or SKILLS_BADGE_LINK not in readme:
            errors.append("README.md must contain the official skills.sh badge for jayanth-mkv/agent-skills-registry")
        if "<!-- catalog:start -->" not in readme or "<!-- catalog:end -->" not in readme:
            errors.append("README.md must contain generated catalog markers")
        for name in names:
            if f"--skill {name}" not in readme:
                errors.append(f"README.md is missing the selective install command for {name}")

    workflow_path = ROOT / ".github" / "workflows" / "validate.yml"
    if not workflow_path.is_file():
        errors.append(".github/workflows/validate.yml is required")
    else:
        workflow = workflow_path.read_text(encoding="utf-8")
        required_workflow_checks = (
            "skills-ref==",
            "agentskills validate",
            "assert_cli_discovery.py",
            "DISABLE_TELEMETRY",
        )
        for check in required_workflow_checks:
            if check not in workflow:
                errors.append(f"validation workflow is missing required gate: {check}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"{len(errors)} error(s) across {len(skill_files)} discoverable skill(s)")
        return 1

    print(f"Validated {len(skill_files)} discoverable skill(s): {', '.join(sorted(names))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
