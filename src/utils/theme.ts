// ─── THEME & LIQUID GLASS ENGINE ──────────────────────────────────
export interface ThemePreset {
  id: string;
  name: string;
  hex: string;
  rgb: string;
}

export const THEME_PRESETS: ThemePreset[] = [
  { id: 'monochrome', name: 'Obsidian (Монохром)', hex: '#ffffff', rgb: '255, 255, 255' },
  { id: 'silver', name: 'Titanium (Серебро)', hex: '#cbd5e1', rgb: '203, 213, 225' },
  { id: 'violet', name: 'Amethyst (Фиолетовый)', hex: '#a855f7', rgb: '168, 85, 247' },
  { id: 'sapphire', name: 'Cyber (Сапфир)', hex: '#38bdf8', rgb: '56, 189, 248' },
  { id: 'emerald', name: 'Matrix (Изумруд)', hex: '#10b981', rgb: '16, 185, 129' },
  { id: 'rose', name: 'Neon Rose (Розовый)', hex: '#f43f5e', rgb: '244, 63, 94' },
  { id: 'amber', name: 'Amber Glow (Янтарь)', hex: '#f59e0b', rgb: '245, 158, 11' },
];

export type NavPosition = 'top' | 'left' | 'right';

export interface ThemeConfig {
  accentColor: string;
  presetId?: string;
  navPosition: NavPosition;
  liquidGlassIntensity: number; // 0 to 1
}

const STORAGE_KEY = 'argus_theme_config';

export function hexToRgb(hex: string): string {
  const clean = hex.replace('#', '');
  if (clean.length === 3) {
    const r = parseInt(clean[0] + clean[0], 16);
    const g = parseInt(clean[1] + clean[1], 16);
    const b = parseInt(clean[2] + clean[2], 16);
    return `${r}, ${g}, ${b}`;
  }
  if (clean.length >= 6) {
    const r = parseInt(clean.substring(0, 2), 16) || 255;
    const g = parseInt(clean.substring(2, 4), 16) || 255;
    const b = parseInt(clean.substring(4, 6), 16) || 255;
    return `${r}, ${g}, ${b}`;
  }
  return '255, 255, 255';
}

export function loadThemeConfig(): ThemeConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        accentColor: parsed.accentColor || '#ffffff',
        presetId: parsed.presetId || 'monochrome',
        navPosition: parsed.navPosition || 'top',
        liquidGlassIntensity: parsed.liquidGlassIntensity ?? 1.0,
      };
    }
  } catch (e) {
    console.warn('Failed to load theme config:', e);
  }
  return {
    accentColor: '#ffffff', // Default: Black & White / Obsidian
    presetId: 'monochrome',
    navPosition: 'top', // Default: Top floating capsule
    liquidGlassIntensity: 1.0,
  };
}

export function applyThemeConfig(config: ThemeConfig) {
  try {
    const root = document.documentElement;
    const rgb = hexToRgb(config.accentColor);
    root.style.setProperty('--accent', config.accentColor);
    root.style.setProperty('--accent-rgb', rgb);
    root.style.setProperty('--accent-glow', `rgba(${rgb}, 0.22)`);
    root.style.setProperty('--accent-glow-strong', `rgba(${rgb}, 0.45)`);
    root.style.setProperty('--accent-subtle', `rgba(${rgb}, 0.1)`);
    root.style.setProperty('--nav-position', config.navPosition);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
    window.dispatchEvent(new CustomEvent('argus_theme_changed', { detail: config }));
  } catch (e) {
    console.error('Failed to apply theme config:', e);
  }
}
