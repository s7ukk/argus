import React from 'react';

interface Props { size?: number; className?: string; style?: React.CSSProperties; }

export const StarburnLogo: React.FC<Props> = ({ size = 24, className = '', style }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className} style={style}>
    <defs>
      <radialGradient id="sg1" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stopColor="#ffffff" />
        <stop offset="45%" stopColor="var(--accent, #ffffff)" />
        <stop offset="100%" stopColor="#6d28d9" />
      </radialGradient>
      <radialGradient id="sg2" cx="50%" cy="30%" r="60%">
        <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9" />
        <stop offset="100%" stopColor="var(--accent, #ffffff)" stopOpacity="0" />
      </radialGradient>
    </defs>
    <circle cx="16" cy="16" r="14" fill="url(#sg1)" opacity="0.15" />
    <path d="M16 2 L18.2 13.3 L29 10 L20.5 18 L29 26 L18.2 22.7 L16 34 L13.8 22.7 L3 26 L11.5 18 L3 10 L13.8 13.3 Z" fill="url(#sg1)" />
    <circle cx="16" cy="16" r="4" fill="url(#sg2)" />
  </svg>
);

// Telegram
export const TelegramIcon: React.FC<Props> = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="12" fill="#26a5e4" />
    <path d="M5.5 11.8l12.5-4.8c.58-.21 1.08.14.9.98l-2.12 10c-.16.7-.58.87-1.17.54l-3.27-2.41-1.58 1.52c-.17.17-.32.32-.66.32l.24-3.36 6.1-5.52c.27-.24-.06-.37-.4-.13L7.12 14.14 4 13.12c-.66-.2-.67-.66.14-.98z" fill="white" />
  </svg>
);

// Discord
export const DiscordIcon: React.FC<Props> = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <rect width="24" height="24" rx="6" fill="#5865F2" />
    <path d="M18.59 6.19A16.4 16.4 0 0015.03 5c-.16.29-.34.68-.47.99a15.28 15.28 0 00-4.12 0 10.8 10.8 0 00-.48-.99 16.36 16.36 0 00-3.57 1.2C4.44 10.15 3.85 14.02 4.14 17.84c1.5 1.1 2.95 1.77 4.38 2.21.35-.48.67-.99.94-1.53a10.7 10.7 0 01-1.49-.71c.12-.09.24-.19.36-.28a11.67 11.67 0 009.35 0c.12.1.24.19.36.28-.48.28-.97.51-1.49.71.27.54.59 1.05.94 1.53 1.43-.44 2.89-1.11 4.38-2.21.36-4.37-.61-8.16-2.28-11.65zm-8.2 9.31c-.9 0-1.63-.82-1.63-1.83s.72-1.83 1.63-1.83c.9 0 1.64.82 1.63 1.83 0 1.01-.73 1.83-1.63 1.83zm6.02 0c-.9 0-1.63-.82-1.63-1.83s.72-1.83 1.63-1.83c.9 0 1.64.82 1.63 1.83 0 1.01-.73 1.83-1.63 1.83z" fill="white" />
  </svg>
);

// Steam
export const SteamIcon: React.FC<Props> = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <defs>
      <linearGradient id="stm" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor="#1b2838" />
        <stop offset="100%" stopColor="#2a475e" />
      </linearGradient>
    </defs>
    <rect width="24" height="24" rx="6" fill="url(#stm)" />
    <path d="M12 3C7.03 3 3 7.03 3 12c0 4.42 3.04 8.12 7.13 9.16l1.33-3.29a3 3 0 114.08-2.79l3.3-1.36C18.12 17.96 15.3 21 12 21c-4.97 0-9-4.03-9-9s4.03-9 9-9 9 4.03 9 9c0 .83-.12 1.63-.33 2.39l-2.96 1.22a3 3 0 00-5.71 0L9.56 18.5C6.36 17.42 4 14.47 4 11c0-4.41 3.59-8 8-8s8 3.59 8 8c0 .9-.15 1.77-.43 2.58l-.01.03-2.95 1.22A3 3 0 0012 15a3 3 0 003-3 3 3 0 00-3-3z" fill="#c7d5e0" />
  </svg>
);

// Spotify
export const SpotifyIcon: React.FC<Props> = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="12" fill="#1DB954" />
    <path d="M17.9 10.9C14.7 9 9.35 8.8 6.3 9.75c-.5.15-1-.15-1.15-.6-.15-.5.15-1 .6-1.15 3.55-1.05 9.4-.85 13.1 1.35.45.25.6.85.35 1.3-.25.35-.85.5-1.3.25zm-.1 2.8c-.25.35-.7.5-1.05.25-2.7-1.65-6.8-2.15-9.95-1.15-.4.1-.85-.1-.95-.5-.1-.4.1-.85.5-.95 3.65-1.1 8.15-.55 11.25 1.35.3.15.45.65.2 1zm-1.2 2.75c-.2.3-.55.4-.85.2-2.35-1.45-5.3-1.75-8.8-.95-.35.1-.65-.15-.75-.45-.1-.35.15-.65.45-.75 3.8-.85 7.1-.5 9.7 1.1.35.15.4.55.25.85z" fill="white" />
  </svg>
);

// Chrome
export const ChromeIcon: React.FC<Props> = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="12" fill="#fff" />
    <circle cx="12" cy="12" r="4.5" fill="#4285F4" />
    <path d="M12 7.5h9.18A12 12 0 0112 0 12 12 0 003 3.72l4.59 7.95A4.5 4.5 0 0112 7.5z" fill="#EA4335" />
    <path d="M20.45 17.25A12 12 0 0021 12c0-1.56-.3-3.05-.82-4.5H12a4.5 4.5 0 014.5 4.5 4.5 4.5 0 01-.68 2.38l4.63 2.87z" fill="#FBBC05" />
    <path d="M7.59 16.45A4.5 4.5 0 0012 16.5a4.5 4.5 0 003.82-2.12l-4.63-2.87c-.37.63-.96 1.12-1.68 1.37L7.59 16.45z" fill="none" />
    <path d="M7.5 12A4.5 4.5 0 0112 7.5l-4.59-7.95A12 12 0 000 12c0 3.31 1.34 6.31 3.52 8.48L8.1 13.5A4.5 4.5 0 017.5 12z" fill="#34A853" />
    <path d="M3.52 20.48A12 12 0 0012 24a12 12 0 008.45-6.75L15.82 14.5A4.5 4.5 0 0112 16.5a4.5 4.5 0 01-4.41-3.5l-4.07 7.48z" fill="#34A853" />
  </svg>
);

// VS Code
export const VSCodeIcon: React.FC<Props> = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none">
    <rect width="100" height="100" rx="20" fill="#007ACC" />
    <path d="M74 17.5L52.75 41.75 35.5 27.5 17.5 40v20l18-12.5 17.25 14.25L74 82.5 82.5 77V23z" fill="white" opacity="0.9" />
    <path d="M74 17.5v65l8.5-5.5V23z" fill="white" opacity="0.5" />
    <path d="M35.5 27.5L17.5 40v20l18-12.5z" fill="white" opacity="0.7" />
  </svg>
);

// Calculator
export const CalcIcon: React.FC<Props> = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <rect width="24" height="24" rx="6" fill="#374151" />
    <rect x="5" y="5" width="14" height="5" rx="2" fill="#9CA3AF" />
    <rect x="5" y="13" width="4" height="3" rx="1" fill="#8B5CF6" />
    <rect x="10" y="13" width="4" height="3" rx="1" fill="#6B7280" />
    <rect x="15" y="13" width="4" height="3" rx="1" fill="#6B7280" />
    <rect x="5" y="18" width="4" height="1.5" rx="0.75" fill="#6B7280" />
    <rect x="10" y="18" width="4" height="1.5" rx="0.75" fill="#6B7280" />
    <rect x="15" y="18" width="4" height="1.5" rx="0.75" fill="#EF4444" />
  </svg>
);

// Notepad
export const NotepadIcon: React.FC<Props> = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <rect width="24" height="24" rx="6" fill="#1E293B" />
    <rect x="5" y="6" width="14" height="12" rx="2" fill="#334155" />
    <rect x="8" y="9" width="8" height="1.5" rx="0.75" fill="#94A3B8" />
    <rect x="8" y="12" width="8" height="1.5" rx="0.75" fill="#94A3B8" />
    <rect x="8" y="15" width="5" height="1.5" rx="0.75" fill="#94A3B8" />
    <rect x="10" y="3" width="4" height="4" rx="1" fill="#475569" />
  </svg>
);
