# UI v02 Implementation Plan

**Source design**: `docs/tood.uk.ui.v02/` (index.html, style.css, base.css, app.js)
**Target**: `apps/web/` — Next.js 16 / React 19 / Tailwind CSS v4
**Goal**: Replace the existing marketing page with the v02 design from the reference HTML, keeping the Next.js structure, TypeScript, and all existing routes.

---

## Architecture decisions

- **No new dependencies.** The design is pure CSS + vanilla JS. All animations are reproduced with CSS keyframes in `globals.css`; interactive behaviours become React `useState`/`useEffect` hooks. No canvas library needed.
- **Font strategy**: Tailwind v4 uses `@theme inline` — add fonts via `<link>` tags injected in `layout.tsx` using Next.js `<Head>` equivalent (put them in the `<html>` head via metadata or a `<link>` inside the layout's `<head>` block). Because Cabinet Grotesk and Switzer are on Fontshare (not Google Fonts), they **cannot** use `next/font`. They are loaded via plain `<link>` tags. Instrument Serif and JetBrains Mono are on Google Fonts and also loaded via `<link>` (not `next/font`) to keep all four fonts in a single `<head>` block alongside the Fontshare ones.
- **Canvas glyph animation**: Port as a React `useEffect` in a `GlyphCanvas` client component. The canvas is purely decorative; `aria-hidden="true"` is already on it in the source. Fallback: if `useEffect` hasn't run yet (SSR), the canvas element renders but is invisible — no layout shift.
- **Dark mode toggle**: Store `data-theme` on `document.documentElement`. Use a `useEffect` to read `prefers-color-scheme` on mount and a `useState` for user override. Apply via `document.documentElement.setAttribute('data-theme', mode)`.
- **Pipeline animation** (`#pipe`): Port as a client component `PipelineDemo` with `useEffect`-driven `setTimeout` timers, mirroring the JS loop exactly. `IntersectionObserver` via a `useRef`.
- **Live demo section**: The live demo calls `GET/POST /api/...` endpoints — the existing Next.js rewrites in `next.config.ts` already proxy `/api/:path*` to the FastAPI backend. Keep the same fetch logic, ported to TypeScript.
- **Provenance demo**: Port as a client component `ProvenanceDemo` with React state for active span key, export bar status, and resolved flag.
- **Join form**: Uses `POST /api/waitlist` — already proxied. Port as a controlled React form.
- **page.tsx** is a single `"use client"` file (already is). Keep that pattern.
- **Tailwind**: The v02 design does **not** use Tailwind utilities — it uses custom CSS classes. Do not fight this. Tailwind's `@import 'tailwindcss'` is kept for the few Tailwind utilities used in login/dashboard pages, but the marketing page components use the custom CSS class names from style.css directly.

---

## 1. Font setup

### Font `<link>` tags (go in `layout.tsx` inside `<head>`)

```html
<link rel="preconnect" href="https://api.fontshare.com" crossOrigin="" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
<link href="https://api.fontshare.com/v2/css?f[]=cabinet-grotesk@500,700,800&display=swap" rel="stylesheet" />
<link href="https://api.fontshare.com/v2/css?f[]=switzer@400,500,600,700&display=swap" rel="stylesheet" />
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
```

### CSS variables (already in style.css — copy verbatim into `globals.css`)

```css
--font-display: 'Cabinet Grotesk', 'Switzer', 'Helvetica Neue', sans-serif;
--font-serif:   'Instrument Serif', Georgia, serif;
--font-body:    'Switzer', 'Helvetica Neue', Arial, sans-serif;
--font-mono:    'JetBrains Mono', ui-monospace, Menlo, monospace;
```

---

## 2. `globals.css` — complete replacement

**Replace the entire file** with the following structure (order matters):

### 2a. Font `@import` at the top
Remove the existing Google Fonts `@import` line. Fonts are now loaded via `<link>` tags in `layout.tsx`, so no `@import` needed here for fonts.

### 2b. Keep `@import 'tailwindcss'`
Keep this line so Tailwind utilities still work for login/dashboard pages.

### 2c. Keep `@custom-variant dark (&:is(.dark *))`
Keep for Tailwind dark variant compatibility.

### 2d. Replace `@theme inline` block
Change to only map the tokens that Tailwind components actually use. Remove the old brand palette (`--signal`, `--ink`, `--paper`, etc.) from the Tailwind `@theme inline` block since the v02 design uses its own CSS custom properties directly.

### 2e. Add the complete base reset (from `base.css`)
Paste the entire `base.css` content into `globals.css` inside an `@layer base {}` block. Exact content:

```css
@layer base {
  *,*::before,*::after { box-sizing: border-box; margin: 0; padding: 0; }
  html {
    -moz-text-size-adjust: none; -webkit-text-size-adjust: none; text-size-adjust: none;
    -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility; scroll-behavior: smooth;
    hanging-punctuation: first last; scroll-padding-top: var(--space-20);
  }
  body {
    min-height: 100dvh; line-height: 1.6;
    font-family: var(--font-body, sans-serif);
    font-size: var(--text-base);
    color: var(--color-text);
    background-color: var(--color-bg);
  }
  img,picture,video,canvas,svg { display: block; max-width: 100%; height: auto; }
  ul[role='list'], ol[role='list'] { list-style: none; }
  input,button,textarea,select { font: inherit; color: inherit; }
  h1,h2,h3,h4,h5,h6 { text-wrap: balance; line-height: 1.15; }
  p,li,figcaption { text-wrap: pretty; max-width: 72ch; }
  ::selection { background: oklch(from var(--color-primary) l c h / .25); color: var(--color-text); }
  :focus-visible { outline: 2px solid var(--color-primary); outline-offset: 3px; border-radius: var(--radius-sm); }
  @media (prefers-reduced-motion: reduce) {
    *,*::before,*::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; scroll-behavior: auto !important; }
  }
  button { cursor: pointer; background: none; border: none; }
  table { border-collapse: collapse; width: 100%; }
  a,button,[role='button'],[role='link'],input,textarea,select {
    transition: color var(--transition-interactive), background var(--transition-interactive),
      border-color var(--transition-interactive), box-shadow var(--transition-interactive);
  }
  .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border-width: 0; }
  [hidden] { display: none !important; }
}
```

### 2f. Add the complete design token block (`:root` and theme variants)

Copy the `:root` block from `style.css` verbatim. This includes:

**Spacing/type/radius/transition tokens** (in `:root`):
```css
:root {
  --text-xs: clamp(.75rem, .7rem + .25vw, .875rem);
  --text-sm: clamp(.875rem, .8rem + .35vw, 1rem);
  --text-base: clamp(1rem, .95rem + .25vw, 1.125rem);
  --text-lg: clamp(1.125rem, 1rem + .75vw, 1.5rem);
  --text-xl: clamp(1.5rem, 1.2rem + 1.25vw, 2.25rem);
  --text-2xl: clamp(2.1rem, 1.2rem + 3vw, 4rem);
  --text-hero: clamp(2.9rem, 1rem + 6.2vw, 7.25rem);
  --space-1:.25rem; --space-2:.5rem; --space-3:.75rem; --space-4:1rem; --space-5:1.25rem;
  --space-6:1.5rem; --space-8:2rem; --space-10:2.5rem; --space-12:3rem; --space-16:4rem;
  --space-20:5rem; --space-24:6rem; --space-32:8rem;
  --radius-sm:.3rem; --radius-md:.5rem; --radius-lg:.75rem; --radius-xl:1.1rem; --radius-full:9999px;
  --transition-interactive: 180ms cubic-bezier(.16,1,.3,1);
  --ease-out: cubic-bezier(.16,1,.3,1);
  --content-wide: 1240px;
  --font-display: 'Cabinet Grotesk','Switzer','Helvetica Neue',sans-serif;
  --font-serif: 'Instrument Serif',Georgia,serif;
  --font-body: 'Switzer','Helvetica Neue',Arial,sans-serif;
  --font-mono: 'JetBrains Mono',ui-monospace,Menlo,monospace;
  --ink: #0f1215; --ink-2: #161a1e; --ink-3: #1e2328; --ink-text: #e9e7e1;
  --ink-muted: #9ea3a8; --ink-line: oklch(.95 .01 80 / .1);
  --mint: #3fd3a0;
}
```

**Light theme tokens** (`:root, [data-theme='light']`):
```css
:root, [data-theme='light'] {
  --color-bg: #f4f2ec; --color-surface: #faf9f5; --color-surface-2: #ffffff;
  --color-surface-offset: #ebe8e0;
  --color-divider: oklch(.25 .01 80 / .10); --color-border: oklch(.25 .01 80 / .16);
  --color-text: #14161a; --color-text-muted: #575b61; --color-text-faint: #8d9095;
  --color-text-inverse: #f7f6f2;
  --color-primary: #0a7a5a; --color-primary-hover: #07624a; --color-primary-active: #054a38;
  --color-primary-highlight: #d1ebe0;
  --glyph: 20,22,26;
  --p-human: #2c5a86; --p-human-bg: #dde7f1;
  --p-ai: #8a5a00; --p-ai-bg: #f5e7c6;
  --p-evidence: #0a7a5a; --p-evidence-bg: #d1ebe0;
  --p-tender: #8a3f2a; --p-tender-bg: #f1dcd2;
  --p-flag: #b0233a; --p-flag-bg: #f8d8dc;
  --shadow-sm: 0 1px 2px oklch(.25 .02 80 / .06);
  --shadow-md: 0 8px 24px oklch(.25 .02 80 / .08);
  --shadow-lg: 0 30px 80px -20px oklch(.25 .02 80 / .25);
}
```

**Dark theme tokens** (`[data-theme='dark']` AND `@media (prefers-color-scheme:dark) :root:not([data-theme])`):
Copy verbatim from `style.css` — includes `--color-bg:#0f1215` through `--p-flag-bg:#401e24`.

### 2g. Add ALL component CSS from `style.css`

Paste the **entire contents of `style.css`** (after the token block) directly into `globals.css`. This is about 600 lines. Do not wrap in `@layer` — these are component classes that must not be reordered by Tailwind's layer system.

### 2h. Keyframe animations needed

These are already inside `style.css` and will come over automatically. For reference, the full list:
- `@keyframes ping` — announcement dot pulse
- `@keyframes rise` — hero headline word animation
- `@keyframes scan` — pipeline scan line
- `@keyframes travel` / `@keyframes travelv` — pipeline link dot
- `@keyframes marq` — marquee scroll
- `@keyframes spin` — stage spinner
- `@keyframes shimmer` — empty state skeleton
- `@keyframes rin` — result list item entry
- `@keyframes swap` — inspector panel fade
- `@keyframes reveal` — (already exists; rename old `reveal` in globals if needed, or reconcile; the v02 `.reveal` pattern uses IntersectionObserver adding `.is-in` class, not a direct animation)

### 2i. Utility classes to add (not in style.css)

These are used in the HTML but not defined — they're semantic helpers:
```css
/* Used by Next.js Link components that need the button pill style */
.btn--nav-ghost { /* inherits .btn .btn--ghost */ }
```
No new classes required; all utilities are covered by `style.css`.

---

## 3. `layout.tsx` changes

**Full rewrite** of `apps/web/app/layout.tsx`:

### Metadata
```ts
export const metadata: Metadata = {
  title: 'tood.os — Every word in your bid, accounted for',
  description: 'tood.os reads the whole tender pack, verifies every requirement against its source by code, and drafts answers where every sentence records who wrote it, which model, what evidence and who approved it.',
  icons: {
    // SVG favicon — inline data URI matching the source
    icon: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect x='4' y='4' width='24' height='24' rx='5' fill='none' stroke='%2314161a' stroke-width='2.4'/%3E%3Cpath d='M10 12h12M10 17h7' stroke='%2314161a' stroke-width='2.4' stroke-linecap='round'/%3E%3Ccircle cx='21.5' cy='21.5' r='3' fill='%230a7a5a'/%3E%3C/svg%3E",
  },
  openGraph: {
    title: 'tood.os — Every word in your bid, accounted for',
    description: 'Verifiable, evidence-bound AI for UK SMEs bidding for public contracts under the Procurement Act 2023.',
    url: 'https://tood.uk',
    siteName: 'tood.os',
    locale: 'en_GB',
    type: 'website',
  },
};
```

### Fonts
Remove `DM_Serif_Display` and `Inter` imports from `next/font/google`. Instead, inject font `<link>` tags directly in the `<head>`. In Next.js App Router, this is done by returning them from a `<head>` element inside the root layout:

```tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-GB">
      <head>
        <link rel="preconnect" href="https://api.fontshare.com" crossOrigin="" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://api.fontshare.com/v2/css?f[]=cabinet-grotesk@500,700,800&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://api.fontshare.com/v2/css?f[]=switzer@400,500,600,700&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

Remove the `className` prop on `<html>` (no more font variable classes needed). Remove `h-full` and hardcoded inline styles from `<body>` — body styling is now handled by `base.css` in `globals.css`.

### JSON-LD script
Add the schema.org structured data as a `<script type="application/ld+json">` tag in the `<head>` block, matching the source HTML:
```json
{"@context":"https://schema.org","@type":"SoftwareApplication","name":"tood.os","applicationCategory":"BusinessApplication","description":"Verifiable, evidence-bound AI workspace for UK public-sector tenders.","offers":{"@type":"Offer","price":"0","priceCurrency":"GBP"}}
```

---

## 4. `page.tsx` — complete rewrite

**Replace the entire file.** Keep `"use client"` at the top. The file is a collection of React components that map 1:1 to the HTML sections.

### Component list (top to bottom, matching index.html structure)

#### 4.1 `SkipLink`
```tsx
<a className="skip" href="#main">Skip to content</a>
```
No state needed.

#### 4.2 `AnnouncementBar`
```tsx
<div className="announce">
  <div className="wrap announce__in">
    <span className="announce__dot" aria-hidden="true" />
    <span>Live now: run the requirement verifier on a real tender PDF.</span>
    <a href="#live">Try it</a>
  </div>
</div>
```
No state needed. The `announce__dot` ping animation is CSS-only.

#### 4.3 `Header`
State: `isScrolled: boolean` (from `useEffect` scroll listener), `theme: 'light'|'dark'` (useState + localStorage).

```tsx
<header className={`header${isScrolled ? ' is-scrolled' : ''}`} id="top">
  <div className="wrap header__in">
    {/* Brand logo SVG */}
    {/* Nav links: #live, #inspect, #standard, #record, #pricing */}
    {/* Actions: theme toggle icon-btn, ghost btn, primary btn */}
  </div>
</header>
```

Theme toggle: `useEffect` on mount reads `prefers-color-scheme`, sets `document.documentElement.setAttribute('data-theme', mode)`. Button toggles between sun/moon SVG icons.

Sun SVG (show in dark mode):
```
circle cx=12 cy=12 r=5 + rays path
```
Moon SVG (show in light mode):
```
path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"
```

#### 4.4 `HeroSection`
State: none at section level. Children use their own state.

Key elements:
- `<canvas className="hero__canvas" id="glyphs" aria-hidden="true" />` — powered by `GlyphCanvas` component
- `<div className="hero__fade" aria-hidden="true" />`
- `.hero__in` with: pill badge, `<h1 className="hero__h">` with word-split spans (see 4.4a), lede paragraph, CTA buttons, note
- `PipelineDemo` component (see 4.4b)

**4.4a Hero headline word split**
The JS in app.js wraps each word in `<span class="w" style="animation-delay:Xs">`. In React, do this statically:

```tsx
<h1 className="hero__h">
  {['Every', 'word', 'in', 'your', 'bid.'].map((w, i) => (
    <span key={i} className="w" style={{ animationDelay: `${0.08 + i * 0.07}s` }}>{w} </span>
  ))}
  <br />
  <em>
    {['Accounted', 'for.'].map((w, i) => (
      <span key={i} className="w" style={{ animationDelay: `${0.08 + (5 + i) * 0.07}s` }}>{w} </span>
    ))}
  </em>
</h1>
```

**4.4b `GlyphCanvas` component**
This is the most complex piece. Port the `glyphField()` function from app.js as a `useEffect` in a `GlyphCanvas` React component.

```tsx
'use client';
// GlyphCanvas.tsx
import { useEffect, useRef } from 'react';

interface Props {
  id: string;
  className?: string;
  opts?: { rgb?: string; base?: number; band?: string; period?: number };
}

export default function GlyphCanvas({ id, className, opts = {} }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    // Port glyphField() verbatim, replacing `document.getElementById` references
    // with the canvas ref. The themeListeners array is module-level so the
    // theme toggle can call readColor(). Return a cleanup function that cancels
    // the requestAnimationFrame and removes event listeners.

    // ... (full port of glyphField from app.js — ~80 lines)

    return () => { /* cancel raf, remove listeners */ };
  }, [opts]);

  return <canvas ref={ref} id={id} className={className} aria-hidden="true" />;
}
```

The `themeListeners` array needs to be accessible to the theme toggle. Simplest approach: use a module-level array `const themeListeners: Array<() => void> = []` exported from a `theme-store.ts` file, and call its members when the theme changes.

**Fallback**: If the canvas is too complex to port in one go, render a static empty `<canvas>` initially (the CSS positions it behind the content, so the page is usable). The glyph animation is purely decorative.

**4.4c `PipelineDemo` component**

Port the `runPipe()` logic. State: `step: number` (0–2), `running: boolean`, `phase: string`.

The animation has these timed phases:
- t=100ms: `is-run` + card[0] `is-act`
- t=500–2080ms (staggered): page `.hl` items get `on` (4 items × 420ms)
- t=2500ms: card[0] loses `is-act`, link[0] gets `go`
- t=3300ms: card[1] gets `is-act`
- t=3400–4920ms: req items get `on` (5 items × 380ms)
- t=5600ms: card[1] loses `is-act`, link[1] gets `go`
- t=6400ms: card[2] gets `is-act`
- t=6500–8580ms: mini `.m` items get `on` (4 items × 520ms)
- t=8800ms: `is-sealed` + card[2] loses `is-act`
- t=12500ms: cycle repeats

Use `useRef` for all timers. Use `IntersectionObserver` to start the cycle only when the element enters the viewport (threshold 0.3). Use `useRef` for active CSS class sets via DOM manipulation (not React state — too many micro-updates), since the component structure is a direct port of the HTML.

**Approach**: Keep the HTML structure as JSX with `ref` callbacks or `useRef` refs on the container, and do the class toggling via `element.classList` inside `useEffect`. This avoids re-rendering 20+ times per cycle.

#### 4.5 `MarqueeSection`
```tsx
<section className="marquee" aria-label="Documents and requirements tood.os handles">
  <div className="marquee__track">
    <MarqueeSet />
    <MarqueeSet aria-hidden />
  </div>
</section>
```
`MarqueeSet` renders the 12 items. The `marq` keyframe handles the animation — no JS needed.

#### 4.6 `ProblemSection`
Static JSX. No state. The `.reveal` class + IntersectionObserver adds `.is-in`.

Key elements: `.problem` grid with `.problem__quote` (blockquote) and `.problem__facts` (3 `.fact` cards + closing paragraph).

#### 4.7 `LiveDemoSection`
This is the most complex interactive section. Port the entire live demo from app.js.

State:
```ts
type Stage = 'idle' | 'parse' | 'extract' | 'verify' | 'done' | 'error';
interface DemoState {
  busy: boolean;
  stage: Stage;
  elapsed: number; // seconds, for timer
  result: AnalysisResult | null;
  error: string | null;
  filter: string;
  selectedId: string | null;
}
```

The API endpoint is `__API_PORT__` replaced in app.js — in Next.js this is just `/api/analyse-sample?name=riverside` and `/api/analyse` — both proxied by `next.config.ts` rewrites.

The fallback (when API unavailable) fetches `./samples/riverside-result.json`. Place this file at `apps/web/public/samples/riverside-result.json` (copy from `docs/tood.uk.ui.v02/samples/`). Check if the samples directory exists:

```
docs/tood.uk.ui.v02/samples/
```

The section renders:
- `.live__head` — eyebrow + h2 + lede
- `.live__grid` — aside (`.live__side`) + main (`.live__out`)
  - aside: sample button, file drop zone, download link, stages list with timer
  - main: empty state / results / error
  - results: 4 KPI counters, filter chips, requirement list, document text panel

#### 4.8 `ProvenanceDemoSection`
Port the provenance demo. State: `activeKey: string`, `resolved: boolean`, `exportOk: boolean`.

The demo uses a static `DATA` map (port verbatim from app.js). No API calls.

Render the `.demo` card with:
- `.demo__bar` (breadcrumbs + toggle checkbox)
- `.demo__body` — editor + inspector aside
- Inspector panel is rendered from `show(k)` logic — in React, compute the panel JSX from `DATA[activeKey]`

#### 4.9 `StandardSection`
Static JSX. 9 `.rule` articles in a `.rules` bento grid. V1 rule is `.rule--big` (span 2×2), V9 is `.rule--wide` (span 2×1).

The `.rule__viz` inside V1 has 5 provenance type spans — static.

#### 4.10 `AIUseRecordSection`
Static JSX. `.record` grid with copy column and `.paper` card (table + hash chain). The paper has a CSS `rotate(-1deg)` hover effect — CSS-only.

#### 4.11 `ModelAdmissionBand`
`.band` dark section with `.admit` grid. 6 `.test` cards. Static JSX.

#### 4.12 `LimitsSection`
Static JSX. 4 limit items. `.limits` grid.

#### 4.13 `PricingSection`
Static JSX. 3 plan cards. `.plan--feat` is the featured middle card (elevated by `translateY(-12px)` CSS).

The featured card has `.btn--primary` with `background: var(--mint)` — this overrides the normal green primary. Handled by `.plan--feat .btn--primary` rule already in style.css.

Seats counter: `<span id="seatsLeft">30</span>` — static for now.

#### 4.14 `FAQSection`
Port the 5 `<details>`/`<summary>` accordions. In React, `<details>` works natively — no state needed. The `.plus` icon CSS handles the open/close animation via `details[open] .plus`.

#### 4.15 `CTASection` (Join form)
Two parts: `GlyphCanvas` (id=`ctaGlyphs`, opts: `{ rgb: '233,231,225', base: 0.05, band: '#3fd3a0', period: 9 }`) + join form.

Form state: `{ name, email, company, role }` + `{ submitting, message, messageColor }`.

Submit calls `POST /api/waitlist` with JSON body.

#### 4.16 `Footer`
Static JSX. `.footer__in` 4-column grid + `.footer__base`.

### `RevealObserver` — shared utility

Create a `useReveal` hook or a `RevealObserver` component that adds `is-in` to `.reveal` elements when they intersect viewport (threshold 0.12). Add stagger delay based on sibling index. Call this once in the main page component:

```tsx
useEffect(() => {
  const items = document.querySelectorAll('.reveal');
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        (e.target as HTMLElement).classList.add('is-in');
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });
  items.forEach((el, i) => {
    const sib = Array.from(el.parentElement?.children ?? []).indexOf(el);
    (el as HTMLElement).style.transitionDelay = `${Math.min(sib * 60, 360)}ms`;
    io.observe(el);
  });
  return () => io.disconnect();
}, []);
```

### Page component structure

```tsx
"use client";

export default function Page() {
  return (
    <>
      <SkipLink />
      <AnnouncementBar />
      <Header />
      <main id="main">
        <HeroSection />
        <MarqueeSection />
        <ProblemSection />
        <LiveDemoSection />
        <ProvenanceDemoSection />
        <StandardSection />
        <AIUseRecordSection />
        <ModelAdmissionBand />
        <LimitsSection />
        <PricingSection />
        <FAQSection />
        <CTASection />
      </main>
      <Footer />
    </>
  );
}
```

---

## 5. `login/page.tsx` changes

Minimal changes only — preserve all logic, update visual style to match v02 tokens.

Changes:
1. Background: `var(--color-bg)` instead of `#F8F6F1` (same value in light mode)
2. Logo: replace `<img src="/tood logo png.png">` with the inline SVG logo from the design:
   ```tsx
   <svg width="32" height="32" viewBox="0 0 24 24" fill="none" aria-hidden="true">
     <rect x="3.5" y="3.5" width="17" height="17" rx="3.5" stroke="currentColor" strokeWidth="1.8"/>
     <path d="M8 9h8M8 12.5h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
     <circle cx="16" cy="16" r="2.2" fill="var(--color-primary)"/>
   </svg>
   ```
3. Headline font: change from `var(--font-dm-serif)` to `var(--font-display)` (Cabinet Grotesk)
4. Body font: change from `var(--font-inter)` to `var(--font-body)` (Switzer)
5. Google button: update border-radius to `var(--radius-full)` (pill shape, matching `.btn`)
6. Primary action color: change from `#1B4FD8` to `var(--color-primary)` (`#0a7a5a`)
7. Keep all auth logic, error handling, and router redirect unchanged

---

## 6. Samples file

Copy `docs/tood.uk.ui.v02/samples/` to `apps/web/public/samples/`. The live demo fallback fetches `/samples/riverside-result.json` when the API is unreachable.

```
cp docs/tood.uk.ui.v02/samples/ apps/web/public/samples/ (recursive)
```

---

## 7. Build verification

After all changes, run:

```bash
cd apps/api && ruff check .        # API lint
cd apps/web && npx next build      # Frontend build (checks TS + build errors)
```

### Expected TypeScript issues to watch for

1. **`crossOrigin` on `<link>`**: In JSX, use `crossOrigin=""` (empty string) not `crossorigin`. ✓ accounted for in plan.
2. **`aria-hidden`**: Use `aria-hidden="true"` string in JSX. ✓
3. **`GlyphCanvas` opts typing**: Define a `GlyphCanvasOpts` interface to avoid `any`.
4. **`PipelineDemo` DOM refs**: Use `useRef<HTMLDivElement>(null)` for the container, access children via `ref.current.querySelectorAll(...)` in `useEffect`.
5. **`details[open]` CSS selector**: This is standard HTML — works natively in React with no state management needed.
6. **`id` conflicts**: `id="glyphs"` is on the hero canvas, `id="ctaGlyphs"` is on the CTA canvas. Keep both — they're referenced by the `GlyphCanvas` component's `id` prop.
7. **`oklch()` CSS functions**: Supported in all modern browsers, but Next.js build does not transform CSS — this is fine since the reference design already uses them.

### No Next.js Image component needed
The design uses only SVG inline graphics and no `<img>` tags on the marketing page (the logo is an inline SVG). The login page currently uses `<img src="/tood logo png.png">` — the plan replaces this with an inline SVG, so `next/image` is not needed.

---

## 8. Risk items

### 8.1 Canvas glyph animation (HIGH complexity)
**What it does**: Fills the canvas with characters from a string, draws a sweeping light band left-to-right, brightens characters near the mouse cursor, and randomly "highlights" individual characters in colour.

**Port approach**: Direct port of the 80-line `glyphField()` function into a `useEffect`. The function uses `requestAnimationFrame`, `IntersectionObserver`, `ResizeObserver`-equivalent (via `resize` event), and `pointermove`/`pointerleave` listeners.

**Risk**: The `themeListeners` array in app.js is module-level and shared between the two canvas instances. In React, this needs to be a module-level singleton or a React context.

**Recommended approach**: Create `apps/web/app/lib/theme-store.ts`:
```ts
export const themeListeners: Array<() => void> = [];
export function notifyThemeChange() {
  themeListeners.forEach(f => f());
}
```
The `Header` component calls `notifyThemeChange()` when the user toggles the theme. Each `GlyphCanvas` pushes its `readColor` function into `themeListeners` on mount and splices it out on unmount.

**Fallback**: If canvas causes SSR issues, wrap `GlyphCanvas` in a `dynamic()` import with `ssr: false`:
```ts
const GlyphCanvas = dynamic(() => import('./GlyphCanvas'), { ssr: false });
```
This is safe — the canvas is `aria-hidden` and purely decorative.

### 8.2 Pipeline animation timing (MEDIUM complexity)
**Risk**: 20+ `setTimeout` calls per cycle. React StrictMode in development calls `useEffect` twice, which would double-fire the cycle. Fix: cancel all timers in the `useEffect` cleanup function (the plan already accounts for this via `useRef` for timers array).

### 8.3 Live demo API integration (MEDIUM complexity)
**What it does**: `POST /api/analyse-sample?name=riverside` returns `{ job_id }`, then polls `GET /api/jobs/:id` until status is `done`. Falls back to `/samples/riverside-result.json`.

**The API URL** in app.js: `'port/8000'.indexOf('__') === 0 ? 'http://localhost:8000' : 'port/8000'` — this is a placeholder that was never replaced (the substring `'port/8000'` does not start with `__`), so it evaluates to the literal string `'port/8000'` as the API URL. In the Next.js port, use relative URLs (`/api/...`) which are proxied by `next.config.ts`. This actually fixes a bug in the original demo.

### 8.4 Tailwind CSS v4 conflict (LOW risk)
Tailwind v4's `@import 'tailwindcss'` will scan all template files and generate utility CSS. The v02 component classes (`.hero`, `.btn`, etc.) are custom classes defined in `globals.css`, not Tailwind utilities — no conflict expected. However, Tailwind may generate a `.btn` utility class if `btn` matches a Tailwind v4 internal name. Mitigation: all component CSS comes after `@import 'tailwindcss'` in the file, so component styles win in specificity.

### 8.5 `oklch()` color functions with `from` keyword (LOW risk)
The design uses `oklch(from var(--color-primary) l c h / .25)` (relative color syntax). This is supported in Chrome 119+, Safari 17.5+, Firefox 128+. Not supported in older browsers. Since this is a B2B SaaS targeting UK procurement professionals, modern browser support is acceptable. No fallback needed, but note this for QA.

---

## 9. File creation summary

| Action | File |
|--------|------|
| Full rewrite | `apps/web/app/globals.css` |
| Full rewrite | `apps/web/app/layout.tsx` |
| Full rewrite | `apps/web/app/page.tsx` |
| Minimal update | `apps/web/app/login/page.tsx` |
| New file | `apps/web/app/components/GlyphCanvas.tsx` |
| New file | `apps/web/app/lib/theme-store.ts` |
| Copy directory | `apps/web/public/samples/` (from `docs/tood.uk.ui.v02/samples/`) |

No changes to: `next.config.ts`, `package.json`, `tsconfig.json`, any API files.

---

## 10. Ordered implementation steps

- [ ] 1. Copy samples directory and create lib/theme-store
      Files: `apps/web/public/samples/` (copy), `apps/web/app/lib/theme-store.ts` (new)
      Verify: `ls apps/web/public/samples/` shows `riverside-result.json`

- [ ] 2. Rewrite `globals.css` — base reset + all design tokens + full style.css content
      Files: `apps/web/app/globals.css`
      Verify: `cd apps/web && npx next build` — no CSS parse errors

- [ ] 3. Rewrite `layout.tsx` — new metadata, font links, JSON-LD, clean body
      Files: `apps/web/app/layout.tsx`
      Verify: `cd apps/web && npx next build` — no TypeScript errors in layout

- [ ] 4. Create `GlyphCanvas.tsx` — canvas glyph field component
      Files: `apps/web/app/components/GlyphCanvas.tsx`
      Verify: component renders without TS errors (`npx next build`)

- [ ] 5. Rewrite `page.tsx` — all sections in order (steps 4.1–4.16 above)
      Files: `apps/web/app/page.tsx`
      Verify: `cd apps/web && npx next build` — full build passes with 0 errors and 0 type errors

- [ ] 6. Update `login/page.tsx` — font vars, SVG logo, primary color token
      Files: `apps/web/app/login/page.tsx`
      Verify: `cd apps/web && npx next build` — passes; login page visually matches v02 token system

- [ ] 7. Final full build + lint check
      Verify: `cd apps/web && npx next build` exits 0; `cd apps/api && ruff check .` exits 0


## Font override (owner instruction — apply after build)
Replace all custom fonts with Arial system font:
- Headlines/display: Arial, font-weight: 700
- Body/content: Arial, font-weight: 400
- Monospace: keep JetBrains Mono for code/hash displays only
- Remove all @import from fontshare.com and fonts.googleapis.com
- CSS: `--font-display: Arial, 'Helvetica Neue', sans-serif; --font-body: Arial, 'Helvetica Neue', sans-serif;`
