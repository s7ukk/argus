import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Database,
  HardDrive,
  Volume2,
  VolumeX,
  Sun,
  Shield,
  Trash2,
  RefreshCw,
  Power,
  Lock,
  Layers,
  CheckCircle,
  Activity
} from 'lucide-react';
import { SystemStats } from '../types';
import { getSystemStats, setVolume, setBrightness, lockPC, launchApp } from '../api';

export const SystemView: React.FC = () => {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [volLevel, setVolLevel] = useState(50);
  const [brLevel, setBrLevel] = useState(80);
  const [isMuted, setIsMuted] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await getSystemStats();
      setStats(data);
      if (data.volume !== undefined) setVolLevel(data.volume);
      if (data.brightness !== undefined) setBrLevel(data.brightness);
    } catch (e) {
      console.error('Failed to get stats:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 3000);
    return () => clearInterval(interval);
  }, []);

  const notify = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3000);
  };

  const handleVolumeChange = async (newVal: number) => {
    setVolLevel(newVal);
    try {
      await setVolume({ level: newVal });
    } catch (e) {}
  };

  const handleMuteToggle = async () => {
    try {
      const res = await setVolume({ mute_toggle: true });
      setIsMuted(res.muted);
      notify(res.muted ? 'Звук выключен' : 'Звук включен');
    } catch (e) {}
  };

  const handleBrightnessChange = async (newVal: number) => {
    setBrLevel(newVal);
    try {
      await setBrightness({ level: newVal });
    } catch (e) {}
  };

  const handleLock = async () => {
    try {
      await lockPC();
      notify('Компьютер заблокирован');
    } catch (e) {}
  };

  const handleOpenTaskMgr = async () => {
    try {
      await launchApp('taskmgr.exe');
      notify('Диспетчер задач открыт');
    } catch (e) {}
  };

  return (
    <div
      style={{
        flex: 1,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        background: 'rgba(7, 5, 15, 0.65)',
        position: 'relative',
        userSelect: 'none',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          padding: '18px 28px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(12, 9, 24, 0.5)',
          backdropFilter: 'blur(10px)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div
            style={{
              width: 38,
              height: 38,
              borderRadius: 12,
              background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.25) 0%, rgba(168, 85, 247, 0.2) 100%)',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#38bdf8',
            }}
          >
            <Cpu size={20} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h2 style={{ fontSize: 18, fontWeight: 800, color: '#ffffff', letterSpacing: '0.02em' }}>
                Управление ПК и Телеметрия
              </h2>
              <span
                style={{
                  fontSize: 10.5,
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: 99,
                  background: 'rgba(34, 197, 94, 0.12)',
                  border: '1px solid rgba(34, 197, 94, 0.3)',
                  color: '#4ade80',
                  textTransform: 'uppercase',
                }}
              >
                Hardware Realtime
              </span>
            </div>
            <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
              Мониторинг нагрузки оборудования Windows и прямое системное управление
            </p>
          </div>
        </div>

        <button
          onClick={fetchStats}
          className="btn-icon"
          style={{ width: 36, height: 36 }}
          title="Обновить телеметрию"
        >
          <RefreshCw size={16} className={loading ? 'anim-spin' : ''} />
        </button>
      </div>

      {notification && (
        <div
          className="anim-fade-up"
          style={{
            position: 'absolute',
            top: 75,
            right: 28,
            zIndex: 50,
            padding: '8px 16px',
            borderRadius: 12,
            background: 'rgba(168, 85, 247, 0.2)',
            border: '1px solid rgba(168, 85, 247, 0.4)',
            color: '#e9d5ff',
            fontSize: 12.5,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            backdropFilter: 'blur(10px)',
          }}
        >
          <CheckCircle size={15} color="#c084fc" />
          <span>{notification}</span>
        </div>
      )}

      {/* Main Grid Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Metric Cards Row */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: 16,
          }}
        >
          {/* CPU Gauge */}
          <div
            className="glass-card"
            style={{
              padding: '20px',
              borderRadius: 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>
                Процессор (CPU)
              </span>
              <Cpu size={18} color="#38bdf8" />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
              <span style={{ fontSize: 32, fontWeight: 800, color: '#ffffff' }}>
                {stats?.cpu?.percent ?? 0}%
              </span>
              <span style={{ fontSize: 12, color: '#64748b' }}>
                {stats?.cpu?.cores ?? 0} ядер / {stats?.cpu?.freq_mhz ?? 0} MHz
              </span>
            </div>
            {/* Progress Bar */}
            <div style={{ width: '100%', height: 6, borderRadius: 99, background: 'rgba(255, 255, 255, 0.08)', overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${stats?.cpu?.percent ?? 0}%`,
                  borderRadius: 99,
                  background: 'linear-gradient(90deg, #38bdf8 0%, #a855f7 100%)',
                  transition: 'width 0.4s ease',
                }}
              />
            </div>
          </div>

          {/* RAM Gauge */}
          <div
            className="glass-card"
            style={{
              padding: '20px',
              borderRadius: 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>
                Память (RAM)
              </span>
              <Database size={18} color="#c084fc" />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
              <span style={{ fontSize: 32, fontWeight: 800, color: '#ffffff' }}>
                {stats?.memory?.percent ?? 0}%
              </span>
              <span style={{ fontSize: 12, color: '#64748b' }}>
                {stats?.memory?.used_gb ?? 0} / {stats?.memory?.total_gb ?? 0} GB
              </span>
            </div>
            <div style={{ width: '100%', height: 6, borderRadius: 99, background: 'rgba(255, 255, 255, 0.08)', overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${stats?.memory?.percent ?? 0}%`,
                  borderRadius: 99,
                  background: 'linear-gradient(90deg, #a855f7 0%, #ec4899 100%)',
                  transition: 'width 0.4s ease',
                }}
              />
            </div>
          </div>

          {/* Disk Gauge */}
          <div
            className="glass-card"
            style={{
              padding: '20px',
              borderRadius: 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>
                Системный диск (C:)
              </span>
              <HardDrive size={18} color="#4ade80" />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
              <span style={{ fontSize: 32, fontWeight: 800, color: '#ffffff' }}>
                {stats?.disk?.percent ?? 0}%
              </span>
              <span style={{ fontSize: 12, color: '#64748b' }}>
                {stats?.disk?.free_gb ?? 0} GB свободно
              </span>
            </div>
            <div style={{ width: '100%', height: 6, borderRadius: 99, background: 'rgba(255, 255, 255, 0.08)', overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${stats?.disk?.percent ?? 0}%`,
                  borderRadius: 99,
                  background: 'linear-gradient(90deg, #4ade80 0%, #38bdf8 100%)',
                  transition: 'width 0.4s ease',
                }}
              />
            </div>
          </div>
        </div>

        {/* Sliders & Direct Hardware Controls */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
            gap: 16,
          }}
        >
          {/* Master Volume Slider */}
          <div className="glass-card" style={{ padding: '20px', borderRadius: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {isMuted ? <VolumeX size={20} color="#f87171" /> : <Volume2 size={20} color="#38bdf8" />}
                <span style={{ fontSize: 14, fontWeight: 700, color: '#ffffff' }}>
                  Громкость системы
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 14, fontWeight: 800, color: '#38bdf8', fontFamily: 'monospace' }}>
                  {isMuted ? 'MUTE' : `${volLevel}%`}
                </span>
                <button
                  onClick={handleMuteToggle}
                  className="btn-icon"
                  style={{ width: 30, height: 30, color: isMuted ? '#f87171' : '#94a3b8' }}
                  title={isMuted ? 'Включить звук' : 'Заглушить звук'}
                >
                  {isMuted ? <VolumeX size={15} /> : <Volume2 size={15} />}
                </button>
              </div>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={volLevel}
              onChange={(e) => handleVolumeChange(Number(e.target.value))}
              style={{ width: '100%', cursor: 'pointer', accentColor: '#38bdf8' }}
            />
          </div>

          {/* Screen Brightness Slider */}
          <div className="glass-card" style={{ padding: '20px', borderRadius: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Sun size={20} color="#fbbf24" />
                <span style={{ fontSize: 14, fontWeight: 700, color: '#ffffff' }}>
                  Яркость монитора
                </span>
              </div>
              <span style={{ fontSize: 14, fontWeight: 800, color: '#fbbf24', fontFamily: 'monospace' }}>
                {brLevel}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={brLevel}
              onChange={(e) => handleBrightnessChange(Number(e.target.value))}
              style={{ width: '100%', cursor: 'pointer', accentColor: '#fbbf24' }}
            />
          </div>
        </div>

        {/* Quick System Action Buttons */}
        <div className="glass-card" style={{ padding: '20px', borderRadius: 16 }}>
          <h4 style={{ fontSize: 14, fontWeight: 700, color: '#ffffff', marginBottom: 14 }}>
            Быстрые системные команды Windows
          </h4>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            <button
              onClick={handleOpenTaskMgr}
              className="glass-card"
              style={{
                padding: '10px 16px',
                borderRadius: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 13,
                fontWeight: 600,
                color: '#f1f5f9',
                cursor: 'pointer',
              }}
            >
              <Activity size={16} color="#38bdf8" />
              <span>Диспетчер задач</span>
            </button>

            <button
              onClick={handleLock}
              className="glass-card"
              style={{
                padding: '10px 16px',
                borderRadius: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 13,
                fontWeight: 600,
                color: '#f1f5f9',
                cursor: 'pointer',
              }}
            >
              <Lock size={16} color="#c084fc" />
              <span>Заблокировать ПК</span>
            </button>

            <button
              onClick={async () => {
                await launchApp('explorer.exe');
                notify('Проводник открыт');
              }}
              className="glass-card"
              style={{
                padding: '10px 16px',
                borderRadius: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 13,
                fontWeight: 600,
                color: '#f1f5f9',
                cursor: 'pointer',
              }}
            >
              <Layers size={16} color="#4ade80" />
              <span>Открыть Проводник</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
