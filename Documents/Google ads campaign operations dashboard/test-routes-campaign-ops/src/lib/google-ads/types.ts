export interface GeneratedCampaign {
  centreName: string
  centreSlug: string
  campaignName: string
  dailyBudgetMicros: bigint
  keywords: GeneratedKeyword[]
  ads: GeneratedAd[]
  negativeKeywords: string[]
  finalUrl: string
}

export interface GeneratedKeyword {
  text: string
  matchType: 'EXACT' | 'PHRASE'
}

export interface GeneratedAd {
  headlines: string[]
  descriptions: string[]
  finalUrl: string
  path1?: string
  path2?: string
  variantLabel: string
}

export interface GoogleAdsConfig {
  clientId: string
  clientSecret: string
  refreshToken: string
  developerToken: string
  customerId: string
  loginCustomerId?: string
}

export interface SyncResult {
  campaignsUpdated: number
  performanceRows: number
  errors: string[]
}
