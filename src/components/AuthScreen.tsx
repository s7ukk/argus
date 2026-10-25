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
    if ((window as any).electronAPI?.openExternal) {
      (window as any).electronAPI.openExternal(url);
    } else {
      window.open(url, '_blank');
    }
  };

  const openTelegramSupport = () => {
    const url = 'https://t.me/argus_adv';
    if ((window as any).electronAPI?.openExternal) {
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
      {/* Ambient background glow */}
      <div
        style={{
          position: 'absolute',
          width: 500,
          height: 500,
          borderRadius: '50%',
          background: 'radial-gradient(circle, var(--accent-glow, rgba(255,255,255,0.1)) 0%, transparent 70%)',
          pointerEvents: 'none',
          filter: 'blur(90px)',
        }}
      />

      {/* Realtime Core Mini Visualizer */}
      <div style={{ marginBottom: 12 }}>
        <StarburnCore isListening={false} isSpeaking={false} size={110} />
      </div>

      {/* Modern Ultra-Thin Minimalist Card */}
      <div
        className="anim-scale-up"
        style={{
          width: '100%',
          maxWidth: 420,
          padding: '36px 32px',
          background: 'rgba(10, 10, 14, 0.78)',
          backdropFilter: 'blur(36px) saturate(190%)',
          WebkitBackdropFilter: 'blur(36px) saturate(190%)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: 24,
          boxShadow: '0 30px 80px rgba(0, 0, 0, 0.75), inset 0 1px 0 rgba(255, 255, 255, 0.15)',
          position: 'relative',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        {/* Specular Top Shimmer */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: '15%',
            right: '15%',
            height: 1,
            background: 'linear-gradient(90deg, transparent, var(--accent, #ffffff), transparent)',
            opacity: 0.5,
          }}
        />

        {/* Brand Title */}
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '2px 10px',
              borderRadius: 9999,
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              color: 'var(--accent, #ffffff)',
              fontSize: 10.5,
              fontWeight: 600,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              marginBottom: 10,
            }}
          >
            <Sparkles size={11} />
            <span>Argus Intelligence</span>
          </div>

          <h1
            style={{
              fontSize: 24,
              fontWeight: 700,
              letterSpacing: '-0.02em',
              color: '#ffffff',
              lineHeight: 1.2,
            }}
          >
            Авторизация
          </h1>
          <p style={{ fontSize: 12.5, color: '#94a3b8', marginTop: 4 }}>
            Введите персональный лицензионный ключ для активации
          </p>
        </div>

        {/* Input & Form */}
        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ position: 'relative', width: '100%' }}>
            <div
              style={{
                position: 'absolute',
                left: 14,
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#64748b',
                display: 'flex',
                alignItems: 'center',
                pointerEvents: 'none',
              }}
            >
              <KeyRound size={15} />
            </div>

            <input
              type="text"
              value={keyCode}
              onChange={(e) => {
                setKeyCode(e.target.value);
                if (error) setError(null);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleVerify();
              }}
              placeholder="ARGUS-XXXX-XXXX-XXXX"
              disabled={loading}
              style={{
                width: '100%',
                padding: '12px 14px 12px 40px',
                background: 'rgba(255, 255, 255, 0.035)',
                border: error
                  ? '1px solid rgba(239, 68, 68, 0.6)'
                  : '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: 14,
                color: '#ffffff',
                fontSize: 13,
                fontFamily: "'JetBrains Mono', ui-monospace, Menlo, monospace",
                outline: 'none',
                letterSpacing: '0.04em',
                transition: 'all 0.2s ease',
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.35)';
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)';
                e.currentTarget.style.boxShadow = '0 0 20px var(--accent-glow, rgba(255, 255, 255, 0.1))';
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = error ? 'rgba(239, 68, 68, 0.6)' : 'rgba(255, 255, 255, 0.1)';
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.035)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            />
          </div>

          {error && (
            <div
              className="anim-fade-in"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 7,
                padding: '8px 12px',
                borderRadius: 10,
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                color: '#f87171',
                fontSize: 11.5,
              }}
            >
              <AlertCircle size={14} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          {/* Submit Button */}
          <button
            onClick={handleVerify}
            disabled={loading || !keyCode.trim()}
            style={{
              width: '100%',
              padding: '11px 20px',
              borderRadius: 14,
              border: '1px solid rgba(255, 255, 255, 0.25)',
              background: loading || !keyCode.trim()
                ? 'rgba(255, 255, 255, 0.05)'
                : 'linear-gradient(135deg, var(--accent, #ffffff) 0%, rgba(220, 220, 230, 0.9) 100%)',
              color: loading || !keyCode.trim() ? '#64748b' : '#09090b',
              fontSize: 13,
              fontWeight: 700,
              letterSpacing: '0.02em',
              cursor: loading || !keyCode.trim() ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              boxShadow: loading || !keyCode.trim() ? 'none' : '0 4px 20px var(--accent-glow, rgba(255, 255, 255, 0.25))',
              transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
            }}
          >
            {loading ? (
              <div style={{ width: 16, height: 16, border: '2px solid rgba(0,0,0,0.2)', borderTopColor: '#09090b', borderRadius: '50%' }} className="anim-spin" />
            ) : (
              <>
                <span>Войти в систему</span>
                <ArrowRight size={14} />
              </>
            )}
          </button>
        </div>

        {/* Telegram Channels / Support Footer */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 16,
            marginTop: 24,
            paddingTop: 16,
            borderTop: '1px solid rgba(255, 255, 255, 0.06)',
            width: '100%',
          }}
        >
          <button
            onClick={openTelegramChannel}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              fontSize: 11.5,
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              cursor: 'pointer',
              transition: 'color 0.15s ease',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
          >
            <TelegramIcon size={13} />
            <span>Канал Argus</span>
          </button>

          <span style={{ color: 'rgba(255, 255, 255, 0.15)' }}>•</span>

          <button
            onClick={openTelegramSupport}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              fontSize: 11.5,
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              cursor: 'pointer',
              transition: 'color 0.15s ease',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
          >
            <ShieldCheck size={13} />
            <span>Поддержка</span>
          </button>
        </div>
      </div>
    </div>
  );
};
