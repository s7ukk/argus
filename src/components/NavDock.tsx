import React, { useState, useEffect, useRef, useLayoutEffect } from 'react';
import { MessageSquare, Boxes, Cpu, Info, Sparkles, User, Settings, Workflow, BookmarkCheck } from 'lucide-react';
import { UserProfile, NavTab } from '../types';
import { NavPosition } from '../utils/theme';

interface NavDockProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  profile: UserProfile;
  onOpenProfile: () => void;
  position?: NavPosition;
  isFloating?: boolean;
}

export const NavDock: React.FC<NavDockProps> = ({
  activeTab,
  onTabChange,
  profile,
  onOpenProfile,
  position = 'top',
  isFloating = false,
}) => {
  const tabs: { id: NavTab; label: string; icon: React.ReactNode }[] = [
    { id: 'chat', label: 'Чат', icon: <MessageSquare size={14} /> },
    { id: 'scenarios', label: 'Сценарии', icon: <Workflow size={14} /> },
    { id: 'plugins', label: 'Плагины', icon: <Boxes size={14} /> },
    { id: 'extras', label: 'Инструменты', icon: <BookmarkCheck size={14} /> },
    { id: 'system', label: 'Система', icon: <Cpu size={14} /> },
    { id: 'about', label: 'О системе', icon: <Info size={14} /> },
    { id: 'settings', label: 'Настройки', icon: <Settings size={14} /> },
  ];

  const isVertical = position === 'left' || position === 'right';

  const containerRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  // Active / scrubbed tab state
  const [scrubTab, setScrubTab] = useState<NavTab>(activeTab);
  const [isScrubbing, setIsScrubbing] = useState(false);

  // Position morphing & staggered stream assembly state
  const [isRepositioning, setIsRepositioning] = useState(false);
  const [morphDeltas, setMorphDeltas] = useState<{ dx: number; dy: number }>({ dx: 0, dy: 0 });
  const prevPositionRef = useRef<NavPosition>(position);

  useEffect(() => {
    if (prevPositionRef.current !== position) {
      const prev = prevPositionRef.current;
      const next = position;
      prevPositionRef.current = position;

      // Subtle, high-speed directional stream vectors
      let dx = 0;
      let dy = 0;
      if (prev === 'top' && next === 'left') { dx = 24; dy = -16; }
      else if (prev === 'top' && next === 'right') { dx = -24; dy = -16; }
      else if (prev === 'left' && next === 'right') { dx = -28; dy = 0; }
      else if (prev === 'right' && next === 'left') { dx = 28; dy = 0; }
      else if (prev === 'left' && next === 'top') { dx = -20; dy = 20; }
      else if (prev === 'right' && next === 'top') { dx = 20; dy = 20; }

      setMorphDeltas({ dx, dy });
      setIsRepositioning(true);

      const timer = setTimeout(() => {
        setIsRepositioning(false);
      }, 450);
      return () => clearTimeout(timer);
    }
  }, [position]);

  // Liquid glass sliding lens geometry (relative to container)
  const [lensStyle, setLensStyle] = useState<{
    left: number;
    top: number;
    width: number;
    height: number;
    opacity: number;
  }>({
    left: 0,
    top: 0,
    width: 0,
    height: 0,
    opacity: 0,
  });

  // Measure active button position within capsule container
  const updateLens = (targetTab: NavTab) => {
    const container = containerRef.current;
    const btn = tabRefs.current[targetTab];
    if (!container || !btn) return;

    const cRect = container.getBoundingClientRect();
    const bRect = btn.getBoundingClientRect();

    setLensStyle({
      left: bRect.left - cRect.left,
      top: bRect.top - cRect.top,
      width: bRect.width,
      height: bRect.height,
      opacity: 1,
    });
  };

  // Keep scrubTab and lens in sync when activeTab changes externally
  useEffect(() => {
    if (!isScrubbing) {
      setScrubTab(activeTab);
      updateLens(activeTab);
    }
  }, [activeTab, isScrubbing]);

  useLayoutEffect(() => {
    updateLens(scrubTab);
    const handleResize = () => updateLens(scrubTab);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [scrubTab, position]);

  // Immediate Click Handling (Always works instantly without event suppression)
  const handleTabClick = (tabId: NavTab) => {
    onTabChange(tabId);
    setScrubTab(tabId);
    updateLens(tabId);
  };

  // Continuous Fluid Drag-Scrubbing Handlers (iOS 27 gesture without blocking normal clicks)
  const startPosRef = useRef<{ x: number; y: number } | null>(null);
  const isDraggingRef = useRef(false);
  const currentScrubTabRef = useRef<NavTab>(scrubTab);

  const findNearestTab = (clientX: number, clientY: number): NavTab => {
    let nearestTab: NavTab = scrubTab;
    let minDistance = Infinity;

    tabs.forEach((t) => {
      const btn = tabRefs.current[t.id];
      if (!btn) return;
      const rect = btn.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const dist = Math.hypot(clientX - centerX, clientY - centerY);
      if (dist < minDistance) {
        minDistance = dist;
        nearestTab = t.id;
      }
    });

    return nearestTab;
  };

  const handlePointerDown = (tabId: NavTab, e: React.PointerEvent) => {
    startPosRef.current = { x: e.clientX, y: e.clientY };
    isDraggingRef.current = false;
    currentScrubTabRef.current = tabId;

    const onPointerMove = (ev: PointerEvent) => {
      if (!startPosRef.current) return;
      const dist = Math.hypot(ev.clientX - startPosRef.current.x, ev.clientY - startPosRef.current.y);
      if (dist > 7) {
        if (!isDraggingRef.current) {
          isDraggingRef.current = true;
          setIsScrubbing(true);
        }
        const nearest = findNearestTab(ev.clientX, ev.clientY);
        if (nearest && nearest !== currentScrubTabRef.current) {
          currentScrubTabRef.current = nearest;
          setScrubTab(nearest);
          updateLens(nearest);
        }
      }
    };

    const onPointerUp = () => {
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
      window.removeEventListener('pointercancel', onPointerUp);

      if (isDraggingRef.current && currentScrubTabRef.current) {
        onTabChange(currentScrubTabRef.current);
      }
      startPosRef.current = null;
      isDraggingRef.current = false;
      setIsScrubbing(false);
    };

    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    window.addEventListener('pointercancel', onPointerUp);
  };

  // Floating dock layout styles with fluid Apple-grade spring physics
  const floatingStyle: React.CSSProperties = isFloating
    ? {
        position: 'fixed',
        zIndex: 99,
        transition: 'top 0.38s cubic-bezier(0.16, 1, 0.3, 1), left 0.38s cubic-bezier(0.16, 1, 0.3, 1), transform 0.38s cubic-bezier(0.16, 1, 0.3, 1)',
        ...(position === 'top'
          ? {
              top: 7,
              left: '50%',
              transform: 'translate(-50%, 0)',
              width: 'auto',
              height: 'auto',
            }
          : position === 'left'
          ? {
              top: '50%',
              left: 14,
              transform: 'translate(0, -50%)',
              width: 'auto',
              height: 'auto',
            }
          : {
              top: '50%',
              left: 'calc(100% - 14px)',
              transform: 'translate(-100%, -50%)',
              width: 'auto',
              height: 'auto',
            }),
      }
    : {
        position: 'relative',
        zIndex: 40,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      };

  return (
    <>
      <style>{`
        @keyframes liquidStreamAssemble {
          0% {
            opacity: 0;
            transform: translate3d(var(--pdx, 0px), var(--pdy, 0px), 0) scale(0.88);
          }
          65% {
            opacity: 1;
            transform: translate3d(calc(var(--pdx, 0px) * -0.06), calc(var(--pdy, 0px) * -0.06), 0) scale(1.02);
          }
          100% {
            opacity: 1;
            transform: translate3d(0, 0, 0) scale(1);
          }
        }
        @keyframes liquidGlassSheen {
          0% {
            transform: translateX(-120%) skewX(-20deg);
            opacity: 0;
          }
          30% {
            opacity: 1;
          }
          100% {
            transform: translateX(240%) skewX(-20deg);
            opacity: 0;
          }
        }
        @keyframes stardustStream {
          0% {
            opacity: 0;
            transform: translate3d(var(--pdx, 0px), var(--pdy, 0px), 0) scale(0.3);
          }
          35% {
            opacity: 0.95;
            transform: translate3d(calc(var(--pdx, 0px) * 0.35), calc(var(--pdy, 0px) * 0.35), 0) scale(1.3);
          }
          100% {
            opacity: 0;
            transform: translate3d(0, 0, 0) scale(0.2);
          }
        }
      `}</style>

      <nav
        aria-label="Основное меню"
        className="no-drag"
        style={{
          userSelect: 'none',
          WebkitAppRegion: 'no-drag' as any,
          pointerEvents: 'auto',
          ...floatingStyle,
        }}
      >
        {/* ─── FLOATING LIQUID GLASS CAPSULE ─── */}
        <div
          ref={containerRef}
          className="no-drag"
          style={{
            position: 'relative',
            display: 'flex',
            flexDirection: isVertical ? 'column' : 'row',
            alignItems: 'center',
            gap: 3,
            padding: isVertical ? '8px 5px' : '4px 6px',
            height: isVertical ? 'auto' : 36,
            borderRadius: 9999,
            background: 'rgba(12, 12, 18, 0.82)',
            backdropFilter: 'blur(35px) saturate(210%)',
            WebkitBackdropFilter: 'blur(35px) saturate(210%)',
            border: '1px solid rgba(255, 255, 255, 0.14)',
            WebkitAppRegion: 'no-drag' as any,
            pointerEvents: 'auto',
            boxShadow: isScrubbing || isRepositioning
              ? '0 18px 45px rgba(0, 0, 0, 0.75), inset 0 1px 1px rgba(255, 255, 255, 0.45), inset 0 -1px 1px rgba(0, 0, 0, 0.4), 0 0 28px var(--accent-glow, rgba(255, 255, 255, 0.2))'
              : '0 16px 40px rgba(0, 0, 0, 0.7), inset 0 1px 1px rgba(255, 255, 255, 0.35), inset 0 -1px 1px rgba(0, 0, 0, 0.4), 0 0 20px var(--accent-glow, rgba(255, 255, 255, 0.08))',
            transition: 'box-shadow 0.28s ease, border-color 0.28s ease, gap 0.32s ease, padding 0.32s ease',
            touchAction: 'none',
            overflow: 'hidden',
          }}
        >
          {/* ─── LIQUID GLASS WAVE SHEEN (Световая волна при перемещении) ─── */}
          {isRepositioning && (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                borderRadius: 9999,
                overflow: 'hidden',
                pointerEvents: 'none',
                zIndex: 4,
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  inset: '-100%',
                  background: 'linear-gradient(105deg, transparent 25%, rgba(255, 255, 255, 0.32) 50%, transparent 75%)',
                  animation: 'liquidGlassSheen 0.42s cubic-bezier(0.16, 1, 0.3, 1) both',
                }}
              />
            </div>
          )}

          {/* ─── MICRO-STARDUST STREAM (Тонкие световые частицы) ─── */}
          {isRepositioning && (
            <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'visible', zIndex: 3 }}>
              {Array.from({ length: 8 }).map((_, pIdx) => (
                <div
                  key={pIdx}
                  style={{
                    position: 'absolute',
                    left: `${15 + pIdx * 10}%`,
                    top: '50%',
                    width: 2,
                    height: 2,
                    borderRadius: '50%',
                    background: pIdx % 2 === 0 ? 'var(--accent, #ffffff)' : '#38bdf8',
                    boxShadow: '0 0 6px var(--accent, #ffffff)',
                    opacity: 0,
                    animation: `stardustStream 0.34s cubic-bezier(0.16, 1, 0.3, 1) ${pIdx * 18}ms both`,
                    ['--pdx' as any]: `${morphDeltas.dx * 1.2}px`,
                    ['--pdy' as any]: `${morphDeltas.dy * 1.2}px`,
                  }}
                />
              ))}
            </div>
          )}

          {/* ─── LIQUID GLASS SLIDING LENS (iOS 27 Fluid Indicator) ─── */}
          <div
            style={{
              position: 'absolute',
              left: lensStyle.left,
              top: lensStyle.top,
              width: lensStyle.width,
              height: lensStyle.height,
              opacity: lensStyle.opacity,
              borderRadius: 9999,
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.22) 0%, rgba(255, 255, 255, 0.08) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.32)',
              boxShadow: '0 4px 18px rgba(0, 0, 0, 0.45), inset 0 1px 1.5px rgba(255, 255, 255, 0.5), inset 0 -1px 1px rgba(0, 0, 0, 0.3), 0 0 18px var(--accent-glow, rgba(255, 255, 255, 0.15))',
              transform: isScrubbing ? 'scale(1.05)' : 'scale(1)',
              transition: isScrubbing
                ? 'left 0.12s cubic-bezier(0.2, 0.9, 0.3, 1.2), top 0.12s cubic-bezier(0.2, 0.9, 0.3, 1.2), width 0.18s ease, height 0.18s ease, transform 0.2s cubic-bezier(0.34, 1.4, 0.64, 1)'
                : 'all 0.32s cubic-bezier(0.16, 1, 0.3, 1)',
              pointerEvents: 'none',
              zIndex: 1,
              willChange: 'left, top, width, height, transform',
            }}
          />

          {/* Sparkle Core Mini Icon (Index 0) */}
          <button
            className="no-drag"
            onClick={() => handleTabClick('chat')}
            style={{
              position: 'relative',
              zIndex: 2,
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.14)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: 'var(--accent, #ffffff)',
              flexShrink: 0,
              WebkitAppRegion: 'no-drag' as any,
              pointerEvents: 'auto',
              transition: 'all 0.2s ease',
              animation: isRepositioning ? `liquidStreamAssemble 0.32s cubic-bezier(0.16, 1, 0.3, 1) 0ms both` : undefined,
              ['--pdx' as any]: `${morphDeltas.dx}px`,
              ['--pdy' as any]: `${morphDeltas.dy}px`,
            }}
            title="Чат Argus"
          >
            <Sparkles size={13} />
          </button>

          {/* Subtle Separator 1 (Index 1) */}
          <div
            style={{
              position: 'relative',
              zIndex: 2,
              background: 'rgba(255, 255, 255, 0.12)',
              flexShrink: 0,
              ...(isVertical
                ? { width: 18, height: 1, margin: '2px 0' }
                : { width: 1, height: 18, margin: '0 3px' }),
              animation: isRepositioning ? `liquidStreamAssemble 0.32s cubic-bezier(0.16, 1, 0.3, 1) 16ms both` : undefined,
              ['--pdx' as any]: `${morphDeltas.dx}px`,
              ['--pdy' as any]: `${morphDeltas.dy}px`,
            }}
          />

          {/* Tab Buttons (Indices 2..8 — Staggered Liquid Wave Assembly) */}
          {tabs.map((tab, idx) => {
            const isActive = (isScrubbing ? scrubTab : activeTab) === tab.id;
            const staggerDelay = 32 + idx * 16;
            return (
              <button
                key={tab.id}
                ref={(el) => { tabRefs.current[tab.id] = el; }}
                className="no-drag"
                onPointerDown={(e) => handlePointerDown(tab.id, e)}
                onClick={() => handleTabClick(tab.id)}
                style={{
                  position: 'relative',
                  zIndex: 2,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: isVertical ? '8px 10px' : '5px 12px',
                  borderRadius: 9999,
                  fontSize: 11.5,
                  fontWeight: isActive ? 600 : 500,
                  letterSpacing: '0.01em',
                  cursor: 'pointer',
                  border: '1px solid transparent',
                  background: 'transparent',
                  color: isActive ? '#ffffff' : '#94a3b8',
                  transition: 'color 0.2s ease, transform 0.2s ease',
                  whiteSpace: 'nowrap',
                  transform: isScrubbing && isActive ? 'scale(1.04)' : 'scale(1)',
                  WebkitAppRegion: 'no-drag' as any,
                  pointerEvents: 'auto',
                  touchAction: 'none',
                  animation: isRepositioning ? `liquidStreamAssemble 0.34s cubic-bezier(0.16, 1, 0.3, 1) ${staggerDelay}ms both` : undefined,
                  ['--pdx' as any]: `${morphDeltas.dx}px`,
                  ['--pdy' as any]: `${morphDeltas.dy}px`,
                }}
                title={tab.label}
              >
                <span
                  style={{
                    color: isActive ? 'var(--accent, #ffffff)' : 'inherit',
                    display: 'flex',
                    transition: 'color 0.2s ease',
                  }}
                >
                  {tab.icon}
                </span>
                {!isVertical && <span>{tab.label}</span>}
              </button>
            );
          })}

          {/* Subtle Separator 2 (Index 9) */}
          <div
            style={{
              position: 'relative',
              zIndex: 2,
              background: 'rgba(255, 255, 255, 0.12)',
              flexShrink: 0,
              ...(isVertical
                ? { width: 18, height: 1, margin: '2px 0' }
                : { width: 1, height: 18, margin: '0 3px' }),
              animation: isRepositioning ? `liquidStreamAssemble 0.32s cubic-bezier(0.16, 1, 0.3, 1) 160ms both` : undefined,
              ['--pdx' as any]: `${morphDeltas.dx}px`,
              ['--pdy' as any]: `${morphDeltas.dy}px`,
            }}
          />

          {/* Profile Avatar Miniature Button (Index 10) */}
          <button
            className="no-drag"
            onClick={onOpenProfile}
            style={{
              position: 'relative',
              zIndex: 2,
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.18) 0%, rgba(255, 255, 255, 0.05) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.22)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: '#ffffff',
              fontSize: 11,
              fontWeight: 700,
              flexShrink: 0,
              WebkitAppRegion: 'no-drag' as any,
              pointerEvents: 'auto',
              boxShadow: '0 0 10px var(--accent-glow, rgba(255, 255, 255, 0.15))',
              transition: 'all 0.18s ease',
              animation: isRepositioning ? `liquidStreamAssemble 0.32s cubic-bezier(0.16, 1, 0.3, 1) 176ms both` : undefined,
              ['--pdx' as any]: `${morphDeltas.dx}px`,
              ['--pdy' as any]: `${morphDeltas.dy}px`,
            }}
            title={`Профиль: ${profile.display_name || 'Пользователь'}`}
          >
            {profile.display_name ? profile.display_name.charAt(0).toUpperCase() : <User size={12} />}
          </button>
        </div>
      </nav>
    </>
  );
};
