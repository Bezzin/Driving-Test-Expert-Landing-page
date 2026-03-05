import { MapPin, Route, Users, Download } from 'lucide-react'
import type { DvsaCentre } from '@/lib/dvsa-types'
import { APP_STORE_URL, PLAY_STORE_URL } from '@/lib/constants'

interface CentreHeroProps {
  centre: DvsaCentre
}

function getPassRateColor(rate: number): string {
  if (rate > 55) return 'bg-green-500/20 text-green-400 border-green-500/30'
  if (rate >= 45) return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
  return 'bg-red-500/20 text-red-400 border-red-500/30'
}

function getDifficultyColor(label: string): string {
  const lower = label.toLowerCase()
  if (lower.includes('easy') || lower.includes('above average'))
    return 'bg-green-500/20 text-green-400 border-green-500/30'
  if (lower.includes('average'))
    return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
  return 'bg-red-500/20 text-red-400 border-red-500/30'
}

export function CentreHero({ centre }: CentreHeroProps) {
  const passRateColor = getPassRateColor(centre.passRateOverall)
  const difficultyColor = getDifficultyColor(centre.difficultyLabel)

  return (
    <section className="py-16 px-6 max-w-7xl mx-auto">
      <div className="flex flex-col gap-6">
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={`inline-flex items-center rounded-full border px-3 py-1 text-sm font-semibold ${passRateColor}`}
          >
            {centre.passRateOverall}% Pass Rate
          </span>
          <span
            className={`inline-flex items-center rounded-full border px-3 py-1 text-sm font-semibold ${difficultyColor}`}
          >
            {centre.difficultyLabel}
          </span>
        </div>

        <h1 className="font-brand text-4xl font-black tracking-tight text-white sm:text-5xl md:text-6xl">
          {centre.name} Driving Test Routes
        </h1>

        <div className="flex flex-wrap items-center gap-4 text-white/60 text-sm">
          <span className="inline-flex items-center gap-1.5">
            <MapPin className="h-4 w-4 text-accent" />
            {centre.region}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Route className="h-4 w-4 text-accent" />
            {centre.totalRoutes
              ? `${centre.totalRoutes} routes available`
              : 'Routes available in the app'}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Users className="h-4 w-4 text-accent" />
            {centre.testsConductedTotal.toLocaleString()} tests conducted
          </span>
        </div>

        <p className="max-w-2xl text-white/70 leading-relaxed">
          Practice the exact driving test routes used at {centre.name} with
          turn-by-turn navigation. Know every junction, roundabout, and tricky
          spot before test day.
        </p>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mt-2">
          <a
            href={PLAY_STORE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-full bg-accent px-6 py-3.5 text-sm font-bold text-black transition-all hover:scale-[1.02] hover:bg-white active:scale-[0.98]"
          >
            <Download className="h-4 w-4" />
            Get on Google Play
          </a>
          <a
            href={APP_STORE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-full border border-white/20 bg-white/5 px-6 py-3.5 text-sm font-bold text-white transition-all hover:border-accent hover:text-accent"
          >
            <Download className="h-4 w-4" />
            Download on App Store
          </a>
        </div>
      </div>
    </section>
  )
}
