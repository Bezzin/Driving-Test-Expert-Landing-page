"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { connectToRun, type RunEvent } from "@/lib/ws"

export function useRunStream(runId: string | null) {
  const [events, setEvents] = useState<RunEvent[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!runId) return

    const ws = connectToRun(runId, (event) => {
      if (event.type === "connected") {
        setConnected(true)
      }
      setEvents((prev) => [...prev, event])
    })

    ws.onclose = () => setConnected(false)
    wsRef.current = ws

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [runId])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
  }, [])

  return { events, connected, disconnect }
}
