"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useState } from "react"
import {
  Home,
  Bot,
  Workflow,
  Play,
  Settings,
  Menu,
  X,
  Zap,
} from "lucide-react"

interface NavItem {
  readonly label: string
  readonly href: string
  readonly icon: React.ReactNode
}

const NAV_ITEMS: readonly NavItem[] = [
  { label: "Dashboard", href: "/", icon: <Home size={20} /> },
  { label: "Agents", href: "/agents", icon: <Bot size={20} /> },
  { label: "Builder", href: "/builder", icon: <Workflow size={20} /> },
  { label: "Runs", href: "/runs", icon: <Play size={20} /> },
  { label: "Settings", href: "/settings", icon: <Settings size={20} /> },
] as const

function NavLink({
  item,
  isActive,
  onClick,
}: {
  readonly item: NavItem
  readonly isActive: boolean
  readonly onClick?: () => void
}) {
  return (
    <Link
      href={item.href}
      onClick={onClick}
      className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
        isActive
          ? "bg-indigo-600/20 text-indigo-400"
          : "text-gray-400 hover:bg-gray-700/50 hover:text-gray-200"
      }`}
    >
      {item.icon}
      <span>{item.label}</span>
    </Link>
  )
}

export function Sidebar() {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/"
    return pathname.startsWith(href)
  }

  const closeMobile = () => setMobileOpen(false)

  return (
    <>
      {/* Mobile toggle button */}
      <button
        type="button"
        onClick={() => setMobileOpen(true)}
        className="fixed left-4 top-4 z-50 rounded-lg bg-gray-800 p-2 text-gray-400 hover:text-gray-200 lg:hidden"
        aria-label="Open sidebar"
      >
        <Menu size={20} />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={closeMobile}
          onKeyDown={(e) => {
            if (e.key === "Escape") closeMobile()
          }}
          role="button"
          tabIndex={0}
          aria-label="Close sidebar overlay"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-gray-800 transition-transform duration-200 lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex h-16 items-center justify-between border-b border-gray-700 px-4">
          <div className="flex items-center gap-2">
            <Zap size={24} className="text-indigo-400" />
            <span className="text-lg font-bold tracking-tight text-gray-100">
              Airees
            </span>
          </div>
          <button
            type="button"
            onClick={closeMobile}
            className="rounded-lg p-1.5 text-gray-400 hover:text-gray-200 lg:hidden"
            aria-label="Close sidebar"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              isActive={isActive(item.href)}
              onClick={closeMobile}
            />
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-gray-700 px-4 py-3">
          <p className="text-xs text-gray-500">Airees v0.1.0</p>
        </div>
      </aside>
    </>
  )
}
