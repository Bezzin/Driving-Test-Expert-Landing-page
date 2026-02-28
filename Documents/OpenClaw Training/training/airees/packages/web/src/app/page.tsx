import { Activity, Bot, Play, Zap } from "lucide-react"
import { StatsCard } from "@/components/stats-card"

const DASHBOARD_STATS = [
  { title: "Active Runs", value: 0, icon: Activity, color: "text-green-400" },
  { title: "Total Agents", value: 0, icon: Bot, color: "text-indigo-400" },
  { title: "Total Runs", value: 0, icon: Play, color: "text-blue-400" },
  { title: "Tokens Used", value: 0, icon: Zap, color: "text-amber-400" },
] as const

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">
          Welcome to Airees
        </h2>
        <p className="mt-1 text-sm text-gray-400">
          Your multi-agent orchestration platform
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {DASHBOARD_STATS.map((stat) => (
          <StatsCard
            key={stat.title}
            title={stat.title}
            value={stat.value}
            icon={stat.icon}
            color={stat.color}
          />
        ))}
      </div>

      <div className="rounded-xl border border-gray-700/50 bg-gray-900 p-6">
        <h3 className="mb-2 text-lg font-semibold text-gray-100">
          Getting Started
        </h3>
        <p className="text-sm leading-relaxed text-gray-400">
          Configure your API keys in Settings, explore pre-built agent
          archetypes in the Agent Library, or build your own custom agents in
          the Builder.
        </p>
      </div>
    </div>
  )
}
