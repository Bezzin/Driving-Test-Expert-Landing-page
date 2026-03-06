import { createAdminClient } from '@/lib/supabase/server'
import { getCustomer, isDryRun } from './client'
import type { SyncResult } from './types'

function getYesterday(): string {
  const date = new Date()
  date.setDate(date.getDate() - 1)
  return date.toISOString().split('T')[0]
}

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

interface PerformanceRow {
  campaign_id: string
  date: string
  impressions: number
  clicks: number
  cost_micros: number
  conversions: number
}

async function generateMockPerformance(
  date: string
): Promise<{ rows: PerformanceRow[]; errors: string[] }> {
  const supabase = createAdminClient()
  const errors: string[] = []

  const { data: campaigns, error: fetchError } = await supabase
    .from('co_campaigns')
    .select('id')
    .in('status', ['draft', 'active'])

  if (fetchError) {
    errors.push(`Failed to fetch campaigns: ${fetchError.message}`)
    return { rows: [], errors }
  }

  const rows: PerformanceRow[] = (campaigns ?? []).map(
    (campaign: { id: string }) => ({
      campaign_id: campaign.id,
      date,
      impressions: randomInt(10, 200),
      clicks: randomInt(1, 30),
      cost_micros: randomInt(500_000, 10_000_000),
      conversions: randomInt(0, 5),
    })
  )

  return { rows, errors }
}

async function fetchLivePerformance(
  date: string
): Promise<{ rows: PerformanceRow[]; errors: string[] }> {
  const supabase = createAdminClient()
  const errors: string[] = []
  const rows: PerformanceRow[] = []

  const customer = getCustomer()
  if (!customer) {
    errors.push('Google Ads customer not available')
    return { rows, errors }
  }

  // Fetch campaigns with their Google IDs
  const { data: campaigns, error: fetchError } = await supabase
    .from('co_campaigns')
    .select('id, google_campaign_id')
    .in('status', ['active'])
    .not('google_campaign_id', 'is', null)

  if (fetchError) {
    errors.push(`Failed to fetch campaigns: ${fetchError.message}`)
    return { rows, errors }
  }

  if (!campaigns || campaigns.length === 0) {
    return { rows, errors }
  }

  try {
    const report = await customer.report({
      entity: 'campaign',
      attributes: ['campaign.resource_name'],
      metrics: [
        'metrics.impressions',
        'metrics.clicks',
        'metrics.cost_micros',
        'metrics.conversions',
      ],
      from_date: date,
      to_date: date,
    })

    // Build a lookup from Google resource name to local campaign ID
    const googleIdToLocalId = new Map<string, string>()
    for (const campaign of campaigns) {
      if (campaign.google_campaign_id) {
        googleIdToLocalId.set(campaign.google_campaign_id, campaign.id)
      }
    }

    for (const row of report) {
      const resourceName = row.campaign?.resource_name
      if (!resourceName) continue

      const localId = googleIdToLocalId.get(resourceName)
      if (!localId) continue

      rows.push({
        campaign_id: localId,
        date,
        impressions: Number(row.metrics?.impressions ?? 0),
        clicks: Number(row.metrics?.clicks ?? 0),
        cost_micros: Number(row.metrics?.cost_micros ?? 0),
        conversions: Number(row.metrics?.conversions ?? 0),
      })
    }
  } catch (err) {
    errors.push(
      `Google Ads report error: ${err instanceof Error ? err.message : String(err)}`
    )
  }

  return { rows, errors }
}

export async function syncPerformance(date?: string): Promise<SyncResult> {
  const targetDate = date ?? getYesterday()
  const errors: string[] = []

  // Fetch performance data (mock or live)
  const { rows, errors: fetchErrors } = isDryRun()
    ? await generateMockPerformance(targetDate)
    : await fetchLivePerformance(targetDate)

  errors.push(...fetchErrors)

  if (rows.length === 0) {
    return { campaignsUpdated: 0, performanceRows: 0, errors }
  }

  // Upsert into co_daily_performance
  const supabase = createAdminClient()
  const campaignIds = new Set<string>()

  const { error: upsertError } = await supabase
    .from('co_daily_performance')
    .upsert(rows, { onConflict: 'campaign_id,date' })

  if (upsertError) {
    errors.push(`Failed to upsert performance data: ${upsertError.message}`)
    return { campaignsUpdated: 0, performanceRows: 0, errors }
  }

  for (const row of rows) {
    campaignIds.add(row.campaign_id)
  }

  return {
    campaignsUpdated: campaignIds.size,
    performanceRows: rows.length,
    errors,
  }
}
