export interface NearbyCentre {
  slug: string
  name: string
  distanceMiles: number
  passRate: number
}

export interface DvsaCentre {
  name: string
  slug: string
  region: string
  latitude: number
  longitude: number
  passRateOverall: number
  passRateMale: number
  passRateFemale: number
  passRateFirstAttempt: number | null
  passRateFirstAttemptMale: number | null
  passRateFirstAttemptFemale: number | null
  passRateAutomatic: number | null
  passRateByAge: Record<string, number>
  passRateHistory: Array<{ year: string; rate: number }>
  testsConductedTotal: number
  testsConductedMale: number
  testsConductedFemale: number
  zeroFaultPasses: number | null
  cancellations: {
    dvsaCancelled: number
    candidateCancelled: number
    noShows: number
  } | null
  nearbyCentres: NearbyCentre[]
  dataPeriod: string
  nationalAverage: number
  difficultyRank: number
  difficultyLabel: string
  totalRoutes: number | null
}

export interface RegionEntry {
  name: string
  slug: string
  centres: string[]
}

export interface RegionsData {
  regions: RegionEntry[]
}
