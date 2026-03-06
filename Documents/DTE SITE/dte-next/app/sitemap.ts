import type { MetadataRoute } from 'next'
import { getAllCentres, getAllRegions } from '@/lib/centres'
import { getAllPosts } from '@/lib/blog'

export const dynamic = 'force-static'

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://www.testroutesexpert.co.uk'
  const now = new Date()

  const staticPages: MetadataRoute.Sitemap = [
    { url: baseUrl, lastModified: now, changeFrequency: 'monthly', priority: 1.0 },
    { url: `${baseUrl}/test-centres/`, lastModified: now, changeFrequency: 'weekly', priority: 0.9 },
    { url: `${baseUrl}/test-routes-app/`, lastModified: now, changeFrequency: 'monthly', priority: 0.8 },
    { url: `${baseUrl}/pass-rates/`, lastModified: now, changeFrequency: 'monthly', priority: 0.7 },
    { url: `${baseUrl}/test-centres/easiest/`, lastModified: now, changeFrequency: 'monthly', priority: 0.6 },
    { url: `${baseUrl}/test-centres/hardest/`, lastModified: now, changeFrequency: 'monthly', priority: 0.6 },
  ]

  const regionPages: MetadataRoute.Sitemap = getAllRegions().map(region => ({
    url: `${baseUrl}/test-centres/regions/${region.slug}/`,
    lastModified: now,
    changeFrequency: 'monthly' as const,
    priority: 0.7,
  }))

  const centrePages: MetadataRoute.Sitemap = getAllCentres().map(centre => ({
    url: `${baseUrl}/test-centres/${centre.slug}/`,
    lastModified: now,
    changeFrequency: 'monthly' as const,
    priority: 0.8,
  }))

  const blogPages: MetadataRoute.Sitemap = [
    { url: `${baseUrl}/blog/`, lastModified: now, changeFrequency: 'weekly' as const, priority: 0.7 },
    ...getAllPosts().map(post => ({
      url: `${baseUrl}/blog/${post.slug}/`,
      lastModified: new Date(post.publishedDate),
      changeFrequency: 'monthly' as const,
      priority: 0.6,
    })),
  ]

  return [...staticPages, ...regionPages, ...centrePages, ...blogPages]
}
