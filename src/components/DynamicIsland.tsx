import React, { useState, useEffect } from 'react';
import { Play, Pause, Square, Sparkles, Clock, CheckCircle2, Mic, Radio, Volume2 } from 'lucide-react';
import { TimerItem } from '../types';

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
  const [isExpanded, setIsExpanded] = useState(false);
  const [hovered, setHovered] = useState(false);

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

  // Determine priority state to display:
  // 1. Dictation (Double-Ctrl)
  // 2. Active Running Timer
  // 3. AI Thinking / Speaking
  // 4. Idle (subtle core status)
  const hasDictation = Boolean(dictationState);
  const hasTimer = Boolean(activeTimer && activeTimer.remaining_seconds > 0);
  const hasAiAction = isAiThinking || isSpeaking;

  // If nothing active and not hovered/expanded, remain invisible or ultra-subtle
  const isVisible = hasDictation || hasTimer || hasAiAction;

  if (!isVisible) {
    return null;
  }

  const showExpanded = (isExpanded || hovered) && (hasTimer || hasAiAction);

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => { setHovered(false); setIsExpanded(false); }}
      onClick={() => setIsExpanded(!isExpanded)}
      style={{
        position: 'fixed',
        top: 44, // Cleanly below the 38px titlebar
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 900,
        minWidth: showExpanded ? 340 : hasDictation ? 320 : hasTimer ? 210 : 170,
        height: showExpanded ? 76 : 32,
        borderRadius: showExpanded ? 24 : 9999,
        background: 'rgba(8, 8, 12, 0.88)',
        backdropFilter: 'blur(32px) saturate(190%)',
        WebkitBackdropFilter: 'blur(32px) saturate(190%)',
        border: hasDictation && dictationState?.active
          ? '1px solid rgba(239, 68, 68, 0.6)'
          : hasDictation && dictationState?.success
          ? '1px solid rgba(34, 197, 94, 0.6)'
          : '1px solid rgba(255, 255, 255, 0.12)',
        boxShadow: hasDictation && dictationState?.active
          ? '0 12px 36px rgba(0, 0, 0, 0.7), 0 0 20px rgba(239, 68, 68, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.2)'
          : '0 12px 36px rgba(0, 0, 0, 0.7), 0 0 20px var(--accent-glow, rgba(255, 255, 255, 0.15)), inset 0 1px 0 rgba(255, 255, 255, 0.15)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: showExpanded ? '10px 18px' : '0 14px',
        cursor: (hasTimer || hasAiAction) ? 'pointer' : 'default',
        transition: 'all 0.34s cubic-bezier(0.16, 1, 0.3, 1)',
        userSelect: 'none',
        overflow: 'hidden',
      }}
    >
      {/* ─── COMPACT PILL MODE ─── */}
      {!showExpanded && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, width: '100%' }}>
          {/* DICTATION STATE */}
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
                    Голосовой ввод...
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <span style={{ width: 2.5, height: 10, background: '#ef4444', borderRadius: 2 }} className="anim-dot" />
                  <span style={{ width: 2.5, height: 15, background: '#ef4444', borderRadius: 2 }} className="anim-dot" />
                  <span style={{ width: 2.5, height: 8, background: '#ef4444', borderRadius: 2 }} className="anim-dot" />
                </div>
              </>
            ) : dictationState?.success ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ color: '#22c55e', fontSize: 13, fontWeight: 800 }}>✓</span>
                <span style={{ fontSize: 11.5, fontWeight: 600, color: '#e2e8f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 240 }}>
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
            /* AI THINKING / SPEAKING PILL */
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                <Sparkles size={12} color="var(--accent, #ffffff)" className="anim-dot" />
                <span style={{ fontSize: 11.5, fontWeight: 600, color: '#e2e8f0' }}>
                  {isSpeaking ? 'Озвучивание...' : 'Argus думает...'}
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
      )}

      {/* ─── EXPANDED INTERACTIVE CARD MODE ─── */}
      {showExpanded && (
        <div className="anim-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {hasTimer && activeTimer ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <span style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Таймер активности
                </span>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#ffffff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {activeTimer.title}
                </span>
                <span style={{ fontSize: 17, fontWeight: 800, fontFamily: 'ui-monospace, monospace', color: 'var(--accent, #ffffff)' }}>
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
                    {isSpeaking ? 'Argus отвечает голосом' : 'Нейросеть генерирует ответ'}
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
