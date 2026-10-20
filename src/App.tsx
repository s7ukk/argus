import React, { useState, useEffect, useRef } from 'react';
import confetti from 'canvas-confetti';
import { Header } from './components/Header';
import { AuthScreen } from './components/AuthScreen';
import { Sidebar } from './components/Sidebar';
import { ChatView } from './components/ChatView';
import { ProfileModal } from './components/ProfileModal';
import { NavDock } from './components/NavDock';
import { ScenariosView } from './components/ScenariosView';
import { PluginsView } from './components/PluginsView';
import { SystemView } from './components/SystemView';
import { AboutView } from './components/AboutView';
import { SettingsView } from './components/SettingsView';
import { UserProfile, ChatSession, ChatMessage, NavTab } from './types';
import {
  verifyKey,
  fetchCurrentSession,
  logoutSession,
  fetchChats,
  createChatSession,
  deleteChatSession,
  renameChatSession,
  fetchMessages,
  sendChatMessage,
  API_BASE,
  smartFetch
} from './api';
import { VoiceAssistant } from './utils/voice';
import './styles/globals.css';

export const App: React.FC = () => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [activeTab, setActiveTab] = useState<NavTab>('chat');
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const voiceAssistantRef = useRef<VoiceAssistant | null>(null);
  const activeChatIdRef = useRef<string | null>(null);
  activeChatIdRef.current = activeChatId;
  const profileRef = useRef<UserProfile | null>(null);
  profileRef.current = profile;

  useEffect(() => {
    voiceAssistantRef.current = new VoiceAssistant(
      (transcript) => {
        setInputText(transcript);
        handleSend(transcript);
      },
      (listening) => setIsListening(listening),
      (speaking) => setIsSpeaking(speaking)
    );

    // Continuous Background Wake Word Detection ("Аргус" / "Argus" in Russian & English)
    try {
      let triggers = 'аргус, argus, эй аргус, hey argus, привет аргус, hi argus, аргуст, авгус, argos';
      const sStr = localStorage.getItem('argus_settings');
      if (sStr) {
        const s = JSON.parse(sStr);
        if (s.trigger_words && s.trigger_words.trim()) triggers = s.trigger_words;
      }
      voiceAssistantRef.current.startWakeWordMonitoring(triggers);
    } catch (e) {}

    // Hook Voice Sunder Global Shortcut (Ctrl+Shift+V)
    if ((window as any).electronAPI?.onVoiceSunderTrigger) {
      (window as any).electronAPI.onVoiceSunderTrigger(() => {
        voiceAssistantRef.current?.toggleListening();
      });
    }

    const handleSettingsUpdated = (e: any) => {
      const updated = e.detail;
      if (updated && voiceAssistantRef.current) {
        if (updated.voice_input_mode === 'trigger') {
          voiceAssistantRef.current.startWakeWordMonitoring(updated.trigger_words);
        } else {
          voiceAssistantRef.current.stopWakeWordMonitoring();
        }
      }
    };
    window.addEventListener('argus_settings_updated', handleSettingsUpdated);

    return () => {
      window.removeEventListener('argus_settings_updated', handleSettingsUpdated);
      voiceAssistantRef.current?.stopWakeWordMonitoring();
      voiceAssistantRef.current?.stopListening();
      voiceAssistantRef.current?.stopSpeaking();
    };
  }, []);

  // Robust Persistent Auto-Login with Disk & Cookie Fallback
  useEffect(() => {
    let chatsAlreadyLoaded = false;

    const initAuth = async () => {
      // 1. Try reading cookie
      const match = document.cookie.match(new RegExp('(^| )argus_access_key=([^;]+)'));
      const cookieKey = match ? decodeURIComponent(match[2]) : null;

      // 2. Try localStorage
      let savedKey = cookieKey || localStorage.getItem('argus_access_key');
      const cachedProfileStr = localStorage.getItem('argus_user_profile');

      // Immediate zero-latency startup if cached profile exists
      if (cachedProfileStr && savedKey) {
        try {
          const cachedProfile = JSON.parse(cachedProfileStr);
          setProfile(cachedProfile);
          chatsAlreadyLoaded = true;
          loadChats(cachedProfile.key_code);
          setCheckingAuth(false);
        } catch (e) {}
      }

      // 3. Fallback: check backend disk session if key not in local storage
      if (!savedKey) {
        try {
          const diskSession = await fetchCurrentSession();
          if (diskSession && diskSession.key_code) {
            savedKey = diskSession.key_code;
            setProfile(diskSession);
            localStorage.setItem('argus_access_key', savedKey);
            localStorage.setItem('argus_user_profile', JSON.stringify(diskSession));
            document.cookie = `argus_access_key=${encodeURIComponent(savedKey)}; max-age=31536000; path=/; SameSite=Lax`;
            chatsAlreadyLoaded = true;
            loadChats(diskSession.key_code);
            setCheckingAuth(false);
          }
        } catch (e) {}
      }

      if (savedKey) {
        const attemptVerify = (attemptsLeft = 3, delay = 1000) => {
          verifyKey(savedKey!)
            .then((p) => {
              setProfile(p);
              localStorage.setItem('argus_access_key', savedKey!);
              localStorage.setItem('argus_user_profile', JSON.stringify(p));
              document.cookie = `argus_access_key=${encodeURIComponent(savedKey!)}; max-age=31536000; path=/; SameSite=Lax`;
              if (!chatsAlreadyLoaded) {
                chatsAlreadyLoaded = true;
                loadChats(p.key_code);
              }
            })
            .catch((err: any) => {
              // ONLY kick the user out if the server explicitly confirmed the key is invalid
              if (err?.isInvalidKey) {
                localStorage.removeItem('argus_access_key');
                localStorage.removeItem('argus_user_profile');
                document.cookie = 'argus_access_key=; max-age=0; path=/;';
                setProfile(null);
              } else if (attemptsLeft > 0) {
                // If it's a backend startup / network delay, retry without logging out
                setTimeout(() => attemptVerify(attemptsLeft - 1, delay * 1.5), delay);
              }
            })
            .finally(() => setCheckingAuth(false));
        };
        attemptVerify();
      } else {
        setCheckingAuth(false);
      }
    };

    initAuth();
  }, []);

  const loadChats = async (keyCode: string) => {
    try {
      const list = await fetchChats(keyCode);
      if (list && list.length > 0) {
        setChats(list);
        setActiveChatId(list[0].id);
        loadMessages(list[0].id);
      } else {
        const newChat = await createChatSession(keyCode, 'Основной диалог');
        setChats([newChat]);
        setActiveChatId(newChat.id);
        setMessages([]);
      }
    } catch (e) {
      console.error('Failed to load chats:', e);
      const fallbackChat: ChatSession = {
        id: 'local-' + Date.now(),
        title: 'Основной диалог',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      setChats([fallbackChat]);
      setActiveChatId(fallbackChat.id);
      setMessages([]);
    }
  };

  const loadMessages = async (chatId: string) => {
    try { setMessages(await fetchMessages(chatId)); }
    catch (e) { console.error('Failed to load messages:', e); }
  };

  const handleAuthSuccess = (newProfile: UserProfile) => {
    setProfile(newProfile);
    confetti({ particleCount: 90, spread: 80, origin: { y: 0.6 }, colors: ['#a855f7', '#7c3aed', '#c084fc', '#e879f9'] });
    loadChats(newProfile.key_code);
  };

  const handleSelectChat = (id: string) => { setActiveChatId(id); loadMessages(id); };

  const handleCreateChat = async () => {
    if (!profile) return;
    try {
      const newChat = await createChatSession(profile.key_code, `Диалог ${chats.length + 1}`);
      setChats([newChat, ...chats]);
      setActiveChatId(newChat.id);
      setMessages([]);
    } catch (e) { console.error(e); }
  };

  const handleRenameChat = async (id: string, newTitle: string) => {
    if (!profile || !newTitle.trim()) return;
    try {
      await renameChatSession(id, profile.key_code, newTitle.trim());
      setChats((prev) => prev.map((c) => (c.id === id ? { ...c, title: newTitle.trim() } : c)));
    } catch (e) {
      console.error('Failed to rename chat:', e);
    }
  };

  const handleDeleteChat = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!profile) return;
    try {
      await deleteChatSession(id, profile.key_code);
      const remaining = chats.filter((c) => c.id !== id);
      setChats(remaining);
      if (activeChatId === id) {
        if (remaining.length > 0) { setActiveChatId(remaining[0].id); loadMessages(remaining[0].id); }
        else { setActiveChatId(null); setMessages([]); }
      }
    } catch (e) { console.error(e); }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    voiceAssistantRef.current?.stopSpeaking();
    setStreamingMessageId(null);
    setLoading(false);
  };

  const handleSend = async (customText?: string) => {
    const textToSend = (customText || inputText).trim();
    const activeProf = profileRef.current || profile;
    if (!textToSend || !activeProf) return;

    // 1. Instantly clear input field and append user message in UI (0ms delay)
    setInputText('');
    const tempMsg: ChatMessage = {
      id: 'temp-' + Date.now(),
      role: 'user',
      content: textToSend,
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, tempMsg]);
    setLoading(true);

    // Instantly finish previous streaming and speech if user sends next message
    setStreamingMessageId(null);
    voiceAssistantRef.current?.stopSpeaking();

    let targetChatId = activeChatIdRef.current || activeChatId;
    if (!targetChatId) {
      try {
        const newChat = await createChatSession(activeProf.key_code, textToSend.substring(0, 28));
        setChats((prev) => [newChat, ...prev]);
        setActiveChatId(newChat.id);
        targetChatId = newChat.id;
      } catch (e) {
        console.error('Failed to create new chat:', e);
      }
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const shouldRequestAudio = activeProf.voice_enabled !== false;
      const res = await sendChatMessage(targetChatId, activeProf.key_code, textToSend, shouldRequestAudio, controller.signal);
      const asstMsg: ChatMessage = {
        id: res.message_id || 'asst-' + Date.now(),
        role: 'assistant',
        content: res.reply,
        action_type: res.action_type,
        action_data: res.action_data,
        audio_base64: res.audio_base64,
        created_at: res.created_at || new Date().toISOString()
      };
      setMessages((prev) => [...prev, asstMsg]);
      setStreamingMessageId(asstMsg.id);

      if (voiceAssistantRef.current && activeProf.voice_enabled !== false) {
        if (res.audio_base64) {
          voiceAssistantRef.current.playBase64Audio(res.audio_base64, res.reply);
        } else {
          smartFetch('/api/voice/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              text: res.reply,
              voice: 'ru-RU-DmitryNeural'
            })
          })
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => {
              if (data && data.audio_base64 && voiceAssistantRef.current) {
                voiceAssistantRef.current.playBase64Audio(data.audio_base64, res.reply);
              }
            })
            .catch(() => {});
        }
      }
    } catch (err: any) {
      if (err?.name === 'AbortError') {
        return;
      }
      console.error('Failed to send message:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('argus_access_key');
    localStorage.removeItem('argus_user_profile');
    document.cookie = 'argus_access_key=; max-age=0; path=/;';
    setProfile(null);
    setChats([]);
    setMessages([]);
    setActiveChatId(null);
    setIsProfileOpen(false);
  };

  // Global Push-to-Talk Hotkey Listener
  useEffect(() => {
    let settingsStr = localStorage.getItem('argus_settings');
    let pttKey = 'Space';
    let isPttMode = false;
    if (settingsStr) {
      try {
        const s = JSON.parse(settingsStr);
        if (s.voice_input_mode === 'ptt') {
          isPttMode = true;
          pttKey = s.ptt_hotkey || 'Space';
        }
      } catch (e) {}
    }

    if (!isPttMode) return;

    let isKeyDown = false;
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is actively typing in an input
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;

      const matches = 
        e.code === pttKey || 
        e.key === pttKey ||
        (pttKey.toLowerCase().includes('cmd') && e.metaKey) ||
        (pttKey.toLowerCase().includes('meta') && e.metaKey) ||
        (pttKey.toLowerCase().includes('ctrl') && (e.ctrlKey || e.metaKey));

      if (matches && !isKeyDown) {
        isKeyDown = true;
        voiceAssistantRef.current?.startListening();
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const matches = 
        e.code === pttKey || 
        e.key === pttKey ||
        (pttKey.toLowerCase().includes('cmd') && !e.metaKey) ||
        (pttKey.toLowerCase().includes('meta') && !e.metaKey) ||
        (pttKey.toLowerCase().includes('ctrl') && !e.ctrlKey && !e.metaKey);

      if (matches && isKeyDown) {
        isKeyDown = false;
        voiceAssistantRef.current?.stopListening();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  if (checkingAuth) {
    return (
      <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:'100vh', background:'#07050f' }}>
        <div style={{ width:28, height:28, border:'2px solid rgba(139,92,246,0.2)', borderTopColor:'#8b5cf6', borderRadius:'50%' }} className="anim-spin" />
      </div>
    );
  }

  return (
    <div style={{ position:'relative', width:'100vw', height:'100vh', overflow:'hidden', display:'flex', flexDirection:'column' }}>
      <div className="bg-app" />
      <div className="bg-grid" />
      <div className="bg-noise" />

      <Header />

      {!profile ? (
        <AuthScreen onSuccess={handleAuthSuccess} />
      ) : (
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative', zIndex: 2 }}>
          {/* Left Vertical Dock with Numbered Tabs (1, 2, 3, 4, 5) */}
          <NavDock
            activeTab={activeTab}
            onTabChange={setActiveTab}
            profile={profile}
            onOpenProfile={() => setIsProfileOpen(true)}
          />

          {/* Active View Switching */}
          {activeTab === 'chat' && (
            <>
              <Sidebar
                chats={chats}
                activeChatId={activeChatId}
                onSelectChat={handleSelectChat}
                onCreateChat={handleCreateChat}
                onDeleteChat={handleDeleteChat}
                onRenameChat={handleRenameChat}
                profile={profile}
                onOpenProfile={() => setIsProfileOpen(true)}
                isCollapsed={isSidebarCollapsed}
                onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
              />
              <ChatView
                messages={messages}
                loading={loading}
                inputText={inputText}
                onInputChange={setInputText}
                onSendMessage={() => handleSend()}
                isListening={isListening}
                onToggleVoice={() => voiceAssistantRef.current?.toggleListening()}
                isSpeaking={isSpeaking}
                profile={profile}
                onQuickAction={(cmd) => { setInputText(cmd); handleSend(cmd); }}
                streamingMessageId={streamingMessageId}
                onStop={handleStop}
                onFinishStreaming={() => setStreamingMessageId(null)}
              />
            </>
          )}

          {activeTab === 'scenarios' && <ScenariosView />}
          {activeTab === 'plugins' && <PluginsView />}
          {activeTab === 'system' && <SystemView />}
          {activeTab === 'about' && <AboutView />}
          {activeTab === 'settings' && <SettingsView />}

          <ProfileModal
            isOpen={isProfileOpen}
            onClose={() => setIsProfileOpen(false)}
            profile={profile}
            onProfileUpdated={setProfile}
            onLogout={handleLogout}
          />
        </div>
      )}
    </div>
  );
};
