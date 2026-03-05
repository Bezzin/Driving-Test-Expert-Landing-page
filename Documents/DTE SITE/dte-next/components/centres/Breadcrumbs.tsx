import Link from 'next/link'
import { ChevronRight } from 'lucide-react'

interface BreadcrumbsProps {
  centreName: string
  regionName: string
  regionSlug: string
}

export function Breadcrumbs({ centreName, regionName, regionSlug }: BreadcrumbsProps) {
  const items = [
    { label: 'Home', href: '/' },
    { label: 'Test Centres', href: '/test-centres/' },
    { label: regionName, href: `/test-centres/regions/${regionSlug}/` },
    { label: centreName },
  ]

  return (
    <nav aria-label="Breadcrumb" className="py-4 px-6 max-w-7xl mx-auto">
      <ol className="flex flex-wrap items-center gap-1 text-sm text-white/50">
        {items.map((item, i) => {
          const isLast = i === items.length - 1
          return (
            <li key={item.label} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="h-3 w-3 shrink-0" />}
              {isLast || !item.href ? (
                <span className="text-white/80">{item.label}</span>
              ) : (
                <Link
                  href={item.href}
                  className="transition-colors hover:text-accent"
                >
                  {item.label}
                </Link>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
