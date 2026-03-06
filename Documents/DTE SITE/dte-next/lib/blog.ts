import * as fs from 'fs'
import * as path from 'path'
import type { BlogPost, BlogCategory } from './blog-types'

const BLOG_DIR = path.join(process.cwd(), 'data', 'blog')

let _allPosts: BlogPost[] | null = null

export function getAllPosts(): BlogPost[] {
  if (_allPosts) return _allPosts

  if (!fs.existsSync(BLOG_DIR)) return []

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
