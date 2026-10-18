import React, { useState } from 'react';
import { Plus, MessageSquare, Trash2, ChevronLeft, ChevronRight, User, Edit2, Check, X } from 'lucide-react';
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
        width: isCollapsed ? 68 : 260,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        transition: 'width 0.22s cubic-bezier(0.4, 0, 0.2, 1)',
        borderRight: '1px solid rgba(255, 255, 255, 0.07)',
        userSelect: 'none',
        position: 'relative',
        zIndex: 20,
      }}
    >
      {/* Top Header & New Chat Button */}
      <div style={{ padding: '16px 14px 12px 14px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: isCollapsed ? 'center' : 'space-between' }}>
          {!isCollapsed && (
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                color: '#64748b',
                paddingLeft: 4,
              }}
            >
              Чаты
            </span>
          )}
          <button
            onClick={onToggleCollapse}
            className="btn-icon"
            style={{ width: 28, height: 28 }}
            title={isCollapsed ? 'Развернуть меню' : 'Свернуть меню'}
          >
            {isCollapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
          </button>
        </div>

        {/* New Chat Button */}
        <button
          onClick={onCreateChat}
          className="btn-primary"
          style={{
            width: '100%',
            justifyContent: 'center',
            padding: isCollapsed ? '10px 0' : '10px 14px',
            fontSize: 13,
            borderRadius: 11,
          }}
          title="Новый диалог"
        >
          <Plus size={16} />
          {!isCollapsed && <span>Новый чат</span>}
        </button>
      </div>

      {/* Chat History List */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '4px 10px',
          display: 'flex',
          flexDirection: 'column',
          gap: 5,
        }}
      >
        {chats.length === 0 ? (
          !isCollapsed && (
            <div
              style={{
                textAlign: 'center',
                padding: '40px 12px',
                color: '#475569',
                fontSize: 12,
              }}
            >
              История диалогов пуста
            </div>
          )
        ) : (
          chats.map((chat) => {
            const isActive = chat.id === activeChatId;
            const isEditing = editingChatId === chat.id;

            return (
              <div
                key={chat.id}
                onClick={() => !isEditing && onSelectChat(chat.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: isCollapsed ? '10px 0' : '8px 10px',
                  borderRadius: 10,
                  cursor: isEditing ? 'default' : 'pointer',
                  background: isActive
                    ? 'linear-gradient(135deg, rgba(139, 92, 246, 0.22) 0%, rgba(219, 39, 119, 0.12) 100%)'
                    : 'transparent',
                  border: isActive
                    ? '1px solid rgba(168, 85, 247, 0.45)'
                    : '1px solid transparent',
                  boxShadow: isActive ? '0 2px 12px rgba(139, 92, 246, 0.2)' : 'none',
                  color: isActive ? '#ffffff' : '#94a3b8',
                  transition: 'all 0.18s ease',
                  position: 'relative',
                }}
                onMouseEnter={(e) => {
                  if (!isActive && !isEditing) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                    e.currentTarget.style.color = '#ffffff';
                  }
                  const actionBtns = e.currentTarget.querySelectorAll('.chat-action-btn');
                  actionBtns.forEach((btn) => ((btn as HTMLElement).style.opacity = '1'));
                }}
                onMouseLeave={(e) => {
                  if (!isActive && !isEditing) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = '#94a3b8';
                  }
                  const actionBtns = e.currentTarget.querySelectorAll('.chat-action-btn');
                  actionBtns.forEach((btn) => ((btn as HTMLElement).style.opacity = '0'));
                }}
                title={chat.title}
              >
                {/* Chat Title / Editing Field */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    overflow: 'hidden',
                    flex: 1,
                    justifyContent: isCollapsed ? 'center' : 'flex-start',
                  }}
                >
                  <MessageSquare
                    size={14}
                    style={{
                      flexShrink: 0,
                      color: isActive ? '#d8b4fe' : '#64748b',
                    }}
                  />
                  {!isCollapsed && (
                    isEditing ? (
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveRename(chat.id, e);
                          if (e.key === 'Escape') handleCancelRename();
                        }}
                        autoFocus
                        onClick={(e) => e.stopPropagation()}
                        style={{
                          background: 'rgba(0, 0, 0, 0.5)',
                          border: '1px solid #a855f7',
                          borderRadius: 6,
                          color: '#ffffff',
                          fontSize: 12,
                          padding: '2px 6px',
                          width: '100%',
                          outline: 'none',
                        }}
                      />
                    ) : (
                      <span
                        onDoubleClick={(e) => startEditing(chat, e)}
                        style={{
                          fontSize: 12.5,
                          fontWeight: isActive ? 600 : 400,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {chat.title}
                      </span>
                    )
                  )}
                </div>

                {/* Action Buttons (Rename & Delete) */}
                {!isCollapsed && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    {isEditing ? (
                      <>
                        <button
                          onClick={(e) => handleSaveRename(chat.id, e)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#34d399',
                            padding: 4,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                          }}
                          title="Сохранить"
                        >
                          <Check size={13} />
                        </button>
                        <button
                          onClick={handleCancelRename}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#f87171',
                            padding: 4,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                          }}
                          title="Отмена"
                        >
                          <X size={13} />
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          className="chat-action-btn"
                          onClick={(e) => startEditing(chat, e)}
                          style={{
                            opacity: 0,
                            background: 'transparent',
                            border: 'none',
                            color: '#64748b',
                            padding: 4,
                            cursor: 'pointer',
                            borderRadius: 6,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            transition: 'opacity 0.15s, color 0.15s',
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.color = '#c084fc';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.color = '#64748b';
                          }}
                          title="Переименовать диалог"
                        >
                          <Edit2 size={12} />
                        </button>
                        <button
                          className="chat-action-btn"
                          onClick={(e) => onDeleteChat(chat.id, e)}
                          style={{
                            opacity: 0,
                            background: 'transparent',
                            border: 'none',
                            color: '#64748b',
                            padding: 4,
                            cursor: 'pointer',
                            borderRadius: 6,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            transition: 'opacity 0.15s, color 0.15s',
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.color = '#f87171';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.color = '#64748b';
                          }}
                          title="Удалить диалог"
                        >
                          <Trash2 size={12} />
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Bottom Profile Button */}
      <div
        style={{
          padding: '12px 14px',
          borderTop: '1px solid rgba(255, 255, 255, 0.07)',
        }}
      >
        <button
          onClick={onOpenProfile}
          className="glass-card"
          style={{
            width: '100%',
            padding: isCollapsed ? '10px 0' : '10px 14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: isCollapsed ? 'center' : 'flex-start',
            gap: 12,
            cursor: 'pointer',
            textAlign: 'left',
            borderRadius: 12,
          }}
          title="Открыть Profile"
        >
          {/* User Avatar */}
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 9,
              background: 'linear-gradient(135deg, #8b5cf6 0%, #d946ef 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              fontWeight: 800,
              fontSize: 13,
              flexShrink: 0,
              boxShadow: '0 2px 8px rgba(139, 92, 246, 0.4)',
            }}
          >
            <User size={16} />
          </div>

          {!isCollapsed && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <span
                style={{
                  fontSize: 13,
                  fontWeight: 700,
                  color: '#f8fafc',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                Profile
              </span>
              <span style={{ fontSize: 11, color: '#94a3b8' }}>
                {profile.display_name}
              </span>
            </div>
          )}
        </button>
      </div>
    </aside>
  );
};
