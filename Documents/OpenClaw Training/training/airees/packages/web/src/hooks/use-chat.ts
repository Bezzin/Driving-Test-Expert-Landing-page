"use client"

import { useState, useCallback, useRef } from "react"

export interface ChatMessage {
  readonly id: string
  readonly role: "user" | "assistant" | "system"
  readonly content: string
  readonly agent?: string
}

interface SSEPayload {
  readonly type: string
  readonly agent: string
  readonly data: Record<string, unknown>
  readonly run_id: string
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export function useChat() {
  const [messages, setMessages] = useState<readonly ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [activeAgent, setActiveAgent] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(async (text: string) => {
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
    }
    setMessages((prev) => [...prev, userMsg])
    setIsStreaming(true)
    setActiveAgent(null)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
        signal: controller.signal,
      })

      if (!response.ok) {
        const errorText = await response.text()
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "system",
            content: `Error: ${response.status} — ${errorText}`,
          },
        ])
        setIsStreaming(false)
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        setIsStreaming(false)
        return
      }

      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() ?? ""

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue
          const jsonStr = line.slice(6).trim()
          if (!jsonStr) continue

          try {
            const payload: SSEPayload = JSON.parse(jsonStr)

            if (payload.type === "agent.start") {
              setActiveAgent(payload.agent)
            }

            if (payload.type === "chat.response") {
              const output = String(payload.data.output ?? "")
              setMessages((prev) => [
                ...prev,
                {
                  id: crypto.randomUUID(),
                  role: "assistant",
                  content: output,
                  agent: payload.agent,
                },
              ])
              setActiveAgent(null)
            }

            if (payload.type === "chat.error") {
              const error = String(payload.data.error ?? "Unknown error")
              setMessages((prev) => [
                ...prev,
                {
                  id: crypto.randomUUID(),
                  role: "system",
                  content: `Error: ${error}`,
                },
              ])
              setActiveAgent(null)
            }
          } catch {
            // skip malformed SSE lines
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        // user cancelled — not an error
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "system",
            content: `Connection error: ${err instanceof Error ? err.message : "Unknown"}`,
          },
        ])
      }
    } finally {
      setIsStreaming(false)
      setActiveAgent(null)
      abortRef.current = null
    }
  }, [])

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return { messages, isStreaming, activeAgent, sendMessage, stopStreaming } as const
}
