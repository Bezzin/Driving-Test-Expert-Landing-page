'use client'

import React, { useState, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import { Menu, X } from 'lucide-react'
import {
  NAV_ITEMS,
  ASSETS,
  HOME_PATH,
  APP_PATH,
  LEGACY_APP_PATH,
} from '@/lib/constants'
import { AppStoreBadge, PlayStoreBadge } from '@/components/UI/StoreBadges'

export const Navbar: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const pathname = usePathname()
  const normalizedPath = pathname.replace(/\/$/, '')
  const isAppPage =
    normalizedPath === APP_PATH.replace(/\/$/, '') ||
    normalizedPath === LEGACY_APP_PATH.replace(/\/$/, '')
  const navItems = isAppPage
    ? [
        { label: 'Our Apps', href: '#download' },
        { label: 'About', href: '#about' },
      ]
    : NAV_ITEMS
  const primaryCta = isAppPage
    ? { label: 'Get Test Routes', href: '#download' }
    : { label: 'Get Test Routes', href: APP_PATH }

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <>
      <header
        className={`fixed z-50 top-0 left-0 right-0 transition-all duration-300 ${scrolled ? 'bg-black/80 backdrop-blur-md border-b border-white/5 py-3' : 'bg-transparent py-5'}`}
      >
        <div className="mx-auto max-w-7xl px-6 flex items-center justify-between">
          <a
            href={HOME_PATH}
            className="relative z-50 block w-56 md:w-72 transition hover:opacity-90"
          >
            <img
              src={ASSETS.logo}
              alt="Driving Test Expert"
              className="w-full h-auto object-contain"
            />
          </a>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-white/70">
            {navItems.map((item) => (
              <a
                key={item.label}
                href={item.href}
                className="transition hover:text-accent"
              >
                {item.label}
              </a>
            ))}
            <div className="flex items-center gap-2">
              <AppStoreBadge className="h-8" />
              <PlayStoreBadge className="h-8" />
            </div>
            <a
              href={primaryCta.href}
              className="inline-flex items-center gap-2 rounded-full px-5 py-2.5 font-bold transition bg-accent text-black hover:bg-white hover:text-black shadow-[0_0_20px_rgba(252,163,17,0.4)]"
            >
              {primaryCta.label}
            </a>
          </nav>

          {/* Mobile Menu Toggle */}
          <button
            onClick={() => setIsOpen(true)}
            className="md:hidden z-50 p-2 text-white hover:text-accent transition"
          >
            <Menu size={28} />
          </button>
        </div>

        {/* Mobile badge row -- visible immediately, no menu needed */}
        <div className="md:hidden flex items-center justify-center gap-3 pb-2 px-6">
          <AppStoreBadge className="h-9" />
          <PlayStoreBadge className="h-9" />
        </div>
      </header>

      {/* Mobile Overlay */}
      <div
        className={`fixed inset-0 z-[60] bg-black/95 backdrop-blur-xl flex flex-col items-center justify-center transition-opacity duration-300 ${isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
      >
        <button
          onClick={() => setIsOpen(false)}
          className="absolute top-6 right-6 p-4 text-white/50 hover:text-accent"
        >
          <X size={32} />
        </button>
        <nav className="flex flex-col gap-8 text-center text-3xl font-bold tracking-tight font-brand">
          {navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              onClick={() => setIsOpen(false)}
              className="hover:text-accent transition text-white"
            >
              {item.label}
            </a>
          ))}
          <div className="flex items-center justify-center gap-4">
            <AppStoreBadge className="h-10" />
            <PlayStoreBadge className="h-10" />
          </div>
          <a
            href={primaryCta.href}
            onClick={() => setIsOpen(false)}
            className="text-accent hover:text-white transition"
          >
            {primaryCta.label}
          </a>
        </nav>
      </div>
    </>
  )
}
