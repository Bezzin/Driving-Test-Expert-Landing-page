import { ArrowRight } from 'lucide-react'
import { APP_PATH } from '@/lib/constants'
import { Reveal } from '@/components/UI/Reveal'

export const Hero: React.FC = () => {
  return (
    <section className="relative min-h-[100svh] overflow-hidden bg-[#121212] pt-36 md:pt-28" id="top">
      <div className="absolute inset-0 z-0">
        <div className="absolute -top-40 left-1/2 h-[440px] w-[440px] -translate-x-1/2 rounded-full bg-[#FFD700]/10 blur-[120px]"></div>
        <div className="absolute bottom-0 left-0 h-80 w-80 rounded-full bg-[#1f2937]/60 blur-[120px]"></div>
      </div>

      <div className="relative z-10 mx-auto grid w-full max-w-7xl grid-cols-1 gap-10 px-6 pb-14 lg:grid-cols-2 lg:items-center lg:gap-16">
        <div className="max-w-2xl">
          <Reveal direction="up" duration={0.8}>
            <h1 className="font-brand text-4xl font-black leading-[1.02] tracking-tight text-white sm:text-5xl md:text-7xl">
              Pass Your Driving Test First Time Without The &ldquo;Test Day&rdquo; Nerves.
            </h1>
          </Reveal>

          <Reveal delay={0.15} width="100%">
            <p className="mt-5 text-base leading-relaxed text-white/75 md:text-xl">
              Get the &ldquo;cheat code&rdquo; for UK learners. Practice the exact routes your examiner uses with turn-by-turn navigation and snag cancelled test dates 10x faster.
            </p>
          </Reveal>

          <Reveal delay={0.25}>
            <div className="mt-8 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
              <a
                href={APP_PATH}
                className="inline-flex items-center justify-center gap-2 rounded-full bg-[#FFD700] px-7 py-4 text-base font-black text-black transition-all hover:scale-[1.02] hover:bg-[#ffe34d] active:scale-[0.98]"
              >
                Find My Test Routes
                <ArrowRight className="h-5 w-5" />
              </a>
              <a
                href="#apps"
                className="inline-flex items-center justify-center rounded-full border border-white/30 bg-transparent px-7 py-4 text-base font-bold text-white transition-colors hover:border-[#FFD700] hover:text-[#FFD700]"
              >
                Get Earlier Test Dates
              </a>
            </div>
          </Reveal>

          <Reveal delay={0.35} width="100%">
            <p className="mt-4 text-sm text-white/75 md:text-base">
              <span className="mr-2 text-[#FFD700]">&#9733;&#9733;&#9733;&#9733;&#9733;</span>
              Join 50,000+ UK learners. No more failed tests.
            </p>
          </Reveal>

          <Reveal delay={0.4} width="100%">
            <p className="mt-3 inline-flex items-center rounded-full border border-[#FFD700]/30 bg-[#FFD700]/10 px-4 py-1.5 text-xs font-bold uppercase tracking-wide text-[#FFD700]">
              Test routes database last updated: February 2026
            </p>
          </Reveal>
        </div>

        <Reveal direction="left" delay={0.2}>
          <div className="mx-auto w-full max-w-[430px]">
            <div className="relative rounded-[2.2rem] border border-white/15 bg-[#0b0b0b] p-3 shadow-[0_24px_80px_rgba(0,0,0,0.65)]">
              <div className="overflow-hidden rounded-[1.6rem] border border-white/10 bg-[#101010]">
                <div className="flex items-center justify-between border-b border-white/10 px-4 py-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[#FFD700]">Test Route Preview</span>
                  <span className="h-2.5 w-2.5 rounded-full bg-[#FFD700]"></span>
                </div>
                <img
                  src="/app-screenshots/route-preview.png"
                  alt="Mobile navigation showing a driving test route"
                  className="h-auto w-full object-cover"
                  loading="eager"
                />
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
