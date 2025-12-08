import React from 'react';
import { Instagram, Youtube, Facebook } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="py-12 border-t border-white/10 bg-black">
      <div className="mx-auto max-w-7xl px-6">
        {/* Main Footer Content */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 mb-8">
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
            <a href="https://www.youtube.com/@JoshRamwell" target="_blank" rel="noopener noreferrer" className="text-white/40 hover:text-accent transition transform hover:scale-110">
              <Youtube size={20} />
            </a>
            <a href="#" className="text-white/40 hover:text-accent transition transform hover:scale-110">
               <Facebook size={20} />
            </a>
          </div>
        </div>

        {/* Legal Links */}
        <div className="border-t border-white/5 pt-8">
          <div className="flex flex-col md:flex-row items-center justify-center gap-4 md:gap-8 text-sm">
            <a 
              href="https://destiny-date-598.notion.site/Privacy-Policy-Test-Routes-Expert-2c04994b32ba8119ada3c1e7911d4398" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-white/40 hover:text-accent transition-colors"
            >
              Privacy Policy
            </a>
            <span className="hidden md:block text-white/20">•</span>
            <a 
              href="https://destiny-date-598.notion.site/Terms-of-Service-Test-Routes-Expert-2c04994b32ba81eea41cd2f9fab3e12e" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-white/40 hover:text-accent transition-colors"
            >
              Terms of Service
            </a>
            <span className="hidden md:block text-white/20">•</span>
            <a 
              href="https://destiny-date-598.notion.site/Support-Test-Routes-Expert-2c04994b32ba817abb69dab932ae981f" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-white/40 hover:text-accent transition-colors"
            >
              Support
            </a>
            <span className="hidden md:block text-white/20">•</span>
            <a 
              href="mailto:support@drivingtestexpert.com"
              className="text-white/40 hover:text-accent transition-colors"
            >
              Contact Us
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
};
