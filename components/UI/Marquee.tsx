import React from 'react';
import { Star } from 'lucide-react';
import { TESTIMONIALS } from '../../constants';

export const Marquee: React.FC = () => {
  const scrollingTestimonials = [...TESTIMONIALS, ...TESTIMONIALS];

  return (
    <section className="py-10 border-y border-white/5 bg-black/40 backdrop-blur-sm overflow-hidden">
      <div className="max-w-7xl mx-auto overflow-hidden relative mask-linear-gradient">
         {/* Gradient Masks */}
        <div className="absolute left-0 top-0 bottom-0 w-20 z-10 bg-gradient-to-r from-bg to-transparent"></div>
        <div className="absolute right-0 top-0 bottom-0 w-20 z-10 bg-gradient-to-l from-bg to-transparent"></div>

        <div className="flex animate-marquee gap-x-8 items-center whitespace-nowrap">
          {scrollingTestimonials.map((item, index) => (
            <span
              key={`${item.author}-${index}`}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm md:text-base text-white/80"
            >
              <Star className="w-4 h-4 text-accent fill-accent" />
              "{item.quote}" - {item.author}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
};
