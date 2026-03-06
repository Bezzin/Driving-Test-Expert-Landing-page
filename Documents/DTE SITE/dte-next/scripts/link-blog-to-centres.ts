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
