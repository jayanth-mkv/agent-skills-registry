---
name: polish-repository-readme
description: Audit, redesign, and validate GitHub repository READMEs using repository-derived premium visual systems, icon-led centered heroes, real demo media or honest paperback fallbacks, plain-language hierarchy, and truthful architecture diagrams. Use when Codex needs to create or improve a repository README, prepare a project for public release, generate coordinated SVG icons, covers, or architecture art, turn a walkthrough into an efficient preview, or review README claims, links, badges, and presentation quality.
---

# Polish Repository README

Create evidence-backed repository landing pages that look deliberate without hiding technical truth.

## Core workflow

1. Read repository instructions and preserve unrelated changes.
2. Inspect source, manifests, docs, tests, media, and the current README.
3. Record each important claim as implemented, experimental, simulated, planned, or unknown.
4. Derive a visual brief from the repository's identity, interface, domain, and existing SVG colors.
5. Use an official logo when one exists. Otherwise create a restrained functional SVG icon.
6. Lead with proof: a real demo when recording exists, or a paperback cover when it does not.
7. Center the identity block; keep the documentation body left aligned.
8. Explain what the project is, then give the shortest verified first-use path.
9. Add a dedicated architecture diagram derived from the actual implementation.
10. Put limitations close to the claims they qualify.
11. Render and inspect every visual, then validate links, Markdown, media, badges, and the final diff.

Read [presentation-rulebook.md](references/presentation-rulebook.md) before choosing hierarchy, proof, or badges. Read [paperback-visual-system.md](references/paperback-visual-system.md) before creating visuals. Read [composition-catalog.md](references/composition-catalog.md) when selecting or hybridizing an icon, cover, or architecture composition.

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
- Create an 8-12 second GIF preview at 800-960 px wide, 8-12 fps, and preferably below 5 MB.
- Begin on the meaningful state; remove idle setup and repeated motion.
- Link the preview to the full recording.
- Use `scripts/make_demo_preview.py` for a reproducible conversion.

When no recording exists:

- Place a paperback cover after the hero navigation.
- Put a real product screenshot after "What is it?" when one is available.
- Never fabricate a product screenshot to fill the gap.

## Asset workflow

1. Inspect the official logo, existing SVGs, UI, screenshots, domain materials, and README tone.
2. Write a one-line brief: `paper / ink / accent / motif / composition / evidence`.
3. Prefer white, off-white, or a very light theme tint; pair it with near-black ink and one restrained repository-derived accent. Add one neighboring shade only when it clarifies hierarchy.
4. Decide whether a composition seed from `assets/templates/` helps. Redraw, combine, or simplify it when useful; invent a new family from the generative axes in the composition catalog when none fits. Treat every seed as a spatial idea, never an allowed list or fill-in-the-blank template.
5. Create a coordinated set: the icon establishes the motif, the cover expresses identity, and the architecture explains implementation. Share visual DNA without repeating the same layout.
6. Vary title placement, geometry, dark-mass placement, proof device, and diagram structure according to the project. Do not default every repository to a left spine and four boxes.
7. Keep architecture separate from the cover and encode implemented, optional, simulated, and planned behavior with labels plus line or fill styles.
8. Render icons at 32, 64, and 128 px; render covers and diagrams at full size and a README-like width. Fix clipping, weak contrast, or illegible labels before handoff.

## Validation

Run the README validator from the target repository root:

```bash
python <skill-path>/scripts/validate_readme.py README.md --repo-root .
```

Also run the repository's existing tests and documentation checks when they are relevant. For a skills collection, verify that its supported installer discovers every published `SKILL.md`.

## Handoff

Report:

- the hierarchy and proof choice;
- media created or converted;
- architecture evidence used;
- badge and install-source evidence;
- validation commands and results;
- anything still planned, simulated, or unverified.
