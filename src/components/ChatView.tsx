import React, { useRef, useEffect, useState } from 'react';
import {
  Send,
  Mic,
  Square,
  ArrowUpRight,
  Volume2,
  VolumeX,
  Sun,
  Lock,
  Camera,
  Radio,
  Clock,
  Zap,
  ShieldAlert,
  PanelLeft
} from 'lucide-react';
import { smartFetch } from '../api';
import { ChatMessage, UserProfile } from '../types';
import { StarburnCore } from './StarburnCore';
import { TelegramIcon, SpotifyIcon } from './Icons';
import { MarkdownRenderer } from './MarkdownRenderer';

interface ChatViewProps {
  messages: ChatMessage[];
  loading: boolean;
  inputText: string;
  onInputChange: (text: string) => void;
  onSendMessage: () => void;
  isListening: boolean;
  onToggleVoice: () => void;
  isSpeaking: boolean;
  profile: UserProfile;
  onQuickAction: (cmd: string) => void;
  streamingMessageId?: string | null;
  onStop?: () => void;
  onFinishStreaming?: () => void;
  isSidebarCollapsed?: boolean;
  onToggleSidebar?: () => void;
  activeChatTitle?: string;
}

export const ChatView: React.FC<ChatViewProps> = ({
  messages,
  loading,
  inputText,
  onInputChange,
  onSendMessage,
  isListening,
  onToggleVoice,
  isSpeaking,
  profile,
  onQuickAction,
  onStop,
  isSidebarCollapsed,
  onToggleSidebar,
  activeChatTitle,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  // Auto-resize textarea dynamically
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      // Clamp between 26px and 140px
      textareaRef.current.style.height = `${Math.min(Math.max(scrollHeight, 26), 140)}px`;
    }
  }, [inputText]);

  const handlePlayMessageAudio = async (msg: ChatMessage) => {
    if (playingAudioId === msg.id) {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
        audioPlayerRef.current = null;
      }
      setPlayingAudioId(null);
      return;
    }

    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current = null;
    }

    try {
      setPlayingAudioId(msg.id);
      let b64 = msg.audio_base64;
      if (!b64) {
        const res = await smartFetch('/api/voice/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: msg.content,
            voice: 'ru-RU-DmitryNeural'
          })
        });
        if (res.ok) {
          const data = await res.json();
          if (data && data.audio_base64) {
            b64 = data.audio_base64;
          }
        }
      }

      if (b64) {
        const cleanB64 = b64.replace(/\s+/g, '');
        const audio = new Audio(`data:audio/mpeg;base64,${cleanB64}`);
        audioPlayerRef.current = audio;
        audio.onended = () => {
          setPlayingAudioId(null);
          audioPlayerRef.current = null;
        };
        audio.onerror = () => {
          setPlayingAudioId(null);
          audioPlayerRef.current = null;
        };
        await audio.play();
      } else {
        setPlayingAudioId(null);
      }
    } catch {
      setPlayingAudioId(null);
    }
  };

  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    scrollToBottom('auto');
  }, [messages.length, loading]);

  const quickPrompts = [
    { label: 'Скриншот экрана', cmd: 'сделай скрин экрана и сохрани на рабочий стол', icon: <Camera size={13} color="var(--accent, #ffffff)" /> },
    { label: 'Звук 50%', cmd: 'поставь звук на 50%', icon: <Volume2 size={13} color="var(--accent, #ffffff)" /> },
    { label: 'Яркость 80%', cmd: 'установи яркость на 80%', icon: <Sun size={13} color="var(--accent, #ffffff)" /> },
    { label: 'Telegram', cmd: 'открой телеграм', icon: <TelegramIcon size={14} /> },
    { label: 'Spotify', cmd: 'включи спотифай', icon: <SpotifyIcon size={14} /> },
    { label: 'Блокировка ПК', cmd: 'заблокируй компьютер', icon: <Lock size={13} color="var(--accent, #ffffff)" /> },
  ];

  const formatMessageTime = (dateStr?: string) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  // Stop button ONLY shows while actively generating or speaking
  const canStop = loading || isSpeaking;

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        position: 'relative',
        overflow: 'hidden',
        userSelect: 'none',
      }}
    >
      {/* ─── Top Bar (Aligned with Sidebar header: height 44px) ─── */}
      <div
        style={{
          height: 44,
          padding: '0 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(255, 255, 255, 0.07)',
          background: 'rgba(8, 8, 12, 0.45)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
          {isSidebarCollapsed && onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="btn-icon"
              style={{
                width: 28,
                height: 28,
                borderRadius: 8,
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                color: '#cbd5e1',
                flexShrink: 0,
              }}
              title="Развернуть диалоги"
            >
              <PanelLeft size={14} />
            </button>
          )}

          <span
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: '#ffffff',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              maxWidth: 360,
            }}
          >
            {activeChatTitle || 'Новый диалог'}
          </span>
        </div>

        {/* Right Info: Argus Neural Online Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: '#4ade80',
              boxShadow: '0 0 6px rgba(74, 222, 128, 0.6)',
            }}
          />
          <span style={{ fontSize: 11, fontWeight: 500, color: '#94a3b8' }}>
            Argus Neural
          </span>
        </div>
      </div>

      {/* ─── SCROLLABLE MESSAGE LIST ─── */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px 28px',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        {messages.length === 0 ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '64vh',
              maxWidth: 580,
              margin: '0 auto',
              textAlign: 'center',
              gap: 16,
            }}
          >
            {/* Realtime Core Visualizer */}
            <StarburnCore isListening={isListening} isSpeaking={isSpeaking} size={150} />

            <div style={{ marginTop: -2 }}>
              <h2
                style={{
                  fontSize: 22,
                  fontWeight: 700,
                  color: '#ffffff',
                  letterSpacing: '-0.02em',
                  marginBottom: 6,
                }}
              >
                {profile.display_name ? `${profile.display_name}, ` : ''}Argus готов к работе
              </h2>
              <p style={{ fontSize: 13, color: '#94a3b8', maxWidth: 440, lineHeight: 1.5 }}>
                Управляйте компьютером голосом и текстом: приложения, задачи, заметки, код или живой диалог.
              </p>
            </div>

            {/* Quick Actions Grid */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 8,
                width: '100%',
                marginTop: 6,
              }}
            >
              {quickPrompts.map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => { if (!loading) onQuickAction(p.cmd); }}
                  disabled={loading}
                  style={{
                    padding: '9px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    opacity: loading ? 0.6 : 1,
                    textAlign: 'left',
                    borderRadius: 9999,
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    background: 'rgba(255, 255, 255, 0.03)',
                    backdropFilter: 'blur(16px)',
                    transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.25)';
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.07)';
                    e.currentTarget.style.transform = 'translateY(-1px) scale(1.02)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                    e.currentTarget.style.transform = 'none';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, overflow: 'hidden' }}>
                    <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center' }}>{p.icon}</div>
                    <span
                      style={{
                        fontSize: 11.5,
                        fontWeight: 600,
                        color: '#f1f5f9',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {p.label}
                    </span>
                  </div>
                  <ArrowUpRight size={11} color="#64748b" style={{ flexShrink: 0 }} />
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === 'user';
            const sentTimeStr = msg.sent_time || formatMessageTime(msg.created_at);
            const respTimeStr = msg.response_time || formatMessageTime(msg.created_at);

            return (
              <div
                key={msg.id}
                className="anim-fade-up"
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 10,
                  maxWidth: 780,
                  width: '100%',
                  alignSelf: isUser ? 'flex-end' : 'flex-start',
                  flexDirection: isUser ? 'row-reverse' : 'row',
                }}
              >
                {/* Avatar Badge */}
                <div
                  style={{
                    width: 30,
                    height: 30,
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    fontSize: 11.5,
                    fontWeight: 700,
                    background: 'rgba(255, 255, 255, 0.08)',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    color: '#ffffff',
                    boxShadow: '0 2px 10px rgba(0, 0, 0, 0.35)',
                  }}
                >
                  {isUser ? (
                    profile.display_name ? profile.display_name.charAt(0).toUpperCase() : 'U'
                  ) : (
                    <span style={{ fontSize: 13, fontWeight: 800 }}>A</span>
                  )}
                </div>

                {/* Message Bubble & Metadata */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 5,
                    maxWidth: '85%',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                    userSelect: 'text',
                  }}
                >
                  <div
                    style={{
                      padding: '12px 18px',
                      borderRadius: isUser ? '20px 20px 6px 20px' : '20px 20px 20px 6px',
                      fontSize: 13.5,
                      lineHeight: 1.6,
                      ...(isUser
                        ? {
                            background: 'rgba(255, 255, 255, 0.1)',
                            color: '#ffffff',
                            border: '1px solid rgba(255, 255, 255, 0.18)',
                            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.15)',
                            backdropFilter: 'blur(20px)',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                          }
                        : {
                            background: 'rgba(12, 12, 16, 0.8)',
                            border: '1px solid rgba(255, 255, 255, 0.08)',
                            backdropFilter: 'blur(28px) saturate(190%)',
                            color: '#f8fafc',
                            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
                          }),
                    }}
                  >
                    {isUser ? (
                      msg.content
                    ) : (
                      <MarkdownRenderer content={msg.content} />
                    )}
                  </div>

                  {/* Wizard / Suggested Options Buttons */}
                  {msg.action_data?.options && Array.isArray(msg.action_data.options) && msg.action_data.options.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                      {msg.action_data.options.map((opt: any, optIdx: number) => {
                        const optLabel = typeof opt === 'string' ? opt : (opt.label || opt.name);
                        const optCmd = typeof opt === 'string' ? opt : (opt.cmd || opt.name || opt.label);
                        return (
                          <button
                            key={optIdx}
                            onClick={() => { if (!loading) onQuickAction(optCmd); }}
                            disabled={loading}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 6,
                              padding: '6px 14px',
                              borderRadius: 9999,
                              background: 'rgba(255, 255, 255, 0.06)',
                              border: '1px solid rgba(255, 255, 255, 0.14)',
                              color: '#ffffff',
                              fontSize: 12,
                              fontWeight: 600,
                              cursor: loading ? 'not-allowed' : 'pointer',
                              transition: 'all 0.18s ease',
                              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.12)';
                              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.3)';
                              e.currentTarget.style.transform = 'translateY(-1px)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)';
                              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.14)';
                              e.currentTarget.style.transform = 'none';
                            }}
                          >
                            <span>{optLabel}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* Bottom Message Metadata: Timestamps & Thinking Duration (NO raw technical badges) */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '0 4px',
                      fontSize: 10.5,
                      color: '#64748b',
                      userSelect: 'none',
                    }}
                  >
                    {isUser ? (
                      /* User message sent time */
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Clock size={10} />
                        <span>{sentTimeStr}</span>
                      </div>
                    ) : (
                      /* Assistant metadata */
                      <>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Clock size={10} />
                          <span>{respTimeStr}</span>
                        </div>

                        {msg.thinking_duration && (
                          <div
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 3,
                              padding: '1px 6px',
                              borderRadius: 9999,
                              background: 'rgba(255, 255, 255, 0.04)',
                              border: '1px solid rgba(255, 255, 255, 0.08)',
                              color: 'var(--accent, #ffffff)',
                              fontSize: 10,
                              fontWeight: 600,
                            }}
                            title="Время размышления нейросети"
                          >
                            <Zap size={9} />
                            <span>{msg.thinking_duration}с</span>
                          </div>
                        )}

                        {/* Audio playback button */}
                        <button
                          onClick={() => handlePlayMessageAudio(msg)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 4,
                            padding: '2px 8px',
                            borderRadius: 6,
                            background: playingAudioId === msg.id ? 'rgba(255, 255, 255, 0.12)' : 'transparent',
                            border: `1px solid ${playingAudioId === msg.id ? 'rgba(255, 255, 255, 0.25)' : 'transparent'}`,
                            color: playingAudioId === msg.id ? '#ffffff' : '#94a3b8',
                            fontSize: 10.5,
                            cursor: 'pointer',
                            transition: 'all 0.15s ease',
                          }}
                          title={playingAudioId === msg.id ? 'Остановить воспроизведение' : 'Озвучить ответ Дмитрием'}
                        >
                          {playingAudioId === msg.id ? <VolumeX size={11} /> : <Volume2 size={11} />}
                          <span>{playingAudioId === msg.id ? 'Остановить' : 'Озвучить'}</span>
                        </button>

                        {/* Only safety confirmation is shown, technical tags like general / delete_note are hidden */}
                        {msg.action_type === 'confirmation_required' && (
                          <div
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 4,
                              padding: '2px 8px',
                              borderRadius: 9999,
                              background: 'rgba(245, 158, 11, 0.12)',
                              border: '1px solid rgba(245, 158, 11, 0.3)',
                              color: '#fbbf24',
                              fontSize: 10.5,
                              fontWeight: 600,
                            }}
                          >
                            <ShieldAlert size={11} />
                            <span>Требуется подтверждение</span>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}

        {/* ─── 3 RUNNING DOTS + Thinking... INDICATOR ─── */}
        {loading && (
          <div
            className="anim-fade-in"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 10,
              padding: '8px 18px',
              borderRadius: 9999,
              background: 'rgba(12, 12, 16, 0.85)',
              backdropFilter: 'blur(28px)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.12)',
              width: 'fit-content',
            }}
          >
            {/* 3 Running / Place-Swapping Dots */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, width: 26, position: 'relative' }}>
              <span
                className="anim-dot-run-1"
                style={{
                  width: 5,
                  height: 5,
                  borderRadius: '50%',
                  background: 'var(--accent, #ffffff)',
                  boxShadow: '0 0 6px var(--accent, #ffffff)',
                }}
              />
              <span
                className="anim-dot-run-2"
                style={{
                  width: 5,
                  height: 5,
                  borderRadius: '50%',
                  background: 'var(--accent, #ffffff)',
                  opacity: 0.8,
                }}
              />
              <span
                className="anim-dot-run-3"
                style={{
                  width: 5,
                  height: 5,
                  borderRadius: '50%',
                  background: 'var(--accent, #ffffff)',
                  opacity: 0.6,
                }}
              />
            </div>
            <span
              style={{
                fontSize: 12.5,
                fontWeight: 600,
                color: '#ffffff',
                letterSpacing: '0.02em',
                fontFamily: "'JetBrains Mono', ui-monospace, monospace",
              }}
            >
              Thinking...
            </span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ─── SLEEK MULTI-LINE LIQUID GLASS INPUT CAPSULE ─── */}
      <div
        style={{
          padding: '8px 24px 18px 24px',
          position: 'relative',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: 720,
            borderRadius: 24,
            background: 'rgba(12, 12, 16, 0.82)',
            backdropFilter: 'blur(32px) saturate(190%)',
            WebkitBackdropFilter: 'blur(32px) saturate(190%)',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '6px 8px 6px 14px',
            border: isListening
              ? '1px solid rgba(239, 68, 68, 0.6)'
              : '1px solid rgba(255, 255, 255, 0.1)',
            boxShadow: isListening
              ? '0 0 24px rgba(239, 68, 68, 0.35), 0 12px 36px rgba(0, 0, 0, 0.6)'
              : '0 12px 40px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.12)',
            transition: 'all 0.22s ease',
          }}
        >
          {/* Microphone Voice Button */}
          <button
            onClick={onToggleVoice}
            style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
              ...(isListening
                ? {
                    background: '#ef4444',
                    color: '#ffffff',
                    boxShadow: '0 0 16px rgba(239, 68, 68, 0.7)',
                    transform: 'scale(1.06)',
                  }
                : {
                    background: 'rgba(255, 255, 255, 0.05)',
                    color: '#94a3b8',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                  }),
            }}
            title={isListening ? 'Остановить голосовой ввод' : 'Голосовой ввод'}
          >
            <Mic size={15} />
          </button>

          {/* Voice Speaking Active Indicator */}
          {isSpeaking && (
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                padding: '3px 8px',
                borderRadius: 9999,
                background: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                color: '#ffffff',
                fontSize: 10,
                fontWeight: 600,
                flexShrink: 0,
              }}
            >
              <Radio size={10} className="anim-dot" />
              <span>Голос...</span>
            </div>
          )}

          {/* Multi-line Textarea Auto-Growing with Crisp Typography */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputText}
            disabled={loading}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!loading && inputText.trim()) {
                  onSendMessage();
                }
              }
            }}
            placeholder={
              loading
                ? 'Thinking...'
                : isListening
                ? 'Слушаю вас... Говорите...'
                : 'Сообщение для Argus... (Shift+Enter для новой строки)'
            }
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: loading ? 'rgba(255, 255, 255, 0.45)' : '#ffffff',
              cursor: loading ? 'not-allowed' : 'text',
              fontSize: 13,
              lineHeight: 1.45,
              padding: '6px 4px',
              resize: 'none',
              maxHeight: 140,
              minHeight: 24,
              userSelect: 'text',
              fontFamily: 'inherit',
              boxSizing: 'border-box',
            }}
          />

          {/* Circular Stop Button (Visible ONLY while generating or speaking) */}
          {canStop && (
            <button
              onClick={onStop}
              style={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                background: '#ef4444',
                color: '#ffffff',
                boxShadow: '0 0 14px rgba(239, 68, 68, 0.5)',
                transition: 'all 0.18s ease',
              }}
              title="Остановить ответ"
            >
              <Square size={12} fill="#ffffff" />
            </button>
          )}

          {/* Sleek Send Button */}
          <button
            onClick={onSendMessage}
            disabled={!inputText.trim() || loading}
            style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              border: 'none',
              cursor: (!inputText.trim() || loading) ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              background: (!inputText.trim() || loading)
                ? 'rgba(255, 255, 255, 0.04)'
                : 'linear-gradient(135deg, var(--accent, #ffffff) 0%, rgba(220, 220, 230, 0.9) 100%)',
              color: (!inputText.trim() || loading) ? '#475569' : '#09090b',
              boxShadow: (!inputText.trim() || loading) ? 'none' : '0 2px 14px var(--accent-glow, rgba(255, 255, 255, 0.3))',
              transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
            }}
            title={loading ? 'Thinking...' : 'Отправить (Enter)'}
          >
            <Send size={13} />
          </button>
        </div>
      </div>
    </div>
  );
};
