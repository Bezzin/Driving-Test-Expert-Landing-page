import type { Metadata } from 'next'
import { Inter, Poppins } from 'next/font/google'
import './globals.css'

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
  weight: ['300', '400', '500', '600'],
})

const poppins = Poppins({
  variable: '--font-poppins',
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800', '900'],
})

export const metadata: Metadata = {
  metadataBase: new URL('https://www.testroutesexpert.co.uk'),
  title: {
    default: 'Test Routes Expert | UK Driving Test Routes & Pass Rates',
    template: '%s | Test Routes Expert',
  },
  description: 'Practice real UK driving test routes with turn-by-turn navigation. 350+ centres, pass rates, tips and maps.',
  keywords: ['driving test routes', 'UK driving test', 'test centre pass rates', 'DVSA test routes', 'driving test practice'],
  authors: [{ name: 'Driving Test Expert' }],
  creator: 'Driving Test Expert',
  publisher: 'Driving Test Expert',
  formatDetection: { telephone: false },
  openGraph: {
    type: 'website',
    locale: 'en_GB',
    siteName: 'Test Routes Expert',
  },
  twitter: {
    card: 'summary_large_image',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en-GB" className="scroll-smooth">
      <body className={`${inter.variable} ${poppins.variable} antialiased`}>
        {children}
      </body>
    </html>
  )
}
