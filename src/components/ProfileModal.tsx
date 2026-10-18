import React, { useState } from 'react';
import { X, Crown, Key, Calendar, ShieldCheck, Check, Save, Volume2, LogOut, Eye, EyeOff } from 'lucide-react';
import { UserProfile } from '../types';
import { updateProfile } from '../api';
import { StarburnLogo } from './Icons';

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
        zIndex: 60,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
        background: 'rgba(0, 0, 0, 0.72)',
        backdropFilter: 'blur(10px)',
        userSelect: 'none',
      }}
      onClick={onClose}
    >
      <div
        className="glass anim-scale-up"
        style={{
          width: '100%',
          maxWidth: 480,
          padding: '24px 26px',
          borderRadius: 18,
          boxShadow: '0 24px 60px rgba(0, 0, 0, 0.75), 0 0 0 1px rgba(255, 255, 255, 0.08) inset',
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
            borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
            paddingBottom: 14,
            marginBottom: 18,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: 'linear-gradient(135deg, rgba(124,58,237,0.3) 0%, rgba(219,39,119,0.2) 100%)',
                border: '1px solid rgba(168,85,247,0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <StarburnLogo size={18} />
            </div>
            <div>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#ffffff' }}>
                Профиль Starburn
              </h3>
              <p style={{ fontSize: 11, color: '#94a3b8' }}>
                Управление учетной записью и параметрами подписки
              </p>
            </div>
          </div>
          <button onClick={onClose} className="btn-icon" title="Закрыть">
            <X size={16} />
          </button>
        </div>

        {/* Subscription Info Card */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div
            className="glass-card"
            style={{
              padding: '14px 16px',
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
              background: 'rgba(255, 255, 255, 0.025)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Crown size={14} color="#fbbf24" />
                <span style={{ fontSize: 11, fontWeight: 700, color: '#d8b4fe', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Тарифный план
                </span>
              </div>
              <span className="badge-active">
                <ShieldCheck size={12} />
                <span>Активен</span>
              </span>
            </div>

            <div style={{ fontSize: 16, fontWeight: 700, color: '#ffffff' }}>
              {profile.tier}
            </div>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingTop: 8,
                borderTop: '1px solid rgba(255, 255, 255, 0.05)',
                fontSize: 11.5,
                color: '#94a3b8',
              }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Calendar size={13} color="#a855f7" />
                <span>Действует до: <strong style={{ color: '#e2e8f0' }}>{formattedDate}</strong></span>
              </span>
              <span className="badge-purple">
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
                padding: '9px 12px',
                borderRadius: 10,
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.06)',
                fontFamily: 'ui-monospace, monospace',
                fontSize: 12,
                color: '#c084fc',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Key size={13} color="#a855f7" />
                <span>{showKey ? profile.key_code : `${profile.key_code.substring(0, 8)}••••••••••••`}</span>
              </div>
              <button
                onClick={() => setShowKey(!showKey)}
                style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', display: 'flex' }}
                title={showKey ? 'Скрыть ключ' : 'Показать ключ'}
              >
                {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>

          {/* User Name Input */}
          <div>
            <label style={{ fontSize: 10.5, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 5 }}>
              Ваше имя (обращение Starburn)
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Имя пользователя..."
                className="input"
                style={{ fontSize: 12.5 }}
              />
              <button
                onClick={handleSave}
                disabled={saving}
                className="btn-primary"
                style={{ padding: '0 16px', fontSize: 12 }}
              >
                {saving ? (
                  <div
                    className="anim-spin"
                    style={{
                      width: 14,
                      height: 14,
                      border: '2px solid rgba(255,255,255,0.3)',
                      borderTopColor: '#ffffff',
                      borderRadius: '50%',
                    }}
                  />
                ) : savedSuccess ? (
                  <>
                    <Check size={14} color="#34d399" />
                    <span>ОК</span>
                  </>
                ) : (
                  <>
                    <Save size={14} />
                    <span>Сохранить</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Voice Response Toggle */}
          <div
            className="glass-card"
            style={{
              padding: '12px 14px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Volume2 size={16} color="#c084fc" />
              <div>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: '#ffffff' }}>
                  Голосовые ответы ассистента
                </div>
                <div style={{ fontSize: 10.5, color: '#94a3b8' }}>
                  Озвучивание нейросетью Edge-TTS (ru-RU-DmitryNeural)
                </div>
              </div>
            </div>

            <label className="toggle">
              <input
                type="checkbox"
                checked={voiceEnabled}
                onChange={(e) => {
                  const val = e.target.checked;
                  setVoiceEnabled(val);
                  updateProfile(profile.key_code, name, val, profile.voice_speed);
                }}
              />
              <span className="toggle-track" />
              <span className="toggle-thumb" />
            </label>
          </div>
        </div>

        {/* Footer Actions */}
        <div
          style={{
            marginTop: 20,
            paddingTop: 14,
            borderTop: '1px solid rgba(255, 255, 255, 0.06)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <button
            onClick={onLogout}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#f87171',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'opacity 0.15s',
            }}
          >
            <LogOut size={13} />
            <span>Выйти / Сменить ключ</span>
          </button>

          <button onClick={onClose} className="btn-ghost">
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
};
