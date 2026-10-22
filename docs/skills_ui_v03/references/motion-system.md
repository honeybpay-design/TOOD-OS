# Cadence motion system

Motion in cadence explains the product and confirms actions. It is calm,
once-only for entrances, and never hides content.

## Tokens

| Token | Value | Use |
| --- | --- | --- |
| `--ease-out` | `cubic-bezier(.22,1,.36,1)` | entrances, reveals, route fades, device transforms |
| `--ease-snap` | `cubic-bezier(.23,1,.32,1)` | presses, small UI responses |
| `--ease-io` | `cubic-bezier(.77,0,.175,1)` | on-screen movement inside vignettes (drag, scan) |
| `--d-press` | 140ms | `:active` scale(.97) |
| `--d-fast` | 180ms | hover color/border, menu fade |
| `--d-mid` | 260ms | dialogs, sheets, state swaps |
| `--d-reveal` | 680ms | scroll reveals |

Animate only `transform`, `opacity`, `clip-path`, stroke offsets and, for the
accordion and compare disclosure, `grid-template-rows` (0fr to 1fr).

## What moves and why

| Element | Motion | Why |
| --- | --- | --- |
| Hero copy | rise 16px + fade, 600ms, 60ms stagger (H1, lede, proof row, CTA), on load | first read, no scroll needed; the whole entrance ends by 820ms |
| Hero stage | rise 640ms, 220ms delay (done by 860ms) | the product arrives after the promise, still inside 900ms |
| Tilt card | `rotateX(20deg)` to 0 with scroll (rAF, passive listener) | signature: the product "stands up" as you engage |
| Hero inbox | a new row every 4.2s with a 700ms slide | shows the inbox is live; paused offscreen, on hidden tabs, under reduced motion |
| Meteor | 2px light travels the top edge of the tilt card and featured tier | signature accent, slow (5.5-6s) |
| Marquee | 46s linear, pause on hover | breadth of customers without demanding attention |
| Bento vignettes | wire pulses, scan beam, chart draw, drag, hover swap | each explains one capability; run only while visible |
| Workflow stage | screen crossfade (420ms) + 14px rise; bars scale in | the step and its screen change together |
| Workflow rail | fills with scroll progress | orientation in a long section |
| Spotlight | 180ms out, 460ms in, 7s progress line | quote changes are legible and pausable |
| Count-up stats | 1.4s ease-out, once at 60% visibility | lands the customer outcome |
| Billing switch | thumb slides 380ms; prices rise in 420ms | confirms the change |
| MacBook lid | -68deg to 0 with scroll | signature close |
| Route change | 320ms fade + 10px rise, jump to top | a new page, not a scroll |
| Buttons, chips, pills | `scale(.97)` on press | tactile feedback |

## Reveal pattern (content visible by default)

1. `<html class="no-js">`; a one-line head script swaps it to `js`.
2. Reveal styles exist only under `.js .rv` (opacity 0, translateY 18px).
3. An IntersectionObserver (`rootMargin: 0px 0px -6%`) adds `.in` once.
4. Safety net: on load, on route change and after fonts load, everything
   already inside the viewport gets `.in`; without IntersectionObserver every
   `.rv` gets `.in` immediately.
5. Stagger with an inline `--i` (70ms per step).
6. Never put `opacity: 0` on content that only a script can reveal, and never
   leave inactive carousel or tab content at low opacity: swap it, or hide it
   with `hidden`/`display: none`.

## Reduced motion

`@media (prefers-reduced-motion: reduce)` collapses durations and iterations,
shows reveals instantly, removes the meteor, beam, cursors, wire pulses and
marquee loop, stops the drag vignette, and keeps the tilt card and MacBook lid
upright. The script also reads the media query: no live inbox rows, no
auto-advancing spotlight (pause button hidden), instant anchor scrolling, no
route fade.

## Forbidden

Scroll-jacking, cursor-follow effects, bouncing or spinning entrances, blur-in
on body text, infinite loops next to reading text, animating layout
properties, and any animation that must finish before content is readable.
