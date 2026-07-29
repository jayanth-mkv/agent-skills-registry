# Technical SEO playbook

Use this reference to investigate whether important content can be fetched, rendered, understood, selected, and maintained. Validate current platform behavior against primary documentation before applying high-risk changes.

## Contents

1. [Dependency order](#dependency-order)
2. [Availability and status behavior](#availability-and-status-behavior)
3. [Robots and index controls](#robots-and-index-controls)
4. [Canonicals and duplicates](#canonicals-and-duplicates)
5. [Sitemaps and discovery](#sitemaps-and-discovery)
6. [Change notification](#change-notification)
7. [Architecture and links](#architecture-and-links)
8. [JavaScript and mobile](#javascript-and-mobile)
9. [Core Web Vitals](#core-web-vitals)
10. [Structured data](#structured-data)
11. [Images, video, and accessibility](#images-video-and-accessibility)
12. [Large sites and crawl logs](#large-sites-and-crawl-logs)
13. [Technical acceptance tests](#technical-acceptance-tests)

## Dependency order

Investigate in this order:

```text
host available
-> URL fetchable
-> intended crawler allowed
-> index directive permits inclusion
-> response/render contains primary content
-> canonical and alternates are coherent
-> URL is discoverable
-> content and markup are interpretable
-> experience is usable
-> search systems recrawl and process
```

A later optimization cannot compensate for an earlier blocker.

## Availability and status behavior

Test representative URLs and variants:

- HTTP and HTTPS;
- preferred and non-preferred hostnames;
- trailing slash/case variants;
- encoded paths and common parameters;
- expired, deleted, moved, unauthorized, and server-error examples;
- asset and API paths needed to render content;
- IPv4/IPv6 or CDN/origin differences when evidence points there.

Record the complete redirect path, status code, final URL, content type, response size, cache behavior, and relevant headers.

On HTTPS pages, inspect insecure subresources and internal HTTP links. Distinguish a browser-blocked or upgraded subresource from a navigational link that redirects. Fix the source template to emit the intended HTTPS URL after confirming the resource works there.

### Status intent

- Return `200` only for a real, usable resource.
- Use a permanent redirect for a durable move when the destination is a genuine replacement.
- Use a temporary redirect only when the move is actually temporary.
- Return `404` or `410` for removed content with no replacement; do not redirect every missing URL to the homepage.
- Treat a `200` page that communicates “not found” as a soft-404 candidate.
- Keep redirect chains short and destinations semantically relevant.
- Investigate sustained `5xx`, connection failures, DNS errors, or extreme response times as availability problems before SEO polish.

Do not recommend status changes solely from a crawler label. Confirm product behavior and the intended lifecycle.

## Robots and index controls

Keep these controls distinct:

| Control | Primary effect |
| --- | --- |
| robots.txt | Controls compliant crawler fetching, not guaranteed index exclusion |
| `noindex` meta | Requests exclusion after the page can be fetched and read |
| `X-Robots-Tag` | Header equivalent, useful for non-HTML resources |
| authentication / authorization | Prevents public access |
| `nosnippet`, `max-snippet`, `data-nosnippet` | Limits search previews, including supported AI search presentations |
| canonical | Signals preferred duplicate; it is not an index-blocking directive |

### Robots audit

- Fetch the root robots.txt for each relevant host.
- Parse user-agent groups, paths, wildcards, end anchors, sitemap declarations, and file status.
- Test exact high-value URLs against the intended crawler tokens.
- Check whether CDN/WAF/bot rules contradict robots.txt.
- Distinguish search crawlers, AI-search crawlers, training crawlers, user-triggered fetchers, ads crawlers, and generic agents.
- Verify current user-agent names and behavior from each provider’s official documentation.
- Confirm the owner’s policy before recommending allow or disallow changes.

Never “fix” a deliberate block merely to raise an audit score.

### Index-directive audit

Inspect raw HTML, rendered DOM, and HTTP headers. Detect:

- unintended `noindex`;
- contradictory crawler-specific and generic directives;
- `noindex` pages blocked in robots.txt, preventing the directive from being observed;
- directives injected or removed by JavaScript;
- template, environment, or header rules affecting whole cohorts;
- staging directives leaking to production.

## Canonicals and duplicates

Canonicalization is a signal set, not a command. Compare:

- redirects;
- HTML or HTTP `rel=canonical`;
- sitemap membership;
- internal-link targets;
- hreflang references;
- HTTP/HTTPS and hostname consistency;
- content similarity;
- GSC user-selected and Google-selected canonicals.

### Canonical acceptance rules

For an intended indexable HTML URL:

- emit at most one absolute canonical in the raw source;
- point it to an accessible, index-eligible URL with equivalent primary content;
- avoid canonical chains and loops;
- keep JavaScript from changing it to a competing target;
- align links and sitemaps with the chosen URL;
- do not canonicalize materially different pages merely to suppress them.

Self-canonicals can reinforce consistency but do not make a page indexable by themselves.

### Duplicate families

Investigate:

- tracking, sorting, filtering, session, and pagination parameters;
- print, AMP, mobile, and syndicated versions;
- uppercase/lowercase and trailing-slash variants;
- protocol and hostname variants;
- near-identical location, product, or programmatic pages;
- faceted navigation combinations;
- duplicate titles as a symptom, not proof of duplicate primary content.

Choose among consolidation, canonicalization, redirect, `noindex`, crawl controls, or intentional separate indexation based on user value and URL purpose.

## Sitemaps and discovery

A sitemap is a discovery and canonical hint, not a guarantee of crawling or indexing.

Audit:

- robots declarations and common sitemap locations;
- index and child sitemap syntax/status;
- only absolute, preferred, index-eligible URLs;
- host/protocol consistency;
- accurate `lastmod` tied to meaningful content changes;
- size and URL limits from the current protocol/search documentation;
- image, video, news, or hreflang extensions when the site actually needs them;
- GSC submitted/read status and discovered-vs-indexed patterns by sitemap cohort.

Compare four inventories:

```text
CMS/database URLs
vs sitemap URLs
vs crawl-discovered URLs
vs search-engine-known/indexed URLs
```

Differences reveal orphan candidates, stale URLs, crawl traps, and inventory gaps. Do not call a URL “orphaned” from a crawl alone; it may have links outside the crawl scope.

## Change notification

Sitemaps, internal links, feeds, and ordinary recrawling remain the durable discovery foundation. For high-change inventory, a search engine may also support an authenticated URL-change notification protocol such as IndexNow.

Use it only when the target engine currently supports it and the site owner authorizes submission:

1. verify the current protocol, endpoint, key ownership, URL limits, and participating engines;
2. generate the key through an approved secret process and expose only the required verification artifact;
3. submit canonical URLs on meaningful create, update, or delete events rather than every request;
4. batch, deduplicate, rate-limit, retry only documented transient failures, and keep a dead-letter queue;
5. record event time, submitted URL, change type, response, retry count, and source release;
6. monitor delivery failures and compare downstream crawl/index evidence by cohort;
7. test deletion and rollback behavior before enabling at scale.

An accepted notification confirms receipt, not crawling, indexing, ranking, or display. Do not expose keys in reports or repositories, and do not use notification APIs to submit URLs the owner does not control.

## Architecture and links

Model the site as URL cohorts and a directed link graph.

Check:

- important pages reachable through crawlable `<a href>` links;
- logical hubs, categories, breadcrumbs, and contextual paths;
- depth distribution by business value;
- isolated or weakly linked cohorts;
- broken internal targets and redirected internal links;
- anchor text that identifies the destination without stuffing;
- links hidden behind interactions or scripts that crawlers may not discover;
- infinite spaces from calendars, filters, searches, or combinations;
- pagination that exposes stable crawlable page URLs;
- internal links to noncanonical, `noindex`, or blocked URLs.

There is no universal “three-click rule.” Treat depth as a proxy for discoverability and priority, then interpret it in the site’s architecture.

### Faceted navigation

Build a facet matrix before changing controls:

| Facet/state | User value | Search demand | Unique inventory/content | Stable URL | Index? | Crawl/discovery rule | Canonical |
| --- | --- | --- | --- | --- | --- | --- | --- |

- Keep user filtering independent from which combinations become search landing pages.
- Allow only selected, stable combinations with real inventory and maintained value.
- Normalize parameter order and prevent session, tracking, empty, contradictory, and near-infinite combinations.
- Make indexable facet pages discoverable through intentional links; do not depend on form controls alone.
- Define empty, low-inventory, changed-inventory, and expired behavior.
- Do not combine robots blocking and `noindex` in a way that prevents the directive from being read.
- Test crawl volume and index state by cohort after each control change.

Canonical tags do not make an infinite URL space harmless. Prevent unnecessary discovery at the generator and linking layers.

### Pagination and incremental loading

- Give each result page a stable crawlable URL and a direct link from the previous page.
- Keep paginated pages self-canonical when they contain distinct items.
- Do not canonicalize every page in a sequence to page one.
- Ensure “load more” or infinite scroll has equivalent URL states and crawlable links.
- Avoid fragment-only navigation for content that needs independent discovery.
- Keep filtering/sorting parameters separate from the core page sequence.
- Test deep pages with JavaScript disabled as a discovery diagnostic and in the rendered experience for users.

## JavaScript and mobile

### Raw/rendered parity

Compare initial HTML with a rendered browser for:

- title, meta description, robots directives, canonical, hreflang;
- primary text, headings, links, images/video;
- structured data;
- HTTP status and error states;
- content requiring clicks, scrolls, consent, login, geolocation, or unsupported APIs;
- hydration errors, client routing, lazy loading, and timeouts.

Prefer server-rendered or reliably pre-rendered critical SEO elements. Do not rely on a non-`200` page to inject corrective metadata with JavaScript.

### Mobile parity

Verify mobile and desktop versions expose equivalent:

- primary content and meaningful media;
- titles, descriptions, directives, canonicals, alternates;
- structured data;
- internal links;
- alt text and captions;
- access to assets.

Also inspect viewport behavior, horizontal overflow, navigation, forms, intrusive interstitials, consent, and tap usability. Treat mobile usability as a user and content-parity concern, not a binary “indexed/not indexed” shortcut.

### Rendering evidence

Use:

- browser devtools and screenshots;
- accessibility tree;
- rendered DOM export;
- Search Console inspection/rendered HTML where available;
- server logs for crawler asset requests;
- controlled JavaScript-disabled comparison as a diagnostic, not as a universal requirement.

## Core Web Vitals

Use current “good” thresholds at the 75th percentile:

| Metric | Good |
| --- | --- |
| LCP | at or below 2.5 seconds |
| INP | at or below 200 milliseconds |
| CLS | at or below 0.1 |

Verify these thresholds against current web.dev documentation at execution time.

### Measurement hierarchy

1. Page-level field data when sufficiently populated.
2. URL-group/origin field data with cohort disclosure.
3. Real-user monitoring owned by the site.
4. Repeated lab tests under documented conditions.
5. A single lab run only as a diagnostic clue.

Do not substitute Total Blocking Time for INP without labeling it as a lab proxy. Test mobile and desktop separately.

### Diagnose causes

For LCP inspect:

- server response and caching;
- discovery time of the LCP resource;
- preload/priority and render-blocking work;
- image size/format/dimensions;
- client rendering and late content insertion.

For INP inspect:

- long main-thread tasks;
- event handlers and third-party code;
- DOM/layout work and rendering delay;
- interaction-specific bottlenecks;
- framework hydration and excessive JavaScript.

For CLS inspect:

- unsized images/embeds/ads;
- injected banners and consent UI;
- font swaps;
- dynamic content inserted above existing content;
- animations that trigger layout.

Set performance budgets by template and protect them in CI where practical.

## Structured data

Structured data can support understanding and eligible search features; it does not guarantee a feature or ranking.

Workflow:

1. Identify a currently supported feature relevant to the visible page.
2. Read the current feature-specific and general guidelines.
3. Choose JSON-LD when practical, while preserving existing valid formats.
4. Mark up only visible, truthful, page-specific content.
5. Include required properties and genuinely available recommended properties.
6. Use stable `@id` values to connect entities where useful.
7. Validate syntax and feature eligibility.
8. Inspect rendered output and production deployment.
9. Monitor enhancement reports/manual actions.

Flag:

- invalid JSON or duplicate contradictory blocks;
- unsupported/deprecated types presented as rich-result opportunities;
- properties not visible or not true;
- self-serving ratings or fake reviews;
- mismatched price, availability, dates, authors, locations, or images;
- markup emitted on `noindex`, blocked, canonicalized-away, or error pages;
- JS-only markup that arrives late on time-sensitive pages.

Schema.org validity and Google rich-result eligibility are different checks. Record both.

## Images, video, and accessibility

### Images

- Use useful, high-quality images near relevant text.
- Preserve meaningful `alt` text; use empty `alt=""` for decorative images.
- Do not stuff keywords into alt text.
- Provide stable dimensions/aspect ratio and responsive sources.
- Compress appropriately and choose formats based on browser/product support.
- Keep important images crawlable and avoid placeholder-only initial markup.
- Check image sitemaps only when normal discovery is insufficient.
- Verify licensing and ownership.

### Video

- Provide a dedicated watch page when video discovery matters.
- Keep title, thumbnail, description, date, duration, transcript/captions, and structured data consistent.
- Ensure the video and thumbnail are fetchable and the video is prominent.
- Use the current video indexing guidance and relevant sitemap/schema rules.

### Accessibility

Audit semantic landmarks, link/button semantics, labels, keyboard access, alt text, captions, focus, contrast, and usable error states. Accessibility is valuable on its own and also improves machine-readable structure. Do not misrepresent an accessibility heuristic as a direct ranking factor.

## Large sites and crawl logs

For very large or rapidly changing sites:

- segment logs by verified crawler, host, directory, status, content type, template, and response time;
- compare crawl frequency with business priority, sitemap freshness, and internal-link prominence;
- identify traps, duplicate parameters, slow cohorts, repeated errors, and stale inventory;
- inspect faceting rules, search pages, session URLs, calendars, infinite pagination, and soft 404s;
- use CMS/database inventory to measure coverage;
- send accurate `Last-Modified`/`ETag` validators where the stack supports them and verify conditional requests return a correct `304` without a response body;
- cache stable resources without serving stale directives, canonicals, inventory, prices, or error states;
- keep robots.txt, sitemaps, redirects, and important HTML available during load spikes;
- change one control at a time where possible.

Use the bundled log analyzer for a bounded first pass, then verify material crawler identities and join path cohorts to the CMS/crawl inventory. Do not invoke “crawl budget” as a generic explanation for a small site. Establish scale, update rate, and crawl evidence first.

## Technical acceptance tests

For every changed cohort test:

```text
Request URL:
Expected status and redirect path:
Expected final URL:
robots.txt result by intended user agent:
Expected meta/X-Robots directive:
Expected canonical:
Expected hreflang set:
Expected sitemap membership:
Expected change-notification event, if used:
Expected internal-link source:
Raw primary content present:
Rendered primary content present:
Expected structured data:
Mobile parity:
Performance budget:
Rollback:
```

Then test at least one positive case, one edge case, and one failure/deleted case. Re-crawl with the same configuration and preserve before/after evidence.
