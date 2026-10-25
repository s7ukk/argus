import React, { useState } from 'react';
import { X, Crown, Key, Calendar, ShieldCheck, Check, Save, Volume2, LogOut, Eye, EyeOff, User, Sparkles } from 'lucide-react';
import { UserProfile } from '../types';
import { updateProfile } from '../api';
import { StarburnLogo } from './Icons';
import { Switch } from './Switch';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  profile: UserProfile;
  onProfileUpdated: (updated: UserProfile) => void;
  onLogout: () => void;
}

export const ProfileModal: React.FC<ProfileModalProps> = ({
  isOpen,
  onClose,
  profile,
  onProfileUpdated,
  onLogout,
}) => {
  const [name, setName] = useState(profile.display_name);
  const [voiceEnabled, setVoiceEnabled] = useState(profile.voice_enabled);
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSave = async () => {
    setSaving(true);
    setSavedSuccess(false);
    try {
      await updateProfile(profile.key_code, name, voiceEnabled, profile.voice_speed);
      onProfileUpdated({
        ...profile,
        display_name: name,
        voice_enabled: voiceEnabled,
      });
      setSavedSuccess(true);
      window.dispatchEvent(new CustomEvent('argus_island_notify', {
        detail: { text: 'Профиль успешно сохранен !', type: 'success' }
      }));
      setTimeout(() => setSavedSuccess(false), 2200);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const formattedDate = new Date(profile.expires_at).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
        background: 'rgba(0, 0, 0, 0.76)',
        backdropFilter: 'blur(16px)',
        userSelect: 'none',
      }}
      onClick={onClose}
    >
      <div
        className="anim-scale-up"
        style={{
          width: '100%',
          maxWidth: 460,
          padding: '28px 26px',
          borderRadius: 24,
          background: 'rgba(12, 12, 16, 0.88)',
          backdropFilter: 'blur(36px) saturate(190%)',
          WebkitBackdropFilter: 'blur(36px) saturate(190%)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 28px 70px rgba(0, 0, 0, 0.8), inset 0 1px 0 rgba(255, 255, 255, 0.15)',
          position: 'relative',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingBottom: 16,
            marginBottom: 20,
            borderBottom: '1px solid rgba(255, 255, 255, 0.07)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {/* Glowing Avatar Ring */}
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.18) 0%, rgba(255, 255, 255, 0.04) 100%)',
                border: '1.5px solid rgba(255, 255, 255, 0.25)',
                boxShadow: '0 0 20px var(--accent-glow, rgba(255, 255, 255, 0.2))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 16,
                fontWeight: 700,
                color: '#ffffff',
              }}
            >
              {profile.display_name ? profile.display_name.charAt(0).toUpperCase() : <User size={18} />}
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#ffffff' }}>
                  {profile.display_name || 'Пользователь Argus'}
                </h3>
                <span
                  style={{
                    padding: '1px 7px',
                    borderRadius: 9999,
                    background: 'rgba(255, 255, 255, 0.06)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    fontSize: 10,
                    fontWeight: 700,
                    color: 'var(--accent, #ffffff)',
                    letterSpacing: '0.04em',
                    textTransform: 'uppercase',
                  }}
                >
                  {profile.tier}
                </span>
              </div>
              <p style={{ fontSize: 11.5, color: '#94a3b8', marginTop: 2 }}>
                Лицензия активна • {profile.days_left} дней осталось
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              width: 30,
              height: 30,
              borderRadius: '50%',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.18s ease',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = '#ffffff'; e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = '#94a3b8'; e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'; }}
          >
            <X size={15} />
          </button>
        </div>

        {/* Content Body */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Subscription Info Card */}
          <div
            style={{
              padding: '14px 16px',
              borderRadius: 16,
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.07)',
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Crown size={14} color="#f59e0b" />
                <span style={{ fontSize: 11, fontWeight: 700, color: '#cbd5e1', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Параметры подписки
                </span>
              </div>
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '2px 8px',
                  borderRadius: 9999,
                  background: 'rgba(34, 197, 94, 0.12)',
                  border: '1px solid rgba(34, 197, 94, 0.3)',
                  color: '#4ade80',
                  fontSize: 10.5,
                  fontWeight: 600,
                }}
              >
                <ShieldCheck size={11} />
                <span>Активен</span>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 12, color: '#94a3b8' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Calendar size={13} color="var(--accent, #ffffff)" />
                <span>Действует до: <strong style={{ color: '#e2e8f0' }}>{formattedDate}</strong></span>
              </span>
              <span style={{ color: '#cbd5e1', fontWeight: 600 }}>
                {profile.days_left} дн.
              </span>
            </div>
          </div>

          {/* License Key Field */}
          <div>
            <label style={{ fontSize: 10.5, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 5 }}>
              Лицензионный ключ
            </label>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                borderRadius: 14,
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                fontFamily: "'JetBrains Mono', ui-monospace, Menlo, monospace",
                fontSize: 12,
                color: '#e2e8f0',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Key size={13} color="var(--accent, #ffffff)" />
                <span>{showKey ? profile.key_code : `${profile.key_code.substring(0, 8)}••••••••••••`}</span>
              </div>
              <button
                onClick={() => setShowKey(!showKey)}
                style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', display: 'flex' }}
                title={showKey ? 'Скрыть ключ' : 'Показать ключ'}
              >
                {showKey ? <EyeOff size={13} /> : <Eye size={13} />}
              </button>
            </div>
          </div>

          {/* User Name Input */}
          <div>
            <label style={{ fontSize: 10.5, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 5 }}>
              Ваше имя (обращение Argus)
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Имя пользователя..."
                style={{
                  flex: 1,
                  padding: '10px 14px',
                  background: 'rgba(255, 255, 255, 0.035)',
                  border: '1px solid rgba(255, 255, 255, 0.09)',
                  borderRadius: 14,
                  color: '#ffffff',
                  fontSize: 12.5,
                  outline: 'none',
                  transition: 'all 0.2s ease',
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.3)';
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.09)';
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.035)';
                }}
              />
              <button
                onClick={handleSave}
                disabled={saving}
                style={{
                  padding: '0 16px',
                  borderRadius: 14,
                  border: '1px solid rgba(255, 255, 255, 0.25)',
                  background: 'linear-gradient(135deg, var(--accent, #ffffff) 0%, rgba(220, 220, 230, 0.9) 100%)',
                  color: '#09090b',
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  transition: 'all 0.18s ease',
                }}
              >
                {saving ? (
                  <div style={{ width: 12, height: 12, border: '2px solid rgba(0,0,0,0.2)', borderTopColor: '#000', borderRadius: '50%' }} className="anim-spin" />
                ) : savedSuccess ? (
                  <>
                    <Check size={13} color="#16a34a" />
                    <span>ОК</span>
                  </>
                ) : (
                  <>
                    <Save size={13} />
                    <span>Сохранить</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Voice Response Toggle with Switch component */}
          <div
            style={{
              padding: '12px 16px',
              borderRadius: 16,
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.07)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Volume2 size={16} color="var(--accent, #ffffff)" />
              <div>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: '#ffffff' }}>
                  Голосовые ответы ассистента
                </div>
                <div style={{ fontSize: 10.5, color: '#94a3b8' }}>
                  Озвучивание нейросетью Edge-TTS (ru-RU-DmitryNeural)
                </div>
              </div>
            </div>

            <Switch
              checked={voiceEnabled}
              onChange={(val) => {
                setVoiceEnabled(val);
                updateProfile(profile.key_code, name, val, profile.voice_speed);
              }}
              size="md"
            />
          </div>
        </div>

        {/* Footer Actions */}
        <div
          style={{
            marginTop: 22,
            paddingTop: 16,
            borderTop: '1px solid rgba(255, 255, 255, 0.07)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <button
            onClick={onLogout}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '7px 14px',
              borderRadius: 9999,
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              color: '#f87171',
              fontSize: 11.5,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.18s ease',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'; }}
          >
            <LogOut size={13} />
            <span>Выйти из аккаунта</span>
          </button>

          <button
            onClick={onClose}
            style={{
              padding: '7px 18px',
              borderRadius: 9999,
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              color: '#ffffff',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.18s ease',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255, 255, 255, 0.12)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)'; }}
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
};
