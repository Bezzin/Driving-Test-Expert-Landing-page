import { NextResponse } from 'next/server'
import { requireAdmin, unauthorizedResponse } from '@/lib/auth/guard'
import { pushCampaignForCentre } from '@/lib/google-ads/campaign-push'
import type { PushResult } from '@/lib/google-ads/campaign-push'

export async function POST(req: Request) {
  try {
    await requireAdmin()
  } catch {
    return unauthorizedResponse()
  }

  try {
    const body = await req.json()
    const centreIds = body?.centreIds

    if (!Array.isArray(centreIds) || centreIds.length === 0) {
      return NextResponse.json(
        { success: false, error: 'centreIds must be a non-empty array' },
        { status: 400 }
      )
    }

    const pushed: PushResult[] = []
    const errors: string[] = []

    for (const centreId of centreIds) {
      try {
        const result = await pushCampaignForCentre(centreId)
        pushed.push(result)
      } catch (err) {
        errors.push(
          `${centreId}: ${err instanceof Error ? err.message : String(err)}`
        )
      }
    }

    return NextResponse.json({
      success: true,
      data: { pushed, errors },
    })
  } catch (err) {
    return NextResponse.json(
      {
        success: false,
        error: err instanceof Error ? err.message : 'Internal server error',
      },
      { status: 500 }
    )
  }
}
