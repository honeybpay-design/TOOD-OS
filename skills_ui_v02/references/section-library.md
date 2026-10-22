# Cadence section and route library

The template is a hash-routed single file: a full home page plus four inner
routes and a not-found route. Every page ships the nav, the hero and the
footer; pick the rest to fit the story but keep the canonical order, which
alternates product, proof and ask.

## Home route (`#/`), canonical order

| # | Section (id) | Layout family | Keeps |
| --- | --- | --- | --- |
| 1 | Pill nav (`header`) | fixed pill, spread at top | always |
| 2 | Hero (`#top`) | centered copy + 3D tilt product card | always |
| 3 | Customer marquee | single-line marquee | recommended |
| 4 | Product bento (`#product`) | 6-col bento, 4+2 then 2+2+2 | recommended |
| 5 | Workflow story (`#workflow`) | sticky split: steps left, stage right | recommended |
| 6 | Customers (`#customers`) | spotlight over a dimmed quote wall + story card | recommended |
| 7 | Integrations and security (`#security`) | 7/5 two-panel | optional |
| 8 | Pricing (`#pricing`) | billing switch, 4 tiers, compare disclosure | recommended |
| 9 | FAQ (`#faq`) | 4/7, sticky aside + accordion | recommended |
| 10 | CTA (`#start`) | split copy + sign-up form, CSS MacBook below | always |
| 11 | Footer | brand + newsletter, 4 link columns, status | always |

Minimal launch page: 1, 2, 3, 4, 8, 10, 11.

### 1. Pill nav
Brand mark (SVG symbol `#brand`) and wordmark, four or five links (in-page
anchors plus the changelog route), "Sign in" and a primary "Start free". The
active section gets `aria-current` from an IntersectionObserver. Mobile: menu
button opens `.mnav` (focus trap, Esc, scrim, body scroll lock).

### 2. Hero
Centered and restrained, exactly four parts: gradient H1 of about 38-46
characters (first line no more than about 24) that breaks into two lines on
desktop (96px, weight 600; check it at 1440), a two-line lede (20px), a
proof row (five tilted customer headshots, five stars, "Trusted by 24,000+ product
teams") and one primary CTA ("Start free"). No announcement pill, no second
button, no logos, stat strips, chips or feature bullets, no glow behind the
copy. The H1 box starts 136px from the top (`padding-top: 8.5rem`). Below, the **tilt card** holds the full product UI: workspace switcher,
nav with counts, saved views, current user (portrait), toolbar with filter
pills and a search field, a feedback list whose rows are rendered from `FEED`
and joined every 4.2s by a row from `INCOMING` (paused offscreen, on hidden
tabs and under reduced motion), and a detail pane: person, ARR, message, AI
tags, the linked roadmap item, actions.

### 3. Marquee
One sentence label, then six to eight fictional wordmarks, each with its own
weight, tracking, case or style and a simple abstract SVG mark. Edge masks,
46s linear loop, pauses on hover, duplicate set is `aria-hidden`.

### 4. Product bento
Chip + gradient H2 + lede, then five cards, each with an animated vignette
that explains one capability:
- **Channels (wide)**: six source pills wired into an inbox hub; cyan pulses
  travel the wires (SVG dash offset).
- **Tagging**: a message card crossed by a scanning beam; tags appear after.
- **Trend**: line chart that draws once when revealed, a pulsing endpoint, a
  delta pill.
- **Triage**: two columns; a card is dragged across by a named cursor while a
  second cursor hovers.
- **Revenue**: two account cards that swap on hover (ARR, plan, renewal).
Vignettes animate only while the card is on screen (`.playing`).

What each vignette demonstrates, so any product can map onto it:
Channels = many inputs wired into one hub; Tagging = automatic
classification of one item; Trend = one metric moving the right way;
Triage = a handoff between two states by named people; Revenue = two related
records compared on hover. Example for an on-call product: Channels become
alert sources, Tagging becomes severity detection, Triage becomes escalation
from level 1 to level 2, Revenue becomes two status-page uptime cards.

### 5. Workflow story
Left-aligned header. Desktop: four `.step` articles scroll past a sticky
`.story-stage`; the step crossing the viewport center becomes active and its
`.screen` crossfades in; a rail on the left fills with scroll progress.
Mobile (under 960px): the same stage sits on top and a tablist switches steps.
Default screens: Sources (connections, sparklines, install snippet), Themes
(KPIs, ranked themes with inline bars and weekly change), Roadmap (three lanes
with waiting counts and ARR), Loop digest (email preview with merge fields,
recipients, send stats).
Phones (under 640px) drop one KPI, one roadmap lane and the last table
column: they carry the class `.m-hide`. Put `.m-hide` on the least important
KPI, lane and column of your own screens, never on the lane that holds the
highlighted `.hl` card or on the story's key moment.

### 6. Customers
Chip + H2 + lede; a dimmed four-column wall of short quotes (from `WALL`)
masked to a dark center; in front the spotlight: portrait in a rotating conic
halo, stars, quote (from `SPOT`), attribution, three portrait pills with a 7s
progress line (auto-advances, pauses on hover, focus, offscreen and via the
pause button). Then the customer story card: editorial photo, label, H3, three
count-up stats, link to the story route.

### 7. Integrations and security
Left: eight integration categories (generic names, Lucide icons, never real
brand logos) and a tabbed webhook payload code block. Right: five security
facts with icons and a link to the legal route.

### 8. Pricing
Chip + H2 + lede + billing radiogroup (sliding thumb, "2 months free").
Four tiers (Free, Starter, featured Growth with meteor and badge, Enterprise
"Custom" opening the sales dialog). Prices swap from `data-monthly` /
`data-yearly` with a short rise. A note on currency and seats, then a
"Compare all features" disclosure revealing a grouped table rendered from
`CMP`.

Two to four tiers. Four is the default grid. With three plans (the common
case), drop a tier, set `<div class="tiers" data-count="3">` (centred,
1080px; one column under 900px), remove its `<th>` from the compare table
head and its column from every `CMP` row (group rows span the head
automatically); with no Enterprise tier, link "Talk to sales" from the
price note or the FAQ aside (any element with `data-open-contact` opens
the sales dialog).
Two plans: `data-count="2"`. Every switchable element (`.price-num`,
`.price-per`, `.bill-note`) has both `data-monthly` and `data-yearly`. If the
user gives only monthly prices, set yearly to 10 x monthly to match the
"2 months free" badge, show it per year or as the monthly equivalent (for
per-user plans: `.price-per` "per user / month" and "per user / year"), and
tell the user the yearly prices were derived. If there is no yearly plan at
all, remove the billing switch and the `data-*` attributes.

### 9. FAQ
Sticky left aside (H2, one sentence, "Talk to sales"), right accordion of six
to ten items, single-open, grid-rows height animation, plus/x icon.

### 10. CTA
Split: gradient H2 and one sentence left; "Work email" form right with inline
validation, loading and a success panel. Below, the **CSS MacBook**: the lid
rotates from -68deg to upright as it scrolls in; screen shows the product's
results; keyboard generated by script; deck fades into the ground.

### 11. Footer
Brand, one-line description, newsletter form (toast on success); columns
Product, Customers, Company, Legal; bottom row with copyright, a real status
line and two or three SVG icon links that resolve to routes or sections.

## Inner routes

| Route | Content |
| --- | --- |
| `#/changelog` | breadcrumb, H1, subscribe form, filter chips with counts, search, entries rendered from `CL`, empty state with "Clear filters" |
| `#/customers/<slug>` | breadcrumb, label, H1, lede, 21:9 cover photo, sticky facts list, prose with figure, pull quote with portrait, stat cards, closing CTA |
| `#/signin` | split: auth card (email magic link or SSO domain, validation, success) and a photo panel with a customer quote |
| `#/legal[/privacy\|terms\|security\|subprocessors]` | TOC, four sections, subprocessor table; sub-paths scroll to the section |
| anything else | 404 with a link home |

Router rules: `#/...` hashes are routes; plain `#id` hashes are anchors on the
home route (switch to home first when needed). Route changes fade in over
320ms, jump to the top, set `document.title` and move focus to `main`.

## Extras the style supports (on request)

Keep tokens, chips and card anatomy identical:
- **Pricing detail**: the compare table as its own route with an FAQ.
- **Blog index and article**: card grid with editorial photos; a 68ch article
  column with the gradient H1.
- **Contact**: the sales dialog form as a page, with a short process timeline.
