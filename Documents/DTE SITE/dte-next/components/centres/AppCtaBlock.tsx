import { Download, CheckCircle, Navigation, Shield } from 'lucide-react'
import { APP_STORE_URL, PLAY_STORE_URL } from '@/lib/constants'

export function AppCtaBlock() {
  return (
    <section className="py-20 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="rounded-3xl border border-accent/20 bg-gradient-to-br from-accent/10 via-black/40 to-black/40 p-8 md:p-12 relative overflow-hidden">
          {/* Glow effect */}
          <div className="absolute -top-20 -right-20 h-64 w-64 rounded-full bg-accent/10 blur-[100px]" />

          <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
            {/* Text content */}
            <div>
              <h2 className="font-brand text-3xl font-bold tracking-tight text-white sm:text-4xl mb-4">
                Know Every Route Before Test Day
              </h2>
              <p className="text-white/70 leading-relaxed mb-6 max-w-lg">
                Test Routes Expert gives you turn-by-turn navigation for real
                driving test routes at every UK test centre. No surprises on
                test day.
              </p>

              <ul className="space-y-3 mb-8">
                <li className="flex items-center gap-3 text-sm text-white/70">
                  <Navigation className="h-4 w-4 text-accent shrink-0" />
                  Turn-by-turn navigation on real test routes
                </li>
                <li className="flex items-center gap-3 text-sm text-white/70">
                  <CheckCircle className="h-4 w-4 text-accent shrink-0" />
                  Track your progress route by route
                </li>
                <li className="flex items-center gap-3 text-sm text-white/70">
                  <Shield className="h-4 w-4 text-accent shrink-0" />
                  Pass First Time Guarantee
                </li>
              </ul>

              <div className="flex flex-col sm:flex-row gap-3">
                <a
                  href={PLAY_STORE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center gap-2 rounded-full bg-accent px-6 py-3.5 text-sm font-bold text-black transition-all hover:scale-[1.02] hover:bg-white active:scale-[0.98] shadow-[0_0_20px_rgba(252,163,17,0.3)]"
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

            {/* App screenshot */}
            <div className="flex justify-center">
              <div className="relative w-full max-w-[280px]">
                <div className="rounded-[2rem] border border-white/15 bg-[#0b0b0b] p-2.5 shadow-[0_24px_80px_rgba(0,0,0,0.65)]">
                  <div className="overflow-hidden rounded-[1.4rem] border border-white/10 bg-[#101010]">
                    <div className="flex items-center justify-between border-b border-white/10 px-3 py-1.5">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-accent">
                        Test Routes Expert
                      </span>
                      <span className="h-2 w-2 rounded-full bg-accent" />
                    </div>
                    <img
                      src="/app-screenshots/route-preview.png"
                      alt="Test Routes Expert app showing a driving test route with turn-by-turn navigation"
                      className="h-auto w-full object-cover"
                      loading="lazy"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
