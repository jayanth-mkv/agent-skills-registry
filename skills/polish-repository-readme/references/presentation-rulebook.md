# Repository presentation rulebook

## Contents

- Canonical sequence
- Alignment
- Proof selection
- Badges
- Content requirements
- Architecture
- Honesty
- Release checklist

## Canonical sequence

Use this order unless repository evidence makes another order clearer:

1. Logo or functional icon, usually 112–144 px.
2. Centered product name.
3. One-sentence promise.
4. Optional one-sentence clarification.
5. A compact row of truthful badges.
6. No more than six navigation links.
7. Real demo preview, or a paperback cover when no recording exists.
8. “What is it?” in plain language.
9. The shortest verified quick start.
10. Capabilities grouped by user outcome.
11. A dedicated architecture diagram.
12. Deeper API, configuration, development, security, and contribution details.

Profile repositories are the exception. They should prioritize the person, work, and contact paths instead of pretending to be a product landing page.

## Alignment

Center the identity block: icon, title, promise, badges, navigation, and primary visual. Left-align explanatory prose, setup steps, code, tables, and reference material. Do not center the entire README.

Keep the hero narrow enough to scan. Treat badges as metadata rather than decoration.

## Proof selection

Prefer evidence in this order:

1. A short preview cut from a real working demo.
2. A real screenshot showing the useful state.
3. A restrained paperback cover that describes the project without pretending to show the product.

Preserve the original MP4 when converting a preview. A GIF is a quick proof, not the canonical recording.

## Badges

Keep badge rows compact and factual. Link every badge to the page that explains or verifies it. Never add an award, usage count, compatibility, build, or security badge before its source exists.

For a public skills repository, use the official install-count badge after confirming the GitHub `owner/repo`:

```markdown
[![skills.sh](https://skills.sh/b/owner/repo)](https://skills.sh/owner/repo)
```

Replace both instances of `owner/repo` with the exact GitHub source. Do not copy a displayed count into static text. The badge remains the live source of truth.

## Content requirements

### What is it?

Answer, in two short paragraphs at most:

- Who is it for?
- What problem does it solve?
- What makes it materially different?
- What runs locally and what depends on a service?

### Quick start

Give the minimum verified path to a first useful result. Derive commands from repository evidence and specify prerequisites. Separate optional configuration from mandatory setup.

### Capabilities

Group features by outcomes instead of producing an undifferentiated checklist. Name limitations beside affected capabilities.

### Technical depth

Progress from simple use to internals. Readers should not need architecture knowledge before the first successful run.

## Architecture

Build diagrams from source paths, entry points, service boundaries, data flow, and tests.

- Show three to six meaningful stages.
- Label direction and important boundaries.
- Use solid lines for implemented paths.
- Use dashed lines only for planned or optional paths, and label them.
- Avoid generic cloud, database, or AI boxes unless the repository proves they exist.
- Keep the architecture diagram separate from the promotional cover.

## Honesty

Never claim a release, integration, metric, compatibility target, or security property without evidence. Use precise labels:

- **Implemented** — present and usable in the repository.
- **Experimental** — present but unstable or incomplete.
- **Simulated** — demonstrated with mock or generated data.
- **Planned** — not yet implemented.
- **Unknown** — evidence was not found; investigate before publishing.

## Visual safe-area gate

For every created or edited SVG, inspect the native render and the actual README-sized render. Zoom into every card, panel, caption, and right/bottom edge; a clean overall silhouette is not enough.

- Measure the visible glyphs, including descenders and strokes—not only SVG text baselines.
- Keep text inside cards and panels at least 16 native pixels from the inner edge horizontally and vertically, unless a smaller, clearly rendered component requires a proportionally equivalent inset.
- Size UI-style cards from their longest label at the embedded width. Treat 16 native pixels as a hard floor, not a target; prefer at least one small-label height of empty space (usually 24 native pixels) along the constrained side.
- Widen or heighten a node and rebalance its connectors before reducing text. Do not make a card merely fit its label.
- Do not leave labels visually touching a divider, border, or the next component. Increase padding, move text, or enlarge the container instead of accepting a tight fit.
- After changing one node, review the complete composition at the embedded width so arrows, alignment, and surrounding whitespace stay balanced.
- Re-render after each spacing fix and inspect all small labels at the embedded README width before committing.

## Release checklist

- Hero identity is centered; body documentation is left aligned.
- Name, promise, badges, and links match repository facts.
- Skills repositories use the official live install-count badge with the verified source.
- Demo is real, short, and linked to its durable source.
- Fallback cover contains no fake interface or metrics.
- Quick-start commands were verified.
- Architecture matches the current implementation.
- Limitations are visible near relevant claims.
- Images have useful alternative text.
- Every SVG passes the visual safe-area gate at its embedded README width.
- Cards are sized around their longest embedded label, with deliberate optical buffer.
- Local links resolve and code fences balance.
- README and asset diffs contain no unrelated changes.
