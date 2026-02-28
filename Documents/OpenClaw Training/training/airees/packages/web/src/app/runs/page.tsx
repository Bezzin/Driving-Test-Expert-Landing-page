"use client"

import { useState } from "react"
import { Play, StopCircle, Clock, Zap } from "lucide-react"
import { RunTimeline } from "@/components/run-timeline"
import { useRunStream } from "@/hooks/use-run-stream"

export default function RunsPage() {
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const { events, connected, disconnect } = useRunStream(activeRunId)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Runs</h1>
        <div className="flex items-center gap-2">
          {connected ? (
            <button
              onClick={() => { disconnect(); setActiveRunId(null) }}
              className="flex items-center gap-2 rounded-md bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700"
            >
              <StopCircle className="h-4 w-4" />
              Stop
            </button>
          ) : (
            <button
              onClick={() => setActiveRunId(`run-${Date.now()}`)}
              className="flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
            >
              <Play className="h-4 w-4" />
              New Run
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg bg-gray-900 p-4 border border-gray-800">
          <div className="flex items-center gap-2 text-gray-400">
            <Clock className="h-4 w-4" />
            <span className="text-sm">Status</span>
          </div>
          <div className="mt-1 text-lg font-semibold text-white">
            {connected ? "Connected" : "Idle"}
          </div>
        </div>
        <div className="rounded-lg bg-gray-900 p-4 border border-gray-800">
          <div className="flex items-center gap-2 text-gray-400">
            <Zap className="h-4 w-4" />
            <span className="text-sm">Events</span>
          </div>
          <div className="mt-1 text-lg font-semibold text-white">{events.length}</div>
        </div>
        <div className="rounded-lg bg-gray-900 p-4 border border-gray-800">
          <div className="flex items-center gap-2 text-gray-400">
            <Play className="h-4 w-4" />
            <span className="text-sm">Run ID</span>
          </div>
          <div className="mt-1 text-sm font-mono text-white truncate">
            {activeRunId ?? "\u2014"}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-gray-800 bg-gray-900 p-6">
        <h2 className="mb-4 text-lg font-semibold text-white">Timeline</h2>
        <RunTimeline events={events} />
      </div>
    </div>
  )
}
