import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Micros conversion: 1 GBP = 1,000,000 micros
export function microsToPounds(micros: number | bigint): number {
  return Number(micros) / 1_000_000
}

export function poundsToMicros(pounds: number): bigint {
  return BigInt(Math.round(pounds * 1_000_000))
}

export function formatPounds(micros: number | bigint): string {
  const pounds = microsToPounds(micros)
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
  }).format(pounds)
}

export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-GB').format(value)
}

export function getCpaColour(cpaMicros: number): string {
  const pounds = microsToPounds(cpaMicros)
  if (pounds < 6) return 'text-green-600'
  if (pounds <= 12) return 'text-amber-600'
  return 'text-red-600'
}

export function getCpaRowColour(cpaMicros: number): string {
  const pounds = microsToPounds(cpaMicros)
  if (pounds < 6) return 'bg-green-50'
  if (pounds <= 12) return 'bg-amber-50'
  return 'bg-red-50'
}
