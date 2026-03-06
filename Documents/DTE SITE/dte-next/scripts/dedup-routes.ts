/**
 * Delete duplicate routes from Supabase.
 * These routes have been confirmed to have identical keyRoads to other routes
 * in the same test centre.
 *
 * Usage: npx tsx scripts/dedup-routes.ts
 */

import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = 'https://zpfkvhnfbbimsfghmjiz.supabase.co'
const SUPABASE_SERVICE_ROLE_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpwZmt2aG5mYmJpbXNmZ2htaml6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NDA4OTI5MSwiZXhwIjoyMDc5NjY1MjkxfQ.D7BWcVUbydo_7zwVYJ3TFgMhOVY-6Wy5IfqdjCAAI4c'

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

interface DuplicateSpec {
  testCenterId: string
  routeNumbers: number[]
}

const DUPLICATES: DuplicateSpec[] = [
  {
    testCenterId: 'stafford',
    routeNumbers: [17, 25, 26, 28, 29, 30, 31],
  },
  {
    testCenterId: 'stoke-on-trent-cobridge',
    routeNumbers: [2, 31, 32, 33, 34, 35, 36, 37, 38, 39],
  },
  {
    testCenterId: 'stoke-on-trent-newcastle-under-lyme',
    routeNumbers: [2, 38, 39, 40, 41, 42, 43, 45, 46, 47, 48, 49],
  },
]

async function main() {
  let totalDeleted = 0

  for (const spec of DUPLICATES) {
    console.log(
      `\nDeleting ${spec.routeNumbers.length} duplicate routes from "${spec.testCenterId}"...`
    )
    console.log(`  Route numbers: ${spec.routeNumbers.join(', ')}`)

    const { data, error } = await supabase
      .from('routes')
      .delete()
      .eq('test_center_id', spec.testCenterId)
      .in('route_number', spec.routeNumbers)
      .select('id, route_number')

    if (error) {
      console.error(`  ERROR: ${error.message}`)
      continue
    }

    const deletedCount = data?.length ?? 0
    console.log(`  Deleted ${deletedCount} rows.`)
    totalDeleted += deletedCount
  }

  console.log(`\nDone! Total deleted: ${totalDeleted} duplicate routes.`)
}

main().catch(console.error)
