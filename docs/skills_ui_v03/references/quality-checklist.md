# Cadence pre-delivery checklist

Run `node scripts/validate-cadence.mjs path/to/index.html` first (it also fails on any name left over from the sample), then walk this list
in a real browser at 1440, 1024, 768 and 390 px. Fix every miss before
delivering.

## Premium UI
- [ ] Geist and Geist Mono actually render (no system fallback in
      screenshots): embedded as data URIs in the standalone file, from the
      fontsource packages or `next/font/google` in a project.
- [ ] H1 and every H2 use the vertical gradient clip; H1 is two lines on desktop.
- [ ] Hero matches the cadence anatomy: H1 at 96px / weight 600 on desktop and
      40px on phones, its box 136px from the top; two-line lede; proof row; one
      primary CTA; tilt card below. No announcement pill, second CTA, glow or
      extra chips. Section H2s stay at or under 3.2rem.
- [ ] No purple, violet or lavender anywhere (hue 235-300), including avatars.
- [ ] One accent only; semantic colors appear only inside product UI.
- [ ] Section compositions vary (no two adjacent sections share a layout family).
- [ ] Every clickable element has hover, `:active` press, `:focus-visible`;
      buttons have loading and disabled states; chips and tabs show selection.
- [ ] Nav condenses into the pill on scroll and marks the active section.
- [ ] No empty bento cell, no orphaned card, no awkward empty band in a frame.

## Imagery
- [ ] Product UI is re-themed to the user's product: workspace, rows, tags,
      numbers, roadmap items, digest copy, MacBook screen.
- [ ] One fictional workspace and one hero roadmap item thread through hero,
      bento, workflow, story and CTA.
- [ ] Photos follow the single art direction; portraits share backdrop and
      light; crops keep faces whole.
- [ ] No text, logos or fake UI inside photos; no real company logos anywhere.
- [ ] Every `<img>` has meaningful `alt` (or `alt=""` if decorative),
      width/height, lazy loading below the fold.

## Motion
- [ ] Hero copy and stage finish their entrance within 900ms, without scrolling.
- [ ] With JavaScript disabled every section is readable.
- [ ] Tilt card stands upright by the time it reaches the top third; MacBook
      lid opens as it enters.
- [ ] Vignettes pause offscreen; live inbox and spotlight pause offscreen and
      on hover/focus; the spotlight has a pause button.
- [ ] With `prefers-reduced-motion: reduce`, nothing loops, nothing slides,
      devices are upright, all content is visible.

## Completeness (a site someone can use as-is)
- [ ] Every nav item, card link, CTA and footer link resolves to a section or
      route; no `href="#"`.
- [ ] Routes work from a cold load with the hash (`#/changelog`, story,
      `#/signin`, `#/legal/security`) and unknown hashes show the 404.
- [ ] Pricing shows the user's real plan count (2-4, `data-count` set below
      four), and on phones the flagship item is still visible (`.m-hide` sits
      on the least important lane, KPI and column).
- [ ] Pricing toggle swaps every price and billing note; compare disclosure
      opens and is keyboard reachable.
- [ ] FAQ is single-open and keyboard operable.
- [ ] Sign-up, newsletter, changelog subscribe, sign-in (email and SSO) and the
      sales dialog validate inline and end in a success state or toast.
- [ ] Changelog filters and search work, counts update, empty state offers
      "Clear filters".
- [ ] Copy is specific and plausible: real facts from the brief; anything
      invented (quotes, logos, metrics, prices, dates) is listed for the user;
      no sample names, no lorem ipsum, no "Your Company", no em dashes.

## Responsiveness and accessibility
- [ ] No horizontal overflow from 360 to 1920 px (watch absolutely positioned
      `.sr-only` text inside scroll containers; give the container
      `position: relative`).
- [ ] Mobile menu traps focus, closes on Esc, link tap, scrim tap.
- [ ] Workflow becomes tabs under 960px; product UI hides the sidebar and
      detail pane; the single hero CTA keeps its natural width on phones.
- [ ] Skip link, `header`/`nav`/`main`/`footer`, one h1 per route, labeled
      inputs, `aria-expanded`/`aria-selected`/`aria-checked` on custom widgets.
- [ ] Body text contrast at least 4.5:1 (`--text-2` on `--bg` is 9.3:1).

## Performance and delivery
- [ ] Standalone file has zero network requests (no CDN, no font service, no
      remote images) and no console errors.
- [ ] (Single-file preview) Runs from disk and inside `<iframe sandbox="allow-scripts">`: no
      storage outside try/catch, no alert/confirm/prompt, no `window.open`, no
      top navigation.
- [ ] Built file is 5 MB or less (8 MB hard cap); images are WebP at the slot
      widths in image-plan.md.
