import React from 'react';
import { MessageSquare, Boxes, Cpu, Info, Sparkles, User, Settings, Workflow, BookmarkCheck } from 'lucide-react';
import { UserProfile, NavTab } from '../types';
import { NavPosition } from '../utils/theme';

interface NavDockProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  profile: UserProfile;
  onOpenProfile: () => void;
  position?: NavPosition;
}

export const NavDock: React.FC<NavDockProps> = ({
  activeTab,
  onTabChange,
  profile,
  onOpenProfile,
  position = 'top',
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

  return (
    <nav
      className="no-drag anim-fade-in"
      style={{
        zIndex: 40,
        display: 'flex',
        alignItems: 'center',
        userSelect: 'none',
        transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        ...(position === 'top'
          ? {
              position: 'relative',
              justifyContent: 'center',
              padding: 0,
              width: 'auto',
              flexShrink: 0,
            }
          : {
              height: '100%',
              flexDirection: 'column',
              justifyContent: 'center',
              padding: '12px 6px',
              flexShrink: 0,
            }),
      }}
    >
      {/* ─── FLOATING CAPSULE PILL ─── */}
      <div
        style={{
          display: 'flex',
          flexDirection: isVertical ? 'column' : 'row',
          alignItems: 'center',
          gap: 3,
          padding: isVertical ? '8px 4px' : '3px 6px',
          height: isVertical ? 'auto' : 32,
          borderRadius: 9999,
          background: 'rgba(12, 12, 16, 0.82)',
          backdropFilter: 'blur(30px) saturate(190%)',
          WebkitBackdropFilter: 'blur(30px) saturate(190%)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 12px 36px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.15), 0 0 20px var(--accent-glow, rgba(255, 255, 255, 0.08))',
          transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      >
        {/* Sparkle Core Mini Icon */}
        <button
          onClick={() => onTabChange('chat')}
          style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.06)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
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
            background: 'rgba(255, 255, 255, 0.1)',
            ...(isVertical
              ? { width: 18, height: 1, margin: '2px 0' }
              : { width: 1, height: 18, margin: '0 3px' }),
          }}
        />

        {/* Tab Buttons (Miniature, no number badges) */}
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              style={{
                position: 'relative',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: isVertical ? '7px 8px' : '5px 11px',
                borderRadius: 9999,
                fontSize: 11.5,
                fontWeight: isActive ? 600 : 500,
                letterSpacing: '0.01em',
                cursor: 'pointer',
                border: isActive
                  ? '1px solid rgba(255, 255, 255, 0.22)'
                  : '1px solid transparent',
                background: isActive
                  ? 'linear-gradient(135deg, rgba(255, 255, 255, 0.12) 0%, rgba(255, 255, 255, 0.05) 100%)'
                  : 'transparent',
                color: isActive ? '#ffffff' : '#94a3b8',
                boxShadow: isActive
                  ? '0 2px 10px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.2)'
                  : 'none',
                transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
                whiteSpace: 'nowrap',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.color = '#ffffff';
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.color = '#94a3b8';
                  e.currentTarget.style.background = 'transparent';
                }
              }}
              title={tab.label}
            >
              <span style={{ color: isActive ? 'var(--accent, #ffffff)' : 'inherit', display: 'flex' }}>
                {tab.icon}
              </span>
              {!isVertical && <span>{tab.label}</span>}
            </button>
          );
        })}

        {/* Subtle Separator */}
        <div
          style={{
            background: 'rgba(255, 255, 255, 0.1)',
            ...(isVertical
              ? { width: 18, height: 1, margin: '2px 0' }
              : { width: 1, height: 18, margin: '0 3px' }),
          }}
        />

        {/* Profile Avatar Miniature Button */}
        <button
          onClick={onOpenProfile}
          style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0.04) 100%)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
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
