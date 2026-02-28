"use client"

import { useCallback, useState } from "react"
import {
  ReactFlow,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  type Connection,
  type Node,
  type Edge,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { AgentNode } from "./agent-node"
import { detectPattern } from "@/lib/pattern-detector"
import { exportToYaml } from "@/lib/yaml-export"

const nodeTypes = { agent: AgentNode }

const initialNodes: Node[] = []
const initialEdges: Edge[] = []

export function FlowCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [pattern, setPattern] = useState<string>("unknown")

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) => {
        const newEdges = addEdge({ ...params, animated: true, style: { stroke: "#6366f1" } }, eds)
        setPattern(detectPattern(nodes, newEdges))
        return newEdges
      })
    },
    [nodes, setEdges]
  )

  const addAgentNode = useCallback(
    (name: string, model: string, toolCount: number) => {
      const newNode: Node = {
        id: `agent-${Date.now()}`,
        type: "agent",
        position: { x: 250, y: nodes.length * 120 + 50 },
        data: { label: name, model, toolCount },
      }
      setNodes((nds) => [...nds, newNode])
    },
    [nodes.length, setNodes]
  )

  const handleExport = useCallback(() => {
    const yaml = exportToYaml(nodes, edges, pattern)
    navigator.clipboard.writeText(yaml)
  }, [nodes, edges, pattern])

  return (
    <div className="flex h-full">
      <div className="w-56 border-r border-gray-700 bg-gray-900 p-4">
        <h3 className="mb-3 text-sm font-semibold text-gray-300">Archetypes</h3>
        <div className="space-y-2">
          {[
            { name: "Researcher", model: "claude-sonnet-4-6", tools: 3 },
            { name: "Coder", model: "claude-sonnet-4-6", tools: 3 },
            { name: "Reviewer", model: "claude-sonnet-4-6", tools: 1 },
            { name: "Planner", model: "claude-opus-4-6", tools: 2 },
            { name: "Writer", model: "claude-sonnet-4-6", tools: 2 },
            { name: "Router", model: "claude-haiku-4-5", tools: 0 },
          ].map((arch) => (
            <button
              key={arch.name}
              onClick={() => addAgentNode(arch.name, arch.model, arch.tools)}
              className="w-full rounded-md bg-gray-800 px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-700"
            >
              {arch.name}
            </button>
          ))}
        </div>
        <div className="mt-6 border-t border-gray-700 pt-4">
          <div className="mb-2 text-xs text-gray-500">Detected Pattern</div>
          <div className="rounded bg-indigo-500/20 px-2 py-1 text-center text-sm font-medium text-indigo-400">
            {pattern}
          </div>
          <button
            onClick={handleExport}
            className="mt-3 w-full rounded-md bg-indigo-600 px-3 py-2 text-sm text-white hover:bg-indigo-700"
          >
            Export YAML
          </button>
        </div>
      </div>
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          className="bg-gray-950"
        >
          <Controls className="!bg-gray-800 !border-gray-700 !text-white [&>button]:!bg-gray-800 [&>button]:!border-gray-700 [&>button]:!text-white [&>button:hover]:!bg-gray-700" />
          <MiniMap className="!bg-gray-900" nodeColor="#4f46e5" />
          <Background variant={BackgroundVariant.Dots} color="#374151" gap={20} />
        </ReactFlow>
      </div>
    </div>
  )
}
