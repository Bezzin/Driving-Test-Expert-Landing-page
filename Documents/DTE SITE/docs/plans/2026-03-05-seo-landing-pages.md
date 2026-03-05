# DTERoutes SEO Landing Pages Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate the existing Vite SPA to Next.js and programmatically generate 300+ SEO-optimised test centre landing pages using DVSA open data and Supabase route data, to outrank testroutes.co.uk across all "[centre name] driving test routes" keywords.

**Architecture:** Next.js App Router with static site generation (SSG) via `generateStaticParams`. DVSA `.ods` data is downloaded and parsed at build time into a local JSON data layer. Supabase provides proprietary route data. Pages are pre-rendered at build, deployed to Vercel. Internal linking uses hub-and-spoke: master hub -> regional hubs -> individual centre pages.

**Tech Stack:** Next.js 15 (App Router), React 19, Tailwind CSS 4, Supabase JS client, `xlsx` (for ODS parsing), `@vercel/og` (OG image generation), TypeScript, Vercel deployment.

---

## Prerequisites / Blockers

Before starting implementation, the following must be provided:

| Item | Status | Notes |
|------|--------|-------|
| Supabase URL + anon key | **NEEDED** | Add `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` to `.env.local` |
| Supabase table schema | **NEEDED** | Need table names and columns for test centres and routes |
| Domain decision | **NEEDED** | Is this `drivingtestexpert.com`, `testroutesexpert.co.uk`, or new domain? |
| Notion API keys | Have | Currently in `.env` but may not be needed for SEO pages |
| Google Ads data | Have | `search_terms_report.xlsx` — 1626 terms, 50 converting, analysed below |
| DVSA datasets | Public | 6 per-centre ODS files, URLs documented in SEO blueprint |
| Competitor analysis | Have | Full blueprint in `SEOblueprintTestRoutesExperoutrankingthecompetition.md` |
| App Store URLs | Have | iOS: `apps.apple.com/gb/app/test-routes-expert/id6757989639`, Android: `play.google.com/store/apps/details?id=com.drivingtestexpert.testroutesexpert` |

---

## Google Ads Intelligence Summary

From the search terms report (1626 terms, 354 with clicks, 50 converting):

**Highest-converting centre keywords:**
- `stafford driving test routes` — 410 clicks, 105 conversions (25.7% CVR, best performer)
- `stafford test routes` — 127 clicks, 52.5 conversions
- `driving test routes stafford` — 84 clicks, 32.5 conversions
- `newcastle under lyme driving test routes` — 69 clicks combined, 3 conversions
- `featherstone driving test routes` — 50+ impressions across variants, 8 clicks
- `lichfield driving test routes` — 64 impressions, 6 clicks

**High-impression centres without clicks (SEO opportunity):**
- Wolverhampton, Telford, Cobridge, Cannock, Wednesbury, Shrewsbury, Burton, Buxton, Worcester, Crawley, Chorley, Chichester, Coventry, Sidcup, Hornchurch, Colwick

**Key insight:** "[centre] driving test routes" is the dominant converting pattern at ~25% CVR. Each centre page should target this exact pattern. Stafford alone drove 200+ conversions — scaling to 300+ centres at even 10% of that performance = massive organic opportunity.

---

## Phase 1: Next.js Project Setup & Component Migration

### Task 1.1: Initialise Next.js project

**Files:**
- Create: `next.config.ts`
- Create: `app/layout.tsx`
- Create: `app/globals.css`
- Create: `package.json` (new)
- Create: `tsconfig.json` (new)
- Create: `tailwind.config.ts`
- Create: `.env.local`

**Step 1: Scaffold Next.js project in new directory**

```bash
cd "C:/Users/Nathaniel/Documents/DTE SITE"
npx create-next-app@latest dte-next --typescript --tailwind --app --src-dir=false --import-alias="@/*" --no-eslint
```

**Step 2: Configure Tailwind with existing brand tokens**

Edit `tailwind.config.ts`:
```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        accent: '#FCA311',
        'accent-glow': 'rgba(252, 163, 17, 0.3)',
        card: '#18181b',
        bg: '#0f0f0f',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        brand: ['Poppins', 'sans-serif'],
      },
      animation: {
        marquee: 'marquee 25s linear infinite',
        float: 'float 6s ease-in-out infinite',
        'float-delayed': 'float 6s ease-in-out 3s infinite',
        'fade-up': 'fadeInUp 0.8s ease-out forwards',
        'pulse-glow': 'pulseGlow 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        shine: 'shine 1.5s infinite',
      },
      keyframes: {
        marquee: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(30px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseGlow: {
          '0%, 100%': { opacity: '0.5', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.05)' },
        },
        shine: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
    },
  },
  plugins: [],
}

export default config
```

**Step 3: Set up `.env.local`**

```
# Supabase (FILL IN)
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=

# Site
NEXT_PUBLIC_SITE_URL=https://www.testroutesexpert.co.uk
NEXT_PUBLIC_PLAY_STORE_URL=https://play.google.com/store/apps/details?id=com.drivingtestexpert.testroutesexpert
NEXT_PUBLIC_APP_STORE_URL=https://apps.apple.com/gb/app/test-routes-expert/id6757989639
```

**Step 4: Configure `next.config.ts`**

```typescript
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
}

export default nextConfig
```

**Step 5: Verify build works**

Run: `cd dte-next && npm run build`
Expected: Successful build with default Next.js page

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: initialise Next.js project with Tailwind brand tokens"
```

---

### Task 1.2: Migrate shared components

**Files:**
- Copy + adapt: `components/Layout/Navbar.tsx`
- Copy + adapt: `components/Layout/Footer.tsx`
- Copy + adapt: `components/UI/Reveal.tsx`
- Copy + adapt: `components/UI/StoreBadges.tsx`
- Copy + adapt: `components/UI/WhatsAppButton.tsx`
- Create: `lib/constants.ts`
- Create: `lib/types.ts`

**Step 1: Move constants and types**

Create `lib/constants.ts` — copy from existing `constants.ts` but replace `import.meta.env.BASE_URL` with `process.env.NEXT_PUBLIC_SITE_URL`, and remove all `window.location` references.

Create `lib/types.ts` — copy from existing `types.ts`.

**Step 2: Adapt components for Next.js**

Key changes needed in each component:
- Replace `<a href>` with Next.js `<Link>` for internal links
- Replace `<img>` with Next.js `<Image>` (or keep `<img>` since we use `output: 'export'`)
- Remove `window.location.pathname` usage (use `usePathname()` from `next/navigation`)
- Add `'use client'` directive to components using `useState`, `useEffect`, `useRef`
- Navbar: replace `window.location.pathname` routing with `usePathname()`
- Reveal: keep as client component (uses IntersectionObserver)

**Step 3: Verify components render**

Create a minimal `app/page.tsx` importing Navbar and Footer to verify they render.

Run: `npm run dev`
Expected: Page renders with navbar and footer

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: migrate shared components to Next.js"
```

---

### Task 1.3: Migrate homepage and app landing page

**Files:**
- Create: `app/page.tsx` (homepage)
- Create: `app/test-routes-app/page.tsx` (app landing page)
- Copy: `components/Features/Hero.tsx`
- Copy: `components/Features/FeatureRow.tsx`
- Copy: `components/Pages/AppLandingPage.tsx`
- Copy: `components/AI/DrivingTutor.tsx`
- Copy: `components/UI/Marquee.tsx`
- Copy: `components/UI/ServiceStatusBanner.tsx`
- Copy: `public/` assets (screenshots, badges)

**Step 1: Create homepage as server component shell with client islands**

`app/page.tsx` should be a server component that composes the client components (Hero, FeatureRow, etc.). Add proper metadata export:

```typescript
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Driving Test Expert - We Get You Passed',
  description: 'Practice real UK driving test routes with turn-by-turn navigation. 350+ test centres, 4000+ routes.',
  openGraph: {
    title: 'Driving Test Expert - We Get You Passed',
    description: 'Practice real UK driving test routes with turn-by-turn navigation.',
    url: 'https://www.testroutesexpert.co.uk',
    siteName: 'Test Routes Expert',
    locale: 'en_GB',
    type: 'website',
  },
}
```

**Step 2: Create app landing page**

Move `AppLandingPage` content to `app/test-routes-app/page.tsx`. Add `'use client'` since it uses hooks. Export metadata separately from a `layout.tsx` if needed, or use `generateMetadata`.

**Step 3: Copy public assets**

```bash
cp -r DTESite/public/* dte-next/public/
```

**Step 4: Verify both pages work**

Run: `npm run dev`
- Visit `/` — homepage renders
- Visit `/test-routes-app/` — app landing page renders

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: migrate homepage and app landing page to Next.js"
```

---

## Phase 2: DVSA Data Pipeline

### Task 2.1: Download and parse DVSA ODS files

**Files:**
- Create: `scripts/fetch-dvsa-data.ts`
- Create: `data/dvsa/centres.json` (generated)
- Create: `lib/dvsa-types.ts`

**Step 1: Define DVSA types**

Create `lib/dvsa-types.ts`:
```typescript
export interface DvsaCentre {
  name: string
  slug: string
  region: string
  passRateOverall: number
  passRateMale: number
  passRateFemale: number
  passRateFirstAttempt: number
  passRateAutomatic: number
  passRateByAge: Record<string, number>
  passRateHistory: Array<{ year: string; rate: number }>
  testsConductedTotal: number
  testsConductedMale: number
  testsConductedFemale: number
  zeroFaultPasses: number
  cancellations: {
    dvsaCancelled: number
    candidateCancelled: number
    noShows: number
  }
  dataPeriod: string
}

export interface DvsaNational {
  averagePassRate: number
  totalCentres: number
  dataPeriod: string
}
```

**Step 2: Write DVSA data fetcher script**

Create `scripts/fetch-dvsa-data.ts`:
- Download all 6 per-centre ODS files from the URLs in the SEO blueprint
- Use `xlsx` package to parse ODS format (it handles ODS natively)
- Extract per-centre data from each dataset
- Merge into a single `centres.json` with all fields populated
- Calculate derived fields: difficulty rank, difficulty label, national averages
- Handle centre name normalisation (matching across datasets)

Install dependency:
```bash
npm install xlsx
npm install -D tsx
```

The script should:
1. Fetch DRT122A (pass rates by gender/month) -> extract latest year per centre
2. Fetch DRT122B (cancellations) -> extract latest year per centre
3. Fetch DRT122C (first-attempt rates) -> extract latest year per centre
4. Fetch DRT122D (pass rates by age 17-25) -> extract latest year per centre
5. Fetch DRT122E (automatic car rates) -> extract latest year per centre
6. Merge all into a unified record per centre
7. Calculate: difficulty rank (sorted by pass rate), difficulty label (top third = "Above Average", middle = "Average", bottom = "Below Average")
8. Output `data/dvsa/centres.json`

DVSA ODS download URLs:
```
DRT122A: https://assets.publishing.service.gov.uk/media/689c5ec6d2a1b0d5d1bb1251/drt122a-car-driving-test-by-test-centre.ods
DRT122B: https://assets.publishing.service.gov.uk/media/689c5ed187bf475940723ee1/drt122b-car-driving-test-cancellations-by-test-centre.ods
DRT122C: https://assets.publishing.service.gov.uk/media/689c5c9b1c63de6de5bb1249/drt122c-car-driving-test-first-attempt-by-test-centre.ods
DRT122D: https://assets.publishing.service.gov.uk/media/689c5cad87bf475940723edd/drt122d-car-driving-test-by-age-by-test-centre.ods
DRT122E: https://assets.publishing.service.gov.uk/media/689c59491c63de6de5bb1246/drt122e-car-driving-test-automatic-by-test-centre.ods
```

**Step 3: Run the script**

```bash
npx tsx scripts/fetch-dvsa-data.ts
```

Expected: `data/dvsa/centres.json` generated with 300+ centre records.

**Step 4: Verify data quality**

```bash
node -e "const d = require('./data/dvsa/centres.json'); console.log('Centres:', d.length); console.log('Sample:', JSON.stringify(d[0], null, 2))"
```

Expected: 300+ centres, each with pass rates, cancellation data, age breakdowns.

**Step 5: Commit**

```bash
git add scripts/fetch-dvsa-data.ts data/dvsa/centres.json lib/dvsa-types.ts
git commit -m "feat: add DVSA data pipeline — parse 6 ODS datasets into centres.json"
```

---

### Task 2.2: Enrich centres with geographic data and slugs

**Files:**
- Create: `scripts/enrich-centres.ts`
- Create: `data/regions.json`
- Modify: `data/dvsa/centres.json`

**Step 1: Add geographic enrichment**

Create `scripts/enrich-centres.ts` that:
- Adds lat/long coordinates per centre (from GOV.UK lookup or hardcoded lookup table)
- Assigns each centre to a region (one of ~15 UK regions)
- Generates URL slugs: lowercase, hyphenated (`birmingham-south-yardley`)
- Calculates nearest 5 centres by haversine distance
- Adds region slug for regional hub pages

Region list:
```
East Anglia, East Midlands, Greater London, North East, North West,
Scotland, South East, South West, Wales, West Midlands, Yorkshire,
Northern Ireland, East of England, Channel Islands
```

**Step 2: Generate region mapping**

Create `data/regions.json`:
```json
{
  "regions": [
    { "name": "Greater London", "slug": "greater-london", "centres": ["sidcup", "wood-green", ...] },
    { "name": "West Midlands", "slug": "west-midlands", "centres": ["stafford", "wolverhampton", ...] }
  ]
}
```

**Step 3: Run enrichment**

```bash
npx tsx scripts/enrich-centres.ts
```

**Step 4: Verify nearby centres calculated**

```bash
node -e "const d = require('./data/dvsa/centres.json'); const s = d.find(c => c.slug === 'stafford'); console.log(s.nearbyCentres)"
```

Expected: 5 nearby centres with distance and pass rate.

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: enrich centres with coordinates, regions, nearby centres"
```

---

### Task 2.3: Integrate Supabase route data

**Files:**
- Create: `lib/supabase.ts`
- Create: `scripts/merge-supabase-routes.ts`
- Modify: `data/dvsa/centres.json`

**Step 1: Create Supabase client**

Create `lib/supabase.ts`:
```typescript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseKey)
```

Install: `npm install @supabase/supabase-js`

**Step 2: Write route merger script**

Create `scripts/merge-supabase-routes.ts`:
- Query Supabase for all test centres and their routes
- Match Supabase centres to DVSA centres by name (fuzzy match if needed)
- Add route count, route names, key roads, and challenges to each centre record
- Flag centres that have Supabase route data vs those that don't

**BLOCKER:** This task requires Supabase credentials. Skip until provided — the rest of the pipeline works without route data (pages will show DVSA stats but say "Routes coming soon" for centres without Supabase data).

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: add Supabase client and route merger script (pending credentials)"
```

---

## Phase 3: Test Centre Page Generation

### Task 3.1: Create data loading utilities

**Files:**
- Create: `lib/centres.ts`

**Step 1: Write data loader**

Create `lib/centres.ts`:
```typescript
import centresData from '@/data/dvsa/centres.json'
import regionsData from '@/data/regions.json'
import type { DvsaCentre } from './dvsa-types'

export function getAllCentres(): DvsaCentre[] {
  return centresData as DvsaCentre[]
}

export function getCentreBySlug(slug: string): DvsaCentre | undefined {
  return getAllCentres().find(c => c.slug === slug)
}

export function getCentresByRegion(regionSlug: string): DvsaCentre[] {
  const region = regionsData.regions.find(r => r.slug === regionSlug)
  if (!region) return []
  return getAllCentres().filter(c => region.centres.includes(c.slug))
}

export function getAllRegions() {
  return regionsData.regions
}

export function getNationalAverage(): number {
  const centres = getAllCentres()
  return centres.reduce((sum, c) => sum + c.passRateOverall, 0) / centres.length
}
```

**Step 2: Verify it loads**

```bash
npx tsx -e "import { getAllCentres } from './lib/centres'; console.log(getAllCentres().length)"
```

**Step 3: Commit**

```bash
git add lib/centres.ts
git commit -m "feat: add centre data loading utilities"
```

---

### Task 3.2: Build the test centre page template

**Files:**
- Create: `app/test-centres/[slug]/page.tsx`
- Create: `app/test-centres/[slug]/layout.tsx`
- Create: `components/centres/CentreHero.tsx`
- Create: `components/centres/PassRateStats.tsx`
- Create: `components/centres/RouteSection.tsx`
- Create: `components/centres/ChallengesSection.tsx`
- Create: `components/centres/TipsSection.tsx`
- Create: `components/centres/NearbyCentres.tsx`
- Create: `components/centres/CentreFaq.tsx`
- Create: `components/centres/AppCtaBlock.tsx`
- Create: `components/centres/Breadcrumbs.tsx`
- Create: `components/centres/SchemaMarkup.tsx`

**Step 1: Create `generateStaticParams`**

`app/test-centres/[slug]/page.tsx`:
```typescript
import { getAllCentres, getCentreBySlug, getNationalAverage } from '@/lib/centres'
import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
// ... import all section components

interface PageProps {
  params: Promise<{ slug: string }>
}

export async function generateStaticParams() {
  return getAllCentres().map(centre => ({
    slug: centre.slug,
  }))
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const centre = getCentreBySlug(slug)
  if (!centre) return {}

  return {
    title: `${centre.name} Driving Test Routes 2026 | Pass Rate, Tips & Maps`,
    description: `Practice ${centre.totalRoutes ?? 'all'} real ${centre.name} driving test routes. ${centre.name} pass rate: ${centre.passRateOverall}%. Routes, tips, and maps to help you pass.`,
    alternates: {
      canonical: `/test-centres/${slug}/`,
    },
    openGraph: {
      title: `${centre.name} Driving Test Centre - Routes, Pass Rates & Tips`,
      description: `${centre.name} pass rate: ${centre.passRateOverall}%. Practice real test routes with turn-by-turn navigation.`,
      url: `/test-centres/${slug}/`,
      siteName: 'Test Routes Expert',
      locale: 'en_GB',
      type: 'article',
    },
  }
}

export default async function CentrePage({ params }: PageProps) {
  const { slug } = await params
  const centre = getCentreBySlug(slug)
  if (!centre) notFound()

  const nationalAverage = getNationalAverage()

  return (
    <>
      <SchemaMarkup centre={centre} nationalAverage={nationalAverage} />
      <Breadcrumbs centre={centre} />
      <CentreHero centre={centre} />
      <PassRateStats centre={centre} nationalAverage={nationalAverage} />
      <RouteSection centre={centre} />
      <ChallengesSection centre={centre} />
      <TipsSection centre={centre} />
      <NearbyCentres centre={centre} />
      <CentreFaq centre={centre} nationalAverage={nationalAverage} />
      <AppCtaBlock centre={centre} />
    </>
  )
}
```

**Step 2: Build each section component**

Each component receives the centre data and renders the corresponding section from the SEO blueprint template. Key requirements per component:

**`SchemaMarkup.tsx`** — Renders `<script type="application/ld+json">` with 4 schema blocks: GovernmentOffice, BreadcrumbList, FAQPage, WebPage. Uses exact templates from SEO blueprint.

**`CentreHero.tsx`** — H1 with centre name, pass rate badge, route count, download CTAs, quick stats row.

**`PassRateStats.tsx`** — HTML data table (Google featured snippet target) with overall/male/female/automatic/first-attempt rates compared to national average. Pass rate by age chart. Historical year-over-year trend. Tests conducted volume.

**`RouteSection.tsx`** — H2 "driving test routes", route count, key roads, sample route preview. CTA to download app. If no Supabase data, show "Routes being mapped — download the app for latest availability."

**`ChallengesSection.tsx`** — H2 "What makes [centre] challenging", specific road references, junction types, speed limit changes. Content generated from centre's geographic context and road data.

**`TipsSection.tsx`** — H2 "How to pass at [centre]", 5-8 centre-specific tips.

**`NearbyCentres.tsx`** — H2 "Test centres near [centre]", table with linked centre names, distance, pass rate, difficulty label. Uses `nearbyCentres` from enriched data.

**`CentreFaq.tsx`** — H2 "FAQ", 6-8 questions with centre-specific answers interpolating real data. Targets People Also Ask queries.

**`AppCtaBlock.tsx`** — App screenshots, download buttons, value prop. Reuse from existing `AppLandingPage` style.

**`Breadcrumbs.tsx`** — `Home > Test Centres > {region} > {centre_name}`, linked except last item.

**Step 3: Verify a single centre page renders**

Run: `npm run dev`
Visit: `/test-centres/stafford/`
Expected: Full page with all sections, real DVSA data

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: add test centre page template with all sections"
```

---

### Task 3.3: Generate unique editorial content per centre

**Files:**
- Create: `scripts/generate-content.ts`
- Create: `data/centre-content.json`

**Step 1: Write content generation script**

This is the most critical task for avoiding thin content penalties. Create `scripts/generate-content.ts` that generates unique editorial paragraphs per centre using:

1. **Geographic context** — reference actual road names (A-roads, B-roads near the centre), local landmarks, town characteristics (urban/suburban/rural)
2. **Statistical context** — compare pass rate to national average and nearby centres, highlight if it's easier/harder
3. **Challenge descriptions** — derive from road types (roundabouts if urban, country lanes if rural, dual carriageways if on A-road)
4. **Tips** — generate based on area characteristics (school zones, bus lanes, parking difficulty)

This can use:
- Centre coordinates + OpenStreetMap Nominatim reverse geocode for local road names
- OR a manually curated lookup table for the top 50 centres (highest search volume from Google Ads data)
- The remaining 250+ centres get algorithmically generated content from geographic features

Output: `data/centre-content.json` with per-centre:
```json
{
  "stafford": {
    "areaDescription": "Stafford test centre is located on...",
    "keyChallenges": ["The A34 dual carriageway...", "..."],
    "specificTips": ["Watch for the 30mph zone on...", "..."],
    "nearbyLandmarks": ["Stafford Castle", "Victoria Park"],
    "roadTypes": ["dual carriageway", "residential", "ring road"],
    "bestTimeToTest": "Mid-morning avoids school traffic on..."
  }
}
```

**Priority centres for manual enrichment** (from Google Ads data — highest search volume):
1. Stafford (410 clicks, 105 conversions)
2. Newcastle Under Lyme (140+ impressions)
3. Featherstone (498 impressions)
4. Lichfield (64 impressions)
5. Wolverhampton (24 impressions)
6. Cobridge/Stoke-on-Trent
7. Telford
8. Cannock
9. Wednesbury
10. Shrewsbury

Then London centres (high search volume nationally):
11. Sidcup, 12. Wood Green, 13. Bromley, 14. Mill Hill, 15. Enfield,
16. Hornchurch, 17. Belvedere, 18. Morden, 19. Hendon, 20. Goodmayes

**Step 2: Run content generation**

```bash
npx tsx scripts/generate-content.ts
```

**Step 3: Spot-check 5 centre content pieces for uniqueness**

Verify no two centres have >70% text overlap.

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: generate unique editorial content per test centre"
```

---

## Phase 4: Hub Pages & Internal Linking

### Task 4.1: Create master hub page

**Files:**
- Create: `app/test-centres/page.tsx`

**Step 1: Build the hub page**

`app/test-centres/page.tsx`:
- H1: "UK Driving Test Centres — Routes, Pass Rates & Tips"
- Group all centres by region
- Each region is a section with H2, list of centres as links
- Show pass rate and difficulty label per centre
- Search/filter functionality (client component)

Metadata:
```typescript
export const metadata: Metadata = {
  title: 'UK Driving Test Centres | Routes, Pass Rates & Maps for Every Centre',
  description: 'Find driving test routes, pass rates and tips for 300+ UK test centres. Practice real DVSA test routes with turn-by-turn navigation.',
}
```

**Step 2: Verify renders**

Visit: `/test-centres/`
Expected: All centres listed by region, all links work

**Step 3: Commit**

```bash
git add app/test-centres/page.tsx
git commit -m "feat: add master test centres hub page"
```

---

### Task 4.2: Create regional hub pages

**Files:**
- Create: `app/test-centres/[region]/page.tsx` (note: this must not conflict with `[slug]`)
- Restructure: Move centre pages to `app/test-centres/centres/[slug]/page.tsx` OR use route groups

**Important routing decision:** Since both `[region]` and `[slug]` are dynamic at the same level, we need to disambiguate. Options:

**Option A (recommended):** Use a catch-all or route interception:
- `/test-centres/` — hub
- `/test-centres/regions/greater-london/` — regional hub
- `/test-centres/stafford/` — centre page

**Option B:** Check in a single `[param]` page whether the param is a region or centre slug.

Go with **Option A** for clarity.

**Files (revised):**
- Create: `app/test-centres/regions/[region]/page.tsx`

**Step 1: Build regional hub page**

```typescript
export async function generateStaticParams() {
  return getAllRegions().map(region => ({
    region: region.slug,
  }))
}
```

Content:
- H1: "Driving Test Centres in {Region}"
- Table of all centres in region: name (linked), pass rate, tests conducted, difficulty
- Regional stats: average pass rate, easiest/hardest centre
- Link back to master hub

**Step 2: Verify renders**

Visit: `/test-centres/regions/west-midlands/`
Expected: All West Midlands centres listed

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: add regional hub pages with internal linking"
```

---

### Task 4.3: Create comparison/aggregate pages

**Files:**
- Create: `app/pass-rates/page.tsx`
- Create: `app/test-centres/easiest/page.tsx`
- Create: `app/test-centres/hardest/page.tsx`

These target high-volume aggregate keywords:
- "UK driving test pass rates by centre"
- "Easiest driving test centres in the UK"
- "Hardest driving test centres in the UK"

Each page uses the same DVSA data but presents it differently:
- `/pass-rates/` — sortable table of ALL centres with pass rates
- `/test-centres/easiest/` — top 20 highest pass rate centres with analysis
- `/test-centres/hardest/` — top 20 lowest pass rate centres with analysis

**Step 1: Build pass rates page**

Full sortable HTML table (no JS required for initial render — Google can parse HTML tables for featured snippets).

**Step 2: Build easiest/hardest pages**

Each with 800+ words of unique editorial content.

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: add pass rate comparison and ranking pages"
```

---

## Phase 5: SEO Infrastructure

### Task 5.1: XML Sitemap generation

**Files:**
- Create: `app/sitemap.ts`

**Step 1: Create sitemap**

```typescript
import type { MetadataRoute } from 'next'
import { getAllCentres, getAllRegions } from '@/lib/centres'

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://www.testroutesexpert.co.uk'

  const staticPages = [
    { url: baseUrl, lastModified: new Date(), changeFrequency: 'monthly' as const, priority: 1.0 },
    { url: `${baseUrl}/test-centres/`, lastModified: new Date(), changeFrequency: 'weekly' as const, priority: 0.9 },
    { url: `${baseUrl}/test-routes-app/`, lastModified: new Date(), changeFrequency: 'monthly' as const, priority: 0.8 },
    { url: `${baseUrl}/pass-rates/`, lastModified: new Date(), changeFrequency: 'monthly' as const, priority: 0.7 },
  ]

  const regionPages = getAllRegions().map(region => ({
    url: `${baseUrl}/test-centres/regions/${region.slug}/`,
    lastModified: new Date(),
    changeFrequency: 'monthly' as const,
    priority: 0.7,
  }))

  const centrePages = getAllCentres().map(centre => ({
    url: `${baseUrl}/test-centres/${centre.slug}/`,
    lastModified: new Date(),
    changeFrequency: 'monthly' as const,
    priority: 0.8,
  }))

  return [...staticPages, ...regionPages, ...centrePages]
}
```

**Step 2: Verify sitemap generates**

Run: `npm run build`
Check: `out/sitemap.xml` contains 300+ URLs

**Step 3: Commit**

```bash
git add app/sitemap.ts
git commit -m "feat: add XML sitemap with all centre and region pages"
```

---

### Task 5.2: robots.txt

**Files:**
- Create: `app/robots.ts`

**Step 1: Create robots.txt**

```typescript
import type { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/api/'],
    },
    sitemap: 'https://www.testroutesexpert.co.uk/sitemap.xml',
  }
}
```

**Step 2: Commit**

```bash
git add app/robots.ts
git commit -m "feat: add robots.txt with sitemap reference"
```

---

### Task 5.3: OG image generation

**Files:**
- Create: `app/test-centres/[slug]/opengraph-image.tsx`

**Step 1: Create OG image template**

Using `@vercel/og` (built into Next.js `ImageResponse`):

```typescript
import { ImageResponse } from 'next/og'
import { getCentreBySlug } from '@/lib/centres'

export const runtime = 'edge'
export const alt = 'Test centre info'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

export default async function Image({ params }: { params: { slug: string } }) {
  const centre = getCentreBySlug(params.slug)
  if (!centre) return new Response('Not found', { status: 404 })

  return new ImageResponse(
    (
      <div style={{
        background: '#0f0f0f',
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '60px',
        color: 'white',
        fontFamily: 'sans-serif',
      }}>
        <div style={{ fontSize: 28, color: '#FCA311', marginBottom: 16 }}>
          TEST ROUTES EXPERT
        </div>
        <div style={{ fontSize: 52, fontWeight: 900, marginBottom: 24 }}>
          {centre.name}
        </div>
        <div style={{ fontSize: 32, color: '#FCA311' }}>
          Pass Rate: {centre.passRateOverall}%
        </div>
        <div style={{ fontSize: 24, color: 'rgba(255,255,255,0.6)', marginTop: 12 }}>
          {centre.totalRoutes ?? '10+'} practice routes available
        </div>
      </div>
    ),
    { ...size }
  )
}
```

**Note:** OG image generation requires `runtime: 'edge'` and won't work with `output: 'export'`. If using static export, pre-generate OG images as PNGs in a build script instead.

**Step 2: Commit**

```bash
git add -A
git commit -m "feat: add per-centre OG image generation"
```

---

### Task 5.4: Root layout with global metadata

**Files:**
- Modify: `app/layout.tsx`

**Step 1: Add comprehensive global metadata**

```typescript
import type { Metadata } from 'next'

export const metadata: Metadata = {
  metadataBase: new URL('https://www.testroutesexpert.co.uk'),
  title: {
    default: 'Test Routes Expert | UK Driving Test Routes & Pass Rates',
    template: '%s | Test Routes Expert',
  },
  description: 'Practice real UK driving test routes with turn-by-turn navigation. 350+ centres, pass rates, tips and maps.',
  keywords: ['driving test routes', 'UK driving test', 'test centre pass rates', 'DVSA test routes', 'driving test practice'],
  authors: [{ name: 'Driving Test Expert' }],
  creator: 'Driving Test Expert',
  publisher: 'Driving Test Expert',
  formatDetection: { telephone: false },
  openGraph: {
    type: 'website',
    locale: 'en_GB',
    siteName: 'Test Routes Expert',
  },
  twitter: {
    card: 'summary_large_image',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
}
```

**Step 2: Add Google Fonts properly**

Use `next/font/google` instead of CDN link:

```typescript
import { Inter, Poppins } from 'next/font/google'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const poppins = Poppins({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800', '900'],
  variable: '--font-poppins',
})
```

**Step 3: Commit**

```bash
git add app/layout.tsx
git commit -m "feat: add global metadata and font optimisation"
```

---

## Phase 6: Build, Test & Deploy

### Task 6.1: Full static build

**Step 1: Run full build**

```bash
npm run build
```

Expected: All 300+ centre pages, 15+ region pages, hub pages, static pages generated.

**Step 2: Check output**

```bash
ls out/test-centres/ | wc -l
```

Expected: 300+ directories

**Step 3: Preview locally**

```bash
npx serve out
```

Visit several centre pages, verify:
- [ ] Unique content per page
- [ ] Pass rate data populated
- [ ] Nearby centres linked correctly
- [ ] Schema markup present in page source
- [ ] Meta tags correct
- [ ] Breadcrumbs work
- [ ] App download CTAs work

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: verify full static build — 300+ pages generated"
```

---

### Task 6.2: Lighthouse & Core Web Vitals check

**Step 1: Run Lighthouse on 3 representative pages**

```bash
npx lighthouse http://localhost:3000/test-centres/stafford/ --output=json --output-path=./lighthouse-stafford.json
```

Targets:
- Performance: >90
- SEO: >95
- Accessibility: >90
- Best Practices: >90
- LCP < 2.5s
- CLS < 0.1

**Step 2: Fix any issues found**

Common fixes: lazy-load images below fold, preload hero image, add `width`/`height` to all images, ensure colour contrast meets WCAG.

**Step 3: Commit fixes**

```bash
git commit -am "perf: optimise Core Web Vitals scores"
```

---

### Task 6.3: Deploy to Vercel

**Step 1: Update Vercel configuration**

The new Next.js project replaces the old Vite SPA. Ensure Vercel detects Next.js framework automatically.

**Step 2: Set environment variables in Vercel dashboard**

Add all `.env.local` variables to Vercel project settings.

**Step 3: Deploy**

```bash
git push origin main
```

Vercel auto-deploys on push.

**Step 4: Verify production**

- [ ] Homepage loads
- [ ] `/test-centres/` hub loads
- [ ] `/test-centres/stafford/` loads with data
- [ ] Schema markup validates at https://search.google.com/test/rich-results
- [ ] Sitemap accessible at `/sitemap.xml`
- [ ] robots.txt accessible at `/robots.txt`
- [ ] OG images generate correctly (check with https://www.opengraph.xyz/)

**Step 5: Submit sitemap to Google Search Console**

Manual step for the user.

---

## Phase 7: Progressive Rollout (Post-Launch)

### Task 7.1: Monitor and iterate

- **Week 1-2:** Monitor Search Console for indexation rate. Target 70%+ of submitted pages indexed.
- **Week 3-4:** Check which centre pages are getting impressions. Prioritise content enrichment for those.
- **Month 2:** Add `noindex` to any pages with <800 words or <6 unique data points until they can be enriched.
- **Month 3:** Begin blog content for topical authority (roundabouts guide, manoeuvres guide, etc.)

### Task 7.2: Supabase route data integration (when credentials available)

- Run `scripts/merge-supabase-routes.ts`
- Update centre pages to show actual route previews
- Add route count to hero sections
- Rebuild and deploy

### Task 7.3: Blog content for topical authority

**Files to create:**
- `app/blog/page.tsx` (blog index)
- `app/blog/[slug]/page.tsx` (blog post template)

Target articles:
1. "UK Driving Test Pass Rates 2026 — Every Centre Ranked"
2. "Roundabouts on the Driving Test: Complete Guide"
3. "Show Me Tell Me Questions 2026"
4. "Driving Test Manoeuvres Explained"
5. "How to Find Driving Test Cancellations"

Each blog post links contextually to relevant centre pages.

---

## Summary

| Phase | Tasks | Estimated Pages Generated |
|-------|-------|--------------------------|
| 1. Next.js Setup | 3 tasks | 2 (homepage + app page) |
| 2. DVSA Data Pipeline | 3 tasks | 0 (data only) |
| 3. Centre Pages | 3 tasks | 300+ centre pages |
| 4. Hub & Linking | 3 tasks | ~20 (hub + regions + rankings) |
| 5. SEO Infrastructure | 4 tasks | 0 (sitemap, robots, OG, metadata) |
| 6. Build & Deploy | 3 tasks | 0 (verification) |
| 7. Post-Launch | 3 tasks | 5+ blog posts |

**Total: ~320+ unique, data-rich, SEO-optimised pages.**
