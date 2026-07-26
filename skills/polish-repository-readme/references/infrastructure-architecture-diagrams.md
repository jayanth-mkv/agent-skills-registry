# Nested infrastructure architecture diagrams

Use this reference when a README needs to explain a deployed or self-hosted system with nested boundaries: cloud or VPC scopes, application planes, workers, APIs, datastores, queues, schedulers, identity providers, and external clients. It is not a reason to invent a deployment diagram for a repository that only proves local code.

## Evidence first

Build an evidence map before drawing. Derive every box, boundary, and arrow from source material.

| Evidence found | Diagram treatment |
| --- | --- |
| Compose, Helm, Terraform, Pulumi, deployment docs, or cloud config | Show the proven deployment or network boundary. |
| Service entry points, workers, queues, stores, and route handlers | Show the implemented service role and data/control flow. |
| Environment examples or credential setup | Show an integration boundary only when the component and relationship are documented. |
| Tests, mocks, samples, or roadmap notes | Label simulated, optional, or planned behavior explicitly. |
| Missing deployment evidence | Draw the logical architecture instead; do not add VPCs, private subnets, OAuth, secrets, or managed services. |

Use the repository's own names where they clarify a boundary. Use a generic role label where branding would be unsupported. Never reproduce a vendor's logo or a reference image's product identity unless the repository provides and permits the official asset.

## Spatial grammar

Choose a boundary map when containment and trust boundaries matter more than a simple linear flow.

1. Start with a concise title and, when helpful, one factual subtitle.
2. Draw the outermost proven boundary first: deployment, network, local machine, or hosted platform.
3. Add nested planes only when they represent real containment, such as an application runtime inside a proven network boundary.
4. Place the execution core near the center; group its workers, services, or APIs as one coherent operating area.
5. Put inputs and user-facing entry points outside the left or top edge; place data, identity, and third-party integrations near the side they serve.
6. Keep operational controls such as schedules, webhooks, or outbound internet paths on a separate lower or side band when that makes crossings disappear.
7. Use five to nine meaningful groups. Split a dense node only when the implementation has a real separate responsibility.

Use a 1400 × 900 or 1600 × 1000 SVG when nested boundaries need vertical breathing room. Do not compress a containment map into a shallow 16:9 strip merely to match a promotional cover.

## Visual grammar

- Use a light canvas, near-black text, one repository-derived accent, and one quiet support tint. Keep most of the page light.
- Make boundaries subtle containers with clear labels; make active components raised cards with a little more contrast. Do not use shadows to replace hierarchy.
- Give containers broader padding than their child cards. Keep the page frame, outer boundary, and inner plane visually distinct.
- Use functional, generic symbols for compute, storage, schedule, API, or browser roles when no official asset exists. Symbols must reinforce labels, never replace them.
- Use a short role label above a component name when that reduces ambiguity: for example, `EXECUTION` then `Workers`.
- Size every card from its longest embedded label. Keep the optical spacing rules in the presentation rulebook; never shrink type merely to preserve a fixed node width.
- Do not copy another product's layout, color palette, logos, or icon artwork. Use the reference as a topology and legibility cue only.

## Connector semantics

| Connector | Meaning |
| --- | --- |
| Solid, single-headed arrow | Implemented, directional request, event, or data flow. |
| Solid line with two arrowheads | A documented two-way exchange; label the interaction when direction would otherwise be unclear. |
| Dashed arrow | Optional, experimental, or planned path; add a nearby state label. |
| Short labeled connector | An important protocol, handoff, or permission boundary such as `webhook`, `OAuth`, or `read-only manifest`, only when proved. |

- Dock connectors at card edges, not through labels or icons.
- Keep arrows horizontal or vertical when possible; reroute nodes before accepting crossings.
- Use one arrow for one concept. Do not use undirected decorative lines.
- Rebalance connector lengths after widening any node; equal spacing is less important than an unambiguous path.

## Construction blueprint

Use this as a starting order, then remove any group the repository does not prove:

```text
title + factual subtitle
outer deployment or trust boundary
  inner application plane
    entry points → execution core → stateful services
external users, APIs, and integrations outside the relevant boundary
documented control, schedule, or outbound paths on a separate band
small legend only when fills or line styles encode state
```

Represent one worker pool as one card unless the code or deployment actually distinguishes worker types. Represent a service mesh, private subnet, secret store, or authentication exchange only when supported by configuration or documentation.

## SVG and review checklist

1. Add meaningful SVG `title` and `desc` elements.
2. Group outer boundaries before their children and keep reusable arrow markers in `defs`.
3. Render at native size and at approximately 900 px wide, then inspect the entire diagram and every dense card.
4. Check that all labels, icon strokes, and connector endpoints have deliberate breathing room at the embedded width.
5. Confirm each boundary, security property, integration, and directional arrow against the evidence map.
6. View against GitHub light and dark page backgrounds; retain clear contrast and a readable outline.
7. Keep the diagram separate from the promotional cover and state any simulated, optional, or planned path in the README text as well.
