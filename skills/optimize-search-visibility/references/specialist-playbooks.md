# Specialist SEO playbooks

Load only the branches that match the site. Apply the core audit first, then these additional checks.

## Contents

1. [Local businesses](#local-businesses)
2. [International and multilingual sites](#international-and-multilingual-sites)
3. [Ecommerce and marketplaces](#ecommerce-and-marketplaces)
4. [Publishers, news, Discover, image, and video](#publishers-news-discover-image-and-video)
5. [SaaS and developer products](#saas-and-developer-products)
6. [Programmatic SEO and user-generated content](#programmatic-seo-and-user-generated-content)
7. [Migrations and redesigns](#migrations-and-redesigns)
8. [Multi-site and enterprise governance](#multi-site-and-enterprise-governance)

## Local businesses

### Confirm the operating model

Identify:

- storefront, service-area, hybrid, practitioner, department, or multi-location business;
- real customer-facing name, address, phone, hours, category, service area, and appointment/order paths;
- which locations are distinct and staffed;
- regulated or sensitive review/claim constraints.

### Audit

- Google Business Profile ownership, verification, primary/secondary categories, address/service area, hours, special hours, phone, website, appointment/menu/order URLs, attributes, photos, products/services, posts, and policy status.
- Consistency between Business Profile, landing page, contact/location data, official profiles, and major relevant citations.
- One useful landing experience per real location or service area, with unique local proof and accurate availability.
- LocalBusiness subtype and properties that are visible, true, and supported.
- Map, directions, parking/accessibility, service radius, staff, licenses, local reviews/testimonials, and conversion path.
- Local query and map-pack observations by grid/locale only through approved data or manual sampling.
- Review acquisition and response practices that follow platform rules; no incentives or gating.
- Duplicate/closed/moved listings and practitioner/location relationships.
- Local backlinks/mentions from legitimate community, partner, association, and press sources.

### Guardrails

- Do not create virtual offices, fake locations, keyword-stuffed names, fabricated reviews, or doorway pages.
- Do not expose a service-area business address when policy or safety requires hiding it.
- Do not mass-generate city pages with swapped place names. Require distinct demand, service reality, proof, and utility.
- Treat NAP consistency as an identity/data-quality issue, not a magic count of citations.

### Measure

Track Business Profile views/interactions where available, local landing visibility, calls/forms/bookings with privacy-safe attribution, direction requests, review quality/response, and local conversion—not grid rank alone.

## International and multilingual sites

### Define targeting

For every market state:

- language and optional region;
- intended audience and legal/commercial availability;
- URL pattern and host;
- canonical;
- hreflang code and reciprocal alternates;
- currency, units, pricing, inventory, shipping, tax, contact, and support;
- owner and translation/review process.

### Audit

- distinct, crawlable URLs for each language/region;
- one chosen hreflang implementation method when practical;
- valid language first, optional region second, plus `x-default` where useful;
- self-reference and reciprocal complete clusters;
- fully qualified URLs and consistent canonical/hreflang relationships;
- localized main content, navigation, metadata, structured data, media, and conversion path;
- redirects based on user choice rather than forced IP/language traps;
- mobile/raw/rendered parity;
- locale-specific sitemaps, Search Console properties, analytics, and performance;
- regional demand and SERPs rather than translated seed keywords only.

### Guardrails

- `hreflang` is not a substitute for translation, indexability, or canonicals.
- The HTML `lang` attribute improves accessibility but is not the hreflang targeting mechanism.
- Avoid canonicals from every locale to one language unless they are true duplicates and that policy is intentional.
- Do not auto-redirect crawlers or users so alternate URLs cannot be accessed.
- Do not publish unreviewed machine translation in high-risk contexts.

### Acceptance

For a sample cluster, every indexable alternate returns `200`, canonicalizes to itself or the documented equivalent, lists the identical reciprocal set, uses supported codes, and gives users a working locale switch.

## Ecommerce and marketplaces

### Inventory the lifecycle

Model:

```text
category -> subcategory/facet -> product family -> variant
-> in stock / temporarily unavailable / discontinued / replaced
```

Define index and canonical policy for every state before changing templates.

### Audit

- product/category URL stability, variant strategy, facets, sorting, pagination, search pages, and crawl traps;
- category copy and merchandising that help selection rather than add filler;
- unique and accurate product names, descriptions, specs, identifiers, media, price, currency, availability, shipping/returns, and reviews;
- Product/Offer/MerchantReturnPolicy or other currently supported markup where applicable and truthful;
- agreement among visible page, structured data, Merchant Center/feed, inventory system, and checkout;
- canonical behavior for variants and parameter URLs;
- expired/discontinued policy: retain, replace, redirect, or return not found based on user need and replacement equivalence;
- image quality, alt text, dimensions, variants, and image discovery;
- filters that users need versus combinations that create low-value index inventory;
- out-of-stock handling and restock/alternative paths;
- internal links from categories, related products, buying guides, and support content;
- merchant listing/free listing eligibility, diagnostics, and policy status;
- reviews: verified collection, moderation, visibility, and no self-serving/fabricated ratings.

### Marketplaces

Also inspect seller/content moderation, duplicate offers, canonical ownership, thin/empty result pages, expired listings, trust/safety, location, and internal search/facet quality. Prevent indexation of empty or nonsensical combinations at the generator level.

### Agentic commerce

When the user asks about shopping agents or emerging commerce protocols:

- verify current official documentation and availability;
- separate production standards from previews/experiments;
- protect credentials, payment, user consent, pricing, and inventory integrity;
- never claim that a protocol improves rankings without evidence;
- keep ordinary product pages, feeds, and checkout usable.

## Publishers, news, Discover, image, and video

### Editorial trust

Audit:

- clear publication, author, editor/reviewer, corrections, ownership, contact, and policy information;
- original reporting, source provenance, timestamps, substantive update history, and conflicts;
- byline/author pages that reflect real expertise;
- paywall/access implementation and supported markup;
- ad/interstitial density and reading experience;
- syndication/canonical agreements;
- archive, tag, topic, author, pagination, and duplicate taxonomy pages.

### News

Verify current Google News policies and supported structured data/sitemap limits. Check:

- stable article URLs and publication dates;
- headline/date/author/image consistency;
- news sitemap recency and status;
- corrections and live-blog behavior;
- transparent sponsored/affiliate labeling;
- no scraped or auto-rewritten reporting.

### Discover

Treat Discover as unpredictable and interest-driven. Use compelling but accurate titles, high-quality large images when permitted, useful current or evergreen content, and a strong page experience. Do not promise inclusion or turn every title into clickbait.

### Images

Build original, licensable, high-resolution media near relevant text. Preserve crawlable sources, responsive variants, descriptive alt where meaningful, stable dimensions, and image metadata where appropriate. Inspect Image search data separately.

### Video

Use dedicated watch pages for strategic videos, prominent playable video, crawlable thumbnails, captions/transcripts, consistent metadata, supported structured data, and video sitemaps when needed. Inspect video indexing and Video search separately.

## SaaS and developer products

### Map the search-to-product journey

Include:

- category/problem pages;
- use cases and industries;
- feature and integration pages;
- comparisons and alternatives;
- pricing and packaging;
- documentation, API references, changelog, status, security/trust, templates/tools;
- onboarding, activation, and support.

### Audit

- positioning and category clarity;
- product claims tied to current capability and proof;
- docs/app/marketing-domain canonical and subdomain relationships;
- versioned docs and obsolete endpoints;
- integration directories with real, distinct utility;
- programmatic template/tool pages and empty states;
- comparison pages that are factual, current, fair, and maintained;
- pricing/schema/organization/product facts across pages and feeds;
- signup/demo conversion and product handoff;
- JavaScript rendering and authenticated/public boundaries;
- developer experience: copyable examples, errors, prerequisites, version/date, and working links.

### Guardrails

- Do not publish fabricated comparison data, customer logos, integrations, reviews, or benchmarks.
- Do not expose authenticated/private docs for search.
- Do not create hundreds of integration/industry pages before the product and content can support distinct value.

## Programmatic SEO and user-generated content

### Require a value model

For each generated page define:

```text
unique input data
user job
page utility
minimum valid state
quality/completeness gate
index eligibility gate
canonical rule
internal discovery rule
update/expiry rule
owner and monitoring
```

Templates are not value. A page should remain useful when the substituted tokens are removed.

### Prelaunch test

- validate demand and user need with a small cohort;
- inspect source-data accuracy, rights, freshness, and missingness;
- prevent empty, duplicate, nonsensical, or privacy-sensitive combinations;
- design filters/facets separately from indexable landing pages;
- ensure unique titles are a consequence of unique page value, not the only difference;
- add editorial/algorithmic QA and abuse controls;
- expose only stable URLs with coherent canonicals and links;
- measure indexation, engagement, conversions, and quality complaints by cohort.

### UGC

Implement moderation, spam detection, author/reputation context, reporting, link attributes, privacy handling, legal escalation, and empty/thin-thread lifecycle rules. Do not mark all UGC as expert content or expose harmful/private material for visibility.

### Scale gates

Expand only when the pilot shows:

- valid pages remain above the quality gate;
- crawl/index behavior is controlled;
- users complete meaningful tasks;
- conversions or strategic outcomes justify maintenance;
- abuse/support load is manageable.

Pause or `noindex` weak cohorts before adding more inventory. Never use scaled generation primarily to manipulate rankings.

## Migrations and redesigns

Treat migrations as change control, not a launch-day checklist.

### Inventory and baseline

Capture:

- all known URLs from CMS, crawl, sitemaps, GSC, analytics, backlinks, logs, and paid/owned campaigns;
- status, canonical, directives, hreflang, structured data, internal links, traffic, conversions, and backlinks;
- top templates and business-critical journeys;
- current field performance and crawl behavior.

### URL map

For every old URL choose:

- unchanged;
- permanent redirect to a true equivalent;
- consolidated into a documented destination;
- intentionally removed with `404`/`410`;
- retained temporarily;
- unresolved owner decision.

Reject bulk homepage redirects and long chains. Preserve query/path behavior only where needed.

### Prelaunch gates

- production-like crawl of staging with access controls that will not leak;
- robots/meta/header environment rules reviewed;
- old-to-new redirects tested automatically;
- canonicals/hreflang/sitemaps/internal links use final production URLs;
- raw/rendered parity and key journeys tested;
- analytics/consent/conversions verified;
- structured data and feeds verified;
- performance budgets met;
- CDN/cache/error behavior tested;
- DNS/TLS/rollback/runbook/owners ready.

### Launch and monitoring

- remove staging blocks only on the correct production release;
- deploy redirects before or with new URLs;
- submit updated sitemaps only when authorized;
- monitor availability, redirects, errors, logs, indexing, traffic, and conversion cohorts;
- keep redirects for as long as users and references need them;
- annotate all systems;
- use predefined rollback thresholds.

Avoid combining domain, CMS, URL, content, design, and analytics changes when they can be staged; simultaneous changes make diagnosis harder.

## Multi-site and enterprise governance

### Define ownership

Create:

- domain/subdomain inventory;
- template/platform inventory;
- page-type and locale owners;
- release and incident contacts;
- source-of-truth content/data systems;
- exception process;
- audit and monitoring cadence.

### Guardrails as code

Where practical validate in CI:

- forbidden production `noindex`/robots rules;
- required canonical/directive behavior by template;
- redirect-map conflicts, loops, and missing destinations;
- hreflang cluster integrity;
- sitemap URL eligibility;
- structured data syntax and data-source agreement;
- title/H1 presence as content QA, not ranking dogma;
- broken internal links;
- performance budgets;
- analytics and consent hooks;
- accessibility basics.

### Rollout

Use cohort releases, feature flags, canaries, and template-level before/after monitoring. Maintain a decision log so later teams understand why a crawl/index policy exists.

### Portfolio decisions

Assess overlap among domains/subdomains by audience, purpose, authority, operations, and legal requirements. Do not consolidate properties merely because one domain has a higher third-party authority metric.
