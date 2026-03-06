# Deduplicate Routes + Homepage Navigation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** (1) Remove duplicate routes from Supabase and local JSON for centres with confirmed duplicates, (2) Add "Test Centres" dropdown navigation to the site Navbar linking to key SEO pages.

**Architecture:** Task 1 uses a Node script to delete duplicate route rows from Supabase `routes` table by matching `test_center_id` + `route_number`, then regenerates local JSON files via the existing export script. Task 2 extends the Navbar component with a hover/click dropdown and updates constants/types.

**Tech Stack:** Next.js 14 (App Router), TypeScript, Tailwind CSS, Supabase JS client, Lucide icons

---

## Task 1: Remove Duplicate Routes from Supabase

### Context

Six local JSON files have >36 routes. Three have confirmed duplicate entries (identical `keyRoads` arrays):

| Centre | Total | Duplicates | After Dedup |
|--------|-------|-----------|-------------|
| stafford | 45 | 7 (#17,25,26,28,29,30,31) | 38 |
| stoke-on-trent-cobridge | 49 | 10 (#2,31,32,33,34,35,36,37,38,39) | 39 |
| stoke-on-trent-newcastle-under-lyme | 53 | 12 (#2,38,39,40,41,42,43,45,46,47,48,49) | 41 |

Two centres (nelson=39, sidcup/sidcup-london=39) have **no duplicates** - leave them untouched.

**Supabase connection:**
- URL: `https://zpfkvhnfbbimsfghmjiz.supabase.co`
- Anon key: in `dte-next/scripts/export-routes.ts:13`
- Table: `routes` (columns: `test_center_id`, `route_number`)

### Step 1: Write the Supabase dedup script

Create: `dte-next/scripts/dedup-routes.ts`

```typescript
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = 'https://zpfkvhnfbbimsfghmjiz.supabase.co'
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpwZmt2aG5mYmJpbXNmZ2htaml6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQwODkyOTEsImV4cCI6MjA3OTY2NTI5MX0.NsNYUGGZojVzBkryERIe6Qz_Km6AdZQQfhl6nElgmkw'

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// Duplicate route numbers to delete, keyed by test_center_id
const DUPLICATES: Record<string, number[]> = {
  stafford: [17, 25, 26, 28, 29, 30, 31],
  'stoke-on-trent-cobridge': [2, 31, 32, 33, 34, 35, 36, 37, 38, 39],
  'stoke-on-trent-newcastle-under-lyme': [2, 38, 39, 40, 41, 42, 43, 45, 46, 47, 48, 49],
}

async function main() {
  for (const [centreId, routeNumbers] of Object.entries(DUPLICATES)) {
    console.log(`\nDeleting ${routeNumbers.length} duplicate routes from ${centreId}...`)

    const { data, error } = await supabase
      .from('routes')
      .delete()
      .eq('test_center_id', centreId)
      .in('route_number', routeNumbers)
      .select('id, route_number')

    if (error) {
      console.error(`  Error: ${error.message}`)
      continue
    }

    console.log(`  Deleted ${data?.length ?? 0} rows: route numbers ${routeNumbers.join(', ')}`)
  }

  console.log('\nDone. Now run: npx tsx scripts/export-routes.ts')
}

main().catch(console.error)
```

### Step 2: Run the dedup script

Run: `cd dte-next && npx tsx scripts/dedup-routes.ts`

Expected output:
```
Deleting 7 duplicate routes from stafford...
  Deleted 7 rows: route numbers 17, 25, 26, 28, 29, 30, 31
Deleting 10 duplicate routes from stoke-on-trent-cobridge...
  Deleted 10 rows: ...
Deleting 12 duplicate routes from stoke-on-trent-newcastle-under-lyme...
  Deleted 12 rows: ...
```

### Step 3: Re-export route data from Supabase

Run: `cd dte-next && npx tsx scripts/export-routes.ts`

This regenerates all `data/routes/*.json` files from Supabase, which will now reflect the deduplicated state.

### Step 4: Re-copy renamed route files

The previous session created copies for slug mismatches (e.g. `sidcup.json` -> `sidcup-london.json`). After re-export, re-run the rename mapping for the 3 affected centres that had copies:

- No action needed for `sidcup-london.json` (sidcup had no duplicates removed)
- Only need to verify stafford, stoke files look correct

Run: `node -e "const fs=require('fs'); ['stafford','stoke-on-trent-cobridge','stoke-on-trent-newcastle-under-lyme'].forEach(f => { const d=JSON.parse(fs.readFileSync('data/routes/'+f+'.json','utf8')); console.log(f+': '+d.routes.length+' routes') })"`

Expected: stafford=38, stoke-cobridge=39, stoke-newcastle=41

### Step 5: Build and verify

Run: `npx next build`

Expected: Build succeeds, 344 pages generated.

### Step 6: Commit

```bash
git add scripts/dedup-routes.ts data/routes/stafford.json data/routes/stoke-on-trent-cobridge.json data/routes/stoke-on-trent-newcastle-under-lyme.json
git commit -m "fix: remove duplicate routes from stafford, stoke-on-trent centres"
```

---

## Task 2: Add Test Centres Navigation to Navbar

### Context

The Navbar currently has two items: "Our Apps" (#apps) and "About" (#about). Need to add a "Test Centres" dropdown that links to the SEO pages.

**Files to modify:**
- `dte-next/lib/types.ts` - extend NavItem type for children
- `dte-next/lib/constants.ts` - add nav items with dropdown children
- `dte-next/components/Layout/Navbar.tsx` - add dropdown rendering
- `dte-next/components/Layout/Footer.tsx` - add test centre links

### Step 1: Update NavItem type

Modify: `dte-next/lib/types.ts`

```typescript
export interface NavItem {
  label: string
  href: string
  children?: NavItem[]
}
```

### Step 2: Update NAV_ITEMS constant

Modify: `dte-next/lib/constants.ts` (lines 1-4)

Replace:
```typescript
export const NAV_ITEMS = [
  { label: 'Our Apps', href: '#apps' },
  { label: 'About', href: '#about' },
]
```

With:
```typescript
export const NAV_ITEMS: import('./types').NavItem[] = [
  {
    label: 'Test Centres',
    href: '/test-centres/',
    children: [
      { label: 'All Test Centres', href: '/test-centres/' },
      { label: 'Easiest Centres', href: '/test-centres/easiest/' },
      { label: 'Hardest Centres', href: '/test-centres/hardest/' },
      { label: 'Pass Rates', href: '/pass-rates/' },
    ],
  },
  { label: 'Our Apps', href: '/test-routes-app' },
  { label: 'About', href: '#about' },
]
```

### Step 3: Update Navbar with dropdown

Modify: `dte-next/components/Layout/Navbar.tsx`

Key changes:
1. Import `ChevronDown` from lucide-react
2. Add `openDropdown` state
3. Render dropdown for items with `children`
4. Close dropdown on click outside / route change
5. Handle mobile menu dropdown items

Full updated component (see implementation step for exact code).

### Step 4: Add Test Centres links to Footer

Modify: `dte-next/components/Layout/Footer.tsx`

Add a "Test Centres" column with links to:
- All Test Centres (`/test-centres/`)
- Easiest Centres (`/test-centres/easiest/`)
- Pass Rates (`/pass-rates/`)

### Step 5: Build and verify

Run: `npx next build`

Expected: Build succeeds.

### Step 6: Commit

```bash
git add dte-next/lib/types.ts dte-next/lib/constants.ts dte-next/components/Layout/Navbar.tsx dte-next/components/Layout/Footer.tsx
git commit -m "feat: add test centres dropdown navigation to navbar and footer"
```
