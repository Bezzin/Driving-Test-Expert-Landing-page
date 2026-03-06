/**
 * Seed co_automation_rules and co_negative_keywords with default data.
 *
 * Usage:
 *   pnpm tsx scripts/seed-automation-rules.ts
 *
 * Requires .env.local with:
 *   NEXT_PUBLIC_SUPABASE_URL
 *   SUPABASE_SERVICE_ROLE_KEY
 */

import 'dotenv/config'
import { createClient } from '@supabase/supabase-js'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AutomationRuleInsert {
  readonly name: string
  readonly description: string
  readonly rule_type: string
  readonly conditions: Record<string, unknown>
  readonly actions: Record<string, unknown>
  readonly lookback_days: number
  readonly requires_approval: boolean
  readonly is_active: boolean
}

interface NegativeKeywordInsert {
  readonly list_name: string
  readonly keyword: string
  readonly match_type: string
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

// ---------------------------------------------------------------------------
// Seed data
// ---------------------------------------------------------------------------

const AUTOMATION_RULES: readonly AutomationRuleInsert[] = [
  {
    name: 'Pause high CPA',
    description:
      'Pause campaigns where CPA exceeds 15.00 and spend exceeds 20.00 over 7 days',
    rule_type: 'pause',
    conditions: {
      cpa_micros_gt: 15_000_000,
      spend_micros_gt: 20_000_000,
    },
    actions: {
      action: 'pause',
    },
    lookback_days: 7,
    requires_approval: false,
    is_active: true,
  },
  {
    name: 'Scale up winners',
    description:
      'Increase budget by 1.5x (max 20.00/day) for campaigns with CPA under 6.00 and 5+ conversions over 7 days',
    rule_type: 'budget_increase',
    conditions: {
      cpa_micros_lt: 6_000_000,
      conversions_gte: 5,
    },
    actions: {
      action: 'budget_multiply',
      multiplier: 1.5,
      max_daily_budget_micros: 20_000_000,
    },
    lookback_days: 7,
    requires_approval: false,
    is_active: true,
  },
  {
    name: 'Scale down underperformers',
    description:
      'Decrease budget by 0.5x (min 3.00/day) for campaigns with CPA above 10.00 and spend above 15.00 over 7 days',
    rule_type: 'budget_decrease',
    conditions: {
      cpa_micros_gt: 10_000_000,
      spend_micros_gt: 15_000_000,
    },
    actions: {
      action: 'budget_multiply',
      multiplier: 0.5,
      min_daily_budget_micros: 3_000_000,
    },
    lookback_days: 7,
    requires_approval: false,
    is_active: true,
  },
  {
    name: 'Alert zero conversions',
    description:
      'Send notification when a campaign has zero conversions but spend exceeds 30.00 over 14 days',
    rule_type: 'notify',
    conditions: {
      conversions_eq: 0,
      spend_micros_gt: 30_000_000,
    },
    actions: {
      action: 'notify',
    },
    lookback_days: 14,
    requires_approval: true,
    is_active: true,
  },
  {
    name: 'Auto-launch tier 1',
    description:
      'Create campaign at 5.00/day budget for tier 1 centres that are pending and have a landing page',
    rule_type: 'create_campaign',
    conditions: {
      priority_tier: 'tier_1',
      status: 'pending',
      has_landing_page: true,
    },
    actions: {
      action: 'create_campaign',
      daily_budget_micros: 5_000_000,
    },
    lookback_days: 0,
    requires_approval: true,
    is_active: true,
  },
]

const NEGATIVE_KEYWORDS: readonly string[] = [
  'driving instructor',
  'driving lessons',
  'book driving test',
  'theory test',
  'DVSA',
  'automatic instructor',
  'manual instructor',
  'intensive course',
  'crash course',
  'driving school',
  'driving test cancellations',
  'driving test tips',
]

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  // 1. Seed automation rules
  console.log('Seeding automation rules...')

  const { error: rulesError } = await supabase
    .from('co_automation_rules')
    .insert([...AUTOMATION_RULES])

  if (rulesError) {
    console.error('Failed to insert automation rules:', rulesError.message)
    process.exit(1)
  }

  console.log(`  Inserted ${AUTOMATION_RULES.length} automation rules`)

  // 2. Seed negative keywords
  console.log('Seeding negative keywords...')

  const keywordRows: NegativeKeywordInsert[] = NEGATIVE_KEYWORDS.map(
    (keyword) => ({
      list_name: 'global',
      keyword,
      match_type: 'phrase',
    }),
  )

  const { error: keywordsError } = await supabase
    .from('co_negative_keywords')
    .insert(keywordRows)

  if (keywordsError) {
    console.error('Failed to insert negative keywords:', keywordsError.message)
    process.exit(1)
  }

  console.log(`  Inserted ${keywordRows.length} negative keywords`)

  // 3. Summary
  console.log('\nSeed complete:')
  console.log(`  Automation rules: ${AUTOMATION_RULES.length}`)
  for (const rule of AUTOMATION_RULES) {
    const approval = rule.requires_approval ? '(needs approval)' : '(auto)'
    console.log(`    - ${rule.name} [${rule.rule_type}] ${approval}`)
  }
  console.log(`  Negative keywords: ${keywordRows.length} (list: global)`)
}

main().catch((err) => {
  console.error('Unexpected error:', err)
  process.exit(1)
})
