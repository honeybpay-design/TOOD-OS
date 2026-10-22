# Cadence style guide

Cadence is a dark, cinematic SaaS marketing site: a cool charcoal ground,
grey-to-white gradient headlines lit by faint diagonal light shafts, one cyan
accent that reads as energy, and the product itself as the hero image. Depth
comes from 3D perspective (the tilting product card, the icon chips, the
MacBook lid) and from light inside surfaces, never from busy color.

The page must read as one continuous product story: the same fictional
workspace, the same customers and the same roadmap item travel from the hero
inbox, through the feature vignettes and the workflow stage, into the customer
story and the CTA screen. A generic dashboard that ignores the story is a failed
output.

## Tokens

Define once on `:root` (see the top of `template.html`). Cadence is dark-only;
do not add a light theme.

| Token | Value | Role |
| --- | --- | --- |
| `--bg` | `#08090b` | page ground (cool charcoal) |
| `--bg-raise` / `--surface` / `--surface-2` / `--surface-3` | `#0b0d10` / `#0f1216` / `#14181d` / `#1a1f25` | raised grounds, inputs, muted buttons |
| `--line` / `--line-2` / `--line-3` | `rgba(226,236,245,.075 / .12 / .2)` | hairlines, card borders, hover borders |
| `--text` | `#eef2f5` | headings, key numbers |
| `--text-2` | `#a9b3bc` | body and ledes (9.3:1 on `--bg`) |
| `--text-3` | `#78838d` | meta, captions (5:1 on `--bg`; never for paragraphs) |
| `--accent` | `#4cc4ea` | the one accent: primary buttons, active states, chart strokes |
| `--accent-hi` | `#6fd2f1` | primary button hover |
| `--accent-text` | `#8fdcf5` | accent used as text on dark (tags, deltas, links on hover) |
| `--accent-ink` | `#031219` | text on accent fills |
| `--accent-soft` / `--accent-line` | `rgba(76,196,234,.1 / .34)` | selected chips, tag fills and borders |
| `--ok` / `--warn` / `--neg` | `#6cc59a` / `#d8b064` / `#df8080` | product-UI semantics only (tags, health), small sizes |
| `--star` | `#f0c75e` | rating stars only |

Rules:

- **One accent.** Cyan is the only working color for page chrome. Semantic
  greens, ambers and reds appear only inside product UI, small and muted.
- **Neutrals are tinted cool**, never pure grey, and never pure `#000`/`#fff`.
- **No purple.** No violet, indigo-violet or lavender (hue 235-300) anywhere:
  not in backgrounds, glows, gradients, headline words or accent fills, and not
  in avatar fills either. Avatar and initials tiles use teal, steel blue, pine,
  slate and amber (`#2b6a86`, `#3f5f8a`, `#3f7a64`, `#3a5f6b`, `#8a6330`, each
  to a darker partner). The hero has no colour wash or glow behind it: only the
  three diagonal light shafts on the charcoal ground.
- Cards sit barely above the ground: a translucent vertical gradient, a
  1px `--line` border and the `--inset` inner light. Elevation is light from
  within. Only devices (tilt card, workflow frames, MacBook) and dialogs get
  the stacked `--shadow-cine` / `--shadow-2`.

## Type

Fonts are **Geist** (sans, variable 100-900) and **Geist Mono** (labels, data,
code, variable). The template loads them from the fontsource CDN with two
`@font-face` rules. In a framework project install
`@fontsource-variable/geist` and `@fontsource-variable/geist-mono` or use
`next/font/google` (`Geist`, `Geist_Mono`); for the standalone single-file
deliverable run `scripts/inline-assets.mjs`, which embeds both woff2 files as
data URIs, so the page makes no network requests. Never load a remote font
stylesheet.

| Role | Size | Weight / tracking / leading |
| --- | --- | --- |
| Display (hero H1) | `clamp(2.5rem, 7.2vw, 6rem)` (96px at 1440, 40px on phones) | 600, `-0.045em`, 1.05, `1.5rem` block padding, max 64rem so it breaks into two lines on desktop ("Close the loop on every / piece of feedback"); `text-wrap: balance` only under 640px. Never larger than 6rem. |
| H2 | `clamp(2rem, 1.3rem + 2.55vw, 3.2rem)` | 540, `-0.035em`, 1.06 |
| H3 / card titles | `clamp(1.2rem, 1.08rem + .45vw, 1.45rem)` or 1.14rem | 560-580, `-0.015em` |
| Lede | `clamp(1.0625rem, 1rem + .3vw, 1.2rem)`; hero lede `clamp(1rem, 1.6vw, 1.25rem)` | 400, 1.55 (hero 1.5), max 40rem (hero 48rem, two lines) |
| Body | 1rem | 400, 1.6, max 65ch |
| Label (mono) | .72rem uppercase | `.08em` tracking, `--text-3` |
| Product UI | 11-13.5px | dense, tabular numbers |

- **Signature gradient clip** (`.grad`): `linear-gradient(180deg, #77828c 0%,
  #c6ced5 34%, #f3f6f8 62%)` with `background-clip: text`. The top line reads
  darker than the bottom; that fade is the style's identity. Use it on the H1
  and every H2, nowhere else.
- Spotlight quotes use the horizontal silver variant (edges `#9aa5ae`, center
  `#f3f6f8`).
- Numbers in data use `font-variant-numeric: tabular-nums`.
- Use mono labels sparingly: at most one small-caps label per three sections
  (the customer story label, workflow step keys, integration headers).

## Layout and rhythm

- Container `min(100% - 2 * var(--gutter), 1240px)`, gutter
  `clamp(16px, 4vw, 40px)`, section padding `clamp(88px, 11vw, 160px)`.
- Vary compositions; never stack identical "centered title + three cards"
  blocks. The template's families: centered hero + device, marquee, 6-column
  bento (4+2 / 2+2+2), sticky split story, spotlight over a wall, split image
  card, 7/5 two-panel, four-column pricing, 4/7 sticky-aside accordion, CTA
  split + device.
- Section headers: the 3D icon chip appears only above product, customers and
  pricing. Workflow, security and FAQ use left-aligned headers without a chip.
- Radius scale: controls `10px`, small UI `6-10px`, cards `18px`, frames and
  devices `22-26px`, chips and the nav `999px`.
- Mobile is designed, not squashed: every multi-column block declares its
  fallback under 960/720/620px, the workflow stage becomes tabs, the product
  UI drops its sidebar and detail pane.

## Components

- **Pill nav**: fixed, centered 940px pill. At the top the brand and actions
  sit at the page edges (`--spread`, transform only); after 40px of scroll they
  glide together and the blurred pill background fades in. Active section gets
  a short cyan underline. Under 960px: brand + primary CTA + menu button that
  opens a focus-trapped sheet (Esc and scrim close it).
- **Buttons**: primary = solid `--accent`, `--accent-ink` text, inset white top
  highlight and a soft cyan underglow; ghost = 3.5% white fill + `--line-2`
  border; muted = `--surface-3`. 46px default height (38 small, 52 large), radius
  10px, `scale(.97)` on press, loading spinner and disabled states.
- **3D icon chip**: 46px, `rotateX(24deg)` in 420px perspective, gradient bezel,
  charcoal face, cyan glyph, blurred underglow and a cyan hairline at its base.
- **Hero** (keep it this restrained): centered H1, two-line lede, a proof row
  (five 56px customer headshots, cover-cropped, with a 2px light border, alternating -4..5deg
  tilts and 16px overlap, five `--star` stars, one line "Trusted by ..." in
  `--text-2`), one primary CTA (48px), then the tilt card. No announcement
  pill, no second button, no stat strips, chips or glows. Hero padding-top
  `8.5rem` puts the H1 box at 136px on every width; the device's top edge
  lands about 800px down at 1440x900, so only its top strip shows in the
  first screen.
- **Tilt card**: 72rem (1152px) product frame, radius 26px, gradient bezel,
  cinematic shadow, `perspective: 1000px`, centre origin; starts at
  `rotateX(20deg)` and eases upright with scroll; a meteor travels its top
  edge; the bottom 38% fades into the ground.
- **Product UI kit** (`.app`, `.win`, `.fb-row`, `.tag`, `.pill`, `.kpi`,
  `.trow`, `.rc`, `.mrow`): real states, real numbers, real names, all fictional.
  Interior text is never lorem ipsum and never a generic "Dashboard".
- **Forms**: label above input, 52px inputs, inline error below with an alert
  icon, helper text, loading button, success panel with a reset action.
- **Dialog**: centered, scrim with blur, focus trap, Esc, returns focus.
- **Toasts**: bottom center, 3.8s, used for subscriptions.

## Imagery

The hero image is the product, built in HTML/CSS/SVG. Photography appears only
where a real company site would use it: customer portraits in the spotlight and
an editorial customer-story photo (plus its detail shot). One art direction:
low-key cinematic, graphite and charcoal, one faint cyan practical light, 50mm,
fine grain, no screens, no text. See [image-plan.md](image-plan.md).

## Voice

Confident, concrete, short. The headline names the outcome ("Close the loop on
every piece of feedback"), not the category. Ledes are one sentence of 20 words
or fewer. Feature blurbs name a specific moment. Numbers are specific and
attributed ("50 min weekly triage, down from 9 hours" in a named customer
story), never inflated platform-wide claims. The hero proof line may carry
one customer count ("Trusted by 24,000+ product teams"): use a figure the
user supplies, or mark an invented one for the user to confirm. Hero H1:
about 38-46 characters with the first line no longer than about 24, so it
renders as two lines at 1440 (check it). No exclamation marks, no em
dashes, no "seamless/elevate/unleash". One CTA label per intent across the
page: "Start free" (sign-up), "Talk to sales" (contact), "Sign in".

## Do and don't

| Do | Don't |
| --- | --- |
| Re-theme every product screen to the user's product | Leave the feedback-tool content in a different product |
| Keep one workspace and one roadmap item threading through the page | Show unrelated KPI cards in each section |
| Use invented wordmarks with simple SVG marks | Use real company logos or claims about real customers |
| Generate portraits with one consistent backdrop and light | Mix stock photos with different lighting, or use initials-only people in the spotlight |
| Keep content visible without JS; reveal under `.js` | Ship text at `opacity: 0` waiting for a script |
| Animate transform, opacity, clip-path | Animate width, height, top, left |
