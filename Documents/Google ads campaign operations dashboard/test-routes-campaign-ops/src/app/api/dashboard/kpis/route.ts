import { NextResponse } from 'next/server'
import { requireAdmin, unauthorizedResponse } from '@/lib/auth/guard'
import { createAdminClient } from '@/lib/supabase/server'

function getDateString(daysAgo: number): string {
  const date = new Date()
  date.setDate(date.getDate() - daysAgo)
  return date.toISOString().split('T')[0]
}

export async function GET() {
  try {
    await requireAdmin()
  } catch {
    return unauthorizedResponse()
  }

  try {
    const supabase = createAdminClient()

    const today = getDateString(0)
    const weekAgo = getDateString(7)
    const monthAgo = getDateString(30)

    // Fetch all performance data for the last 30 days in one query
    const { data: perfRows, error: perfError } = await supabase
      .from('co_daily_performance')
      .select('date, cost_micros, conversions')
      .gte('date', monthAgo)

    if (perfError) {
      return NextResponse.json(
        {
          success: false,
          error: `Failed to fetch performance data: ${perfError.message}`,
        },
        { status: 500 }
      )
    }

    let spendToday = 0
    let spendThisWeek = 0
    let spendThisMonth = 0
    let conversionsThisWeek = 0

    for (const row of perfRows ?? []) {
      const rowDate = row.date as string
      const cost = (row.cost_micros as number) ?? 0
      const conv = (row.conversions as number) ?? 0

      spendThisMonth += cost

      if (rowDate >= weekAgo) {
        spendThisWeek += cost
        conversionsThisWeek += conv
      }

      if (rowDate === today) {
        spendToday += cost
      }
    }

    const avgCpaThisWeek =
      conversionsThisWeek > 0 ? spendThisWeek / conversionsThisWeek : 0

    // Active campaigns count
    const { count: activeCampaigns, error: campaignError } = await supabase
      .from('co_campaigns')
      .select('id', { count: 'exact', head: true })
      .in('status', ['active', 'draft'])

    if (campaignError) {
      return NextResponse.json(
        {
          success: false,
          error: `Failed to count campaigns: ${campaignError.message}`,
        },
        { status: 500 }
      )
    }

    // Pending approvals count
    const { count: pendingApprovals, error: approvalError } = await supabase
      .from('co_automation_log')
      .select('id', { count: 'exact', head: true })
      .eq('status', 'pending_approval')

    if (approvalError) {
      return NextResponse.json(
        {
          success: false,
          error: `Failed to count pending approvals: ${approvalError.message}`,
        },
        { status: 500 }
      )
    }

    return NextResponse.json({
      success: true,
      data: {
        spendToday,
        spendThisWeek,
        spendThisMonth,
        conversionsThisWeek,
        avgCpaThisWeek,
        activeCampaigns: activeCampaigns ?? 0,
        pendingApprovals: pendingApprovals ?? 0,
      },
    })
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
