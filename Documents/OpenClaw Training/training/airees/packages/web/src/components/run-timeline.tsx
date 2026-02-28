"use client"

import type { RunEvent } from "@/lib/ws"

interface RunTimelineProps {
  events: RunEvent[]
}

const eventColors: Record<string, string> = {
  "agent.start": "bg-indigo-500",
  "agent.complete": "bg-green-500",
  "agent.tool_call": "bg-yellow-500",
  "agent.handoff": "bg-purple-500",
  "run.start": "bg-blue-500",
  "run.complete": "bg-green-600",
  "run.error": "bg-red-500",
  connected: "bg-gray-500",
  pong: "bg-gray-600",
}

export function RunTimeline({ events }: RunTimelineProps) {
  if (events.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-gray-500">
        No events yet. Start a run to see the timeline.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {events.map((event, i) => (
        <div key={i} className="flex items-start gap-3">
          <div className="flex flex-col items-center">
            <div className={`h-3 w-3 rounded-full ${eventColors[event.type] ?? "bg-gray-500"}`} />
            {i < events.length - 1 && <div className="h-8 w-px bg-gray-700" />}
          </div>
          <div className="flex-1 pb-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-white">{event.type}</span>
              {event.agent && (
                <span className="rounded bg-gray-700 px-1.5 py-0.5 text-xs text-gray-300">
                  {event.agent}
                </span>
              )}
            </div>
            {event.timestamp && (
              <div className="text-xs text-gray-500">{event.timestamp}</div>
            )}
            {event.data && (
              <pre className="mt-1 rounded bg-gray-800 p-2 text-xs text-gray-400 overflow-x-auto">
                {JSON.stringify(event.data, null, 2)}
              </pre>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
