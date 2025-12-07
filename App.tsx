import React from 'react';
import { Navbar } from './components/Layout/Navbar';
import { Hero } from './components/Features/Hero';
import { Marquee } from './components/UI/Marquee';
import { FeatureRow } from './components/Features/FeatureRow';
import { Footer } from './components/Layout/Footer';
import { DrivingTutor } from './components/AI/DrivingTutor';
import { ASSETS } from './constants';
import { Feature } from './types';
import { Reveal } from './components/UI/Reveal';
import { ArrowRight, ChevronDown, Sparkles } from 'lucide-react';

function App() {
  
  const features: Feature[] = [
    {
      id: 'retest',
      title: 'The *ReTest* App',
      subtitle: 'Beat The Wait',
      description: "Don't get stuck in the backlog. ReTest is our premium driving test cancellations app. We scan the DVSA system 24/7 to snag you an earlier test date, getting you on the road months sooner.",
      image: ASSETS.reTestBox, 
      reverse: false,
      cta: 'Download the App',
      isGlassOrange: true
    },
    {
      id: 'routes',
      title: 'Know Your *Routes*',
      subtitle: 'Turn-by-Turn Navigation',
      description: "Stop guessing where you'll go. Our 'Driving Test Routes' system features full turn-by-turn navigation for every possible test route in your local area, so there are no surprises on the big day.",
      image: ASSETS.routesBox, 
      reverse: true,
      cta: 'Find My Test Centre',
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

      <main id="systems" className="relative z-10 py-12 flex flex-col gap-12 md:gap-24 px-6 max-w-7xl mx-auto">
        {features.map((feature) => (
          <FeatureRow key={feature.id} feature={feature} />
        ))}
      </main>

      <section id="results" className="py-24 border-t border-white/10 relative z-10 bg-black/50 backdrop-blur-sm">
        <Reveal width="100%" direction="up">
            <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
                {[
                    { val: '98%', label: 'Pass Rate' },
                    { val: '10k+', label: 'Students' },
                    { val: '24h', label: 'Support' },
                    { val: '#1', label: 'Rated Course' },
                ].map((stat, i) => (
                    <div key={i} className="group cursor-default transform hover:-translate-y-1 transition duration-300">
                        <div className="text-4xl md:text-5xl font-black text-white group-hover:text-accent transition-colors duration-300">{stat.val}</div>
                        <div className="text-accent text-sm font-bold uppercase tracking-widest mt-2 opacity-70 group-hover:opacity-100 transition-opacity">{stat.label}</div>
                    </div>
                ))}
            </div>
        </Reveal>
      </section>

      <section id="contact" className="py-24 md:py-36 relative z-10 overflow-hidden">
         {/* Decorative ambient light */}
         <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-accent/10 rounded-full blur-[120px] pointer-events-none opacity-50 mix-blend-screen"></div>

        <div className="mx-auto max-w-4xl px-6 text-center relative z-20">
          <Reveal direction="up" delay={0.2}>
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-accent/20 bg-accent/5 text-accent text-xs font-bold uppercase tracking-widest mb-6 backdrop-blur-md shadow-[0_0_15px_rgba(252,163,17,0.2)]">
              <Sparkles size={12} />
              Limited Intake 2025
            </div>
            <h2 className="font-brand text-5xl md:text-7xl font-black tracking-tight mb-6 text-white leading-none drop-shadow-lg">
                Start Your <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-yellow-200">Engine</span>
            </h2>
            <p className="mt-4 text-white/60 text-lg md:text-xl max-w-2xl mx-auto">
              Don't leave your license to chance. Get the unfair advantage that 10,000+ students are using to pass first time.
            </p>
          </Reveal>
          
          <Reveal direction="up" delay={0.4} width="100%">
            <div className="mt-16 relative group max-w-2xl mx-auto">
                {/* Outer Glow Ring */}
                <div className="absolute -inset-0.5 bg-gradient-to-r from-accent via-yellow-500 to-accent rounded-[2.1rem] opacity-30 group-hover:opacity-70 blur-md transition duration-500 animate-pulse-glow"></div>
                
                {/* Form Container */}
                <form className="relative bg-[#0d0d0d] ring-1 ring-white/10 rounded-[2rem] p-8 md:p-12 grid grid-cols-1 md:grid-cols-2 gap-6 text-left shadow-2xl backdrop-blur-xl">
                    
                    {/* Header inside form */}
                    <div className="md:col-span-2 mb-4 flex items-center justify-between border-b border-white/5 pb-6">
                         <div>
                            <h3 className="text-2xl font-bold text-white">Priority Access</h3>
                            <p className="text-white/40 text-sm mt-1">Join the waitlist for our next cohort.</p>
                         </div>
                         <div className="hidden md:flex h-12 w-12 items-center justify-center rounded-full bg-accent/10 text-accent border border-accent/20 shadow-[0_0_15px_rgba(252,163,17,0.1)]">
                            <ArrowRight size={22} className="-rotate-45" />
                         </div>
                    </div>

                    {/* Inputs */}
                    <div className="space-y-2 group/input">
                        <label className="text-xs font-bold uppercase tracking-wide text-white/40 group-focus-within/input:text-accent transition-colors ml-1">Full Name</label>
                        <input className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-4 text-white placeholder-white/20 focus:outline-none focus:border-accent/50 focus:bg-white/10 focus:ring-1 focus:ring-accent/50 transition-all shadow-inner" placeholder="Enter your name" />
                    </div>

                    <div className="space-y-2 group/input">
                        <label className="text-xs font-bold uppercase tracking-wide text-white/40 group-focus-within/input:text-accent transition-colors ml-1">Email Address</label>
                        <input className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-4 text-white placeholder-white/20 focus:outline-none focus:border-accent/50 focus:bg-white/10 focus:ring-1 focus:ring-accent/50 transition-all shadow-inner" placeholder="name@example.com" />
                    </div>

                    <div className="md:col-span-2 space-y-2 group/input">
                        <label className="text-xs font-bold uppercase tracking-wide text-white/40 group-focus-within/input:text-accent transition-colors ml-1">Current Status</label>
                        <div className="relative">
                            <select className="w-full appearance-none bg-white/5 border border-white/10 rounded-xl px-4 py-4 text-white focus:outline-none focus:border-accent/50 focus:bg-white/10 focus:ring-1 focus:ring-accent/50 transition-all cursor-pointer shadow-inner">
                                <option className="bg-card">I haven't started learning</option>
                                <option className="bg-card">I'm currently taking lessons</option>
                                <option className="bg-card">I've failed before (help me!)</option>
                                <option className="bg-card">I have a test booked soon</option>
                            </select>
                            <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" size={18} />
                        </div>
                    </div>

                    {/* Button */}
                    <button type="button" className="md:col-span-2 mt-6 group/btn relative w-full overflow-hidden rounded-xl bg-accent p-4 transition-all hover:bg-white hover:scale-[1.01] active:scale-[0.98] shadow-[0_0_20px_rgba(252,163,17,0.3)] hover:shadow-[0_0_40px_rgba(252,163,17,0.5)]">
                        <div className="relative z-10 flex items-center justify-center gap-2 font-black text-black text-lg uppercase tracking-wide">
                            Get My Free Plan
                            <ArrowRight className="transition-transform group-hover/btn:translate-x-1" size={20} />
                        </div>
                        {/* Shine effect */}
                        <div className="absolute inset-0 group-hover/btn:animate-shine bg-gradient-to-r from-transparent via-white/40 to-transparent z-0"></div>
                    </button>
                    
                    <p className="md:col-span-2 text-center text-[10px] text-white/20 uppercase tracking-widest mt-2 font-medium">
                        Secure SSL Encryption • No Spam Guarantee
                    </p>
                </form>
            </div>
          </Reveal>
        </div>
      </section>

      <Footer />
      <DrivingTutor />
    </div>
  );
}

export default App;