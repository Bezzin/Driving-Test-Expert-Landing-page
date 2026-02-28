"use client"

import { Bot, Wrench } from "lucide-react"

interface AgentCardProps {
  readonly name: string
  readonly description: string
  readonly model: string
  readonly toolsCount: number
  readonly onUse?: () => void
}

function modelBadgeColor(model: string): string {
  if (model.includes("opus")) return "bg-purple-600/20 text-purple-400"
  if (model.includes("sonnet")) return "bg-blue-600/20 text-blue-400"
  if (model.includes("haiku")) return "bg-green-600/20 text-green-400"
  return "bg-gray-600/20 text-gray-400"
}

export function AgentCard({
  name,
  description,
  model,
  toolsCount,
  onUse,
}: AgentCardProps) {
  return (
    <div className="flex flex-col rounded-xl border border-gray-700/50 bg-gray-900 p-5 transition-colors hover:border-gray-600">
      <div className="mb-3 flex items-start justify-between">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600/20">
          <Bot size={20} className="text-indigo-400" />
        </div>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${modelBadgeColor(model)}`}
        >
          {model}
        </span>
      </div>

      <h3 className="mb-1.5 text-sm font-semibold text-gray-100">{name}</h3>
      <p className="mb-4 flex-1 text-xs leading-relaxed text-gray-400">
        {description}
      </p>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <Wrench size={14} />
          <span>
            {toolsCount} tool{toolsCount !== 1 ? "s" : ""}
          </span>
        </div>
        <button
          type="button"
          onClick={onUse}
          className="rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-indigo-500"
        >
          Use
        </button>
      </div>
    </div>
  )
}
