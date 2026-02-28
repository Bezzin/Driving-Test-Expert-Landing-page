"use client"

import { Handle, Position } from "@xyflow/react"

interface AgentNodeData {
  label: string
  model: string
  toolCount: number
}

export function AgentNode({ data }: { data: AgentNodeData }) {
  return (
    <div className="rounded-lg border border-gray-600 bg-gray-800 p-4 shadow-lg min-w-[180px]">
      <Handle type="target" position={Position.Top} className="!bg-indigo-500" />
      <div className="text-sm font-semibold text-white">{data.label}</div>
      <div className="mt-1 text-xs text-gray-400">{data.model}</div>
      {data.toolCount > 0 && (
        <div className="mt-1 text-xs text-gray-500">{data.toolCount} tools</div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-indigo-500" />
    </div>
  )
}
