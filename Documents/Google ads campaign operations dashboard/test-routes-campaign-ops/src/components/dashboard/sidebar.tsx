'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface NavItem {
  readonly href: string
  readonly label: string
  readonly icon: string
}

const NAV_ITEMS: readonly NavItem[] = [
  { href: '/dashboard', label: 'Dashboard', icon: '\u{1F4CA}' },
  { href: '/dashboard/automation', label: 'Automation', icon: '\u26A1' },
  { href: '/dashboard/bulk', label: 'Bulk Actions', icon: '\u{1F4DA}' },
  { href: '/dashboard/settings', label: 'Settings', icon: '\u2699\uFE0F' },
] as const

interface SidebarProps {
  readonly dryRun: boolean
}

export function Sidebar({ dryRun }: SidebarProps) {
  const pathname = usePathname()

  const isActive = (href: string): boolean => {
    if (href === '/dashboard') {
      return pathname === '/dashboard'
    }
    return pathname.startsWith(href)
  }

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-60 flex-col bg-slate-900 text-slate-100">
      <div className="flex flex-col gap-1 border-b border-slate-700 px-5 py-5">
        <h1 className="text-lg font-bold tracking-tight text-white">
          Campaign Ops
        </h1>
        <span className="text-xs text-slate-400">Test Routes Expert</span>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
              isActive(item.href)
                ? 'bg-slate-700/70 text-white'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            )}
          >
            <span className="text-base">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>

      {dryRun && (
        <div className="border-t border-slate-700 px-5 py-4">
          <Badge variant="secondary" className="bg-amber-500/20 text-amber-300">
            Dry Run Mode
          </Badge>
        </div>
      )}
    </aside>
  )
}
