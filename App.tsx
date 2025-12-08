import React, { useState } from 'react';
import { Navbar } from './components/Layout/Navbar';
import { Hero } from './components/Features/Hero';
import { Marquee } from './components/UI/Marquee';
import { FeatureRow } from './components/Features/FeatureRow';
import { Footer } from './components/Layout/Footer';
import { DrivingTutor } from './components/AI/DrivingTutor';
import { ASSETS } from './constants';
import { Feature } from './types';
import { Reveal } from './components/UI/Reveal';
import { ArrowRight, ChevronDown, Sparkles, CheckCircle } from 'lucide-react';

function App() {
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    currentStatus: "I haven't started learning"
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');
  
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitStatus('idle');

    try {
      const response = await fetch('/.netlify/functions/submit-waitlist', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setSubmitStatus('success');
        setFormData({
          fullName: '',
          email: '',
          currentStatus: "I haven't started learning"
        });
        // Reset success message after 5 seconds
        setTimeout(() => setSubmitStatus('idle'), 5000);
      } else {
        const error = await response.json();
        throw new Error(error.message || 'Failed to submit form');
      }
    } catch (error) {
      console.error('Form submission error:', error);
      setSubmitStatus('error');
      setTimeout(() => setSubmitStatus('idle'), 5000);
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const features: Feature[] = [
    {
      id: 'retest',
      title: 'The *ReTest* App',
      subtitle: 'Beat The Wait',
      description: "Don't get stuck in the backlog. ReTest is our premium driving test cancellations app. We scan the DVSA system 24/7 to snag you an earlier test date, getting you on the road months sooner.",
      image: ASSETS.reTestBox, 
      reverse: false,
      cta: 'JOIN THE WAITLIST',
      ctaLink: '#contact',
      isGlassOrange: true
    },
    {
      id: 'routes',
      title: 'Know Your *Routes*',
      subtitle: 'Turn-by-Turn Navigation',
      description: "Stop guessing where you'll go. Our 'Driving Test Routes' system features full turn-by-turn navigation for every possible test route in your local area, so there are no surprises on the big day.",
      image: ASSETS.routesBox, 
      reverse: true,
      cta: 'GET A FREE ROUTE',
      ctaLink: 'https://josh-the-driving-instructor-crawfish.sender.site/',
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

      <main id="systems" className="relative z-10 py-12 flex flex-col gap-12 md:gap-24 px-6 max-w-7xl mx-auto">
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

      <section id="contact" className="py-24 md:py-36 relative z-10 overflow-hidden">
         {/* Decorative ambient light */}
         <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-accent/10 rounded-full blur-[120px] pointer-events-none opacity-50 mix-blend-screen"></div>

        <div className="relative z-20 w-full flex justify-center">
          <div className="w-full max-w-4xl px-6">
          <Reveal direction="up" delay={0.2}>
            <h2 className="font-brand text-5xl md:text-7xl font-black tracking-tight mb-6 text-white leading-none drop-shadow-lg text-center">
                <span className="inline-block pl-10 md:pl-20 lg:pl-28">Start Your <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-yellow-200">Engine</span></span>
            </h2>
          </Reveal>
          
          <Reveal direction="up" delay={0.4} width="100%">
            <div className="mt-16 relative group max-w-2xl mx-auto">
                {/* Outer Glow Ring */}
                <div className="absolute -inset-0.5 bg-gradient-to-r from-accent via-yellow-500 to-accent rounded-[2.1rem] opacity-30 group-hover:opacity-70 blur-md transition duration-500 animate-pulse-glow"></div>
                
                {/* Form Container */}
                <form onSubmit={handleSubmit} className="relative bg-[#0d0d0d] ring-1 ring-white/10 rounded-[2rem] p-8 md:p-12 grid grid-cols-1 md:grid-cols-2 gap-6 text-left shadow-2xl backdrop-blur-xl">
                    
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

                    {/* Success Message */}
                    {submitStatus === 'success' && (
                        <div className="md:col-span-2 p-4 rounded-xl bg-green-500/10 border border-green-500/30 flex items-center gap-3 text-green-400">
                            <CheckCircle size={20} />
                            <span className="text-sm font-medium">Success! You've been added to the waitlist.</span>
                        </div>
                    )}

                    {/* Error Message */}
                    {submitStatus === 'error' && (
                        <div className="md:col-span-2 p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3 text-red-400">
                            <span className="text-sm font-medium">Error submitting form. Please try again.</span>
                        </div>
                    )}

                    {/* Inputs */}
                    <div className="space-y-2 group/input">
                        <label htmlFor="fullName" className="text-xs font-bold uppercase tracking-wide text-white/40 group-focus-within/input:text-accent transition-colors ml-1">Full Name</label>
                        <input 
                            id="fullName"
                            name="fullName"
                            type="text"
                            required
                            value={formData.fullName}
                            onChange={handleInputChange}
                            disabled={isSubmitting}
                            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-4 text-white placeholder-white/20 focus:outline-none focus:border-accent/50 focus:bg-white/10 focus:ring-1 focus:ring-accent/50 transition-all shadow-inner disabled:opacity-50 disabled:cursor-not-allowed" 
                            placeholder="Enter your name" 
                        />
                    </div>

                    <div className="space-y-2 group/input">
                        <label htmlFor="email" className="text-xs font-bold uppercase tracking-wide text-white/40 group-focus-within/input:text-accent transition-colors ml-1">Email Address</label>
                        <input 
                            id="email"
                            name="email"
                            type="email"
                            required
                            value={formData.email}
                            onChange={handleInputChange}
                            disabled={isSubmitting}
                            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-4 text-white placeholder-white/20 focus:outline-none focus:border-accent/50 focus:bg-white/10 focus:ring-1 focus:ring-accent/50 transition-all shadow-inner disabled:opacity-50 disabled:cursor-not-allowed" 
                            placeholder="name@example.com" 
                        />
                    </div>

                    <div className="md:col-span-2 space-y-2 group/input">
                        <label htmlFor="currentStatus" className="text-xs font-bold uppercase tracking-wide text-white/40 group-focus-within/input:text-accent transition-colors ml-1">Current Status</label>
                        <div className="relative">
                            <select 
                                id="currentStatus"
                                name="currentStatus"
                                value={formData.currentStatus}
                                onChange={handleInputChange}
                                disabled={isSubmitting}
                                className="w-full appearance-none bg-white/5 border border-white/10 rounded-xl px-4 py-4 text-white focus:outline-none focus:border-accent/50 focus:bg-white/10 focus:ring-1 focus:ring-accent/50 transition-all cursor-pointer shadow-inner disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <option value="I haven't started learning" className="bg-card">I haven't started learning</option>
                                <option value="I'm currently taking lessons" className="bg-card">I'm currently taking lessons</option>
                                <option value="I've failed before (help me!)" className="bg-card">I've failed before (help me!)</option>
                                <option value="I have a test booked soon" className="bg-card">I have a test booked soon</option>
                            </select>
                            <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" size={18} />
                        </div>
                    </div>

                    {/* Button */}
                    <button 
                        type="submit" 
                        disabled={isSubmitting}
                        className="md:col-span-2 mt-6 group/btn relative w-full overflow-hidden rounded-xl bg-accent p-4 transition-all hover:bg-white hover:scale-[1.01] active:scale-[0.98] shadow-[0_0_20px_rgba(252,163,17,0.3)] hover:shadow-[0_0_40px_rgba(252,163,17,0.5)] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                    >
                        <div className="relative z-10 flex items-center justify-center gap-2 font-black text-black text-lg uppercase tracking-wide">
                            {isSubmitting ? 'Submitting...' : 'Get My Free Plan'}
                            {!isSubmitting && <ArrowRight className="transition-transform group-hover/btn:translate-x-1" size={20} />}
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
        </div>
      </section>

      <Footer />
      <DrivingTutor />
    </div>
  );
}

export default App;
