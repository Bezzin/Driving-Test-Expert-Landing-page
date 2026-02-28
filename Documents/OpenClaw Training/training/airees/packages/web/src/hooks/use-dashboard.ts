"use client"

import { useState, useEffect } from "react"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export interface DashboardMetrics {
  active_projects: number
  needs_attention: number
  queue_length: number
  completed: number
}

export function useDashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchMetrics() {
      try {
        const resp = await fetch(`${API_URL}/api/dashboard/metrics`)
        if (!resp.ok) throw new Error("Failed to fetch metrics")
        const data = await resp.json()
        setMetrics(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error")
      } finally {
        setLoading(false)
      }
    }
    fetchMetrics()
    const interval = setInterval(fetchMetrics, 10000)
    return () => clearInterval(interval)
  }, [])

  return { metrics, loading, error }
}
