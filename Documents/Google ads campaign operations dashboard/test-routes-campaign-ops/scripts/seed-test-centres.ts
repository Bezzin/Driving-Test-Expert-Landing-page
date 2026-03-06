/**
 * Seed co_test_centres from DVSA centres.json + existing test_centers table.
 *
 * Usage:
 *   pnpm tsx scripts/seed-test-centres.ts
 *
 * Requires .env.local with:
 *   NEXT_PUBLIC_SUPABASE_URL
 *   SUPABASE_SERVICE_ROLE_KEY
 */

import 'dotenv/config'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { createClient } from '@supabase/supabase-js'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DvsaCentre {
  readonly name: string
  readonly slug: string
  readonly region: string
  readonly passRateOverall: number
  readonly testsConductedTotal: number
  readonly difficultyRank: number
  readonly latitude: number
  readonly longitude: number
  readonly totalRoutes?: number
}

interface AppTestCenter {
  readonly id: string
  readonly name: string
  readonly route_count: number
}

type PriorityTier = 'tier_1' | 'tier_2' | 'tier_3'

interface CoTestCentreInsert {
  readonly app_test_center_id: string | null
  readonly name: string
  readonly slug: string
  readonly region: string
  readonly latitude: number
  readonly longitude: number
  readonly route_count: number
  readonly has_landing_page: boolean
  readonly landing_page_url: string | null
  readonly pass_rate: number
  readonly tests_conducted: number
  readonly difficulty_rank: number
  readonly estimated_monthly_searches: number | null
  readonly priority_tier: PriorityTier
  readonly status: string
  readonly notes: string | null
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY

if (!SUPABASE_URL || !SUPABASE_KEY) {
  console.error(
    'Missing env vars. Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env.local',
  )
  process.exit(1)
}

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

const DVSA_PATH = resolve(
  'C:/Users/Nathaniel/Documents/DTE SITE/dte-next/data/dvsa/centres.json',
)

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function normaliseName(name: string): string {
  return name
    .toLowerCase()
    .replace(/[''`]/g, '')
    .replace(/\s*\(.*?\)\s*/g, '')  // strip parenthetical like "(London)"
    .replace(/[^a-z0-9]/g, '')      // strip non-alphanumeric
    .trim()
}

function assignPriorityTiers(
  centres: readonly DvsaCentre[],
): ReadonlyMap<string, PriorityTier> {
  const sorted = [...centres].sort(
    (a, b) => b.testsConductedTotal - a.testsConductedTotal,
  )
  const total = sorted.length
  const tier1Cutoff = Math.ceil(total * 0.15)
  const tier2Cutoff = Math.ceil(total * 0.45) // top 15% + next 30%

  const tiers = new Map<string, PriorityTier>()
  for (let i = 0; i < sorted.length; i++) {
    const tier: PriorityTier =
      i < tier1Cutoff ? 'tier_1' : i < tier2Cutoff ? 'tier_2' : 'tier_3'
    tiers.set(sorted[i].slug, tier)
  }
  return tiers
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  // 1. Load DVSA centres from disk
  console.log(`Reading DVSA centres from ${DVSA_PATH}`)
  const raw = readFileSync(DVSA_PATH, 'utf-8')
  const dvsaCentres: DvsaCentre[] = JSON.parse(raw)
  console.log(`  Loaded ${dvsaCentres.length} DVSA centres`)

  // 2. Fetch existing app test_centers from Supabase
  console.log('Fetching existing test_centers from Supabase...')
  const { data: appCentres, error: fetchError } = await supabase
    .from('test_centers')
    .select('id, name, route_count')

  if (fetchError) {
    console.error('Failed to fetch test_centers:', fetchError.message)
    process.exit(1)
  }

  console.log(`  Found ${appCentres?.length ?? 0} existing app test centres`)

  // 3. Build normalised-name -> app centre lookup
  const appLookup = new Map<string, AppTestCenter>()
  for (const centre of appCentres ?? []) {
    appLookup.set(normaliseName(centre.name), centre)
  }

  // 4. Calculate priority tiers
  const tiers = assignPriorityTiers(dvsaCentres)

  // 5. Build insert rows by matching DVSA -> app centres
  let matched = 0
  let unmatched = 0

  const rows: CoTestCentreInsert[] = dvsaCentres.map((dvsa) => {
    const normName = normaliseName(dvsa.name)
    const appCentre = appLookup.get(normName) ?? null

    if (appCentre) {
      matched++
    } else {
      unmatched++
    }

    const hasLandingPage = appCentre !== null && (appCentre.route_count ?? 0) > 0
    const landingPageUrl = hasLandingPage
      ? `https://test-routes.co.uk/test-centres/${dvsa.slug}`
      : null

    return {
      app_test_center_id: appCentre?.id ?? null,
      name: dvsa.name,
      slug: dvsa.slug,
      region: dvsa.region,
      latitude: dvsa.latitude,
      longitude: dvsa.longitude,
      route_count: appCentre?.route_count ?? dvsa.totalRoutes ?? 0,
      has_landing_page: hasLandingPage,
      landing_page_url: landingPageUrl,
      pass_rate: dvsa.passRateOverall,
      tests_conducted: dvsa.testsConductedTotal,
      difficulty_rank: dvsa.difficultyRank,
      estimated_monthly_searches: null,
      priority_tier: tiers.get(dvsa.slug) ?? 'tier_3',
      status: 'pending',
      notes: appCentre ? null : 'No matching app test centre found',
    }
  })

  console.log(`\nMatching results:`)
  console.log(`  Matched:   ${matched}`)
  console.log(`  Unmatched: ${unmatched}`)
  console.log(`  Total:     ${rows.length}`)

  // 6. Insert in batches (Supabase has a default row limit per insert)
  const BATCH_SIZE = 50
  let inserted = 0

  for (let i = 0; i < rows.length; i += BATCH_SIZE) {
    const batch = rows.slice(i, i + BATCH_SIZE)
    const { error: insertError } = await supabase
      .from('co_test_centres')
      .insert(batch)

    if (insertError) {
      console.error(
        `Insert failed at batch starting index ${i}:`,
        insertError.message,
      )
      process.exit(1)
    }

    inserted += batch.length
    console.log(`  Inserted ${inserted}/${rows.length}`)
  }

  // 7. Summary
  const tier1Count = rows.filter((r) => r.priority_tier === 'tier_1').length
  const tier2Count = rows.filter((r) => r.priority_tier === 'tier_2').length
  const tier3Count = rows.filter((r) => r.priority_tier === 'tier_3').length

  console.log(`\nSeed complete:`)
  console.log(`  Tier 1 (top 15%):       ${tier1Count}`)
  console.log(`  Tier 2 (next 30%):      ${tier2Count}`)
  console.log(`  Tier 3 (remaining 55%): ${tier3Count}`)
  console.log(`  Total inserted:         ${inserted}`)
}

main().catch((err) => {
  console.error('Unexpected error:', err)
  process.exit(1)
})
