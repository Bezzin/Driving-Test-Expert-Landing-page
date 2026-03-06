import * as fs from 'fs'
import * as path from 'path'
import type { YouTubeVideo } from '../lib/blog-types'

const VIDEOS_FILE = path.join(__dirname, '..', 'data', 'youtube', 'videos.json')
const TRANSCRIPTS_DIR = path.join(__dirname, '..', 'data', 'youtube', 'transcripts')

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function fetchCaptionUrl(videoId: string): Promise<string | null> {
  const res = await fetch(`https://www.youtube.com/watch?v=${videoId}`, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
      'Accept-Language': 'en-GB,en;q=0.9',
    },
  })
  if (!res.ok) return null

  const html = await res.text()
  const match = html.match(/"captionTracks":(\[.*?\])/)
  if (!match) return null

  const tracks = JSON.parse(match[1]) as Array<{ languageCode: string; baseUrl: string }>

  // Prefer English, fall back to first available
  const enTrack = tracks.find(t => t.languageCode === 'en') ?? tracks[0]
  return enTrack?.baseUrl ?? null
}

async function fetchTranscriptText(captionUrl: string): Promise<string> {
  // Fetch the XML captions
  const res = await fetch(captionUrl)
  if (!res.ok) throw new Error(`Failed to fetch captions: ${res.status}`)

  const xml = await res.text()

  // Parse XML text segments: <text start="..." dur="...">content</text>
  const segments: string[] = []
  const regex = new RegExp('<text[^>]*>(.*?)</text>', 'gs')
  let m: RegExpExecArray | null
  while ((m = regex.exec(xml)) !== null) {
    // Decode HTML entities
    const decoded = m[1]
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
      .replace(/\n/g, ' ')
    segments.push(decoded)
  }

  return segments.join(' ')
}

async function main() {
  const videos: YouTubeVideo[] = JSON.parse(fs.readFileSync(VIDEOS_FILE, 'utf-8'))
  fs.mkdirSync(TRANSCRIPTS_DIR, { recursive: true })

  let fetched = 0
  let skipped = 0

  for (const video of videos) {
    const outFile = path.join(TRANSCRIPTS_DIR, `${video.videoId}.json`)

    if (fs.existsSync(outFile)) {
      console.log(`  Already have: ${video.title}`)
      fetched++
      continue
    }

    console.log(`Fetching transcript: ${video.title}...`)
    try {
      const captionUrl = await fetchCaptionUrl(video.videoId)
      if (!captionUrl) {
        console.warn(`  Skipped (no captions): ${video.title}`)
        skipped++
        await sleep(1000)
        continue
      }

      const text = await fetchTranscriptText(captionUrl)
      const wordCount = text.split(/\s+/).length

      if (wordCount < 50) {
        console.warn(`  Skipped (too short: ${wordCount} words): ${video.title}`)
        skipped++
        await sleep(1000)
        continue
      }

      fs.writeFileSync(outFile, JSON.stringify({
        videoId: video.videoId,
        title: video.title,
        transcript: text,
        wordCount,
      }, null, 2))
      fetched++
      console.log(`  OK (${wordCount} words)`)
    } catch (err) {
      console.warn(`  Skipped: ${video.title} — ${(err as Error).message}`)
      skipped++
    }

    await sleep(1500)
  }

  console.log(`\nDone. Fetched: ${fetched}, Skipped: ${skipped}`)
}

main().catch(console.error)
