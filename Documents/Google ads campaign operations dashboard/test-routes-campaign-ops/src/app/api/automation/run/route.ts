import { NextResponse } from 'next/server'
import { requireAdmin, unauthorizedResponse } from '@/lib/auth/guard'
import { runAutomationEngine } from '@/lib/automation/engine'

export async function POST(req: Request) {
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
    const result = await runAutomationEngine()

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
