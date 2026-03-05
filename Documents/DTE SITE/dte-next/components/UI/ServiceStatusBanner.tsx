'use client'

import { useState, useEffect } from 'react'
import { AlertTriangle, X } from 'lucide-react'

interface StatusData {
  active: boolean
  message: string
  type: 'maintenance' | 'outage' | 'info'
}

const TYPE_STYLES: Record<StatusData['type'], { bg: string; border: string; icon: string }> = {
  maintenance: {
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    icon: 'text-amber-400',
  },
  outage: {
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    icon: 'text-red-400',
  },
  info: {
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    icon: 'text-blue-400',
  },
}

export const ServiceStatusBanner: React.FC = () => {
  const [status, setStatus] = useState<StatusData | null>(null)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    fetch('/status.json?t=' + Date.now())
      .then(res => res.json())
      .then((data: StatusData) => {
        if (data.active) {
          setStatus(data)
        }
      })
      .catch(() => {
        // Silently fail — no banner if fetch fails
      })
  }, [])

  if (!status || dismissed) return null

  const styles = TYPE_STYLES[status.type] || TYPE_STYLES.maintenance

  return (
    <div className={`fixed top-0 left-0 right-0 z-[60] ${styles.bg} ${styles.border} border-b backdrop-blur-md`}>
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <AlertTriangle className={`w-5 h-5 flex-shrink-0 ${styles.icon}`} />
          <p className="text-sm text-white/90 font-medium truncate">
            {status.message}
          </p>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-white/40 hover:text-white/80 transition flex-shrink-0"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
