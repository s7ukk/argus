import React from 'react';
import { MessageSquare, Boxes, Cpu, Info, Sparkles, User, Settings, Workflow } from 'lucide-react';
import { UserProfile, NavTab } from '../types';

interface NavDockProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  profile: UserProfile;
  onOpenProfile: () => void;
}

export const NavDock: React.FC<NavDockProps> = ({
  activeTab,
  onTabChange,
  profile,
  onOpenProfile,
}) => {
  const tabs: { id: NavTab; number: number; label: string; icon: React.ReactNode }[] = [
    { id: 'chat', number: 1, label: 'Чат', icon: <MessageSquare size={17} /> },
    { id: 'scenarios', number: 2, label: 'Сценарии', icon: <Workflow size={17} /> },
    { id: 'plugins', number: 3, label: 'Плагины', icon: <Boxes size={17} /> },
    { id: 'system', number: 4, label: 'Система', icon: <Cpu size={17} /> },
    { id: 'about', number: 5, label: 'О системе', icon: <Info size={17} /> },
    { id: 'settings', number: 6, label: 'Настройки', icon: <Settings size={17} /> },
  ];

  return (
    <div
      style={{
        width: 68,
        height: '100%',
        background: 'rgba(8, 6, 16, 0.95)',
        backdropFilter: 'blur(20px)',
        borderRight: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 0',
        zIndex: 30,
        userSelect: 'none',
        flexShrink: 0,
      }}
    >
      {/* Top Logo / Core Icon */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
        <button
          onClick={() => onTabChange('chat')}
          style={{
            width: 44,
            height: 44,
            borderRadius: 14,
            background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.25) 0%, rgba(56, 189, 248, 0.2) 100%)',
            border: '1px solid rgba(168, 85, 247, 0.4)',
            boxShadow: '0 0 20px rgba(168, 85, 247, 0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
          }}
          title="Argus Neural Core"
        >
          <Sparkles size={20} color="#c084fc" />
        </button>

        {/* Vertical Divider */}
        <div style={{ width: 32, height: 1, background: 'rgba(255, 255, 255, 0.08)' }} />

        {/* Numbered Navigation Tabs matching user's sketch (1, 2, 3, 4) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                style={{
                  position: 'relative',
                  width: 48,
                  height: 48,
                  borderRadius: 14,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 2,
                  cursor: 'pointer',
                  border: isActive
                    ? '1px solid rgba(168, 85, 247, 0.6)'
                    : '1px solid rgba(255, 255, 255, 0.06)',
                  background: isActive
                    ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.3) 0%, rgba(124, 58, 237, 0.25) 100%)'
                    : 'rgba(255, 255, 255, 0.03)',
                  boxShadow: isActive ? '0 0 16px rgba(168, 85, 247, 0.4), inset 0 0 12px rgba(168, 85, 247, 0.2)' : 'none',
                  color: isActive ? '#ffffff' : '#64748b',
                  transition: 'all 0.18s ease',
                }}
                title={`${tab.number}. ${tab.label}`}
              >
                {/* Active Indicator Bar */}
                {isActive && (
                  <div
                    style={{
                      position: 'absolute',
                      left: -8,
                      width: 3.5,
                      height: 22,
                      borderRadius: '0 4px 4px 0',
                      background: 'linear-gradient(180deg, #c084fc 0%, #38bdf8 100%)',
                      boxShadow: '0 0 8px #a855f7',
                    }}
                  />
                )}

                {/* Number Badge at Top Right */}
                <span
                  style={{
                    position: 'absolute',
                    top: 3,
                    right: 5,
                    fontSize: 9,
                    fontWeight: 800,
                    fontFamily: 'ui-monospace, monospace',
                    color: isActive ? '#c084fc' : '#475569',
                  }}
                >
                  {tab.number}
                </span>

                <div style={{ marginTop: 2 }}>{tab.icon}</div>
                <span
                  style={{
                    fontSize: 9.5,
                    fontWeight: 700,
                    letterSpacing: '0.02em',
                    color: isActive ? '#f1f5f9' : '#64748b',
                    lineHeight: 1,
                  }}
                >
                  {tab.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Bottom Profile Shortcut */}
      <button
        onClick={onOpenProfile}
        style={{
          width: 44,
          height: 44,
          borderRadius: 14,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          background: 'rgba(255, 255, 255, 0.04)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          color: '#94a3b8',
          transition: 'all 0.2s ease',
        }}
        title={`Профиль: ${profile.display_name}`}
      >
        <User size={18} />
      </button>
    </div>
  );
};
