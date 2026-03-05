import { AlertTriangle, ChevronRight } from 'lucide-react'
import type { DvsaCentre } from '@/lib/dvsa-types'
import type { CentreContentEntry } from '@/lib/centre-content'

interface ChallengesSectionProps {
  centre: DvsaCentre
  content: CentreContentEntry | undefined
}

export function ChallengesSection({ centre, content }: ChallengesSectionProps) {
  if (!content) return null

  return (
    <section className="py-16 px-6 max-w-7xl mx-auto">
      <h2 className="font-brand text-3xl font-bold tracking-tight text-white sm:text-4xl mb-8">
        What Makes {centre.name} Challenging
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Key challenges */}
        <div className="rounded-2xl border border-white/10 bg-black/40 p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="h-5 w-5 text-amber-400" />
            <h3 className="text-lg font-semibold text-white">Key Challenges</h3>
          </div>
          <ul className="space-y-3">
            {content.keyChallenges.map((challenge, i) => (
              <li key={i} className="flex items-start gap-3 text-white/70 text-sm leading-relaxed">
                <ChevronRight className="h-4 w-4 text-accent shrink-0 mt-0.5" />
                {challenge}
              </li>
            ))}
          </ul>
        </div>

        {/* Difficulty analysis */}
        <div className="rounded-2xl border border-white/10 bg-black/40 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Difficulty Analysis</h3>
          <p className="text-white/70 text-sm leading-relaxed mb-4">
            {content.difficultyAnalysis}
          </p>

          {content.roadTypes.length > 0 && (
            <>
              <h4 className="text-sm font-semibold text-white/80 mb-3">
                Road Types to Prepare For
              </h4>
              <div className="flex flex-wrap gap-2">
                {content.roadTypes.map(type => (
                  <span
                    key={type}
                    className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-white/60 capitalize"
                  >
                    {type}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  )
}
