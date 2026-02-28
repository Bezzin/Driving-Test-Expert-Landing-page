"use client"

import { Activity, AlertTriangle, CheckCircle2, Clock } from "lucide-react"
import { StatsCard } from "@/components/stats-card"
import { useDashboard } from "@/hooks/use-dashboard"

export default function DashboardPage() {
  const { metrics, loading, error } = useDashboard()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="text-red-400">Failed to load dashboard: {error}</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Active Projects"
          value={metrics?.active_projects ?? 0}
          icon={Activity}
          color="indigo"
        />
        <StatsCard
          title="Needs Attention"
          value={metrics?.needs_attention ?? 0}
          icon={AlertTriangle}
          color={metrics?.needs_attention ? "red" : "gray"}
        />
        <StatsCard
          title="Queue"
          value={metrics?.queue_length ?? 0}
          icon={Clock}
          color="yellow"
        />
        <StatsCard
          title="Completed"
          value={metrics?.completed ?? 0}
          icon={CheckCircle2}
          color="green"
        />
      </div>
    </div>
  )
}
