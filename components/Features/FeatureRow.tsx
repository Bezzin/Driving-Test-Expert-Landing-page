import React from 'react';
import { Feature } from '../../types';
import { Reveal } from '../UI/Reveal';

interface FeatureRowProps {
  feature: Feature;
}

export const FeatureRow: React.FC<FeatureRowProps> = ({ feature }) => {
  const isReversed = feature.reverse;
  const isExternalLink = Boolean(
    feature.ctaLink &&
    /^(https?:)?\/\//.test(feature.ctaLink)
  );
  
  return (
    <div className={`relative ${feature.isGlassOrange ? 'group' : ''}`}>
      <div 
        className={`
          rounded-[2.5rem] p-8 md:p-16 grid md:grid-cols-2 gap-12 items-center transition-all duration-700
          ${feature.isGlassOrange 
            ? 'bg-black border border-accent/20 shadow-[0_0_40px_rgba(252,163,17,0.1)] hover:border-accent/40 hover:-translate-y-2 hover:shadow-[0_0_60px_rgba(252,163,17,0.15)]' 
            : 'bg-black border border-white/10 shadow-2xl hover:border-white/20 hover:bg-white/5'}
        `}
      >
        {/* Content Side */}
        <div className={`relative z-10 ${isReversed ? 'md:order-1' : 'md:order-2'}`}>
          <Reveal direction={isReversed ? 'right' : 'left'} delay={0.2}>
            {feature.isGlassOrange && (
                <div className="inline-block px-3 py-1 rounded-full border border-accent/30 bg-accent/10 text-accent text-xs font-bold uppercase tracking-widest mb-4 shadow-[0_0_10px_rgba(252,163,17,0.3)]">
                Top Secret Access
                </div>
            )}
            
            <h2 className="font-brand text-4xl md:text-5xl font-bold mb-6 text-white leading-tight">
                {feature.title.split('*').map((part, i) => 
                i % 2 === 1 ? <span key={i} className="text-accent inline-block animate-pulse-glow">{part}</span> : part
                )}
            </h2>
            
            <div className="space-y-4">
                {!feature.isGlassOrange && <div className="h-1 w-20 bg-accent mb-6 rounded-full"></div>}
                <p className="text-xl text-gray-300 leading-relaxed font-light">
                {feature.description}
                </p>
            </div>

            {feature.cta && (
              feature.ctaLink ? (
                <a
                  href={feature.ctaLink}
                  {...(isExternalLink ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                  className="mt-8 group/btn text-accent font-bold uppercase tracking-wide border-b border-accent/50 pb-1 hover:text-white hover:border-white transition-all flex items-center gap-2"
                >
                  {feature.cta}
                  <span className="transition-transform group-hover/btn:translate-x-1">&rarr;</span>
                </a>
              ) : (
                <button className="mt-8 group/btn text-accent font-bold uppercase tracking-wide border-b border-accent/50 pb-1 hover:text-white hover:border-white transition-all flex items-center gap-2">
                  {feature.cta} 
                  <span className="transition-transform group-hover/btn:translate-x-1">&rarr;</span>
                </button>
              )
            )}
          </Reveal>
        </div>

        {/* Image Side */}
        <div className={`relative flex justify-center items-center ${isReversed ? 'md:order-2' : 'md:order-1'}`}>
           <Reveal direction={isReversed ? 'left' : 'right'} delay={0.3} className="w-full">
            {feature.isGlassOrange && (
                <div className="absolute -inset-10 bg-orange-500/10 blur-[60px] rounded-full opacity-50 group-hover:opacity-80 transition duration-1000 animate-pulse"></div>
            )}
            
            <div className={`relative z-10 w-full flex justify-center ${feature.isGlassOrange ? 'animate-float' : 'animate-float-delayed'}`}>
                <img 
                src={feature.image} 
                alt={feature.title} 
                className={`
                    w-full h-auto max-h-[400px] object-contain 
                    transform transition-all duration-700 hover:scale-105 hover:rotate-2
                    ${feature.isGlassOrange ? 'brightness-110' : 'opacity-90 hover:opacity-100'}
                `}
                />
            </div>
          </Reveal>
        </div>

      </div>
    </div>
  );
};
