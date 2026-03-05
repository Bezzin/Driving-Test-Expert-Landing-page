import Link from 'next/link'
import { MapPin, ArrowRight } from 'lucide-react'
import type { DvsaCentre } from '@/lib/dvsa-types'

interface NearbyCentresProps {
  centre: DvsaCentre
  regionSlug: string
}

function getDifficultyForRate(rate: number, nationalAvg: number): string {
  const diff = rate - nationalAvg
  if (diff > 5) return 'Easy'
  if (diff > 0) return 'Above Average'
  if (diff > -5) return 'Below Average'
  return 'Hard'
}

function getDifficultyColor(label: string): string {
  switch (label) {
    case 'Easy':
      return 'text-green-400'
    case 'Above Average':
      return 'text-green-400'
    case 'Below Average':
      return 'text-amber-400'
    case 'Hard':
      return 'text-red-400'
    default:
      return 'text-white/60'
  }
}

export function NearbyCentres({ centre, regionSlug }: NearbyCentresProps) {
  if (centre.nearbyCentres.length === 0) return null

  const hasHigherPassRate = centre.nearbyCentres.some(
    n => n.passRate > centre.passRateOverall
  )

  return (
    <section className="py-16 px-6 max-w-7xl mx-auto">
      <h2 className="font-brand text-3xl font-bold tracking-tight text-white sm:text-4xl mb-8">
        Test Centres Near {centre.name}
      </h2>

      <div className="rounded-2xl border border-white/10 bg-black/40 overflow-hidden mb-6">
        <div className="flex items-center gap-2 px-6 py-4 border-b border-white/10">
          <MapPin className="h-5 w-5 text-accent" />
          <h3 className="text-lg font-semibold text-white">Nearby Centres</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-white/10 text-sm text-white/50">
                <th className="px-4 py-3 font-medium">Centre Name</th>
                <th className="px-4 py-3 font-medium">Distance</th>
                <th className="px-4 py-3 font-medium">Pass Rate</th>
                <th className="px-4 py-3 font-medium">Difficulty</th>
              </tr>
            </thead>
            <tbody>
              {centre.nearbyCentres.map(nearby => {
                const difficulty = getDifficultyForRate(nearby.passRate, centre.nationalAverage)
                return (
                  <tr
                    key={nearby.slug}
                    className="border-b border-white/5 hover:bg-white/5 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/test-centres/${nearby.slug}/`}
                        className="text-sm font-medium text-accent hover:text-white transition-colors"
                      >
                        {nearby.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm text-white/60">
                      {nearby.distanceMiles} miles
                    </td>
                    <td className="px-4 py-3 text-sm font-semibold text-white">
                      {nearby.passRate}%
                    </td>
                    <td className={`px-4 py-3 text-sm font-medium ${getDifficultyColor(difficulty)}`}>
                      {difficulty}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {hasHigherPassRate && (
        <p className="text-sm text-white/50 mb-4">
          Looking for a higher pass rate? Some nearby centres have better statistics.
          Compare options above to find the best fit for you.
        </p>
      )}

      <Link
        href={`/test-centres/regions/${regionSlug}/`}
        className="inline-flex items-center gap-2 text-sm font-medium text-accent hover:text-white transition-colors"
      >
        View all centres in {centre.region}
        <ArrowRight className="h-4 w-4" />
      </Link>
    </section>
  )
}
