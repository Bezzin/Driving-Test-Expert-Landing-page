import React from 'react';
import { Navbar } from './components/Layout/Navbar';
import { Hero } from './components/Features/Hero';
import { Marquee } from './components/UI/Marquee';
import { FeatureRow } from './components/Features/FeatureRow';
import { Footer } from './components/Layout/Footer';
import { DrivingTutor } from './components/AI/DrivingTutor';
import { WhatsAppButton } from './components/UI/WhatsAppButton';
import { AppLandingPage } from './components/Pages/AppLandingPage';
import { ASSETS, APP_PATH, LEGACY_APP_PATH, TESTIMONIALS, TRUST_STATS } from './constants';
import { Feature } from './types';
import { Reveal } from './components/UI/Reveal';
import { ArrowRight, Smartphone, Apple, Star } from 'lucide-react';

function HomePage() {
  const features: Feature[] = [
    {
      id: 'retest',
      title: 'The *ReTest* App',
      subtitle: 'Beat The Wait',
      description: "Don't get stuck in the backlog. ReTest is our premium driving test cancellations app. We scan the DVSA system 24/7 to snag you an earlier test date, getting you on the road months sooner.",
      image: ASSETS.reTestBox,
      reverse: false,
      cta: 'GET THE APP',
      ctaLink: APP_PATH,
      isGlassOrange: true
    },
    {
      id: 'routes',
      title: 'Know Your *Routes*',
      subtitle: 'Turn-by-Turn Navigation',
      description: "Stop guessing where you'll go. Our 'Driving Test Routes' system features full turn-by-turn navigation for every possible test route in your local area, so there are no surprises on the big day.",
      image: ASSETS.routesBox,
      reverse: true,
      cta: 'GET THE APP',
      ctaLink: APP_PATH,
      isGlassOrange: false
    },
    {
      id: 'discord',
      title: 'Private *Community*',
      subtitle: 'Join the Squad',
      description: "You are not alone. Join thousands of learner drivers in our exclusive Discord. Share tips, vent about failures, and celebrate passes with a community that gets it.",
      image: ASSETS.discordBox,
      reverse: false,
      cta: 'Join Discord',
      isGlassOrange: false
    },
    {
      id: 'youtube',
      title: 'Viral *Tutorials*',
      subtitle: 'Over 4 Million Views',
      description: "Visual learner? Join the massive community on our channel with over 4 million views. Watch 4K POV driving lessons, common fault analysis, and mock tests with real examiners.",
      image: ASSETS.youtubeBox,
      reverse: true,
      cta: 'Watch Now',
      ctaLink: 'https://www.youtube.com/c/joshthedrivinginstructor',
      isGlassOrange: true
    }
  ];

  return (
    <div className="bg-bg min-h-screen text-white selection:bg-accent/30 selection:text-white overflow-x-hidden">

      {/* Background Texture */}
      <div className="fixed inset-0 z-0 pointer-events-none opacity-20 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]"></div>

      <Navbar />

      <Hero />

      <Marquee />

      {/* App Promo Section */}
      <section className="relative z-10 py-16 md:py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <Reveal direction="up" delay={0.2}>
            <div className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-accent via-yellow-500 to-accent rounded-[2.1rem] opacity-20 group-hover:opacity-40 blur-md transition duration-500 animate-pulse-glow"></div>
              <div className="relative bg-[#0d0d0d] ring-1 ring-accent/20 rounded-[2rem] p-8 md:p-12 lg:p-16 text-center shadow-2xl">
                <div className="inline-block px-4 py-2 rounded-full border border-accent/30 bg-accent/10 text-accent text-xs font-bold uppercase tracking-widest mb-6 shadow-[0_0_15px_rgba(252,163,17,0.2)]">
                  New App Available
                </div>

                <h2 className="font-brand text-3xl md:text-5xl lg:text-6xl font-black tracking-tight text-white mb-4 leading-tight">
                  Practise{' '}
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-yellow-200">
                    REAL
                  </span>{' '}
                  Driving Test Routes
                </h2>
                <p className="text-lg md:text-xl text-white/60 max-w-2xl mx-auto mb-10">
                  Available on Android and iPhone. Download and start practising today.
                </p>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-6">
                  <a
                    href={APP_PATH}
                    className="group/btn inline-flex items-center gap-3 rounded-full bg-green-500 px-8 py-4 font-extrabold text-lg text-black transition-all hover:bg-green-400 hover:scale-105 active:scale-95 shadow-[0_0_25px_rgba(34,197,94,0.4)]"
                  >
                    <Smartphone className="w-5 h-5" />
                    Android — Get It Now
                    <ArrowRight className="w-5 h-5 transition-transform group-hover/btn:translate-x-1" />
                  </a>
                  <a
                    href={APP_PATH}
                    className="group/btn inline-flex items-center gap-3 rounded-full border-2 border-accent/50 bg-accent/10 px-8 py-4 font-extrabold text-lg text-accent transition-all hover:bg-accent hover:text-black hover:scale-105 active:scale-95 hover:shadow-[0_0_25px_rgba(252,163,17,0.4)]"
                  >
                    <Apple className="w-5 h-5" />
                    iPhone — Download Now
                    <ArrowRight className="w-5 h-5 transition-transform group-hover/btn:translate-x-1" />
                  </a>
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <main id="apps" className="relative z-10 py-12 flex flex-col gap-12 md:gap-24 px-6 max-w-7xl mx-auto">
        {features.map((feature) => (
          <FeatureRow key={feature.id} feature={feature} />
        ))}
      </main>

      <section id="about" className="py-24 md:py-36 relative z-10 border-t border-white/10 bg-black/30 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6">
          <Reveal direction="up" delay={0.2}>
            <div className="max-w-4xl mx-auto">
              <h2 className="font-brand text-4xl md:text-6xl font-black mb-4 text-white">
                About <span className="text-accent">Test Routes Expert</span>
              </h2>
              <div className="h-1 w-20 bg-accent mb-8 rounded-full"></div>

              <div className="space-y-6 text-lg text-white/80 leading-relaxed">
                <p className="text-xl text-white/90">
                  Test Routes Expert helps learner drivers in the UK practice real driving test routes with turn-by-turn navigation. Our app provides:
                </p>

                <ul className="space-y-4 ml-4">
                  <li className="flex items-start gap-3">
                    <span className="text-accent mt-2">•</span>
                    <div>
                      <strong className="text-white">Authentic Test Routes</strong> - Real routes used at UK driving test centres
                    </div>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-accent mt-2">•</span>
                    <div>
                      <strong className="text-white">Turn-by-Turn Navigation</strong> - Voice-guided directions with speed limit warnings
                    </div>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-accent mt-2">•</span>
                    <div>
                      <strong className="text-white">Multiple Test Centres</strong> - Routes from various DVSA test centres across the UK
                    </div>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-accent mt-2">•</span>
                    <div>
                      <strong className="text-white">Freemium Model</strong> - One free route per test centre, unlimited with Premium subscription
                    </div>
                  </li>
                </ul>

                <div className="mt-12 pt-8 border-t border-white/10">
                  <h3 className="font-brand text-2xl md:text-3xl font-bold mb-4 text-white">Contact</h3>
                  <div className="space-y-2 text-white/70">
                    <p>
                      <strong className="text-white">Email:</strong>{' '}
                      <a href="mailto:support@drivingtestexpert.com" className="text-accent hover:text-yellow-300 transition-colors">
                        support@drivingtestexpert.com
                      </a>
                    </p>
                    <p>
                      <strong className="text-white">Website:</strong>{' '}
                      <a href="https://drivingtestexpert.com" className="text-accent hover:text-yellow-300 transition-colors">
                        drivingtestexpert.com
                      </a>
                    </p>
                    <p className="text-white/60 text-sm mt-4">
                      Developer: Nathaniel Berry
                    </p>
                    <p className="text-white/40 text-xs mt-2">
                      Last updated: December 2025
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <section className="relative z-10 py-20 md:py-28 px-6 border-t border-white/10 bg-black/30">
        <div className="max-w-7xl mx-auto">
          <Reveal direction="up" delay={0.1}>
            <div className="text-center mb-12">
              <p className="text-accent font-bold uppercase tracking-[0.2em] text-xs mb-3">Trusted by learners</p>
              <h2 className="font-brand text-4xl md:text-6xl font-black text-white">
                Real Reviews. Real Confidence.
              </h2>
            </div>
          </Reveal>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 mb-12">
            {TRUST_STATS.map((stat) => (
              <div key={stat.label} className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 md:p-6 text-center">
                <p className="text-2xl md:text-4xl font-black text-accent">{stat.value}</p>
                <p className="text-xs md:text-sm text-white/60 mt-2 uppercase tracking-wider">{stat.label}</p>
              </div>
            ))}
          </div>

          <div className="grid md:grid-cols-3 gap-5">
            {TESTIMONIALS.slice(0, 3).map((item) => (
              <div key={item.author} className="rounded-2xl border border-white/10 bg-black/50 p-6 md:p-7">
                <div className="flex items-center gap-1 mb-4">
                  {Array.from({ length: item.rating }).map((_, idx) => (
                    <Star key={`${item.author}-star-${idx}`} className="w-4 h-4 text-accent fill-accent" />
                  ))}
                </div>
                <p className="text-white/90 leading-relaxed">"{item.quote}"</p>
                <p className="mt-4 text-sm text-white/60">- {item.author}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <Footer />
      <DrivingTutor />
      <WhatsAppButton />
    </div>
  );
}

function App() {
  const path = window.location.pathname;

  if (
    path === APP_PATH ||
    path === APP_PATH + '/' ||
    path === LEGACY_APP_PATH ||
    path === LEGACY_APP_PATH + '/'
  ) {
    return <AppLandingPage />;
  }

  return <HomePage />;
}

export default App;
