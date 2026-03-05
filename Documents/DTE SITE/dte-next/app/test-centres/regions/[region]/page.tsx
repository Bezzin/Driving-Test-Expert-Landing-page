import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ChevronRight, BarChart3, TrendingUp, TrendingDown, Building2 } from 'lucide-react'
import {
  getAllRegions,
  getRegionBySlug,
  getCentresByRegion,
  getNationalAverage,
} from '@/lib/centres'
import { getPassRateColor } from '@/lib/display-utils'
import { Navbar } from '@/components/Layout/Navbar'
import { Footer } from '@/components/Layout/Footer'

export function generateStaticParams() {
  return getAllRegions().map(region => ({
    region: region.slug,
  }))
}

export function generateMetadata({
  params,
}: {
  params: Promise<{ region: string }>
}): Promise<Metadata> {
  return params.then(({ region: regionSlug }) => {
    const region = getRegionBySlug(regionSlug)
    if (!region) {
      return { title: 'Region Not Found' }
    }

    const title = `Driving Test Centres in ${region.name}`
    const description = `Browse all driving test centres in ${region.name} with pass rates, difficulty ratings, and test routes. Find the best centre for your driving test.`

    return {
      title,
      description,
      alternates: {
        canonical: `/test-centres/regions/${regionSlug}/`,
      },
      openGraph: {
        title,
        description,
        url: `https://www.testroutesexpert.co.uk/test-centres/regions/${regionSlug}/`,
        siteName: 'Test Routes Expert',
        locale: 'en_GB',
        type: 'website',
      },
    }
  })
}

export default async function RegionPage({
  params,
}: {
  params: Promise<{ region: string }>
}) {
  const { region: regionSlug } = await params
  const region = getRegionBySlug(regionSlug)

  if (!region) {
    notFound()
  }

  const centres = getCentresByRegion(regionSlug)
    .slice()
    .sort((a, b) => b.passRateOverall - a.passRateOverall)
  const nationalAverage = getNationalAverage()

  const regionPassRates = centres.map(c => c.passRateOverall)
  const regionAverage =
    Math.round(
      (regionPassRates.reduce((sum, r) => sum + r, 0) / regionPassRates.length) * 10
    ) / 10

  const easiest = centres[0]
  const hardest = centres[centres.length - 1]

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
              <span className="text-white/80">{region.name}</span>
            </li>
          </ol>
        </nav>

        {/* Hero */}
        <section className="py-12 px-6 max-w-7xl mx-auto">
          <h1 className="font-brand text-4xl font-black tracking-tight text-white sm:text-5xl md:text-6xl mb-6">
            Driving Test Centres in {region.name}
          </h1>
          <p className="max-w-3xl text-white/70 leading-relaxed text-lg mb-10">
            There are {centres.length} driving test centres in {region.name}. The regional
            average pass rate is {regionAverage}%, compared to the national average of{' '}
            {nationalAverage}%. Browse all centres below to find pass rates, difficulty
            ratings, and links to detailed route information.
          </p>

          {/* Region Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-16">
            <div className="rounded-2xl border border-white/10 bg-black/40 p-6 text-center">
              <div className="flex items-center justify-center gap-2 mb-2">
                <Building2 className="h-5 w-5 text-accent" />
                <span className="text-sm font-medium text-white/50">Centres</span>
              </div>
              <p className="text-3xl font-bold text-white">{centres.length}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/40 p-6 text-center">
              <div className="flex items-center justify-center gap-2 mb-2">
                <BarChart3 className="h-5 w-5 text-accent" />
                <span className="text-sm font-medium text-white/50">Regional Average</span>
              </div>
              <p className={`text-3xl font-bold ${getPassRateColor(regionAverage)}`}>
                {regionAverage}%
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/40 p-6 text-center">
              <div className="flex items-center justify-center gap-2 mb-2">
                <TrendingUp className="h-5 w-5 text-green-400" />
                <span className="text-sm font-medium text-white/50">Easiest Centre</span>
              </div>
              <p className="text-lg font-bold text-white truncate" title={easiest.name}>
                {easiest.name}
              </p>
              <p className="text-sm text-green-400">{easiest.passRateOverall}%</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/40 p-6 text-center">
              <div className="flex items-center justify-center gap-2 mb-2">
                <TrendingDown className="h-5 w-5 text-red-400" />
                <span className="text-sm font-medium text-white/50">Hardest Centre</span>
              </div>
              <p className="text-lg font-bold text-white truncate" title={hardest.name}>
                {hardest.name}
              </p>
              <p className="text-sm text-red-400">{hardest.passRateOverall}%</p>
            </div>
          </div>
        </section>

        {/* Centres Table */}
        <section className="pb-16 px-6 max-w-7xl mx-auto">
          <div className="rounded-2xl border border-white/10 bg-black/40 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-white/10 text-sm text-white/50">
                    <th className="px-4 py-3 font-medium">Centre Name</th>
                    <th className="px-4 py-3 font-medium text-right">Pass Rate</th>
                    <th className="px-4 py-3 font-medium text-right hidden sm:table-cell">
                      Tests Conducted
                    </th>
                    <th className="px-4 py-3 font-medium hidden md:table-cell">Difficulty</th>
                  </tr>
                </thead>
                <tbody>
                  {centres.map(centre => (
                    <tr
                      key={centre.slug}
                      className="border-b border-white/5 hover:bg-white/5 transition-colors"
                    >
                      <td className="px-4 py-3 text-sm">
                        <Link
                          href={`/test-centres/${centre.slug}/`}
                          className="font-medium text-white hover:text-accent transition-colors"
                        >
                          {centre.name}
                        </Link>
                      </td>
                      <td
                        className={`px-4 py-3 text-sm font-semibold text-right ${getPassRateColor(centre.passRateOverall)}`}
                      >
                        {centre.passRateOverall}%
                      </td>
                      <td className="px-4 py-3 text-sm text-white/60 text-right hidden sm:table-cell">
                        {centre.testsConductedTotal.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-sm text-white/60 hidden md:table-cell">
                        {centre.difficultyLabel}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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
