# YouTube-to-Blog Pipeline Design

> **Goal:** Build an automated pipeline that transforms Josh Ramwell's YouTube video backlog into SEO-optimised blog posts on the dte-next site, creating topical authority and internal linking fuel for the 300+ test centre pages.

> **Approach:** Full automated pipeline — scrape channel, extract transcripts, categorise, generate content via Gemini, publish as SSG pages in Next.js.

---

## Why blog posts matter for ranking

1. **Topical authority** — Centre pages cover transactional intent ("[centre] driving test routes"). Blog posts cover informational intent ("how to deal with roundabouts on a driving test"). Together they signal comprehensive topic coverage to Google.
2. **Internal linking fuel** — Each blog post creates natural opportunities to link to centre pages, passing link equity to money pages.
3. **Competitor parity** — testroutes.co.uk already has 10+ blog posts. Not having them is a gap they can exploit.

## Content source: YouTube transcripts

Josh's channel (@JoshRamwell) has 34,000+ subscribers and 4M+ views of general driving and motoring tips content. Using video transcripts as the source material means:
- Content is genuinely unique (not generic AI waffle)
- Josh's practical, encouraging voice is preserved
- Each blog post embeds the original video (boosts time-on-page, sends signals to YouTube)
- Google does NOT penalise AI-generated content that is genuinely useful and data-enriched

---

## Pipeline Architecture

```
YouTube Channel (@JoshRamwell)
        |
        v
+---------------------+
| 1. Scrape Channel   |  scripts/scrape-youtube.ts
|    - Video titles    |  Output: data/youtube/videos.json
|    - URLs, views     |
|    - Durations       |
+----------+----------+
           v
+---------------------+
| 2. Extract           |  scripts/fetch-transcripts.ts
|    Transcripts       |  Uses: youtube-transcript (npm)
|    - Auto-captions   |  Output: data/youtube/transcripts/{video-id}.json
+----------+----------+
           v
+---------------------+
| 3. Categorise &     |  scripts/categorise-videos.ts
|    Prioritise       |  Tags: roundabouts, parking, motorway, etc.
|    - Topic tagging   |  Matches to centre pages where relevant
|    - SEO keywords    |  Output: data/youtube/categorised.json
|    - Sort by views   |
+----------+----------+
           v
+---------------------+
| 4. Generate Posts   |  scripts/generate-blog-posts.ts
|    via Gemini        |  Input: transcript + DVSA data + keywords
|    - Structured H1/  |  Output: data/blog/{slug}.json
|      H2/FAQ          |
|    - Internal links  |
|    - Centre links    |
+----------+----------+
           v
+---------------------+
| 5. Next.js SSG      |  app/blog/[slug]/page.tsx
|    Build-time render |  generateStaticParams from data/blog/*.json
|    - Blog index      |  app/blog/page.tsx
|    - Post pages      |  Sitemap integration
|    - Schema markup   |
+---------------------+
```

All data lives in `data/` as JSON — same pattern as DVSA centres. Scripts are standalone TypeScript run with `tsx`. Gemini is called during generation (step 4), not during Next.js build.

---

## Blog Post Structure

Each generated post follows this template:

### 1. Hero / Header
- Breadcrumb: `Home > Blog > {Post Title}`
- H1: SEO-optimised title derived from video topic
- Published date, estimated read time
- Embedded YouTube video (the original source)

### 2. Introduction (~100 words)
- Hook with the problem/question
- Preview what they'll learn
- Natural mention of key SEO terms

### 3. Main Content (~800-1200 words)
- 3-5 H2 sections restructured from transcript into logical flow
- Practical advice in Josh's voice
- DVSA data injected where relevant
- 3-5 contextual internal links to centre pages

### 4. Key Takeaways
- 4-6 bulleted summary points
- Scannable for skimmers

### 5. FAQ Section (3-5 questions)
- FAQPage schema markup
- Targets "People Also Ask" queries
- 40-80 word answers, data-enriched

### 6. Related Content
- 2-3 related blog posts (by topic tag)
- 3-5 related test centres (matched by topic to centre challenges)

### 7. App CTA Block
- Reuses existing AppCtaBlock component
- iOS + Android download buttons

### Target word count
1,200-1,800 words per post.

### Meta tags per post
```html
<title>{Post Title} | Driving Test Expert Blog</title>
<meta name="description" content="{155 char unique summary}">
<link rel="canonical" href="/blog/{slug}/">
<meta property="og:type" content="article">
```

### Schema markup per post
- **Article** (author: Josh Ramwell, publisher: Driving Test Expert)
- **BreadcrumbList**
- **FAQPage**
- **VideoObject** (for the embedded YouTube video)

---

## Topic Categorisation

| Category | Example topics | Primary keyword target | Links to |
|----------|---------------|----------------------|----------|
| Manoeuvres | Bay parking, parallel park, emergency stop | "driving test manoeuvres 2026" | Centres where manoeuvre is common |
| Junctions | Roundabouts, crossroads, T-junctions | "roundabouts driving test" | Centres with difficult roundabouts |
| Road types | Dual carriageway, motorway, country lanes | "dual carriageway driving test" | Centres on A-roads/motorways |
| Test prep | Show me tell me, what to expect, nerves | "show me tell me questions 2026" | Hub page, app download |
| Common faults | Mirror checks, observation, speed | "driving test common faults" | Pass rates page, hardest centres |
| General driving | Night driving, motorway tips, weather | "driving in rain tips" | Relevant centres, app download |

### Priority queue
1. Highest view count first (proven audience interest)
2. Topics matching "People Also Ask" queries (direct SEO opportunity)
3. Topics linking to the most centre pages (maximises internal linking value)
4. Evergreen over dated content

---

## Internal Linking Strategy

### Blog-to-centre links
Each blog post links to 3-5 centre pages selected by matching post topic to centre `keyChallenges` data. E.g. a roundabouts post links to centres whose challenges mention roundabouts.

### Centre-to-blog links (bidirectional)
After blog posts exist, `scripts/link-blog-to-centres.ts` updates the related content section on centre pages to link matching blog posts by topic tag overlap.

### Blog-to-blog links
Each post links to 1-2 related posts matched by shared topic tags.

### Hub links
Every post links to `/test-centres/` at least once.

```
Blog: "Roundabouts Guide"
  +-- links to --> /test-centres/stafford/
  +-- links to --> /test-centres/wolverhampton/
  +-- links to --> /test-centres/coventry/

Centre: /test-centres/stafford/
  +-- "Related articles" links back to --> /blog/roundabouts-guide/
```

---

## Technical Implementation

### File structure (within dte-next)

```
dte-next/
+-- scripts/
|   +-- scrape-youtube.ts
|   +-- fetch-transcripts.ts
|   +-- categorise-videos.ts
|   +-- generate-blog-posts.ts
|   +-- link-blog-to-centres.ts
+-- data/
|   +-- youtube/
|   |   +-- videos.json
|   |   +-- categorised.json
|   |   +-- transcripts/
|   |       +-- {video-id}.json
|   +-- blog/
|       +-- {slug}.json
+-- app/
|   +-- blog/
|       +-- page.tsx
|       +-- [slug]/
|           +-- page.tsx
+-- components/
|   +-- blog/
|       +-- BlogHero.tsx
|       +-- BlogContent.tsx
|       +-- BlogFaq.tsx
|       +-- BlogRelated.tsx
|       +-- BlogSchemaMarkup.tsx
|       +-- BlogIndex.tsx
+-- lib/
    +-- blog.ts
    +-- youtube.ts
```

### Blog post JSON schema

```typescript
interface BlogPost {
  slug: string
  title: string
  metaDescription: string
  publishedDate: string
  category: string
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
```

### Dependencies

| Package | Purpose | Already in project? |
|---------|---------|-------------------|
| youtube-transcript | Extract auto-captions | No |
| @google/genai | Gemini API for content generation | No (in DTESite, add to dte-next) |
| cheerio | Scrape YouTube channel page | No |
| tsx | Run TypeScript scripts | Yes |

### Gemini prompt strategy

Each video is processed with a structured prompt containing:
- The full transcript text
- Video title and metadata
- Target SEO keyword
- Related centre data (names, slugs, challenges)
- Relevant DVSA national statistics
- Strict rules: write in second person, maintain Josh's tone, include internal links, reference only provided data, output as JSON matching BlogPost schema

### One-command pipeline

```bash
npm run blog:generate
```

Chains: scrape-youtube -> fetch-transcripts -> categorise -> generate-blog-posts -> link-blog-to-centres

Then `npm run build` picks up new JSON and generates pages.

---

## Blog Index & Navigation

### Blog index (/blog/)
- H1: "Driving Test Tips & Guides"
- Category filter tabs: All | Manoeuvres | Junctions | Road Types | Test Prep | Common Faults | General
- Posts as cards in grid (2 cols desktop, 1 col mobile)
- Each card: YouTube thumbnail, title, category tag, read time, excerpt
- Default sort: most recent first

### Navigation update
Navbar becomes: **Test Centres** | **Blog** | **Our Apps** | **About**

Blog is a top-level nav item linking to `/blog/`.

### Footer update
Add "Guides" column: Driving Test Tips, Common Faults Guide, Manoeuvres Guide, Show Me Tell Me Questions — linking to highest-value blog posts.

### Sitemap integration
Blog posts added to existing `app/sitemap.ts` with priority 0.6 (lower than centre pages at 0.8).

---

## Success criteria

- Pipeline runs end-to-end with a single command
- 20+ blog posts generated from top YouTube videos
- Each post: 1,200-1,800 words, unique content, 3-5 internal centre links
- Blog index and post pages pass Lighthouse SEO >95
- Bidirectional linking: centre pages link to relevant blog posts
- Schema markup validates for Article, FAQPage, VideoObject, BreadcrumbList
