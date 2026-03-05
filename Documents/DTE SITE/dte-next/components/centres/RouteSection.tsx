import { Route, Navigation, Smartphone, Download } from 'lucide-react'
import type { DvsaCentre } from '@/lib/dvsa-types'
import type { CentreContentEntry } from '@/lib/centre-content'
import { APP_STORE_URL, PLAY_STORE_URL } from '@/lib/constants'

interface RouteSectionProps {
  centre: DvsaCentre
  content: CentreContentEntry | undefined
}

export function RouteSection({ centre, content }: RouteSectionProps) {
  const roadTypes = content?.roadTypes ?? []

  return (
    <section className="py-16 px-6 max-w-7xl mx-auto">
      <h2 className="font-brand text-3xl font-bold tracking-tight text-white sm:text-4xl mb-8">
        {centre.name} Driving Test Routes
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Route info */}
        <div className="rounded-2xl border border-white/10 bg-black/40 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Route className="h-5 w-5 text-accent" />
            <h3 className="text-lg font-semibold text-white">Route Information</h3>
          </div>
          <p className="text-white/70 leading-relaxed mb-4">
            {centre.totalRoutes
              ? `There are ${centre.totalRoutes} known test routes at ${centre.name}. Each route is designed to test a range of driving skills across different road types and conditions.`
              : `Test routes at ${centre.name} cover a variety of road types and driving scenarios. Routes are updated regularly by DVSA examiners.`}
          </p>

          {roadTypes.length > 0 && (
            <>
              <h4 className="text-sm font-semibold text-white/80 mb-3">Road Types You Will Encounter</h4>
              <div className="flex flex-wrap gap-2">
                {roadTypes.map(type => (
                  <span
                    key={type}
                    className="inline-flex items-center rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent capitalize"
                  >
                    {type}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>

        {/* App CTA */}
        <div className="rounded-2xl border border-accent/20 bg-accent/5 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Navigation className="h-5 w-5 text-accent" />
              <h3 className="text-lg font-semibold text-white">Practice All Routes in the App</h3>
            </div>
            <p className="text-white/70 leading-relaxed mb-2">
              The Test Routes Expert app gives you turn-by-turn navigation for
              every test route at {centre.name}. Practice each route as many
              times as you need before your test day.
            </p>
            <ul className="space-y-2 mb-6 text-sm text-white/60">
              <li className="flex items-start gap-2">
                <Smartphone className="h-4 w-4 text-accent shrink-0 mt-0.5" />
                Turn-by-turn navigation on every route
              </li>
              <li className="flex items-start gap-2">
                <Smartphone className="h-4 w-4 text-accent shrink-0 mt-0.5" />
                Track your progress as you complete routes
              </li>
              <li className="flex items-start gap-2">
                <Smartphone className="h-4 w-4 text-accent shrink-0 mt-0.5" />
                Speed awareness and junction warnings
              </li>
            </ul>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <a
              href={PLAY_STORE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-full bg-accent px-5 py-3 text-sm font-bold text-black transition-all hover:scale-[1.02] hover:bg-white active:scale-[0.98]"
            >
              <Download className="h-4 w-4" />
              Google Play
            </a>
            <a
              href={APP_STORE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-full border border-white/20 bg-white/5 px-5 py-3 text-sm font-bold text-white transition-all hover:border-accent hover:text-accent"
            >
              <Download className="h-4 w-4" />
              App Store
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
