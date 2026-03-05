import type { Metadata } from 'next'
import Link from 'next/link'
import { ChevronRight, TrendingUp, MapPin } from 'lucide-react'
import { getAllCentres, getNationalAverage } from '@/lib/centres'
import { getRegionSlugMap } from '@/lib/display-utils'
import { Navbar } from '@/components/Layout/Navbar'
import { Footer } from '@/components/Layout/Footer'

export const metadata: Metadata = {
  title: 'Easiest Driving Test Centres in the UK 2026',
  description:
    'Discover the 20 easiest driving test centres in the UK based on pass rates. Find centres with the highest pass rates and learn what makes them easier.',
  alternates: {
    canonical: '/test-centres/easiest/',
  },
  openGraph: {
    title: 'Easiest Driving Test Centres in the UK 2026',
    description:
      'Discover the 20 easiest driving test centres in the UK based on pass rates. Find centres with the highest pass rates and learn what makes them easier.',
    url: 'https://www.testroutesexpert.co.uk/test-centres/easiest/',
    siteName: 'Test Routes Expert',
    locale: 'en_GB',
    type: 'website',
  },
}

export default function EasiestCentresPage() {
  const allCentres = getAllCentres()
    .slice()
    .sort((a, b) => b.passRateOverall - a.passRateOverall)
  const top20 = allCentres.slice(0, 20)
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
              <span className="text-white/80">Easiest</span>
            </li>
          </ol>
        </nav>

        {/* Hero */}
        <section className="py-12 px-6 max-w-7xl mx-auto">
          <div className="flex items-center gap-3 mb-4">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-green-500/20 border border-green-500/30 px-3 py-1 text-sm font-semibold text-green-400">
              <TrendingUp className="h-4 w-4" />
              Highest Pass Rates
            </span>
          </div>
          <h1 className="font-brand text-4xl font-black tracking-tight text-white sm:text-5xl md:text-6xl mb-6">
            Easiest Driving Test Centres in the UK 2026
          </h1>
          <div className="max-w-3xl text-white/70 leading-relaxed text-lg mb-10 space-y-4">
            <p>
              Some driving test centres consistently record higher pass rates than
              others, and while no test is truly &ldquo;easy,&rdquo; the centres on this list give
              candidates a statistically better chance of passing. Several factors
              contribute to higher pass rates: quieter roads with less congestion,
              simpler junction layouts, lower traffic density during test hours, and
              wider residential streets that are more forgiving for manoeuvres.
            </p>
            <p>
              Rural and semi-rural centres tend to dominate this list because they
              feature fewer hazards per mile, giving learners more time to react and
              demonstrate safe driving. Many of these centres also see fewer test
              candidates overall, which often correlates with calmer conditions on
              test day. The national average pass rate is {nationalAverage}%, but
              the centres below comfortably exceed that mark. Remember that thorough
              preparation and local route knowledge remain the most reliable ways to
              pass, regardless of which centre you choose.
            </p>
          </div>
        </section>

        {/* Top 20 Cards */}
        <section className="pb-16 px-6 max-w-7xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {top20.map((centre, index) => {
              const regionSlug = regionSlugs.get(centre.region) ?? ''
              const diff = centre.passRateOverall - nationalAverage

              return (
                <Link
                  key={centre.slug}
                  href={`/test-centres/${centre.slug}/`}
                  className="group rounded-2xl border border-white/10 bg-black/40 p-6 transition-all hover:border-green-500/40 hover:bg-black/60 relative"
                >
                  <span className="absolute top-3 right-3 text-xs font-bold text-white/20">
                    #{index + 1}
                  </span>
                  <h3 className="font-semibold text-white group-hover:text-green-400 transition-colors mb-2 pr-6">
                    {centre.name}
                  </h3>
                  <div className="flex items-center gap-1.5 text-xs text-white/50 mb-4">
                    <MapPin className="h-3 w-3" />
                    {regionSlug ? (
                      <span>{centre.region}</span>
                    ) : (
                      <span>{centre.region}</span>
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-2xl font-bold text-green-400">
                      {centre.passRateOverall}%
                    </span>
                    <span className="text-xs text-green-400/70">
                      +{diff.toFixed(1)}% vs avg
                    </span>
                  </div>
                </Link>
              )
            })}
          </div>
        </section>

        {/* Full table fallback */}
        <section className="pb-16 px-6 max-w-7xl mx-auto">
          <div className="rounded-2xl border border-white/10 bg-black/40 overflow-hidden">
            <div className="flex items-center gap-2 px-6 py-4 border-b border-white/10">
              <TrendingUp className="h-5 w-5 text-green-400" />
              <h2 className="text-lg font-semibold text-white">
                Top 20 Easiest Centres &mdash; Full Details
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
                  {top20.map((centre, index) => {
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
                        <td className="px-4 py-3 text-sm font-semibold text-right text-green-400">
                          {centre.passRateOverall}%
                        </td>
                        <td className="px-4 py-3 text-sm text-right text-green-400 hidden md:table-cell">
                          +{diff.toFixed(1)}%
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
            href="/test-centres/hardest/"
            className="text-sm font-medium text-accent hover:text-white transition-colors"
          >
            View hardest centres &rarr;
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
