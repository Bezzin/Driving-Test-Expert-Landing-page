import { NextResponse } from 'next/server'
import { requireAdmin, unauthorizedResponse } from '@/lib/auth/guard'
import { createAdminClient } from '@/lib/supabase/server'

interface ParsedCentre {
  name: string
  slug: string
  region: string
  latitude: number
  longitude: number
}

function parseCsv(text: string): { rows: ParsedCentre[]; errors: string[] } {
  const lines = text.trim().split('\n')
  const errors: string[] = []
  const rows: ParsedCentre[] = []

  if (lines.length < 2) {
    errors.push('CSV must have a header row and at least one data row')
    return { rows, errors }
  }

  const header = lines[0].toLowerCase().split(',').map((h) => h.trim())
  const nameIdx = header.indexOf('name')
  const slugIdx = header.indexOf('slug')
  const regionIdx = header.indexOf('region')
  const latIdx = header.indexOf('latitude')
  const lngIdx = header.indexOf('longitude')

  if (nameIdx === -1 || slugIdx === -1 || regionIdx === -1) {
    errors.push('CSV must have columns: name, slug, region')
    return { rows, errors }
  }

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim()
    if (!line) continue

    const cols = line.split(',').map((c) => c.trim())
    const name = cols[nameIdx] ?? ''
    const slug = cols[slugIdx] ?? ''
    const region = cols[regionIdx] ?? ''

    if (!name || !slug || !region) {
      errors.push(`Row ${i + 1}: missing required fields (name, slug, region)`)
      continue
    }

    const latitude = latIdx !== -1 ? parseFloat(cols[latIdx] ?? '0') : 0
    const longitude = lngIdx !== -1 ? parseFloat(cols[lngIdx] ?? '0') : 0

    if (latIdx !== -1 && isNaN(latitude)) {
      errors.push(`Row ${i + 1}: invalid latitude`)
      continue
    }

    if (lngIdx !== -1 && isNaN(longitude)) {
      errors.push(`Row ${i + 1}: invalid longitude`)
      continue
    }

    rows.push({ name, slug, region, latitude, longitude })
  }

  return { rows, errors }
}

export async function POST(req: Request) {
  try {
    await requireAdmin()
  } catch {
    return unauthorizedResponse()
  }

  try {
    let csvText: string

    const contentType = req.headers.get('content-type') ?? ''

    if (contentType.includes('multipart/form-data')) {
      const formData = await req.formData()
      const file = formData.get('file')

      if (!file || !(file instanceof File)) {
        return NextResponse.json(
          { success: false, error: 'No file provided in form data' },
          { status: 400 }
        )
      }

      csvText = await file.text()
    } else {
      csvText = await req.text()
    }

    if (!csvText.trim()) {
      return NextResponse.json(
        { success: false, error: 'Empty CSV body' },
        { status: 400 }
      )
    }

    const { rows, errors } = parseCsv(csvText)

    if (rows.length === 0) {
      return NextResponse.json(
        {
          success: false,
          error: 'No valid rows to import',
          data: { imported: 0, errors },
        },
        { status: 400 }
      )
    }

    const supabase = createAdminClient()

    const upsertData = rows.map((row) => ({
      name: row.name,
      slug: row.slug,
      region: row.region,
      latitude: row.latitude,
      longitude: row.longitude,
    }))

    const { error: upsertError } = await supabase
      .from('co_test_centres')
      .upsert(upsertData, { onConflict: 'slug' })

    if (upsertError) {
      errors.push(`Database upsert failed: ${upsertError.message}`)
      return NextResponse.json(
        {
          success: false,
          error: 'Import failed',
          data: { imported: 0, errors },
        },
        { status: 500 }
      )
    }

    return NextResponse.json({
      success: true,
      data: { imported: rows.length, errors },
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
