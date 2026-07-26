# Repository-derived paperback visual system

## Contents

- Intent
- Discover the theme
- Construct the palette
- Coordinate the asset family
- Design each asset
- Control variation
- Encode architecture truth
- Render and review

## Intent

Create a visual system that feels authored for the repository. Keep the premium paper-and-ink character, but do not force every project into the same colors, spine, title position, or box diagram.

Prefer visual restraint over decoration:

- white, off-white, or a very light theme tint;
- near-black ink instead of large areas of arbitrary color;
- one muted accent derived from repository evidence;
- one neighboring support tint only when it improves hierarchy;
- system serif, sans-serif, and monospace fonts that render reliably on GitHub.

## Discover the theme

Inspect sources in this order:

1. Official logo and documented brand assets.
2. Existing repository SVGs and product iconography.
3. Real interface screenshots or demo frames.
4. Domain materials such as paper, stone, film, instruments, maps, or schematics.
5. Repository tone: research, developer tool, industrial system, library, creative application, or service.

Do not invent a fashionable palette when the repository already provides a credible identity. When no identity exists, derive the motif from what the software does.

Write a brief before drawing:

```text
paper: cool white
ink: blue-black
accent: muted slate from the existing icon
motif: scope reticle + source document
cover: asymmetric technical dossier
architecture: sources → local engine → auditable outputs
evidence: SVG icon, CLI entry point, output formats
```

## Construct the palette

Use role-based tokens rather than copying arbitrary hex values throughout an SVG.

| Role | Guidance |
| --- | --- |
| Paper | White or a 92–98% light theme tint; usually 70–90% of the canvas |
| Ink | Near-black with a subtle warm, cool, or green cast |
| Accent | A muted repository-derived hue with strong contrast where used for text |
| Support | A lighter neighboring tint for panels, rings, or current-state fills |
| Rule | A quiet mid-light neutral or desaturated accent |

Good starting families include cool white + blue-black + slate, limestone + brown-black + ochre, gallery white + green-black + sage, and warm white + charcoal + oxblood. These are examples, not mandatory palettes.

Avoid neon accents, candy colors, rainbow palettes, pure saturated primaries, and low-contrast gray-on-tint text. Do not use color alone to communicate status.

## Coordinate the asset family

Use a shared palette, line-weight family, type hierarchy, and one recurring motif. Change how that motif behaves in each asset:

- The icon compresses it into one recognizable mark.
- The cover turns it into identity and atmosphere.
- The architecture diagram uses it to clarify flow or boundaries.

Do not paste the icon at large scale into every visual. Reinterpret it through geometry, framing, rhythm, or line work.

## Design each asset

### Icon

- Use a 256 × 256 canvas and a restrained light container.
- Make the silhouette readable at 32 px.
- Prefer one functional metaphor over initials or decorative symbols.
- Use consistent strokes and no more than three visible color roles.
- Add SVG `<title>` and `<desc>` elements.

### Cover

- Use a 1200 × 630 canvas and one dominant composition.
- Include the exact project name, one defensible promise, and concise verified metadata.
- Use one command only when it is the shortest verified first result.
- Let asymmetry, framing, a dark panel, a technical mark, or an editorial strip carry the composition.
- Keep the canvas predominantly light even when using a dark structural block.

### Architecture

- Use a 1400 × 720 canvas for a compact diagram. Use 1400 × 900 or 1600 × 1000 only when nested deployment boundaries need vertical room; choose geometry that matches the system: rail, hub, stack, branch, storyboard, boundary map, or layered pipeline.
- Show three to six meaningful stages or groups.
- Prioritize readable labels and flow over visual symmetry.
- Include a legend when line or fill styles encode state.

## Control variation

Select, hybridize, or invent a family using [composition-catalog.md](composition-catalog.md). The supplied families are examples, not boundaries. Change at least two structural decisions between unrelated repositories:

- title placement or scale;
- frame, spine, band, or dark-panel placement;
- motif geometry;
- diagram topology;
- density and whitespace rhythm;
- serif/monospace hierarchy.

Keep the palette and motif coherent, but avoid novelty for its own sake. Premium work is controlled, not busy.

## Encode architecture truth

- Use solid paths or fills for implemented behavior.
- Use dashed paths or outlines for planned or optional behavior.
- Label experimental and simulated stages explicitly.
- Pair every color distinction with text, a line style, a pattern, or a shape change.
- Derive every node from source paths, entry points, manifests, tests, or verified runtime behavior.

## Render and review

1. Parse every SVG as XML.
2. Render icons at 32, 64, 128, and 256 px.
3. Render covers and diagrams at full size and approximately 900 px wide.
4. Check font fallback, clipping, alignment, whitespace, and line weight.
5. Verify normal text contrast is at least 4.5:1 and large text or essential shapes at least 3:1.
6. View the image against both GitHub light and dark page backgrounds.
7. Compare the set with other repository visuals and revise obvious layout duplication.
