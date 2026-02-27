import React from 'react';
import { APP_STORE_URL, PLAY_STORE_URL } from '../../constants';

interface BadgeProps {
  className?: string;
}

export const AppStoreBadge: React.FC<BadgeProps> = ({ className = 'h-10' }) => (
  <a href={APP_STORE_URL} target="_blank" rel="noopener noreferrer">
    <img
      src="/badges/app-store-badge.svg"
      alt="Download on the App Store"
      className={className}
    />
  </a>
);

export const PlayStoreBadge: React.FC<BadgeProps> = ({ className = 'h-10' }) => (
  <a href={PLAY_STORE_URL} target="_blank" rel="noopener noreferrer">
    <img
      src="/badges/google-play-badge.svg"
      alt="Get it on Google Play"
      className={className}
    />
  </a>
);
