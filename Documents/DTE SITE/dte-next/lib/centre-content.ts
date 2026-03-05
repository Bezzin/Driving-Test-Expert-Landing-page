import contentData from '@/data/centre-content.json'

export interface CentreContentEntry {
  slug: string
  name: string
  areaDescription: string
  keyChallenges: string[]
  specificTips: string[]
  bestTimeToTest: string
  roadTypes: string[]
  difficultyAnalysis: string
}

export function getContentBySlug(slug: string): CentreContentEntry | undefined {
  return (contentData as CentreContentEntry[]).find(c => c.slug === slug)
}
