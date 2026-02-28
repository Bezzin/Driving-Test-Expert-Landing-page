export interface RunEvent {
  type: string
  agent?: string
  data?: Record<string, unknown>
  timestamp?: string
}

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"

export function connectToRun(
  runId: string,
  onEvent: (event: RunEvent) => void
): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/ws/runs/${runId}`)
  ws.onmessage = (msg) => {
    try {
      onEvent(JSON.parse(msg.data))
    } catch {
      // ignore parse errors
    }
  }
  return ws
}
