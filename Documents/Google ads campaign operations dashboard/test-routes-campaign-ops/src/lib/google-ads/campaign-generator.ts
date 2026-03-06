import type { GeneratedCampaign, GeneratedKeyword, GeneratedAd } from './types'

export interface CentreInput {
  name: string
  slug: string
  route_count: number
  pass_rate: number | null
  landing_page_url: string | null
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text
  return text.slice(0, max)
}

export function generateKeywords(centreName: string): GeneratedKeyword[] {
  const name = centreName.trim()

  const exactKeywords: GeneratedKeyword[] = [
    { text: `${name} driving test routes`, matchType: 'EXACT' },
    { text: `${name} test routes`, matchType: 'EXACT' },
    { text: `driving test routes ${name}`, matchType: 'EXACT' },
    { text: `${name} driving test route`, matchType: 'EXACT' },
  ]

  const phraseKeywords: GeneratedKeyword[] = [
    { text: `${name} driving test routes`, matchType: 'PHRASE' },
    { text: `${name} test routes`, matchType: 'PHRASE' },
    { text: `${name} test centre routes`, matchType: 'PHRASE' },
    { text: `practise driving test ${name}`, matchType: 'PHRASE' },
  ]

  return [...exactKeywords, ...phraseKeywords]
}

export function generateAds(centre: CentreInput): GeneratedAd[] {
  const name = truncate(centre.name, 30)
  const slug = centre.slug
  const finalUrl =
    centre.landing_page_url ?? `https://testroutesexpert.co.uk/routes/${slug}`

  const routeCountHeadline =
    centre.route_count > 0
      ? truncate(`${centre.route_count} Real Test Routes`, 30)
      : 'Real Test Routes'

  const passRateHeadline =
    centre.pass_rate !== null && centre.pass_rate > 0
      ? truncate(`${centre.pass_rate}% Pass Rate Area`, 30)
      : 'Know Your Routes'

  const variantA: GeneratedAd = {
    headlines: [
      truncate(`${name} Test Routes`, 30),
      truncate('Turn-by-Turn Navigation', 30),
      truncate('Pass Your Test First Time', 30),
      routeCountHeadline,
      truncate('Practice Real Test Routes', 30),
      truncate('Download Free Today', 30),
    ],
    descriptions: [
      truncate(
        `Practice the exact routes examiners use at ${name} test centre. Turn-by-turn sat nav guidance on every route.`,
        90
      ),
      truncate(
        'Join 50,000+ UK learners. Real test routes with voice navigation. One free route per centre. Download now.',
        90
      ),
    ],
    finalUrl,
    path1: 'test-routes',
    path2: truncate(slug, 15),
    variantLabel: 'navigation_focus',
  }

  const variantB: GeneratedAd = {
    headlines: [
      truncate(`${name} Test Routes`, 30),
      truncate('Practise Routes Virtually', 30),
      passRateHeadline,
      truncate('Virtual Test Route Practice', 30),
      truncate('Beat Test Day Nerves', 30),
      truncate('Try For Free', 30),
    ],
    descriptions: [
      truncate(
        `Go through ${name} test routes virtually before your test. Interactive practise mode lets you learn every junction.`,
        90
      ),
      truncate(
        `Stop guessing where you'll go. Practise ${name} driving test routes with our virtual walkthrough. Free download.`,
        90
      ),
    ],
    finalUrl,
    path1: 'practise',
    path2: truncate(slug, 15),
    variantLabel: 'practise_focus',
  }

  return [variantA, variantB]
}

export function generateCampaign(
  centre: CentreInput,
  negativeKeywords: string[],
  dailyBudgetMicros: bigint
): GeneratedCampaign {
  const finalUrl =
    centre.landing_page_url ?? `https://testroutesexpert.co.uk/routes/${centre.slug}`

  return {
    centreName: centre.name,
    centreSlug: centre.slug,
    campaignName: `TR - ${centre.name}`,
    dailyBudgetMicros,
    keywords: generateKeywords(centre.name),
    ads: generateAds(centre),
    negativeKeywords,
    finalUrl,
  }
}
