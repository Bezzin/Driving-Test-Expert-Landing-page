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
