import 'dotenv/config'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

async function main() {
  console.log('RLS Audit -- checking all co_ tables...\n')

  const { data, error } = await supabase.rpc('pg_tables_check') // This won't exist

  // Since we can't query pg_tables directly via PostgREST, print the SQL to run
  console.log('Run this SQL in Supabase Dashboard (SQL Editor) or via MCP:\n')
  console.log(`SELECT
  tablename,
  rowsecurity,
  CASE WHEN rowsecurity THEN 'SECURE' ELSE 'EXPOSED' END AS status
FROM pg_tables
WHERE schemaname = 'public' AND tablename LIKE 'co_%'
ORDER BY tablename;`)

  console.log('\nExpected: All 8 co_ tables should show SECURE.\n')

  // Also try to verify by attempting to read each table
  const tables = [
    'co_test_centres', 'co_campaigns', 'co_keywords', 'co_ad_copy',
    'co_daily_performance', 'co_automation_rules', 'co_automation_log', 'co_negative_keywords'
  ]

  console.log('Verifying tables exist and are accessible via service role key:')
  for (const table of tables) {
    const { count, error } = await supabase.from(table).select('*', { count: 'exact', head: true })
    if (error) {
      console.log(`  ${table}: ERROR - ${error.message}`)
    } else {
      console.log(`  ${table}: OK (${count} rows)`)
    }
  }
}

main()
