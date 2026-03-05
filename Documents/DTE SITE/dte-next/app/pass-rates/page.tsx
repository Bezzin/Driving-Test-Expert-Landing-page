import type { Metadata } from 'next'
import Link from 'next/link'
import { ChevronRight, BarChart3 } from 'lucide-react'
import { getAllCentres, getNationalAverage, getTotalCentres } from '@/lib/centres'
import { getPassRateColor, getRegionSlugMap } from '@/lib/display-utils'
import { Navbar } from '@/components/Layout/Navbar'
import { Footer } from '@/components/Layout/Footer'

export const metadata: Metadata = {
  title: 'UK Driving Test Pass Rates by Centre 2026',
  description:
    'Complete table of UK driving test pass rates for every centre in 2026. Compare pass rates, see national averages, and find the easiest and hardest centres.',
  alternates: {
    canonical: '/pass-rates/',
  },
  openGraph: {
    title: 'UK Driving Test Pass Rates by Centre 2026',
    description:
      'Complete table of UK driving test pass rates for every centre in 2026. Compare pass rates, see national averages, and find the easiest and hardest centres.',
    url: 'https://www.testroutesexpert.co.uk/pass-rates/',
    siteName: 'Test Routes Expert',
    locale: 'en_GB',
    type: 'website',
  },
}

export default function PassRatesPage() {
  const allCentres = getAllCentres()
    .slice()
    .sort((a, b) => b.passRateOverall - a.passRateOverall)
  const nationalAverage = getNationalAverage()
  const totalCentres = getTotalCentres()
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
              <span className="text-white/80">Pass Rates</span>
            </li>
          </ol>
        </nav>

        {/* Hero */}
        <section className="py-12 px-6 max-w-7xl mx-auto">
          <h1 className="font-brand text-4xl font-black tracking-tight text-white sm:text-5xl md:text-6xl mb-6">
            UK Driving Test Pass Rates by Centre 2026
          </h1>
          <p className="max-w-3xl text-white/70 leading-relaxed text-lg mb-6">
            The complete list of pass rates for all {totalCentres} UK driving test centres,
            sorted from highest to lowest. The national average pass rate is{' '}
            <span className="text-accent font-semibold">{nationalAverage}%</span>.
            Use this table to compare centres in your area and find the one that gives
            you the best chance of passing.
          </p>

          <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-4 py-2 text-sm text-accent mb-10">
            <BarChart3 className="h-4 w-4" />
            National Average: {nationalAverage}%
          </div>
        </section>

        {/* Full Table */}
        <section className="pb-16 px-6 max-w-7xl mx-auto">
          <div className="rounded-2xl border border-white/10 bg-black/40 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-white/10 text-sm text-white/50">
                    <th className="px-4 py-3 font-medium w-12 text-right">#</th>
                    <th className="px-4 py-3 font-medium">Centre Name</th>
                    <th className="px-4 py-3 font-medium hidden sm:table-cell">Region</th>
                    <th className="px-4 py-3 font-medium text-right">Pass Rate</th>
                    <th className="px-4 py-3 font-medium text-right hidden md:table-cell">
                      Tests Conducted
                    </th>
                    <th className="px-4 py-3 font-medium hidden lg:table-cell">Difficulty</th>
                  </tr>
                </thead>
                <tbody>
                  {allCentres.map((centre, index) => {
                    const isNearAverage =
                      Math.abs(centre.passRateOverall - nationalAverage) < 0.5
                    const regionSlug = regionSlugs.get(centre.region) ?? ''

                    return (
                      <tr
                        key={centre.slug}
                        className={`border-b border-white/5 hover:bg-white/5 transition-colors ${
                          isNearAverage ? 'bg-accent/5 border-l-2 border-l-accent' : ''
                        }`}
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
                        <td
                          className={`px-4 py-3 text-sm font-semibold text-right ${getPassRateColor(centre.passRateOverall)}`}
                        >
                          {centre.passRateOverall}%
                        </td>
                        <td className="px-4 py-3 text-sm text-white/60 text-right hidden md:table-cell">
                          {centre.testsConductedTotal.toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-sm text-white/60 hidden lg:table-cell">
                          {centre.difficultyLabel}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Legend */}
          <div className="mt-4 flex flex-wrap gap-4 text-xs text-white/40">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-accent" />
              Highlighted rows are closest to the national average ({nationalAverage}%)
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-green-400" />
              Above 55%
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-amber-400" />
              45%&ndash;55%
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-red-400" />
              Below 45%
            </span>
          </div>
        </section>

        {/* Back link */}
        <section className="pb-16 px-6 max-w-7xl mx-auto">
          <Link
            href="/test-centres/"
            className="text-sm font-medium text-accent hover:text-white transition-colors"
          >
            &larr; Back to all UK test centres
          </Link>
        </section>
      </main>
      <Footer />
    </>
  )
}
