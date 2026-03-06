# Campaign Operations Dashboard - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Full-featured Google Ads campaign operations dashboard managing 300+ UK driving test centre campaigns with automated rules, performance tracking, and approval workflows.

**Architecture:** Next.js 14 App Router with Supabase (shared instance), Google Ads API integration with dry-run mode, Vercel Cron for daily automation. One campaign per test centre. Auto-tiering from DVSA test volume data.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Recharts, Supabase (@supabase/ssr + @supabase/supabase-js), google-ads-api, pnpm, Vercel

**Supabase Project:** `zpfkvhnfbbimsfghmjiz` (Test Routes Expert, eu-central-1)

**Existing app tables (READ ONLY):**
- `test_centers` (359 rows): id (text PK), name, address, city, postcode, location (geography), route_count (int)
- `routes` (5,837 rows): id (uuid PK), test_center_id (text FK), name, route_number, geojson, etc.

**DVSA data source:** `C:\Users\Nathaniel\Documents\DTE SITE\dte-next\data\dvsa\centres.json` (322 centres with testsConductedTotal, passRateOverall, slug, region, latitude, longitude, difficultyRank)

---

## Phase 1: Project Init & Database

### Task 1: Scaffold Next.js project

**Step 1: Create the project**

Run:
```bash
cd "c:/Users/Nathaniel/Documents/Google ads campaign operations dashboard"
pnpm create next-app@latest test-routes-campaign-ops --typescript --tailwind --eslint --app --src-dir --use-pnpm
```

Accept defaults when prompted.

**Step 2: Install dependencies**

Run:
```bash
cd test-routes-campaign-ops
pnpm add @supabase/supabase-js @supabase/ssr google-ads-api recharts zod
pnpm add -D @types/node
```

**Step 3: Install shadcn/ui**

Run:
```bash
pnpm dlx shadcn@latest init -d
pnpm dlx shadcn@latest add button card table input label badge tabs dialog select dropdown-menu toast sheet separator switch textarea alert
```

**Step 4: Create .env.local.example**

Create: `test-routes-campaign-ops/.env.local.example`

```env
# Public (safe to expose in browser)
NEXT_PUBLIC_SUPABASE_URL=https://zpfkvhnfbbimsfghmjiz.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=

# Secret (server-side ONLY - NEVER prefix with NEXT_PUBLIC_)
SUPABASE_SERVICE_ROLE_KEY=
ADMIN_EMAIL=

# Google Ads (server-side only)
GOOGLE_ADS_CLIENT_ID=
GOOGLE_ADS_CLIENT_SECRET=
GOOGLE_ADS_REFRESH_TOKEN=
GOOGLE_ADS_DEVELOPER_TOKEN=
GOOGLE_ADS_CUSTOMER_ID=
GOOGLE_ADS_LOGIN_CUSTOMER_ID=

# Feature flags
DRY_RUN=true

# Notifications
DISCORD_WEBHOOK_URL=

# Cron secret (set by Vercel automatically)
CRON_SECRET=
```

**Step 5: Create .env.local from example**

Copy `.env.local.example` to `.env.local` and fill in `NEXT_PUBLIC_SUPABASE_URL`. Other values added later.

**Step 6: Create vercel.json**

Create: `test-routes-campaign-ops/vercel.json`

```json
{
  "crons": [
    {
      "path": "/api/campaigns/sync",
      "schedule": "0 6 * * *"
    },
    {
      "path": "/api/automation/run",
      "schedule": "0 7 * * *"
    }
  ]
}
```

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: scaffold Next.js project with dependencies and config"
```

---

### Task 2: Supabase migration - create co_ tables

**Step 1: Run migration via Supabase MCP**

Apply the following migration using `apply_migration` on project `zpfkvhnfbbimsfghmjiz`:

```sql
-- ============================================================
-- Campaign Operations Tables
-- All prefixed co_ to distinguish from app tables
-- ============================================================

-- co_test_centres: master list enriched with DVSA data
create table co_test_centres (
  id uuid primary key default gen_random_uuid(),
  app_test_center_id text,
  name text not null,
  slug text unique not null,
  region text,
  dvsa_id text,
  latitude numeric,
  longitude numeric,
  route_count integer default 0,
  has_landing_page boolean default true,
  landing_page_url text,
  pass_rate numeric,
  tests_conducted integer default 0,
  difficulty_rank integer,
  estimated_monthly_searches integer,
  priority_tier text default 'unranked'
    check (priority_tier in ('tier_1', 'tier_2', 'tier_3', 'unranked')),
  status text default 'pending'
    check (status in ('pending', 'active', 'paused', 'excluded')),
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- co_campaigns: one Google Ads campaign per centre
create table co_campaigns (
  id uuid primary key default gen_random_uuid(),
  test_centre_id uuid references co_test_centres(id),
  google_campaign_id text,
  google_ad_group_id text,
  campaign_name text not null,
  campaign_type text default 'location_specific'
    check (campaign_type in ('location_specific', 'generic_national', 'practice_feature')),
  status text default 'draft'
    check (status in ('draft', 'pending_review', 'active', 'paused', 'removed')),
  daily_budget_micros bigint,
  target_cpa_micros bigint,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- co_keywords: keywords per campaign
create table co_keywords (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid references co_campaigns(id),
  keyword_text text not null,
  match_type text not null
    check (match_type in ('EXACT', 'PHRASE')),
  google_keyword_id text,
  status text default 'active',
  created_at timestamptz default now()
);

-- co_ad_copy: ad variants per campaign
create table co_ad_copy (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid references co_campaigns(id),
  headline_1 text not null,
  headline_2 text,
  headline_3 text,
  headline_4 text,
  headline_5 text,
  headline_6 text,
  description_1 text not null,
  description_2 text,
  final_url text not null,
  path_1 text,
  path_2 text,
  variant_label text,
  google_ad_id text,
  status text default 'draft',
  created_at timestamptz default now()
);

-- co_daily_performance: synced from Google Ads API daily
create table co_daily_performance (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid references co_campaigns(id),
  date date not null,
  impressions integer default 0,
  clicks integer default 0,
  cost_micros bigint default 0,
  conversions numeric default 0,
  conversion_value_micros bigint default 0,
  ctr numeric generated always as (
    case when impressions > 0 then clicks::numeric / impressions else 0 end
  ) stored,
  cpa_micros bigint generated always as (
    case when conversions > 0 then (cost_micros / conversions)::bigint else 0 end
  ) stored,
  avg_cpc_micros bigint generated always as (
    case when clicks > 0 then (cost_micros / clicks)::bigint else 0 end
  ) stored,
  synced_at timestamptz default now(),
  unique(campaign_id, date)
);

-- co_automation_rules: configurable rules
create table co_automation_rules (
  id uuid primary key default gen_random_uuid(),
  rule_name text not null,
  rule_type text not null
    check (rule_type in ('pause', 'scale_up', 'scale_down', 'alert', 'launch')),
  conditions jsonb not null,
  actions jsonb not null,
  is_active boolean default true,
  requires_approval boolean default false,
  created_at timestamptz default now()
);

-- co_automation_log: audit trail
create table co_automation_log (
  id uuid primary key default gen_random_uuid(),
  rule_id uuid references co_automation_rules(id),
  campaign_id uuid references co_campaigns(id),
  action_taken text not null,
  details jsonb,
  status text default 'executed'
    check (status in ('executed', 'pending_approval', 'approved', 'rejected')),
  created_at timestamptz default now()
);

-- co_negative_keywords: shared lists
create table co_negative_keywords (
  id uuid primary key default gen_random_uuid(),
  keyword_text text not null,
  list_name text default 'global',
  created_at timestamptz default now()
);
```

**Step 2: Verify tables created**

Run SQL:
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'co_%' ORDER BY tablename;
```

Expected: 8 tables listed.

---

### Task 3: RLS policies on all co_ tables

**Step 1: Apply RLS migration**

```sql
-- ============================================================
-- RLS POLICIES FOR ALL CAMPAIGN OPS TABLES
-- Admin-only access. App users (anon key) get ZERO access.
-- ============================================================

-- co_test_centres
alter table co_test_centres enable row level security;
create policy "admin_full_access" on co_test_centres
  for all using (
    auth.uid() is not null
    and (select email from auth.users where id = auth.uid()) = current_setting('app.admin_email', true)
  );

-- co_campaigns
alter table co_campaigns enable row level security;
create policy "admin_full_access" on co_campaigns
  for all using (
    auth.uid() is not null
    and (select email from auth.users where id = auth.uid()) = current_setting('app.admin_email', true)
  );

-- co_keywords
alter table co_keywords enable row level security;
create policy "admin_full_access" on co_keywords
  for all using (
    auth.uid() is not null
    and (select email from auth.users where id = auth.uid()) = current_setting('app.admin_email', true)
  );

-- co_ad_copy
alter table co_ad_copy enable row level security;
create policy "admin_full_access" on co_ad_copy
  for all using (
    auth.uid() is not null
    and (select email from auth.users where id = auth.uid()) = current_setting('app.admin_email', true)
  );

-- co_daily_performance
alter table co_daily_performance enable row level security;
create policy "admin_full_access" on co_daily_performance
  for all using (
    auth.uid() is not null
    and (select email from auth.users where id = auth.uid()) = current_setting('app.admin_email', true)
  );

-- co_automation_rules
alter table co_automation_rules enable row level security;
create policy "admin_full_access" on co_automation_rules
  for all using (
    auth.uid() is not null
    and (select email from auth.users where id = auth.uid()) = current_setting('app.admin_email', true)
  );

-- co_automation_log
alter table co_automation_log enable row level security;
create policy "admin_full_access" on co_automation_log
  for all using (
    auth.uid() is not null
    and (select email from auth.users where id = auth.uid()) = current_setting('app.admin_email', true)
  );

-- co_negative_keywords
alter table co_negative_keywords enable row level security;
create policy "admin_full_access" on co_negative_keywords
  for all using (
    auth.uid() is not null
    and (select email from auth.users where id = auth.uid()) = current_setting('app.admin_email', true)
  );
```

**Step 2: Verify RLS**

Run SQL:
```sql
SELECT tablename, rowsecurity,
  case when rowsecurity then 'SECURE' else 'EXPOSED' end as status
FROM pg_tables
WHERE schemaname = 'public' AND tablename LIKE 'co_%'
ORDER BY tablename;
```

Expected: All 8 tables show `rowsecurity = true`.

---

### Task 4: Seed test centres from existing data + DVSA

**Step 1: Create seed script**

Create: `test-routes-campaign-ops/scripts/seed-test-centres.ts`

This script:
1. Reads DVSA `centres.json` (322 centres with testsConductedTotal, passRateOverall, slug, region, lat/lng, difficultyRank)
2. Queries existing `test_centers` table from Supabase (359 rows with id, name, route_count)
3. Matches by name (fuzzy) or slug
4. Calculates priority tiers from testsConductedTotal:
   - Sort all centres by testsConductedTotal descending
   - Top 15% -> tier_1 (~48 centres)
   - Next 30% -> tier_2 (~97 centres)
   - Remaining -> tier_3
5. Inserts into `co_test_centres` with:
   - `app_test_center_id` = matching test_centers.id (for cross-referencing routes)
   - `route_count` from test_centers.route_count
   - `has_landing_page` = true (all 322 are live)
   - `landing_page_url` = `https://drivingtestexpert.com/test-centres/{slug}/`
   - All DVSA fields mapped

```typescript
import { createClient } from '@supabase/supabase-js'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!

const supabase = createClient(supabaseUrl, supabaseServiceKey)

interface DvsaCentre {
  name: string
  slug: string
  region: string
  passRateOverall: number
  testsConductedTotal: number
  difficultyRank: number
  latitude: number
  longitude: number
}

interface AppTestCenter {
  id: string
  name: string
  route_count: number
}

function calculateTiers(centres: DvsaCentre[]): Map<string, string> {
  const sorted = [...centres].sort((a, b) => b.testsConductedTotal - a.testsConductedTotal)
  const total = sorted.length
  const tier1Cutoff = Math.ceil(total * 0.15)
  const tier2Cutoff = Math.ceil(total * 0.45)

  const tiers = new Map<string, string>()
  sorted.forEach((centre, index) => {
    if (index < tier1Cutoff) {
      tiers.set(centre.slug, 'tier_1')
    } else if (index < tier2Cutoff) {
      tiers.set(centre.slug, 'tier_2')
    } else {
      tiers.set(centre.slug, 'tier_3')
    }
  })
  return tiers
}

function normalise(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]/g, '')
}

function matchAppCentre(
  dvsaName: string,
  dvsaSlug: string,
  appCentres: AppTestCenter[]
): AppTestCenter | undefined {
  const normDvsa = normalise(dvsaName)
  return appCentres.find(ac => {
    const normApp = normalise(ac.name)
    return normApp === normDvsa || ac.id === dvsaSlug
  })
}

async function main() {
  // Read DVSA data
  const dvsaPath = resolve('C:/Users/Nathaniel/Documents/DTE SITE/dte-next/data/dvsa/centres.json')
  const dvsaCentres: DvsaCentre[] = JSON.parse(readFileSync(dvsaPath, 'utf-8'))

  // Fetch app test_centers
  const { data: appCentres, error } = await supabase
    .from('test_centers')
    .select('id, name, route_count')

  if (error) {
    console.error('Failed to fetch test_centers:', error)
    process.exit(1)
  }

  // Calculate tiers
  const tiers = calculateTiers(dvsaCentres)

  // Build insert rows
  const rows = dvsaCentres.map(dvsa => {
    const appMatch = matchAppCentre(dvsa.name, dvsa.slug, appCentres as AppTestCenter[])

    return {
      app_test_center_id: appMatch?.id ?? null,
      name: dvsa.name,
      slug: dvsa.slug,
      region: dvsa.region,
      latitude: dvsa.latitude,
      longitude: dvsa.longitude,
      route_count: appMatch?.route_count ?? 0,
      has_landing_page: true,
      landing_page_url: `https://drivingtestexpert.com/test-centres/${dvsa.slug}/`,
      pass_rate: dvsa.passRateOverall,
      tests_conducted: dvsa.testsConductedTotal,
      difficulty_rank: dvsa.difficultyRank,
      priority_tier: tiers.get(dvsa.slug) ?? 'unranked',
      status: 'pending' as const,
    }
  })

  // Insert in batches of 50
  for (let i = 0; i < rows.length; i += 50) {
    const batch = rows.slice(i, i + 50)
    const { error: insertError } = await supabase
      .from('co_test_centres')
      .upsert(batch, { onConflict: 'slug' })

    if (insertError) {
      console.error(`Failed to insert batch ${i}:`, insertError)
      process.exit(1)
    }
    console.log(`Inserted batch ${i + 1}-${Math.min(i + 50, rows.length)}`)
  }

  // Summary
  const tier1 = rows.filter(r => r.priority_tier === 'tier_1').length
  const tier2 = rows.filter(r => r.priority_tier === 'tier_2').length
  const tier3 = rows.filter(r => r.priority_tier === 'tier_3').length
  const matched = rows.filter(r => r.app_test_center_id !== null).length

  console.log(`\nSeeded ${rows.length} centres:`)
  console.log(`  Tier 1: ${tier1}`)
  console.log(`  Tier 2: ${tier2}`)
  console.log(`  Tier 3: ${tier3}`)
  console.log(`  Matched to app: ${matched}/${rows.length}`)
}

main()
```

**Step 2: Run seed script**

```bash
cd test-routes-campaign-ops
pnpm tsx scripts/seed-test-centres.ts
```

**Step 3: Verify**

Run SQL:
```sql
SELECT priority_tier, count(*) FROM co_test_centres GROUP BY priority_tier ORDER BY priority_tier;
```

Expected: ~48 tier_1, ~97 tier_2, ~177 tier_3.

**Step 4: Commit**

```bash
git add scripts/seed-test-centres.ts
git commit -m "feat: add seed script for test centres with DVSA data and auto-tiering"
```

---

### Task 5: Seed default automation rules and negative keywords

**Step 1: Create seed script**

Create: `test-routes-campaign-ops/scripts/seed-automation-rules.ts`

```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

const defaultRules = [
  {
    rule_name: 'Pause high CPA campaigns',
    rule_type: 'pause',
    conditions: { cpa_above_micros: 15_000_000, min_spend_micros: 20_000_000, lookback_days: 7 },
    actions: { set_status: 'paused' },
    is_active: true,
    requires_approval: false,
  },
  {
    rule_name: 'Scale up winners',
    rule_type: 'scale_up',
    conditions: { cpa_below_micros: 6_000_000, min_conversions: 5, lookback_days: 7 },
    actions: { budget_multiplier: 1.5, max_daily_budget_micros: 20_000_000 },
    is_active: true,
    requires_approval: false,
  },
  {
    rule_name: 'Scale down underperformers',
    rule_type: 'scale_down',
    conditions: { cpa_above_micros: 10_000_000, min_spend_micros: 15_000_000, lookback_days: 7 },
    actions: { budget_multiplier: 0.5, min_daily_budget_micros: 3_000_000 },
    is_active: true,
    requires_approval: false,
  },
  {
    rule_name: 'Alert on zero conversions',
    rule_type: 'alert',
    conditions: { conversions_equals: 0, min_spend_micros: 30_000_000, lookback_days: 14 },
    actions: { notify: true },
    is_active: true,
    requires_approval: true,
  },
  {
    rule_name: 'Auto-launch tier 1 centres',
    rule_type: 'launch',
    conditions: { priority_tier: 'tier_1', status: 'pending', has_landing_page: true },
    actions: { create_campaign: true, initial_budget_micros: 5_000_000 },
    is_active: true,
    requires_approval: true,
  },
]

const negativeKeywords = [
  'driving instructor', 'driving lessons', 'book driving test',
  'theory test', 'DVSA', 'automatic instructor', 'manual instructor',
  'intensive course', 'crash course', 'driving school',
  'driving test cancellations', 'driving test tips',
]

async function main() {
  const { error: rulesError } = await supabase
    .from('co_automation_rules')
    .insert(defaultRules)

  if (rulesError) {
    console.error('Failed to seed rules:', rulesError)
    process.exit(1)
  }
  console.log(`Seeded ${defaultRules.length} automation rules`)

  const negRows = negativeKeywords.map(kw => ({
    keyword_text: kw,
    list_name: 'global',
  }))

  const { error: nkError } = await supabase
    .from('co_negative_keywords')
    .insert(negRows)

  if (nkError) {
    console.error('Failed to seed negative keywords:', nkError)
    process.exit(1)
  }
  console.log(`Seeded ${negativeKeywords.length} negative keywords`)
}

main()
```

**Step 2: Run**

```bash
pnpm tsx scripts/seed-automation-rules.ts
```

**Step 3: Commit**

```bash
git add scripts/seed-automation-rules.ts
git commit -m "feat: add seed script for automation rules and negative keywords"
```

---

## Phase 2: Auth & Supabase Clients

### Task 6: Supabase client setup (browser + server + middleware)

**Files to create:**
- `src/lib/supabase/client.ts` — browser client (anon key, auth only)
- `src/lib/supabase/server.ts` — server client (service role key)
- `src/lib/supabase/middleware.ts` — session client for auth checks

**Step 1: Browser client**

Create: `test-routes-campaign-ops/src/lib/supabase/client.ts`

```typescript
import { createBrowserClient } from '@supabase/ssr'

export const createClient = () =>
  createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
```

**Step 2: Server admin client**

Create: `test-routes-campaign-ops/src/lib/supabase/server.ts`

```typescript
import { createClient as createSupabaseClient } from '@supabase/supabase-js'

export const createAdminClient = () =>
  createSupabaseClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } }
  )
```

**Step 3: Middleware session client**

Create: `test-routes-campaign-ops/src/lib/supabase/middleware.ts`

```typescript
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export const createServerSessionClient = async () => {
  const cookieStore = await cookies()
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          )
        },
      },
    }
  )
}
```

**Step 4: Commit**

```bash
git add src/lib/supabase/
git commit -m "feat: add Supabase client setup (browser, server, middleware)"
```

---

### Task 7: Auth guard and middleware

**Step 1: Create auth guard**

Create: `test-routes-campaign-ops/src/lib/auth/guard.ts`

```typescript
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
```

**Step 2: Create Next.js middleware for auth redirect**

Create: `test-routes-campaign-ops/src/middleware.ts`

```typescript
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => {
            request.cookies.set(name, value)
            supabaseResponse.cookies.set(name, value, options)
          })
        },
      },
    }
  )

  const { data: { user } } = await supabase.auth.getUser()

  // Redirect unauthenticated users to login
  if (!user && !request.nextUrl.pathname.startsWith('/login') && !request.nextUrl.pathname.startsWith('/auth')) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }

  // Redirect authenticated users away from login
  if (user && request.nextUrl.pathname.startsWith('/login')) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  return supabaseResponse
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api/).*)'],
}
```

**Step 3: Commit**

```bash
git add src/lib/auth/ src/middleware.ts
git commit -m "feat: add auth guard and middleware for session management"
```

---

### Task 8: Login page

**Step 1: Create auth callback route**

Create: `test-routes-campaign-ops/src/app/auth/callback/route.ts`

```typescript
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { NextResponse, type NextRequest } from 'next/server'

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')

  if (code) {
    const cookieStore = await cookies()
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll()
          },
          setAll(cookiesToSet) {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            )
          },
        },
      }
    )

    const { error } = await supabase.auth.exchangeCodeForSession(code)
    if (!error) {
      return NextResponse.redirect(`${origin}/dashboard`)
    }
  }

  return NextResponse.redirect(`${origin}/login?error=auth`)
}
```

**Step 2: Create login page**

Create: `test-routes-campaign-ops/src/app/login/page.tsx`

```tsx
'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    const supabase = createClient()
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    })

    if (error) {
      setError(error.message)
    } else {
      setSent(true)
    }
    setLoading(false)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Campaign Operations</CardTitle>
          <CardDescription>Test Routes Expert - Admin Dashboard</CardDescription>
        </CardHeader>
        <CardContent>
          {sent ? (
            <p className="text-sm text-green-600">
              Check your email for a magic link to sign in.
            </p>
          ) : (
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? 'Sending...' : 'Send Magic Link'}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
```

**Step 3: Root page redirect**

Create: `test-routes-campaign-ops/src/app/page.tsx`

```tsx
import { redirect } from 'next/navigation'

export default function Home() {
  redirect('/dashboard')
}
```

**Step 4: Commit**

```bash
git add src/app/auth/ src/app/login/ src/app/page.tsx
git commit -m "feat: add magic link login and auth callback"
```

---

## Phase 3: Core Libraries

### Task 9: Utility functions

**Step 1: Create utils**

Create: `test-routes-campaign-ops/src/lib/utils.ts`

```typescript
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

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
```

**Step 2: Commit**

```bash
git add src/lib/utils.ts
git commit -m "feat: add utility functions for micros conversion and formatting"
```

---

### Task 10: Discord notification utility

Create: `test-routes-campaign-ops/src/lib/discord.ts`

```typescript
interface DiscordEmbed {
  title: string
  description?: string
  color?: number
  fields?: Array<{ name: string; value: string; inline?: boolean }>
  timestamp?: string
}

export async function sendDiscordNotification(
  content: string,
  embeds?: DiscordEmbed[]
): Promise<void> {
  const webhookUrl = process.env.DISCORD_WEBHOOK_URL
  if (!webhookUrl) {
    console.log('[Discord] No webhook URL configured, skipping notification')
    console.log('[Discord] Message:', content)
    return
  }

  const body: Record<string, unknown> = { content }
  if (embeds) {
    body.embeds = embeds
  }

  const response = await fetch(webhookUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    console.error(`[Discord] Failed to send: ${response.status} ${response.statusText}`)
  }
}

// Colours for embeds
export const DISCORD_COLOURS = {
  success: 0x22c55e,  // green
  warning: 0xf59e0b,  // amber
  danger: 0xef4444,   // red
  info: 0x3b82f6,     // blue
}
```

Commit:
```bash
git add src/lib/discord.ts
git commit -m "feat: add Discord webhook notification utility"
```

---

### Task 11: Google Ads client with dry-run mode

**Step 1: Create types**

Create: `test-routes-campaign-ops/src/lib/google-ads/types.ts`

```typescript
export interface GeneratedCampaign {
  centreName: string
  centreSlug: string
  campaignName: string
  dailyBudgetMicros: bigint
  keywords: GeneratedKeyword[]
  ads: GeneratedAd[]
  negativeKeywords: string[]
  finalUrl: string
}

export interface GeneratedKeyword {
  text: string
  matchType: 'EXACT' | 'PHRASE'
}

export interface GeneratedAd {
  headlines: string[]
  descriptions: string[]
  finalUrl: string
  path1?: string
  path2?: string
  variantLabel: string
}

export interface GoogleAdsConfig {
  clientId: string
  clientSecret: string
  refreshToken: string
  developerToken: string
  customerId: string
  loginCustomerId?: string
}

export interface SyncResult {
  campaignsUpdated: number
  performanceRows: number
  errors: string[]
}
```

**Step 2: Create client**

Create: `test-routes-campaign-ops/src/lib/google-ads/client.ts`

```typescript
import { GoogleAdsApi } from 'google-ads-api'
import type { GoogleAdsConfig } from './types'

let clientInstance: GoogleAdsApi | null = null

export function getGoogleAdsClient(): GoogleAdsApi | null {
  if (process.env.DRY_RUN === 'true') {
    return null
  }

  if (clientInstance) {
    return clientInstance
  }

  const config: GoogleAdsConfig = {
    clientId: process.env.GOOGLE_ADS_CLIENT_ID!,
    clientSecret: process.env.GOOGLE_ADS_CLIENT_SECRET!,
    refreshToken: process.env.GOOGLE_ADS_REFRESH_TOKEN!,
    developerToken: process.env.GOOGLE_ADS_DEVELOPER_TOKEN!,
    customerId: process.env.GOOGLE_ADS_CUSTOMER_ID!,
    loginCustomerId: process.env.GOOGLE_ADS_LOGIN_CUSTOMER_ID,
  }

  clientInstance = new GoogleAdsApi({
    client_id: config.clientId,
    client_secret: config.clientSecret,
    developer_token: config.developerToken,
  })

  return clientInstance
}

export function getCustomer() {
  const client = getGoogleAdsClient()
  if (!client) return null

  return client.Customer({
    customer_id: process.env.GOOGLE_ADS_CUSTOMER_ID!,
    login_customer_id: process.env.GOOGLE_ADS_LOGIN_CUSTOMER_ID,
    refresh_token: process.env.GOOGLE_ADS_REFRESH_TOKEN!,
  })
}

export function isDryRun(): boolean {
  return process.env.DRY_RUN === 'true'
}
```

**Step 3: Commit**

```bash
git add src/lib/google-ads/
git commit -m "feat: add Google Ads client with dry-run mode"
```

---

### Task 12: Campaign generator

Create: `test-routes-campaign-ops/src/lib/google-ads/campaign-generator.ts`

```typescript
import type { GeneratedCampaign, GeneratedKeyword, GeneratedAd } from './types'

interface CentreInput {
  name: string
  slug: string
  route_count: number
  pass_rate: number | null
  landing_page_url: string | null
}

export function generateKeywords(centreName: string): GeneratedKeyword[] {
  const base = centreName.toLowerCase()
  return [
    { text: `${base} driving test routes`, matchType: 'EXACT' },
    { text: `${base} test routes`, matchType: 'EXACT' },
    { text: `driving test routes ${base}`, matchType: 'EXACT' },
    { text: `${base} driving test route`, matchType: 'EXACT' },
    { text: `${base} driving test routes`, matchType: 'PHRASE' },
    { text: `${base} test routes`, matchType: 'PHRASE' },
    { text: `${base} test centre routes`, matchType: 'PHRASE' },
    { text: `practise driving test ${base}`, matchType: 'PHRASE' },
  ]
}

function truncate(text: string, max: number): string {
  return text.length <= max ? text : text.slice(0, max - 1).trim()
}

export function generateAds(centre: CentreInput): GeneratedAd[] {
  const { name, route_count, pass_rate } = centre
  const finalUrl = centre.landing_page_url ?? `https://drivingtestexpert.com/test-routes-app`

  const routeText = route_count > 0 ? `${route_count} Real Test Routes` : 'Real Test Routes'
  const passRateText = pass_rate ? `${pass_rate.toFixed(0)}% Pass Rate Area` : 'Know Your Routes'

  // Variant A: Navigation focus
  const variantA: GeneratedAd = {
    headlines: [
      truncate(`${name} Test Routes`, 30),
      'Turn-by-Turn Navigation',
      'Pass Your Test First Time',
      truncate(routeText, 30),
      'Practice Real Test Routes',
      'Download Free Today',
    ],
    descriptions: [
      truncate(`Practice the exact routes examiners use at ${name} test centre. Turn-by-turn sat nav guidance on every route.`, 90),
      truncate(`Join 50,000+ UK learners. Real test routes with voice navigation. One free route per centre. Download now.`, 90),
    ],
    finalUrl,
    path1: 'test-routes',
    path2: centre.slug.slice(0, 15),
    variantLabel: 'navigation_focus',
  }

  // Variant B: Practise feature focus
  const variantB: GeneratedAd = {
    headlines: [
      truncate(`${name} Test Routes`, 30),
      'Practise Routes Virtually',
      truncate(passRateText, 30),
      'Virtual Test Route Practice',
      'Beat Test Day Nerves',
      'Try For Free',
    ],
    descriptions: [
      truncate(`Go through ${name} test routes virtually before your test. Interactive practise mode lets you learn every junction.`, 90),
      truncate(`Stop guessing where you'll go. Practise ${name} driving test routes with our virtual walkthrough. Free download.`, 90),
    ],
    finalUrl,
    path1: 'practise',
    path2: centre.slug.slice(0, 15),
    variantLabel: 'practise_focus',
  }

  return [variantA, variantB]
}

export function generateCampaign(
  centre: CentreInput,
  negativeKeywords: string[],
  dailyBudgetMicros: bigint = 5_000_000n
): GeneratedCampaign {
  return {
    centreName: centre.name,
    centreSlug: centre.slug,
    campaignName: `Test Routes - ${centre.name}`,
    dailyBudgetMicros,
    keywords: generateKeywords(centre.name),
    ads: generateAds(centre),
    negativeKeywords,
    finalUrl: centre.landing_page_url ?? 'https://drivingtestexpert.com/test-routes-app',
  }
}
```

Commit:
```bash
git add src/lib/google-ads/campaign-generator.ts
git commit -m "feat: add campaign generator with keyword and ad copy templates"
```

---

### Task 13: Campaign push logic (dry-run + real)

Create: `test-routes-campaign-ops/src/lib/google-ads/campaign-push.ts`

```typescript
import { createAdminClient } from '@/lib/supabase/server'
import { getCustomer, isDryRun } from './client'
import { generateCampaign } from './campaign-generator'
import type { GeneratedCampaign } from './types'

interface PushResult {
  centreSlug: string
  campaignId: string
  dryRun: boolean
  googleCampaignId?: string
  googleAdGroupId?: string
}

async function pushToGoogleAds(config: GeneratedCampaign): Promise<{
  campaignId: string
  adGroupId: string
}> {
  const customer = getCustomer()
  if (!customer) {
    throw new Error('Google Ads client not available')
  }

  // Create campaign
  const campaign = await customer.campaigns.create({
    name: config.campaignName,
    advertising_channel_type: 'SEARCH',
    status: 'PAUSED',
    campaign_budget: {
      amount_micros: Number(config.dailyBudgetMicros),
      delivery_method: 'STANDARD',
    },
    bidding_strategy_type: 'TARGET_CPA',
  })

  // Create ad group
  const adGroup = await customer.adGroups.create({
    campaign: campaign.resource_name,
    name: `${config.campaignName} - Ad Group`,
    status: 'ENABLED',
    type: 'SEARCH_STANDARD',
  })

  return {
    campaignId: campaign.resource_name.split('/').pop()!,
    adGroupId: adGroup.resource_name.split('/').pop()!,
  }
}

export async function pushCampaignForCentre(centreId: string): Promise<PushResult> {
  const supabase = createAdminClient()

  // Fetch centre
  const { data: centre, error: centreError } = await supabase
    .from('co_test_centres')
    .select('*')
    .eq('id', centreId)
    .single()

  if (centreError || !centre) {
    throw new Error(`Centre not found: ${centreId}`)
  }

  // Check for existing campaign
  const { data: existing } = await supabase
    .from('co_campaigns')
    .select('id')
    .eq('test_centre_id', centreId)
    .maybeSingle()

  if (existing) {
    throw new Error(`Campaign already exists for ${centre.name}`)
  }

  // Fetch negative keywords
  const { data: negKws } = await supabase
    .from('co_negative_keywords')
    .select('keyword_text')
    .eq('list_name', 'global')

  const negativeKeywords = (negKws ?? []).map(nk => nk.keyword_text)

  // Generate campaign config
  const config = generateCampaign(
    {
      name: centre.name,
      slug: centre.slug,
      route_count: centre.route_count ?? 0,
      pass_rate: centre.pass_rate,
      landing_page_url: centre.landing_page_url,
    },
    negativeKeywords,
    BigInt(centre.daily_budget_micros ?? 5_000_000)
  )

  let googleCampaignId: string | undefined
  let googleAdGroupId: string | undefined

  if (!isDryRun()) {
    const result = await pushToGoogleAds(config)
    googleCampaignId = result.campaignId
    googleAdGroupId = result.adGroupId
  }

  // Insert campaign record
  const { data: campaign, error: campaignError } = await supabase
    .from('co_campaigns')
    .insert({
      test_centre_id: centreId,
      google_campaign_id: googleCampaignId ?? null,
      google_ad_group_id: googleAdGroupId ?? null,
      campaign_name: config.campaignName,
      campaign_type: 'location_specific',
      status: isDryRun() ? 'draft' : 'active',
      daily_budget_micros: Number(config.dailyBudgetMicros),
    })
    .select()
    .single()

  if (campaignError || !campaign) {
    throw new Error(`Failed to insert campaign: ${campaignError?.message}`)
  }

  // Insert keywords
  const keywordRows = config.keywords.map(kw => ({
    campaign_id: campaign.id,
    keyword_text: kw.text,
    match_type: kw.matchType,
  }))

  await supabase.from('co_keywords').insert(keywordRows)

  // Insert ad copy
  const adRows = config.ads.map(ad => ({
    campaign_id: campaign.id,
    headline_1: ad.headlines[0],
    headline_2: ad.headlines[1] ?? null,
    headline_3: ad.headlines[2] ?? null,
    headline_4: ad.headlines[3] ?? null,
    headline_5: ad.headlines[4] ?? null,
    headline_6: ad.headlines[5] ?? null,
    description_1: ad.descriptions[0],
    description_2: ad.descriptions[1] ?? null,
    final_url: ad.finalUrl,
    path_1: ad.path1 ?? null,
    path_2: ad.path2 ?? null,
    variant_label: ad.variantLabel,
    status: isDryRun() ? 'draft' : 'active',
  }))

  await supabase.from('co_ad_copy').insert(adRows)

  return {
    centreSlug: centre.slug,
    campaignId: campaign.id,
    dryRun: isDryRun(),
    googleCampaignId,
    googleAdGroupId,
  }
}
```

Commit:
```bash
git add src/lib/google-ads/campaign-push.ts
git commit -m "feat: add campaign push logic with dry-run and real API support"
```

---

### Task 14: Performance sync module

Create: `test-routes-campaign-ops/src/lib/google-ads/performance-sync.ts`

```typescript
import { createAdminClient } from '@/lib/supabase/server'
import { getCustomer, isDryRun } from './client'
import type { SyncResult } from './types'

interface PerformanceRow {
  campaign_id: string
  date: string
  impressions: number
  clicks: number
  cost_micros: number
  conversions: number
  conversion_value_micros: number
}

async function fetchFromGoogleAds(date: string): Promise<PerformanceRow[]> {
  const customer = getCustomer()
  if (!customer) return []

  const supabase = createAdminClient()

  // Get all campaigns with google IDs
  const { data: campaigns } = await supabase
    .from('co_campaigns')
    .select('id, google_campaign_id')
    .not('google_campaign_id', 'is', null)

  if (!campaigns?.length) return []

  const googleIdToDbId = new Map(
    campaigns.map(c => [c.google_campaign_id, c.id])
  )

  const results = await customer.report({
    entity: 'campaign',
    attributes: ['campaign.id'],
    metrics: [
      'metrics.impressions',
      'metrics.clicks',
      'metrics.cost_micros',
      'metrics.conversions',
      'metrics.conversions_value',
    ],
    segments: ['segments.date'],
    constraints: {
      'segments.date': date,
    },
  })

  return results
    .filter(r => googleIdToDbId.has(String(r.campaign?.id)))
    .map(r => ({
      campaign_id: googleIdToDbId.get(String(r.campaign?.id))!,
      date,
      impressions: Number(r.metrics?.impressions ?? 0),
      clicks: Number(r.metrics?.clicks ?? 0),
      cost_micros: Number(r.metrics?.cost_micros ?? 0),
      conversions: Number(r.metrics?.conversions ?? 0),
      conversion_value_micros: Number((r.metrics?.conversions_value ?? 0) * 1_000_000),
    }))
}

function generateMockData(campaignIds: string[], date: string): PerformanceRow[] {
  return campaignIds.map(id => ({
    campaign_id: id,
    date,
    impressions: Math.floor(Math.random() * 200) + 10,
    clicks: Math.floor(Math.random() * 30) + 1,
    cost_micros: Math.floor(Math.random() * 10_000_000) + 500_000,
    conversions: Math.floor(Math.random() * 5),
    conversion_value_micros: Math.floor(Math.random() * 20_000_000),
  }))
}

export async function syncPerformance(date?: string): Promise<SyncResult> {
  const supabase = createAdminClient()
  const targetDate = date ?? new Date(Date.now() - 86400000).toISOString().split('T')[0]

  let rows: PerformanceRow[]

  if (isDryRun()) {
    // Generate mock data for all draft/active campaigns
    const { data: campaigns } = await supabase
      .from('co_campaigns')
      .select('id')
      .in('status', ['draft', 'active'])

    rows = generateMockData(
      (campaigns ?? []).map(c => c.id),
      targetDate
    )
  } else {
    rows = await fetchFromGoogleAds(targetDate)
  }

  if (rows.length === 0) {
    return { campaignsUpdated: 0, performanceRows: 0, errors: [] }
  }

  const errors: string[] = []

  // Upsert performance data
  const { error } = await supabase
    .from('co_daily_performance')
    .upsert(rows, { onConflict: 'campaign_id,date' })

  if (error) {
    errors.push(`Upsert error: ${error.message}`)
  }

  return {
    campaignsUpdated: new Set(rows.map(r => r.campaign_id)).size,
    performanceRows: rows.length,
    errors,
  }
}
```

Commit:
```bash
git add src/lib/google-ads/performance-sync.ts
git commit -m "feat: add performance sync with mock data for dry-run mode"
```

---

### Task 15: Automation engine

Create: `test-routes-campaign-ops/src/lib/automation/engine.ts`

```typescript
import { createAdminClient } from '@/lib/supabase/server'
import { sendDiscordNotification, DISCORD_COLOURS } from '@/lib/discord'
import { pushCampaignForCentre } from '@/lib/google-ads/campaign-push'
import { formatPounds } from '@/lib/utils'

interface AutomationResult {
  rulesEvaluated: number
  actionsExecuted: number
  actionsPendingApproval: number
  errors: string[]
}

interface AggregatedPerformance {
  campaign_id: string
  campaign_name: string
  test_centre_id: string
  daily_budget_micros: number
  campaign_status: string
  total_spend_micros: number
  total_conversions: number
  total_clicks: number
  total_impressions: number
  cpa_micros: number
}

async function getAggregatedPerformance(
  lookbackDays: number
): Promise<AggregatedPerformance[]> {
  const supabase = createAdminClient()
  const since = new Date(Date.now() - lookbackDays * 86400000).toISOString().split('T')[0]

  const { data, error } = await supabase.rpc('get_campaign_performance', {
    since_date: since,
  })

  if (error) {
    // Fallback: manual query
    const { data: campaigns } = await supabase
      .from('co_campaigns')
      .select(`
        id, campaign_name, test_centre_id, daily_budget_micros, status,
        co_daily_performance (cost_micros, conversions, clicks, impressions)
      `)
      .in('status', ['active', 'draft'])

    return (campaigns ?? []).map(c => {
      const perfs = (c.co_daily_performance ?? []) as Array<{
        cost_micros: number
        conversions: number
        clicks: number
        impressions: number
      }>
      const totalSpend = perfs.reduce((sum, p) => sum + (p.cost_micros ?? 0), 0)
      const totalConversions = perfs.reduce((sum, p) => sum + (p.conversions ?? 0), 0)

      return {
        campaign_id: c.id,
        campaign_name: c.campaign_name,
        test_centre_id: c.test_centre_id,
        daily_budget_micros: c.daily_budget_micros ?? 5_000_000,
        campaign_status: c.status,
        total_spend_micros: totalSpend,
        total_conversions: totalConversions,
        total_clicks: perfs.reduce((sum, p) => sum + (p.clicks ?? 0), 0),
        total_impressions: perfs.reduce((sum, p) => sum + (p.impressions ?? 0), 0),
        cpa_micros: totalConversions > 0 ? Math.round(totalSpend / totalConversions) : 0,
      }
    })
  }

  return data ?? []
}

export async function runAutomationEngine(): Promise<AutomationResult> {
  const supabase = createAdminClient()
  const result: AutomationResult = {
    rulesEvaluated: 0,
    actionsExecuted: 0,
    actionsPendingApproval: 0,
    errors: [],
  }

  // Load active rules
  const { data: rules, error: rulesError } = await supabase
    .from('co_automation_rules')
    .select('*')
    .eq('is_active', true)

  if (rulesError || !rules) {
    result.errors.push(`Failed to load rules: ${rulesError?.message}`)
    return result
  }

  for (const rule of rules) {
    result.rulesEvaluated++
    const conditions = rule.conditions as Record<string, unknown>
    const actions = rule.actions as Record<string, unknown>
    const lookbackDays = (conditions.lookback_days as number) ?? 7

    try {
      if (rule.rule_type === 'launch') {
        await handleLaunchRule(supabase, rule, conditions, actions, result)
      } else {
        const performances = await getAggregatedPerformance(lookbackDays)
        for (const perf of performances) {
          const matched = evaluateConditions(rule.rule_type, conditions, perf)
          if (matched) {
            await executeAction(supabase, rule, perf, actions, result)
          }
        }
      }
    } catch (err) {
      result.errors.push(`Rule "${rule.rule_name}": ${err}`)
    }
  }

  // Send Discord summary
  await sendDiscordNotification('Automation engine completed', [
    {
      title: 'Automation Run Summary',
      color: result.errors.length > 0 ? DISCORD_COLOURS.warning : DISCORD_COLOURS.success,
      fields: [
        { name: 'Rules Evaluated', value: String(result.rulesEvaluated), inline: true },
        { name: 'Actions Executed', value: String(result.actionsExecuted), inline: true },
        { name: 'Pending Approval', value: String(result.actionsPendingApproval), inline: true },
        { name: 'Errors', value: String(result.errors.length), inline: true },
      ],
    },
  ])

  return result
}

function evaluateConditions(
  ruleType: string,
  conditions: Record<string, unknown>,
  perf: AggregatedPerformance
): boolean {
  switch (ruleType) {
    case 'pause':
      return (
        perf.cpa_micros > (conditions.cpa_above_micros as number) &&
        perf.total_spend_micros >= (conditions.min_spend_micros as number)
      )
    case 'scale_up':
      return (
        perf.cpa_micros > 0 &&
        perf.cpa_micros < (conditions.cpa_below_micros as number) &&
        perf.total_conversions >= (conditions.min_conversions as number)
      )
    case 'scale_down':
      return (
        perf.cpa_micros > (conditions.cpa_above_micros as number) &&
        perf.total_spend_micros >= (conditions.min_spend_micros as number)
      )
    case 'alert':
      return (
        perf.total_conversions === (conditions.conversions_equals as number) &&
        perf.total_spend_micros >= (conditions.min_spend_micros as number)
      )
    default:
      return false
  }
}

async function executeAction(
  supabase: ReturnType<typeof createAdminClient>,
  rule: Record<string, unknown>,
  perf: AggregatedPerformance,
  actions: Record<string, unknown>,
  result: AutomationResult
) {
  const logEntry = {
    rule_id: rule.id as string,
    campaign_id: perf.campaign_id,
    action_taken: '',
    details: {} as Record<string, unknown>,
    status: rule.requires_approval ? 'pending_approval' : 'executed',
  }

  switch (rule.rule_type as string) {
    case 'pause':
      logEntry.action_taken = `Pause campaign: ${perf.campaign_name}`
      logEntry.details = { cpa: formatPounds(perf.cpa_micros), spend: formatPounds(perf.total_spend_micros) }
      if (!rule.requires_approval) {
        await supabase.from('co_campaigns').update({ status: 'paused' }).eq('id', perf.campaign_id)
      }
      break

    case 'scale_up': {
      const multiplier = actions.budget_multiplier as number
      const maxBudget = actions.max_daily_budget_micros as number
      const newBudget = Math.min(Math.round(perf.daily_budget_micros * multiplier), maxBudget)
      logEntry.action_taken = `Scale up budget: ${perf.campaign_name}`
      logEntry.details = { from: formatPounds(perf.daily_budget_micros), to: formatPounds(newBudget), cpa: formatPounds(perf.cpa_micros) }
      if (!rule.requires_approval) {
        await supabase.from('co_campaigns').update({ daily_budget_micros: newBudget }).eq('id', perf.campaign_id)
      }
      break
    }

    case 'scale_down': {
      const multiplier = actions.budget_multiplier as number
      const minBudget = actions.min_daily_budget_micros as number
      const newBudget = Math.max(Math.round(perf.daily_budget_micros * multiplier), minBudget)
      logEntry.action_taken = `Scale down budget: ${perf.campaign_name}`
      logEntry.details = { from: formatPounds(perf.daily_budget_micros), to: formatPounds(newBudget), cpa: formatPounds(perf.cpa_micros) }
      if (!rule.requires_approval) {
        await supabase.from('co_campaigns').update({ daily_budget_micros: newBudget }).eq('id', perf.campaign_id)
      }
      break
    }

    case 'alert':
      logEntry.action_taken = `Alert: zero conversions for ${perf.campaign_name}`
      logEntry.details = { spend: formatPounds(perf.total_spend_micros), impressions: perf.total_impressions, clicks: perf.total_clicks }
      await sendDiscordNotification(`Zero conversions alert: ${perf.campaign_name} has spent ${formatPounds(perf.total_spend_micros)} with 0 conversions`)
      break
  }

  await supabase.from('co_automation_log').insert(logEntry)

  if (rule.requires_approval) {
    result.actionsPendingApproval++
  } else {
    result.actionsExecuted++
  }
}

async function handleLaunchRule(
  supabase: ReturnType<typeof createAdminClient>,
  rule: Record<string, unknown>,
  conditions: Record<string, unknown>,
  actions: Record<string, unknown>,
  result: AutomationResult
) {
  // Find eligible centres
  const { data: centres } = await supabase
    .from('co_test_centres')
    .select('id, name, slug')
    .eq('priority_tier', conditions.priority_tier as string)
    .eq('status', conditions.status as string)
    .eq('has_landing_page', conditions.has_landing_page as boolean)

  if (!centres?.length) return

  // Check which already have campaigns
  const { data: existingCampaigns } = await supabase
    .from('co_campaigns')
    .select('test_centre_id')

  const existingSet = new Set((existingCampaigns ?? []).map(c => c.test_centre_id))
  const eligible = centres.filter(c => !existingSet.has(c.id))

  for (const centre of eligible) {
    const logEntry = {
      rule_id: rule.id as string,
      campaign_id: null as string | null,
      action_taken: `Auto-launch campaign for ${centre.name}`,
      details: { centre_slug: centre.slug, budget: formatPounds(Number(actions.initial_budget_micros ?? 5_000_000)) },
      status: rule.requires_approval ? 'pending_approval' : 'executed',
    }

    if (!rule.requires_approval) {
      try {
        const pushResult = await pushCampaignForCentre(centre.id)
        logEntry.campaign_id = pushResult.campaignId
      } catch (err) {
        result.errors.push(`Launch ${centre.name}: ${err}`)
        continue
      }
    }

    await supabase.from('co_automation_log').insert(logEntry)

    if (rule.requires_approval) {
      result.actionsPendingApproval++
    } else {
      result.actionsExecuted++
    }
  }
}
```

Commit:
```bash
git add src/lib/automation/
git commit -m "feat: add automation engine with rule evaluation and execution"
```

---

## Phase 4: API Routes

### Task 16: API routes

All routes use `requireAdmin()` guard. Cron routes also validate `CRON_SECRET`.

**Files to create:**

1. `src/app/api/campaigns/generate/route.ts`
2. `src/app/api/campaigns/push/route.ts`
3. `src/app/api/campaigns/sync/route.ts`
4. `src/app/api/automation/run/route.ts`
5. `src/app/api/automation/approve/[id]/route.ts`
6. `src/app/api/automation/reject/[id]/route.ts`
7. `src/app/api/centres/route.ts`
8. `src/app/api/centres/import/route.ts`
9. `src/app/api/dashboard/kpis/route.ts`

Each follows this pattern:

```typescript
import { requireAdmin, unauthorizedResponse } from '@/lib/auth/guard'
import { createAdminClient } from '@/lib/supabase/server'

export async function GET(req: Request) {
  try {
    await requireAdmin()
  } catch {
    return unauthorizedResponse()
  }

  const supabase = createAdminClient()
  // ... route logic
}
```

Cron routes additionally check:
```typescript
const authHeader = req.headers.get('authorization')
if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
  try { await requireAdmin() } catch { return unauthorizedResponse() }
}
```

**Implement all 9 routes with full logic as described in the design doc.** Each route should handle errors, return appropriate status codes, and use the Supabase admin client for all database operations.

Commit after all routes:
```bash
git add src/app/api/
git commit -m "feat: add all API routes with auth guards"
```

---

## Phase 5: Dashboard UI

### Task 17: Dashboard layout

Create: `src/app/dashboard/layout.tsx`

Sidebar navigation with links to: Dashboard, Automation, Bulk Actions, Settings. Header with user info and logout button. Use shadcn/ui components.

### Task 18: Main dashboard page

Create: `src/app/dashboard/page.tsx`

Components needed:
- `src/components/dashboard/kpi-cards.tsx` — 4 cards (spend, conversions, CPA, active campaigns)
- `src/components/dashboard/approval-banner.tsx` — alert for pending actions
- `src/components/dashboard/centres-table.tsx` — sortable/filterable table, colour-coded rows

Fetches data from `/api/dashboard/kpis` and `/api/centres`.

### Task 19: Centre detail page

Create: `src/app/dashboard/centres/[slug]/page.tsx`

Components:
- `src/components/dashboard/performance-chart.tsx` — Recharts line chart (spend, conversions, CPA)
- `src/components/dashboard/keyword-table.tsx` — keyword performance
- `src/components/dashboard/ad-copy-comparison.tsx` — variant A vs B CTR
- `src/components/dashboard/centre-automation-log.tsx` — filtered log
- Manual controls: budget slider, pause/resume button, edit ad copy dialog

### Task 20: Automation page

Create: `src/app/dashboard/automation/page.tsx`

Components:
- `src/components/dashboard/rules-list.tsx` — toggle on/off per rule
- `src/components/dashboard/approval-queue.tsx` — approve/reject inline
- `src/components/dashboard/automation-log.tsx` — full log with filters

### Task 21: Bulk actions page

Create: `src/app/dashboard/bulk/page.tsx`

Components:
- Multi-select centres table with checkboxes
- Action bar: Launch Selected, Pause Selected, Adjust Budget
- Campaign preview modal (shows generated config before pushing)
- CSV import section with file upload and validation

### Task 22: Settings page

Create: `src/app/dashboard/settings/page.tsx`

Sections:
- Environment status (green/red indicators for configured credentials)
- Default budget and CPA target inputs
- Discord webhook URL input
- Negative keyword list editor (add/remove)

Commit after each page:
```bash
git commit -m "feat: add [page name]"
```

---

## Phase 6: Final Integration

### Task 23: CLAUDE.md

Create: `test-routes-campaign-ops/CLAUDE.md` with project context as specified in the design doc.

### Task 24: RLS audit script

Create: `test-routes-campaign-ops/scripts/audit-rls.ts`

```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

async function main() {
  const { data, error } = await supabase.rpc('check_rls_status')

  // Fallback: direct query
  const { data: tables } = await supabase
    .from('pg_tables')
    .select('tablename, rowsecurity')

  // Actually use raw SQL via supabase-js
  const result = await fetch(
    `${process.env.NEXT_PUBLIC_SUPABASE_URL}/rest/v1/rpc/`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': process.env.SUPABASE_SERVICE_ROLE_KEY!,
        'Authorization': `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY!}`,
      },
    }
  )

  console.log('RLS Audit - checking all co_ tables...')
  // This script should be run via Supabase SQL directly:
  // SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'co_%';
  console.log('Run this SQL in Supabase dashboard or via MCP:')
  console.log(`SELECT tablename, rowsecurity,
    case when rowsecurity then 'SECURE' else 'EXPOSED' end as status
  FROM pg_tables
  WHERE schemaname = 'public' AND tablename LIKE 'co_%'
  ORDER BY tablename;`)
}

main()
```

### Task 25: Package.json scripts

Add to `test-routes-campaign-ops/package.json`:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "db:seed": "tsx scripts/seed-test-centres.ts && tsx scripts/seed-automation-rules.ts",
    "db:audit": "tsx scripts/audit-rls.ts",
    "sync": "curl -X GET http://localhost:3000/api/campaigns/sync",
    "automate": "curl -X POST http://localhost:3000/api/automation/run"
  }
}
```

### Task 26: Final build and verify

```bash
cd test-routes-campaign-ops
pnpm build
```

Fix any TypeScript or build errors.

### Task 27: Final commit

```bash
git add -A
git commit -m "feat: complete campaign operations dashboard"
```

---

## Summary

| Phase | Tasks | What it delivers |
|-------|-------|-----------------|
| 1: Init & Database | 1-5 | Project scaffold, Supabase tables with RLS, seeded data |
| 2: Auth | 6-8 | Magic link login, auth guard, middleware |
| 3: Core Libraries | 9-15 | Utils, Discord, Google Ads client, campaign generator, performance sync, automation engine |
| 4: API Routes | 16 | All 9 API endpoints with auth |
| 5: Dashboard UI | 17-22 | All 6 pages with components |
| 6: Integration | 23-27 | CLAUDE.md, audit scripts, build verification |
