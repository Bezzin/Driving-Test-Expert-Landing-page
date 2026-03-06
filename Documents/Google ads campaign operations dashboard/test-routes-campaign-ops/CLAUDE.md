# Test Routes Expert -- Campaign Operations Dashboard

## What This Is
Internal ops dashboard for managing Google Ads campaigns across 300+ UK driving test centres.
Solo-founder tool -- designed for agent-driven automation with human approval for strategic decisions.

## Stack
Next.js 14 (App Router), Supabase (SHARED with the React Native app), Tailwind + shadcn/ui, Google Ads API, Vercel

## Security -- READ THIS FIRST
- This project shares a Supabase instance with the production Test Routes Expert React Native app.
- All campaign ops tables are prefixed `co_` and MUST have RLS enabled with admin-only policies.
- The service role key is used ONLY in server-side API routes (`src/app/api/`). NEVER in client components.
- The browser client uses the anon key for auth ONLY. All data fetching goes through API routes.
- The dashboard NEVER writes to app tables. Read-only cross-references only.

## Key Concepts
- All monetary values stored as MICROS (bigint). 1 GBP = 1,000,000 micros. Convert only in UI.
- DRY_RUN env var controls whether Google Ads API calls are real or mocked.
- Campaign structure: one campaign per test centre.
- Two ad variants per centre: "navigation focus" and "practise focus".
- Auto-tiering: centres are ranked by DVSA test volume (tier_1 = top 15%, tier_2 = next 30%, tier_3 = rest).
- Automation engine runs daily, evaluates rules, executes or queues for approval.

## Commands
- `pnpm dev` -- local dev
- `pnpm build` -- production build
- `pnpm db:seed` -- seed test centres and automation rules
- `pnpm db:audit` -- verify RLS on all co_ tables
- `pnpm sync` -- manual performance sync
- `pnpm automate` -- manual automation engine run

## Important Files
- `src/lib/auth/guard.ts` -- requireAdmin() auth guard (used by ALL API routes)
- `src/lib/supabase/server.ts` -- service role client (SERVER-SIDE ONLY)
- `src/lib/supabase/client.ts` -- anon client (browser, auth only)
- `src/lib/google-ads/campaign-generator.ts` -- campaign creation logic
- `src/lib/google-ads/campaign-push.ts` -- push campaigns to Google Ads
- `src/lib/google-ads/performance-sync.ts` -- daily metrics sync
- `src/lib/automation/engine.ts` -- rule evaluation and execution
- `scripts/seed-test-centres.ts` -- DVSA centre data seeding
- `scripts/seed-automation-rules.ts` -- default rules and negative keywords

## API Routes
- POST /api/campaigns/generate -- preview campaign config
- POST /api/campaigns/push -- create campaigns in Google Ads
- GET /api/campaigns/sync -- trigger performance sync (cron: 06:00 UTC)
- POST /api/automation/run -- trigger automation engine (cron: 07:00 UTC)
- POST /api/automation/approve/:id -- approve pending action
- POST /api/automation/reject/:id -- reject pending action
- GET /api/centres -- list centres with performance
- POST /api/centres/import -- CSV import
- GET /api/dashboard/kpis -- aggregated metrics

## Database Tables (all co_ prefixed, all RLS enabled)
co_test_centres, co_campaigns, co_keywords, co_ad_copy, co_daily_performance, co_automation_rules, co_automation_log, co_negative_keywords
