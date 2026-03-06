'use client'

import { useEffect, useState, useCallback } from 'react'
import { KpiCards } from '@/components/dashboard/kpi-cards'
import { ApprovalBanner } from '@/components/dashboard/approval-banner'
import { CentresTable, type Centre } from '@/components/dashboard/centres-table'

interface KpiData {
  readonly spendToday: number
  readonly spendThisWeek: number
  readonly spendThisMonth: number
  readonly conversionsThisWeek: number
  readonly avgCpaThisWeek: number
  readonly activeCampaigns: number
  readonly pendingApprovals: number
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-32 animate-pulse rounded-xl bg-muted"
          />
        ))}
      </div>
      <div className="h-96 animate-pulse rounded-xl bg-muted" />
    </div>
  )
}

function ErrorBanner({ message }: { readonly message: string }) {
  return (
    <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
      {message}
    </div>
  )
}

export default function DashboardPage() {
  const [kpis, setKpis] = useState<KpiData | null>(null)
  const [centres, setCentres] = useState<readonly Centre[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [launchingIds, setLaunchingIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      setError(null)

      try {
        const [kpiRes, centresRes] = await Promise.all([
          fetch('/api/dashboard/kpis'),
          fetch('/api/centres'),
        ])

        if (!kpiRes.ok) {
          throw new Error(`KPI fetch failed: ${kpiRes.status}`)
        }
        if (!centresRes.ok) {
          throw new Error(`Centres fetch failed: ${centresRes.status}`)
        }

        const kpiJson = await kpiRes.json()
        const centresJson = await centresRes.json()

        if (!kpiJson.success) {
          throw new Error(kpiJson.error ?? 'Failed to load KPIs')
        }
        if (!centresJson.success) {
          throw new Error(centresJson.error ?? 'Failed to load centres')
        }

        setKpis(kpiJson.data)
        setCentres(centresJson.data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const handleLaunch = useCallback(async (centreId: string) => {
    setLaunchingIds((prev) => new Set([...prev, centreId]))

    try {
      const res = await fetch('/api/campaigns/push', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ centreIds: [centreId] }),
      })

      const json = await res.json()

      if (!res.ok || !json.success) {
        throw new Error(json.error ?? 'Push failed')
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to launch campaign'
      )
    } finally {
      setLaunchingIds((prev) => {
        const next = new Set(prev)
        next.delete(centreId)
        return next
      })
    }
  }, [])

  if (loading) {
    return <LoadingSkeleton />
  }

  if (error && !kpis) {
    return <ErrorBanner message={error} />
  }

  return (
    <div className="space-y-6">
      {error && <ErrorBanner message={error} />}

      {kpis && (
        <>
          <ApprovalBanner count={kpis.pendingApprovals} />
          <KpiCards data={kpis} />
        </>
      )}

      <div>
        <h3 className="mb-4 text-lg font-semibold">Test Centres</h3>
        <CentresTable
          centres={centres}
          onLaunch={handleLaunch}
          launchingIds={launchingIds}
        />
      </div>
    </div>
  )
}
