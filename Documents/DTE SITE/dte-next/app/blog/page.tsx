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
