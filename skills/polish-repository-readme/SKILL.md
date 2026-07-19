---
name: polish-repository-readme
description: Audit, redesign, and validate GitHub repository READMEs using icon-led centered heroes, real demo media or paperback fallbacks, plain-language information hierarchy, and honest architecture diagrams. Use when Codex needs to create or improve a repository README, prepare a project for public release, generate supporting SVG README assets, turn a walkthrough into an efficient preview, or review README claims, links, badges, and presentation quality.
---

# Polish Repository README

Create evidence-backed repository landing pages that look deliberate without hiding technical truth.

## Core workflow

1. Read repository instructions and preserve unrelated changes.
2. Inspect source, manifests, docs, tests, media, and the current README.
3. Record each important claim as implemented, experimental, simulated, planned, or unknown.
4. Use an official logo when one exists. Otherwise create a restrained functional SVG icon.
5. Lead with proof: a real demo when recording exists, or a paperback cover when it does not.
6. Center the identity block; keep the documentation body left aligned.
7. Explain what the project is, then give the shortest verified first-use path.
8. Add a dedicated architecture diagram derived from the actual implementation.
9. Put limitations close to the claims they qualify.
10. Validate links, Markdown, SVGs, media, badges, and the final diff.

Read [presentation-rulebook.md](references/presentation-rulebook.md) before choosing hierarchy, proof, or badges. Read [paperback-visual-system.md](references/paperback-visual-system.md) before creating visuals.

## Evidence rules

- Derive commands from package scripts, manifests, entry points, tests, or working examples.
- Use only badges backed by a real URL or repository fact.
- For a public skills repository, add the official `skills.sh` install-count badge with its verified `owner/repo` source.
- Never invent adoption numbers, performance claims, integrations, screenshots, or architecture.
- Label simulated, experimental, planned, and unavailable behavior explicitly.
- Treat profile repositories as an exception: prioritize personal identity and navigation instead of a product demo.

## Proof decision

When a real recording exists:

- Keep the complete MP4 as the durable source.
- Create an 8–12 second GIF preview at 800–960 px wide, 8–12 fps, and preferably below 5 MB.
- Begin on the meaningful state; remove idle setup and repeated motion.
- Link the preview to the full recording.
- Use `scripts/make_demo_preview.py` for a reproducible conversion.

When no recording exists:

- Place a paperback cover after the hero navigation.
- Put a real product screenshot after “What is it?” when one is available.
- Never fabricate a product screenshot to fill the gap.

## Asset workflow

1. Copy the closest SVG from `assets/templates/`.
2. Replace the placeholder title, promise, labels, and diagram stages with repository-specific content.
3. Preserve the paper-and-ink tokens unless the repository has a stronger existing identity.
4. Keep architecture separate from the cover.
5. Open or render every SVG before handoff.

## Validation

Run the README validator from the target repository root:

```bash
python <skill-path>/scripts/validate_readme.py README.md --repo-root .
```

Also run the repository’s existing tests and documentation checks when they are relevant. For a skills collection, verify that its supported installer discovers every published `SKILL.md`.

## Handoff

Report:

- the hierarchy and proof choice;
- media created or converted;
- architecture evidence used;
- badge and install-source evidence;
- validation commands and results;
- anything still planned, simulated, or unverified.
