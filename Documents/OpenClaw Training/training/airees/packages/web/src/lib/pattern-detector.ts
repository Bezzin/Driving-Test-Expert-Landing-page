import type { Node, Edge } from "@xyflow/react"

export type Pattern = "pipeline" | "parallel" | "triage" | "shared_state" | "unknown"

export function detectPattern(nodes: Node[], edges: Edge[]): Pattern {
  if (nodes.length === 0 || edges.length === 0) return "unknown"

  const outDegree = new Map<string, number>()
  const inDegree = new Map<string, number>()

  for (const node of nodes) {
    outDegree.set(node.id, 0)
    inDegree.set(node.id, 0)
  }

  for (const edge of edges) {
    outDegree.set(edge.source, (outDegree.get(edge.source) ?? 0) + 1)
    inDegree.set(edge.target, (inDegree.get(edge.target) ?? 0) + 1)
  }

  const maxOut = Math.max(...outDegree.values())
  const maxIn = Math.max(...inDegree.values())

  // Pipeline: linear chain
  if (maxOut <= 1 && maxIn <= 1 && edges.length === nodes.length - 1) {
    return "pipeline"
  }

  // Parallel/Triage: one node fans out
  if (maxOut > 1 && maxIn <= 1) {
    const fanOutNode = nodes.find((n) => outDegree.get(n.id) === maxOut)
    const label = fanOutNode?.data?.label as string | undefined
    if (label?.toLowerCase().includes("router")) {
      return "triage"
    }
    return "parallel"
  }

  return "unknown"
}
