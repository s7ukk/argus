import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, Square, Sparkles, Clock, Check, Mic, Bell, Info } from 'lucide-react';
import { TimerItem } from '../types';

export interface IslandNotification {
  id: string;
  text: string;
  type?: 'success' | 'info' | 'alert' | 'timer';
  duration?: number;
}

interface DynamicIslandProps {
  dictationState: { active: boolean; text?: string; success?: boolean } | null;
  isAiThinking: boolean;
  isSpeaking: boolean;
  onStopAi?: () => void;
}

export const DynamicIsland: React.FC<DynamicIslandProps> = ({
  dictationState,
  isAiThinking,
  isSpeaking,
  onStopAi,
}) => {
  const [activeTimer, setActiveTimer] = useState<TimerItem | null>(null);
  const [notification, setNotification] = useState<IslandNotification | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [hovered, setHovered] = useState(false);
  const notifyTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Poll / Listen for active running timers from localStorage
  useEffect(() => {
    const checkTimers = () => {
      try {
        const raw = localStorage.getItem('argus_extras_timers');
        if (raw) {
          const list: TimerItem[] = JSON.parse(raw);
          const running = list.find((t) => t.is_running && t.remaining_seconds > 0);
          setActiveTimer(running || null);
        } else {
          setActiveTimer(null);
        }
      } catch {
        setActiveTimer(null);
      }
    };

    checkTimers();
    const interval = setInterval(checkTimers, 800);
    window.addEventListener('argus_extras_updated', checkTimers);
    return () => {
      clearInterval(interval);
      window.removeEventListener('argus_extras_updated', checkTimers);
    };
  }, []);

  // Listen for in-app notifications/settings toasts to show right in Dynamic Island!
  useEffect(() => {
    const handleIslandNotify = (e: any) => {
      const detail = e.detail;
      if (!detail || !detail.text) return;

      if (notifyTimerRef.current) clearTimeout(notifyTimerRef.current);

      const notif: IslandNotification = {
        id: 'notif-' + Date.now(),
        text: detail.text,
        type: detail.type || 'info',
        duration: detail.duration || 3200,
      };

      setNotification(notif);

      try {
        (window as any).electronAPI?.showIslandNotification?.({
          text: detail.text,
          type: detail.type || 'info',
          duration: detail.duration || 3200,
        });
      } catch {}

      notifyTimerRef.current = setTimeout(() => {
        setNotification(null);
      }, notif.duration);
    };

    window.addEventListener('argus_island_notify', handleIslandNotify);
    return () => {
      window.removeEventListener('argus_island_notify', handleIslandNotify);
      if (notifyTimerRef.current) clearTimeout(notifyTimerRef.current);
    };
  }, []);

  const handleToggleTimer = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!activeTimer) return;
    try {
      const raw = localStorage.getItem('argus_extras_timers');
      if (raw) {
        const list: TimerItem[] = JSON.parse(raw);
        const updated = list.map((t) =>
          t.id === activeTimer.id ? { ...t, is_running: !t.is_running } : t
        );
        localStorage.setItem('argus_extras_timers', JSON.stringify(updated));
        window.dispatchEvent(new CustomEvent('argus_extras_updated'));
      }
    } catch (e) {
      console.warn('Failed to toggle timer:', e);
    }
  };

  const handleStopTimer = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!activeTimer) return;
    try {
      const raw = localStorage.getItem('argus_extras_timers');
      if (raw) {
        const list: TimerItem[] = JSON.parse(raw);
        const updated = list.map((t) =>
          t.id === activeTimer.id ? { ...t, is_running: false, remaining_seconds: t.duration_seconds } : t
        );
        localStorage.setItem('argus_extras_timers', JSON.stringify(updated));
        window.dispatchEvent(new CustomEvent('argus_extras_updated'));
      }
    } catch (e) {
      console.warn('Failed to stop timer:', e);
    }
  };

  const formatTimerTime = (totalSec: number) => {
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Determine priority states:
  // 1. Toast Notification / Settings / Timer finished
  // 2. Double-Ctrl Dictation HUD
  // 3. Active Running Timer
  // 4. AI Thinking / Speaking
  const hasNotif = Boolean(notification);
  const hasDictation = Boolean(dictationState);
  const hasTimer = Boolean(activeTimer && activeTimer.remaining_seconds > 0);
  const hasAiAction = isAiThinking || isSpeaking;

  const isVisible = hasNotif || hasDictation || hasTimer || hasAiAction;

  if (!isVisible) {
    return null;
  }

  const showExpanded = (isExpanded || hovered) && (hasTimer || hasAiAction) && !hasNotif && !hasDictation;

  return (
    <div
      className="no-drag"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => { setHovered(false); setIsExpanded(false); }}
      onClick={() => setIsExpanded(!isExpanded)}
      style={{
        position: 'fixed',
        top: 3,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 9999999, // Float on top of EVERYTHING
        minWidth: showExpanded
          ? 340
          : hasNotif
          ? 280
          : hasDictation
          ? 340
          : hasTimer
          ? 200
          : 170,
        height: showExpanded ? 76 : 32,
        borderRadius: showExpanded ? 24 : 9999,
        background: 'rgba(8, 8, 12, 0.92)',
        backdropFilter: 'blur(36px) saturate(200%)',
        WebkitBackdropFilter: 'blur(36px) saturate(200%)',
        border: hasNotif && notification?.type === 'success'
          ? '1px solid rgba(74, 222, 128, 0.45)'
          : hasNotif && notification?.type === 'timer'
          ? '1px solid rgba(251, 191, 36, 0.5)'
          : hasDictation && dictationState?.active
          ? '1px solid rgba(239, 68, 68, 0.65)'
          : hasDictation && dictationState?.success
          ? '1px solid rgba(74, 222, 128, 0.65)'
          : '1px solid rgba(255, 255, 255, 0.14)',
        boxShadow: hasDictation && dictationState?.active
          ? '0 16px 40px rgba(0, 0, 0, 0.75), 0 0 24px rgba(239, 68, 68, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.2)'
          : '0 16px 44px rgba(0, 0, 0, 0.75), 0 0 20px var(--accent-glow, rgba(255, 255, 255, 0.12)), inset 0 1px 0 rgba(255, 255, 255, 0.15)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: showExpanded ? '10px 18px' : '0 14px',
        cursor: (hasTimer || hasAiAction) ? 'pointer' : 'default',
        transition: 'all 0.32s cubic-bezier(0.16, 1, 0.3, 1)',
        userSelect: 'none',
        overflow: 'hidden',
      }}
    >
      {/* ─── 1. NOTIFICATIONS / SETTINGS POPUP DISPLAY ─── */}
      {hasNotif && !showExpanded ? (
        <div className="anim-fade-in" style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', justifyContent: 'center' }}>
          {notification?.type === 'success' ? (
            <div style={{ width: 18, height: 18, borderRadius: '50%', background: 'rgba(74, 222, 128, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Check size={11} color="#4ade80" />
            </div>
          ) : notification?.type === 'timer' ? (
            <Bell size={13} color="#fbbf24" className="anim-dot" />
          ) : (
            <Info size={13} color="var(--accent, #ffffff)" />
          )}
          <span style={{ fontSize: 12, fontWeight: 600, color: '#ffffff', letterSpacing: '0.01em', whiteSpace: 'nowrap' }}>
            {notification?.text}
          </span>
        </div>
      ) : !showExpanded ? (
        /* ─── 2. COMPACT PILL MODE ─── */
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, width: '100%' }}>
          {/* DICTATION (DOUBLE-CTRL) STATE */}
          {hasDictation ? (
            dictationState?.active ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: '#ef4444',
                      boxShadow: '0 0 10px #ef4444',
                    }}
                    className="anim-dot"
                  />
                  <span style={{ fontSize: 11.5, fontWeight: 700, color: '#ffffff', letterSpacing: '0.02em' }}>
                    Голосовой ввод... (Double-Ctrl)
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                  <span style={{ width: 2.5, height: 10, background: '#ef4444', borderRadius: 2 }} className="anim-dot" />
                  <span style={{ width: 2.5, height: 16, background: '#ef4444', borderRadius: 2 }} className="anim-dot" />
                  <span style={{ width: 2.5, height: 9, background: '#ef4444', borderRadius: 2 }} className="anim-dot" />
                </div>
              </>
            ) : dictationState?.success ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Check size={13} color="#4ade80" />
                <span style={{ fontSize: 11.5, fontWeight: 600, color: '#e2e8f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 260 }}>
                  «{dictationState.text}»
                </span>
              </div>
            ) : null
          ) : hasTimer && activeTimer ? (
            /* RUNNING TIMER PILL */
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, overflow: 'hidden' }}>
                <div
                  style={{
                    width: 18,
                    height: 18,
                    borderRadius: '50%',
                    background: 'rgba(255, 255, 255, 0.08)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Clock size={11} color="var(--accent, #ffffff)" />
                </div>
                <span
                  style={{
                    fontSize: 11.5,
                    fontWeight: 600,
                    color: '#e2e8f0',
                    maxWidth: 100,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {activeTimer.title}
                </span>
              </div>
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 800,
                  fontFamily: 'ui-monospace, monospace',
                  color: 'var(--accent, #ffffff)',
                  letterSpacing: '0.04em',
                }}
              >
                {formatTimerTime(activeTimer.remaining_seconds)}
              </span>
            </>
          ) : hasAiAction ? (
            /* AI THINKING (3 RUNNING DOTS) OR SPEAKING */
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {/* 3 Running / Place-Swapping Dots */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 3, width: 20, position: 'relative' }}>
                  <span
                    className="anim-dot-run-1"
                    style={{
                      width: 4.5,
                      height: 4.5,
                      borderRadius: '50%',
                      background: 'var(--accent, #ffffff)',
                    }}
                  />
                  <span
                    className="anim-dot-run-2"
                    style={{
                      width: 4.5,
                      height: 4.5,
                      borderRadius: '50%',
                      background: 'var(--accent, #ffffff)',
                      opacity: 0.8,
                    }}
                  />
                  <span
                    className="anim-dot-run-3"
                    style={{
                      width: 4.5,
                      height: 4.5,
                      borderRadius: '50%',
                      background: 'var(--accent, #ffffff)',
                      opacity: 0.6,
                    }}
                  />
                </div>
                <span
                  style={{
                    fontSize: 11.5,
                    fontWeight: 600,
                    color: '#ffffff',
                    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                  }}
                >
                  {isSpeaking ? 'Озвучивание...' : 'Thinking...'}
                </span>
              </div>
              {onStopAi && (
                <button
                  onClick={(e) => { e.stopPropagation(); onStopAi(); }}
                  style={{
                    width: 18,
                    height: 18,
                    borderRadius: '50%',
                    background: 'rgba(239, 68, 68, 0.3)',
                    border: '1px solid rgba(239, 68, 68, 0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                  }}
                  title="Остановить"
                >
                  <Square size={8} fill="#ffffff" color="#ffffff" />
                </button>
              )}
            </>
          ) : null}
        </div>
      ) : null}

      {/* ─── 3. EXPANDED INTERACTIVE CARD MODE ─── */}
      {showExpanded && (
        <div className="anim-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {hasTimer && activeTimer ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <span style={{ fontSize: 10.5, color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Таймер активности
                </span>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#ffffff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {activeTimer.title}
                </span>
                <span style={{ fontSize: 16, fontWeight: 800, fontFamily: 'ui-monospace, monospace', color: 'var(--accent, #ffffff)' }}>
                  {formatTimerTime(activeTimer.remaining_seconds)}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <button
                  onClick={handleToggleTimer}
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    background: 'rgba(255, 255, 255, 0.1)',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    color: '#ffffff',
                    transition: 'all 0.18s ease',
                  }}
                  title={activeTimer.is_running ? 'Пауза' : 'Возобновить'}
                >
                  {activeTimer.is_running ? <Pause size={13} /> : <Play size={13} />}
                </button>

                <button
                  onClick={handleStopTimer}
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    background: 'rgba(239, 68, 68, 0.2)',
                    border: '1px solid rgba(239, 68, 68, 0.4)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    color: '#f87171',
                    transition: 'all 0.18s ease',
                  }}
                  title="Сбросить таймер"
                >
                  <Square size={11} fill="#f87171" />
                </button>
              </div>
            </div>
          ) : hasAiAction ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Sparkles size={16} color="var(--accent, #ffffff)" className="anim-dot" />
                <div>
                  <div style={{ fontSize: 12.5, fontWeight: 700, color: '#ffffff' }}>
                    {isSpeaking ? 'Argus отвечает голосом' : 'Thinking...'}
                  </div>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>
                    Нажмите «Остановить» для прерывания
                  </div>
                </div>
              </div>

              {onStopAi && (
                <button
                  onClick={(e) => { e.stopPropagation(); onStopAi(); }}
                  style={{
                    padding: '6px 14px',
                    borderRadius: 9999,
                    background: 'rgba(239, 68, 68, 0.25)',
                    border: '1px solid rgba(239, 68, 68, 0.45)',
                    color: '#ffffff',
                    fontSize: 11.5,
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 5,
                  }}
                >
                  <Square size={10} fill="#ffffff" />
                  <span>Остановить</span>
                </button>
              )}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
};
