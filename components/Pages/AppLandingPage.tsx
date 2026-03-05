import React, { useEffect, useRef, useState } from 'react';
import { Navbar } from '../Layout/Navbar';
import { Footer } from '../Layout/Footer';
import { Reveal } from '../UI/Reveal';
import { ServiceStatusBanner } from '../UI/ServiceStatusBanner';
import { APP_SCREENSHOTS, HOME_PATH, PLAY_STORE_URL, APP_STORE_URL, TESTIMONIALS, TRUST_STATS } from '../../constants';
import { ArrowRight, Smartphone, Apple, MapPin, Navigation, Shield, Star, PlayCircle } from 'lucide-react';

const YOUTUBE_CHANNEL_URL = 'https://www.youtube.com/@JoshRamwell';
const YOUTUBE_VIDEOS_URL = 'https://www.youtube.com/@JoshRamwell/videos';

export const AppLandingPage: React.FC = () => {
  const [isIOSUser, setIsIOSUser] = useState(false);
  const [showStickyCta, setShowStickyCta] = useState(false);
  const [activeShotIndex, setActiveShotIndex] = useState(0);
  const carouselRef = useRef<HTMLDivElement>(null);

  const mobileShots = [
    { src: '/app-screenshots/route-preview.png', title: 'Know every turn before you even start the engine.' },
    { src: '/app-screenshots/navigation-light.png', title: "Never miss a 'trap' junction again with turn-by-turn alerts." },
    { src: '/app-screenshots/navigation-dark.png', title: 'Avoid an instant fail with real-time speed limit warnings.' },
    { src: '/app-screenshots/route-progress.png', title: 'Track your mastery of every route at your local centre.' },
    { src: '/app-screenshots/centre-list.png', title: '350+ UK Test Centres. Find yours in 2 seconds.' },
  ];

  useEffect(() => {
    setIsIOSUser(/iPhone|iPad|iPod/i.test(window.navigator.userAgent));

    const handleScroll = () => {
      const hero = document.getElementById('top');
      if (!hero) return;
      const { bottom } = hero.getBoundingClientRect();
      setShowStickyCta(bottom < window.innerHeight * 0.55);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleCarouselScroll = () => {
    const el = carouselRef.current;
    if (!el) return;
    const card = el.firstElementChild as HTMLElement | null;
    if (!card) return;

    const gap = 16;
    const step = card.offsetWidth + gap;
    const nextIndex = Math.round(el.scrollLeft / step);
    const boundedIndex = Math.max(0, Math.min(mobileShots.length - 1, nextIndex));
    setActiveShotIndex(boundedIndex);
  };

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#121212] pb-24 text-white selection:bg-[#FFD700]/30 selection:text-white md:pb-0">
      <div className="fixed inset-0 z-0 pointer-events-none opacity-20 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]"></div>

      <ServiceStatusBanner />
      <Navbar />

      <section className="relative min-h-[100svh] overflow-hidden pt-24 md:pt-28" id="top">
        <div className="absolute inset-0 z-0">
          <div className="absolute inset-0 bg-[#121212]"></div>
          <div className="absolute left-1/2 top-0 h-[420px] w-[420px] -translate-x-1/2 rounded-full bg-[#FFD700]/15 blur-[130px]"></div>
          <div className="absolute bottom-0 right-0 h-80 w-80 rounded-full bg-[#1f2937]/70 blur-[120px]"></div>
        </div>

        <div className="relative z-10 mx-auto grid w-full max-w-7xl grid-cols-1 items-center gap-10 px-6 pb-14 lg:grid-cols-2 lg:gap-14">
          <div>
            <Reveal direction="up" duration={0.8}>
              <h1 className="font-brand text-4xl font-black leading-[1.02] tracking-tight text-white sm:text-5xl md:text-7xl">
                Pass Your Driving Test First Time and Skip the 6-Month "Fail Loop".
              </h1>
            </Reveal>

            <Reveal delay={0.15}>
              <p className="mt-5 max-w-2xl text-base leading-relaxed text-white/75 md:text-xl">
                Don't get stuck in the 24-week backlog. Use the "cheat code" to practice every examiner route at your local centre so you pass first time and stay off the waiting list forever.
              </p>
            </Reveal>

            <Reveal delay={0.2}>
              <p className="mt-4 inline-flex items-center rounded-full border border-[#FFD700]/30 bg-[#FFD700]/10 px-4 py-1.5 text-xs font-bold text-[#FFD700] md:text-sm">
                Save £137+ in rebooking fees and "holding" lessons by passing on your first attempt.
              </p>
            </Reveal>

            <Reveal delay={0.25}>
              <div className="mt-5 inline-flex flex-wrap items-center gap-2 rounded-full border border-[#FFD700]/35 bg-[#FFD700]/10 px-4 py-2 text-xs font-black uppercase tracking-wide text-[#FFD700] md:text-sm">
                <span>34,000+ YouTube Subscribers</span>
                <span className="text-white/40">|</span>
                <span>4M+ Views</span>
                <span className="text-white/40">|</span>
                <span>#1 Trusted Route Guide</span>
              </div>
            </Reveal>

            <Reveal delay={0.3}>
              <p className="mt-3 inline-flex items-center rounded-full border border-[#FFD700]/30 bg-[#FFD700]/10 px-4 py-1.5 text-xs font-bold uppercase tracking-wide text-[#FFD700]">
                Routes database last updated: February 2026
              </p>
            </Reveal>

            <Reveal delay={0.35}>
              <div className="mt-8 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
                <a
                  href="#download"
                  className="inline-flex items-center justify-center gap-2 rounded-full bg-[#FFD700] px-7 py-4 text-base font-black text-black transition-all hover:scale-[1.02] hover:bg-[#ffe34d] active:scale-[0.98]"
                >
                  Unlock My Local Routes
                  <ArrowRight className="h-5 w-5" />
                </a>
                <a
                  href="#download"
                  className="inline-flex items-center justify-center rounded-full border border-white/30 bg-transparent px-7 py-4 text-base font-bold text-white transition-colors hover:border-[#FFD700] hover:text-[#FFD700]"
                >
                  Download on iPhone
                </a>
              </div>
            </Reveal>
          </div>

          <Reveal direction="left" delay={0.2}>
            <div className="mx-auto w-full max-w-[430px]">
              <div className="relative rounded-[2.2rem] border border-white/15 bg-[#0b0b0b] p-3 shadow-[0_24px_80px_rgba(0,0,0,0.65)]">
                <div className="overflow-hidden rounded-[1.6rem] border border-white/10 bg-[#101010]">
                  <div className="flex items-center justify-between border-b border-white/10 px-4 py-2">
                    <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[#FFD700]">Local Route Preview</span>
                    <span className="h-2.5 w-2.5 rounded-full bg-[#FFD700]"></span>
                  </div>
                  <div className="relative">
                    <img
                      src="/app-screenshots/navigation-light.png"
                      alt="Mobile navigation UI with a test route line"
                      className="h-auto w-full object-cover"
                      loading="eager"
                    />
                  </div>
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <section className="relative z-10 px-6 pb-16" id="benefits">
        <div className="mx-auto max-w-7xl">
          <Reveal direction="up" delay={0.1}>
            <h2 className="font-brand text-3xl font-black text-white md:text-5xl">What You Get So You Pass Faster</h2>
          </Reveal>
          <div className="mt-8 grid gap-5 md:grid-cols-3">
            <Reveal direction="up" delay={0.2}>
              <div className="rounded-2xl border border-white/10 bg-black/40 p-6">
                <div className="mb-4 inline-flex rounded-xl border border-[#FFD700]/30 bg-[#FFD700]/10 p-2 text-[#FFD700]">
                  <Navigation className="h-5 w-5" />
                </div>
                <h3 className="text-xl font-black text-white">Turn-by-Turn Nav</h3>
                <p className="mt-3 text-white/70">
                  Drive your local test routes like you've lived there for 10 years so you never miss a junction.
                </p>
              </div>
            </Reveal>
            <Reveal direction="up" delay={0.3}>
              <div className="rounded-2xl border border-white/10 bg-black/40 p-6">
                <div className="mb-4 inline-flex rounded-xl border border-[#FFD700]/30 bg-[#FFD700]/10 p-2 text-[#FFD700]">
                  <MapPin className="h-5 w-5" />
                </div>
                <h3 className="text-xl font-black text-white">Real DVSA Routes</h3>
                <p className="mt-3 text-white/70">
                  Practice the actual roads you'll be tested on so there are ZERO surprises on the big day.
                </p>
              </div>
            </Reveal>
            <Reveal direction="up" delay={0.4}>
              <div className="rounded-2xl border border-white/10 bg-black/40 p-6">
                <div className="mb-4 inline-flex rounded-xl border border-[#FFD700]/30 bg-[#FFD700]/10 p-2 text-[#FFD700]">
                  <Shield className="h-5 w-5" />
                </div>
                <h3 className="text-xl font-black text-white">Speed Awareness</h3>
                <p className="mt-3 text-white/70">
                  Get real-time speed alerts so you don't fail for a simple 21-in-a-20 mistake.
                </p>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      <section className="relative z-10 px-6 pb-16">
        <div className="mx-auto max-w-7xl">
          <Reveal direction="up" delay={0.1}>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {TRUST_STATS.map((stat) => (
                <div key={stat.label} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-center">
                  <p className="text-2xl font-black text-[#FFD700] md:text-3xl">{stat.value}</p>
                  <p className="mt-1 text-[10px] uppercase tracking-wider text-white/60 md:text-xs">{stat.label}</p>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      <section id="about" className="relative z-10 px-6 pb-16">
        <div className="mx-auto max-w-7xl">
          <Reveal direction="up" delay={0.15}>
            <div className="mb-6">
              <h2 className="font-brand text-3xl font-black text-white md:text-5xl">See the "Cheat Code" in Action</h2>
              <p className="mt-2 text-white/65">Watch route guidance through difficult turns before your real test day.</p>
            </div>
          </Reveal>

          <Reveal direction="up" delay={0.2}>
            <a
              href={YOUTUBE_VIDEOS_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="group block overflow-hidden rounded-3xl border border-white/10 bg-black/50 p-3 transition-colors hover:border-[#FFD700]/40"
            >
              <div className="relative aspect-video overflow-hidden rounded-2xl border border-white/10">
                <img
                  src="/app-screenshots/navigation-dark.png"
                  alt="POV route teaser"
                  className="h-full w-full object-cover"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-black/35"></div>
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="flex items-center gap-2 rounded-full border border-[#FFD700]/40 bg-black/65 px-4 py-2 text-[#FFD700]">
                    <PlayCircle className="h-5 w-5" />
                    <span className="text-sm font-black uppercase tracking-wide">Watch Route Teaser</span>
                  </div>
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between gap-3 px-1">
                <p className="text-sm text-white/75">See the "Cheat Code" in Action</p>
                <span className="inline-flex items-center gap-2 text-sm font-bold text-[#FFD700] group-hover:text-white">
                  <PlayCircle className="h-4 w-4" />
                  Watch on YouTube
                </span>
              </div>
            </a>
          </Reveal>
        </div>
      </section>

      <section className="relative z-10 px-6 pb-16">
        <div className="mx-auto max-w-7xl">
          <Reveal direction="up" delay={0.15}>
            <div className="mb-6">
              <h2 className="font-brand text-3xl font-black text-white md:text-5xl">Why 34,000 Learners Trust Our Routes</h2>
            </div>
          </Reveal>

          <div className="grid gap-5 md:grid-cols-3">
            {TESTIMONIALS.slice(0, 2).map((item) => (
              <Reveal key={item.author} direction="up" delay={0.2}>
                <div className="rounded-2xl border border-white/10 bg-black/50 p-5 text-left">
                  <div className="mb-3 flex items-center gap-1">
                    {Array.from({ length: item.rating }).map((_, index) => (
                      <Star key={`${item.author}-${index}`} className="h-4 w-4 fill-[#FFD700] text-[#FFD700]" />
                    ))}
                  </div>
                  <p className="leading-relaxed text-white/90">"{item.quote}"</p>
                  <p className="mt-3 text-sm text-white/60">- {item.author}</p>
                </div>
              </Reveal>
            ))}

            <Reveal direction="up" delay={0.25}>
              <a
                href={YOUTUBE_VIDEOS_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="group block rounded-2xl border border-white/10 bg-black/50 p-3 transition-colors hover:border-[#FFD700]/40"
              >
                <div className="relative overflow-hidden rounded-xl border border-white/10">
                  <img
                    src="/app-screenshots/route-preview.png"
                    alt="Why learners trust our routes"
                    className="aspect-video w-full object-cover"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 flex items-center justify-center bg-black/35">
                    <PlayCircle className="h-12 w-12 text-[#FFD700]" />
                  </div>
                </div>
                <p className="mt-3 px-1 text-sm font-bold text-white">Why 34,000 learners trust our routes.</p>
              </a>
            </Reveal>
          </div>
        </div>
      </section>

      <section className="relative z-10 px-6 pb-16">
        <div className="mx-auto max-w-7xl">
          <Reveal direction="up" delay={0.2}>
            <div className="mb-6">
              <h2 className="font-brand text-3xl font-black text-white md:text-5xl">App Screenshots</h2>
            </div>
          </Reveal>

          <div className="md:hidden">
            <div
              ref={carouselRef}
              onScroll={handleCarouselScroll}
              className="flex snap-x snap-mandatory gap-4 overflow-x-auto pb-3 pl-1 pr-10 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"
            >
              {mobileShots.map((shot) => (
                <figure key={shot.src} className="snap-center shrink-0 basis-[86%] rounded-3xl border border-white/10 bg-black/50 p-3 text-left">
                  <figcaption className="mb-3 px-1 text-sm font-bold text-white">{shot.title}</figcaption>
                  <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#0e0e0e] p-2">
                    <div className="mx-auto w-full max-w-[300px] rounded-[1.9rem] border border-white/15 bg-[#0b0b0b] p-2 shadow-[0_16px_30px_rgba(0,0,0,0.5)]">
                      <div className="overflow-hidden rounded-[1.4rem] border border-white/10">
                        <img src={shot.src} alt={shot.title} className="h-auto w-full" loading="lazy" />
                      </div>
                    </div>
                  </div>
                </figure>
              ))}
            </div>
            <div className="mt-3 flex items-center justify-center gap-2">
              {mobileShots.map((shot, idx) => (
                <span
                  key={shot.src}
                  className={`h-1.5 rounded-full transition-all ${idx === activeShotIndex ? 'w-6 bg-[#FFD700]' : 'w-1.5 bg-white/30'}`}
                ></span>
              ))}
            </div>
          </div>

          <div className="hidden gap-5 md:grid md:grid-cols-2 lg:grid-cols-3">
            {APP_SCREENSHOTS.map((shot) => (
              <figure key={shot.src} className="rounded-3xl border border-white/10 bg-black/40 p-3 text-left">
                <img src={shot.src} alt={shot.title} className="h-auto w-full rounded-2xl border border-white/10" loading="lazy" />
                <figcaption className="mt-3 px-1 text-sm text-white/80">{shot.title}</figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      <section className="relative z-10 px-6 pb-12" id="download">
        <div className="mx-auto grid max-w-4xl gap-8 md:grid-cols-2">
          <Reveal direction="left" delay={0.3} width="100%">
            <div className="relative group h-full w-full">
              <div className="absolute -inset-0.5 rounded-[2.1rem] bg-gradient-to-r from-green-500 via-green-400 to-green-500 opacity-20 blur-md transition duration-500 group-hover:opacity-50"></div>
              <div className="relative flex h-full flex-col rounded-[2rem] bg-[#0d0d0d] p-8 text-center ring-1 ring-white/10 md:p-10">
                <div className="mb-6 flex justify-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-green-500/20 bg-green-500/10 text-green-400">
                    <Smartphone size={32} />
                  </div>
                </div>

                <h2 className="font-brand text-2xl font-bold text-white md:text-3xl">Android Users</h2>
                <p className="mb-8 mt-3 flex-grow leading-relaxed text-white/60">
                  Get instant access and start practising your local routes today.
                </p>

                <a
                  href={PLAY_STORE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group/btn relative block w-full min-h-[60px] overflow-hidden rounded-xl bg-green-500 p-4 shadow-[0_0_20px_rgba(34,197,94,0.3)] transition-all hover:scale-[1.02] hover:bg-green-400 hover:shadow-[0_0_40px_rgba(34,197,94,0.5)] active:scale-[0.98]"
                >
                  <div className="relative z-10 flex min-h-[28px] items-center justify-center gap-3 text-base font-black uppercase tracking-wide text-black">
                    <svg viewBox="0 0 24 24" className="h-6 w-6 fill-current">
                      <path d="M3.18 23.71c-.35-.2-.59-.56-.59-.98V1.27c0-.42.24-.78.6-.98l11.26 11.71L3.18 23.71zm1.4.9l12.52-7.24-2.76-2.87L4.58 24.61zM20.73 11.3L17.6 9.49 14.7 12l2.9 2.51 3.13-1.81c.56-.32.56-1.08 0-1.4zM4.58-.62l9.76 10.11 2.76-2.87L4.58-.62z" />
                    </svg>
                    Unlock My Local Routes
                  </div>
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent group-hover/btn:animate-shine"></div>
                </a>

                <p className="mt-4 text-xs font-medium uppercase tracking-wider text-white/30">Available Now</p>
              </div>
            </div>
          </Reveal>

          <Reveal direction="right" delay={0.3} width="100%">
            <div className="relative group h-full w-full">
              <div className="absolute -inset-0.5 rounded-[2.1rem] bg-gradient-to-r from-[#FFD700] via-yellow-500 to-[#FFD700] opacity-20 blur-md transition duration-500 group-hover:opacity-50"></div>
              <div className="relative flex h-full flex-col rounded-[2rem] bg-[#0d0d0d] p-8 text-center ring-1 ring-white/10 md:p-10">
                <div className="mb-6 flex justify-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-[#FFD700]/20 bg-[#FFD700]/10 text-[#FFD700]">
                    <Apple size={32} />
                  </div>
                </div>

                <h2 className="font-brand text-2xl font-bold text-white md:text-3xl">iPhone Users</h2>
                <p className="mb-8 mt-3 flex-grow leading-relaxed text-white/60">
                  Available now on the App Store. Download and start practising today.
                </p>

                <a
                  href={APP_STORE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group/btn relative block w-full min-h-[60px] overflow-hidden rounded-xl bg-black p-4 shadow-[0_0_20px_rgba(255,215,0,0.3)] ring-1 ring-white/20 transition-all hover:scale-[1.02] hover:ring-[#FFD700]/50 hover:shadow-[0_0_40px_rgba(255,215,0,0.5)] active:scale-[0.98]"
                >
                  <div className="relative z-10 flex min-h-[28px] items-center justify-center gap-2 text-base font-black uppercase tracking-wide text-white">
                    <Apple size={20} />
                    Download on the App Store
                  </div>
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent group-hover/btn:animate-shine"></div>
                </a>

                <p className="mt-4 text-xs font-medium uppercase tracking-wider text-white/30">Available Now</p>
              </div>
            </div>
          </Reveal>
        </div>

        <Reveal direction="up" delay={0.5}>
          <div className="mx-auto mt-8 max-w-4xl rounded-2xl border border-[#FFD700]/30 bg-[#FFD700]/10 p-4 text-center">
            <p className="text-sm font-bold text-[#FFD700] md:text-base">
              Pass First Time Guarantee: If you practice all routes and don't pass, we'll give you Premium access for free until you do.
            </p>
          </div>
        </Reveal>
      </section>

      <section className="relative z-10 px-6 pb-12">
        <div className="mx-auto max-w-7xl border-t border-white/5 pt-8">
          <a href={HOME_PATH} className="inline-flex items-center gap-2 text-sm text-white/40 transition-colors hover:text-[#FFD700]">
            <ArrowRight className="h-4 w-4 rotate-180" />
            Back to drivingtestexpert.com
          </a>
        </div>
      </section>

      <Footer />

      {showStickyCta && (
        <div className="fixed inset-x-0 bottom-0 z-[70] border-t border-[#FFD700]/20 bg-black/85 p-3 backdrop-blur-md md:hidden">
          <a
            href={isIOSUser ? APP_STORE_URL : PLAY_STORE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-[#FFD700] px-6 py-3 text-sm font-black uppercase tracking-wide text-black shadow-[0_0_20px_rgba(255,215,0,0.35)]"
          >
            {isIOSUser ? 'Download on the App Store' : 'Unlock My Local Routes'}
            <ArrowRight className="h-4 w-4" />
          </a>
        </div>
      )}
    </div>
  );
};
