import type { Metadata } from 'next'
import { HomePageContent } from '@/components/Pages/HomePage'

export const metadata: Metadata = {
  title: 'Driving Test Expert — We Get You Passed',
  description:
    'Practice real UK driving test routes with turn-by-turn navigation. 350+ test centres, 4000+ routes. ReTest cancellation finder. Join 50,000+ UK learners.',
  openGraph: {
    title: 'Driving Test Expert — We Get You Passed',
    description:
      'Practice real UK driving test routes with turn-by-turn navigation.',
    url: 'https://www.testroutesexpert.co.uk',
    siteName: 'Test Routes Expert',
    locale: 'en_GB',
    type: 'website',
  },
}

export default function HomePage() {
  return <HomePageContent />
}
