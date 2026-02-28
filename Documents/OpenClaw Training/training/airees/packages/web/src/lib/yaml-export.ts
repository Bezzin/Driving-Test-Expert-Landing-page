import type { Node, Edge } from "@xyflow/react"

export function exportToYaml(nodes: Node[], edges: Edge[], pattern: string): string {
  const lines: string[] = [
    `name: custom-workflow`,
    `description: "Generated from visual builder"`,
    `pattern: ${pattern}`,
    ``,
  ]

  if (pattern === "pipeline") {
    lines.push("steps:")
    const ordered = topologicalSort(nodes, edges)
    for (const node of ordered) {
      lines.push(`  - agent: ${(node.data?.label as string)?.toLowerCase() ?? "unknown"}`)
      lines.push(`    task: "Process input"`)
    }
  } else {
    lines.push("agents:")
    for (const node of nodes) {
      const name = (node.data?.label as string)?.toLowerCase() ?? "unknown"
      lines.push(`  ${name}:`)
      lines.push(`    model: ${(node.data?.model as string) ?? "claude-sonnet-4-6"}`)
    }
  }

  return lines.join("\n")
}

function topologicalSort(nodes: Node[], edges: Edge[]): Node[] {
  const inDegree = new Map<string, number>()
  const adj = new Map<string, string[]>()

  for (const node of nodes) {
    inDegree.set(node.id, 0)
    adj.set(node.id, [])
  }

  for (const edge of edges) {
    adj.get(edge.source)?.push(edge.target)
    inDegree.set(edge.target, (inDegree.get(edge.target) ?? 0) + 1)
  }

  const queue = nodes.filter((n) => inDegree.get(n.id) === 0).map((n) => n.id)
  const sorted: string[] = []

  while (queue.length > 0) {
    const id = queue.shift()!
    sorted.push(id)
    for (const neighbor of adj.get(id) ?? []) {
      const deg = (inDegree.get(neighbor) ?? 1) - 1
      inDegree.set(neighbor, deg)
      if (deg === 0) queue.push(neighbor)
    }
  }

  const nodeMap = new Map(nodes.map((n) => [n.id, n]))
  return sorted.map((id) => nodeMap.get(id)!).filter(Boolean)
}
