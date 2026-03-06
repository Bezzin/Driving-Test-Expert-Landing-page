'use client'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatPounds, getCpaColour } from '@/lib/utils'

interface KpiData {
  readonly spendToday: number
  readonly spendThisWeek: number
  readonly conversionsThisWeek: number
  readonly avgCpaThisWeek: number
  readonly activeCampaigns: number
  readonly pendingApprovals: number
}

interface KpiCardsProps {
  readonly data: KpiData
}

export function KpiCards({ data }: KpiCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Card>
        <CardHeader>
          <CardDescription>Total Spend (7d)</CardDescription>
          <CardTitle className="text-2xl">
            {formatPounds(data.spendThisWeek)}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            Today: {formatPounds(data.spendToday)}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardDescription>Conversions (7d)</CardDescription>
          <CardTitle className="text-2xl">
            {data.conversionsThisWeek}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            This week
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardDescription>Avg CPA (7d)</CardDescription>
          <CardTitle className={`text-2xl ${getCpaColour(data.avgCpaThisWeek)}`}>
            {formatPounds(data.avgCpaThisWeek)}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            {data.avgCpaThisWeek > 0
              ? `Per conversion`
              : 'No conversions yet'}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardDescription>Active Campaigns</CardDescription>
          <CardTitle className="flex items-center gap-2 text-2xl">
            {data.activeCampaigns}
            {data.pendingApprovals > 0 && (
              <Badge variant="secondary" className="bg-amber-100 text-amber-800 text-xs">
                {data.pendingApprovals} pending
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            Running campaigns
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
