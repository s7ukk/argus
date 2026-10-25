import React, { useState, useEffect } from 'react';
import { Minus, Square, X } from 'lucide-react';
import { StarburnLogo } from './Icons';

interface HeaderProps {
  subtitleText?: string;
  centerContent?: React.ReactNode;
}

export const Header: React.FC<HeaderProps> = ({
  subtitleText = "",
  centerContent,
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
        height: centerContent ? 46 : 38,
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: isMac ? '0 14px 0 76px' : '0 12px 0 16px',
        position: 'relative',
        zIndex: 50,
        borderBottom: '1px solid rgba(255, 255, 255, 0.07)',
        background: 'rgba(10, 10, 14, 0.94)',
        backdropFilter: 'blur(30px)',
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
          background: 'linear-gradient(90deg, transparent 0%, var(--accent-glow, rgba(255,255,255,0.4)) 50%, transparent 100%)',
        }}
      />

      {/* Left: Argus Logo & Name */}
      <div className="no-drag" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div
          style={{
            width: 22,
            height: 22,
            borderRadius: 6,
            background: 'rgba(255, 255, 255, 0.06)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 10px var(--accent-glow, rgba(255,255,255,0.15))',
          }}
        >
          <StarburnLogo size={13} />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span
            style={{
              fontSize: 12.5,
              fontWeight: 700,
              letterSpacing: '0.04em',
              color: '#ffffff',
            }}
          >
            Argus
          </span>
          {subtitleText && (
            <span
              style={{
                fontSize: 10,
                fontWeight: 500,
                color: 'rgba(255, 255, 255, 0.45)',
              }}
            >
              {subtitleText}
            </span>
          )}
        </div>
      </div>

      {/* Center: Draggable region or Centered Navigation Dock */}
      {centerContent ? (
        <>
          <div className="drag" style={{ flex: 1, minWidth: 16 }} />
          <div className="no-drag" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {centerContent}
          </div>
          <div className="drag" style={{ flex: 1, minWidth: 16 }} />
        </>
      ) : (
        <div className="drag" style={{ flex: 1 }} />
      )}

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
