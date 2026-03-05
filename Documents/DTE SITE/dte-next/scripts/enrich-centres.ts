import * as fs from 'fs'
import * as path from 'path'

// ── Types ────────────────────────────────────────────────────────

interface NearbyCentre {
  slug: string
  name: string
  distanceMiles: number
  passRate: number
}

interface DvsaCentre {
  name: string
  slug: string
  region: string
  passRateOverall: number
  latitude?: number
  longitude?: number
  nearbyCentres?: NearbyCentre[]
  [key: string]: unknown
}

interface GeocacheEntry {
  lat: number
  lon: number
  source: 'nominatim' | 'fallback'
  query: string
  timestamp: string
}

interface RegionEntry {
  name: string
  slug: string
  centres: string[]
}

// ── Config ───────────────────────────────────────────────────────

const PROJECT_ROOT = path.resolve(__dirname, '..')
const CENTRES_PATH = path.join(PROJECT_ROOT, 'data', 'dvsa', 'centres.json')
const GEOCACHE_PATH = path.join(PROJECT_ROOT, 'data', 'dvsa', 'geocache.json')
const REGIONS_PATH = path.join(PROJECT_ROOT, 'data', 'regions.json')

const NOMINATIM_BASE = 'https://nominatim.openstreetmap.org/search'
const USER_AGENT = 'TestRoutesExpert/1.0 (support@drivingtestexpert.com)'
const REQUEST_DELAY_MS = 1100 // slightly over 1s to be safe
const FALLBACK_LAT = 52.5
const FALLBACK_LON = -1.5

// ── Valid regions ────────────────────────────────────────────────

const VALID_REGIONS = [
  'East Anglia',
  'East Midlands',
  'East of England',
  'Greater London',
  'North East',
  'North West',
  'Northern Ireland',
  'Scotland',
  'South East',
  'South West',
  'Wales',
  'West Midlands',
  'Yorkshire and the Humber',
] as const

// Map old/incorrect regions to correct ones
const REGION_CORRECTIONS: Record<string, string> = {
  'London': 'Greater London',
  'Yorkshire and Humber': 'Yorkshire and the Humber',
  'England': '', // needs manual fix based on centre name
}

// Manual region fixes for centres that fall through the cracks
const MANUAL_REGION_FIXES: Record<string, string> = {
  'walton-lgv': 'South East', // Walton-on-Thames, Surrey
  'cheetham-hill-manchester': 'North West', // Cheetham Hill is in Manchester, not London
  'chertsey-london': 'South East', // Chertsey is in Surrey, not London
  'nottingham-colwick': 'East Midlands', // Nottingham is in the East Midlands
  'warwick-wedgenock-house': 'West Midlands', // Warwick is in the West Midlands
  'west-wickham-london': 'Greater London', // West Wickham is in Greater London
  'alnwick': 'North East', // Alnwick is in Northumberland
  'berwick-on-tweed': 'North East', // Berwick-upon-Tweed is in Northumberland
  'tilbury': 'East of England', // Tilbury is in Essex
  'winchester': 'South East', // Winchester is in Hampshire
  'banbury': 'South East', // Banbury is in Oxfordshire
  'newport-isle-of-wight': 'South East', // Newport IoW is on the Isle of Wight
  'slough-london': 'South East', // Slough is in Berkshire, not London
}

// Manual coordinate overrides for centres Nominatim can't resolve
// Sourced from known addresses / Google Maps
const MANUAL_COORDINATES: Record<string, { lat: number; lon: number }> = {
  'Aberdeen South (Cove)': { lat: 57.0862, lon: -2.1028 },
  'Beverley LGV': { lat: 53.8428, lon: -0.4285 },
  'Cambridge (Brookmount Court)': { lat: 52.1993, lon: 0.1346 },
  'Carlisle LGV (Cars)': { lat: 54.8944, lon: -2.9357 },
  'Chelmsford (Hanbury Road)': { lat: 51.7283, lon: 0.4799 },
  'Culham LGV': { lat: 51.6568, lon: -1.2327 },
  'Enfield (Innova Business Park)': { lat: 51.6633, lon: -0.0473 },
  'Exeter LGV': { lat: 50.7256, lon: -3.5269 },
  'Isleworth (Fleming Way)': { lat: 51.4732, lon: -0.3313 },
  'Leicester (Cannock Street)': { lat: 52.6362, lon: -1.1250 },
  'Plymouth LGV': { lat: 50.3714, lon: -4.1424 },
  'Stoke-On-Trent (Cobridge)': { lat: 53.0319, lon: -2.1753 },
  'Swindon LGV': { lat: 51.5615, lon: -1.7854 },
  'Walton LGV': { lat: 51.3799, lon: -0.4089 },
  'Warwick (Wedgenock House)': { lat: 52.2890, lon: -1.5849 },
}

// ── Helpers ──────────────────────────────────────────────────────

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function roundCoord(n: number): number {
  return Math.round(n * 10000) / 10000
}

function roundDistance(n: number): number {
  return Math.round(n * 10) / 10
}

function toSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

function haversineDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 3959 // Earth radius in miles
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLon = ((lon2 - lon1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

// ── Geocoding ────────────────────────────────────────────────────

function loadGeocache(): Record<string, GeocacheEntry> {
  if (fs.existsSync(GEOCACHE_PATH)) {
    const raw = fs.readFileSync(GEOCACHE_PATH, 'utf-8')
    return JSON.parse(raw) as Record<string, GeocacheEntry>
  }
  return {}
}

function saveGeocache(cache: Record<string, GeocacheEntry>): void {
  fs.writeFileSync(GEOCACHE_PATH, JSON.stringify(cache, null, 2))
}

async function geocodeCentre(
  centreName: string,
  cache: Record<string, GeocacheEntry>
): Promise<{ lat: number; lon: number; fromCache: boolean; source: 'nominatim' | 'fallback' }> {
  // Check manual overrides first
  if (MANUAL_COORDINATES[centreName]) {
    const manual = MANUAL_COORDINATES[centreName]
    cache[centreName] = {
      lat: manual.lat,
      lon: manual.lon,
      source: 'nominatim',
      query: 'manual-override',
      timestamp: new Date().toISOString(),
    }
    saveGeocache(cache)
    return { lat: manual.lat, lon: manual.lon, fromCache: false, source: 'nominatim' }
  }

  // Check cache — but skip if cached as fallback (we want to retry those)
  if (cache[centreName] && cache[centreName].source !== 'fallback') {
    return {
      lat: cache[centreName].lat,
      lon: cache[centreName].lon,
      fromCache: true,
      source: cache[centreName].source,
    }
  }

  // If cache has a non-fallback entry, use it
  if (cache[centreName] && cache[centreName].source === 'fallback') {
    // Skip — we'll re-geocode below
    delete cache[centreName]
  }

  const query = `${centreName} driving test centre, UK`
  const url = `${NOMINATIM_BASE}?q=${encodeURIComponent(query)}&format=json&limit=1&countrycodes=gb`

  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': USER_AGENT,
      },
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const results = (await response.json()) as Array<{ lat: string; lon: string }>

    if (results.length > 0) {
      const lat = roundCoord(parseFloat(results[0].lat))
      const lon = roundCoord(parseFloat(results[0].lon))

      cache[centreName] = {
        lat,
        lon,
        source: 'nominatim',
        query,
        timestamp: new Date().toISOString(),
      }
      saveGeocache(cache)

      return { lat, lon, fromCache: false, source: 'nominatim' }
    }

    // No results — try a simpler query without "driving test centre"
    const fallbackQuery = `${centreName}, UK`
    const fallbackUrl = `${NOMINATIM_BASE}?q=${encodeURIComponent(fallbackQuery)}&format=json&limit=1&countrycodes=gb`

    await sleep(REQUEST_DELAY_MS)

    const fallbackResponse = await fetch(fallbackUrl, {
      headers: { 'User-Agent': USER_AGENT },
    })

    if (fallbackResponse.ok) {
      const fallbackResults = (await fallbackResponse.json()) as Array<{
        lat: string
        lon: string
      }>

      if (fallbackResults.length > 0) {
        const lat = roundCoord(parseFloat(fallbackResults[0].lat))
        const lon = roundCoord(parseFloat(fallbackResults[0].lon))

        cache[centreName] = {
          lat,
          lon,
          source: 'nominatim',
          query: fallbackQuery,
          timestamp: new Date().toISOString(),
        }
        saveGeocache(cache)

        return { lat, lon, fromCache: false, source: 'nominatim' }
      }
    }

    // Complete failure — use UK centre fallback
    console.warn(`  WARNING: Geocoding failed for "${centreName}" — using fallback coordinates`)
    cache[centreName] = {
      lat: FALLBACK_LAT,
      lon: FALLBACK_LON,
      source: 'fallback',
      query,
      timestamp: new Date().toISOString(),
    }
    saveGeocache(cache)

    return { lat: FALLBACK_LAT, lon: FALLBACK_LON, fromCache: false, source: 'fallback' }
  } catch (error) {
    console.warn(
      `  WARNING: Geocoding error for "${centreName}": ${error instanceof Error ? error.message : String(error)} — using fallback`
    )
    cache[centreName] = {
      lat: FALLBACK_LAT,
      lon: FALLBACK_LON,
      source: 'fallback',
      query,
      timestamp: new Date().toISOString(),
    }
    saveGeocache(cache)

    return { lat: FALLBACK_LAT, lon: FALLBACK_LON, fromCache: false, source: 'fallback' }
  }
}

// ── Region correction ────────────────────────────────────────────

function correctRegion(centre: DvsaCentre): string {
  // Check manual fixes first
  if (MANUAL_REGION_FIXES[centre.slug]) {
    return MANUAL_REGION_FIXES[centre.slug]
  }

  // Check if region needs correction via mapping
  const currentRegion = centre.region
  if (REGION_CORRECTIONS[currentRegion] !== undefined) {
    const corrected = REGION_CORRECTIONS[currentRegion]
    if (corrected === '') {
      // Unknown — log warning
      console.warn(
        `  WARNING: Centre "${centre.name}" has region "England" — needs manual assignment`
      )
      return 'South East' // default fallback for unresolved England centres
    }
    return corrected
  }

  // Validate it's a known region
  if (!(VALID_REGIONS as readonly string[]).includes(currentRegion)) {
    console.warn(
      `  WARNING: Centre "${centre.name}" has unknown region "${currentRegion}"`
    )
    return currentRegion
  }

  return currentRegion
}

// ── Nearest centres ──────────────────────────────────────────────

function calculateNearbyCentres(
  centres: DvsaCentre[]
): Map<string, NearbyCentre[]> {
  const nearbyMap = new Map<string, NearbyCentre[]>()

  for (const centre of centres) {
    const distances: Array<{
      slug: string
      name: string
      distanceMiles: number
      passRate: number
    }> = []

    for (const other of centres) {
      if (other.slug === centre.slug) continue
      if (!centre.latitude || !centre.longitude || !other.latitude || !other.longitude) continue

      const dist = haversineDistance(
        centre.latitude,
        centre.longitude,
        other.latitude,
        other.longitude
      )

      distances.push({
        slug: other.slug,
        name: other.name,
        distanceMiles: roundDistance(dist),
        passRate: other.passRateOverall,
      })
    }

    // Sort by distance, take 5 nearest
    distances.sort((a, b) => a.distanceMiles - b.distanceMiles)
    nearbyMap.set(centre.slug, distances.slice(0, 5))
  }

  return nearbyMap
}

// ── Region data generation ───────────────────────────────────────

function generateRegionsData(centres: DvsaCentre[]): { regions: RegionEntry[] } {
  const regionMap = new Map<string, string[]>()

  for (const centre of centres) {
    const region = centre.region
    const existing = regionMap.get(region) ?? []
    regionMap.set(region, [...existing, centre.slug])
  }

  const regions: RegionEntry[] = Array.from(regionMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, slugs]) => ({
      name,
      slug: toSlug(name),
      centres: slugs.sort(),
    }))

  return { regions }
}

// ── Main ─────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log('=== Enriching centres with geographic data ===\n')

  // Load centres
  const rawCentres = JSON.parse(
    fs.readFileSync(CENTRES_PATH, 'utf-8')
  ) as DvsaCentre[]

  console.log(`Loaded ${rawCentres.length} centres from centres.json`)

  // ── Step 1: Fix regions ────────────────────────────────────────

  console.log('\n--- Step 1: Verifying/fixing regions ---\n')

  let regionFixCount = 0
  const centresWithRegions = rawCentres.map((centre) => {
    const correctedRegion = correctRegion(centre)
    if (correctedRegion !== centre.region) {
      console.log(`  Fixed: "${centre.name}" region "${centre.region}" -> "${correctedRegion}"`)
      regionFixCount++
    }
    return { ...centre, region: correctedRegion }
  })

  console.log(`\n  Region fixes applied: ${regionFixCount}`)

  // ── Step 2: Geocode centres ────────────────────────────────────

  console.log('\n--- Step 2: Geocoding centres ---\n')

  const geocache = loadGeocache()
  const cachedCount = Object.keys(geocache).length
  console.log(`  Geocache entries: ${cachedCount}`)

  let geocodedFromApi = 0
  let geocodedFromCache = 0
  let fallbackCount = 0

  const centresWithCoords: DvsaCentre[] = []

  for (let i = 0; i < centresWithRegions.length; i++) {
    const centre = centresWithRegions[i]
    const { lat, lon, fromCache, source } = await geocodeCentre(centre.name, geocache)

    if (fromCache) {
      geocodedFromCache++
    } else {
      geocodedFromApi++
      // Respect rate limit — only sleep if we actually made an API call
      if (i < centresWithRegions.length - 1) {
        await sleep(REQUEST_DELAY_MS)
      }
    }

    if (source === 'fallback') {
      fallbackCount++
    }

    centresWithCoords.push({
      ...centre,
      latitude: lat,
      longitude: lon,
    })

    // Progress logging every 25 centres
    if ((i + 1) % 25 === 0 || i === centresWithRegions.length - 1) {
      console.log(
        `  Progress: ${i + 1}/${centresWithRegions.length} (API: ${geocodedFromApi}, Cache: ${geocodedFromCache})`
      )
    }
  }

  const successfullyGeocoded = centresWithCoords.filter(
    (c) =>
      c.latitude !== FALLBACK_LAT || c.longitude !== FALLBACK_LON
  ).length

  console.log(`\n  Geocoding complete:`)
  console.log(`    From API: ${geocodedFromApi}`)
  console.log(`    From cache: ${geocodedFromCache}`)
  console.log(`    Using fallback coords: ${fallbackCount}`)
  console.log(`    Successfully geocoded: ${successfullyGeocoded}/${centresWithCoords.length}`)

  // ── Step 3: Calculate nearest centres ──────────────────────────

  console.log('\n--- Step 3: Calculating nearest centres ---\n')

  const nearbyMap = calculateNearbyCentres(centresWithCoords)

  const enrichedCentres = centresWithCoords.map((centre) => ({
    ...centre,
    nearbyCentres: nearbyMap.get(centre.slug) ?? [],
  }))

  console.log(`  Calculated nearest 5 centres for ${nearbyMap.size} centres`)

  // ── Step 4: Generate regions.json ──────────────────────────────

  console.log('\n--- Step 4: Generating regions.json ---\n')

  const regionsData = generateRegionsData(enrichedCentres)
  fs.writeFileSync(REGIONS_PATH, JSON.stringify(regionsData, null, 2))

  console.log(`  Written ${regionsData.regions.length} regions to ${REGIONS_PATH}`)
  for (const region of regionsData.regions) {
    console.log(`    ${region.name}: ${region.centres.length} centres`)
  }

  // ── Step 5: Update centres.json ────────────────────────────────

  console.log('\n--- Step 5: Updating centres.json ---\n')

  fs.writeFileSync(CENTRES_PATH, JSON.stringify(enrichedCentres, null, 2))

  const fileSizeKB = (fs.statSync(CENTRES_PATH).size / 1024).toFixed(1)
  console.log(`  Written ${enrichedCentres.length} centres to ${CENTRES_PATH}`)
  console.log(`  File size: ${fileSizeKB} KB`)

  // ── Verification ───────────────────────────────────────────────

  console.log('\n=== Verification ===\n')

  // Print total geocoded
  console.log(`Successfully geocoded centres: ${successfullyGeocoded}/${enrichedCentres.length}`)

  // Print Stafford's data
  const stafford = enrichedCentres.find((c) => c.slug === 'stafford')
  if (stafford) {
    console.log(`\nStafford:`)
    console.log(`  Coordinates: ${stafford.latitude}, ${stafford.longitude}`)
    console.log(`  5 nearest centres:`)
    for (const nearby of stafford.nearbyCentres ?? []) {
      console.log(
        `    - ${nearby.name}: ${nearby.distanceMiles} miles (pass rate: ${nearby.passRate}%)`
      )
    }
  }

  // Print region counts
  console.log(`\nRegion counts:`)
  const regionCounts: Record<string, number> = {}
  for (const centre of enrichedCentres) {
    regionCounts[centre.region] = (regionCounts[centre.region] ?? 0) + 1
  }
  Object.entries(regionCounts)
    .sort(([a], [b]) => a.localeCompare(b))
    .forEach(([region, count]) => {
      console.log(`  ${region}: ${count}`)
    })

  // Check for any centres still using fallback coords
  if (fallbackCount > 0) {
    console.log(`\nWARNING: ${fallbackCount} centres using fallback coordinates:`)
    for (const centre of enrichedCentres) {
      if (
        centre.latitude === FALLBACK_LAT &&
        centre.longitude === FALLBACK_LON
      ) {
        console.log(`  - ${centre.name} (${centre.slug})`)
      }
    }
  }

  // Check for LGV centres sharing coordinates
  const lgvCentres = enrichedCentres.filter((c) => c.name.includes('LGV'))
  if (lgvCentres.length > 0) {
    console.log(`\nLGV centres (may share coordinates with non-LGV counterparts): ${lgvCentres.length}`)
    for (const lgv of lgvCentres) {
      const baseName = lgv.name.replace(' LGV', '')
      const base = enrichedCentres.find((c) => c.name === baseName)
      if (base) {
        const sharesCoords =
          base.latitude === lgv.latitude && base.longitude === lgv.longitude
        console.log(
          `  - ${lgv.name}: ${sharesCoords ? 'shares coords with' : 'different from'} ${base.name}`
        )
      }
    }
  }

  console.log('\n=== Enrichment complete ===')
}

main().catch((err) => {
  console.error('FATAL:', err)
  process.exit(1)
})
