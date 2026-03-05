import { TrendingUp, TrendingDown, Minus, BarChart3, Users } from 'lucide-react'
import type { DvsaCentre } from '@/lib/dvsa-types'

interface PassRateStatsProps {
  centre: DvsaCentre
}

function TrendArrow({ current, previous }: { current: number; previous: number }) {
  const diff = current - previous
  if (Math.abs(diff) < 0.5) return <Minus className="h-4 w-4 text-white/40" />
  if (diff > 0) return <TrendingUp className="h-4 w-4 text-green-400" />
  return <TrendingDown className="h-4 w-4 text-red-400" />
}

function ComparisonCell({ value, average }: { value: number | null; average: number }) {
  if (value === null) return <td className="px-4 py-3 text-white/40">N/A</td>
  const diff = value - average
  const color = diff > 0 ? 'text-green-400' : diff < 0 ? 'text-red-400' : 'text-white/60'
  return (
    <td className={`px-4 py-3 text-sm ${color}`}>
      {diff > 0 ? '+' : ''}
      {diff.toFixed(1)}%
    </td>
  )
}

export function PassRateStats({ centre }: PassRateStatsProps) {
  const tableRows: Array<{ label: string; value: number | null; average: number }> = [
    { label: 'Overall', value: centre.passRateOverall, average: centre.nationalAverage },
    { label: 'Male', value: centre.passRateMale, average: centre.nationalAverage },
    { label: 'Female', value: centre.passRateFemale, average: centre.nationalAverage },
    { label: 'First Attempt', value: centre.passRateFirstAttempt, average: centre.nationalAverage },
    { label: 'Automatic', value: centre.passRateAutomatic, average: centre.nationalAverage },
  ]

  const ageEntries = Object.entries(centre.passRateByAge)
    .filter(([age]) => {
      const n = parseInt(age, 10)
      return n >= 17 && n <= 25
    })
    .sort(([a], [b]) => parseInt(a, 10) - parseInt(b, 10))

  const maxAgeRate = ageEntries.length > 0
    ? Math.max(...ageEntries.map(([, rate]) => rate))
    : 100

  return (
    <section className="py-16 px-6 max-w-7xl mx-auto">
      <h2 className="font-brand text-3xl font-bold tracking-tight text-white sm:text-4xl mb-8">
        {centre.name} Pass Rate Statistics
      </h2>

      {/* Pass rate comparison table */}
      <div className="rounded-2xl border border-white/10 bg-black/40 overflow-hidden mb-10">
        <div className="flex items-center gap-2 px-6 py-4 border-b border-white/10">
          <BarChart3 className="h-5 w-5 text-accent" />
          <h3 className="text-lg font-semibold text-white">Pass Rate Comparison</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-white/10 text-sm text-white/50">
                <th className="px-4 py-3 font-medium">Category</th>
                <th className="px-4 py-3 font-medium">{centre.name}</th>
                <th className="px-4 py-3 font-medium">National Average</th>
                <th className="px-4 py-3 font-medium">Difference</th>
              </tr>
            </thead>
            <tbody>
              {tableRows.map(row => (
                <tr key={row.label} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                  <td className="px-4 py-3 text-sm font-medium text-white/80">{row.label}</td>
                  <td className="px-4 py-3 text-sm font-semibold text-white">
                    {row.value !== null ? `${row.value}%` : 'N/A'}
                  </td>
                  <td className="px-4 py-3 text-sm text-white/60">{row.average}%</td>
                  <ComparisonCell value={row.value} average={row.average} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pass rate by age */}
      {ageEntries.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-black/40 p-6 mb-10">
          <h3 className="text-lg font-semibold text-white mb-6">Pass Rate by Age (17-25)</h3>
          <div className="space-y-3">
            {ageEntries.map(([age, rate]) => (
              <div key={age} className="flex items-center gap-3">
                <span className="w-8 text-sm text-white/60 text-right shrink-0">
                  {age}
                </span>
                <div className="flex-1 h-7 rounded-full bg-white/5 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-accent/80 to-accent flex items-center justify-end pr-2 transition-all"
                    style={{ width: `${Math.max((rate / maxAgeRate) * 100, 8)}%` }}
                  >
                    <span className="text-xs font-bold text-black">{rate}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Historical trend */}
      {centre.passRateHistory.length > 1 && (
        <div className="rounded-2xl border border-white/10 bg-black/40 p-6 mb-10">
          <h3 className="text-lg font-semibold text-white mb-6">Historical Pass Rate Trend</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
            {centre.passRateHistory.map((entry, i) => {
              const prev = i > 0 ? centre.passRateHistory[i - 1].rate : entry.rate
              return (
                <div
                  key={entry.year}
                  className="rounded-xl border border-white/10 bg-white/5 p-4 text-center"
                >
                  <p className="text-xs text-white/50 mb-1">{entry.year}</p>
                  <p className="text-2xl font-bold text-white">{entry.rate}%</p>
                  {i > 0 && (
                    <div className="flex items-center justify-center gap-1 mt-1">
                      <TrendArrow current={entry.rate} previous={prev} />
                      <span
                        className={`text-xs font-medium ${
                          entry.rate - prev > 0
                            ? 'text-green-400'
                            : entry.rate - prev < 0
                              ? 'text-red-400'
                              : 'text-white/40'
                        }`}
                      >
                        {entry.rate - prev > 0 ? '+' : ''}
                        {(entry.rate - prev).toFixed(1)}%
                      </span>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Tests conducted */}
      <div className="rounded-2xl border border-white/10 bg-black/40 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Users className="h-5 w-5 text-accent" />
          <h3 className="text-lg font-semibold text-white">Tests Conducted</h3>
        </div>
        <p className="text-sm text-white/50 mb-4">Data period: {centre.dataPeriod}</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-center">
            <p className="text-2xl font-bold text-white">
              {centre.testsConductedTotal.toLocaleString()}
            </p>
            <p className="text-sm text-white/50 mt-1">Total</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-center">
            <p className="text-2xl font-bold text-white">
              {centre.testsConductedMale.toLocaleString()}
            </p>
            <p className="text-sm text-white/50 mt-1">Male</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-center">
            <p className="text-2xl font-bold text-white">
              {centre.testsConductedFemale.toLocaleString()}
            </p>
            <p className="text-sm text-white/50 mt-1">Female</p>
          </div>
        </div>
        {centre.zeroFaultPasses !== null && centre.zeroFaultPasses > 0 && (
          <p className="mt-4 text-sm text-accent">
            {centre.zeroFaultPasses} candidates achieved zero driving faults in this period.
          </p>
        )}
      </div>
    </section>
  )
}
