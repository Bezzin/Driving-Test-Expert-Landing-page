import { NextResponse, type NextRequest } from 'next/server'
import { requireAdmin, unauthorizedResponse } from '@/lib/auth/guard'
import { createAdminClient } from '@/lib/supabase/server'

interface CentreRow {
  id: string
  name: string
  slug: string
  region: string
  priority_tier: string | null
  status: string
  route_count: number | null
  has_landing_page: boolean
  pass_rate: number | null
  tests_conducted: number | null
}

interface PerformanceRow {
  campaign_id: string
  impressions: number
  clicks: number
  cost_micros: number
  conversions: number
}

interface CampaignRow {
  id: string
  centre_id: string
  co_daily_performance: PerformanceRow[]
}

const VALID_SORT_FIELDS = new Set([
  'name',
  'region',
  'priority_tier',
  'status',
  'route_count',
  'pass_rate',
  'tests_conducted',
  'spend_7d',
  'conversions_7d',
  'cpa',
])

export async function GET(req: NextRequest) {
  try {
    await requireAdmin()
  } catch {
    return unauthorizedResponse()
  }

  try {
    const supabase = createAdminClient()
    const searchParams = req.nextUrl.searchParams

    const tierFilter = searchParams.get('tier')
    const statusFilter = searchParams.get('status')
    const sortField = searchParams.get('sort') ?? 'name'
    const sortOrder = searchParams.get('order') ?? 'asc'

    if (!VALID_SORT_FIELDS.has(sortField)) {
      return NextResponse.json(
        { success: false, error: `Invalid sort field: ${sortField}` },
        { status: 400 }
      )
    }

    // Fetch centres
    let centresQuery = supabase
      .from('co_test_centres')
      .select(
        'id, name, slug, region, priority_tier, status, route_count, has_landing_page, pass_rate, tests_conducted'
      )

    if (tierFilter) {
      centresQuery = centresQuery.eq('priority_tier', tierFilter)
    }

    if (statusFilter) {
      centresQuery = centresQuery.eq('status', statusFilter)
    }

    const { data: centres, error: centresError } = await centresQuery

    if (centresError) {
      return NextResponse.json(
        {
          success: false,
          error: `Failed to fetch centres: ${centresError.message}`,
        },
        { status: 500 }
      )
    }

    // Fetch 7-day performance via campaigns
    const cutoffDate = new Date()
    cutoffDate.setDate(cutoffDate.getDate() - 7)
    const cutoff = cutoffDate.toISOString().split('T')[0]

    const { data: campaigns } = await supabase
      .from('co_campaigns')
      .select(
        `
        id,
        centre_id,
        co_daily_performance (
          campaign_id,
          impressions,
          clicks,
          cost_micros,
          conversions
        )
      `
      )
      .gte('co_daily_performance.date', cutoff)

    // Aggregate performance by centre
    const perfByCentre = new Map<
      string,
      { spend: number; conversions: number }
    >()

    for (const campaign of (campaigns ?? []) as CampaignRow[]) {
      const rows = campaign.co_daily_performance ?? []
      for (const row of rows) {
        const existing = perfByCentre.get(campaign.centre_id) ?? {
          spend: 0,
          conversions: 0,
        }
        perfByCentre.set(campaign.centre_id, {
          spend: existing.spend + (row.cost_micros ?? 0),
          conversions: existing.conversions + (row.conversions ?? 0),
        })
      }
    }

    // Merge centres with performance
    const data = (centres ?? []).map((centre: CentreRow) => {
      const perf = perfByCentre.get(centre.id) ?? {
        spend: 0,
        conversions: 0,
      }
      const cpa = perf.conversions > 0 ? perf.spend / perf.conversions : 0

      return {
        id: centre.id,
        name: centre.name,
        slug: centre.slug,
        region: centre.region,
        priority_tier: centre.priority_tier,
        status: centre.status,
        route_count: centre.route_count,
        has_landing_page: centre.has_landing_page,
        pass_rate: centre.pass_rate,
        tests_conducted: centre.tests_conducted,
        spend_7d: perf.spend,
        conversions_7d: perf.conversions,
        cpa,
      }
    })

    // Sort
    const ascending = sortOrder !== 'desc'
    data.sort((a, b) => {
      const aVal = a[sortField as keyof typeof a] ?? 0
      const bVal = b[sortField as keyof typeof b] ?? 0

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return ascending
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }

      const aNum = Number(aVal)
      const bNum = Number(bVal)
      return ascending ? aNum - bNum : bNum - aNum
    })

    return NextResponse.json({ success: true, data })
  } catch (err) {
    return NextResponse.json(
      {
        success: false,
        error: err instanceof Error ? err.message : 'Internal server error',
      },
      { status: 500 }
    )
  }
}
