import React from 'react';
import { ArrowRight, PlayCircle } from 'lucide-react';
import { ASSETS } from '../../constants';
import { Reveal } from '../UI/Reveal';

export const Hero: React.FC = () => {
  return (
    <section className="min-h-[100svh] flex items-center pt-20 relative overflow-hidden" id="top">
      
      {/* Background Banner Image Layer */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-bg z-0"></div>
        
        {/* Main Image with cinematic blending */}
        <div className="absolute inset-0 z-10">
             <img 
                src={ASSETS.heroInstructor} 
                alt="Driving Instructor" 
                className="w-full h-full object-cover object-top opacity-60 lg:opacity-80"
             />
             {/* Gradient Overlays for Text Readability */}
             <div className="absolute inset-0 bg-gradient-to-r from-bg via-bg/90 to-transparent lg:via-bg/80"></div>
             <div className="absolute inset-0 bg-gradient-to-t from-bg via-transparent to-transparent opacity-80"></div>
        </div>

        {/* Abstract Abstract Ambience */}
        <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1496360879793-27c11d279e2c?q=80&w=2000&auto=format&fit=crop')] opacity-10 bg-cover bg-center mix-blend-overlay z-10"></div>
      </div>

      {/* Content Layer */}
      <div className="relative z-20 w-full max-w-7xl mx-auto px-6 flex flex-col justify-center min-h-[60vh]">
        <div className="max-w-4xl">
          <div className="relative mb-6">
            <Reveal direction="down" duration={0.8}>
                <h1 className="font-brand text-5xl sm:text-6xl md:text-8xl lg:text-9xl font-black tracking-tighter leading-[0.9] italic uppercase text-white drop-shadow-2xl">
                We Get <br />
                <span className="text-accent relative inline-block mt-2">
                    You Passed
                    {/* SVG Arrow */}
                    <svg className="absolute -bottom-8 -left-4 w-48 h-16 opacity-90" viewBox="0 0 200 60" xmlns="http://www.w3.org/2000/svg">
                    <path 
                        className="stroke-accent stroke-[4] fill-none stroke-linecap-round animate-draw [stroke-dasharray:1000] [stroke-dashoffset:1000]" 
                        d="M10,20 C50,20 120,25 180,10 M170,0 L180,10 L165,20" 
                    />
                    </svg>
                </span>
                </h1>
            </Reveal>
          </div>

          <Reveal delay={0.3} width="100%">
            <p className="mt-8 text-lg md:text-2xl text-white/90 max-w-2xl font-light leading-relaxed border-l-4 border-accent pl-6 drop-shadow-md">
                Here at <strong className="text-white">drivingtestexpert.com</strong>, we have designed never-before-seen <span className="text-accent font-bold">proprietary systems</span> to help you pass your driving test <strong className="text-white text-2xl italic uppercase ml-1 font-brand">FASTER</strong> and <strong className="text-white text-2xl italic uppercase font-brand">EASIER</strong> than ever.
            </p>
          </Reveal>

          <Reveal delay={0.5}>
            <div className="mt-12 flex flex-col sm:flex-row items-start sm:items-center gap-6">
                <button className="group relative rounded-full bg-accent px-8 py-5 text-black font-extrabold text-xl transition-transform hover:scale-105 active:scale-95 shadow-[0_0_30px_rgba(252,163,17,0.5)] flex items-center gap-2 overflow-hidden">
                <div className="absolute inset-0 -translate-x-full group-hover:animate-shimmer bg-shimmer-gradient z-0"></div>
                <span className="relative z-10 flex items-center gap-2">
                    Start Learning
                    <ArrowRight className="w-6 h-6 transition-transform group-hover:translate-x-1" />
                </span>
                </button>
                <button className="group rounded-full px-8 py-5 text-white font-semibold text-lg border border-white/20 hover:border-accent hover:text-accent transition-colors backdrop-blur-md flex items-center gap-2 bg-black/30">
                <PlayCircle className="w-6 h-6 transition-transform group-hover:scale-110" />
                Watch Success Stories
                </button>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
};