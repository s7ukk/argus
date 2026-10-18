import React, { useState } from 'react';
import { KeyRound, ShieldCheck, AlertCircle, ArrowRight, Sparkles } from 'lucide-react';
import { verifyKey } from '../api';
import { UserProfile } from '../types';
import { StarburnCore } from './StarburnCore';
import { TelegramIcon } from './Icons';

interface AuthScreenProps {
  onSuccess: (profile: UserProfile) => void;
}

export const AuthScreen: React.FC<AuthScreenProps> = ({ onSuccess }) => {
  const [keyCode, setKeyCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = async () => {
    const key = keyCode.trim();
    if (!key) {
      setError('Пожалуйста, введите лицензионный ключ доступа');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const profile = await verifyKey(key);
      localStorage.setItem('argus_access_key', key);
      localStorage.setItem('argus_user_profile', JSON.stringify(profile));
      // Save cookie with 1 year expiration
      document.cookie = `argus_access_key=${encodeURIComponent(key)}; max-age=31536000; path=/; SameSite=Lax`;
      onSuccess(profile);
    } catch (err: any) {
      setError(err.message || 'Ключ недействителен или срок его действия истек');
    } finally {
      setLoading(false);
    }
  };

  const openTelegramChannel = () => {
    const url = 'https://t.me/techargus';
    if ((window as any).electronAPI && (window as any).electronAPI.openExternal) {
      (window as any).electronAPI.openExternal(url);
    } else {
      window.open(url, '_blank');
    }
  };

  const openTelegramSupport = () => {
    const url = 'https://t.me/argus_adv';
    if ((window as any).electronAPI && (window as any).electronAPI.openExternal) {
      (window as any).electronAPI.openExternal(url);
    } else {
      window.open(url, '_blank');
    }
  };

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        position: 'relative',
        zIndex: 10,
        userSelect: 'none',
        height: '100%',
      }}
    >
      {/* Radiant Background Aura */}
      <div
        style={{
          position: 'absolute',
          width: 700,
          height: 700,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(168,85,247,0.2) 0%, rgba(56,189,248,0.1) 45%, transparent 70%)',
          pointerEvents: 'none',
          filter: 'blur(110px)',
        }}
      />

      {/* Realtime Core */}
      <div style={{ marginBottom: 8 }}>
        <StarburnCore isListening={false} isSpeaking={false} size={140} />
      </div>

      {/* Top Headline: "ВХОД В ARGUS" */}
      <div style={{ textAlign: 'center', marginBottom: 22, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '3px 12px',
            borderRadius: 99,
            background: 'rgba(168, 85, 247, 0.1)',
            border: '1px solid rgba(168, 85, 247, 0.3)',
            color: '#d8b4fe',
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}
        >
          <Sparkles size={12} color="#c084fc" />
          <span>ARGUS NEURAL CORE</span>
        </div>

        <h1
          style={{
            fontSize: 34,
            fontWeight: 800,
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
            color: '#ffffff',
            lineHeight: 1.1,
            background: 'linear-gradient(135deg, #ffffff 40%, #e9d5ff 75%, #38bdf8 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            textShadow: '0 4px 24px rgba(168,85,247,0.45)',
          }}
        >
          ВХОД В ARGUS
        </h1>
      </div>

      {/* Clean Glassmorphic Auth Card */}
      <div
        className="glass-card anim-scale-up"
        style={{
          width: '100%',
          maxWidth: 460,
          padding: '32px 28px',
          background: 'rgba(12, 8, 24, 0.88)',
          boxShadow: '0 25px 70px rgba(0, 0, 0, 0.75), 0 0 0 1px rgba(168, 85, 247, 0.25) inset',
          position: 'relative',
          overflow: 'hidden',
          borderRadius: 20,
        }}
      >
        {/* Animated Top Border Shimmer */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: 2,
            background: 'linear-gradient(90deg, transparent 0%, #a855f7 35%, #38bdf8 70%, transparent 100%)',
          }}
        />

        {/* Input & Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              value={keyCode}
              onChange={(e) => setKeyCode(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && handleVerify()}
              placeholder="Вставьте лицензионный ключ..."
              className="input"
              style={{
                paddingLeft: 42,
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                letterSpacing: '0.06em',
                fontSize: 13,
                height: 50,
                borderRadius: 14,
              }}
              disabled={loading}
              autoFocus
            />
            <KeyRound
              size={18}
              style={{
                position: 'absolute',
                left: 14,
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#c084fc',
                pointerEvents: 'none',
              }}
            />
          </div>

          {error && (
            <div
              className="anim-fade-up"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '11px 14px',
                borderRadius: 12,
                background: 'rgba(239, 68, 68, 0.14)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#fca5a5',
                fontSize: 12.5,
              }}
            >
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          <button
            onClick={() => handleVerify()}
            disabled={loading}
            className="btn-primary"
            style={{
              width: '100%',
              height: 50,
              justifyContent: 'center',
              fontSize: 14,
              fontWeight: 700,
              borderRadius: 14,
            }}
          >
            {loading ? (
              <div
                className="anim-spin"
                style={{
                  width: 18,
                  height: 18,
                  border: '2px solid rgba(255,255,255,0.3)',
                  borderTopColor: '#ffffff',
                  borderRadius: '50%',
                }}
              />
            ) : (
              <>
                <ShieldCheck size={18} />
                <span>Войти</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Bottom Bar matching user's sketch: Left = "наши каналы", Right = "продолжить" */}
      <div
        style={{
          position: 'fixed',
          bottom: 24,
          left: 28,
          right: 28,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          zIndex: 20,
        }}
      >
        {/* Bottom Left: "наши каналы:" -> Vertical Column of Links */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-start' }}>
          <span
            style={{
              fontSize: 11,
              fontWeight: 800,
              color: '#64748b',
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              paddingLeft: 2,
            }}
          >
            наши каналы:
          </span>
          <button
            onClick={openTelegramChannel}
            className="glass-card"
            style={{
              padding: '6px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              cursor: 'pointer',
              borderRadius: 10,
              background: 'rgba(38, 165, 228, 0.12)',
              border: '1px solid rgba(38, 165, 228, 0.35)',
              color: '#38bdf8',
              fontSize: 12,
              fontWeight: 600,
            }}
            title="Официальный Telegram-канал"
          >
            <TelegramIcon size={15} />
            <span>Канал: @techargus</span>
          </button>
          <button
            onClick={openTelegramSupport}
            className="glass-card"
            style={{
              padding: '6px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              cursor: 'pointer',
              borderRadius: 10,
              background: 'rgba(168, 85, 247, 0.12)',
              border: '1px solid rgba(168, 85, 247, 0.35)',
              color: '#c084fc',
              fontSize: 12,
              fontWeight: 600,
            }}
            title="Поддержка в Telegram"
          >
            <TelegramIcon size={15} />
            <span>Поддержка: @argus_adv</span>
          </button>
        </div>

        {/* Bottom Right: "продолжить" */}
        <button
          onClick={() => handleVerify()}
          disabled={loading || !keyCode.trim()}
          className="btn-primary"
          style={{
            padding: '10px 22px',
            borderRadius: 14,
            fontSize: 13,
            fontWeight: 800,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span>продолжить</span>
          <ArrowRight size={15} />
        </button>
      </div>
    </div>
  );
};
