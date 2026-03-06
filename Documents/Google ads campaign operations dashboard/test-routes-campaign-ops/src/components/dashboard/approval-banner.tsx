'use client'

import Link from 'next/link'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

interface ApprovalBannerProps {
  readonly count: number
}

export function ApprovalBanner({ count }: ApprovalBannerProps) {
  if (count <= 0) {
    return null
  }

  return (
    <Alert className="border-amber-300 bg-amber-50 text-amber-900">
      <AlertTitle className="font-semibold">
        Pending Approvals
      </AlertTitle>
      <AlertDescription>
        You have {count} pending approval{count !== 1 ? 's' : ''}.{' '}
        <Link
          href="/dashboard/automation"
          className="font-medium underline underline-offset-4 hover:text-amber-700"
        >
          Review now
        </Link>
      </AlertDescription>
    </Alert>
  )
}
