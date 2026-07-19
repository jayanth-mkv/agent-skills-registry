# Paperback visual system

## Contents

- Principles
- Tokens
- Composition
- Icons
- Covers
- Architecture diagrams
- Motion
- Accessibility

## Principles

- Communicate identity, outcome, and proof in that order.
- Use warm paper and dark ink instead of glossy effects.
- Make the work feel like a field note or technical paperback, not an advertisement.
- Show a real demo when available; use a cover only as the fallback.
- Give architecture its own diagram.
- Keep all text readable on mobile and in GitHub dark mode.

## Tokens

| Role | Value |
| --- | --- |
| Paper | `#F4F0E7` |
| Ink | `#151515` |
| Graphite | `#69655E` |
| Rule | `#B9B3A8` |
| Display type | Georgia, Times New Roman, serif |
| Body type | Arial, Helvetica, sans-serif |
| Code type | Courier New, monospace |

Repositories may introduce one accessible accent color from an existing identity. Do not turn the system into a multi-color theme.

## Composition

- Cover canvas: 1200 × 630.
- Architecture canvas: 1400 × 720.
- Use a visible outer frame, generous margins, and an 8 px spacing rhythm.
- Prefer square corners and simple line work.
- Avoid gradients, glow, glass effects, stock illustrations, and icon walls.
- Limit a cover to product name, promise, one command or proof line, and concise metadata.

## Icons

Use the official logo when licensing and repository evidence allow it. Otherwise create a functional SVG mark related to the product.

Place the mark in a restrained rounded-square paper container. Include SVG `<title>` and `<desc>` elements. Do not use emoji as product icons.

## Covers

A paperback cover must state the exact project name and a defensible promise. It may show:

- one verified command;
- a short implementation label;
- a small metadata line such as “LOCAL / OPEN / SCRIPTABLE.”

It must not show fabricated download counts, customer logos, awards, charts, screenshots, or benchmarks.

## Architecture diagrams

Use three to six stages with one obvious reading direction. Label boundaries and line meaning. Solid lines mean current implementation; dashed lines mean optional or planned behavior. Never rely on color alone.

## Motion

Cut demo previews to 8–12 seconds, 800–960 px wide, 8–12 fps, and preferably below 5 MB. Start on meaningful action. Link to the complete MP4. Do not convert a long walkthrough into a full-length GIF.

## Accessibility

- Maintain at least 4.5:1 contrast for normal text.
- Avoid tiny labels that become unreadable in GitHub’s responsive view.
- Give every README image descriptive alternative text.
- Add `<title>` and `<desc>` to SVGs.
- Pair color differences with labels, patterns, or line styles.
