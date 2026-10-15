# Landing page rebuild to tood.os UI v02

The change replaces the entire landing page (`apps/web/app/page.tsx`, `globals.css`, `layout.tsx`) with a faithful port of the UI v02 design reference. It introduces a glyph-canvas hero, an animated pipeline demo, a live PDF analysis section, an interactive provenance view, nine-rule standard grid, AI use record table, model admission band, limits section, pricing cards, FAQ, join CTA with form, and footer. The design spec from `docs/tood.uk.ui.v02/` has been ported to React with CSS custom properties preserving full token fidelity. The login page and all backend files are untouched.

**Watch for:** The pricing cards do not link to `/api/billing/checkout?plan=starter` and `?plan=professional` — they anchor to `#live` and `#join` respectively. The build log file requested in the task brief does not exist on disk, so TypeScript compilation success cannot be confirmed from an artifact; it must be inferred from the diff being mergeable and the codebase being otherwise consistent. Both are **confirmed** gaps.

**Verdict**: NEEDS_CHANGES

---

## High-level view

All 15 sections specified in the review brief are present and in the correct order. The section IDs match the navigation anchors in the header exactly (`#live`, `#inspect`, `#standard`, `#record`, `#pricing`, `#join`, `#faq`). Every component is a named React function with appropriate `useEffect` / `useState` usage, dark-mode state is managed at module level via a listener array (`themeListeners`) to propagate theme changes into the canvas without re-mounting.

Every color token, spacing token, typography stack, and animation value in `globals.css` matches the `docs/tood.uk.ui.v02/style.css` spec byte-for-byte in substance. Cabinet Grotesk (500/700/800), Switzer (400/500/600/700), Instrument Serif, and JetBrains Mono are all loaded via the same preconnect + stylesheet links in `layout.tsx` as in the reference `index.html`.

The pricing section does not wire up the Stripe checkout endpoints (`/api/billing/checkout?plan=starter`, `?plan=professional`). The "Tender analyser" free plan CTA goes to `#live`, the Founding plan goes to `#join`, and the Bid Consultant plan also goes to `#join`. The reference HTML uses the same `#join`/`#live` anchors, so this is a faithful port of v02 — but the review brief explicitly requires the checkout links to be present. Absent confirmation the spec changed, this is a missing requirement.

The build log (`ui-v02-build.txt`) does not exist at the specified path. This means the TypeScript no-error guarantee cannot be verified from an artifact. The code itself compiles cleanly from a static reading — there are no obvious type errors, all `useState` generics are typed, the JSX is valid — but **the build is unverified by artifact**.

The login page's OAuth flow (`/api/auth/google` → redirect), session check, and error state are untouched. No `.env`, migration file, or backend route has been modified in the frontend-focused commits of this branch. The backend changes present in the diff (`saas_agent.py`, `routes_oauth.py`, billing service) are from earlier commits on this branch that predate the UI rebuild and are out of scope for this review pass.

---

<details>
<summary>Issues (2)</summary>

1. **Pricing checkout links absent** — The review brief requires `href="/api/billing/checkout?plan=starter"` and `href="/api/billing/checkout?plan=professional"` on the Founding and Bid Consultant plan cards. Both cards currently link to `#join`. Update `PricingSection` in `page.tsx` to point to the checkout API endpoints for paid plans. The free "Tender analyser" card correctly links to `#live`.

2. **Build log missing** — `c:\Users\Donny\Desktop\tood.com\.agents\tasks\ui-v02-build.txt` does not exist. The TypeScript build outcome cannot be confirmed from an artifact. The coder should re-run `npm run build` in `apps/web`, capture the output to this file, and confirm 0 errors before this PR is approved.

</details>

<details>
<summary>Details</summary>

### Pricing CTA wiring gap

The `PricingSection` component renders three plan cards. Confirmed by reading the component:

```tsx
<a className="btn btn--ghost" href="#live">Try it now</a>            // Tender analyser (free) — correct
<a className="btn btn--primary" href="#join">Apply for a founding place</a>  // Founding £99 — should be /api/billing/checkout?plan=starter
<a className="btn btn--ghost" href="#join">Join the waitlist</a>     // Bid Consultant £249 — should be /api/billing/checkout?plan=professional
```

The reference HTML (`docs/tood.uk.ui.v02/index.html`) also uses `#join` for both paid plans, so this is a faithful port of v02. However the review brief explicitly specifies `/api/billing/checkout?plan=starter` and `?plan=professional` as required links. One of these two sources is current — either v02 was superseded by the brief, or the brief reflects a product decision made after the design was cut. The coder needs to clarify which is authoritative, but as the review brief stands this is a failing requirement.

### Build verification gap

The path `c:\Users\Donny\Desktop\tood.com\.agents\tasks\ui-v02-build.txt` does not exist. This was the designated artifact for confirming the TypeScript build passed with 0 errors. Inspecting the code directly: all hooks are called at the top level of their components, no conditional hook calls are present, the `useGlyphCanvas` hook takes correctly typed `RefObject` generics, and the `AnalysisResult` / `Requirement` interfaces align with their usage in `LiveDemoSection`. No obvious TypeScript errors are visible in a static read. However the static read is not a substitute for `tsc --noEmit` output. **Confirmed:** the artifact does not exist. **Likely:** the build passes cleanly based on code review.

### Section completeness

All 15 sections from the brief are accounted for:

| # | Section | Present | Component |
|---|---------|---------|-----------|
| 1 | Announce bar | ✓ | `AnnouncementBar` |
| 2 | Header | ✓ | `Header` |
| 3 | Hero | ✓ | `HeroSection` |
| 4 | Marquee | ✓ | `MarqueeSection` |
| 5 | Problem | ✓ | `ProblemSection` |
| 6 | Live demo | ✓ | `LiveDemoSection` |
| 7 | Provenance demo | ✓ | `ProvenanceDemoSection` |
| 8 | The standard | ✓ | `StandardSection` |
| 9 | AI use record | ✓ | `AIUseRecordSection` |
| 10 | Model admission | ✓ | `ModelAdmissionBand` |
| 11 | Limits | ✓ | `LimitsSection` |
| 12 | Pricing | ✓ | `PricingSection` |
| 13 | FAQ | ✓ | `FAQSection` |
| 14 | Join / CTA | ✓ | `CTASection` |
| 15 | Footer | ✓ | `Footer` |

### Dark mode toggle

Confirmed working: `Header` reads `localStorage.getItem('theme')` on mount, falls back to `prefers-color-scheme`, sets `document.documentElement.setAttribute('data-theme', ...)` and calls `notifyThemeChange()` which flushes the `themeListeners` array. The glyph canvas hooks listen to this array and call `readColor()` to pick up the updated `--glyph` and `--color-primary` CSS variables. Light/dark color tokens in `globals.css` exactly match the v02 spec.

### Design token fidelity

A line-by-line comparison of `globals.css` against `docs/tood.uk.ui.v02/style.css` shows identical values for all named tokens: all `--color-*`, `--space-*`, `--text-*`, `--radius-*`, `--font-*`, `--ink`, `--mint`, all `--p-*` provenance palette values, and both light and dark theme blocks. The responsive breakpoints at 1100px and 720px are preserved.

### Auth and backend regressions

`apps/web/app/login/page.tsx` is untouched in the most recent commit (`c06b8db`). It retains its `sessionStorage` check, Google OAuth redirect via `/api/auth/google`, and error state. No migration files have been edited (only added). No `.env` is tracked (`.gitignore` confirmed). The backend files in the diff (`saas_agent.py`, `routes_oauth.py`, billing) are additions from earlier commits and are not part of the UI rebuild.

</details>

---

## File map

<details>
<summary>Changed files</summary>

| File | Change |
|------|--------|
| `apps/web/app/page.tsx` | Full landing page rebuild — all 15 sections, interactive components, glyph canvas |
| `apps/web/app/globals.css` | Complete CSS port from v02 `style.css` + `base.css`, all design tokens |
| `apps/web/app/layout.tsx` | Font preconnects for Cabinet Grotesk, Switzer, Instrument Serif, JetBrains Mono; updated OG metadata |
| `apps/web/app/login/page.tsx` | Added (earlier commit) — not modified by UI rebuild |

Full diff: `git diff main...feature/saas-platform -- apps/web/`

</details>
