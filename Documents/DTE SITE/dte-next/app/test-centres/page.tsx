import type { Metadata } from 'next'
import Link from 'next/link'
import { MapPin, BarChart3, Building2 } from 'lucide-react'
import { getAllCentres, getAllRegions, getCentresByRegion, getNationalAverage, getTotalCentres } from '@/lib/centres'
import { getPassRateBadge } from '@/lib/display-utils'
import { Navbar } from '@/components/Layout/Navbar'
import { Footer } from '@/components/Layout/Footer'

export const metadata: Metadata = {
  title: 'UK Driving Test Centres | Routes, Pass Rates & Maps for Every Centre',
  description:
    'Browse all UK driving test centres with pass rates, difficulty ratings, routes, and maps. Find your nearest centre and prepare for test day.',
  alternates: {
    canonical: '/test-centres/',
  },
  openGraph: {
    title: 'UK Driving Test Centres | Routes, Pass Rates & Maps for Every Centre',
    description:
      'Browse all UK driving test centres with pass rates, difficulty ratings, routes, and maps. Find your nearest centre and prepare for test day.',
    url: 'https://www.testroutesexpert.co.uk/test-centres/',
    siteName: 'Test Routes Expert',
    locale: 'en_GB',
    type: 'website',
  },
}


export default function TestCentresHub() {
  const allCentres = getAllCentres()
  const regions = getAllRegions()
  const nationalAverage = getNationalAverage()
  const totalCentres = getTotalCentres()

  const passRates = allCentres.map(c => c.passRateOverall)
  const minRate = Math.min(...passRates)
  const maxRate = Math.max(...passRates)

  const regionData = regions.map(region => {
    const centres = getCentresByRegion(region.slug)
      .slice()
      .sort((a, b) => b.passRateOverall - a.passRateOverall)
    return { ...region, centres }
  })

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
              <span className="mx-1">/</span>
              <span className="text-white/80">Test Centres</span>
            </li>
          </ol>
        </nav>

        {/* Hero */}
        <section className="py-12 px-6 max-w-7xl mx-auto">
          <h1 className="font-brand text-4xl font-black tracking-tight text-white sm:text-5xl md:text-6xl mb-6">
            UK Driving Test Centres
          </h1>
          <p className="max-w-3xl text-white/70 leading-relaxed text-lg mb-10">
            Explore every driving test centre across the United Kingdom with detailed pass rates,
            difficulty ratings, and real test routes. Whether you are choosing a test centre
            with the highest pass rate or looking for route maps at your local centre, we
            cover all {totalCentres} DVSA test centres grouped by region. Each centre page
            includes pass rate breakdowns by gender and age, historical trends, known test
            routes with turn-by-turn directions, common challenges, and expert tips to help
            you pass first time.
          </p>

          {/* Stats Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-16">
            <div className="rounded-2xl border border-white/10 bg-black/40 p-6 text-center">
              <div className="flex items-center justify-center gap-2 mb-2">
                <Building2 className="h-5 w-5 text-accent" />
                <span className="text-sm font-medium text-white/50">Total Centres</span>
              </div>
              <p className="text-3xl font-bold text-white">{totalCentres}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/40 p-6 text-center">
              <div className="flex items-center justify-center gap-2 mb-2">
                <BarChart3 className="h-5 w-5 text-accent" />
                <span className="text-sm font-medium text-white/50">National Average</span>
              </div>
              <p className="text-3xl font-bold text-white">{nationalAverage}%</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/40 p-6 text-center">
              <div className="flex items-center justify-center gap-2 mb-2">
                <MapPin className="h-5 w-5 text-accent" />
                <span className="text-sm font-medium text-white/50">Pass Rate Range</span>
              </div>
              <p className="text-3xl font-bold text-white">
                {minRate}% &ndash; {maxRate}%
              </p>
            </div>
          </div>
        </section>

        {/* Region Sections */}
        {regionData.map(region => (
          <section key={region.slug} className="py-10 px-6 max-w-7xl mx-auto">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
              <h2 className="font-brand text-2xl font-bold tracking-tight text-white sm:text-3xl">
                {region.name}
              </h2>
              <Link
                href={`/test-centres/regions/${region.slug}/`}
                className="text-sm font-medium text-accent hover:text-white transition-colors"
              >
                View all {region.centres.length} centres in {region.name} &rarr;
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {region.centres.map(centre => (
                <Link
                  key={centre.slug}
                  href={`/test-centres/${centre.slug}/`}
                  className="group rounded-2xl border border-white/10 bg-black/40 p-6 transition-all hover:border-accent/40 hover:bg-black/60"
                >
                  <h3 className="font-semibold text-white group-hover:text-accent transition-colors mb-3">
                    {centre.name}
                  </h3>
                  <div className="flex items-center justify-between">
                    <span
                      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-sm font-semibold ${getPassRateBadge(centre.passRateOverall)}`}
                    >
                      {centre.passRateOverall}%
                    </span>
                    <span className="text-xs text-white/50">{centre.difficultyLabel}</span>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        ))}

        {/* Links to aggregate pages */}
        <section className="py-16 px-6 max-w-7xl mx-auto">
          <h2 className="font-brand text-2xl font-bold tracking-tight text-white sm:text-3xl mb-6">
            Explore More
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Link
              href="/pass-rates/"
              className="rounded-2xl border border-white/10 bg-black/40 p-6 transition-all hover:border-accent/40 hover:bg-black/60 group"
            >
              <h3 className="font-semibold text-white group-hover:text-accent transition-colors mb-2">
                UK Pass Rates by Centre
              </h3>
              <p className="text-sm text-white/50">
                Full table of all {totalCentres} centres ranked by pass rate.
              </p>
            </Link>
            <Link
              href="/test-centres/easiest/"
              className="rounded-2xl border border-white/10 bg-black/40 p-6 transition-all hover:border-accent/40 hover:bg-black/60 group"
            >
              <h3 className="font-semibold text-white group-hover:text-accent transition-colors mb-2">
                Easiest Test Centres
              </h3>
              <p className="text-sm text-white/50">
                Top 20 centres with the highest pass rates in the UK.
              </p>
            </Link>
            <Link
              href="/test-centres/hardest/"
              className="rounded-2xl border border-white/10 bg-black/40 p-6 transition-all hover:border-accent/40 hover:bg-black/60 group"
            >
              <h3 className="font-semibold text-white group-hover:text-accent transition-colors mb-2">
                Hardest Test Centres
              </h3>
              <p className="text-sm text-white/50">
                Bottom 20 centres with the lowest pass rates in the UK.
              </p>
            </Link>
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}
