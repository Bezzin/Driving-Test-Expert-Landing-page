"use client"

import { useRef, useEffect, useState, type FormEvent } from "react"
import { Send, Square, Zap, Loader2 } from "lucide-react"
import { useChat, type ChatMessage } from "@/hooks/use-chat"

function AgentBadge({ name }: { readonly name: string }) {
  return (
    <span className="mb-1 inline-block rounded-full bg-indigo-500/15 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider text-indigo-400">
      {name}
    </span>
  )
}

function MessageBubble({ message }: { readonly message: ChatMessage }) {
  if (message.role === "system") {
    return (
      <div className="flex justify-center px-4 py-2">
        <p className="max-w-md rounded-lg bg-red-500/10 px-4 py-2 text-center text-sm italic text-red-400/90">
          {message.content}
        </p>
      </div>
    )
  }

  const isUser = message.role === "user"

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} px-4`}>
      <div className={`max-w-[75%] ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        {!isUser && message.agent && <AgentBadge name={message.agent} />}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-indigo-600 text-gray-50"
              : "bg-gray-800 text-gray-200 ring-1 ring-gray-700/60"
          }`}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    </div>
  )
}

function ThinkingIndicator({ agent }: { readonly agent: string | null }) {
  return (
    <div className="flex justify-start px-4">
      <div className="flex flex-col items-start">
        {agent && <AgentBadge name={agent} />}
        <div className="flex items-center gap-2.5 rounded-2xl bg-gray-800 px-4 py-3 ring-1 ring-gray-700/60">
          <Loader2 size={14} className="animate-spin text-indigo-400" />
          <span className="text-sm text-gray-400">
            {agent ? `${agent} is thinking...` : "Routing..."}
          </span>
        </div>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 pb-20">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600/10 ring-1 ring-indigo-500/20">
        <Zap size={28} className="text-indigo-400" />
      </div>
      <div className="text-center">
        <h2 className="text-lg font-semibold text-gray-200">
          What can I help you with?
        </h2>
        <p className="mt-1 max-w-sm text-sm text-gray-500">
          Type a message and Airees will route it to the best agent automatically.
        </p>
      </div>
    </div>
  )
}

export function ChatView() {
  const { messages, isStreaming, activeAgent, sendMessage, stopStreaming } = useChat()
  const [canSend, setCanSend] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isStreaming, activeAgent])

  useEffect(() => {
    if (!isStreaming) {
      inputRef.current?.focus()
    }
  }, [isStreaming])

  const getInputValue = () => inputRef.current?.value.trim() ?? ""

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = getInputValue()
    if (!trimmed || isStreaming) return
    if (inputRef.current) inputRef.current.value = ""
    setCanSend(false)
    sendMessage(trimmed)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleInput = () => {
    setCanSend(getInputValue().length > 0)
  }

  const isEmpty = messages.length === 0

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      {/* Messages area */}
      <div className="flex flex-1 flex-col overflow-y-auto">
        {isEmpty ? (
          <EmptyState />
        ) : (
          <div className="flex flex-col gap-4 py-6">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isStreaming && <ThinkingIndicator agent={activeAgent} />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-800 bg-gray-900/80 px-4 py-3 backdrop-blur-sm">
        <form
          onSubmit={handleSubmit}
          className="mx-auto flex max-w-3xl items-end gap-3"
        >
          <textarea
            ref={inputRef}
            onInput={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Send a message..."
            rows={1}
            disabled={isStreaming}
            className="flex-1 resize-none rounded-xl border border-gray-700 bg-gray-800 px-4 py-3 text-sm text-gray-100 placeholder-gray-500 transition-colors focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 disabled:opacity-50"
          />
          {isStreaming ? (
            <button
              type="button"
              onClick={stopStreaming}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-red-600/80 text-white transition-colors hover:bg-red-600"
              aria-label="Stop"
            >
              <Square size={16} />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!canSend}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white transition-colors hover:bg-indigo-500 disabled:opacity-30 disabled:hover:bg-indigo-600"
              aria-label="Send"
            >
              <Send size={16} />
            </button>
          )}
        </form>
      </div>
    </div>
  )
}
