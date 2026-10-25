import React, { useState } from 'react';
import { Plus, MessageSquare, Trash2, ChevronLeft, User, Edit2, Check, X } from 'lucide-react';
import { ChatSession, UserProfile } from '../types';

interface SidebarProps {
  chats: ChatSession[];
  activeChatId: string | null;
  onSelectChat: (id: string) => void;
  onCreateChat: () => void;
  onDeleteChat: (id: string, e: React.MouseEvent) => void;
  onRenameChat?: (id: string, newTitle: string) => void;
  profile: UserProfile;
  onOpenProfile: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  chats,
  activeChatId,
  onSelectChat,
  onCreateChat,
  onDeleteChat,
  onRenameChat,
  profile,
  onOpenProfile,
  isCollapsed,
  onToggleCollapse,
}) => {
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [hoveredChatId, setHoveredChatId] = useState<string | null>(null);

  const startEditing = (chat: ChatSession, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingChatId(chat.id);
    setEditTitle(chat.title);
  };

  const handleSaveRename = (chatId: string, e?: React.MouseEvent | React.KeyboardEvent) => {
    if (e) e.stopPropagation();
    if (editTitle.trim() && onRenameChat) {
      onRenameChat(chatId, editTitle.trim());
    }
    setEditingChatId(null);
  };

  const handleCancelRename = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setEditingChatId(null);
  };

  return (
    <aside
      className="glass"
      style={{
        width: isCollapsed ? 0 : 250,
        minWidth: isCollapsed ? 0 : 250,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        transition: 'width 0.26s cubic-bezier(0.16, 1, 0.3, 1), min-width 0.26s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.22s ease',
        opacity: isCollapsed ? 0 : 1,
        pointerEvents: isCollapsed ? 'none' : 'auto',
        overflow: 'hidden',
        borderRight: isCollapsed ? 'none' : '1px solid rgba(255, 255, 255, 0.08)',
        background: 'rgba(10, 10, 14, 0.78)',
        backdropFilter: 'blur(30px) saturate(190%)',
        WebkitBackdropFilter: 'blur(30px) saturate(190%)',
        userSelect: 'none',
        position: 'relative',
        zIndex: 20,
      }}
    >
      {/* ─── Top Header & New Chat Button ─── */}
      <div style={{ padding: '14px 14px 10px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span
            style={{
              fontSize: 11,
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: '#94a3b8',
              paddingLeft: 4,
            }}
          >
            Диалоги
          </span>
          <button
            onClick={onToggleCollapse}
            className="btn-icon"
            style={{ width: 26, height: 26 }}
            title="Свернуть список чатов"
          >
            <ChevronLeft size={15} />
          </button>
        </div>

        {/* New Chat Button */}
        <button
          onClick={onCreateChat}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 7,
            padding: '8px 14px',
            borderRadius: 9999,
            background: 'rgba(255, 255, 255, 0.06)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            color: '#ffffff',
            fontSize: 12.5,
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
            boxShadow: '0 2px 10px rgba(0, 0, 0, 0.3)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.12)';
            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.25)';
            e.currentTarget.style.transform = 'translateY(-1px)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)';
            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.12)';
            e.currentTarget.style.transform = 'none';
          }}
          title="Создать новый диалог"
        >
          <Plus size={14} />
          <span>Новый чат</span>
        </button>
      </div>

      {/* ─── Chat History List ─── */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '4px 8px',
          display: 'flex',
          flexDirection: 'column',
          gap: 4,
        }}
      >
        {chats.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              padding: '36px 12px',
              color: '#64748b',
              fontSize: 12,
            }}
          >
            История диалогов пуста
          </div>
        ) : (
          chats.map((chat) => {
            const isActive = chat.id === activeChatId;
            const isEditing = editingChatId === chat.id;

            return (
              <div
                key={chat.id}
                onClick={() => !isEditing && onSelectChat(chat.id)}
                onMouseEnter={() => setHoveredChatId(chat.id)}
                onMouseLeave={() => setHoveredChatId(null)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '7px 10px',
                  borderRadius: 12,
                  cursor: isEditing ? 'default' : 'pointer',
                  background: isActive
                    ? 'rgba(255, 255, 255, 0.1)'
                    : hoveredChatId === chat.id
                    ? 'rgba(255, 255, 255, 0.04)'
                    : 'transparent',
                  border: isActive
                    ? '1px solid rgba(255, 255, 255, 0.18)'
                    : '1px solid transparent',
                  boxShadow: isActive ? '0 2px 10px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.15)' : 'none',
                  color: isActive ? '#ffffff' : '#94a3b8',
                  transition: 'all 0.15s ease',
                  overflow: 'hidden',
                }}
              >
                {isEditing ? (
                  <div
                    style={{ display: 'flex', alignItems: 'center', gap: 5, width: '100%' }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveRename(chat.id, e);
                        if (e.key === 'Escape') handleCancelRename(e);
                      }}
                      autoFocus
                      style={{
                        flex: 1,
                        background: 'rgba(0, 0, 0, 0.4)',
                        border: '1px solid rgba(255, 255, 255, 0.25)',
                        borderRadius: 6,
                        padding: '3px 6px',
                        color: '#ffffff',
                        fontSize: 12,
                        outline: 'none',
                      }}
                    />
                    <button
                      onClick={(e) => handleSaveRename(chat.id, e)}
                      style={{ background: 'transparent', border: 'none', color: '#4ade80', cursor: 'pointer', padding: 2 }}
                    >
                      <Check size={13} />
                    </button>
                    <button
                      onClick={handleCancelRename}
                      style={{ background: 'transparent', border: 'none', color: '#f87171', cursor: 'pointer', padding: 2 }}
                    >
                      <X size={13} />
                    </button>
                  </div>
                ) : (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden', flex: 1 }}>
                      <MessageSquare size={13} style={{ flexShrink: 0, opacity: isActive ? 1 : 0.6 }} />
                      <span
                        style={{
                          fontSize: 12,
                          fontWeight: isActive ? 600 : 500,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {chat.title}
                      </span>
                    </div>

                    {/* Actions on hover */}
                    {(hoveredChatId === chat.id || isActive) && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 3, flexShrink: 0 }}>
                        <button
                          onClick={(e) => startEditing(chat, e)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#94a3b8',
                            cursor: 'pointer',
                            padding: 2,
                            display: 'flex',
                          }}
                          title="Переименовать"
                        >
                          <Edit2 size={12} />
                        </button>
                        <button
                          onClick={(e) => onDeleteChat(chat.id, e)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#94a3b8',
                            cursor: 'pointer',
                            padding: 2,
                            display: 'flex',
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.color = '#f87171')}
                          onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
                          title="Удалить диалог"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* ─── Bottom Profile Button ─── */}
      <div
        style={{
          padding: '10px 12px',
          borderTop: '1px solid rgba(255, 255, 255, 0.07)',
        }}
      >
        <button
          onClick={onOpenProfile}
          style={{
            width: '100%',
            padding: '8px 10px',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            cursor: 'pointer',
            textAlign: 'left',
            borderRadius: 14,
            background: 'rgba(255, 255, 255, 0.035)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            transition: 'all 0.18s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.035)';
            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
          }}
          title="Открыть профиль"
        >
          {/* User Avatar */}
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: 'rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              fontWeight: 700,
              fontSize: 12,
              flexShrink: 0,
            }}
          >
            {profile.display_name ? profile.display_name.charAt(0).toUpperCase() : <User size={13} />}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <span
              style={{
                fontSize: 12.5,
                fontWeight: 600,
                color: '#ffffff',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {profile.display_name || 'Профиль'}
            </span>
            <span style={{ fontSize: 10.5, color: '#64748b' }}>
              {profile.tier} • {profile.days_left} дн.
            </span>
          </div>
        </button>
      </div>
    </aside>
  );
};
