import type { Metadata } from 'next'
import Link from 'next/link'
import { ChevronRight, TrendingDown, MapPin } from 'lucide-react'
import { getAllCentres, getNationalAverage } from '@/lib/centres'
import { getRegionSlugMap } from '@/lib/display-utils'
import { Navbar } from '@/components/Layout/Navbar'
import { Footer } from '@/components/Layout/Footer'

export const metadata: Metadata = {
  title: 'Hardest Driving Test Centres in the UK 2026',
  description:
    'The 20 hardest driving test centres in the UK ranked by lowest pass rates. Learn what makes these centres challenging and how to prepare.',
  alternates: {
    canonical: '/test-centres/hardest/',
  },
  openGraph: {
    title: 'Hardest Driving Test Centres in the UK 2026',
    description:
      'The 20 hardest driving test centres in the UK ranked by lowest pass rates. Learn what makes these centres challenging and how to prepare.',
    url: 'https://www.testroutesexpert.co.uk/test-centres/hardest/',
    siteName: 'Test Routes Expert',
    locale: 'en_GB',
    type: 'website',
  },
}

export default function HardestCentresPage() {
  const allCentres = getAllCentres()
    .slice()
    .sort((a, b) => a.passRateOverall - b.passRateOverall)
  const bottom20 = allCentres.slice(0, 20)
  const nationalAverage = getNationalAverage()
  const regionSlugs = getRegionSlugMap()

  return (
    <>
      <Navbar />
      <main className="min-h-screen bg-bg pt-28">
        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="py-4 px-6 max-w-7xl mx-auto">
          <ol className="flex flex-wrap items-center gap-1 text-sm text-white/50">
            <li className="flex items-center gap-1">
              <Link href="/" className="transition-colors hover:text-accent">Home</Link>
            </li>
            <li className="flex items-center gap-1">
              <ChevronRight className="h-3 w-3 shrink-0" />
              <Link href="/test-centres/" className="transition-colors hover:text-accent">
                Test Centres
              </Link>
            </li>
            <li className="flex items-center gap-1">
              <ChevronRight className="h-3 w-3 shrink-0" />
              <span className="text-white/80">Hardest</span>
            </li>
          </ol>
        </nav>

        {/* Hero */}
        <section className="py-12 px-6 max-w-7xl mx-auto">
          <div className="flex items-center gap-3 mb-4">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-red-500/20 border border-red-500/30 px-3 py-1 text-sm font-semibold text-red-400">
              <TrendingDown className="h-4 w-4" />
              Lowest Pass Rates
            </span>
          </div>
          <h1 className="font-brand text-4xl font-black tracking-tight text-white sm:text-5xl md:text-6xl mb-6">
            Hardest Driving Test Centres in the UK 2026
          </h1>
          <div className="max-w-3xl text-white/70 leading-relaxed text-lg mb-10 space-y-4">
            <p>
              Certain driving test centres are notoriously difficult, recording pass
              rates well below the national average of {nationalAverage}%. The centres
              on this list present the greatest statistical challenge for learner
              drivers. Heavy traffic, complex road layouts, busy multi-lane
              roundabouts, and demanding urban environments all contribute to lower
              pass rates. Many of these centres are located in dense city areas where
              congestion is a constant factor during test hours.
            </p>
            <p>
              If your nearest centre appears on this list, do not be discouraged.
              Success at these centres is absolutely achievable with the right
              preparation. Practising the specific test routes used by your centre is
              one of the most effective strategies. Familiarise yourself with tricky
              junctions, one-way systems, and areas of heavy pedestrian activity.
              Consider booking your test at off-peak times when traffic is lighter.
              Our app provides turn-by-turn route guides for every centre listed
              below, giving you a significant advantage on test day.
            </p>
          </div>
        </section>

        {/* Bottom 20 Cards */}
        <section className="pb-16 px-6 max-w-7xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {bottom20.map((centre, index) => {
              const diff = nationalAverage - centre.passRateOverall

              return (
                <Link
                  key={centre.slug}
                  href={`/test-centres/${centre.slug}/`}
                  className="group rounded-2xl border border-white/10 bg-black/40 p-6 transition-all hover:border-red-500/40 hover:bg-black/60 relative"
                >
                  <span className="absolute top-3 right-3 text-xs font-bold text-white/20">
                    #{index + 1}
                  </span>
                  <h3 className="font-semibold text-white group-hover:text-red-400 transition-colors mb-2 pr-6">
                    {centre.name}
                  </h3>
                  <div className="flex items-center gap-1.5 text-xs text-white/50 mb-4">
                    <MapPin className="h-3 w-3" />
                    <span>{centre.region}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-2xl font-bold text-red-400">
                      {centre.passRateOverall}%
                    </span>
                    <span className="text-xs text-red-400/70">
                      -{diff.toFixed(1)}% vs avg
                    </span>
                  </div>
                </Link>
              )
            })}
          </div>
        </section>

        {/* Full table */}
        <section className="pb-16 px-6 max-w-7xl mx-auto">
          <div className="rounded-2xl border border-white/10 bg-black/40 overflow-hidden">
            <div className="flex items-center gap-2 px-6 py-4 border-b border-white/10">
              <TrendingDown className="h-5 w-5 text-red-400" />
              <h2 className="text-lg font-semibold text-white">
                Bottom 20 Hardest Centres &mdash; Full Details
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-white/10 text-sm text-white/50">
                    <th className="px-4 py-3 font-medium w-12 text-right">#</th>
                    <th className="px-4 py-3 font-medium">Centre Name</th>
                    <th className="px-4 py-3 font-medium hidden sm:table-cell">Region</th>
                    <th className="px-4 py-3 font-medium text-right">Pass Rate</th>
                    <th className="px-4 py-3 font-medium text-right hidden md:table-cell">
                      vs National Avg
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {bottom20.map((centre, index) => {
                    const diff = centre.passRateOverall - nationalAverage
                    const regionSlug = regionSlugs.get(centre.region) ?? ''

                    return (
                      <tr
                        key={centre.slug}
                        className="border-b border-white/5 hover:bg-white/5 transition-colors"
                      >
                        <td className="px-4 py-3 text-sm text-white/40 text-right">
                          {index + 1}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <Link
                            href={`/test-centres/${centre.slug}/`}
                            className="font-medium text-white hover:text-accent transition-colors"
                          >
                            {centre.name}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-sm hidden sm:table-cell">
                          {regionSlug ? (
                            <Link
                              href={`/test-centres/regions/${regionSlug}/`}
                              className="text-white/60 hover:text-accent transition-colors"
                            >
                              {centre.region}
                            </Link>
                          ) : (
                            <span className="text-white/60">{centre.region}</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm font-semibold text-right text-red-400">
                          {centre.passRateOverall}%
                        </td>
                        <td className="px-4 py-3 text-sm text-right text-red-400 hidden md:table-cell">
                          {diff.toFixed(1)}%
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Back links */}
        <section className="pb-16 px-6 max-w-7xl mx-auto flex flex-wrap gap-4">
          <Link
            href="/test-centres/"
            className="text-sm font-medium text-accent hover:text-white transition-colors"
          >
            &larr; All test centres
          </Link>
          <Link
            href="/test-centres/easiest/"
            className="text-sm font-medium text-accent hover:text-white transition-colors"
          >
            View easiest centres &rarr;
          </Link>
          <Link
            href="/pass-rates/"
            className="text-sm font-medium text-accent hover:text-white transition-colors"
          >
            Full pass rate table &rarr;
          </Link>
        </section>
      </main>
      <Footer />
    </>
  )
}
