"use client"

import { usePathname } from "next/navigation"

const ROUTE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/agents": "Agent Library",
  "/builder": "Builder",
  "/runs": "Runs",
  "/settings": "Settings",
}

function getPageTitle(pathname: string): string {
  if (ROUTE_TITLES[pathname]) return ROUTE_TITLES[pathname]

  const segments = pathname.split("/").filter(Boolean)
  if (segments.length > 0) {
    const firstSegment = segments[0]
    return ROUTE_TITLES[`/${firstSegment}`] || "Airees"
  }

  return "Airees"
}

export function Header() {
  const pathname = usePathname()
  const title = getPageTitle(pathname)

  return (
    <header className="flex h-16 items-center border-b border-gray-800 bg-gray-900/50 px-6 backdrop-blur-sm">
      <div className="flex flex-1 items-center gap-4 pl-10 lg:pl-0">
        <h1 className="text-lg font-semibold text-gray-100">{title}</h1>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-sm font-medium text-white">
          A
        </div>
      </div>
    </header>
  )
}
