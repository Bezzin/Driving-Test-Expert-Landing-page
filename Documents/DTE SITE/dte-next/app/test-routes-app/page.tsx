import type { Metadata } from 'next'
import { AppLandingPage } from '@/components/Pages/AppLandingPage'

export const metadata: Metadata = {
  title: 'Test Routes Expert App — Practice Real Driving Test Routes',
  description:
    'Download Test Routes Expert. Practice real driving test routes with turn-by-turn navigation. 350+ UK test centres. Available on iOS and Android.',
}

export default function TestRoutesAppPage() {
  return <AppLandingPage />
}
