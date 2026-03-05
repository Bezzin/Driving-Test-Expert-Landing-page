import { getAllRegions } from '@/lib/centres'

export function getPassRateColor(rate: number): string {
  if (rate > 55) return 'text-green-400'
  if (rate >= 45) return 'text-amber-400'
  return 'text-red-400'
}

export function getPassRateBadge(rate: number): string {
  if (rate > 55) return 'bg-green-500/20 text-green-400 border-green-500/30'
  if (rate >= 45) return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
  return 'bg-red-500/20 text-red-400 border-red-500/30'
}

export function getRegionSlugMap(): Map<string, string> {
  const regions = getAllRegions()
  const map = new Map<string, string>()
  for (const region of regions) {
    map.set(region.name, region.slug)
  }
  return map
}
