const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function fetchAgents() {
  const res = await fetch(`${API_BASE}/api/agents`)
  return res.json()
}

export async function fetchArchetypes() {
  const res = await fetch(`${API_BASE}/api/archetypes`)
  return res.json()
}

export async function createAgent(agent: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/api/agents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(agent),
  })
  return res.json()
}
