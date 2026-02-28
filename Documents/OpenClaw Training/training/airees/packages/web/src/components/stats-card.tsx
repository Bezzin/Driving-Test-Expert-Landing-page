import type { LucideIcon } from "lucide-react"

interface StatsCardProps {
  readonly title: string
  readonly value: string | number
  readonly icon: LucideIcon
  readonly color?: string
}

export function StatsCard({
  title,
  value,
  icon: Icon,
  color = "text-indigo-400",
}: StatsCardProps) {
  return (
    <div className="rounded-xl border border-gray-700/50 bg-gray-900 p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">{title}</p>
        <Icon size={20} className={color} />
      </div>
      <p className="mt-2 text-2xl font-bold text-gray-100">{value}</p>
    </div>
  )
}
