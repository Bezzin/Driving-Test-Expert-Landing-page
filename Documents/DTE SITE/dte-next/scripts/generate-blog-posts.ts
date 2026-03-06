import { GoogleGenAI } from '@google/genai'
import * as fs from 'fs'
import * as path from 'path'
import * as dotenv from 'dotenv'
import type { YouTubeVideo, BlogPost, BlogCategory } from '../lib/blog-types'
import type { DvsaCentre } from '../lib/dvsa-types'

dotenv.config({ path: path.join(__dirname, '..', '.env.local') })

const VIDEOS_FILE = path.join(__dirname, '..', 'data', 'youtube', 'videos.json')
const CENTRES_FILE = path.join(__dirname, '..', 'data', 'dvsa', 'centres.json')
const CONTENT_FILE = path.join(__dirname, '..', 'data', 'centre-content.json')
const BLOG_DIR = path.join(__dirname, '..', 'data', 'blog')

const MAX_POSTS = parseInt(process.env.MAX_BLOG_POSTS ?? '50', 10)

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY! })

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function slugify(title: string): string {
  return title
    .toLowerCase()
    .replace(/['']/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .substring(0, 60)
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

function matchCentresToTopic(
  title: string,
  tags: string[],
  centres: DvsaCentre[],
  contentMap: Record<string, { keyChallenges?: string[]; roadTypes?: string[] }>
): Array<{ slug: string; name: string; reason: string }> {
  const matches: Array<{ slug: string; name: string; reason: string; score: number }> = []
  const titleLower = title.toLowerCase()

  for (const centre of centres) {
    const content = contentMap[centre.slug]
    if (!content) continue

    const challenges = (content.keyChallenges ?? []).join(' ').toLowerCase()
    const roadTypes = (content.roadTypes ?? []).join(' ').toLowerCase()
    const combined = challenges + ' ' + roadTypes

    let score = 0
    let reason = ''

    // Check if video title mentions the centre area
    const nameLower = centre.name.toLowerCase()
    if (titleLower.includes(nameLower.split(' ')[0])) {
      score += 5
      reason = `Video features ${centre.name} area`
    }

    for (const tag of tags) {
      const normalised = tag.toLowerCase().replace(/-/g, ' ')
      if (combined.includes(normalised)) {
        score++
        reason = reason || `Known for ${normalised} challenges`
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

async function generatePost(
  video: YouTubeVideo,
  centres: DvsaCentre[],
  contentMap: Record<string, { keyChallenges?: string[]; roadTypes?: string[] }>
): Promise<BlogPost | null> {
  const nationalAvg = centres.reduce((s, c) => s + c.passRateOverall, 0) / centres.length
  const totalCentres = centres.length

  const prompt = `You are writing a blog post for Test Routes Expert (testroutesexpert.co.uk), a UK driving test preparation website.

TASK: Write a structured, SEO-optimised blog post based on this YouTube video topic.

VIDEO TITLE: ${video.title}
VIDEO BY: Josh Ramwell (driving instructor, 34,000+ YouTube subscribers, 4M+ views)
VIDEO URL: ${video.url}

DVSA DATA TO REFERENCE:
- National average pass rate: ${nationalAvg.toFixed(1)}%
- Total UK test centres: ${totalCentres}
- Data period: April 2024 - March 2025

REQUIREMENTS:
1. Title: SEO-optimised, 50-65 characters. Rephrase the video title into a search-friendly blog title.
2. Meta description: 150-155 characters, includes target keyword naturally.
3. Category: Pick ONE from: "manoeuvres", "junctions", "road-types", "test-prep", "common-faults", "general-driving"
4. Tags: 3-6 specific topic tags (e.g. "roundabouts", "bay-parking", "mirror-checks")
5. SEO keywords: 5-8 related keywords for this post.
6. Slug: URL-friendly slug (e.g. "roundabouts-driving-test-guide")
7. Introduction: 80-120 words in HTML. Hook the reader, preview the content.
8. Main content: 3-5 sections with H2 headings. Total 800-1200 words across all sections.
   - Write practical, actionable driving advice
   - Use Josh's practical, encouraging instructor tone
   - Include at least one HTML link: <a href="/test-centres/">our test centres hub</a>
   - Reference DVSA data naturally where relevant
   - Write in second person ("you") directed at learner drivers
   - Use <p> tags for paragraphs, <ul>/<li> for lists, <strong> for emphasis
9. Key takeaways: 4-6 bullet points summarising main advice.
10. FAQs: 3-5 questions targeting "People Also Ask" queries for this topic.
    - Each answer: 40-80 words.

OUTPUT FORMAT: Return ONLY a valid JSON object with this exact structure (no markdown fences, no explanation):
{
  "title": "string",
  "metaDescription": "string",
  "category": "string",
  "tags": ["string"],
  "seoKeywords": ["string"],
  "slug": "string",
  "content": {
    "introduction": "string (HTML)",
    "sections": [{"heading": "string", "body": "string (HTML)"}],
    "keyTakeaways": ["string"]
  },
  "faqs": [{"question": "string", "answer": "string"}]
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

    const slug = parsed.slug || slugify(video.title)
    const tags = parsed.tags ?? []

    const matchingCentres = matchCentresToTopic(video.title, tags, centres, contentMap)

    const post: BlogPost = {
      slug,
      title: parsed.title,
      metaDescription: parsed.metaDescription,
      publishedDate: new Date().toISOString().split('T')[0],
      category: parsed.category as BlogCategory,
      tags,
      youtubeVideoId: video.videoId,
      youtubeTitle: video.title,
      youtubeViews: video.views,
      estimatedReadMinutes: 0,
      content: parsed.content,
      faqs: parsed.faqs ?? [],
      relatedCentres: matchingCentres,
      relatedPostSlugs: [],
      seoKeywords: parsed.seoKeywords ?? [],
    }

    post.estimatedReadMinutes = Math.max(3, Math.round(getWordCount(post) / 250))

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

  const videos: YouTubeVideo[] = JSON.parse(fs.readFileSync(VIDEOS_FILE, 'utf-8'))
  const centres: DvsaCentre[] = JSON.parse(fs.readFileSync(CENTRES_FILE, 'utf-8'))
  const contentMap: Record<string, { keyChallenges?: string[]; roadTypes?: string[] }> =
    JSON.parse(fs.readFileSync(CONTENT_FILE, 'utf-8'))

  fs.mkdirSync(BLOG_DIR, { recursive: true })

  // Filter out non-driving content (e.g. travel/car hire videos)
  const drivingVideos = videos.filter(v => {
    const titleLower = v.title.toLowerCase()
    const isDriving = titleLower.includes('driv') || titleLower.includes('test') ||
      titleLower.includes('examiner') || titleLower.includes('learner') ||
      titleLower.includes('roundabout') || titleLower.includes('junction') ||
      titleLower.includes('manoeuvre') || titleLower.includes('parking') ||
      titleLower.includes('lane') || titleLower.includes('traffic') ||
      titleLower.includes('car') || titleLower.includes('road') ||
      titleLower.includes('fail') || titleLower.includes('pass')
    return isDriving
  })

  const toGenerate = drivingVideos.slice(0, MAX_POSTS)
  console.log(`Generating ${toGenerate.length} blog posts (of ${videos.length} total videos, ${drivingVideos.length} driving-related)...`)

  const allPosts: BlogPost[] = []

  // Load any already-generated posts
  const existingFiles = fs.existsSync(BLOG_DIR)
    ? fs.readdirSync(BLOG_DIR).filter(f => f.endsWith('.json'))
    : []
  const existingSlugs = new Set(existingFiles.map(f => f.replace('.json', '')))

  for (let i = 0; i < toGenerate.length; i++) {
    const video = toGenerate[i]
    const expectedSlug = slugify(video.title)

    // Check if already generated (by videoId in filename or slug match)
    const existingFile = existingFiles.find(f => {
      const post: BlogPost = JSON.parse(fs.readFileSync(path.join(BLOG_DIR, f), 'utf-8'))
      return post.youtubeVideoId === video.videoId
    })

    if (existingFile) {
      console.log(`  Already exists: ${existingFile}`)
      allPosts.push(JSON.parse(fs.readFileSync(path.join(BLOG_DIR, existingFile), 'utf-8')))
      continue
    }

    console.log(`[${i + 1}/${toGenerate.length}] Generating: ${video.title}...`)
    const post = await generatePost(video, centres, contentMap)

    if (post) {
      // Ensure unique slug
      let finalSlug = post.slug
      let counter = 2
      while (existingSlugs.has(finalSlug)) {
        finalSlug = `${post.slug}-${counter}`
        counter++
      }
      post.slug = finalSlug
      existingSlugs.add(finalSlug)

      const wordCount = getWordCount(post)
      console.log(`  OK: ${finalSlug} (${wordCount} words, ${post.faqs.length} FAQs, ${post.relatedCentres.length} centres)`)
      fs.writeFileSync(path.join(BLOG_DIR, `${finalSlug}.json`), JSON.stringify(post, null, 2))
      allPosts.push(post)
    }

    // Rate limit: 2 seconds between Gemini calls
    await sleep(2000)
  }

  // Post-processing: fill in relatedPostSlugs by matching shared tags
  console.log('\nLinking related posts...')
  for (const post of allPosts) {
    const related = allPosts
      .filter(other => other.slug !== post.slug)
      .map(other => {
        const sharedTags = post.tags.filter(t => other.tags.includes(t))
        const sameCategory = post.category === other.category ? 1 : 0
        return { slug: other.slug, score: sharedTags.length + sameCategory }
      })
      .filter(r => r.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 3)
      .map(r => r.slug)

    post.relatedPostSlugs = related
    const outFile = path.join(BLOG_DIR, `${post.slug}.json`)
    fs.writeFileSync(outFile, JSON.stringify(post, null, 2))
  }

  console.log(`\nDone. Generated ${allPosts.length} blog posts in ${BLOG_DIR}`)

  // Summary by category
  const byCat: Record<string, number> = {}
  for (const p of allPosts) {
    byCat[p.category] = (byCat[p.category] || 0) + 1
  }
  console.log('\nBy category:')
  Object.entries(byCat).sort((a, b) => b[1] - a[1]).forEach(([cat, count]) => {
    console.log(`  ${cat}: ${count}`)
  })
}

main().catch(console.error)
