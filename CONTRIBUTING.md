# Contributing

Thanks for helping make Skills Dump dependable for real project work. Contributions may add a focused skill, improve an existing workflow, repair documentation, or strengthen repository tooling.

[AGENTS.md](AGENTS.md) is the authoritative contribution rulebook for humans and coding agents. Read it before editing.

## Add a skill

1. Choose a lowercase kebab-case name.
2. Create `skills/<name>/SKILL.md` and only the resources the workflow truly needs.
3. Keep the skill independently installable and include `LICENSE.txt`.
4. Add quoted interface metadata in `agents/openai.yaml`.
5. Add the skill to `skills.sh.json`.
6. Generate the root catalog.
7. Pass repository validation, the official specification validator, and real CLI discovery.
8. Forward-test the skill on a realistic task.
9. Add the change under “Unreleased” in `CHANGELOG.md`.

Start from an official skill initializer when one is available. Do not copy another skill blindly; remove resources and instructions the new workflow does not need.

## Validate

Run the dependency-free repository checks:

```bash
python scripts/validate_all_skills.py
python scripts/generate_catalog.py --check
python skills/polish-repository-readme/scripts/validate_readme.py README.md --repo-root .
```

Validate the Agent Skills specification with the pinned reference package:

```bash
python -m pip install skills-ref==0.1.1
agentskills validate skills/<skill-name>
```

Confirm that the same CLI used by merge-blocking CI discovers every skill:

```bash
DISABLE_TELEMETRY=1 npx --yes skills@1.5.19 add . --list
```

On Windows PowerShell, set `$env:DISABLE_TELEMETRY="1"` before the `npx` command. Run any skill-specific checks shown in `SKILL.md` and open changed SVG, GIF, and screenshot assets before submitting them.

## Indexing

skills.sh automatically tracks a public repository after users install from it through the `skills` CLI. Contributors do not manually register entries and must not create fake install events.

The root badge must keep this exact source unless the repository is renamed or transferred:

```markdown
[![skills.sh](https://skills.sh/b/jayanth-mkv/skills-dump)](https://skills.sh/jayanth-mkv/skills-dump)
```

## Commit and pull request

Use a one-line Conventional Commit title and at least one descriptive body line. Never include author names, assistant names, or co-author trailers.

In the pull request, explain the problem, behavior, verification, and any security or network implications. Include output from repository validation, official specification validation, and CLI discovery. The pull request template contains the complete checklist.

## Scope

A focused skill is better than a large bundle of loosely related instructions. If a proposed skill cannot be described with a clear trigger, split or rethink it before submission.
