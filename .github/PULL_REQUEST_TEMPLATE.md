## Problem

What user or contributor problem does this change solve?

## Change

What behavior, skill, documentation, or tooling changed?

## Verification

Include repository validation, official specification validation, real CLI discovery, and realistic usage checks.

## Checklist

- [ ] I read and followed `AGENTS.md`.
- [ ] The skill is a direct child of `skills/` and independently installable.
- [ ] `SKILL.md` uses valid frontmatter, an actionable description, and fewer than 500 lines.
- [ ] The pinned `skills-ref` validator accepts every changed skill.
- [ ] The pinned `skills` CLI discovers every published skill.
- [ ] Claims, commands, screenshots, badges, and diagrams are evidence-backed.
- [ ] `skills.sh.json` and the generated catalog are synchronized.
- [ ] The official skills.sh badge still points to `jayanth-mkv/agent-skills-registry`.
- [ ] Every new skill contains `LICENSE.txt` and `agents/openai.yaml`.
- [ ] Scripts provide `--help` and fail safely.
- [ ] I forward-tested substantial skill behavior and visually inspected changed assets.
- [ ] I documented network, dependency, security, or destructive behavior.
- [ ] CI or tests disable installer telemetry.
- [ ] The commit has a Conventional Commit title and descriptive body.
- [ ] The commit does not name authors, assistants, or co-authors.
