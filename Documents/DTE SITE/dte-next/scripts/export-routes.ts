/**
 * Export route data from Supabase for all test centres.
 * Generates individual JSON files per centre in data/routes/.
 *
 * Usage: npx tsx scripts/export-routes.ts
 */

import { createClient } from '@supabase/supabase-js'
import * as fs from 'fs'
import * as path from 'path'

const SUPABASE_URL = 'https://zpfkvhnfbbimsfghmjiz.supabase.co'
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpwZmt2aG5mYmJpbXNmZ2htaml6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQwODkyOTEsImV4cCI6MjA3OTY2NTI5MX0.NsNYUGGZojVzBkryERIe6Qz_Km6AdZQQfhl6nElgmkw'

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

const OUT_DIR = path.join(__dirname, '..', 'data', 'routes')

interface RouteRow {
  id: string
  test_center_id: string
  name: string
  route_number: number
  distance_km: number
  estimated_duration_mins: number
  difficulty: string
  mapbox_route: {
    legs: Array<{
      steps: Array<{
        name: string
        maneuver: { type: string; instruction: string }
        distance: number
        duration: number
      }>
    }>
    geometry: {
      type: string
      coordinates: number[][]
    }
  }
}

interface CentreRow {
  id: string
  name: string
  address: string | null
  postcode: string | null
  route_count: number
}

async function main() {
  console.log('Fetching test centres...')
  const { data: centres, error: centreError } = await supabase
    .from('test_centers')
    .select('id, name, address, postcode, route_count')
    .order('name')

  if (centreError) {
    console.error('Failed to fetch centres:', centreError)
    process.exit(1)
  }

  console.log(`Found ${centres.length} centres. Fetching routes...`)

  // Ensure output directory exists
  fs.mkdirSync(OUT_DIR, { recursive: true })

  let exported = 0
  let skipped = 0

  for (const centre of centres as CentreRow[]) {
    // Fetch routes per centre to avoid timeout on large mapbox_route JSONB
    const { data: routes, error: routeError } = await supabase
      .from('routes')
      .select('id, test_center_id, name, route_number, distance_km, estimated_duration_mins, difficulty, mapbox_route')
      .eq('test_center_id', centre.id)
      .order('route_number')

    if (routeError) {
      console.error(`Failed to fetch routes for ${centre.id}:`, routeError.message)
      skipped++
      continue
    }

    if (!routes || routes.length === 0) {
      skipped++
      continue
    }

    // Extract road names and manoeuvre counts per route
    const routeData = routes.map(route => {
      const keyRoads = new Set<string>()
      let roundabouts = 0
      let turns = 0

      if (route.mapbox_route?.legs) {
        for (const leg of route.mapbox_route.legs) {
          if (!leg.steps) continue
          for (const step of leg.steps) {
            const mtype = step.maneuver?.type
            if (step.name && step.name !== '' && mtype !== 'arrive' && mtype !== 'depart') {
              keyRoads.add(step.name)
            }
            if (mtype === 'roundabout' || mtype === 'rotary') roundabouts++
            if (mtype === 'turn') turns++
          }
        }
      }

      return {
        routeNumber: route.route_number,
        distanceKm: Math.round(route.distance_km * 10) / 10,
        durationMins: route.estimated_duration_mins,
        keyRoads: Array.from(keyRoads).sort(),
        roundabouts,
        turns,
      }
    })

    // Collect all unique roads across all routes
    const allRoads = new Set<string>()
    for (const r of routeData) {
      for (const road of r.keyRoads) {
        allRoads.add(road)
      }
    }

    const output = {
      centreId: centre.id,
      centreName: centre.name,
      address: centre.address ?? '',
      postcode: centre.postcode ?? '',
      routeCount: routes.length,
      allRoads: Array.from(allRoads).sort(),
      routes: routeData.sort((a, b) => a.routeNumber - b.routeNumber),
    }

    const filePath = path.join(OUT_DIR, `${centre.id}.json`)
    fs.writeFileSync(filePath, JSON.stringify(output, null, 2))
    exported++
  }

  console.log(`\nDone! Exported ${exported} centres, skipped ${skipped} (no routes).`)
  console.log(`Files written to: ${OUT_DIR}`)
}

main().catch(console.error)
