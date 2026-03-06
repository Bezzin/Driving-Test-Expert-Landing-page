'use client'

import { useState, useMemo, useCallback } from 'react'
import Link from 'next/link'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  formatPounds,
  formatNumber,
  getCpaColour,
  getCpaRowColour,
  microsToPounds,
} from '@/lib/utils'

export interface Centre {
  readonly id: string
  readonly name: string
  readonly slug: string
  readonly region: string
  readonly priority_tier: string | null
  readonly status: string
  readonly route_count: number | null
  readonly has_landing_page: boolean
  readonly pass_rate: number | null
  readonly tests_conducted: number | null
  readonly spend_7d: number
  readonly conversions_7d: number
  readonly cpa: number
}

type SortField = 'name' | 'spend_7d' | 'conversions_7d' | 'cpa'
type SortDir = 'asc' | 'desc'

interface CentresTableProps {
  readonly centres: readonly Centre[]
  readonly onLaunch: (centreId: string) => void
  readonly launchingIds: ReadonlySet<string>
}

const TIER_STYLES: Record<string, string> = {
  tier_1: 'bg-green-100 text-green-800',
  tier_2: 'bg-blue-100 text-blue-800',
  tier_3: 'bg-gray-100 text-gray-700',
}

const STATUS_STYLES: Record<string, string> = {
  active: 'bg-green-100 text-green-800',
  paused: 'bg-amber-100 text-amber-800',
  pending: 'bg-gray-100 text-gray-600',
  excluded: 'bg-red-100 text-red-800',
}

function getRowBg(centre: Centre): string {
  if (centre.status !== 'active') {
    return ''
  }
  if (centre.cpa <= 0) {
    return ''
  }
  return getCpaRowColour(centre.cpa)
}

function compareCentres(a: Centre, b: Centre, field: SortField, dir: SortDir): number {
  let result = 0

  switch (field) {
    case 'name':
      result = a.name.localeCompare(b.name)
      break
    case 'spend_7d':
      result = a.spend_7d - b.spend_7d
      break
    case 'conversions_7d':
      result = a.conversions_7d - b.conversions_7d
      break
    case 'cpa':
      result = a.cpa - b.cpa
      break
  }

  return dir === 'desc' ? -result : result
}

export function CentresTable({ centres, onLaunch, launchingIds }: CentresTableProps) {
  const [sortField, setSortField] = useState<SortField>('name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [tierFilter, setTierFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const handleSort = useCallback((field: SortField) => {
    setSortField((prev) => {
      if (prev === field) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
        return prev
      }
      setSortDir('asc')
      return field
    })
  }, [])

  const filtered = useMemo(() => {
    return centres.filter((c) => {
      if (tierFilter !== 'all' && c.priority_tier !== tierFilter) {
        return false
      }
      if (statusFilter !== 'all' && c.status !== statusFilter) {
        return false
      }
      return true
    })
  }, [centres, tierFilter, statusFilter])

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => compareCentres(a, b, sortField, sortDir))
  }, [filtered, sortField, sortDir])

  const sortIndicator = (field: SortField): string => {
    if (sortField !== field) return ''
    return sortDir === 'asc' ? ' \u2191' : ' \u2193'
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">Tier:</span>
          <Select value={tierFilter} onValueChange={(v) => setTierFilter(v ?? 'all')}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All tiers</SelectItem>
              <SelectItem value="tier_1">Tier 1</SelectItem>
              <SelectItem value="tier_2">Tier 2</SelectItem>
              <SelectItem value="tier_3">Tier 3</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">Status:</span>
          <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v ?? 'all')}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="paused">Paused</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="excluded">Excluded</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <span className="ml-auto text-sm text-muted-foreground">
          {sorted.length} centre{sorted.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead
                className="cursor-pointer select-none"
                onClick={() => handleSort('name')}
              >
                Centre Name{sortIndicator('name')}
              </TableHead>
              <TableHead>Region</TableHead>
              <TableHead>Tier</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Routes</TableHead>
              <TableHead
                className="cursor-pointer select-none text-right"
                onClick={() => handleSort('spend_7d')}
              >
                7d Spend{sortIndicator('spend_7d')}
              </TableHead>
              <TableHead
                className="cursor-pointer select-none text-right"
                onClick={() => handleSort('conversions_7d')}
              >
                7d Conv{sortIndicator('conversions_7d')}
              </TableHead>
              <TableHead
                className="cursor-pointer select-none text-right"
                onClick={() => handleSort('cpa')}
              >
                7d CPA{sortIndicator('cpa')}
              </TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.length === 0 && (
              <TableRow>
                <TableCell colSpan={9} className="py-8 text-center text-muted-foreground">
                  No centres match the current filters.
                </TableCell>
              </TableRow>
            )}
            {sorted.map((centre) => (
              <TableRow key={centre.id} className={getRowBg(centre)}>
                <TableCell className="font-medium">
                  <Link
                    href={`/dashboard/centres/${centre.slug}`}
                    className="text-primary underline-offset-4 hover:underline"
                  >
                    {centre.name}
                  </Link>
                </TableCell>
                <TableCell>{centre.region}</TableCell>
                <TableCell>
                  {centre.priority_tier && (
                    <Badge
                      variant="secondary"
                      className={TIER_STYLES[centre.priority_tier] ?? 'bg-gray-100 text-gray-700'}
                    >
                      {centre.priority_tier.replace('_', ' ')}
                    </Badge>
                  )}
                </TableCell>
                <TableCell>
                  <Badge
                    variant="secondary"
                    className={STATUS_STYLES[centre.status] ?? 'bg-gray-100 text-gray-600'}
                  >
                    {centre.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  {centre.route_count != null ? formatNumber(centre.route_count) : '-'}
                </TableCell>
                <TableCell className="text-right">
                  {centre.spend_7d > 0 ? formatPounds(centre.spend_7d) : '-'}
                </TableCell>
                <TableCell className="text-right">
                  {centre.conversions_7d > 0 ? formatNumber(centre.conversions_7d) : '-'}
                </TableCell>
                <TableCell className={`text-right font-medium ${centre.cpa > 0 ? getCpaColour(centre.cpa) : ''}`}>
                  {centre.cpa > 0
                    ? formatPounds(centre.cpa)
                    : '-'}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      variant="default"
                      size="xs"
                      onClick={() => onLaunch(centre.id)}
                      disabled={launchingIds.has(centre.id) || centre.status === 'excluded'}
                    >
                      {launchingIds.has(centre.id) ? 'Pushing...' : 'Launch'}
                    </Button>
                    <Link href={`/dashboard/centres/${centre.slug}`}>
                      <Button variant="outline" size="xs">
                        View
                      </Button>
                    </Link>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
