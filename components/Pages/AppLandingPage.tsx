import React, { useState } from 'react';
import { Navbar } from '../Layout/Navbar';
import { Footer } from '../Layout/Footer';
import { Reveal } from '../UI/Reveal';
import { ASSETS, PLAY_STORE_URL } from '../../constants';
import { ArrowRight, CheckCircle, Smartphone, Apple, MapPin, Navigation, Shield } from 'lucide-react';

export const AppLandingPage: React.FC = () => {
  const [formData, setFormData] = useState({ fullName: '', email: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitStatus('idle');

    try {
      const response = await fetch('/.netlify/functions/submit-waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fullName: formData.fullName,
          email: formData.email,
          currentStatus: 'iPhone App Waitlist - Early Access',
        }),
      });

      if (response.ok) {
        setSubmitStatus('success');
        setFormData({ fullName: '', email: '' });
        setTimeout(() => setSubmitStatus('idle'), 5000);
      } else {
        throw new Error('Failed to submit');
      }
    } catch (error) {
      setSubmitStatus('error');
      setTimeout(() => setSubmitStatus('idle'), 5000);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-bg min-h-screen text-white selection:bg-accent/30 selection:text-white overflow-x-hidden">
      {/* Background Texture */}
      <div className="fixed inset-0 z-0 pointer-events-none opacity-20 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]"></div>

      <Navbar />

      {/* Hero Section */}
      <section className="min-h-[100svh] flex items-center pt-20 relative overflow-hidden" id="top">
        {/* Background gradient */}
        <div className="absolute inset-0 z-0">
          <div className="absolute inset-0 bg-bg"></div>
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-accent/15 rounded-full blur-[150px] pointer-events-none"></div>
          <div className="absolute bottom-0 left-0 right-0 h-1/2 bg-gradient-to-t from-bg to-transparent"></div>
        </div>

        <div className="relative z-10 w-full max-w-5xl mx-auto px-6 text-center py-20">
          <Reveal direction="down" duration={0.8}>
            <div className="inline-block px-4 py-2 rounded-full border border-accent/30 bg-accent/10 text-accent text-sm font-bold uppercase tracking-widest mb-8 shadow-[0_0_15px_rgba(252,163,17,0.2)]">
              <MapPin className="inline w-4 h-4 mr-2 -mt-0.5" />
              Test Route Expert App
            </div>
          </Reveal>

          <Reveal direction="up" delay={0.2}>
            <h1 className="font-brand text-4xl sm:text-5xl md:text-7xl lg:text-8xl font-black tracking-tight leading-[1.05] text-white mb-8">
              Practise{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-yellow-200">
                REAL
              </span>{' '}
              Driving Test Routes{' '}
              <span className="block mt-2 text-3xl sm:text-4xl md:text-5xl lg:text-6xl text-white/80 font-bold">
                Before Your Test
              </span>
            </h1>
          </Reveal>

          <Reveal direction="up" delay={0.4}>
            <p className="text-lg md:text-xl text-white/70 max-w-2xl mx-auto leading-relaxed mb-6">
              Turn-by-turn navigation for every test route at your local test centre.
              No surprises on the big day.
            </p>
          </Reveal>

          {/* Feature pills */}
          <Reveal direction="up" delay={0.5}>
            <div className="flex flex-wrap justify-center gap-3 mb-16">
              <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-white/60 text-sm">
                <Navigation className="w-4 h-4 text-accent" />
                Turn-by-Turn Nav
              </div>
              <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-white/60 text-sm">
                <MapPin className="w-4 h-4 text-accent" />
                Real DVSA Routes
              </div>
              <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-white/60 text-sm">
                <Shield className="w-4 h-4 text-accent" />
                Free Route Included
              </div>
            </div>
          </Reveal>

          {/* Two Cards: Android + iPhone */}
          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">

            {/* Android Card */}
            <Reveal direction="left" delay={0.3}>
              <div className="relative group h-full">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-green-500 via-green-400 to-green-500 rounded-[2.1rem] opacity-20 group-hover:opacity-50 blur-md transition duration-500"></div>
                <div className="relative bg-[#0d0d0d] ring-1 ring-white/10 rounded-[2rem] p-8 md:p-10 text-center h-full flex flex-col">
                  <div className="flex justify-center mb-6">
                    <div className="h-16 w-16 flex items-center justify-center rounded-2xl bg-green-500/10 text-green-400 border border-green-500/20">
                      <Smartphone size={32} />
                    </div>
                  </div>

                  <h2 className="font-brand text-2xl md:text-3xl font-bold text-white mb-3">
                    Android Users
                  </h2>
                  <p className="text-white/60 mb-8 leading-relaxed flex-grow">
                    Download the app now and start practising your local test routes today.
                  </p>

                  <a
                    href={PLAY_STORE_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group/btn relative w-full overflow-hidden rounded-xl bg-green-500 p-4 transition-all hover:bg-green-400 hover:scale-[1.02] active:scale-[0.98] shadow-[0_0_20px_rgba(34,197,94,0.3)] hover:shadow-[0_0_40px_rgba(34,197,94,0.5)] block"
                  >
                    <div className="relative z-10 flex items-center justify-center gap-3 font-black text-black text-lg uppercase tracking-wide">
                      <svg viewBox="0 0 24 24" className="w-6 h-6 fill-current">
                        <path d="M3.18 23.71c-.35-.2-.59-.56-.59-.98V1.27c0-.42.24-.78.6-.98l11.26 11.71L3.18 23.71zm1.4.9l12.52-7.24-2.76-2.87L4.58 24.61zM20.73 11.3L17.6 9.49 14.7 12l2.9 2.51 3.13-1.81c.56-.32.56-1.08 0-1.4zM4.58-.62l9.76 10.11 2.76-2.87L4.58-.62z"/>
                      </svg>
                      Get it on Google Play
                    </div>
                    <div className="absolute inset-0 group-hover/btn:animate-shine bg-gradient-to-r from-transparent via-white/30 to-transparent z-0"></div>
                  </a>

                  <p className="text-white/30 text-xs mt-4 uppercase tracking-wider font-medium">
                    Available Now
                  </p>
                </div>
              </div>
            </Reveal>

            {/* iPhone Card */}
            <Reveal direction="right" delay={0.3}>
              <div className="relative group h-full">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-accent via-yellow-500 to-accent rounded-[2.1rem] opacity-20 group-hover:opacity-50 blur-md transition duration-500 animate-pulse-glow"></div>
                <div className="relative bg-[#0d0d0d] ring-1 ring-white/10 rounded-[2rem] p-8 md:p-10 text-center h-full flex flex-col">
                  <div className="flex justify-center mb-6">
                    <div className="h-16 w-16 flex items-center justify-center rounded-2xl bg-accent/10 text-accent border border-accent/20">
                      <Apple size={32} />
                    </div>
                  </div>

                  <h2 className="font-brand text-2xl md:text-3xl font-bold text-white mb-3">
                    iPhone Users
                  </h2>
                  <p className="text-white/60 mb-2 leading-relaxed">
                    Apple version coming soon!
                  </p>
                  <p className="text-accent font-semibold text-sm mb-6">
                    Join the early access list and get a free test route on launch.
                  </p>

                  <form onSubmit={handleSubmit} className="space-y-4 flex-grow flex flex-col">
                    {submitStatus === 'success' && (
                      <div className="p-3 rounded-xl bg-green-500/10 border border-green-500/30 flex items-center gap-2 text-green-400 text-sm">
                        <CheckCircle size={16} />
                        <span className="font-medium">You're on the list!</span>
                      </div>
                    )}

                    {submitStatus === 'error' && (
                      <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                        Something went wrong. Please try again.
                      </div>
                    )}

                    <input
                      name="fullName"
                      type="text"
                      required
                      value={formData.fullName}
                      onChange={handleInputChange}
                      disabled={isSubmitting}
                      placeholder="Your name"
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/20 focus:outline-none focus:border-accent/50 focus:bg-white/10 focus:ring-1 focus:ring-accent/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    />

                    <input
                      name="email"
                      type="email"
                      required
                      value={formData.email}
                      onChange={handleInputChange}
                      disabled={isSubmitting}
                      placeholder="your@email.com"
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/20 focus:outline-none focus:border-accent/50 focus:bg-white/10 focus:ring-1 focus:ring-accent/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    />

                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="mt-auto group/btn relative w-full overflow-hidden rounded-xl bg-accent p-4 transition-all hover:bg-white hover:scale-[1.02] active:scale-[0.98] shadow-[0_0_20px_rgba(252,163,17,0.3)] hover:shadow-[0_0_40px_rgba(252,163,17,0.5)] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                    >
                      <div className="relative z-10 flex items-center justify-center gap-2 font-black text-black text-base uppercase tracking-wide">
                        {isSubmitting ? 'Joining...' : 'Join Early Access'}
                        {!isSubmitting && <ArrowRight className="transition-transform group-hover/btn:translate-x-1" size={18} />}
                      </div>
                      <div className="absolute inset-0 group-hover/btn:animate-shine bg-gradient-to-r from-transparent via-white/40 to-transparent z-0"></div>
                    </button>
                  </form>

                  <p className="text-white/20 text-[10px] mt-4 uppercase tracking-widest font-medium">
                    No Spam - Free Route on Launch
                  </p>
                </div>
              </div>
            </Reveal>
          </div>

          {/* Back to main site link */}
          <Reveal direction="up" delay={0.6}>
            <div className="mt-16 pt-8 border-t border-white/5">
              <a
                href="/"
                className="text-white/40 hover:text-accent transition-colors text-sm inline-flex items-center gap-2"
              >
                <ArrowRight className="rotate-180 w-4 h-4" />
                Back to drivingtestexpert.com
              </a>
            </div>
          </Reveal>
        </div>
      </section>

      <Footer />
    </div>
  );
};
