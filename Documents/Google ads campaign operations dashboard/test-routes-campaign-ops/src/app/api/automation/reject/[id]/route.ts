import { NextResponse } from 'next/server'
import { requireAdmin, unauthorizedResponse } from '@/lib/auth/guard'
import { createAdminClient } from '@/lib/supabase/server'

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    await requireAdmin()
  } catch {
    return unauthorizedResponse()
  }

  try {
    const { id } = await params
    const supabase = createAdminClient()

    // Fetch the log entry to verify it exists and is pending
    const { data: logEntry, error: logError } = await supabase
      .from('co_automation_log')
      .select('id, status')
      .eq('id', id)
      .single()

    if (logError || !logEntry) {
      return NextResponse.json(
        { success: false, error: `Log entry not found: ${id}` },
        { status: 404 }
      )
    }

    if (logEntry.status !== 'pending_approval') {
      return NextResponse.json(
        {
          success: false,
          error: `Log entry is not pending approval (current status: ${logEntry.status})`,
        },
        { status: 400 }
      )
    }

    // Update status to rejected
    const { error: updateError } = await supabase
      .from('co_automation_log')
      .update({ status: 'rejected' })
      .eq('id', id)

    if (updateError) {
      return NextResponse.json(
        {
          success: false,
          error: `Failed to update status: ${updateError.message}`,
        },
        { status: 500 }
      )
    }

    return NextResponse.json({ success: true })
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
