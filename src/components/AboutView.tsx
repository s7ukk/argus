import React from 'react';
import { Sparkles, Shield, Cpu, Terminal, ExternalLink, Heart, Globe, Radio } from 'lucide-react';
import { TelegramIcon } from './Icons';

export const AboutView: React.FC = () => {
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
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto',
        background: 'rgba(8, 8, 12, 0.65)',
        position: 'relative',
        userSelect: 'none',
        padding: '28px',
      }}
    >
      <div style={{ maxWidth: 760, margin: '0 auto', width: '100%', display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Main Banner Card */}
        <div
          className="glass-card"
          style={{
            padding: '36px 32px',
            borderRadius: 24,
            position: 'relative',
            overflow: 'hidden',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            boxShadow: '0 25px 60px rgba(0, 0, 0, 0.6)',
          }}
        >
          {/* Radiant Aura */}
          <div
            style={{
              position: 'absolute',
              top: -60,
              right: -60,
              width: 250,
              height: 250,
              borderRadius: '50%',
              background: 'radial-gradient(circle, rgba(255, 255, 255, 0.15) 0%, transparent 70%)',
              filter: 'blur(50px)',
              pointerEvents: 'none',
            }}
          />

          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 12px', borderRadius: 99, background: 'rgba(255, 255, 255, 0.06)', border: '1px solid rgba(255, 255, 255, 0.15)', color: '#cbd5e1', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', marginBottom: 16 }}>
            <Sparkles size={12} color="var(--accent, #ffffff)" />
            <span>ARGUS SYSTEM OVERVIEW</span>
          </div>

          <h1 style={{ fontSize: 32, fontWeight: 800, color: '#ffffff', letterSpacing: '0.04em', lineHeight: 1.1, marginBottom: 12 }}>
            ARGUS AUTONOMOUS AI
          </h1>

          <p style={{ fontSize: 14, color: '#94a3b8', lineHeight: 1.6, maxWidth: 620, marginBottom: 24 }}>
            Персональный автономный искусственный интеллект глубокой интеграции с операционной системой Windows. Оснащен динамическим сканером приложений, подсистемой выполнения локальных Python-плагинов в изолированных процессах, голосовым синтезом Edge-TTS и поддержкой сложных составных инструкций.
          </p>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
            <button
              onClick={openTelegramChannel}
              className="glass-card"
              style={{
                padding: '10px 18px',
                borderRadius: 14,
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                background: 'rgba(38, 165, 228, 0.15)',
                border: '1px solid rgba(38, 165, 228, 0.4)',
                color: '#38bdf8',
                fontSize: 13,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              <TelegramIcon size={18} />
              <span>Канал: @techargus</span>
              <ExternalLink size={14} />
            </button>
            <button
              onClick={openTelegramSupport}
              className="glass-card"
              style={{
                padding: '10px 18px',
                borderRadius: 14,
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                background: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: 'var(--accent, #ffffff)',
                fontSize: 13,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              <TelegramIcon size={18} />
              <span>Поддержка: @argus_adv</span>
              <ExternalLink size={14} />
            </button>
          </div>
        </div>

        {/* Feature Highlights Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
          <div className="glass-card" style={{ padding: '20px', borderRadius: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(255, 255, 255, 0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent, #ffffff)' }}>
              <Cpu size={18} />
            </div>
            <h4 style={{ fontSize: 14, fontWeight: 700, color: '#ffffff' }}>Динамический запуск</h4>
            <p style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.4 }}>
              Сканирует реестр App Paths, ярлыки меню «Пуск» и папки AppData. Запускает любые установленные на ПК программы.
            </p>
          </div>

          <div className="glass-card" style={{ padding: '20px', borderRadius: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(56,189,248,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#38bdf8' }}>
              <Terminal size={18} />
            </div>
            <h4 style={{ fontSize: 14, fontWeight: 700, color: '#ffffff' }}>Локальные плагины</h4>
            <p style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.4 }}>
              Возможность загружать Python скрипты (.py / .zip), запускать и мониторить фоновые процессы с выводом консольных логов.
            </p>
          </div>

          <div className="glass-card" style={{ padding: '20px', borderRadius: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(34,197,94,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#4ade80' }}>
              <Shield size={18} />
            </div>
            <h4 style={{ fontSize: 14, fontWeight: 700, color: '#ffffff' }}>Безопасность</h4>
            <p style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.4 }}>
              Все данные плагинов и лицензионные параметры кэшируются локально на компьютере, не отправляясь во внешние облака.
            </p>
          </div>
        </div>

        {/* System Details Footer */}
        <div className="glass-card" style={{ padding: '16px 20px', borderRadius: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 12, color: '#64748b', flexWrap: 'wrap', gap: 10 }}>
          <div>
            Argus Core Version: <span style={{ color: '#94a3b8', fontWeight: 600 }}>2.4.0-Enterprise</span>
          </div>
          <div style={{ display: 'flex', gap: 16 }}>
            <span>Канал: <a onClick={openTelegramChannel} style={{ color: '#38bdf8', cursor: 'pointer', textDecoration: 'underline' }}>t.me/techargus</a></span>
            <span>Поддержка: <a onClick={openTelegramSupport} style={{ color: 'var(--accent, #ffffff)', cursor: 'pointer', textDecoration: 'underline' }}>t.me/argus_adv</a></span>
          </div>
        </div>
      </div>
    </div>
  );
};
