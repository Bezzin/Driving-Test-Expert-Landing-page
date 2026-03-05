import centresData from '@/data/dvsa/centres.json'
import regionsData from '@/data/regions.json'
import type { DvsaCentre, RegionEntry } from './dvsa-types'

export function getAllCentres(): DvsaCentre[] {
  return centresData as DvsaCentre[]
}

export function getCentreBySlug(slug: string): DvsaCentre | undefined {
  return getAllCentres().find(c => c.slug === slug)
}

export function getCentresByRegion(regionSlug: string): DvsaCentre[] {
  const region = (regionsData as { regions: RegionEntry[] }).regions.find(
    r => r.slug === regionSlug
  )
  if (!region) return []
  return getAllCentres().filter(c => region.centres.includes(c.slug))
}

export function getAllRegions(): RegionEntry[] {
  return (regionsData as { regions: RegionEntry[] }).regions
}

export function getRegionBySlug(regionSlug: string): RegionEntry | undefined {
  return getAllRegions().find(r => r.slug === regionSlug)
}

export function getNationalAverage(): number {
  const centres = getAllCentres()
  const total = centres.reduce((sum, c) => sum + c.passRateOverall, 0)
  return Math.round((total / centres.length) * 10) / 10
}

export function getTotalCentres(): number {
  return getAllCentres().length
}
