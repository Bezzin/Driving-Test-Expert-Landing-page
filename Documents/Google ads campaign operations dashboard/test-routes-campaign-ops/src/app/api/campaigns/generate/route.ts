import { NextResponse } from 'next/server'
import { requireAdmin, unauthorizedResponse } from '@/lib/auth/guard'
import { createAdminClient } from '@/lib/supabase/server'
import { generateCampaign } from '@/lib/google-ads/campaign-generator'
import type { CentreInput } from '@/lib/google-ads/campaign-generator'

const DEFAULT_DAILY_BUDGET_MICROS = BigInt(5_000_000)

export async function POST(req: Request) {
  try {
    await requireAdmin()
  } catch {
    return unauthorizedResponse()
  }

  try {
    const body = await req.json()
    const centreIds = body?.centreIds

    if (!Array.isArray(centreIds) || centreIds.length === 0) {
      return NextResponse.json(
        { success: false, error: 'centreIds must be a non-empty array' },
        { status: 400 }
      )
    }

    const supabase = createAdminClient()

    const { data: negRows } = await supabase
      .from('co_negative_keywords')
      .select('keyword')
      .eq('list_name', 'global')

    const negativeKeywords = (negRows ?? []).map(
      (row: { keyword: string }) => row.keyword
    )

    const generated = []

    for (const centreId of centreIds) {
      const { data: centre, error: centreError } = await supabase
        .from('co_test_centres')
        .select('id, name, slug, route_count, pass_rate, landing_page_url')
        .eq('id', centreId)
        .single()

      if (centreError || !centre) {
        return NextResponse.json(
          {
            success: false,
            error: `Centre not found: ${centreId}`,
          },
          { status: 404 }
        )
      }

      const centreInput: CentreInput = {
        name: centre.name,
        slug: centre.slug,
        route_count: centre.route_count ?? 0,
        pass_rate: centre.pass_rate ?? null,
        landing_page_url: centre.landing_page_url ?? null,
      }

      const config = generateCampaign(
        centreInput,
        negativeKeywords,
        DEFAULT_DAILY_BUDGET_MICROS
      )

      generated.push({
        ...config,
        dailyBudgetMicros: Number(config.dailyBudgetMicros),
      })
    }

    return NextResponse.json({ success: true, data: generated })
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
