import { Lightbulb, Clock } from 'lucide-react'
import type { DvsaCentre } from '@/lib/dvsa-types'
import type { CentreContentEntry } from '@/lib/centre-content'

interface TipsSectionProps {
  centre: DvsaCentre
  content: CentreContentEntry | undefined
}

export function TipsSection({ centre, content }: TipsSectionProps) {
  if (!content) return null

  return (
    <section className="py-16 px-6 max-w-7xl mx-auto">
      <h2 className="font-brand text-3xl font-bold tracking-tight text-white sm:text-4xl mb-8">
        How to Pass Your Driving Test at {centre.name}
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Tips list */}
        <div className="lg:col-span-2 rounded-2xl border border-white/10 bg-black/40 p-6">
          <div className="flex items-center gap-2 mb-6">
            <Lightbulb className="h-5 w-5 text-accent" />
            <h3 className="text-lg font-semibold text-white">Expert Tips</h3>
          </div>
          <ol className="space-y-4">
            {content.specificTips.map((tip, i) => (
              <li key={i} className="flex items-start gap-4">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent/20 text-xs font-bold text-accent">
                  {i + 1}
                </span>
                <p className="text-white/70 text-sm leading-relaxed pt-0.5">
                  {tip}
                </p>
              </li>
            ))}
          </ol>
        </div>

        {/* Best time to test */}
        <div className="rounded-2xl border border-accent/20 bg-accent/5 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="h-5 w-5 text-accent" />
            <h3 className="text-lg font-semibold text-white">Best Time to Test</h3>
          </div>
          <p className="text-white/70 text-sm leading-relaxed">
            {content.bestTimeToTest}
          </p>
        </div>
      </div>
    </section>
  )
}
