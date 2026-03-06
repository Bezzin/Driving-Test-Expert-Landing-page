# Campaign Operations Dashboard - Design Document

**Date:** 2026-03-06
**Project:** Test Routes Expert - Google Ads Campaign Operations Dashboard
**Repo:** `test-routes-campaign-ops/` (inside Google ads campaign operations dashboard repo)

## Overview

Internal operations dashboard for programmatically managing Google Ads campaigns across 300+ UK driving test centres. Designed for a solo founder with 90% agent-driven automation and human intervention only for strategic decisions and approvals.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Repo location | `test-routes-campaign-ops/` inside current repo | User preference |
| Centre data source | Seed `co_test_centres` from existing Supabase `test_centers` table + DVSA volume data | Avoids data drift, accurate on day one |
| Campaign structure | One campaign per centre in Google Ads | Per-centre budget control needed during phased rollout from handful to 300+ |
| Tiering | Auto-calculated from DVSA `tests_conducted` volume | Data-driven, no manual assignment needed |
| Scope | Full build, all 11 steps from spec | Going live within the week |
| Google Ads API | Dry-run mode until credentials are configured | Credentials expected soon, full pipeline built regardless |
| Landing pages | All 322 live at `drivingtestexpert.com/test-centres/{slug}/` | No fallback URL needed |
| Auth | Magic link login, single admin user via `ADMIN_EMAIL` env var | Solo founder tool |

## Architecture

```
Browser (Admin)
  |  Next.js Dashboard UI (Tailwind + shadcn/ui)
  |  Auth via Supabase magic link (anon key only)
  |
  |  fetch /api/*
  v
Next.js API Routes (Vercel)
  - requireAdmin() guard on every route
  - Service role key used here ONLY
  - Dry-run mode toggle for Google Ads calls
  |                    |
  v                    v
Supabase DB          Google Ads API
(shared w/ app)      (1 campaign per centre)
  |
  |-- App tables (READ ONLY): test_centers, routes
  |-- Campaign ops (RLS: admin only): co_* tables

Vercel Cron Jobs (daily)
  06:00 UTC - Performance sync (Google Ads -> DB)
  07:00 UTC - Automation engine (evaluate rules)
  07:05 UTC - Discord summary notification
```

### Security Model

- Shared Supabase instance with the Test Routes Expert React Native app
- All `co_` tables have RLS enabled with admin-only policies
- Service role key used ONLY in server-side API routes (`src/app/api/`)
- Browser client uses anon key for auth ONLY, all data fetching via API routes
- Dashboard NEVER writes to app tables — read-only cross-references only
- Cron endpoints validate `CRON_SECRET` header

## Database Schema

### Supabase Project

- **Project:** Test Routes Expert (`zpfkvhnfbbimsfghmjiz`)
- **Region:** eu-central-1
- **Existing app tables:** test_centers (359 rows), routes (5,837 rows), active_sessions, app_config, user_feedback, route_requests, route_ratings

### New Campaign Ops Tables

All prefixed `co_` to distinguish from app tables. All have RLS enabled with admin-only policies.

| Table | Purpose |
|-------|---------|
| `co_test_centres` | Master list of 300+ centres with DVSA data and auto-calculated tiers |
| `co_campaigns` | One Google Ads campaign record per centre |
| `co_keywords` | Keywords per campaign (8 per centre from templates) |
| `co_ad_copy` | Ad variants per campaign (2 per centre: navigation + practise focus) |
| `co_daily_performance` | Daily metrics synced from Google Ads API |
| `co_automation_rules` | Configurable rules the automation engine evaluates |
| `co_automation_log` | Audit trail of every automated action |
| `co_negative_keywords` | Shared negative keyword lists |

### Auto-Tiering Logic

Tiers calculated from DVSA `tests_conducted` data during seeding:
- **Tier 1** (~top 15%, ~50 centres): Highest annual test volume (big cities)
- **Tier 2** (~next 30%, ~100 centres): Medium volume
- **Tier 3** (remaining ~170 centres): Lower volume

### Schema Details

Follows the spec exactly. Key points:
- All monetary values stored as micros (bigint). 1 GBP = 1,000,000 micros
- `co_daily_performance` has generated columns for CTR, CPA, avg CPC
- `co_automation_rules` uses JSONB for conditions and actions
- `co_campaigns` maps 1:1 to a test centre

## Campaign Generation

### Google Ads Structure (per centre)

- 1 campaign (e.g. "Test Routes - Stafford")
- 1 ad group per campaign
- 8 keywords (4 EXACT, 4 PHRASE from templates)
- 2 responsive search ad variants (navigation focus + practise focus)
- Shared negative keyword list
- Daily budget: 5 GBP (configurable)

### Ad Copy Personalisation

- Route count from `routes` table (e.g. "12 Real Test Routes")
- Pass rate from DVSA data (e.g. "45% Pass Rate")
- Final URL: `https://drivingtestexpert.com/test-centres/{slug}/`
- Headlines: max 30 chars, descriptions: max 90 chars

### Dry-Run Mode

When `DRY_RUN=true`:
- Campaign generator produces full config as JSON
- Records stored in DB with status "draft"
- No Google Ads API calls made
- Dashboard fully functional with draft data

When `DRY_RUN=false`:
- "Push" action takes draft campaigns and creates them in Google Ads
- Google campaign/ad group/keyword IDs stored back in DB

### Idempotency

Before generating, checks if `co_campaigns` already has a record for that centre. If yes, skips or updates — never duplicates.

## Automation Engine

Runs daily at 07:00 UTC via Vercel Cron after performance sync.

### Process

1. Load all active rules from `co_automation_rules`
2. For each active campaign, aggregate performance over the rule's `lookback_days`
3. Evaluate conditions against aggregated data
4. If conditions met: execute action or queue for approval
5. Log everything to `co_automation_log`

### Default Rules

| Rule | Trigger | Action | Auto? |
|------|---------|--------|-------|
| Pause high CPA | CPA > 15 GBP, spent > 20 GBP, 7 days | Pause campaign | Yes |
| Scale up winners | CPA < 6 GBP, 5+ conversions, 7 days | Budget x1.5 (max 20 GBP/day) | Yes |
| Scale down underperformers | CPA > 10 GBP, spent > 15 GBP, 7 days | Budget x0.5 (min 3 GBP/day) | Yes |
| Alert zero conversions | 0 conversions, spent > 30 GBP, 14 days | Discord alert | Needs approval |
| Auto-launch tier 1 | Tier 1 + pending + has landing page | Create campaign at 5 GBP/day | Needs approval |

### Safety Rails

- `requires_approval` flag per rule
- Budget caps on scale-up (never exceeds max)
- Budget floors on scale-down (never goes below min)
- Full audit trail in `co_automation_log`

## Dashboard UI

### Pages

**`/login`** - Magic link authentication
- Email input, Supabase sends magic link, redirects to `/dashboard`

**`/dashboard`** - Main overview
- KPI cards: total spend (today/week/month), conversions, avg CPA, active campaigns
- Alert banner for pending approval actions
- Centres table: sortable/filterable, colour-coded by CPA performance
- Quick actions per row: Launch, Pause, Scale Up, View Details

**`/dashboard/centres/[slug]`** - Centre detail
- Performance chart (Recharts): daily spend, conversions, CPA over time
- Keyword performance table
- Ad copy variants with CTR comparison
- Automation log for this centre
- Manual controls: budget, pause/resume, edit ad copy

**`/dashboard/automation`** - Rules & logs
- Rules list with toggle on/off
- Pending approval queue (approve/reject inline)
- Full automation log with filters

**`/dashboard/bulk`** - Bulk operations
- Multi-select centres: batch launch, pause, budget adjust
- CSV import for centre data
- Campaign generator: select -> preview -> approve -> push

**`/dashboard/settings`** - Configuration
- Environment status (credentials configured, dry-run status)
- Default budget and CPA targets
- Discord webhook URL
- Negative keyword list management

## API Routes

| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/api/campaigns/generate` | Generate campaign config for selected centres |
| POST | `/api/campaigns/push` | Push draft campaigns to Google Ads |
| GET | `/api/campaigns/sync` | Trigger performance sync (also used by cron) |
| POST | `/api/automation/run` | Trigger automation engine (also used by cron) |
| POST | `/api/automation/approve/:id` | Approve pending action |
| POST | `/api/automation/reject/:id` | Reject pending action |
| GET | `/api/centres` | List all centres with latest metrics |
| POST | `/api/centres/import` | Bulk import centres from CSV |
| GET | `/api/dashboard/kpis` | Aggregated dashboard metrics |

All routes guarded by `requireAdmin()`. Cron routes additionally validate `CRON_SECRET`.

## Cron Jobs & Notifications

### Vercel Cron

| Time (UTC) | Endpoint | Purpose |
|------------|----------|---------|
| 06:00 | `GET /api/campaigns/sync` | Sync previous day's performance from Google Ads |
| 07:00 | `POST /api/automation/run` | Evaluate automation rules and execute actions |

### Discord Notifications

- Daily summary after automation run: spend, conversions, CPA, actions taken
- Immediate alert for pending approval items
- Anomaly alerts (zero conversions with significant spend)

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Database:** Supabase (shared with React Native app)
- **Auth:** Supabase Auth (magic link, single admin)
- **Styling:** Tailwind CSS + shadcn/ui
- **Charts:** Recharts
- **Google Ads:** `google-ads-api` npm package
- **Cron:** Vercel Cron
- **Deployment:** Vercel
- **Package manager:** pnpm
- **Notifications:** Discord webhook

## Data Sources

- **Existing Supabase tables:** `test_centers` (359 centres), `routes` (5,837 routes)
- **DVSA data:** `C:\Users\Nathaniel\Documents\DTE SITE\dte-next\data\dvsa\centres.json` (322 centres with test volumes, pass rates, historical trends)
- **SEO/content data:** `C:\Users\Nathaniel\Documents\DTE SITE\dte-next\data\centre-content.json` (editorial content per centre)
- **Regional data:** `C:\Users\Nathaniel\Documents\DTE SITE\dte-next\data\regions.json` (14 UK regions)

## Build Order

1. Project init + Supabase migration + RLS + security audit
2. Auth (magic link login, middleware redirect, requireAdmin guard)
3. Google Ads client with dry-run mode
4. Campaign generator (keywords, ad copy, negative keywords)
5. Seed script (test centres from existing data + DVSA volumes + auto-tiering)
6. Dashboard UI - main page with centres table and KPIs
7. Centre detail page with performance charts
8. Performance sync module
9. Automation engine + default rules
10. Bulk actions + CSV import
11. Discord notifications
12. Settings page + automation management UI
