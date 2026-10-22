---
name: bs-cadence-marketing-landing
description: Generate a dark, motion-rich SaaS marketing landing page in the cadence style, with a charcoal ground, one cyan accent, gradient headlines, faint diagonal light shafts and believable CSS product UI. The page tells one continuous product story, from a pill nav and a hero product card that tilts upright on scroll, through animated feature vignettes, a scroll-driven workflow stage, a customer spotlight with portraits, integrations and security, four-tier pricing with a billing switch, FAQ and a sign-up CTA ending in a scroll-opening CSS MacBook, plus changelog, customer story, sign-in and legal routes. Use it when a founder, marketer or product team wants a distinctive dark launch page or a complete product site with focused calls to action. Standalone output is one self-contained HTML file with embedded fonts and images that runs from disk and in a sandboxed iframe; inside a user's project, generate the same visual grammar in its own stack.
---

# Cadence Marketing Landing

Build a **dark, motion-rich SaaS marketing site** in the cadence style: cool
charcoal ground, one cyan accent, grey-to-white gradient headlines, faint
diagonal light shafts, and the product itself as the hero image, rendered as
rich CSS product UI that tilts upright on scroll. The whole site reads as one
continuous product story with focused calls to action, and works as a real
front end someone can ship: complete navigation, working pricing, forms with
validation and success states, a changelog, a customer story, sign-in and
legal pages.

Every output **starts from [references/template.html](references/template.html)**.
It is the working blueprint: tokens, fonts, the sprite, the pill nav, the hero
product UI, the bento vignettes, the sticky workflow stage, the spotlight, the
pricing switch and compare table, the FAQ, the forms and dialog, the MacBook,
the router and inner routes, and the reveal and motion system. Its content is
a fictional worked example (Loopwright, a feedback tool, and its customer
workspace Fernhold). Do not re-derive the CSS or JS; replace content at the
`REPLACE` comments, in the `SITE` constants at the top of the script and in
its data arrays (`FEED`, `INCOMING`, `WALL`, `SPOT`, `CODE`, `CMP`, `CL`),
then work through the **Replace checklist** below, and re-theme every
product screen.

## References

- [style-guide.md](references/style-guide.md): tokens, type scale, layout rhythm, component anatomy, voice, do and don't.
- [section-library.md](references/section-library.md): home sections in canonical order, inner routes, router rules.
- [image-plan.md](references/image-plan.md): art direction, the image slots, prompts, crop rules.
- [motion-system.md](references/motion-system.md): motion tokens, what moves and why, reveal pattern, reduced motion.
- [icon-library.md](references/icon-library.md): sprite pattern, glyph table, wordmarks, people.
- [quality-checklist.md](references/quality-checklist.md): the pre-delivery checklist.
- `references/images/`: the demo photos the template points to; which ones may be reused is under **Adapting to a real brief**.
- Fonts: Geist (variable) and Geist Mono (variable). The template loads them from the fontsource CDN. In a framework project install `@fontsource-variable/geist` and `@fontsource-variable/geist-mono` or use `next/font/google` (`Geist`, `Geist_Mono`); for the standalone single-file deliverable run `scripts/inline-assets.mjs`, which downloads and embeds both woff2 files as data URIs, so the page makes no network requests.
- Scripts: `scripts/inline-assets.mjs` (builds the single file) and `scripts/validate-cadence.mjs` (checks it, including sample leftovers).

## Workflow

1. **Gather the story.** Product name and what it does; the outcome-first
   headline; one example customer workspace (the customer using the product) and one
   flagship request that will travel through the page; 4-5 capabilities for
   the bento; three or four workflow moves; two or three spotlight customers
   plus four to eight short wall quotes; one customer story with three specific,
   attributed numbers; integrations and security facts the product can
   honestly claim; pricing (two to four tiers; monthly and yearly when offered); 6-10 FAQ
   pairs; 6-9 changelog entries. Draft missing copy in the cadence voice
   (style guide, "Voice") and map the brief with **Adapting to a real brief**
   below. For a real business, facts come from the brief; anything you have
   to invent (quotes, customer names, wordmarks, metrics, prices, dates) is
   plausible placeholder copy that you list in your final reply. Never use
   real logos or claims about real customers, and never invent
   certifications, awards or security claims.
2. **Choose the deliverable.** No existing project: build **one
   self-contained HTML file** from the template, like the store demo. This is
   the default; do not ask a stack question. The user has a framework project
   or asks for one: inspect it first, preserve unrelated files, detect React/Next,
   Vue/Nuxt, Svelte, Astro or plain HTML from `package.json` and config, and
   build the same sections as components: tokens in the project's styling
   system, Geist and Geist Mono from `@fontsource-variable/geist` and
   `@fontsource-variable/geist-mono` (or `next/font/google`), Lucide components for icons,
   the router replaced by real routes, the scroll effects as small utilities.
   Every rule below still holds.
3. **Read the style guide and section library** before writing markup. Pick
   sections in canonical order; nav, hero, CTA and footer always ship. Keep at
   least one inner route (changelog or customer story) when the product has
   the content for it. Keep the hero restrained: two-line gradient H1 at 96px
   (40px on phones), a two-line lede, the proof row and one primary CTA above
   the tilt card, with nothing added (no announcement pill, second button,
   chips or glow) and no purple anywhere on the page.
4. **Plan the imagery** with [image-plan.md](references/image-plan.md): the
   hero is product UI, never a photo. Photos fill only the role-based slots
   (three spotlight portraits, the story editorial, the story detail and the
   five small hero proof-row headshots), all in the one art direction. Write
   the plan (id, role, aspect, crop focus, prompt) before generating;
   generate with the host's image tool, check every result for artifacts,
   text and bad crops, and regenerate misses. Save WebP
   at the slot widths into `images/`. If no image tool exists, keep initials
   avatars and tell the user which slots need photos.
5. **Copy the template and fill it.** Copy `references/template.html` to
   your own source file (for example `site/index.src.html`) with the images
   you use in `site/images/`. Replace every `REPLACE` slot, the `SITE`
   constants and every data array, then the **Replace checklist**. Re-theme the product UI completely: workspace, sidebar, rows, tags,
   detail pane, bento vignettes, workflow screens, roadmap, digest, MacBook
   screen. Keep the flagship request consistent everywhere it appears. Delete
   unused sections and their nav and footer links, then delete every
   `REPLACE` comment.
6. **Keep the motion system** ([motion-system.md](references/motion-system.md)):
   content visible without JS (`.js .rv` reveals with the in-view safety net),
   hero entrance on load, scroll-linked tilt card and MacBook lid, vignettes
   that run only on screen, pausable spotlight, count-ups once, and a complete
   `prefers-reduced-motion` path. Animate transform and opacity only.
7. **Keep it usable.** Every link resolves to a section or route; pricing
   toggle, compare disclosure, FAQ, tabs, mobile menu, dialog, sign-up,
   newsletter, changelog filters/search and sign-in all work with inline
   validation, loading, success and empty states.
8. **Build the standalone file**:
   `node scripts/inline-assets.mjs site/index.src.html site/index.html`
   inlines `images/` and the two fontsource CDN fonts (downloaded once at
   build time) as data URIs, and embeds each repeated image only once (its
   first `<img>` carries the data and `data-imgkey`; repeats copy it at load
   through a three-line script). Target 5 MB or less, hard cap 8 MB.
9. **Validate**: `node scripts/validate-cadence.mjs site/index.src.html --source`
   while you work (relative images and the CDN fonts allowed), then
   `node scripts/validate-cadence.mjs site/index.html` on the built file. A
   deployed site that keeps `images/` and `fonts/` beside the page uses
   `--files`; `--template` is only for the blueprint. It fails on remote
   requests, unsafe sandbox APIs, emoji and dingbats, leftover `REPLACE`
   slots, missing structure (home and 404 routes, one h1 per route, every
   anchor and route link resolves, labelled inputs), 2-4 pricing tiers,
   missing `alt`, missing reduced-motion or focus styles, oversize files, and
   any name left over from the sample (Loopwright, Fernhold, its people and
   customer companies). For a framework port run its own build and lint.
10. **Review in a browser** at 1440, 1024, 768 and 390 px, with the
    [quality checklist](references/quality-checklist.md): watch the tilt card
    stand up, a live inbox row arrive, the workflow stage change screens, the
    spotlight rotate and pause, the billing switch, the compare table, two FAQ
    items, the MacBook lid, the mobile menu and tabs, every form's error and
    success state, and each route loaded cold from its hash. Check the console
    and horizontal overflow. Fix what you see, then review again.

## Adapting to a real brief

- **Counts flex; the grammar does not.** Pricing takes two to four tiers:
  four is the default grid; three: delete one `.tier`, set `data-count="3"`
  on `.tiers`, drop its compare column (`<th>` and the `CMP` column); two:
  `data-count="2"` (section library, section 8). Only monthly prices: derive
  yearly as 10 x monthly and say so. Bento: five cards (`.b-wide` + `.b-third`,
  then three `.b-third`) or four (`.b-wide`, `.b-third`, then `.b-third`,
  `.b-wide`: give the last card `b-wide` instead of `b-third`). Wall
  quotes: four to eight. Spotlight: two or three (one `.t-pill` per `SPOT`
  entry). Workflow: three or four steps (one `.step`, one `.screen` and one
  `.story-tabs` tab each).
  FAQ six to ten; changelog any number. Marquee six to eight wordmarks.
- **Map the sections to the product.** The bento vignettes are generic
  moves (many inputs into one hub, automatic classification, a metric
  trending, a handoff between named people, two records compared): an
  on-call tool maps them to alert sources, severity detection, MTTA trend,
  escalation level 1 to 2 and status-page cards; an invoicing tool to bank
  feeds, receipt matching, days-sales-outstanding, approval handoff and two
  client accounts. The hero inbox becomes the product's main list (alerts,
  invoices, tickets) with the same row anatomy. A product without a public
  changelog keeps the customer story route, or the reverse; delete the unused
  route, its nav link and footer link.
- **Phones hide by class.** `.m-hide` marks the KPI, roadmap lane and table
  column dropped under 640px; move it to your least important ones, never
  onto the lane or row that carries the story's highlighted (`.hl`) card.
- **Real facts only.** For a real business, testimonials, customer names and
  logos, metrics, team, prices, dates, integrations and security facts come
  from the brief. Anything missing is drafted as plausible placeholder copy
  and listed in your final reply for the user to confirm or replace,
  including the proof-row customer count. Rewrite the legal and security
  route from the user's facts: no invented SOC 2, ISO, HIPAA, GDPR or uptime
  claims, awards or certifications.
- **People photos.** If the site shows real people (founders, real
  customers), ask for their photos. Generated portraits, including the
  shipped `portrait-*` and `ava-*` files, are stand-ins: say so.
- **Shipped images.** Reusable as stand-ins with new names (generic studio
  portraits on the graphite backdrop): `portrait-amara`, `portrait-tomas`,
  `portrait-ingrid`, `ava-jonas`, `ava-dev`, `ava-elena`, `ava-mei`,
  `ava-priscilla`. Sample-specific, regenerate for any other product:
  `story-team` (a team at a wall of feedback index cards) and `story-detail`
  (hands sorting index cards). Priority when the image budget is short is in
  image-plan.md.
- **Deliverable.** No project: the single HTML file built with
  `scripts/inline-assets.mjs` (fonts and images as data URIs, safe in a
  sandboxed preview). A normal deployed site may keep `images/` and the font
  files beside the page (validate with `--files`). A framework project: port
  per step 2 with local image and font files.
- **The hero copy changes, its anatomy does not.** New H1 (about 38-46
  characters, two lines at 1440), two-line lede, proof row and one CTA; same
  sizes, same tilt card.

## Replace checklist

Strings outside the data arrays; the validator names any sample leftover.

- `<title>`, meta description, `og:*` tags and `og:url` (the sample domain).
- `SITE` in the script: `brand` (tab titles), `homeTitle`, `storySlug` (the
  customer story route, also in every `href="#/customers/..."` link) and the
  two subscription toasts. The story tab title comes from the story's h1.
- Brand mark and wordmark in the nav and footer, the nav `aria-label`, the
  footer copyright line and status line.
- The hero product UI markup: workspace switcher, sidebar user (name and
  portrait), saved views, detail pane, and `#inboxCount` (the live counter
  starts from its text).
- The install snippet (`data-workspace`, script name), webhook payloads in
  `CODE`, the digest email (`From` line and address), MacBook screen.
- Spotlight markup (`#spotImg`, `#spotCite` and the `.t-pill` names) must
  match `SPOT[0]`; the sign-in quote; the story route's facts, prose, pull
  quote and stats.
- The marquee label and wordmarks; the triage vignette's cursor name.
- Legal route: company name, dates, hosting regions, subprocessors.

## Constraints

- Standalone deliverables are one HTML file: no frameworks, CDN scripts,
  remote stylesheets, font services or remote images. Fonts and images are
  embedded as data URIs (a deployed site may keep them as local files beside
  the page).
- Sandbox-safe when the page is previewed inside a sandboxed iframe (a
  single-file demo): no `fetch` or other network APIs, no `alert`/`confirm`/
  `prompt`, no `window.open`, no top navigation; storage only inside
  try/catch with an in-memory fallback (the template needs none). A deployed
  site or framework project does not need these restrictions.
- Dark only. One cyan accent for page chrome; muted semantic colors only inside
  product UI.
- Typography is Geist and Geist Mono, loaded as described under References:
  fontsource CDN in the template, fontsource packages or `next/font/google` in
  a project, embedded data URIs in a standalone file. Swap only when the user
  supplies a brand face, and load it the same way.
- No emoji or Unicode dingbats; icons are inline SVG in Lucide grammar.
- English copy by default; switch only when asked. No em dashes, no lorem
  ipsum, no inflated claims.
