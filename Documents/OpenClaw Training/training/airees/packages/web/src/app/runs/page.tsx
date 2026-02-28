import { Play } from "lucide-react"

export default function RunsPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <Play size={48} className="mb-4 text-gray-600" />
      <h2 className="text-xl font-bold text-gray-100">Runs</h2>
      <p className="mt-2 text-sm text-gray-400">
        Agent run history will appear here
      </p>
    </div>
  )
}
