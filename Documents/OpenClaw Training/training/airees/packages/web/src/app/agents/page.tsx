"use client"

import { Bot, Plus } from "lucide-react"
import { AgentCard } from "@/components/agent-card"

interface Archetype {
  readonly name: string
  readonly description: string
  readonly model: string
  readonly toolsCount: number
}

const ARCHETYPES: readonly Archetype[] = [
  {
    name: "Research Analyst",
    description:
      "Performs deep web research, synthesises findings, and produces structured reports.",
    model: "claude-sonnet-4-6",
    toolsCount: 4,
  },
  {
    name: "Code Assistant",
    description:
      "Writes, reviews, and refactors code across multiple languages with best-practice guidance.",
    model: "claude-sonnet-4-6",
    toolsCount: 5,
  },
  {
    name: "Data Extractor",
    description:
      "Extracts structured data from unstructured text, PDFs, and web pages.",
    model: "claude-haiku-4-5",
    toolsCount: 3,
  },
  {
    name: "Content Writer",
    description:
      "Drafts blog posts, marketing copy, and social media content in a consistent brand voice.",
    model: "claude-sonnet-4-6",
    toolsCount: 2,
  },
  {
    name: "QA Tester",
    description:
      "Generates test plans, writes automated test suites, and analyses test coverage.",
    model: "claude-haiku-4-5",
    toolsCount: 4,
  },
  {
    name: "DevOps Engineer",
    description:
      "Manages CI/CD pipelines, infrastructure-as-code, and deployment automation.",
    model: "claude-sonnet-4-6",
    toolsCount: 6,
  },
  {
    name: "Security Auditor",
    description:
      "Analyses code and configurations for security vulnerabilities and compliance issues.",
    model: "claude-opus-4-6",
    toolsCount: 5,
  },
  {
    name: "Product Manager",
    description:
      "Breaks down feature requests into user stories, acceptance criteria, and roadmap items.",
    model: "claude-sonnet-4-6",
    toolsCount: 3,
  },
] as const

export default function AgentsPage() {
  return (
    <div className="space-y-10">
      {/* Archetypes section */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-100">Archetypes</h2>
            <p className="mt-0.5 text-sm text-gray-400">
              Pre-built agent templates ready to use
            </p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {ARCHETYPES.map((archetype) => (
            <AgentCard
              key={archetype.name}
              name={archetype.name}
              description={archetype.description}
              model={archetype.model}
              toolsCount={archetype.toolsCount}
            />
          ))}
        </div>
      </section>

      {/* My Agents section */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-100">My Agents</h2>
            <p className="mt-0.5 text-sm text-gray-400">
              Custom agents you have created
            </p>
          </div>
          <button
            type="button"
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500"
          >
            <Plus size={16} />
            New Agent
          </button>
        </div>
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-700 bg-gray-900/50 py-16">
          <Bot size={40} className="mb-3 text-gray-600" />
          <p className="text-sm font-medium text-gray-400">No agents yet</p>
          <p className="mt-1 text-xs text-gray-500">
            Create your first agent or use an archetype above
          </p>
        </div>
      </section>
    </div>
  )
}
