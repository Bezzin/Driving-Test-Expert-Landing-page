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
