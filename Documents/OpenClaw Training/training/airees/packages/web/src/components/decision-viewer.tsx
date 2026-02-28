"use client"

import { useState, useEffect } from "react"
import { FileText } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

interface DecisionViewerProps {
  projectId: string
}

export function DecisionViewer({ projectId }: DecisionViewerProps) {
  const [markdown, setMarkdown] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchDecisions() {
      try {
        const resp = await fetch(`${API_URL}/api/state/${projectId}/decisions`)
        if (!resp.ok) {
          setMarkdown(null)
          return
        }
        const data = await resp.json()
        setMarkdown(data.markdown)
      } catch {
        setMarkdown(null)
      } finally {
        setLoading(false)
      }
    }
    fetchDecisions()
  }, [projectId])

  if (loading) {
    return <div className="animate-pulse h-32 bg-gray-800 rounded-lg" />
  }

  if (!markdown) {
    return (
      <div className="flex items-center gap-2 text-gray-500 p-4">
        <FileText className="w-4 h-4" />
        <span>No decisions recorded yet</span>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-4 h-4 text-indigo-400" />
        <h3 className="text-sm font-medium text-gray-300">Decision Document</h3>
      </div>
      <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
        {markdown}
      </pre>
    </div>
  )
}
