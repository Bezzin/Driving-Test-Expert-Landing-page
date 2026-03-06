export interface BlogPost {
  slug: string
  title: string
  metaDescription: string
  publishedDate: string
  category: BlogCategory
  tags: string[]
  youtubeVideoId: string
  youtubeTitle: string
  youtubeViews: number
  estimatedReadMinutes: number
  content: {
    introduction: string
    sections: Array<{
      heading: string
      body: string
    }>
    keyTakeaways: string[]
  }
  faqs: Array<{
    question: string
    answer: string
  }>
  relatedCentres: Array<{
    slug: string
    name: string
    reason: string
  }>
  relatedPostSlugs: string[]
  seoKeywords: string[]
}

export type BlogCategory =
  | 'manoeuvres'
  | 'junctions'
  | 'road-types'
  | 'test-prep'
  | 'common-faults'
  | 'general-driving'

export const BLOG_CATEGORIES: Record<BlogCategory, { label: string; description: string }> = {
  'manoeuvres': { label: 'Manoeuvres', description: 'Bay parking, parallel park, emergency stop and more' },
  'junctions': { label: 'Junctions', description: 'Roundabouts, crossroads, T-junctions and other junctions' },
  'road-types': { label: 'Road Types', description: 'Dual carriageways, motorways, country lanes' },
  'test-prep': { label: 'Test Prep', description: 'Show me tell me, what to expect, managing nerves' },
  'common-faults': { label: 'Common Faults', description: 'Mirror checks, observation, speed awareness' },
  'general-driving': { label: 'General Driving', description: 'Night driving, weather, motorway tips' },
}

export interface YouTubeVideo {
  videoId: string
  title: string
  url: string
  views: number
  duration: string
  publishedDate: string
  thumbnailUrl: string
}

export interface CategorisedVideo extends YouTubeVideo {
  category: BlogCategory
  tags: string[]
  targetKeyword: string
  suggestedSlug: string
  matchingCentres: Array<{ slug: string; name: string; reason: string }>
  priority: number
}
