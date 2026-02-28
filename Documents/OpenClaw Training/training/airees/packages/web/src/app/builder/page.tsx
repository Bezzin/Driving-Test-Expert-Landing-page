import { Workflow } from "lucide-react"

export default function BuilderPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <Workflow size={48} className="mb-4 text-gray-600" />
      <h2 className="text-xl font-bold text-gray-100">Agent Builder</h2>
      <p className="mt-2 text-sm text-gray-400">
        Visual agent builder coming soon
      </p>
    </div>
  )
}
