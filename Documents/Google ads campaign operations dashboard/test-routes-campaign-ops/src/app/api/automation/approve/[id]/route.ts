import { NextResponse } from 'next/server'
import { requireAdmin, unauthorizedResponse } from '@/lib/auth/guard'
import { createAdminClient } from '@/lib/supabase/server'
import { pushCampaignForCentre } from '@/lib/google-ads/campaign-push'

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    await requireAdmin()
  } catch {
    return unauthorizedResponse()
  }

  try {
    const { id } = await params
    const supabase = createAdminClient()

    // Fetch the log entry
    const { data: logEntry, error: logError } = await supabase
      .from('co_automation_log')
      .select('id, rule_id, campaign_id, action, details, status')
      .eq('id', id)
      .single()

    if (logError || !logEntry) {
      return NextResponse.json(
        { success: false, error: `Log entry not found: ${id}` },
        { status: 404 }
      )
    }

    if (logEntry.status !== 'pending_approval') {
      return NextResponse.json(
        {
          success: false,
          error: `Log entry is not pending approval (current status: ${logEntry.status})`,
        },
        { status: 400 }
      )
    }

    // Update status to approved
    const { error: updateError } = await supabase
      .from('co_automation_log')
      .update({ status: 'approved' })
      .eq('id', id)

    if (updateError) {
      return NextResponse.json(
        {
          success: false,
          error: `Failed to update status: ${updateError.message}`,
        },
        { status: 500 }
      )
    }

    // Execute the pending action based on action type
    const details = logEntry.details as Record<string, unknown>

    switch (logEntry.action) {
      case 'pause': {
        if (logEntry.campaign_id) {
          await supabase
            .from('co_campaigns')
            .update({ status: 'paused' })
            .eq('id', logEntry.campaign_id)
        }
        break
      }
      case 'scale_up': {
        const newBudget = details?.new_budget_micros as number | undefined
        if (logEntry.campaign_id && newBudget !== undefined) {
          await supabase
            .from('co_campaigns')
            .update({ daily_budget_micros: newBudget })
            .eq('id', logEntry.campaign_id)
        }
        break
      }
      case 'scale_down': {
        const newBudget = details?.new_budget_micros as number | undefined
        if (logEntry.campaign_id && newBudget !== undefined) {
          await supabase
            .from('co_campaigns')
            .update({ daily_budget_micros: newBudget })
            .eq('id', logEntry.campaign_id)
        }
        break
      }
      case 'launch': {
        // Find the centre by slug from details and push campaign
        const centreSlug = details?.centre_slug as string | undefined
        if (centreSlug) {
          const { data: centre } = await supabase
            .from('co_test_centres')
            .select('id')
            .eq('slug', centreSlug)
            .single()

          if (centre) {
            await pushCampaignForCentre(centre.id)
          }
        }
        break
      }
      case 'alert': {
        // Alerts don't have an executable action beyond acknowledgement
        break
      }
    }

    return NextResponse.json({ success: true })
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
