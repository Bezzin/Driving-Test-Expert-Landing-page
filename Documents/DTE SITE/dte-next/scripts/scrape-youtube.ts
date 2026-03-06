import * as cheerio from 'cheerio'
import * as fs from 'fs'
import * as path from 'path'
import type { YouTubeVideo } from '../lib/blog-types'

const CHANNEL_URL = 'https://www.youtube.com/@JoshRamwell/videos'
const OUTPUT_DIR = path.join(__dirname, '..', 'data', 'youtube')
const OUTPUT_FILE = path.join(OUTPUT_DIR, 'videos.json')

function parseViewCount(text: string): number {
  const cleaned = text.toLowerCase().replace(/\s/g, '')
  if (cleaned.includes('k')) return Math.round(parseFloat(cleaned) * 1000)
  if (cleaned.includes('m')) return Math.round(parseFloat(cleaned) * 1000000)
  return parseInt(cleaned.replace(/[^0-9]/g, ''), 10) || 0
}

async function scrapeChannel(): Promise<YouTubeVideo[]> {
  // YouTube's /videos page renders client-side. We fetch the page HTML
  // and parse the ytInitialData JSON blob embedded in the script tags.
  console.log('Fetching channel page...')
  const res = await fetch(CHANNEL_URL, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
      'Accept-Language': 'en-GB,en;q=0.9',
    },
  })

  if (!res.ok) throw new Error(`Failed to fetch channel: ${res.status}`)

  const html = await res.text()

  // Extract ytInitialData from script tags
  const match = html.match(/var ytInitialData = ({.*?});<\/script>/s)
  if (!match) {
    // Fallback: try another pattern
    const match2 = html.match(/ytInitialData\s*=\s*({.*?});/s)
    if (!match2) throw new Error('Could not find ytInitialData in page HTML')
    return parseYtInitialData(match2[1])
  }

  return parseYtInitialData(match[1])
}

function parseYtInitialData(jsonStr: string): YouTubeVideo[] {
  const data = JSON.parse(jsonStr)
  const videos: YouTubeVideo[] = []

  // Navigate the deeply nested YouTube data structure
  const tabs = data?.contents?.twoColumnBrowseResultsRenderer?.tabs ?? []
  for (const tab of tabs) {
    const tabContent = tab?.tabRenderer?.content
    const richGrid = tabContent?.richGridRenderer
    if (!richGrid) continue

    for (const item of richGrid.contents ?? []) {
      const videoRenderer = item?.richItemRenderer?.content?.videoRenderer
      if (!videoRenderer) continue

      const videoId = videoRenderer.videoId
      if (!videoId) continue

      const title = videoRenderer.title?.runs?.[0]?.text ?? ''
      const viewText = videoRenderer.viewCountText?.simpleText ?? videoRenderer.viewCountText?.runs?.[0]?.text ?? '0'
      const duration = videoRenderer.lengthText?.simpleText ?? ''
      const published = videoRenderer.publishedTimeText?.simpleText ?? ''

      videos.push({
        videoId,
        title,
        url: `https://www.youtube.com/watch?v=${videoId}`,
        views: parseViewCount(viewText),
        duration,
        publishedDate: published,
        thumbnailUrl: `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`,
      })
    }
  }

  return videos
}

async function main() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true })

  const videos = await scrapeChannel()
  console.log(`Found ${videos.length} videos`)

  // Sort by views descending
  videos.sort((a, b) => b.views - a.views)

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(videos, null, 2))
  console.log(`Saved to ${OUTPUT_FILE}`)

  // Show top 10
  console.log('\nTop 10 by views:')
  videos.slice(0, 10).forEach((v, i) => {
    console.log(`  ${i + 1}. ${v.title} (${v.views.toLocaleString()} views)`)
  })
}

main().catch(console.error)
