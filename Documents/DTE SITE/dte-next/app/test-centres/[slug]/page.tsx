import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { getAllCentres, getCentreBySlug, getAllRegions } from '@/lib/centres'
import { getContentBySlug } from '@/lib/centre-content'
import { SchemaMarkup } from '@/components/centres/SchemaMarkup'
import { Breadcrumbs } from '@/components/centres/Breadcrumbs'
import { CentreHero } from '@/components/centres/CentreHero'
import { PassRateStats } from '@/components/centres/PassRateStats'
import { RouteSection } from '@/components/centres/RouteSection'
import { ChallengesSection } from '@/components/centres/ChallengesSection'
import { TipsSection } from '@/components/centres/TipsSection'
import { NearbyCentres } from '@/components/centres/NearbyCentres'
import { CentreFaq } from '@/components/centres/CentreFaq'
import { AppCtaBlock } from '@/components/centres/AppCtaBlock'
import { RoutePreview } from '@/components/centres/RoutePreview'
import { Navbar } from '@/components/Layout/Navbar'
import { Footer } from '@/components/Layout/Footer'

// Test: load route data for Stafford only
function getRouteData(slug: string) {
  try {
    if (slug === 'stafford') {
      return require('@/data/routes/stafford.json')
    }
  } catch {
    return null
  }
  return null
}

function getRegionSlug(regionName: string): string {
  const regions = getAllRegions()
  const region = regions.find(r => r.name === regionName)
  return region?.slug ?? regionName.toLowerCase().replace(/\s+/g, '-')
}

export function generateStaticParams() {
  return getAllCentres().map(centre => ({
    slug: centre.slug,
  }))
}

export function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>
}): Promise<Metadata> {
  return params.then(({ slug }) => {
    const centre = getCentreBySlug(slug)
    if (!centre) {
      return {
        title: 'Centre Not Found',
      }
    }

    const title = `${centre.name} Driving Test Routes 2026 | Pass Rate, Tips & Maps`
    const description = `Practice real ${centre.name} driving test routes. ${centre.name} pass rate: ${centre.passRateOverall}%. Routes, tips, and maps to help you pass first time.`

    return {
      title,
      description,
      alternates: {
        canonical: `/test-centres/${slug}/`,
      },
      openGraph: {
        title,
        description,
        url: `https://www.testroutesexpert.co.uk/test-centres/${slug}/`,
        siteName: 'Test Routes Expert',
        locale: 'en_GB',
        type: 'website',
      },
    }
  })
}

export default async function CentrePage({
  params,
}: {
  params: Promise<{ slug: string }>
}) {
  const { slug } = await params
  const centre = getCentreBySlug(slug)

  if (!centre) {
    notFound()
  }

  const content = getContentBySlug(slug)
  const regionSlug = getRegionSlug(centre.region)
  const routeData = getRouteData(slug)

  return (
    <>
      <SchemaMarkup centre={centre} content={content} regionSlug={regionSlug} />
      <Navbar />
      <main className="min-h-screen bg-bg pt-28">
        <Breadcrumbs
          centreName={centre.name}
          regionName={centre.region}
          regionSlug={regionSlug}
        />
        <CentreHero centre={centre} />
        <PassRateStats centre={centre} />
        {routeData ? (
          <RoutePreview
            centreName={centre.name}
            centreSlug={centre.slug}
            postcode={routeData.postcode}
            routeCount={routeData.routeCount}
            allRoads={routeData.allRoads}
            routes={routeData.routes}
            latitude={centre.latitude}
            longitude={centre.longitude}
          />
        ) : (
          <RouteSection centre={centre} content={content} />
        )}
        <ChallengesSection centre={centre} content={content} />
        <TipsSection centre={centre} content={content} />
        <NearbyCentres centre={centre} regionSlug={regionSlug} />
        <CentreFaq centre={centre} content={content} />
        <AppCtaBlock />
      </main>
      <Footer />
    </>
  )
}
