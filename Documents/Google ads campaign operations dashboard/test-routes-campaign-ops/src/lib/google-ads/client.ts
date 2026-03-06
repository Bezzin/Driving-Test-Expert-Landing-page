import { GoogleAdsApi } from 'google-ads-api'
import type { GoogleAdsConfig } from './types'

let clientInstance: GoogleAdsApi | null = null

export function getGoogleAdsClient(): GoogleAdsApi | null {
  if (process.env.DRY_RUN === 'true') {
    return null
  }

  if (clientInstance) {
    return clientInstance
  }

  const config: GoogleAdsConfig = {
    clientId: process.env.GOOGLE_ADS_CLIENT_ID!,
    clientSecret: process.env.GOOGLE_ADS_CLIENT_SECRET!,
    refreshToken: process.env.GOOGLE_ADS_REFRESH_TOKEN!,
    developerToken: process.env.GOOGLE_ADS_DEVELOPER_TOKEN!,
    customerId: process.env.GOOGLE_ADS_CUSTOMER_ID!,
    loginCustomerId: process.env.GOOGLE_ADS_LOGIN_CUSTOMER_ID,
  }

  clientInstance = new GoogleAdsApi({
    client_id: config.clientId,
    client_secret: config.clientSecret,
    developer_token: config.developerToken,
  })

  return clientInstance
}

export function getCustomer() {
  const client = getGoogleAdsClient()
  if (!client) return null

  return client.Customer({
    customer_id: process.env.GOOGLE_ADS_CUSTOMER_ID!,
    login_customer_id: process.env.GOOGLE_ADS_LOGIN_CUSTOMER_ID,
    refresh_token: process.env.GOOGLE_ADS_REFRESH_TOKEN!,
  })
}

export function isDryRun(): boolean {
  return process.env.DRY_RUN === 'true'
}
