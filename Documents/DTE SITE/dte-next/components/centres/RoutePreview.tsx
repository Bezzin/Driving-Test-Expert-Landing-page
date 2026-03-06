import Link from 'next/link'
import { Route, Clock, ArrowRight, Navigation, RotateCw, Download, MapPin } from 'lucide-react'
import { APP_STORE_URL, PLAY_STORE_URL } from '@/lib/constants'

interface RouteData {
  routeNumber: number
  distanceKm: number
  durationMins: number
  keyRoads: string[]
  roundabouts: number
  turns: number
}

interface RoutePreviewProps {
  centreName: string
  centreSlug: string
  postcode: string
  routeCount: number
  allRoads: string[]
  routes: RouteData[]
  latitude: number
  longitude: number
}

export function RoutePreview({
  centreName,
  centreSlug,
  postcode,
  routeCount,
  allRoads,
  routes,
  latitude,
  longitude,
}: RoutePreviewProps) {
  const shortest = routes.reduce((a, b) => (a.distanceKm < b.distanceKm ? a : b))
  const longest = routes.reduce((a, b) => (a.distanceKm > b.distanceKm ? a : b))
  const avgDistance = Math.round((routes.reduce((s, r) => s + r.distanceKm, 0) / routes.length) * 10) / 10
  const avgDuration = Math.round(routes.reduce((s, r) => s + r.durationMins, 0) / routes.length)
  const totalRoundabouts = routes.reduce((s, r) => s + r.roundabouts, 0)
  const avgRoundabouts = Math.round(totalRoundabouts / routes.length)

  // Static map from OpenStreetMap (no API key needed)
  const mapUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${longitude - 0.04},${latitude - 0.03},${longitude + 0.04},${latitude + 0.03}&layer=mapnik&marker=${latitude},${longitude}`

  // Show first 10 routes in the preview table
  const previewRoutes = routes.slice(0, 10)
  const hasMore = routes.length > 10

  return (
    <section className="py-16 px-6 max-w-7xl mx-auto">
      <div className="flex flex-col gap-8">
        {/* Section Header */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-accent/20 border border-accent/30 px-3 py-1 text-sm font-semibold text-accent">
              <Navigation className="h-4 w-4" />
              {routeCount} Routes Available
            </span>
          </div>
          <h2 className="font-brand text-3xl font-bold tracking-tight text-white sm:text-4xl mb-4">
            {centreName} Test Routes
          </h2>
          <p className="max-w-3xl text-white/70 leading-relaxed">
            We have mapped {routeCount} real driving test routes used at {centreName} ({postcode}).
            Routes range from {shortest.distanceKm} km ({shortest.durationMins} mins) to {longest.distanceKm} km
            ({longest.durationMins} mins), with an average distance of {avgDistance} km taking around {avgDuration} minutes.
            Practice every route with turn-by-turn navigation in the app before your test day.
          </p>
        </div>

        {/* Stats + Map Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Route Stats */}
          <div className="lg:col-span-1 grid grid-cols-2 gap-4">
            <div className="rounded-2xl border border-white/10 bg-black/40 p-5 text-center">
              <Route className="h-5 w-5 text-accent mx-auto mb-2" />
              <p className="text-2xl font-bold text-white">{routeCount}</p>
              <p className="text-xs text-white/50">Total Routes</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/40 p-5 text-center">
              <Clock className="h-5 w-5 text-accent mx-auto mb-2" />
              <p className="text-2xl font-bold text-white">{avgDuration} min</p>
              <p className="text-xs text-white/50">Avg Duration</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/40 p-5 text-center">
              <MapPin className="h-5 w-5 text-accent mx-auto mb-2" />
              <p className="text-2xl font-bold text-white">{avgDistance} km</p>
              <p className="text-xs text-white/50">Avg Distance</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/40 p-5 text-center">
              <RotateCw className="h-5 w-5 text-accent mx-auto mb-2" />
              <p className="text-2xl font-bold text-white">{avgRoundabouts}</p>
              <p className="text-xs text-white/50">Avg Roundabouts</p>
            </div>
          </div>

          {/* Map Preview */}
          <div className="lg:col-span-2 rounded-2xl border border-white/10 bg-black/40 overflow-hidden">
            <iframe
              title={`Map of ${centreName}`}
              src={mapUrl}
              className="w-full h-64 lg:h-full min-h-[250px]"
              loading="lazy"
              style={{ border: 0 }}
            />
          </div>
        </div>

        {/* Route Table */}
        <div className="rounded-2xl border border-white/10 bg-black/40 overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
            <div className="flex items-center gap-2">
              <Route className="h-5 w-5 text-accent" />
              <h3 className="text-lg font-semibold text-white">Route Overview</h3>
            </div>
            <span className="text-xs text-white/40">
              Showing {previewRoutes.length} of {routeCount} routes
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-white/10 text-sm text-white/50">
                  <th className="px-4 py-3 font-medium w-16">Route</th>
                  <th className="px-4 py-3 font-medium text-right">Distance</th>
                  <th className="px-4 py-3 font-medium text-right">Duration</th>
                  <th className="px-4 py-3 font-medium text-right hidden sm:table-cell">Roundabouts</th>
                  <th className="px-4 py-3 font-medium text-right hidden sm:table-cell">Turns</th>
                  <th className="px-4 py-3 font-medium hidden md:table-cell">Key Roads</th>
                </tr>
              </thead>
              <tbody>
                {previewRoutes.map(route => (
                  <tr
                    key={route.routeNumber}
                    className="border-b border-white/5 hover:bg-white/5 transition-colors"
                  >
                    <td className="px-4 py-3 text-sm font-semibold text-accent">
                      #{route.routeNumber}
                    </td>
                    <td className="px-4 py-3 text-sm text-white/80 text-right">
                      {route.distanceKm} km
                    </td>
                    <td className="px-4 py-3 text-sm text-white/80 text-right">
                      {route.durationMins} min
                    </td>
                    <td className="px-4 py-3 text-sm text-white/60 text-right hidden sm:table-cell">
                      {route.roundabouts}
                    </td>
                    <td className="px-4 py-3 text-sm text-white/60 text-right hidden sm:table-cell">
                      {route.turns}
                    </td>
                    <td className="px-4 py-3 text-sm text-white/50 hidden md:table-cell">
                      <span className="line-clamp-1">
                        {route.keyRoads.slice(0, 4).join(', ')}
                        {route.keyRoads.length > 4 && ` +${route.keyRoads.length - 4} more`}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {hasMore && (
            <div className="px-6 py-4 border-t border-white/10 text-center">
              <p className="text-sm text-white/50">
                + {routeCount - 10} more routes available in the app
              </p>
            </div>
          )}
        </div>

        {/* Roads Used Section - SEO Gold */}
        <div className="rounded-2xl border border-white/10 bg-black/40 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">
            Roads Used in {centreName} Test Routes
          </h3>
          <p className="text-sm text-white/60 mb-4">
            Across all {routeCount} routes, examiners at {centreName} use {allRoads.length} different
            roads. Familiarise yourself with these roads before your test:
          </p>
          <div className="flex flex-wrap gap-2">
            {allRoads.map(road => (
              <span
                key={road}
                className="inline-flex items-center rounded-full bg-white/5 border border-white/10 px-3 py-1 text-xs text-white/70"
              >
                {road}
              </span>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="rounded-2xl border border-accent/20 bg-accent/5 p-8 text-center">
          <h3 className="font-brand text-2xl font-bold text-white mb-3">
            Practice All {routeCount} Routes with Turn-by-Turn Navigation
          </h3>
          <p className="text-white/60 mb-6 max-w-xl mx-auto">
            Get the full route details with voice-guided navigation.
            Know every junction, roundabout, and lane change before test day.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <a
              href={PLAY_STORE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-full bg-accent px-6 py-3.5 text-sm font-bold text-black transition-all hover:scale-[1.02] hover:bg-white active:scale-[0.98]"
            >
              <Download className="h-4 w-4" />
              Get on Google Play
            </a>
            <a
              href={APP_STORE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-full border border-white/20 bg-white/5 px-6 py-3.5 text-sm font-bold text-white transition-all hover:border-accent hover:text-accent"
            >
              <Download className="h-4 w-4" />
              Download on App Store
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
