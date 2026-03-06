import { createAdminClient } from '@/lib/supabase/server'
import { getCustomer, isDryRun } from './client'
import { generateCampaign } from './campaign-generator'
import type { CentreInput } from './campaign-generator'

export interface PushResult {
  centreSlug: string
  campaignId: string
  dryRun: boolean
  googleCampaignResourceName?: string
  googleAdGroupResourceName?: string
}

const DEFAULT_DAILY_BUDGET_MICROS = BigInt(5_000_000) // 5 GBP

export async function pushCampaignForCentre(
  centreId: string
): Promise<PushResult> {
  const supabase = createAdminClient()

  // 1. Fetch the centre
  const { data: centre, error: centreError } = await supabase
    .from('co_test_centres')
    .select('id, name, slug, route_count, pass_rate, landing_page_url')
    .eq('id', centreId)
    .single()

  if (centreError || !centre) {
    throw new Error(
      `Failed to fetch centre ${centreId}: ${centreError?.message ?? 'not found'}`
    )
  }

  // 2. Idempotency check — throw if campaign already exists
  const { data: existingCampaign } = await supabase
    .from('co_campaigns')
    .select('id')
    .eq('centre_id', centreId)
    .limit(1)
    .single()

  if (existingCampaign) {
    throw new Error(
      `Campaign already exists for centre ${centre.slug} (centre_id: ${centreId})`
    )
  }

  // 3. Fetch negative keywords
  const { data: negRows } = await supabase
    .from('co_negative_keywords')
    .select('keyword')
    .eq('list_name', 'global')

  const negativeKeywords = (negRows ?? []).map(
    (row: { keyword: string }) => row.keyword
  )

  // 4. Generate campaign config
  const centreInput: CentreInput = {
    name: centre.name,
    slug: centre.slug,
    route_count: centre.route_count ?? 0,
    pass_rate: centre.pass_rate ?? null,
    landing_page_url: centre.landing_page_url ?? null,
  }

  const campaignConfig = generateCampaign(
    centreInput,
    negativeKeywords,
    DEFAULT_DAILY_BUDGET_MICROS
  )

  let googleCampaignResourceName: string | undefined
  let googleAdGroupResourceName: string | undefined

  // 5. If NOT dry-run, create in Google Ads
  if (!isDryRun()) {
    const customer = getCustomer()
    if (!customer) {
      throw new Error('Google Ads customer not available and not in dry-run mode')
    }

    try {
      const campaignResponse = await customer.campaigns.create([
        {
          name: campaignConfig.campaignName,
          status: 2, // PAUSED
          advertising_channel_type: 2, // SEARCH
          campaign_budget: {
            amount_micros: Number(campaignConfig.dailyBudgetMicros),
            delivery_method: 1, // STANDARD
          },
        },
      ] as never)
      const campaignResults = (
        campaignResponse as unknown as {
          results: Array<{ resource_name: string }>
        }
      ).results
      googleCampaignResourceName = campaignResults[0]?.resource_name

      const adGroupResponse = await customer.adGroups.create([
        {
          name: `${campaignConfig.campaignName} - Ad Group`,
          campaign: googleCampaignResourceName,
          status: 3, // PAUSED
          type: 2, // SEARCH_STANDARD
        },
      ] as never)
      const adGroupResults = (
        adGroupResponse as unknown as {
          results: Array<{ resource_name: string }>
        }
      ).results
      googleAdGroupResourceName = adGroupResults[0]?.resource_name
    } catch (err) {
      throw new Error(
        `Google Ads API error: ${err instanceof Error ? err.message : String(err)}`
      )
    }
  }

  const status = isDryRun() ? 'draft' : 'active'

  // 6. Insert campaign record
  const { data: campaignRow, error: insertError } = await supabase
    .from('co_campaigns')
    .insert({
      centre_id: centreId,
      campaign_name: campaignConfig.campaignName,
      status,
      daily_budget_micros: Number(campaignConfig.dailyBudgetMicros),
      google_campaign_id: googleCampaignResourceName ?? null,
      google_ad_group_id: googleAdGroupResourceName ?? null,
    })
    .select('id')
    .single()

  if (insertError || !campaignRow) {
    throw new Error(
      `Failed to insert campaign: ${insertError?.message ?? 'unknown error'}`
    )
  }

  const campaignId = campaignRow.id

  // Insert keywords
  const keywordRows = campaignConfig.keywords.map((kw) => ({
    campaign_id: campaignId,
    keyword_text: kw.text,
    match_type: kw.matchType,
  }))

  const { error: kwError } = await supabase
    .from('co_keywords')
    .insert(keywordRows)

  if (kwError) {
    throw new Error(`Failed to insert keywords: ${kwError.message}`)
  }

  // Insert ad copy
  const adRows = campaignConfig.ads.map((ad) => ({
    campaign_id: campaignId,
    variant_label: ad.variantLabel,
    headlines: ad.headlines,
    descriptions: ad.descriptions,
    final_url: ad.finalUrl,
    path1: ad.path1 ?? null,
    path2: ad.path2 ?? null,
  }))

  const { error: adError } = await supabase
    .from('co_ad_copy')
    .insert(adRows)

  if (adError) {
    throw new Error(`Failed to insert ad copy: ${adError.message}`)
  }

  return {
    centreSlug: centre.slug,
    campaignId,
    dryRun: isDryRun(),
    googleCampaignResourceName,
    googleAdGroupResourceName,
  }
}
