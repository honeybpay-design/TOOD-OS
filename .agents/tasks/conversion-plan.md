# Implementation Plan: Conversion Upgrade for tood.uk Frontend

## Overview
Transform the Next.js frontend (apps/web) to convert visitors into paying customers with a 14-day free trial model, Google login CTA, and real dashboard functionality.

## Key Files to Modify
- `apps/web/app/page.tsx` - Landing page (hero, stats, pricing, trial section, announcement)
- `apps/web/app/login/page.tsx` - Login page (two-panel conversion layout)
- `apps/web/app/dashboard/page.tsx` - Dashboard (real API integration, trial banner)
- `apps/web/next.config.ts` - API rewrites configuration
- `apps/web/app/globals.css` - CSS variables reference

## Plan

### [ ] 1. Update Landing Page Hero Section
**What to do:**
- Replace 'Join the founding 30' and 'Try the demo' CTAs with 'Start free trial — 14 days free' linking to /login
- Add secondary CTA: 'See how it works' linking to #live section
- Add subtext: 'No credit card required · Cancel any time · Google sign-in'
- Update header nav buttons: 'Try the demo' → 'Sign in', 'Join the founding 30' → 'Start free trial'

**Files:**
- `apps/web/app/page.tsx` (Header and HeroSection components)

**Verify:**
- Run `cd apps/web && npm run build` - should compile without errors
- Visually check header CTAs changed in browser preview

### [ ] 2. Add Stats Bar under Hero
**What to do:**
- Add dark background stats bar with 4 real metrics:
  1. 'Requirements extracted: 56+'
  2. 'Tender documents processed: 1+'
  3. 'UK procurement regulations: 3'
  4. 'Export accuracy: 100%'
- Use --ink color token (#0f1215) for background
- Place immediately after HeroSection component

**Files:**
- `apps/web/app/page.tsx` (new StatsBar component after HeroSection)

**Verify:**
- Build succeeds
- Stats bar appears with correct styling and real numbers

### [ ] 3. Update Pricing Section CTAs
**What to do:**
- Change all plan CTA buttons to 'Start 14-day free trial'
- Add 'Most popular' badge on Professional plan
- Add tagline: 'All plans include a 14-day free trial. No credit card required.'
- Update CTA href values:
  - Starter: `/login?plan=starter`
  - Professional: `/login?plan=professional`
  - Enterprise: `mailto:hello@tood.uk?subject=Enterprise%20enquiry`

**Files:**
- `apps/web/app/page.tsx` (PricingSection component)

**Verify:**
- Pricing section shows updated CTAs and badge
- Links point to correct destinations

### [ ] 4. Add 'How the 14-day trial works' Section
**What to do:**
- Insert new section between pricing and FAQ (or after pricing if no FAQ)
- Four numbered steps:
  1. Sign in with Google — takes 30 seconds
  2. Upload your first tender — any PDF or DOCX
  3. Get your requirement matrix — free, no card needed
  4. Upgrade when you're ready — or don't. No pressure.

**Files:**
- `apps/web/app/page.tsx` (new TrialHowItWorks component)

**Verify:**
- New section appears with correct content and styling
- Build succeeds

### [ ] 5. Update Announcement Bar
**What to do:**
- Change text to: '14-day free trial · No credit card · Sign in with Google'
- Change link to: 'Start free →' linking to /login

**Files:**
- `apps/web/app/page.tsx` (AnnouncementBar component)

**Verify:**
- Announcement bar shows updated messaging
- Link works correctly

### [ ] 6. Redesign Login Page as Conversion Layout
**What to do:**
- Create two-panel layout (40%/60% on desktop, full-width on mobile)
- Left panel: Logo, headline 'Start your 14-day free trial', sub-headline 'No credit card required', prominent Google Sign-in button
- Right panel: Dark ink background with benefit points and testimonial
- Handle ?plan= URL parameter to show plan-specific notice
- Modify handleSignIn to pass plan param to OAuth endpoint

**Files:**
- `apps/web/app/login/page.tsx` (complete redesign)

**Verify:**
- Login page has new two-panel layout
- Google sign-in works with plan parameter passing
- Mobile responsive design works

### [ ] 7. Implement Real Dashboard
**What to do:**
- Replace 'coming soon' placeholder with functional dashboard
- Header: Logo + org name + plan badge + sign out
- Trial banner with localStorage countdown
- Quick action buttons: '+ New tender', 'Load sample tender', 'Add evidence'
- Recent tenders list fetching from GET /api/tenders
- Stats row showing evidence and tender counts
- Integrate with /me endpoint for user data

**Files:**
- `apps/web/app/dashboard/page.tsx` (complete implementation)
- Create supporting components in `apps/web/app/dashboard/components/`

**Verify:**
- Dashboard loads real data from API
- Trial banner shows countdown
- All API calls work with Bearer token from sessionStorage

### [ ] 8. Add /v1/:path* Rewrite to next.config.ts
**What to do:**
- Add third rewrite: `{ source: '/v1/:path*', destination: apiUrl + '/v1/:path*' }`
- Keep existing rewrites intact

**Files:**
- `apps/web/next.config.ts`

**Verify:**
- Build succeeds
- All API endpoints accessible via both /api/ and /v1/ paths

### [ ] 9. Build and Fix TypeScript Errors
**What to do:**
- Run `cd apps/web && npm run build`
- Fix any TypeScript errors that appear
- Ensure all new components have proper TypeScript types

**Files:**
- All modified files

**Verify:**
- `npm run build` completes successfully with 0 errors

### [ ] 10. Deploy to Production
**What to do:**
1. `gcloud builds submit c:\Users\Donny\Desktop\tood.com\apps\web --tag europe-west2-docker.pkg.dev/tood-os/tood/web:latest --project=tood-os`
2. `gcloud run deploy tood-os-web --image europe-west2-docker.pkg.dev/tood-os/tood/web:latest --region europe-west2 --project=tood-os --set-env-vars="API_URL=https://tood-os-api-844874461521.europe-west2.run.app"`
3. `firebase deploy --only hosting --project tood-os`

**Files:**
- Deployment scripts/commands

**Verify:**
- All deployments succeed
- New version is live at tood.uk

### [ ] 11. Commit and Push to Branch
**What to do:**
- Commit with message: `feat: conversion upgrade — 14-day free trial, Google login CTA, real dashboard`
- Push to branch: `feature/saas-platform`

**Files:**
- All modified files

**Verify:**
- Changes committed locally
- Branch pushed to remote

## Dependencies
- Items 1-5 (landing page) can be done in parallel
- Item 6 (login page) depends on item 8 (rewrite) for plan param handling
- Item 7 (dashboard) depends on API endpoints being available
- Item 9 must pass before item 10 (deploy)
- Item 11 is final step after all others complete