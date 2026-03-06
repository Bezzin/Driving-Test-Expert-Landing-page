import { createAdminClient } from '@/lib/supabase/server'
import { sendDiscordNotification, DISCORD_COLOURS } from '@/lib/discord'
import { formatPounds, microsToPounds } from '@/lib/utils'
import { pushCampaignForCentre } from '@/lib/google-ads/campaign-push'

export interface AutomationResult {
  rulesEvaluated: number
  actionsExecuted: number
  actionsPendingApproval: number
  errors: string[]
}

interface AutomationRule {
  id: string
  rule_name: string
  rule_type: 'pause' | 'scale_up' | 'scale_down' | 'alert' | 'launch'
  is_active: boolean
  requires_approval: boolean
  lookback_days: number
  conditions: Record<string, unknown>
  actions: Record<string, unknown>
}

interface AggregatedPerformance {
  campaign_id: string
  campaign_name: string
  centre_id: string
  status: string
  daily_budget_micros: number
  total_impressions: number
  total_clicks: number
  total_cost_micros: number
  total_conversions: number
  cpa_micros: number
}

async function getAggregatedPerformance(
  lookbackDays: number
): Promise<AggregatedPerformance[]> {
  const supabase = createAdminClient()

  const cutoffDate = new Date()
  cutoffDate.setDate(cutoffDate.getDate() - lookbackDays)
  const cutoff = cutoffDate.toISOString().split('T')[0]

  const { data, error } = await supabase
    .from('co_campaigns')
    .select(
      `
      id,
      campaign_name,
      centre_id,
      status,
      daily_budget_micros,
      co_daily_performance!inner (
        impressions,
        clicks,
        cost_micros,
        conversions,
        date
      )
    `
    )
    .in('status', ['active', 'draft'])

  if (error) {
    throw new Error(`Failed to fetch campaign performance: ${error.message}`)
  }

  return (data ?? []).map((campaign: Record<string, unknown>) => {
    const perfRows = (
      campaign.co_daily_performance as Array<{
        impressions: number
        clicks: number
        cost_micros: number
        conversions: number
        date: string
      }>
    ).filter((row) => row.date >= cutoff)

    const totalImpressions = perfRows.reduce(
      (sum, r) => sum + (r.impressions ?? 0),
      0
    )
    const totalClicks = perfRows.reduce((sum, r) => sum + (r.clicks ?? 0), 0)
    const totalCostMicros = perfRows.reduce(
      (sum, r) => sum + (r.cost_micros ?? 0),
      0
    )
    const totalConversions = perfRows.reduce(
      (sum, r) => sum + (r.conversions ?? 0),
      0
    )
    const cpaMicros =
      totalConversions > 0
        ? Math.round(totalCostMicros / totalConversions)
        : 0

    return {
      campaign_id: campaign.id as string,
      campaign_name: campaign.campaign_name as string,
      centre_id: campaign.centre_id as string,
      status: campaign.status as string,
      daily_budget_micros: campaign.daily_budget_micros as number,
      total_impressions: totalImpressions,
      total_clicks: totalClicks,
      total_cost_micros: totalCostMicros,
      total_conversions: totalConversions,
      cpa_micros: cpaMicros,
    }
  })
}

async function logAction(
  ruleId: string,
  campaignId: string | null,
  action: string,
  details: Record<string, unknown>,
  status: 'executed' | 'pending_approval'
): Promise<void> {
  const supabase = createAdminClient()
  const { error } = await supabase.from('co_automation_log').insert({
    rule_id: ruleId,
    campaign_id: campaignId,
    action,
    details,
    status,
  })

  if (error) {
    throw new Error(`Failed to log automation action: ${error.message}`)
  }
}

async function evaluatePause(
  rule: AutomationRule,
  campaigns: AggregatedPerformance[],
  result: AutomationResult
): Promise<void> {
  const cpaThreshold = Number(rule.conditions.cpa_above_micros ?? 0)
  const minSpend = Number(rule.conditions.min_spend_micros ?? 0)
  const supabase = createAdminClient()

  for (const campaign of campaigns) {
    if (campaign.status !== 'active') continue
    if (campaign.cpa_micros <= cpaThreshold) continue
    if (campaign.total_cost_micros <= minSpend) continue

    const details = {
      campaign_name: campaign.campaign_name,
      cpa_micros: campaign.cpa_micros,
      threshold_micros: cpaThreshold,
      spend_micros: campaign.total_cost_micros,
    }

    if (rule.requires_approval) {
      await logAction(rule.id, campaign.campaign_id, 'pause', details, 'pending_approval')
      result.actionsPendingApproval++
    } else {
      await supabase
        .from('co_campaigns')
        .update({ status: 'paused' })
        .eq('id', campaign.campaign_id)
      await logAction(rule.id, campaign.campaign_id, 'pause', details, 'executed')
      result.actionsExecuted++
    }
  }
}

async function evaluateScaleUp(
  rule: AutomationRule,
  campaigns: AggregatedPerformance[],
  result: AutomationResult
): Promise<void> {
  const cpaThreshold = Number(rule.conditions.cpa_below_micros ?? 0)
  const minConversions = Number(rule.conditions.min_conversions ?? 0)
  const multiplier = Number(rule.actions.budget_multiplier ?? 1.2)
  const maxBudgetMicros = Number(rule.actions.max_budget_micros ?? 50_000_000)
  const supabase = createAdminClient()

  for (const campaign of campaigns) {
    if (campaign.status !== 'active') continue
    if (campaign.cpa_micros <= 0) continue
    if (campaign.cpa_micros >= cpaThreshold) continue
    if (campaign.total_conversions < minConversions) continue

    const newBudget = Math.min(
      Math.round(campaign.daily_budget_micros * multiplier),
      maxBudgetMicros
    )

    const details = {
      campaign_name: campaign.campaign_name,
      old_budget_micros: campaign.daily_budget_micros,
      new_budget_micros: newBudget,
      cpa_micros: campaign.cpa_micros,
      multiplier,
    }

    if (rule.requires_approval) {
      await logAction(rule.id, campaign.campaign_id, 'scale_up', details, 'pending_approval')
      result.actionsPendingApproval++
    } else {
      await supabase
        .from('co_campaigns')
        .update({ daily_budget_micros: newBudget })
        .eq('id', campaign.campaign_id)
      await logAction(rule.id, campaign.campaign_id, 'scale_up', details, 'executed')
      result.actionsExecuted++
    }
  }
}

async function evaluateScaleDown(
  rule: AutomationRule,
  campaigns: AggregatedPerformance[],
  result: AutomationResult
): Promise<void> {
  const cpaThreshold = Number(rule.conditions.cpa_above_micros ?? 0)
  const minSpend = Number(rule.conditions.min_spend_micros ?? 0)
  const multiplier = Number(rule.actions.budget_multiplier ?? 0.8)
  const minBudgetMicros = Number(rule.actions.min_budget_micros ?? 1_000_000)
  const supabase = createAdminClient()

  for (const campaign of campaigns) {
    if (campaign.status !== 'active') continue
    if (campaign.cpa_micros <= cpaThreshold) continue
    if (campaign.total_cost_micros <= minSpend) continue

    const newBudget = Math.max(
      Math.round(campaign.daily_budget_micros * multiplier),
      minBudgetMicros
    )

    const details = {
      campaign_name: campaign.campaign_name,
      old_budget_micros: campaign.daily_budget_micros,
      new_budget_micros: newBudget,
      cpa_micros: campaign.cpa_micros,
      multiplier,
    }

    if (rule.requires_approval) {
      await logAction(rule.id, campaign.campaign_id, 'scale_down', details, 'pending_approval')
      result.actionsPendingApproval++
    } else {
      await supabase
        .from('co_campaigns')
        .update({ daily_budget_micros: newBudget })
        .eq('id', campaign.campaign_id)
      await logAction(rule.id, campaign.campaign_id, 'scale_down', details, 'executed')
      result.actionsExecuted++
    }
  }
}

async function evaluateAlert(
  rule: AutomationRule,
  campaigns: AggregatedPerformance[],
  result: AutomationResult
): Promise<void> {
  const minSpend = Number(rule.conditions.min_spend_micros ?? 0)

  for (const campaign of campaigns) {
    if (campaign.total_conversions !== 0) continue
    if (campaign.total_cost_micros <= minSpend) continue

    const details = {
      campaign_name: campaign.campaign_name,
      spend_micros: campaign.total_cost_micros,
      impressions: campaign.total_impressions,
      clicks: campaign.total_clicks,
    }

    if (rule.requires_approval) {
      await logAction(rule.id, campaign.campaign_id, 'alert', details, 'pending_approval')
      result.actionsPendingApproval++
    } else {
      await sendDiscordNotification(
        `Zero conversions alert: **${campaign.campaign_name}**`,
        [
          {
            title: 'Zero Conversions Alert',
            description: `Campaign "${campaign.campaign_name}" has spent ${formatPounds(campaign.total_cost_micros)} with 0 conversions over the last ${rule.lookback_days} days.`,
            color: DISCORD_COLOURS.warning,
            fields: [
              {
                name: 'Spend',
                value: formatPounds(campaign.total_cost_micros),
                inline: true,
              },
              {
                name: 'Clicks',
                value: String(campaign.total_clicks),
                inline: true,
              },
              {
                name: 'Impressions',
                value: String(campaign.total_impressions),
                inline: true,
              },
            ],
          },
        ]
      )
      await logAction(rule.id, campaign.campaign_id, 'alert', details, 'executed')
      result.actionsExecuted++
    }
  }
}

async function evaluateLaunch(
  rule: AutomationRule,
  result: AutomationResult
): Promise<void> {
  const supabase = createAdminClient()
  const targetTier = rule.conditions.tier as string | undefined
  const targetStatus = rule.conditions.centre_status as string | undefined

  // Find eligible centres: matching tier/status, has landing page, no existing campaign
  let query = supabase
    .from('co_test_centres')
    .select('id, name, slug')
    .eq('has_landing_page', true)

  if (targetTier) {
    query = query.eq('tier', targetTier)
  }

  if (targetStatus) {
    query = query.eq('status', targetStatus)
  }

  const { data: centres, error: centreError } = await query

  if (centreError) {
    result.errors.push(`Launch rule: failed to fetch centres: ${centreError.message}`)
    return
  }

  if (!centres || centres.length === 0) {
    return
  }

  // Filter out centres that already have campaigns
  const { data: existingCampaigns } = await supabase
    .from('co_campaigns')
    .select('centre_id')

  const existingCentreIds = new Set(
    (existingCampaigns ?? []).map((c: { centre_id: string }) => c.centre_id)
  )

  const eligibleCentres = centres.filter(
    (c: { id: string }) => !existingCentreIds.has(c.id)
  )

  for (const centre of eligibleCentres) {
    const details = {
      centre_name: (centre as { name: string }).name,
      centre_slug: (centre as { slug: string }).slug,
    }

    if (rule.requires_approval) {
      await logAction(rule.id, null, 'launch', details, 'pending_approval')
      result.actionsPendingApproval++
    } else {
      try {
        await pushCampaignForCentre(centre.id)
        await logAction(rule.id, null, 'launch', details, 'executed')
        result.actionsExecuted++
      } catch (err) {
        const errorMsg = `Launch failed for ${(centre as { slug: string }).slug}: ${err instanceof Error ? err.message : String(err)}`
        result.errors.push(errorMsg)
        await logAction(rule.id, null, 'launch_error', { ...details, error: errorMsg }, 'executed')
      }
    }
  }
}

export async function runAutomationEngine(): Promise<AutomationResult> {
  const result: AutomationResult = {
    rulesEvaluated: 0,
    actionsExecuted: 0,
    actionsPendingApproval: 0,
    errors: [],
  }

  const supabase = createAdminClient()

  // 1. Load active rules
  const { data: rules, error: rulesError } = await supabase
    .from('co_automation_rules')
    .select('*')
    .eq('is_active', true)

  if (rulesError) {
    result.errors.push(`Failed to load automation rules: ${rulesError.message}`)
    return result
  }

  if (!rules || rules.length === 0) {
    return result
  }

  // 2. Evaluate each rule
  for (const rule of rules as AutomationRule[]) {
    try {
      result.rulesEvaluated++

      if (rule.rule_type === 'launch') {
        await evaluateLaunch(rule, result)
        continue
      }

      // For non-launch rules, get aggregated performance
      const campaigns = await getAggregatedPerformance(rule.lookback_days)

      switch (rule.rule_type) {
        case 'pause':
          await evaluatePause(rule, campaigns, result)
          break
        case 'scale_up':
          await evaluateScaleUp(rule, campaigns, result)
          break
        case 'scale_down':
          await evaluateScaleDown(rule, campaigns, result)
          break
        case 'alert':
          await evaluateAlert(rule, campaigns, result)
          break
      }
    } catch (err) {
      result.errors.push(
        `Rule "${rule.rule_name}" (${rule.rule_type}) failed: ${err instanceof Error ? err.message : String(err)}`
      )
    }
  }

  // 3. Send Discord summary
  try {
    await sendDiscordNotification('Automation engine run complete', [
      {
        title: 'Automation Engine Summary',
        color:
          result.errors.length > 0
            ? DISCORD_COLOURS.warning
            : DISCORD_COLOURS.success,
        fields: [
          {
            name: 'Rules Evaluated',
            value: String(result.rulesEvaluated),
            inline: true,
          },
          {
            name: 'Actions Executed',
            value: String(result.actionsExecuted),
            inline: true,
          },
          {
            name: 'Pending Approval',
            value: String(result.actionsPendingApproval),
            inline: true,
          },
          ...(result.errors.length > 0
            ? [
                {
                  name: 'Errors',
                  value: result.errors.slice(0, 5).join('\n'),
                  inline: false,
                },
              ]
            : []),
        ],
        timestamp: new Date().toISOString(),
      },
    ])
  } catch (err) {
    result.errors.push(
      `Discord notification failed: ${err instanceof Error ? err.message : String(err)}`
    )
  }

  return result
}
