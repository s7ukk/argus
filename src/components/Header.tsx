import React, { useState, useEffect } from 'react';
import { Minus, Square, X } from 'lucide-react';
import { StarburnLogo } from './Icons';

interface HeaderProps {
  subtitleText?: string;
}

export const Header: React.FC<HeaderProps> = ({
  subtitleText = "",
}) => {
  const [isMac, setIsMac] = useState(false);

  useEffect(() => {
    const electronIsMac = (window as any).electronAPI?.isMac;
    if (typeof electronIsMac === 'boolean') {
      setIsMac(electronIsMac);
    } else {
      const isDarwin = typeof navigator !== 'undefined' && (/Mac|iPod|iPhone|iPad/.test(navigator.platform) || /Mac/i.test(navigator.userAgent));
      setIsMac(isDarwin);
    }
  }, []);

  const handleMinimize = () => {
    if ((window as any).electronAPI) (window as any).electronAPI.minimize();
  };

  const handleMaximize = () => {
    if ((window as any).electronAPI) (window as any).electronAPI.maximize();
  };

  const handleClose = () => {
    if ((window as any).electronAPI) (window as any).electronAPI.close();
  };

  return (
    <header
      className="glass drag"
      style={{
        height: 38,
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: isMac ? '0 14px 0 76px' : '0 12px 0 16px',
        position: 'relative',
        zIndex: 50,
        borderBottom: '1px solid rgba(255, 255, 255, 0.07)',
        background: 'rgba(8, 6, 16, 0.88)',
        backdropFilter: 'blur(16px)',
        userSelect: 'none',
        flexShrink: 0,
      }}
    >
      {/* Top Accent Gradient Line */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 1,
          background: 'linear-gradient(90deg, transparent 0%, rgba(168,85,247,0.6) 30%, rgba(56,189,248,0.5) 70%, transparent 100%)',
        }}
      />

      {/* Left: Argus Logo & Name */}
      <div className="no-drag" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div
          style={{
            width: 24,
            height: 24,
            borderRadius: 7,
            background: 'linear-gradient(135deg, rgba(168,85,247,0.35) 0%, rgba(56,189,248,0.2) 100%)',
            border: '1px solid rgba(168,85,247,0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 10px rgba(168,85,247,0.25)',
          }}
        >
          <StarburnLogo size={14} />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span
            style={{
              fontSize: 13,
              fontWeight: 800,
              letterSpacing: '0.02em',
              background: 'linear-gradient(135deg, #ffffff 40%, #e9d5ff 75%, #38bdf8 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Argus
          </span>
          {subtitleText && (
            <span
              style={{
                fontSize: 10.5,
                fontWeight: 500,
                color: 'rgba(216, 180, 254, 0.5)',
              }}
            >
              {subtitleText}
            </span>
          )}
        </div>
      </div>

      {/* Center: System Status Telemetry */}
      <div className="no-drag" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
            padding: '2px 8px',
            borderRadius: 999,
            background: 'rgba(255, 255, 255, 0.035)',
            border: '1px solid rgba(255, 255, 255, 0.06)',
            boxShadow: 'inset 0 0 8px rgba(0,0,0,0.3)',
          }}
        >
          <div
            style={{
              width: 5,
              height: 5,
              borderRadius: '50%',
              background: '#34d399',
              boxShadow: '0 0 8px #34d399',
            }}
          />
          <span style={{ fontSize: 10.5, color: '#cbd5e1', fontWeight: 600 }}>
            Online
          </span>
        </div>
      </div>

      {/* Right: Window Controls (on Windows/Linux) */}
      {!isMac ? (
        <div className="no-drag" style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <button
            onClick={handleMinimize}
            style={{
              width: 28,
              height: 24,
              borderRadius: 6,
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background 0.15s, color 0.15s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.08)';
              e.currentTarget.style.color = '#ffffff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = '#94a3b8';
            }}
            title="Свернуть"
          >
            <Minus size={13} />
          </button>
          <button
            onClick={handleMaximize}
            style={{
              width: 28,
              height: 24,
              borderRadius: 6,
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background 0.15s, color 0.15s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.08)';
              e.currentTarget.style.color = '#ffffff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = '#94a3b8';
            }}
            title="Развернуть"
          >
            <Square size={11} />
          </button>
          <button
            onClick={handleClose}
            style={{
              width: 28,
              height: 24,
              borderRadius: 6,
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background 0.15s, color 0.15s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(239,68,68,0.25)';
              e.currentTarget.style.color = '#f87171';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = '#94a3b8';
            }}
            title="Закрыть"
          >
            <X size={13} />
          </button>
        </div>
      ) : (
        <div style={{ width: 10 }} />
      )}
    </header>
  );
};
