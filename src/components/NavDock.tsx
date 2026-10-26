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

  // Keep scrubTab in sync when activeTab changes externally
  useEffect(() => {
    if (!isScrubbing) {
      setScrubTab(activeTab);
    }
  }, [activeTab, isScrubbing]);

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

  useLayoutEffect(() => {
    updateLens(scrubTab);
    const handleResize = () => updateLens(scrubTab);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [scrubTab, position]);

  // Liquid Glass Drag-Scrubbing Handlers (iOS 27 gesture)
  const isPointerDownRef = useRef(false);
  const currentScrubTabRef = useRef<NavTab>(activeTab);

  const findNearestTab = (clientX: number, clientY: number): NavTab | null => {
    let closestTab: NavTab | null = null;
    let minDistance = Infinity;

    for (const t of tabs) {
      const el = tabRefs.current[t.id];
      if (!el) continue;
      const rect = el.getBoundingClientRect();

      // Check if point is inside
      if (
        clientX >= rect.left &&
        clientX <= rect.right &&
        clientY >= rect.top &&
        clientY <= rect.bottom
      ) {
        return t.id;
      }

      // Calculate center distance
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const dist = Math.hypot(clientX - centerX, clientY - centerY);

      if (dist < minDistance) {
        minDistance = dist;
        closestTab = t.id;
      }
    }

    return closestTab;
  };

  const handlePointerDown = (tabId: NavTab, e: React.PointerEvent) => {
    e.preventDefault();
    isPointerDownRef.current = true;
    currentScrubTabRef.current = tabId;
    setIsScrubbing(true);
    setScrubTab(tabId);
    updateLens(tabId);

    const onPointerMove = (ev: PointerEvent) => {
      if (!isPointerDownRef.current) return;
      const nearest = findNearestTab(ev.clientX, ev.clientY);
      if (nearest && nearest !== currentScrubTabRef.current) {
        currentScrubTabRef.current = nearest;
        setScrubTab(nearest);
        updateLens(nearest);
      }
    };

    const onPointerUp = () => {
      isPointerDownRef.current = false;
      setIsScrubbing(false);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
      window.removeEventListener('pointercancel', onPointerUp);

      if (currentScrubTabRef.current) {
        onTabChange(currentScrubTabRef.current);
      }
    };

    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    window.addEventListener('pointercancel', onPointerUp);
  };

  // Floating dock layout styles
  const floatingStyle: React.CSSProperties = isFloating
    ? {
        position: 'fixed',
        zIndex: 99,
        transition: 'top 0.55s cubic-bezier(0.34, 1.25, 0.64, 1), left 0.55s cubic-bezier(0.34, 1.25, 0.64, 1), transform 0.55s cubic-bezier(0.34, 1.25, 0.64, 1), width 0.4s ease, height 0.4s ease',
        ...(position === 'top'
          ? {
              top: 6,
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
    <nav
      className="no-drag"
      style={{
        userSelect: 'none',
        ...floatingStyle,
      }}
    >
      {/* ─── FLOATING LIQUID GLASS CAPSULE ─── */}
      <div
        ref={containerRef}
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
          boxShadow: isScrubbing
            ? '0 18px 45px rgba(0, 0, 0, 0.75), inset 0 1px 1px rgba(255, 255, 255, 0.45), inset 0 -1px 1px rgba(0, 0, 0, 0.4), 0 0 28px var(--accent-glow, rgba(255, 255, 255, 0.2))'
            : '0 16px 40px rgba(0, 0, 0, 0.7), inset 0 1px 1px rgba(255, 255, 255, 0.35), inset 0 -1px 1px rgba(0, 0, 0, 0.4), 0 0 20px var(--accent-glow, rgba(255, 255, 255, 0.08))',
          transition: 'box-shadow 0.3s ease, border-color 0.3s ease, gap 0.4s ease, padding 0.4s ease',
          touchAction: 'none',
        }}
      >
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
              : 'all 0.32s cubic-bezier(0.34, 1.4, 0.64, 1)',
            pointerEvents: 'none',
            zIndex: 1,
            willChange: 'left, top, width, height, transform',
          }}
        />

        {/* Sparkle Core Mini Icon */}
        <button
          onClick={() => onTabChange('chat')}
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
            transition: 'all 0.2s ease',
          }}
          title="Argus Core"
        >
          <Sparkles size={13} />
        </button>

        {/* Subtle Separator */}
        <div
          style={{
            position: 'relative',
            zIndex: 2,
            background: 'rgba(255, 255, 255, 0.12)',
            flexShrink: 0,
            ...(isVertical
              ? { width: 18, height: 1, margin: '2px 0' }
              : { width: 1, height: 18, margin: '0 3px' }),
          }}
        />

        {/* Tab Buttons (Supports direct click + continuous drag scrubbing) */}
        {tabs.map((tab) => {
          const isActive = scrubTab === tab.id;
          return (
            <button
              key={tab.id}
              ref={(el) => { tabRefs.current[tab.id] = el; }}
              onPointerDown={(e) => handlePointerDown(tab.id, e)}
              onClick={() => onTabChange(tab.id)}
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
                touchAction: 'none',
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

        {/* Subtle Separator */}
        <div
          style={{
            position: 'relative',
            zIndex: 2,
            background: 'rgba(255, 255, 255, 0.12)',
            flexShrink: 0,
            ...(isVertical
              ? { width: 18, height: 1, margin: '2px 0' }
              : { width: 1, height: 18, margin: '0 3px' }),
          }}
        />

        {/* Profile Avatar Miniature Button */}
        <button
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
            boxShadow: '0 0 10px var(--accent-glow, rgba(255, 255, 255, 0.15))',
            transition: 'all 0.18s ease',
          }}
          title={`Профиль: ${profile.display_name || 'Пользователь'}`}
        >
          {profile.display_name ? profile.display_name.charAt(0).toUpperCase() : <User size={12} />}
        </button>
      </div>
    </nav>
  );
};
