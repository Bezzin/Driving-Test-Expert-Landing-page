import { NextResponse, type NextRequest } from 'next/server'
import { requireAdmin, unauthorizedResponse } from '@/lib/auth/guard'
import { syncPerformance } from '@/lib/google-ads/performance-sync'

export async function GET(req: NextRequest) {
  const authHeader = req.headers.get('authorization')

  if (authHeader === `Bearer ${process.env.CRON_SECRET}`) {
    // Cron job, proceed
  } else {
    try {
      await requireAdmin()
    } catch {
      return unauthorizedResponse()
    }
  }

  try {
    const date = req.nextUrl.searchParams.get('date') ?? undefined
    const result = await syncPerformance(date)

    return NextResponse.json({ success: true, data: result })
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
