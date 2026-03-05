import type { DvsaCentre } from '@/lib/dvsa-types'
import type { CentreContentEntry } from '@/lib/centre-content'

interface SchemaMarkupProps {
  centre: DvsaCentre
  content: CentreContentEntry | undefined
  regionSlug: string
}

function buildFaqQuestions(centre: DvsaCentre, content: CentreContentEntry | undefined) {
  const roadTypesText = content?.roadTypes?.length
    ? content.roadTypes.join(', ')
    : 'a variety of road types'

  const nearbyText = centre.nearbyCentres.length > 0
    ? `Nearby centres include ${centre.nearbyCentres
        .slice(0, 3)
        .map(n => `${n.name} (${n.passRate}%, ${n.distanceMiles} miles)`)
        .join(', ')}.`
    : 'Check nearby centres for alternative options.'

  return [
    {
      '@type': 'Question' as const,
      name: `What is the pass rate at ${centre.name}?`,
      acceptedAnswer: {
        '@type': 'Answer' as const,
        text: `The current pass rate at ${centre.name} is ${centre.passRateOverall}%, compared to the national average of ${centre.nationalAverage}%. This is based on ${centre.testsConductedTotal.toLocaleString()} tests conducted during ${centre.dataPeriod}.`,
      },
    },
    {
      '@type': 'Question' as const,
      name: `Is ${centre.name} a hard driving test centre?`,
      acceptedAnswer: {
        '@type': 'Answer' as const,
        text: `${centre.name} is ranked ${centre.difficultyRank} out of 322 centres for difficulty and is classified as "${centre.difficultyLabel}". ${centre.passRateOverall >= centre.nationalAverage ? 'The pass rate is at or above the national average.' : 'The pass rate is below the national average.'}`,
      },
    },
    {
      '@type': 'Question' as const,
      name: `How many test routes does ${centre.name} have?`,
      acceptedAnswer: {
        '@type': 'Answer' as const,
        text: centre.totalRoutes
          ? `${centre.name} has ${centre.totalRoutes} known test routes. You can practise all of them with turn-by-turn navigation in the Test Routes Expert app.`
          : `The exact number of routes at ${centre.name} varies. You can practise real test routes with turn-by-turn navigation in the Test Routes Expert app.`,
      },
    },
    {
      '@type': 'Question' as const,
      name: `What roads are commonly used at ${centre.name}?`,
      acceptedAnswer: {
        '@type': 'Answer' as const,
        text: `Test routes at ${centre.name} commonly include ${roadTypesText}. Preparing for these road types will help you feel confident on test day.`,
      },
    },
    {
      '@type': 'Question' as const,
      name: `What's the best time to take a driving test at ${centre.name}?`,
      acceptedAnswer: {
        '@type': 'Answer' as const,
        text: content?.bestTimeToTest ?? 'Mid-morning slots, typically between 10am and 12pm, tend to have lighter traffic. Avoid school run times for a calmer experience.',
      },
    },
    {
      '@type': 'Question' as const,
      name: `How does ${centre.name} compare to nearby centres?`,
      acceptedAnswer: {
        '@type': 'Answer' as const,
        text: nearbyText,
      },
    },
  ]
}

export function SchemaMarkup({ centre, content, regionSlug }: SchemaMarkupProps) {
  const url = `https://www.testroutesexpert.co.uk/test-centres/${centre.slug}/`
  const faqQuestions = buildFaqQuestions(centre, content)

  const schemas = [
    {
      '@context': 'https://schema.org',
      '@type': 'GovernmentOffice',
      name: `${centre.name} Driving Test Centre`,
      description: `DVSA practical driving test centre. Pass rate: ${centre.passRateOverall}%. Practice routes available.`,
      url,
      geo: {
        '@type': 'GeoCoordinates',
        latitude: String(centre.latitude),
        longitude: String(centre.longitude),
      },
      hasMap: `https://www.google.com/maps?q=${centre.latitude},${centre.longitude}`,
    },
    {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        {
          '@type': 'ListItem',
          position: 1,
          name: 'Home',
          item: 'https://www.testroutesexpert.co.uk/',
        },
        {
          '@type': 'ListItem',
          position: 2,
          name: 'Test Centres',
          item: 'https://www.testroutesexpert.co.uk/test-centres/',
        },
        {
          '@type': 'ListItem',
          position: 3,
          name: centre.region,
          item: `https://www.testroutesexpert.co.uk/test-centres/regions/${regionSlug}/`,
        },
        {
          '@type': 'ListItem',
          position: 4,
          name: centre.name,
          item: url,
        },
      ],
    },
    {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: faqQuestions,
    },
    {
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: `${centre.name} Driving Test Routes 2026 | Pass Rate, Tips & Maps`,
      url,
      dateModified: new Date().toISOString().split('T')[0],
      inLanguage: 'en-GB',
      isPartOf: {
        '@type': 'WebSite',
        name: 'Test Routes Expert',
        url: 'https://www.testroutesexpert.co.uk/',
      },
    },
  ]

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schemas) }}
    />
  )
}
