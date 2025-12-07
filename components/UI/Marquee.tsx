import React from 'react';
import { BRAND_LOGOS } from '../../constants';

export const Marquee: React.FC = () => {
  return (
    <section className="py-10 border-y border-white/5 bg-black/40 backdrop-blur-sm overflow-hidden">
      <div className="max-w-7xl mx-auto overflow-hidden relative mask-linear-gradient">
         {/* Gradient Masks */}
        <div className="absolute left-0 top-0 bottom-0 w-20 z-10 bg-gradient-to-r from-bg to-transparent"></div>
        <div className="absolute right-0 top-0 bottom-0 w-20 z-10 bg-gradient-to-l from-bg to-transparent"></div>

        <div className="flex animate-marquee gap-x-16 items-center whitespace-nowrap">
          {BRAND_LOGOS.map((brand, index) => (
            <span key={`${brand}-${index}`} className="text-2xl font-black text-white/20 uppercase font-mono hover:text-white/40 transition-colors cursor-default">
              {brand}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
};
