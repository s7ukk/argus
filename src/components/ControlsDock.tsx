import React, { useState, useEffect } from 'react';
import { Volume2, Sun, Power, ChevronUp, ChevronDown, Mic, Sliders, Cpu, HardDrive } from 'lucide-react';
import { SystemStats } from '../types';
import { getSystemStats, setVolume, setBrightness, lockPC, launchApp } from '../api';
import { TelegramIcon, DiscordIcon, SteamIcon, SpotifyIcon, ChromeIcon, VSCodeIcon, CalcIcon, NotepadIcon } from './Icons';

interface ControlsDockProps {
  onTriggerVoice: () => void;
  isListening: boolean;
}

export const ControlsDock: React.FC<ControlsDockProps> = ({ onTriggerVoice, isListening }) => {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [volumeLevel, setVolumeLevel] = useState<number>(50);
  const [brightnessLevel, setBrightnessLevel] = useState<number>(70);

  const loadStats = async () => {
    try {
      const data = await getSystemStats();
      setStats(data);
      if (typeof data.volume === 'number') setVolumeLevel(data.volume);
      if (typeof data.brightness === 'number') setBrightnessLevel(data.brightness);
    } catch (e) {
      // offline
    }
  };

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleVolumeChange = async (val: number) => {
    setVolumeLevel(val);
    await setVolume({ level: val });
  };

  const handleBrightnessChange = async (val: number) => {
    setBrightnessLevel(val);
    await setBrightness({ level: val });
  };

  const appLaunchers = [
    { name: 'Telegram', cmd: 'telegram', icon: <TelegramIcon size={18} /> },
    { name: 'Discord', cmd: 'discord', icon: <DiscordIcon size={18} /> },
    { name: 'Steam', cmd: 'steam', icon: <SteamIcon size={18} /> },
    { name: 'Spotify', cmd: 'spotify', icon: <SpotifyIcon size={18} /> },
    { name: 'Chrome', cmd: 'chrome', icon: <ChromeIcon size={18} /> },
    { name: 'VS Code', cmd: 'vscode', icon: <VSCodeIcon size={18} /> },
    { name: 'Калькулятор', cmd: 'calculator', icon: <CalcIcon size={18} /> },
    { name: 'Блокнот', cmd: 'notepad', icon: <NotepadIcon size={18} /> },
  ];

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 40,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        userSelect: 'none',
      }}
    >
      {/* Expanded Control HUD Drawer */}
      {isOpen && (
        <div
          className="glass anim-scale-up"
          style={{
            width: 330,
            padding: '20px 22px',
            borderRadius: 18,
            marginBottom: 12,
            boxShadow: '0 25px 65px rgba(0,0,0,0.8), 0 0 0 1px rgba(168,85,247,0.25) inset',
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}
        >
          {/* Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: '1px solid rgba(255,255,255,0.07)',
              paddingBottom: 12,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <Sliders size={15} color="#c084fc" />
              <span style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#ffffff' }}>
                Управление ПК
              </span>
            </div>
            <span style={{ fontSize: 10, color: '#a855f7', fontWeight: 700, letterSpacing: '0.06em' }}>
              ARGUS
            </span>
          </div>

          {/* Volume Slider */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12.5, color: '#cbd5e1' }}>
                <Volume2 size={14} color="#c084fc" />
                <span>Громкость</span>
              </span>
              <span style={{ fontSize: 12.5, fontWeight: 700, color: '#ffffff', fontFamily: 'ui-monospace, monospace' }}>
                {volumeLevel}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={volumeLevel}
              onChange={(e) => handleVolumeChange(Number(e.target.value))}
            />
          </div>

          {/* Brightness Slider */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12.5, color: '#cbd5e1' }}>
                <Sun size={14} color="#fbbf24" />
                <span>Яркость</span>
              </span>
              <span style={{ fontSize: 12.5, fontWeight: 700, color: '#ffffff', fontFamily: 'ui-monospace, monospace' }}>
                {brightnessLevel}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={brightnessLevel}
              onChange={(e) => handleBrightnessChange(Number(e.target.value))}
            />
          </div>

          {/* App Launchers */}
          <div>
            <span
              style={{
                fontSize: 10.5,
                fontWeight: 700,
                color: '#64748b',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                display: 'block',
                marginBottom: 8,
              }}
            >
              Быстрый запуск
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 7 }}>
              {appLaunchers.map((app) => (
                <button
                  key={app.name}
                  onClick={() => launchApp(app.cmd)}
                  className="glass-card"
                  style={{
                    padding: '9px 4px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 5,
                    cursor: 'pointer',
                    borderRadius: 12,
                  }}
                  title={`Запустить ${app.name}`}
                >
                  {app.icon}
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      color: '#cbd5e1',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      maxWidth: '100%',
                    }}
                  >
                    {app.name}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Hardware Stats */}
          {stats && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: 8,
                borderTop: '1px solid rgba(255,255,255,0.07)',
                paddingTop: 12,
              }}
            >
              <div
                style={{
                  padding: '8px 10px',
                  borderRadius: 10,
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <Cpu size={15} color="#c084fc" />
                <div>
                  <div style={{ fontSize: 10, color: '#94a3b8' }}>ЦП</div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#ffffff', fontFamily: 'ui-monospace, monospace' }}>
                    {stats.cpu?.percent ?? 0}%
                  </div>
                </div>
              </div>
              <div
                style={{
                  padding: '8px 10px',
                  borderRadius: 10,
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <HardDrive size={15} color="#ec4899" />
                <div>
                  <div style={{ fontSize: 10, color: '#94a3b8' }}>ОЗУ</div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#ffffff', fontFamily: 'ui-monospace, monospace' }}>
                    {stats.memory?.percent ?? 0}%
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Lock Computer */}
          <button
            onClick={() => lockPC()}
            style={{
              width: '100%',
              padding: '10px',
              borderRadius: 10,
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#fca5a5',
              fontSize: 12,
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 7,
              cursor: 'pointer',
              transition: 'background 0.18s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239,68,68,0.22)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(239,68,68,0.12)'; }}
          >
            <Power size={14} />
            <span>Заблокировать ПК</span>
          </button>
        </div>
      )}

      {/* Main Bottom-Right Trigger: ЗАПУСК Button + HUD Expand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="glass-card"
          style={{
            width: 44,
            height: 44,
            borderRadius: 13,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            color: '#c084fc',
          }}
          title="Открыть пульт ПК"
        >
          {isOpen ? <ChevronDown size={19} /> : <ChevronUp size={19} />}
        </button>

        {/* Big Glow Launch Button ("запуск справа снизу") */}
        <button
          onClick={onTriggerVoice}
          className={isListening ? '' : 'btn-primary'}
          style={{
            height: 44,
            padding: '0 24px',
            borderRadius: 13,
            fontSize: 12.5,
            fontWeight: 800,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            cursor: 'pointer',
            transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
            ...(isListening
              ? {
                  background: 'linear-gradient(135deg, #e11d48 0%, #f43f5e 100%)',
                  color: '#ffffff',
                  border: '1px solid rgba(244,63,94,0.6)',
                  boxShadow: '0 0 35px rgba(244, 63, 94, 0.8)',
                  transform: 'scale(1.04)',
                }
              : {}),
          }}
          title="Запуск голосового управления Argus"
        >
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Mic size={16} />
            {isListening && (
              <span
                className="anim-dot"
                style={{
                  position: 'absolute',
                  top: -2,
                  right: -2,
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: '#ffffff',
                }}
              />
            )}
          </div>
          <span>{isListening ? 'СЛУШАЮ...' : 'ЗАПУСК'}</span>
        </button>
      </div>
    </div>
  );
};
