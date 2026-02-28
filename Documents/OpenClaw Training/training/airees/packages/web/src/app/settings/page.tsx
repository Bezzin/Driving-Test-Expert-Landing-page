"use client"

import { useState, useEffect, type FormEvent } from "react"
import { Save, Eye, EyeOff } from "lucide-react"

interface SettingsState {
  readonly anthropicApiKey: string
  readonly openRouterApiKey: string
  readonly defaultModel: string
}

const MODEL_OPTIONS = [
  { value: "claude-opus-4-6", label: "Claude Opus 4.6" },
  { value: "claude-sonnet-4-6", label: "Claude Sonnet 4.6" },
  { value: "claude-haiku-4-5", label: "Claude Haiku 4.5" },
] as const

const STORAGE_KEY = "airees-settings"

function loadSettings(): SettingsState {
  if (typeof window === "undefined") {
    return {
      anthropicApiKey: "",
      openRouterApiKey: "",
      defaultModel: "claude-sonnet-4-6",
    }
  }

  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return JSON.parse(stored) as SettingsState
    }
  } catch {
    // Fall through to default
  }

  return {
    anthropicApiKey: "",
    openRouterApiKey: "",
    defaultModel: "claude-sonnet-4-6",
  }
}

function PasswordInput({
  id,
  value,
  onChange,
  placeholder,
}: {
  readonly id: string
  readonly value: string
  readonly onChange: (value: string) => void
  readonly placeholder: string
}) {
  const [visible, setVisible] = useState(false)

  return (
    <div className="relative">
      <input
        id={id}
        type={visible ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 pr-10 text-sm text-gray-100 placeholder-gray-500 transition-colors focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
      />
      <button
        type="button"
        onClick={() => setVisible((prev) => !prev)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
        aria-label={visible ? "Hide input" : "Show input"}
      >
        {visible ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  )
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsState>({
    anthropicApiKey: "",
    openRouterApiKey: "",
    defaultModel: "claude-sonnet-4-6",
  })
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setSettings(loadSettings())
  }, [])

  const updateField = (field: keyof SettingsState, value: string) => {
    setSettings((prev) => ({ ...prev, [field]: value }))
    setSaved(false)
  }

  const handleSave = (e: FormEvent) => {
    e.preventDefault()

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (error) {
      throw new Error(
        `Failed to save settings: ${error instanceof Error ? error.message : "Unknown error"}`
      )
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-gray-100">Settings</h2>
        <p className="mt-1 text-sm text-gray-400">
          Configure API keys and default preferences
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Anthropic API Key */}
        <div className="rounded-xl border border-gray-700/50 bg-gray-900 p-5">
          <label
            htmlFor="anthropic-key"
            className="mb-1 block text-sm font-medium text-gray-200"
          >
            Anthropic API Key
          </label>
          <p className="mb-3 text-xs text-gray-500">
            Required for Claude model access
          </p>
          <PasswordInput
            id="anthropic-key"
            value={settings.anthropicApiKey}
            onChange={(v) => updateField("anthropicApiKey", v)}
            placeholder="sk-ant-..."
          />
        </div>

        {/* OpenRouter API Key */}
        <div className="rounded-xl border border-gray-700/50 bg-gray-900 p-5">
          <label
            htmlFor="openrouter-key"
            className="mb-1 block text-sm font-medium text-gray-200"
          >
            OpenRouter API Key
            <span className="ml-2 text-xs font-normal text-gray-500">
              Optional
            </span>
          </label>
          <p className="mb-3 text-xs text-gray-500">
            For accessing models via OpenRouter
          </p>
          <PasswordInput
            id="openrouter-key"
            value={settings.openRouterApiKey}
            onChange={(v) => updateField("openRouterApiKey", v)}
            placeholder="sk-or-..."
          />
        </div>

        {/* Default Model */}
        <div className="rounded-xl border border-gray-700/50 bg-gray-900 p-5">
          <label
            htmlFor="default-model"
            className="mb-1 block text-sm font-medium text-gray-200"
          >
            Default Model
          </label>
          <p className="mb-3 text-xs text-gray-500">
            Model used for new agents by default
          </p>
          <select
            id="default-model"
            value={settings.defaultModel}
            onChange={(e) => updateField("defaultModel", e.target.value)}
            className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-gray-100 transition-colors focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            {MODEL_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Save button */}
        <div className="flex items-center gap-3">
          <button
            type="submit"
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-500"
          >
            <Save size={16} />
            Save Settings
          </button>
          {saved && (
            <span className="text-sm text-green-400">
              Settings saved successfully
            </span>
          )}
        </div>
      </form>
    </div>
  )
}
