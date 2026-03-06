# YouTube-to-Blog Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an automated pipeline that scrapes Josh Ramwell's YouTube channel, extracts transcripts, generates SEO-optimised blog posts via Gemini, and publishes them as statically-generated pages in the existing dte-next Next.js site.

**Architecture:** Five standalone TypeScript scripts chain together: scrape channel -> fetch transcripts -> categorise/prioritise -> generate posts via Gemini -> update centre pages with blog links. Output is JSON in `data/blog/`. Next.js reads JSON at build time via `generateStaticParams`, same pattern as the existing 300+ centre pages.

**Tech Stack:** Next.js 16 (App Router, `output: 'export'`), React 19, Tailwind CSS 4, `@google/genai` (Gemini), `youtube-transcript`, `cheerio`, `tsx`, TypeScript.

---

## Prerequisites / Blockers

| Item | Status | Notes |
|------|--------|-------|
| Gemini API key | **NEEDED** | Add `GEMINI_API_KEY` to `dte-next/.env.local`. Get from https://aistudio.google.com/apikey |
| `@google/genai` | Have | Already in `dte-next/package.json` |
| YouTube channel URL | Have | `https://www.youtube.com/@JoshRamwell` |
| DVSA centre data | Have | `dte-next/data/dvsa/centres.json` (322 centres) |
| Centre content data | Have | `dte-next/data/centre-content.json` |
| `tsx` | Have | Already in devDependencies |

**ACTION REQUIRED before starting:** Add `GEMINI_API_KEY=your-key-here` to `dte-next/.env.local`.

---

## Phase 1: Dependencies & Types

### Task 1.1: Install new dependencies

**Files:**
- Modify: `dte-next/package.json`

**Step 1: Install packages**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npm install youtube-transcript cheerio`
Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npm install -D @types/cheerio`

Expected: Both packages added to `package.json`

**Step 2: Verify installs**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && node -e "require('youtube-transcript'); require('cheerio'); console.log('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
cd "c:/Users/Nathaniel/Documents/DTE SITE"
git add dte-next/package.json dte-next/package-lock.json
git commit -m "chore: add youtube-transcript and cheerio dependencies"
```

---

### Task 1.2: Define blog types

**Files:**
- Create: `dte-next/lib/blog-types.ts`

**Step 1: Create the types file**

```typescript
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
```

**Step 2: Commit**

```bash
git add dte-next/lib/blog-types.ts
git commit -m "feat: add blog and YouTube type definitions"
```

---

### Task 1.3: Add GEMINI_API_KEY to .env.local

**Files:**
- Modify: `dte-next/.env.local`

**Step 1: Append the key placeholder**

Add this line to the end of `dte-next/.env.local`:

```
# Gemini (for blog content generation)
GEMINI_API_KEY=
```

**Step 2: Remind user to fill in the key**

The user must paste their Gemini API key before running the generate script. Get one from https://aistudio.google.com/apikey.

**Step 3: Commit (do NOT commit the actual key)**

```bash
git add dte-next/.env.local
git commit -m "chore: add GEMINI_API_KEY placeholder to .env.local"
```

---

## Phase 2: YouTube Scraping & Transcripts

### Task 2.1: Scrape YouTube channel

**Files:**
- Create: `dte-next/scripts/scrape-youtube.ts`
- Create: `dte-next/data/youtube/videos.json` (generated output)

**Step 1: Create the scrape script**

```typescript
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
```

**Step 2: Run the scrape**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npx tsx scripts/scrape-youtube.ts`

Expected: `data/youtube/videos.json` created with video metadata. Console shows top 10 videos by view count.

**Note:** YouTube's HTML structure changes frequently. If `ytInitialData` parsing fails, the script will throw a clear error. In that case, adjust the parsing logic or use an alternative approach (e.g., `yt-dlp --flat-playlist --dump-json`).

**Step 3: Verify output**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && node -e "const d = require('./data/youtube/videos.json'); console.log('Videos:', d.length); console.log('Sample:', JSON.stringify(d[0], null, 2))"`

Expected: Multiple videos, each with `videoId`, `title`, `views`, `url`.

**Step 4: Commit**

```bash
git add dte-next/scripts/scrape-youtube.ts dte-next/data/youtube/videos.json
git commit -m "feat: add YouTube channel scraper — extract video metadata"
```

---

### Task 2.2: Fetch transcripts

**Files:**
- Create: `dte-next/scripts/fetch-transcripts.ts`
- Create: `dte-next/data/youtube/transcripts/*.json` (generated output)

**Step 1: Create the transcript fetcher**

```typescript
import { YoutubeTranscript } from 'youtube-transcript'
import * as fs from 'fs'
import * as path from 'path'
import type { YouTubeVideo } from '../lib/blog-types'

const VIDEOS_FILE = path.join(__dirname, '..', 'data', 'youtube', 'videos.json')
const TRANSCRIPTS_DIR = path.join(__dirname, '..', 'data', 'youtube', 'transcripts')

// Rate limit: wait between requests to avoid being blocked
function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function fetchTranscript(videoId: string): Promise<string | null> {
  try {
    const transcript = await YoutubeTranscript.fetchTranscript(videoId, { lang: 'en' })
    if (!transcript || transcript.length === 0) return null
    // Join all segments into plain text
    return transcript.map(seg => seg.text).join(' ')
  } catch (err) {
    console.warn(`  Skipped ${videoId}: ${(err as Error).message}`)
    return null
  }
}

async function main() {
  const videos: YouTubeVideo[] = JSON.parse(fs.readFileSync(VIDEOS_FILE, 'utf-8'))
  fs.mkdirSync(TRANSCRIPTS_DIR, { recursive: true })

  let fetched = 0
  let skipped = 0

  for (const video of videos) {
    const outFile = path.join(TRANSCRIPTS_DIR, `${video.videoId}.json`)

    // Skip if already fetched
    if (fs.existsSync(outFile)) {
      console.log(`  Already have: ${video.title}`)
      fetched++
      continue
    }

    console.log(`Fetching transcript: ${video.title}...`)
    const text = await fetchTranscript(video.videoId)

    if (text) {
      const wordCount = text.split(/\s+/).length
      fs.writeFileSync(outFile, JSON.stringify({
        videoId: video.videoId,
        title: video.title,
        transcript: text,
        wordCount,
      }, null, 2))
      fetched++
      console.log(`  OK (${wordCount} words)`)
    } else {
      skipped++
    }

    // Rate limit: 1 second between requests
    await sleep(1000)
  }

  console.log(`\nDone. Fetched: ${fetched}, Skipped: ${skipped}`)
}

main().catch(console.error)
```

**Step 2: Run the fetcher**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npx tsx scripts/fetch-transcripts.ts`

Expected: `data/youtube/transcripts/` directory populated with one JSON file per video. Some videos may be skipped (no captions available). This will take a while due to rate limiting.

**Step 3: Verify output**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && ls data/youtube/transcripts/ | head -5`
Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && node -e "const d = require('./data/youtube/transcripts/' + require('fs').readdirSync('./data/youtube/transcripts')[0]); console.log(d.title, '-', d.wordCount, 'words'); console.log(d.transcript.substring(0, 200))"`

Expected: Transcript text visible, reasonable word count (500-5000+).

**Step 4: Commit**

```bash
git add dte-next/scripts/fetch-transcripts.ts
# Don't commit transcripts directory (too large, regenerable)
echo "data/youtube/transcripts/" >> dte-next/.gitignore
git add dte-next/.gitignore
git commit -m "feat: add YouTube transcript fetcher"
```

---

## Phase 3: Categorise & Generate

### Task 3.1: Categorise and prioritise videos

**Files:**
- Create: `dte-next/scripts/categorise-videos.ts`
- Create: `dte-next/data/youtube/categorised.json` (generated output)

**Step 1: Create the categorisation script**

This script uses Gemini to categorise each video by topic, assign tags, suggest a blog slug, and match to relevant centre pages.

```typescript
import { GoogleGenAI } from '@google/genai'
import * as fs from 'fs'
import * as path from 'path'
import * as dotenv from 'dotenv'
import type { YouTubeVideo, CategorisedVideo, BlogCategory } from '../lib/blog-types'
import type { DvsaCentre } from '../lib/dvsa-types'

dotenv.config({ path: path.join(__dirname, '..', '.env.local') })

const VIDEOS_FILE = path.join(__dirname, '..', 'data', 'youtube', 'videos.json')
const TRANSCRIPTS_DIR = path.join(__dirname, '..', 'data', 'youtube', 'transcripts')
const CENTRES_FILE = path.join(__dirname, '..', 'data', 'dvsa', 'centres.json')
const CONTENT_FILE = path.join(__dirname, '..', 'data', 'centre-content.json')
const OUTPUT_FILE = path.join(__dirname, '..', 'data', 'youtube', 'categorised.json')

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY! })

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function categoriseVideo(
  video: YouTubeVideo,
  transcriptSnippet: string,
  centreNames: string[]
): Promise<Omit<CategorisedVideo, keyof YouTubeVideo> | null> {
  const prompt = `You are categorising a YouTube video about UK driving tests for a blog.

VIDEO TITLE: ${video.title}
TRANSCRIPT EXCERPT (first 500 words): ${transcriptSnippet}

Categorise this video. Return ONLY a JSON object with these fields:
{
  "category": one of "manoeuvres" | "junctions" | "road-types" | "test-prep" | "common-faults" | "general-driving",
  "tags": array of 3-6 specific topic tags (e.g. "roundabouts", "bay-parking", "mirror-checks"),
  "targetKeyword": the primary SEO keyword this blog post should target (e.g. "roundabouts driving test"),
  "suggestedSlug": URL slug for the blog post (e.g. "roundabouts-driving-test-guide"),
  "matchingCentreReasons": array of 2-3 short reasons why this topic relates to specific driving test centres (e.g. "centres with challenging roundabouts nearby")
}

Return ONLY valid JSON, no markdown fences, no explanation.`

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-2.0-flash',
      contents: prompt,
    })

    const text = response.text?.trim() ?? ''
    // Strip markdown code fences if present
    const jsonStr = text.replace(/^```json?\n?/i, '').replace(/\n?```$/i, '').trim()
    const parsed = JSON.parse(jsonStr)

    return {
      category: parsed.category as BlogCategory,
      tags: parsed.tags ?? [],
      targetKeyword: parsed.targetKeyword ?? '',
      suggestedSlug: parsed.suggestedSlug ?? '',
      matchingCentres: [],  // Will be filled in next step
      priority: 0,          // Will be calculated
    }
  } catch (err) {
    console.warn(`  Failed to categorise: ${video.title} — ${(err as Error).message}`)
    return null
  }
}

function matchCentresToTopic(
  tags: string[],
  centres: DvsaCentre[],
  contentMap: Record<string, { keyChallenges?: string[]; roadTypes?: string[] }>
): Array<{ slug: string; name: string; reason: string }> {
  const matches: Array<{ slug: string; name: string; reason: string; score: number }> = []

  for (const centre of centres) {
    const content = contentMap[centre.slug]
    if (!content) continue

    const challenges = (content.keyChallenges ?? []).join(' ').toLowerCase()
    const roadTypes = (content.roadTypes ?? []).join(' ').toLowerCase()
    const combined = challenges + ' ' + roadTypes

    let score = 0
    let reason = ''
    for (const tag of tags) {
      const normalised = tag.toLowerCase().replace(/-/g, ' ')
      if (combined.includes(normalised)) {
        score++
        reason = `Known for ${normalised} challenges`
      }
    }

    if (score > 0) {
      matches.push({ slug: centre.slug, name: centre.name, reason, score })
    }
  }

  return matches
    .sort((a, b) => b.score - a.score)
    .slice(0, 5)
    .map(({ slug, name, reason }) => ({ slug, name, reason }))
}

async function main() {
  if (!process.env.GEMINI_API_KEY) {
    console.error('ERROR: Set GEMINI_API_KEY in dte-next/.env.local')
    process.exit(1)
  }

  const videos: YouTubeVideo[] = JSON.parse(fs.readFileSync(VIDEOS_FILE, 'utf-8'))
  const centres: DvsaCentre[] = JSON.parse(fs.readFileSync(CENTRES_FILE, 'utf-8'))
  const contentMap: Record<string, { keyChallenges?: string[]; roadTypes?: string[] }> =
    JSON.parse(fs.readFileSync(CONTENT_FILE, 'utf-8'))

  // Filter to videos that have transcripts
  const videosWithTranscripts = videos.filter(v => {
    const tFile = path.join(TRANSCRIPTS_DIR, `${v.videoId}.json`)
    return fs.existsSync(tFile)
  })

  console.log(`${videosWithTranscripts.length} videos have transcripts (of ${videos.length} total)`)

  const categorised: CategorisedVideo[] = []

  for (let i = 0; i < videosWithTranscripts.length; i++) {
    const video = videosWithTranscripts[i]
    console.log(`[${i + 1}/${videosWithTranscripts.length}] Categorising: ${video.title}`)

    const tFile = path.join(TRANSCRIPTS_DIR, `${video.videoId}.json`)
    const tData = JSON.parse(fs.readFileSync(tFile, 'utf-8'))
    const snippet = tData.transcript.split(/\s+/).slice(0, 500).join(' ')

    const result = await categoriseVideo(video, snippet, centres.map(c => c.name))
    if (!result) continue

    // Match centres to this video's tags
    const matchingCentres = matchCentresToTopic(result.tags, centres, contentMap)

    // Calculate priority: views * (1 + 0.1 * matching centres)
    const priority = video.views * (1 + 0.1 * matchingCentres.length)

    categorised.push({
      ...video,
      ...result,
      matchingCentres,
      priority,
    })

    // Rate limit Gemini calls
    await sleep(500)
  }

  // Sort by priority descending
  categorised.sort((a, b) => b.priority - a.priority)

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(categorised, null, 2))
  console.log(`\nCategorised ${categorised.length} videos. Saved to ${OUTPUT_FILE}`)

  console.log('\nTop 10 by priority:')
  categorised.slice(0, 10).forEach((v, i) => {
    console.log(`  ${i + 1}. [${v.category}] ${v.title} (${v.views.toLocaleString()} views, ${v.matchingCentres.length} centre matches)`)
  })
}

main().catch(console.error)
```

**Step 2: Install dotenv (for .env.local loading in scripts)**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npm install dotenv`

**Step 3: Run categorisation**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npx tsx scripts/categorise-videos.ts`

Expected: `data/youtube/categorised.json` with all videos tagged, sorted by priority.

**Step 4: Commit**

```bash
git add dte-next/scripts/categorise-videos.ts dte-next/data/youtube/categorised.json
git commit -m "feat: add video categorisation with Gemini + centre matching"
```

---

### Task 3.2: Generate blog posts via Gemini

**Files:**
- Create: `dte-next/scripts/generate-blog-posts.ts`
- Create: `dte-next/data/blog/*.json` (generated output)

**Step 1: Create the blog generator script**

```typescript
import { GoogleGenAI } from '@google/genai'
import * as fs from 'fs'
import * as path from 'path'
import * as dotenv from 'dotenv'
import type { CategorisedVideo, BlogPost } from '../lib/blog-types'
import type { DvsaCentre } from '../lib/dvsa-types'

dotenv.config({ path: path.join(__dirname, '..', '.env.local') })

const CATEGORISED_FILE = path.join(__dirname, '..', 'data', 'youtube', 'categorised.json')
const TRANSCRIPTS_DIR = path.join(__dirname, '..', 'data', 'youtube', 'transcripts')
const CENTRES_FILE = path.join(__dirname, '..', 'data', 'dvsa', 'centres.json')
const BLOG_DIR = path.join(__dirname, '..', 'data', 'blog')

// How many posts to generate per run (set high for full run, low for testing)
const MAX_POSTS = parseInt(process.env.MAX_BLOG_POSTS ?? '50', 10)

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY! })

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function getWordCount(post: BlogPost): number {
  const introWords = post.content.introduction.split(/\s+/).length
  const sectionWords = post.content.sections.reduce(
    (sum, s) => sum + s.heading.split(/\s+/).length + s.body.split(/\s+/).length,
    0
  )
  const takeawayWords = post.content.keyTakeaways.join(' ').split(/\s+/).length
  const faqWords = post.faqs.reduce(
    (sum, f) => sum + f.question.split(/\s+/).length + f.answer.split(/\s+/).length,
    0
  )
  return introWords + sectionWords + takeawayWords + faqWords
}

async function generatePost(
  video: CategorisedVideo,
  transcript: string,
  centres: DvsaCentre[]
): Promise<BlogPost | null> {
  const nationalAvg = centres.reduce((s, c) => s + c.passRateOverall, 0) / centres.length
  const totalCentres = centres.length

  // Build centre context for the prompt
  const centreContext = video.matchingCentres
    .map(mc => {
      const centre = centres.find(c => c.slug === mc.slug)
      if (!centre) return ''
      return `- ${centre.name} (slug: ${centre.slug}, pass rate: ${centre.passRateOverall}%, ${mc.reason})`
    })
    .filter(Boolean)
    .join('\n')

  const prompt = `You are writing a blog post for Test Routes Expert (testroutesexpert.co.uk), a UK driving test preparation website.

TASK: Transform this YouTube video transcript into a structured, SEO-optimised blog post.

SOURCE VIDEO TITLE: ${video.title}
TARGET SEO KEYWORD: ${video.targetKeyword}
CATEGORY: ${video.category}
TAGS: ${video.tags.join(', ')}

TRANSCRIPT:
${transcript}

DVSA DATA TO REFERENCE:
- National average pass rate: ${nationalAvg.toFixed(1)}%
- Total UK test centres: ${totalCentres}
- Data period: April 2024 - March 2025

RELATED TEST CENTRES (link to these in the content):
${centreContext || 'No specific centre matches — link to /test-centres/ hub instead.'}

REQUIREMENTS:
1. Title: SEO-optimised, targeting "${video.targetKeyword}". 50-65 characters.
2. Meta description: 150-155 characters, includes target keyword.
3. Introduction: 80-120 words. Hook the reader, preview the content, mention the keyword naturally.
4. Main content: 3-5 sections with H2 headings. Total 800-1200 words across all sections.
   - Restructure the transcript into logical, well-organised sections
   - Maintain Josh's practical, encouraging tone
   - Include internal links as HTML anchor tags: <a href="/test-centres/{slug}/">{Centre Name}</a>
   - Include at least one link to <a href="/test-centres/">our test centres hub</a>
   - Reference DVSA data naturally where relevant (don't force it)
   - Write in second person ("you") directed at learner drivers
5. Key takeaways: 4-6 bullet points summarising main advice.
6. FAQs: 3-5 questions targeting "People Also Ask" queries for this topic.
   - Each answer: 40-80 words, data-enriched where possible.
7. SEO keywords: 5-8 related keywords for this post.

OUTPUT FORMAT: Return ONLY a valid JSON object matching this exact structure (no markdown fences):
{
  "title": "string",
  "metaDescription": "string",
  "content": {
    "introduction": "string (HTML)",
    "sections": [{"heading": "string", "body": "string (HTML)"}],
    "keyTakeaways": ["string"]
  },
  "faqs": [{"question": "string", "answer": "string"}],
  "seoKeywords": ["string"]
}

CRITICAL: Return ONLY the JSON. No explanation, no code fences.`

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-2.0-flash',
      contents: prompt,
    })

    const text = response.text?.trim() ?? ''
    const jsonStr = text.replace(/^```json?\n?/i, '').replace(/\n?```$/i, '').trim()
    const parsed = JSON.parse(jsonStr)

    const post: BlogPost = {
      slug: video.suggestedSlug,
      title: parsed.title,
      metaDescription: parsed.metaDescription,
      publishedDate: new Date().toISOString().split('T')[0],
      category: video.category,
      tags: video.tags,
      youtubeVideoId: video.videoId,
      youtubeTitle: video.title,
      youtubeViews: video.views,
      estimatedReadMinutes: Math.max(3, Math.round(getWordCount({
        ...parsed,
        slug: video.suggestedSlug,
        publishedDate: '',
        category: video.category,
        tags: video.tags,
        youtubeVideoId: video.videoId,
        youtubeTitle: video.title,
        youtubeViews: video.views,
        estimatedReadMinutes: 0,
        relatedCentres: video.matchingCentres,
        relatedPostSlugs: [],
        seoKeywords: parsed.seoKeywords ?? [],
        content: parsed.content,
        faqs: parsed.faqs,
      }) / 250)),
      content: parsed.content,
      faqs: parsed.faqs ?? [],
      relatedCentres: video.matchingCentres,
      relatedPostSlugs: [], // Filled in post-processing
      seoKeywords: parsed.seoKeywords ?? [],
    }

    return post
  } catch (err) {
    console.error(`  Failed: ${video.title} — ${(err as Error).message}`)
    return null
  }
}

async function main() {
  if (!process.env.GEMINI_API_KEY) {
    console.error('ERROR: Set GEMINI_API_KEY in dte-next/.env.local')
    process.exit(1)
  }

  const categorised: CategorisedVideo[] = JSON.parse(fs.readFileSync(CATEGORISED_FILE, 'utf-8'))
  const centres: DvsaCentre[] = JSON.parse(fs.readFileSync(CENTRES_FILE, 'utf-8'))

  fs.mkdirSync(BLOG_DIR, { recursive: true })

  const toGenerate = categorised.slice(0, MAX_POSTS)
  console.log(`Generating ${toGenerate.length} blog posts...`)

  const allPosts: BlogPost[] = []

  for (let i = 0; i < toGenerate.length; i++) {
    const video = toGenerate[i]
    const outFile = path.join(BLOG_DIR, `${video.suggestedSlug}.json`)

    // Skip if already generated
    if (fs.existsSync(outFile)) {
      console.log(`  Already exists: ${video.suggestedSlug}`)
      allPosts.push(JSON.parse(fs.readFileSync(outFile, 'utf-8')))
      continue
    }

    // Load transcript
    const tFile = path.join(TRANSCRIPTS_DIR, `${video.videoId}.json`)
    if (!fs.existsSync(tFile)) {
      console.warn(`  No transcript: ${video.title}`)
      continue
    }
    const tData = JSON.parse(fs.readFileSync(tFile, 'utf-8'))

    console.log(`[${i + 1}/${toGenerate.length}] Generating: ${video.suggestedSlug}...`)
    const post = await generatePost(video, tData.transcript, centres)

    if (post) {
      const wordCount = getWordCount(post)
      console.log(`  OK (${wordCount} words, ${post.faqs.length} FAQs, ${post.relatedCentres.length} centres)`)
      fs.writeFileSync(outFile, JSON.stringify(post, null, 2))
      allPosts.push(post)
    }

    // Rate limit: 2 seconds between Gemini calls for content generation
    await sleep(2000)
  }

  // Post-processing: fill in relatedPostSlugs by matching shared tags
  console.log('\nLinking related posts...')
  for (const post of allPosts) {
    const related = allPosts
      .filter(other => other.slug !== post.slug)
      .map(other => {
        const sharedTags = post.tags.filter(t => other.tags.includes(t))
        return { slug: other.slug, score: sharedTags.length }
      })
      .filter(r => r.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 3)
      .map(r => r.slug)

    post.relatedPostSlugs = related

    // Re-save with related posts
    const outFile = path.join(BLOG_DIR, `${post.slug}.json`)
    fs.writeFileSync(outFile, JSON.stringify(post, null, 2))
  }

  console.log(`\nDone. Generated ${allPosts.length} blog posts in ${BLOG_DIR}`)
}

main().catch(console.error)
```

**Step 2: Run generation (test with 3 first)**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && MAX_BLOG_POSTS=3 npx tsx scripts/generate-blog-posts.ts`

Expected: 3 JSON files in `data/blog/`, each with full blog post content.

**Step 3: Verify a generated post**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && node -e "const f=require('fs').readdirSync('./data/blog')[0]; const d=require('./data/blog/'+f); console.log('Title:', d.title); console.log('Words:', d.content.sections.reduce((s,x)=>s+x.body.split(' ').length,0)); console.log('FAQs:', d.faqs.length); console.log('Centres:', d.relatedCentres.length)"`

Expected: Title shown, 800+ words, 3+ FAQs, centre links present.

**Step 4: Run full generation**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npx tsx scripts/generate-blog-posts.ts`

Expected: All posts generated. Previously generated posts are skipped (idempotent).

**Step 5: Commit**

```bash
git add dte-next/scripts/generate-blog-posts.ts dte-next/data/blog/
git commit -m "feat: add Gemini blog post generator with centre linking"
```

---

## Phase 4: Next.js Blog Pages

### Task 4.1: Create blog data loader

**Files:**
- Create: `dte-next/lib/blog.ts`

**Step 1: Write the data loader**

```typescript
import * as fs from 'fs'
import * as path from 'path'
import type { BlogPost, BlogCategory } from './blog-types'

const BLOG_DIR = path.join(process.cwd(), 'data', 'blog')

let _allPosts: BlogPost[] | null = null

export function getAllPosts(): BlogPost[] {
  if (_allPosts) return _allPosts

  const files = fs.readdirSync(BLOG_DIR).filter(f => f.endsWith('.json'))
  _allPosts = files.map(f => {
    const raw = fs.readFileSync(path.join(BLOG_DIR, f), 'utf-8')
    return JSON.parse(raw) as BlogPost
  })

  // Sort by published date descending (newest first)
  _allPosts.sort((a, b) => b.publishedDate.localeCompare(a.publishedDate))

  return _allPosts
}

export function getPostBySlug(slug: string): BlogPost | undefined {
  return getAllPosts().find(p => p.slug === slug)
}

export function getPostsByCategory(category: BlogCategory): BlogPost[] {
  return getAllPosts().filter(p => p.category === category)
}

export function getRelatedPosts(post: BlogPost): BlogPost[] {
  return post.relatedPostSlugs
    .map(slug => getPostBySlug(slug))
    .filter((p): p is BlogPost => p !== undefined)
}
```

**Step 2: Verify it loads**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npx tsx -e "import { getAllPosts } from './lib/blog'; console.log('Posts:', getAllPosts().length)"`

Expected: Shows the number of generated posts.

**Step 3: Commit**

```bash
git add dte-next/lib/blog.ts
git commit -m "feat: add blog data loader"
```

---

### Task 4.2: Create blog post page

**Files:**
- Create: `dte-next/app/blog/[slug]/page.tsx`
- Create: `dte-next/components/blog/BlogSchemaMarkup.tsx`

**Step 1: Create the schema markup component**

Create `dte-next/components/blog/BlogSchemaMarkup.tsx`:

```typescript
import type { BlogPost } from '@/lib/blog-types'

interface BlogSchemaMarkupProps {
  post: BlogPost
}

export function BlogSchemaMarkup({ post }: BlogSchemaMarkupProps) {
  const url = `https://www.testroutesexpert.co.uk/blog/${post.slug}/`

  const schemas = [
    {
      '@context': 'https://schema.org',
      '@type': 'Article',
      headline: post.title,
      description: post.metaDescription,
      url,
      datePublished: post.publishedDate,
      dateModified: post.publishedDate,
      author: {
        '@type': 'Person',
        name: 'Josh Ramwell',
        url: 'https://www.youtube.com/@JoshRamwell',
      },
      publisher: {
        '@type': 'Organization',
        name: 'Driving Test Expert',
        url: 'https://www.testroutesexpert.co.uk/',
      },
      inLanguage: 'en-GB',
    },
    {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        {
          '@type': 'ListItem',
          position: 1,
          name: 'Home',
          item: 'https://www.testroutesexpert.co.uk/',
        },
        {
          '@type': 'ListItem',
          position: 2,
          name: 'Blog',
          item: 'https://www.testroutesexpert.co.uk/blog/',
        },
        {
          '@type': 'ListItem',
          position: 3,
          name: post.title,
          item: url,
        },
      ],
    },
    {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: post.faqs.map(faq => ({
        '@type': 'Question',
        name: faq.question,
        acceptedAnswer: {
          '@type': 'Answer',
          text: faq.answer,
        },
      })),
    },
    {
      '@context': 'https://schema.org',
      '@type': 'VideoObject',
      name: post.youtubeTitle,
      description: post.metaDescription,
      thumbnailUrl: `https://i.ytimg.com/vi/${post.youtubeVideoId}/hqdefault.jpg`,
      uploadDate: post.publishedDate,
      embedUrl: `https://www.youtube.com/embed/${post.youtubeVideoId}`,
      contentUrl: `https://www.youtube.com/watch?v=${post.youtubeVideoId}`,
    },
  ]

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schemas) }}
    />
  )
}
```

**Step 2: Create the blog post page**

Create `dte-next/app/blog/[slug]/page.tsx`:

```typescript
import { getAllPosts, getPostBySlug, getRelatedPosts } from '@/lib/blog'
import { BLOG_CATEGORIES } from '@/lib/blog-types'
import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import { Navbar } from '@/components/Layout/Navbar'
import { Footer } from '@/components/Layout/Footer'
import { AppCtaBlock } from '@/components/centres/AppCtaBlock'
import { BlogSchemaMarkup } from '@/components/blog/BlogSchemaMarkup'
import { HelpCircle, Clock, Calendar, Tag, ChevronRight, Play } from 'lucide-react'

interface PageProps {
  params: Promise<{ slug: string }>
}

export async function generateStaticParams() {
  return getAllPosts().map(post => ({ slug: post.slug }))
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const post = getPostBySlug(slug)
  if (!post) return {}

  return {
    title: post.title,
    description: post.metaDescription,
    alternates: { canonical: `/blog/${slug}/` },
    openGraph: {
      title: post.title,
      description: post.metaDescription,
      url: `/blog/${slug}/`,
      type: 'article',
      publishedTime: post.publishedDate,
      authors: ['Josh Ramwell'],
      images: [`https://i.ytimg.com/vi/${post.youtubeVideoId}/maxresdefault.jpg`],
    },
  }
}

export default async function BlogPostPage({ params }: PageProps) {
  const { slug } = await params
  const post = getPostBySlug(slug)
  if (!post) notFound()

  const relatedPosts = getRelatedPosts(post)
  const categoryInfo = BLOG_CATEGORIES[post.category]

  return (
    <div className="min-h-screen bg-bg text-white">
      <Navbar />
      <BlogSchemaMarkup post={post} />

      <main className="pt-32 pb-16">
        {/* Breadcrumb */}
        <div className="max-w-4xl mx-auto px-6 mb-8">
          <nav className="flex items-center gap-2 text-sm text-white/50">
            <a href="/" className="hover:text-accent transition-colors">Home</a>
            <ChevronRight className="h-3 w-3" />
            <a href="/blog/" className="hover:text-accent transition-colors">Blog</a>
            <ChevronRight className="h-3 w-3" />
            <span className="text-white/70 truncate">{post.title}</span>
          </nav>
        </div>

        {/* Hero */}
        <header className="max-w-4xl mx-auto px-6 mb-10">
          <div className="flex items-center gap-3 mb-4">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-accent/10 border border-accent/20 px-3 py-1 text-xs font-semibold text-accent">
              <Tag className="h-3 w-3" />
              {categoryInfo.label}
            </span>
            <span className="flex items-center gap-1.5 text-xs text-white/50">
              <Clock className="h-3 w-3" />
              {post.estimatedReadMinutes} min read
            </span>
            <span className="flex items-center gap-1.5 text-xs text-white/50">
              <Calendar className="h-3 w-3" />
              {new Date(post.publishedDate).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}
            </span>
          </div>
          <h1 className="font-brand text-3xl sm:text-4xl md:text-5xl font-black tracking-tight text-white leading-tight">
            {post.title}
          </h1>
        </header>

        {/* YouTube Embed */}
        <div className="max-w-4xl mx-auto px-6 mb-12">
          <div className="rounded-2xl border border-white/10 overflow-hidden bg-black">
            <div className="relative aspect-video">
              <iframe
                src={`https://www.youtube.com/embed/${post.youtubeVideoId}`}
                title={post.youtubeTitle}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                className="absolute inset-0 w-full h-full"
                loading="lazy"
              />
            </div>
            <div className="px-4 py-3 flex items-center gap-2 text-sm text-white/50 border-t border-white/10">
              <Play className="h-3.5 w-3.5 text-accent" />
              <span>Watch the full video: {post.youtubeTitle}</span>
            </div>
          </div>
        </div>

        {/* Introduction */}
        <article className="max-w-4xl mx-auto px-6">
          <div
            className="text-lg text-white/80 leading-relaxed mb-10 [&_a]:text-accent [&_a]:underline [&_a]:underline-offset-2 hover:[&_a]:text-white [&_a]:transition-colors"
            dangerouslySetInnerHTML={{ __html: post.content.introduction }}
          />

          {/* Main content sections */}
          {post.content.sections.map((section, i) => (
            <section key={i} className="mb-10">
              <h2 className="font-brand text-2xl sm:text-3xl font-bold text-white mb-4">
                {section.heading}
              </h2>
              <div
                className="text-white/75 leading-relaxed space-y-4 [&_a]:text-accent [&_a]:underline [&_a]:underline-offset-2 hover:[&_a]:text-white [&_a]:transition-colors [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:space-y-2 [&_ol]:list-decimal [&_ol]:pl-6 [&_ol]:space-y-2 [&_strong]:text-white [&_p]:mb-3"
                dangerouslySetInnerHTML={{ __html: section.body }}
              />
            </section>
          ))}

          {/* Key Takeaways */}
          <section className="mb-12 rounded-2xl border border-accent/20 bg-accent/5 p-6 md:p-8">
            <h2 className="font-brand text-xl font-bold text-accent mb-4">Key Takeaways</h2>
            <ul className="space-y-3">
              {post.content.keyTakeaways.map((point, i) => (
                <li key={i} className="flex items-start gap-3 text-white/80">
                  <span className="mt-1.5 h-2 w-2 rounded-full bg-accent shrink-0" />
                  {point}
                </li>
              ))}
            </ul>
          </section>

          {/* FAQ Section */}
          {post.faqs.length > 0 && (
            <section className="mb-12">
              <h2 className="font-brand text-2xl sm:text-3xl font-bold text-white mb-6">
                Frequently Asked Questions
              </h2>
              <div className="space-y-3">
                {post.faqs.map((faq, i) => (
                  <details
                    key={i}
                    className="group rounded-2xl border border-white/10 bg-black/40 overflow-hidden"
                  >
                    <summary className="flex cursor-pointer items-center gap-3 px-6 py-4 text-white hover:bg-white/5 transition-colors list-none [&::-webkit-details-marker]:hidden">
                      <HelpCircle className="h-5 w-5 text-accent shrink-0" />
                      <span className="text-sm font-semibold flex-1">{faq.question}</span>
                      <span className="text-white/40 transition-transform group-open:rotate-45 text-xl leading-none">+</span>
                    </summary>
                    <div className="px-6 pb-5 pt-1">
                      <p className="text-sm text-white/70 leading-relaxed pl-8">{faq.answer}</p>
                    </div>
                  </details>
                ))}
              </div>
            </section>
          )}

          {/* Related Centres */}
          {post.relatedCentres.length > 0 && (
            <section className="mb-12">
              <h2 className="font-brand text-xl font-bold text-white mb-4">Related Test Centres</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {post.relatedCentres.map(centre => (
                  <a
                    key={centre.slug}
                    href={`/test-centres/${centre.slug}/`}
                    className="rounded-xl border border-white/10 bg-black/40 p-4 hover:border-accent/30 transition-colors group"
                  >
                    <p className="font-semibold text-white group-hover:text-accent transition-colors text-sm">
                      {centre.name}
                    </p>
                    <p className="text-xs text-white/50 mt-1">{centre.reason}</p>
                  </a>
                ))}
              </div>
            </section>
          )}

          {/* Related Posts */}
          {relatedPosts.length > 0 && (
            <section className="mb-12">
              <h2 className="font-brand text-xl font-bold text-white mb-4">Related Articles</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {relatedPosts.map(related => (
                  <a
                    key={related.slug}
                    href={`/blog/${related.slug}/`}
                    className="rounded-xl border border-white/10 bg-black/40 overflow-hidden hover:border-accent/30 transition-colors group"
                  >
                    <img
                      src={`https://i.ytimg.com/vi/${related.youtubeVideoId}/hqdefault.jpg`}
                      alt={related.title}
                      className="w-full aspect-video object-cover"
                      loading="lazy"
                    />
                    <div className="p-4">
                      <span className="text-xs text-accent font-semibold uppercase tracking-wider">
                        {BLOG_CATEGORIES[related.category].label}
                      </span>
                      <p className="font-semibold text-white group-hover:text-accent transition-colors text-sm mt-1.5 line-clamp-2">
                        {related.title}
                      </p>
                      <p className="text-xs text-white/50 mt-2">{related.estimatedReadMinutes} min read</p>
                    </div>
                  </a>
                ))}
              </div>
            </section>
          )}
        </article>

        <AppCtaBlock />
      </main>

      <Footer />
    </div>
  )
}
```

**Step 3: Verify the page builds**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npx next build`

Expected: Build succeeds. Blog post pages appear in the output.

**Step 4: Verify page renders**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npx next dev`

Visit: `http://localhost:3000/blog/{first-slug}/` (use the slug of the first generated post)

Expected: Full blog post page with video embed, content sections, FAQs, related centres and posts.

**Step 5: Commit**

```bash
git add dte-next/app/blog/[slug]/page.tsx dte-next/components/blog/BlogSchemaMarkup.tsx
git commit -m "feat: add blog post page with schema markup, video embed, FAQ"
```

---

### Task 4.3: Create blog index page

**Files:**
- Create: `dte-next/app/blog/page.tsx`

**Step 1: Create the blog index**

```typescript
import { getAllPosts } from '@/lib/blog'
import { BLOG_CATEGORIES, type BlogCategory } from '@/lib/blog-types'
import type { Metadata } from 'next'
import { Navbar } from '@/components/Layout/Navbar'
import { Footer } from '@/components/Layout/Footer'
import { Clock, Tag, ChevronRight } from 'lucide-react'

export const metadata: Metadata = {
  title: 'Driving Test Tips & Guides',
  description: 'Expert driving test tips, manoeuvre guides, and test preparation advice from Josh Ramwell. 34,000+ YouTube subscribers trust his guidance.',
  alternates: { canonical: '/blog/' },
}

export default function BlogIndexPage() {
  const posts = getAllPosts()
  const categories = Object.entries(BLOG_CATEGORIES) as [BlogCategory, { label: string; description: string }][]

  // Group posts by category for the filter display
  const categoryCounts = categories.map(([key]) => ({
    key,
    count: posts.filter(p => p.category === key).length,
  }))

  return (
    <div className="min-h-screen bg-bg text-white">
      <Navbar />

      <main className="pt-32 pb-16">
        {/* Breadcrumb */}
        <div className="max-w-7xl mx-auto px-6 mb-8">
          <nav className="flex items-center gap-2 text-sm text-white/50">
            <a href="/" className="hover:text-accent transition-colors">Home</a>
            <ChevronRight className="h-3 w-3" />
            <span className="text-white/70">Blog</span>
          </nav>
        </div>

        {/* Header */}
        <div className="max-w-7xl mx-auto px-6 mb-12">
          <h1 className="font-brand text-4xl sm:text-5xl md:text-6xl font-black tracking-tight text-white">
            Driving Test Tips & Guides
          </h1>
          <p className="mt-4 text-lg text-white/60 max-w-2xl">
            Expert advice from Josh Ramwell — 34,000+ YouTube subscribers and 4M+ views helping learner drivers pass first time.
          </p>
        </div>

        {/* Category tags */}
        <div className="max-w-7xl mx-auto px-6 mb-10">
          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-accent/10 border border-accent/30 px-4 py-1.5 text-sm font-semibold text-accent">
              All ({posts.length})
            </span>
            {categoryCounts.filter(c => c.count > 0).map(({ key, count }) => (
              <span
                key={key}
                className="inline-flex items-center gap-1.5 rounded-full bg-white/5 border border-white/10 px-4 py-1.5 text-sm font-medium text-white/60"
              >
                {BLOG_CATEGORIES[key].label} ({count})
              </span>
            ))}
          </div>
        </div>

        {/* Post grid */}
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {posts.map(post => (
              <a
                key={post.slug}
                href={`/blog/${post.slug}/`}
                className="rounded-2xl border border-white/10 bg-black/40 overflow-hidden hover:border-accent/30 transition-all group"
              >
                <div className="relative aspect-video overflow-hidden">
                  <img
                    src={`https://i.ytimg.com/vi/${post.youtubeVideoId}/hqdefault.jpg`}
                    alt={post.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />
                  <div className="absolute top-3 left-3">
                    <span className="inline-flex items-center gap-1 rounded-full bg-black/70 backdrop-blur-sm border border-white/10 px-2.5 py-1 text-[10px] font-semibold text-accent uppercase tracking-wider">
                      <Tag className="h-2.5 w-2.5" />
                      {BLOG_CATEGORIES[post.category].label}
                    </span>
                  </div>
                </div>
                <div className="p-5">
                  <h2 className="font-brand text-lg font-bold text-white group-hover:text-accent transition-colors leading-snug line-clamp-2">
                    {post.title}
                  </h2>
                  <p className="mt-2 text-sm text-white/50 line-clamp-2">
                    {post.metaDescription}
                  </p>
                  <div className="mt-4 flex items-center gap-4 text-xs text-white/40">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {post.estimatedReadMinutes} min read
                    </span>
                    <span>{post.youtubeViews.toLocaleString()} video views</span>
                  </div>
                </div>
              </a>
            ))}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}
```

**Step 2: Verify build**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npx next build`

Expected: Build succeeds, `/blog/` page generated.

**Step 3: Commit**

```bash
git add dte-next/app/blog/page.tsx
git commit -m "feat: add blog index page with category tags and post grid"
```

---

## Phase 5: Navigation, Sitemap & Linking

### Task 5.1: Add Blog to navigation

**Files:**
- Modify: `dte-next/lib/constants.ts` (line 1-14)
- Modify: `dte-next/components/Layout/Footer.tsx` (lines 43-69)

**Step 1: Update NAV_ITEMS**

In `dte-next/lib/constants.ts`, change the `NAV_ITEMS` array to insert Blog after Test Centres:

```typescript
export const NAV_ITEMS: import('./types').NavItem[] = [
  {
    label: 'Test Centres',
    href: '/test-centres/',
    children: [
      { label: 'All Test Centres', href: '/test-centres/' },
      { label: 'Easiest Centres', href: '/test-centres/easiest/' },
      { label: 'Hardest Centres', href: '/test-centres/hardest/' },
      { label: 'Pass Rates', href: '/pass-rates/' },
    ],
  },
  { label: 'Blog', href: '/blog/' },
  { label: 'Our Apps', href: '/test-routes-app' },
  { label: 'About', href: '#about' },
]
```

**Step 2: Add Guides section to Footer**

In `dte-next/components/Layout/Footer.tsx`, add a "Guides" row between the "Test Centres" section and the "Legal Links" section (after line 69, before line 73):

```tsx
        {/* Guides */}
        <div className="border-t border-white/5 pt-8 mb-8">
          <h3 className="text-sm font-semibold text-white/60 mb-4 text-center">
            Guides
          </h3>
          <div className="flex flex-col md:flex-row items-center justify-center gap-4 md:gap-8 text-sm">
            <a
              href="/blog/"
              className="text-white/40 hover:text-accent transition-colors"
            >
              Driving Test Tips
            </a>
            <span className="hidden md:block text-white/20">&bull;</span>
            <a
              href="https://www.youtube.com/@JoshRamwell"
              target="_blank"
              rel="noopener noreferrer"
              className="text-white/40 hover:text-accent transition-colors"
            >
              YouTube Channel
            </a>
          </div>
        </div>
```

**Step 3: Verify**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npx next build`

Expected: Build succeeds.

**Step 4: Commit**

```bash
git add dte-next/lib/constants.ts dte-next/components/Layout/Footer.tsx
git commit -m "feat: add Blog to navbar and footer navigation"
```

---

### Task 5.2: Add blog posts to sitemap

**Files:**
- Modify: `dte-next/app/sitemap.ts`

**Step 1: Update sitemap to include blog posts**

Add the blog import and pages to `dte-next/app/sitemap.ts`. After the existing `centrePages` block (line 26-29), add:

```typescript
import { getAllPosts } from '@/lib/blog'
```

Add to the top imports, and add this block before the return statement:

```typescript
  const blogPages: MetadataRoute.Sitemap = [
    { url: `${baseUrl}/blog/`, lastModified: now, changeFrequency: 'weekly' as const, priority: 0.7 },
    ...getAllPosts().map(post => ({
      url: `${baseUrl}/blog/${post.slug}/`,
      lastModified: new Date(post.publishedDate),
      changeFrequency: 'monthly' as const,
      priority: 0.6,
    })),
  ]
```

Update the return to include blogPages:

```typescript
  return [...staticPages, ...regionPages, ...centrePages, ...blogPages]
```

**Step 2: Verify sitemap**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npx next build`

Check the generated sitemap includes `/blog/` URLs.

**Step 3: Commit**

```bash
git add dte-next/app/sitemap.ts
git commit -m "feat: add blog posts to XML sitemap"
```

---

### Task 5.3: Create centre-to-blog linking script

**Files:**
- Create: `dte-next/scripts/link-blog-to-centres.ts`

This script reads all blog posts, then updates `data/centre-content.json` to add a `relatedBlogPosts` field to each centre that has matching blog posts. The centre page template will then render these links.

**Step 1: Create the linking script**

```typescript
import * as fs from 'fs'
import * as path from 'path'
import type { BlogPost } from '../lib/blog-types'

const BLOG_DIR = path.join(__dirname, '..', 'data', 'blog')
const CONTENT_FILE = path.join(__dirname, '..', 'data', 'centre-content.json')

interface CentreContentWithBlog {
  [slug: string]: {
    relatedBlogPosts?: Array<{ slug: string; title: string }>
    [key: string]: unknown
  }
}

function main() {
  // Load all blog posts
  const blogFiles = fs.readdirSync(BLOG_DIR).filter(f => f.endsWith('.json'))
  const posts: BlogPost[] = blogFiles.map(f =>
    JSON.parse(fs.readFileSync(path.join(BLOG_DIR, f), 'utf-8'))
  )

  // Load centre content
  const content: CentreContentWithBlog = JSON.parse(
    fs.readFileSync(CONTENT_FILE, 'utf-8')
  )

  // Build a map: centreSlug -> blog posts that link to it
  const centreToBlogs: Record<string, Array<{ slug: string; title: string }>> = {}

  for (const post of posts) {
    for (const centre of post.relatedCentres) {
      if (!centreToBlogs[centre.slug]) {
        centreToBlogs[centre.slug] = []
      }
      centreToBlogs[centre.slug].push({ slug: post.slug, title: post.title })
    }
  }

  // Update centre content with blog links
  let updated = 0
  for (const [centreSlug, blogPosts] of Object.entries(centreToBlogs)) {
    if (content[centreSlug]) {
      content[centreSlug].relatedBlogPosts = blogPosts.slice(0, 3) // Max 3 per centre
      updated++
    }
  }

  fs.writeFileSync(CONTENT_FILE, JSON.stringify(content, null, 2))
  console.log(`Updated ${updated} centres with blog post links`)
}

main()
```

**Step 2: Run the linker**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npx tsx scripts/link-blog-to-centres.ts`

Expected: Console shows number of centres updated.

**Step 3: Commit**

```bash
git add dte-next/scripts/link-blog-to-centres.ts dte-next/data/centre-content.json
git commit -m "feat: add bidirectional blog-to-centre linking"
```

---

### Task 5.4: Add npm script for full pipeline

**Files:**
- Modify: `dte-next/package.json`

**Step 1: Add the blog:generate script**

Add to the `"scripts"` section in `dte-next/package.json`:

```json
"blog:scrape": "tsx scripts/scrape-youtube.ts",
"blog:transcripts": "tsx scripts/fetch-transcripts.ts",
"blog:categorise": "tsx scripts/categorise-videos.ts",
"blog:generate": "tsx scripts/generate-blog-posts.ts",
"blog:link": "tsx scripts/link-blog-to-centres.ts",
"blog:all": "npm run blog:scrape && npm run blog:transcripts && npm run blog:categorise && npm run blog:generate && npm run blog:link"
```

**Step 2: Verify**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npm run blog:all`

Expected: Full pipeline runs end-to-end.

**Step 3: Commit**

```bash
git add dte-next/package.json
git commit -m "feat: add blog:all pipeline npm script"
```

---

## Phase 6: Build & Verify

### Task 6.1: Full build and verification

**Step 1: Run full build**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npx next build`

Expected: Build succeeds. Blog pages appear alongside centre pages.

**Step 2: Count blog pages in output**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && ls out/blog/ | wc -l`

Expected: Number matches generated blog posts + 1 (index page).

**Step 3: Spot-check 3 pages**

Run: `cd "c:/Users/Nathaniel/Documents/DTE SITE/dte-next" && npx serve out`

Verify on 3 different blog post pages:
- [ ] Title and H1 render correctly
- [ ] YouTube video embeds and plays
- [ ] Content sections have actual substance (not placeholder)
- [ ] Internal links to centre pages are clickable
- [ ] FAQ section expands/collapses
- [ ] Related centres section shows links
- [ ] Related posts section shows other blog posts
- [ ] Schema markup present in page source (view source, search for "ld+json")
- [ ] Blog index page shows all posts in grid
- [ ] Navbar shows "Blog" link
- [ ] Footer shows "Guides" section

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: verify full build — blog pipeline complete"
```

---

## Summary

| Phase | Tasks | What it produces |
|-------|-------|-----------------|
| 1. Dependencies & Types | 3 tasks | npm packages, TypeScript types, env setup |
| 2. YouTube Scraping | 2 tasks | `data/youtube/videos.json`, transcript files |
| 3. Categorise & Generate | 2 tasks | `data/youtube/categorised.json`, `data/blog/*.json` |
| 4. Next.js Pages | 3 tasks | `/blog/` index, `/blog/[slug]/` post pages |
| 5. Navigation & Linking | 4 tasks | Navbar/footer updates, sitemap, centre-blog links |
| 6. Build & Verify | 1 task | Full verification |

**Total: 15 tasks, one-command pipeline (`npm run blog:all`), 20+ blog posts.**
