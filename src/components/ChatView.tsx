import React, { useRef, useEffect, useState } from 'react';
import { Send, Mic, Square, CheckCircle2, ArrowUpRight, Volume2, VolumeX, Sun, Lock, Camera, Radio } from 'lucide-react';
import { smartFetch } from '../api';
import { ChatMessage, UserProfile } from '../types';
import { StarburnCore } from './StarburnCore';
import { StarburnLogo, TelegramIcon, SpotifyIcon } from './Icons';

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
}

// ─── SMOOTH TYPEWRITER TEXT COMPONENT ─────────────────────────────
const TypewriterText: React.FC<{
  text: string;
  isStreaming?: boolean;
  onFinish?: () => void;
}> = ({ text, isStreaming = false, onFinish }) => {
  const [displayedLength, setDisplayedLength] = useState(isStreaming ? 0 : text.length);

  useEffect(() => {
    if (!isStreaming) {
      setDisplayedLength(text.length);
      return;
    }

    if (displayedLength >= text.length) {
      onFinish?.();
      return;
    }

    // Dynamic typing speed: longer text steps by 2-3 characters to keep it responsive (~1.5s total max)
    const step = text.length > 300 ? 3 : text.length > 80 ? 2 : 1;
    const timer = setTimeout(() => {
      setDisplayedLength((prev) => Math.min(text.length, prev + step));
    }, 18);

    return () => clearTimeout(timer);
  }, [displayedLength, text, isStreaming, onFinish]);

  const visibleText = isStreaming ? text.slice(0, displayedLength) : text;
  const isTyping = isStreaming && displayedLength < text.length;

  return (
    <span>
      {visibleText}
      {isTyping && (
        <span
          className="anim-dot"
          style={{
            display: 'inline-block',
            width: 7,
            height: 14,
            marginLeft: 3,
            verticalAlign: '-2px',
            background: 'linear-gradient(180deg, #c084fc 0%, #ec4899 100%)',
            borderRadius: 3,
            boxShadow: '0 0 10px rgba(192, 132, 252, 0.8)',
          }}
        />
      )}
    </span>
  );
};

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
  streamingMessageId,
  onStop,
  onFinishStreaming,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

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

  const scrollToBottom = (behavior: ScrollBehavior = 'auto') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    scrollToBottom('auto');
  }, [messages.length, loading]);

  useEffect(() => {
    if (streamingMessageId) {
      scrollToBottom('smooth');
    }
  }, [streamingMessageId]);

  const quickPrompts = [
    { label: 'Скриншот экрана', cmd: 'сделай скрин экрана и сохрани на рабочий стол', icon: <Camera size={14} color="#38bdf8" /> },
    { label: 'Звук 50%', cmd: 'поставь звук на 50%', icon: <Volume2 size={14} color="#c084fc" /> },
    { label: 'Яркость 80%', cmd: 'установи яркость на 80%', icon: <Sun size={14} color="#fbbf24" /> },
    { label: 'Telegram', cmd: 'открой телеграм', icon: <TelegramIcon size={15} /> },
    { label: 'Spotify', cmd: 'включи спотифай', icon: <SpotifyIcon size={15} /> },
    { label: 'Блокировка ПК', cmd: 'заблокируй компьютер', icon: <Lock size={14} color="#f87171" /> },
  ];

  const canStop = loading || isSpeaking || Boolean(streamingMessageId);

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
      {/* Scrollable Message List */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px 32px',
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
              minHeight: '66vh',
              maxWidth: 580,
              margin: '0 auto',
              textAlign: 'center',
              gap: 16,
            }}
          >
            {/* Celestial Core Visualizer */}
            <StarburnCore isListening={isListening} isSpeaking={isSpeaking} size={170} />

            <div style={{ marginTop: -4 }}>
              <h2
                style={{
                  fontSize: 23,
                  fontWeight: 800,
                  color: '#ffffff',
                  letterSpacing: '-0.02em',
                  marginBottom: 6,
                  background: 'linear-gradient(135deg, #ffffff 40%, #e9d5ff 75%, #f472b6 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                {profile.display_name ? `${profile.display_name}, ` : ''}Argus готов к работе
              </h2>
              <p style={{ fontSize: 13, color: '#94a3b8', maxWidth: 440, lineHeight: 1.5 }}>
                Управляйте компьютером голосом и текстом: звук, экран, приложения, сайты или живой диалог.
              </p>
            </div>

            {/* Quick Actions Grid */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 8,
                width: '100%',
                marginTop: 4,
              }}
            >
              {quickPrompts.map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => { if (!loading) onQuickAction(p.cmd); }}
                  disabled={loading}
                  className="glass-card"
                  style={{
                    padding: '10px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    opacity: loading ? 0.6 : 1,
                    textAlign: 'left',
                    borderRadius: 14,
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    background: 'rgba(255, 255, 255, 0.03)',
                    transition: 'all 0.18s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                    <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center' }}>{p.icon}</div>
                    <span
                      style={{
                        fontSize: 12,
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
                  <ArrowUpRight size={12} color="#64748b" style={{ flexShrink: 0 }} />
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === 'user';
            const isStreamingThis = !isUser && msg.id === streamingMessageId;

            return (
              <div
                key={msg.id}
                className="anim-fade-up"
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 10,
                  maxWidth: 720,
                  width: '100%',
                  alignSelf: isUser ? 'flex-end' : 'flex-start',
                  flexDirection: isUser ? 'row-reverse' : 'row',
                }}
              >
                {/* Avatar Badge */}
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    fontSize: 12,
                    fontWeight: 700,
                    background: isUser
                      ? 'linear-gradient(135deg, #8b5cf6 0%, #d946ef 100%)'
                      : 'linear-gradient(135deg, rgba(139, 92, 246, 0.3) 0%, rgba(217, 70, 239, 0.15) 100%)',
                    border: isUser
                      ? '1.5px solid rgba(255, 255, 255, 0.3)'
                      : '1.5px solid rgba(168, 85, 247, 0.45)',
                    color: '#ffffff',
                    boxShadow: isUser ? '0 4px 14px rgba(139, 92, 246, 0.35)' : '0 2px 10px rgba(0,0,0,0.3)',
                  }}
                >
                  {isUser ? (
                    profile.display_name ? profile.display_name.charAt(0).toUpperCase() : 'U'
                  ) : (
                    <StarburnLogo size={18} />
                  )}
                </div>

                {/* Message Capsule */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 6,
                    maxWidth: '82%',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                    userSelect: 'text',
                  }}
                >
                  <div
                    style={{
                      padding: '11px 17px',
                      borderRadius: isUser ? '20px 20px 5px 20px' : '20px 20px 20px 5px',
                      fontSize: 13.5,
                      lineHeight: 1.58,
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      ...(isUser
                        ? {
                            background: 'linear-gradient(135deg, #7c3aed 0%, #9333ea 50%, #c026d3 100%)',
                            color: '#ffffff',
                            boxShadow: '0 4px 18px rgba(124, 58, 237, 0.32)',
                            border: '1px solid rgba(255, 255, 255, 0.18)',
                          }
                        : {
                            background: 'rgba(22, 17, 40, 0.72)',
                            border: '1px solid rgba(168, 85, 247, 0.22)',
                            backdropFilter: 'blur(20px)',
                            color: '#f8fafc',
                            boxShadow: '0 6px 24px rgba(0, 0, 0, 0.35)',
                          }),
                    }}
                  >
                    {isUser ? (
                      msg.content
                    ) : (
                      <TypewriterText
                        text={msg.content}
                        isStreaming={isStreamingThis}
                        onFinish={onFinishStreaming}
                      />
                    )}
                  </div>

                  {/* Interactive Wizard & Options Buttons */}
                  {msg.action_data?.options && Array.isArray(msg.action_data.options) && msg.action_data.options.length > 0 && (
                    <div
                      style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: 8,
                        marginTop: 4,
                      }}
                    >
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
                              padding: '8px 16px',
                              borderRadius: 12,
                              background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.28) 0%, rgba(217, 70, 239, 0.22) 100%)',
                              border: '1px solid rgba(168, 85, 247, 0.5)',
                              color: '#ffffff',
                              fontSize: 13,
                              fontWeight: 600,
                              cursor: loading ? 'not-allowed' : 'pointer',
                              opacity: loading ? 0.6 : 1,
                              transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                              boxShadow: '0 4px 14px rgba(0, 0, 0, 0.3)',
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background = 'linear-gradient(135deg, rgba(139, 92, 246, 0.5) 0%, rgba(217, 70, 239, 0.4) 100%)';
                              e.currentTarget.style.borderColor = 'rgba(192, 132, 252, 0.85)';
                              e.currentTarget.style.transform = 'translateY(-2px)';
                              e.currentTarget.style.boxShadow = '0 6px 20px rgba(168, 85, 247, 0.4)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = 'linear-gradient(135deg, rgba(139, 92, 246, 0.28) 0%, rgba(217, 70, 239, 0.22) 100%)';
                              e.currentTarget.style.borderColor = 'rgba(168, 85, 247, 0.5)';
                              e.currentTarget.style.transform = 'translateY(0)';
                              e.currentTarget.style.boxShadow = '0 4px 14px rgba(0, 0, 0, 0.3)';
                            }}
                          >
                            <span>{optLabel}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* Assistant Actions Bar: Listen / Replay Voice + System Action Badge */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4, flexWrap: 'wrap' }}>
                    {msg.role === 'assistant' && (
                      <button
                        onClick={() => handlePlayMessageAudio(msg)}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 5,
                          padding: '3px 9px',
                          borderRadius: 8,
                          background: playingAudioId === msg.id ? 'rgba(168, 85, 247, 0.25)' : 'rgba(255, 255, 255, 0.04)',
                          border: `1px solid ${playingAudioId === msg.id ? 'rgba(168, 85, 247, 0.5)' : 'rgba(255, 255, 255, 0.08)'}`,
                          color: playingAudioId === msg.id ? '#c084fc' : '#94a3b8',
                          fontSize: 11,
                          fontWeight: 500,
                          cursor: 'pointer',
                          transition: 'all 0.15s ease'
                        }}
                        title={playingAudioId === msg.id ? 'Остановить воспроизведение' : 'Озвучить ответ голосом Дмитрия'}
                      >
                        {playingAudioId === msg.id ? <VolumeX size={12} /> : <Volume2 size={12} />}
                        <span>{playingAudioId === msg.id ? 'Остановить' : 'Озвучить'}</span>
                      </button>
                    )}

                    {msg.action_type && (
                      <div
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '3px 10px',
                          borderRadius: 9999,
                          background: 'rgba(16, 185, 129, 0.12)',
                          border: '1px solid rgba(16, 185, 129, 0.3)',
                          color: '#34d399',
                          fontSize: 10.5,
                          fontFamily: 'ui-monospace, monospace',
                          fontWeight: 600,
                          boxShadow: '0 0 12px rgba(16, 185, 129, 0.15)',
                        }}
                      >
                        <CheckCircle2 size={12} />
                        <span>{msg.action_type}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}

        {/* Loading Indicator */}
        {loading && (
          <div
            className="anim-fade-in"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              maxWidth: 360,
            }}
          >
            <div
              style={{
                width: 30,
                height: 30,
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'rgba(124, 58, 237, 0.25)',
                border: '1px solid rgba(168, 85, 247, 0.4)',
              }}
            >
              <StarburnLogo size={16} />
            </div>
            <div
              style={{
                padding: '8px 14px',
                borderRadius: 9999,
                background: 'rgba(22, 17, 40, 0.72)',
                border: '1px solid rgba(168, 85, 247, 0.2)',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 12,
                color: '#d8b4fe',
              }}
            >
              <span
                className="anim-dot"
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: '#c084fc',
                }}
              />
              <span>Argus думает и выполняет...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ─── ULTRA-THIN SLEEK FLOATING PILL INPUT BAR ─────────────────── */}
      <div
        style={{
          padding: '10px 24px 18px 24px',
          position: 'relative',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: 740,
            minHeight: 46,
            padding: '4px 6px 4px 14px',
            borderRadius: 9999, // Perfect smooth pill
            background: 'rgba(14, 11, 28, 0.82)',
            backdropFilter: 'blur(24px)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            border: isListening
              ? '1px solid rgba(244, 63, 94, 0.6)'
              : '1px solid rgba(168, 85, 247, 0.28)',
            boxShadow: isListening
              ? '0 0 28px rgba(244, 63, 94, 0.35), 0 8px 30px rgba(0, 0, 0, 0.5)'
              : '0 8px 32px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05) inset',
            transition: 'all 0.22s ease',
          }}
        >
          {/* Microphone Voice Button */}
          <button
            onClick={onToggleVoice}
            style={{
              width: 34,
              height: 34,
              borderRadius: '50%',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
              ...(isListening
                ? {
                    background: 'linear-gradient(135deg, #e11d48 0%, #f43f5e 100%)',
                    color: '#ffffff',
                    boxShadow: '0 0 18px rgba(244, 63, 94, 0.7)',
                    transform: 'scale(1.08)',
                  }
                : {
                    background: 'rgba(255, 255, 255, 0.06)',
                    color: '#c084fc',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                  }),
            }}
            title={isListening ? 'Остановить голосовой ввод' : 'Голосовой ввод'}
          >
            <Mic size={16} />
          </button>

          {/* Voice Speaking Active Indicator */}
          {isSpeaking && (
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                padding: '3px 9px',
                borderRadius: 9999,
                background: 'rgba(251, 191, 36, 0.15)',
                border: '1px solid rgba(251, 191, 36, 0.35)',
                color: '#fde047',
                fontSize: 10.5,
                fontWeight: 600,
                flexShrink: 0,
              }}
            >
              <Radio size={11} className="anim-dot" />
              <span>Озвучивание...</span>
            </div>
          )}

          {/* Clean Compact Input Field */}
          <input
            type="text"
            value={inputText}
            disabled={loading}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!loading) {
                  onSendMessage();
                }
              }
            }}
            placeholder={
              loading
                ? 'Идёт обработка запроса, сэр... Пожалуйста, подождите...'
                : isListening
                ? 'Слушаю ваш голос... Произнесите команду...'
                : 'Спросите Argus или отдайте команду (звук, скриншот, яркость, программы)...'
            }
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: loading ? 'rgba(255, 255, 255, 0.45)' : '#ffffff',
              cursor: loading ? 'not-allowed' : 'text',
              fontSize: 13.5,
              padding: '6px 4px',
              userSelect: 'text',
            }}
          />

          {/* Circular Stop Button (Visible while generating or speaking) */}
          {canStop && (
            <button
              onClick={onStop}
              style={{
                width: 34,
                height: 34,
                borderRadius: '50%',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                color: '#ffffff',
                boxShadow: '0 0 16px rgba(239, 68, 68, 0.55)',
                transition: 'all 0.18s ease',
              }}
              title="Остановить ответ"
            >
              <Square size={13} fill="#ffffff" />
            </button>
          )}

          {/* Sleek Circular Send Button */}
          <button
            onClick={onSendMessage}
            disabled={!inputText.trim() || loading}
            style={{
              width: 34,
              height: 34,
              borderRadius: '50%',
              border: 'none',
              cursor: (!inputText.trim() || loading) ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              background: (!inputText.trim() || loading)
                ? 'rgba(255, 255, 255, 0.05)'
                : 'linear-gradient(135deg, #a855f7 0%, #ec4899 100%)',
              color: (!inputText.trim() || loading) ? '#64748b' : '#ffffff',
              boxShadow: (!inputText.trim() || loading) ? 'none' : '0 0 16px rgba(168, 85, 247, 0.45)',
              transition: 'all 0.18s ease',
            }}
            title={loading ? 'Идёт обработка запроса, сэр...' : 'Отправить (Enter)'}
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};
