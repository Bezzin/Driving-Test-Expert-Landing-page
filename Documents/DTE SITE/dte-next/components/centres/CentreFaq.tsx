import { HelpCircle } from 'lucide-react'
import type { DvsaCentre } from '@/lib/dvsa-types'
import type { CentreContentEntry } from '@/lib/centre-content'

interface CentreFaqProps {
  centre: DvsaCentre
  content: CentreContentEntry | undefined
}

interface FaqItem {
  question: string
  answer: string
}

function buildFaqItems(centre: DvsaCentre, content: CentreContentEntry | undefined): FaqItem[] {
  const roadTypesText = content?.roadTypes?.length
    ? content.roadTypes.join(', ')
    : 'a variety of road types'

  const nearbyText = centre.nearbyCentres.length > 0
    ? `Nearby alternatives include ${centre.nearbyCentres
        .slice(0, 3)
        .map(n => `${n.name} (${n.passRate}%, ${n.distanceMiles} miles away)`)
        .join('; ')}. Comparing pass rates and distances can help you choose the best centre for your test.`
    : 'Check the regional hub page for alternative centres in your area.'

  return [
    {
      question: `What is the pass rate at ${centre.name}?`,
      answer: `The current pass rate at ${centre.name} is ${centre.passRateOverall}%. The national average is ${centre.nationalAverage}%. These figures are based on ${centre.testsConductedTotal.toLocaleString()} tests conducted during ${centre.dataPeriod}. The male pass rate is ${centre.passRateMale}% and the female pass rate is ${centre.passRateFemale}%.`,
    },
    {
      question: `Is ${centre.name} a hard driving test centre?`,
      answer: `${centre.name} is ranked ${centre.difficultyRank} out of 322 UK test centres for difficulty and is classified as "${centre.difficultyLabel}". ${centre.passRateOverall >= centre.nationalAverage ? 'The pass rate here is at or above the national average, suggesting it is not one of the harder centres.' : 'The pass rate is below the national average, which may indicate a more challenging test experience.'}`,
    },
    {
      question: `How many test routes does ${centre.name} have?`,
      answer: centre.totalRoutes
        ? `${centre.name} has ${centre.totalRoutes} known test routes. Each route tests a range of driving skills and covers different road types. You can practise all of these routes with turn-by-turn navigation in the Test Routes Expert app.`
        : `The exact number of routes at ${centre.name} varies and is updated regularly. You can practise real test routes used at this centre with turn-by-turn navigation in the Test Routes Expert app.`,
    },
    {
      question: `What roads are commonly used at ${centre.name}?`,
      answer: `Test routes at ${centre.name} commonly include ${roadTypesText}. Being comfortable on these road types is essential for passing. The Test Routes Expert app lets you practise on the exact roads used in the test.`,
    },
    {
      question: `What's the best time to take a driving test at ${centre.name}?`,
      answer: content?.bestTimeToTest ?? 'Mid-morning slots between 10am and 12pm typically have lighter traffic. Avoiding school run times (8:15-9:15am and 2:45-3:30pm) can also help reduce stress on test day.',
    },
    {
      question: `How does ${centre.name} compare to nearby centres?`,
      answer: nearbyText,
    },
  ]
}

export function CentreFaq({ centre, content }: CentreFaqProps) {
  const faqItems = buildFaqItems(centre, content)

  return (
    <section className="py-16 px-6 max-w-7xl mx-auto">
      <h2 className="font-brand text-3xl font-bold tracking-tight text-white sm:text-4xl mb-8">
        Frequently Asked Questions About {centre.name}
      </h2>

      <div className="space-y-3">
        {faqItems.map((item, i) => (
          <details
            key={i}
            className="group rounded-2xl border border-white/10 bg-black/40 overflow-hidden"
          >
            <summary className="flex cursor-pointer items-center gap-3 px-6 py-4 text-white hover:bg-white/5 transition-colors list-none [&::-webkit-details-marker]:hidden">
              <HelpCircle className="h-5 w-5 text-accent shrink-0" />
              <span className="text-sm font-semibold flex-1">{item.question}</span>
              <span className="text-white/40 transition-transform group-open:rotate-45 text-xl leading-none">
                +
              </span>
            </summary>
            <div className="px-6 pb-5 pt-1">
              <p className="text-sm text-white/70 leading-relaxed pl-8">
                {item.answer}
              </p>
            </div>
          </details>
        ))}
      </div>
    </section>
  )
}
