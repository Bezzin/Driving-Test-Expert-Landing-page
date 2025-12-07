import React from 'react';
import { Instagram, Youtube, Facebook } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="py-12 border-t border-white/10 bg-black">
      <div className="mx-auto max-w-7xl px-6 flex flex-col md:flex-row items-center justify-between gap-6">
        
        <div className="flex flex-col md:flex-row items-center gap-4">
          <div className="font-brand font-bold text-xl text-white/40">
            drivingtest<span className="text-white/60">expert</span>.com
          </div>
          <p className="text-sm text-white/40">© 2025 All rights reserved.</p>
        </div>

        <div className="flex items-center gap-6">
          <a href="#" className="text-white/40 hover:text-accent transition transform hover:scale-110">
            <Instagram size={20} />
          </a>
          <a href="#" className="text-white/40 hover:text-accent transition transform hover:scale-110">
            <Youtube size={20} />
          </a>
          <a href="#" className="text-white/40 hover:text-accent transition transform hover:scale-110">
             <Facebook size={20} />
          </a>
        </div>
      </div>
    </footer>
  );
};
