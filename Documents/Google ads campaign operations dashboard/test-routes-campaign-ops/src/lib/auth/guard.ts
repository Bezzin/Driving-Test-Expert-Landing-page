import { createServerSessionClient } from '@/lib/supabase/middleware'

const ADMIN_EMAIL = process.env.ADMIN_EMAIL!

export async function requireAdmin() {
  const supabase = await createServerSessionClient()
  const { data: { user }, error } = await supabase.auth.getUser()

  if (error || !user || user.email !== ADMIN_EMAIL) {
    throw new Error('Unauthorized')
  }

  return user
}

export function unauthorizedResponse() {
  return Response.json({ error: 'Unauthorized' }, { status: 401 })
}
