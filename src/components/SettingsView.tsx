import React, { useState, useEffect } from 'react';
import {
  Settings,
  Mic,
  Volume2,
  Terminal,
  Globe,
  Sparkles,
  Check,
  Play,
  RotateCcw,
  Shield,
  Radio,
  Cpu,
  Layers,
  KeyRound,
  ExternalLink,
  Palette
} from 'lucide-react';
import { AppSettings, BrowserInfo } from '../types';
import { Switch } from './Switch';
import {
  THEME_PRESETS,
  loadThemeConfig,
  applyThemeConfig,
  ThemeConfig,
  NavPosition
} from '../utils/theme';
import {
  fetchSettings,
  updateSettings,
  fetchInstalledBrowsers,
  testFishAudio,
  testEdgeTTS,
  executeTerminal,
  getTerminalAIAssistant
} from '../api';

export const SettingsView: React.FC = () => {
  const [settings, setSettings] = useState<AppSettings>({
    voice_input_mode: 'trigger',
    trigger_words: 'джарвис, jarvis, аргус, argus, эй джарвис, эй аргус',
    ptt_hotkey: 'Space',
    voice_provider: 'edge-tts',
    fish_api_key: '',
    fish_model_id: '',
    edge_voice: 'jarvis',
    voice_speed: 1.05,
    browser_mode: 'ask',
    default_browser: 'auto',
    default_music_app: 'auto',
    auto_heal_plugins: true,
    default_shell: 'powershell',
    openrouter_api_key: '',
    openrouter_model: 'meta-llama/llama-3.3-70b-instruct',
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [browsers, setBrowsers] = useState<BrowserInfo[]>([]);
  const [themeConfig, setThemeConfig] = useState<ThemeConfig>(() => loadThemeConfig());

  const handleUpdateTheme = (updated: Partial<ThemeConfig>) => {
    const next = { ...themeConfig, ...updated };
    setThemeConfig(next);
    applyThemeConfig(next);
    window.dispatchEvent(new CustomEvent('argus_island_notify', {
      detail: { text: 'Тема интерфейса обновлена', type: 'info', duration: 2000 }
    }));
  };

  // Fish Audio preview test state
  const [testingFish, setTestingFish] = useState(false);
  const [fishTestError, setFishTestError] = useState<string | null>(null);

  // Edge-TTS preview test state
  const [testingEdge, setTestingEdge] = useState(false);
  const [edgeTestError, setEdgeTestError] = useState<string | null>(null);

  // Terminal AI Assistant tester
  const [termPrompt, setTermPrompt] = useState('покажи сколько свободного места на дисках');
  const [genCmd, setGenCmd] = useState('');
  const [termOutput, setTermOutput] = useState('');
  const [generatingCmd, setGeneratingCmd] = useState(false);
  const [executingCmd, setExecutingCmd] = useState(false);

  useEffect(() => {
    const loadAll = async () => {
      try {
        setLoading(true);
        const [savedSet, brList] = await Promise.all([
          fetchSettings().catch(() => null),
          fetchInstalledBrowsers().catch(() => []),
        ]);
        if (savedSet) setSettings((prev) => ({ ...prev, ...savedSet }));
        setBrowsers(brList);
      } catch (e) {
        console.error('Settings load error:', e);
      } finally {
        setLoading(false);
      }
    };
    loadAll();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      await updateSettings(settings);
      // Synchronize in localStorage for instant frontend access
      localStorage.setItem('argus_settings', JSON.stringify(settings));
      window.dispatchEvent(new CustomEvent('argus_settings_updated', { detail: settings }));
      window.dispatchEvent(new CustomEvent('argus_island_notify', {
        detail: { text: 'Настройки успешно сохранены !', type: 'success' }
      }));
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2400);
    } catch (e: any) {
      alert(e.message || 'Ошибка сохранения настроек');
    } finally {
      setSaving(false);
    }
  };

  const handleTestEdgeVoice = async () => {
    setEdgeTestError(null);
    setTestingEdge(true);
    try {
      const isEnglish = settings.edge_voice === 'jarvis-en' || settings.edge_voice.includes('GB') || settings.edge_voice.includes('US');
      const testPhrase = isEnglish
        ? 'At your service, sir.'
        : 'На связи, сэр.';
      const res = await testEdgeTTS(
        settings.edge_voice,
        settings.voice_speed,
        testPhrase
      );
      if (res && res.audio_base64) {
        const cleanB64 = res.audio_base64.replace(/\s+/g, '');
        const audio = new Audio(`data:audio/mpeg;base64,${cleanB64}`);
        audio.play().catch((err) => console.warn('Edge voice play error:', err));
      }
    } catch (e: any) {
      setEdgeTestError(e.message || 'Не удалось воспроизвести голос');
    } finally {
      setTestingEdge(false);
    }
  };

  const handleTestFishAudio = async () => {
    if (!settings.fish_api_key.trim()) {
      setFishTestError('Введите API ключ Fish Audio');
      return;
    }
    setFishTestError(null);
    setTestingFish(true);
    try {
      const res = await testFishAudio(
        settings.fish_api_key.trim(),
        settings.fish_model_id.trim() || undefined,
        'Здравствуйте ! Голосовой синтез Argus через API Fish Audio работает превосходно.'
      );
      if (res && res.audio_base64) {
        const cleanB64 = res.audio_base64.replace(/\s+/g, '');
        const audio = new Audio(`data:audio/mpeg;base64,${cleanB64}`);
        audio.play().catch((err) => console.warn('Fish audio play notice:', err));
      }
    } catch (e: any) {
      setFishTestError(e.message || 'Не удалось проверить Fish Audio');
    } finally {
      setTestingFish(false);
    }
  };

  const handleAskAIForTerminal = async () => {
    if (!termPrompt.trim()) return;
    setGeneratingCmd(true);
    setTermOutput('');
    try {
      const res = await getTerminalAIAssistant(termPrompt);
      if (res && res.command) {
        setGenCmd(res.command);
      }
    } catch (e: any) {
      setTermOutput(`Ошибка генерации: ${e.message}`);
    } finally {
      setGeneratingCmd(false);
    }
  };

  const handleRunGeneratedTerminal = async () => {
    if (!genCmd.trim()) return;
    setExecutingCmd(true);
    try {
      const res = await executeTerminal(genCmd, settings.default_shell);
      const text = res.output || res.error || (res.success ? 'Команда выполнена успешно' : 'Ошибка');
      setTermOutput(text);
    } catch (e: any) {
      setTermOutput(`Ошибка: ${e.message}`);
    } finally {
      setExecutingCmd(false);
    }
  };

  if (loading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: 28, height: 28, border: '2px solid rgba(255, 255, 255, 0.1)', borderTopColor: 'var(--accent, #ffffff)', borderRadius: '50%' }} className="anim-spin" />
      </div>
    );
  }

  return (
    <div
      style={{
        flex: 1,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        background: 'rgba(8, 8, 12, 0.65)',
        position: 'relative',
        userSelect: 'none',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          padding: '18px 28px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(12, 12, 16, 0.5)',
          backdropFilter: 'blur(10px)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div
            style={{
              width: 38,
              height: 38,
              borderRadius: 12,
              background: 'linear-gradient(135deg, var(--accent-glow, rgba(255, 255, 255, 0.12)) 0%, rgba(56, 189, 248, 0.2) 100%)',
              border: '1px solid var(--accent-glow, rgba(255, 255, 255, 0.15))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent, #ffffff)',
            }}
          >
            <Settings size={20} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h2 style={{ fontSize: 18, fontWeight: 800, color: '#ffffff', letterSpacing: '0.02em' }}>
                Параметры и Настройки Argus
              </h2>
              <span
                style={{
                  fontSize: 10.5,
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: 99,
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  color: 'var(--accent, #ffffff)',
                  textTransform: 'uppercase',
                }}
              >
                Core Engine 2.0
              </span>
            </div>
            <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
              Настройка триггер-слов, голоса ИИ через Fish Audio / Edge-TTS, браузеров и кроссплатформенного терминала
            </p>
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary"
          style={{
            padding: '9px 20px',
            borderRadius: 12,
            fontSize: 13,
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            boxShadow: '0 0 16px rgba(255, 255, 255, 0.15)',
          }}
        >
          {savedSuccess ? <Check size={16} color="#4ade80" /> : <Settings size={15} />}
          <span>{savedSuccess ? 'Сохранено !' : saving ? 'Сохранение...' : 'Сохранить настройки'}</span>
        </button>
      </div>

      {/* Main Settings Content */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '26px 32px',
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 22,
          maxWidth: 1380,
          margin: '0 auto',
          width: '100%',
        }}
      >
        {/* 0. Appearance & Liquid Glass Theme Engine */}
        <div
          className="anim-fade-up"
          style={{
            gridColumn: '1 / -1',
            padding: 24,
            borderRadius: 22,
            background: 'rgba(12, 12, 16, 0.82)',
            backdropFilter: 'blur(30px) saturate(190%)',
            WebkitBackdropFilter: 'blur(30px) saturate(190%)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            boxShadow: '0 14px 40px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.12)',
            display: 'flex',
            flexDirection: 'column',
            gap: 20,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: '50%',
                  background: 'rgba(255, 255, 255, 0.08)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--accent, #ffffff)',
                  boxShadow: '0 0 16px var(--accent-glow, rgba(255, 255, 255, 0.2))',
                }}
              >
                <Palette size={18} />
              </div>
              <div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#ffffff' }}>
                  Внешний вид & Liquid Glass
                </h3>
                <p style={{ fontSize: 12, color: '#94a3b8' }}>
                  Настройка цветовой палитры, стиля стекла и расположения панели навигации
                </p>
              </div>
            </div>

            {/* Nav Position Switcher */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(255, 255, 255, 0.04)', padding: '4px', borderRadius: 9999, border: '1px solid rgba(255, 255, 255, 0.08)' }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: '#64748b', padding: '0 8px' }}>Панель меню:</span>
              {[
                { pos: 'top' as NavPosition, label: 'Сверху (дефолт)' },
                { pos: 'left' as NavPosition, label: 'Слева' },
                { pos: 'right' as NavPosition, label: 'Справа' },
              ].map((item) => {
                const isSelected = themeConfig.navPosition === item.pos;
                return (
                  <button
                    key={item.pos}
                    onClick={() => handleUpdateTheme({ navPosition: item.pos })}
                    style={{
                      padding: '5px 12px',
                      borderRadius: 9999,
                      border: isSelected ? '1px solid rgba(255, 255, 255, 0.25)' : '1px solid transparent',
                      background: isSelected ? 'rgba(255, 255, 255, 0.14)' : 'transparent',
                      color: isSelected ? '#ffffff' : '#94a3b8',
                      fontSize: 11.5,
                      fontWeight: isSelected ? 600 : 500,
                      cursor: 'pointer',
                      transition: 'all 0.18s ease',
                    }}
                  >
                    {item.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Color Palettes & Custom Picker */}
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', marginBottom: 10 }}>
              Цветовая тема приложения:
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center' }}>
              {THEME_PRESETS.map((preset) => {
                const isActive = themeConfig.accentColor.toLowerCase() === preset.hex.toLowerCase();
                return (
                  <button
                    key={preset.id}
                    onClick={() => handleUpdateTheme({ accentColor: preset.hex, presetId: preset.id })}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '7px 14px',
                      borderRadius: 9999,
                      background: isActive ? 'rgba(255, 255, 255, 0.12)' : 'rgba(255, 255, 255, 0.04)',
                      border: isActive ? `1.5px solid ${preset.hex}` : '1px solid rgba(255, 255, 255, 0.08)',
                      boxShadow: isActive ? `0 0 14px rgba(${preset.rgb}, 0.35)` : 'none',
                      cursor: 'pointer',
                      color: isActive ? '#ffffff' : '#94a3b8',
                      fontSize: 12,
                      fontWeight: 600,
                      transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                    }}
                  >
                    <span
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: '50%',
                        background: preset.hex,
                        boxShadow: `0 0 8px ${preset.hex}`,
                      }}
                    />
                    <span>{preset.name}</span>
                  </button>
                );
              })}

              {/* Custom Color Input */}
              <label
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '5px 12px',
                  borderRadius: 9999,
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: 600,
                  color: '#ffffff',
                }}
              >
                <input
                  type="color"
                  value={themeConfig.accentColor}
                  onChange={(e) => handleUpdateTheme({ accentColor: e.target.value, presetId: 'custom' })}
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: '50%',
                    border: 'none',
                    cursor: 'pointer',
                    background: 'transparent',
                  }}
                />
                <span>Палитра цветов</span>
              </label>
            </div>
          </div>
        </div>

        {/* 1. Voice Input & Trigger Words */}
        <div
          className="glass-card"
          style={{
            padding: 22,
            borderRadius: 18,
            border: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 10,
                background: 'rgba(56, 189, 248, 0.15)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#38bdf8',
              }}
            >
              <Mic size={17} />
            </div>
            <div>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#ffffff' }}>Голосовой ввод и Триггер-слова</h3>
              <p style={{ fontSize: 11.5, color: '#94a3b8' }}>Выберите способ активации голосового ассистента</p>
            </div>
          </div>

          {/* Mode Selector */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
            {[
              { id: 'trigger', label: 'Триггер-слово', desc: '«Аргус», «Argus»' },
              { id: 'ptt', label: 'Push-to-Talk', desc: 'Зажатие клавиши' },
              { id: 'click', label: 'По клику', desc: 'Кнопка микрофона' },
            ].map((m) => (
              <button
                key={m.id}
                onClick={() => setSettings({ ...settings, voice_input_mode: m.id as any })}
                style={{
                  padding: '12px 10px',
                  borderRadius: 12,
                  textAlign: 'center',
                  cursor: 'pointer',
                  border:
                    settings.voice_input_mode === m.id
                      ? '1px solid rgba(56, 189, 248, 0.6)'
                      : '1px solid rgba(255, 255, 255, 0.06)',
                  background:
                    settings.voice_input_mode === m.id
                      ? 'rgba(56, 189, 248, 0.15)'
                      : 'rgba(255, 255, 255, 0.02)',
                  color: settings.voice_input_mode === m.id ? '#ffffff' : '#94a3b8',
                  transition: 'all 0.18s ease',
                }}
              >
                <div style={{ fontSize: 12.5, fontWeight: 700 }}>{m.label}</div>
                <div style={{ fontSize: 10, color: '#64748b', marginTop: 2 }}>{m.desc}</div>
              </button>
            ))}
          </div>

          {/* Trigger Words input */}
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 6 }}>
              Слова-активаторы (через запятую)
            </label>
            <input
              type="text"
              value={settings.trigger_words}
              onChange={(e) => setSettings({ ...settings, trigger_words: e.target.value })}
              placeholder="аргус, argus, эй аргус, привет аргус"
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: 10,
                background: 'rgba(0, 0, 0, 0.35)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                color: '#ffffff',
                fontSize: 13,
                outline: 'none',
              }}
            />
            <span style={{ fontSize: 11, color: '#64748b', marginTop: 4, display: 'block' }}>
              Когда ассистент слышит любое из этих слов, он мгновенно начинает запись команды.
            </span>

            {/* Quick Trigger Selection Chips */}
            <div style={{ marginTop: 10 }}>
              <span style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 6 }}>
                Быстрый выбор триггер-слов (нажмите чтобы добавить / убрать):
              </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {[
                  'аргус',
                  'argus',
                  'эй аргус',
                  'привет аргус',
                  'джарвис',
                  'компьютер',
                  'помощник',
                  'hey argus',
                ].map((tw) => {
                  const wordsList = settings.trigger_words
                    .split(',')
                    .map((w) => w.trim().toLowerCase())
                    .filter(Boolean);
                  const isSelected = wordsList.includes(tw.toLowerCase());
                  return (
                    <button
                      key={tw}
                      type="button"
                      onClick={() => {
                        let nextList = [...wordsList];
                        if (isSelected) {
                          nextList = nextList.filter((w) => w !== tw.toLowerCase());
                        } else {
                          nextList.push(tw.toLowerCase());
                        }
                        setSettings({ ...settings, trigger_words: nextList.join(', ') });
                      }}
                      style={{
                        padding: '4px 10px',
                        borderRadius: 99,
                        fontSize: 11,
                        fontWeight: 600,
                        cursor: 'pointer',
                        border: isSelected
                          ? '1px solid rgba(56, 189, 248, 0.6)'
                          : '1px solid rgba(255, 255, 255, 0.1)',
                        background: isSelected
                          ? 'rgba(56, 189, 248, 0.2)'
                          : 'rgba(255, 255, 255, 0.04)',
                        color: isSelected ? '#38bdf8' : '#94a3b8',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      {isSelected ? '• ' : '+ '}
                      {tw}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Push-to-Talk Hotkey */}
          {settings.voice_input_mode === 'ptt' && (
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 6 }}>
                Клавиша Push-to-Talk (удержание)
              </label>
              <select
                value={settings.ptt_hotkey}
                onChange={(e) => setSettings({ ...settings, ptt_hotkey: e.target.value })}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 10,
                  background: '#0d0918',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#ffffff',
                  fontSize: 13,
                  outline: 'none',
                }}
              >
                <option value="Space">Пробел (Space)</option>
                <option value="F8">Клавиша F8</option>
                <option value="F9">Клавиша F9</option>
                <option value="Alt">Левый Alt</option>
                <option value="Control">Клавиша Ctrl</option>
              </select>
            </div>
          )}
        </div>

        {/* 2. Voice Model & Fish Audio API */}
        <div
          className="glass-card"
          style={{
            padding: 22,
            borderRadius: 18,
            border: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 10,
                background: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent, #ffffff)',
              }}
            >
              <Volume2 size={17} />
            </div>
            <div>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#ffffff' }}>Синтез речи и Голос ИИ</h3>
              <p style={{ fontSize: 11.5, color: '#94a3b8' }}>Настройка нейро-голоса через Edge-TTS или Fish Audio</p>
            </div>
          </div>

          {/* Voice Provider Switch */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
            <button
              onClick={() => setSettings({ ...settings, voice_provider: 'edge-tts' })}
              style={{
                padding: '10px',
                borderRadius: 12,
                cursor: 'pointer',
                border:
                  settings.voice_provider === 'edge-tts'
                    ? '1px solid rgba(255, 255, 255, 0.3)'
                    : '1px solid rgba(255, 255, 255, 0.06)',
                background:
                  settings.voice_provider === 'edge-tts'
                    ? 'rgba(255, 255, 255, 0.08)'
                    : 'rgba(255, 255, 255, 0.02)',
                color: settings.voice_provider === 'edge-tts' ? '#ffffff' : '#94a3b8',
                fontWeight: 700,
                fontSize: 12.5,
              }}
            >
              Neural Edge-TTS (Бесплатно)
            </button>
            <button
              onClick={() => setSettings({ ...settings, voice_provider: 'fish-audio' })}
              style={{
                padding: '10px',
                borderRadius: 12,
                cursor: 'pointer',
                border:
                  settings.voice_provider === 'fish-audio'
                    ? '1px solid rgba(255, 255, 255, 0.2)'
                    : '1px solid rgba(255, 255, 255, 0.06)',
                background:
                  settings.voice_provider === 'fish-audio'
                    ? 'rgba(255, 255, 255, 0.08)'
                    : 'rgba(255, 255, 255, 0.02)',
                color: settings.voice_provider === 'fish-audio' ? '#ffffff' : '#94a3b8',
                fontWeight: 700,
                fontSize: 12.5,
              }}
            >
              Fish Audio API (Клонирование)
            </button>
          </div>

          {settings.voice_provider === 'fish-audio' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 6 }}>
                  Fish Audio API Key
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="password"
                    value={settings.fish_api_key}
                    onChange={(e) => setSettings({ ...settings, fish_api_key: e.target.value })}
                    placeholder="fish-api-xxxxxxxxxxxxxxxx"
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: 10,
                      background: 'rgba(0, 0, 0, 0.35)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#ffffff',
                      fontSize: 13,
                      outline: 'none',
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 6 }}>
                  Reference Voice Model ID (ID голоса на fish.audio)
                </label>
                <input
                  type="text"
                  value={settings.fish_model_id}
                  onChange={(e) => setSettings({ ...settings, fish_model_id: e.target.value })}
                  placeholder="e58b9062b01d4a138c202026778f67e5"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 10,
                    background: 'rgba(0, 0, 0, 0.35)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#ffffff',
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <button
                  onClick={handleTestFishAudio}
                  disabled={testingFish || !settings.fish_api_key.trim()}
                  className="btn-secondary"
                  style={{
                    padding: '8px 16px',
                    borderRadius: 10,
                    fontSize: 12,
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  <Play size={13} />
                  <span>{testingFish ? 'Генерация...' : 'Прослушать голос (Тест)'}</span>
                </button>
                <a
                  href="https://fish.audio"
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    fontSize: 11.5,
                    color: 'var(--accent, #ffffff)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                    textDecoration: 'none',
                  }}
                >
                  Получить ключ на fish.audio <ExternalLink size={12} />
                </a>
              </div>

              {fishTestError && (
                <div style={{ fontSize: 11.5, color: '#f87171', background: 'rgba(239,68,68,0.1)', padding: '6px 10px', borderRadius: 8 }}>
                  {fishTestError}
                </div>
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 6 }}>
                  Студийный голос ассистента
                </label>
                <select
                  value={settings.edge_voice}
                  onChange={(e) => setSettings({ ...settings, edge_voice: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 10,
                    background: '#0d0918',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#ffffff',
                    fontSize: 13,
                    outline: 'none',
                  }}
                >
                  <option value="jarvis">J.A.R.V.I.S. (Интеллектуальный мужской) — Основной</option>
                  <option value="jarvis-en">J.A.R.V.I.S. Original (British English / Paul Bettany style)</option>
                  <option value="ru-RU-DmitryNeural">Дмитрий (ru-RU) — Уверенный мужской голос</option>
                  <option value="ru-RU-SvetlanaNeural">Светлана (ru-RU) — Мягкий и выразительный женский голос</option>
                  <option value="en-US-ChristopherNeural">Christopher (en-US) — Американский английский (мужской)</option>
                  <option value="en-US-JennyNeural">Jenny (en-US) — Американский английский (женский)</option>
                  <option value="en-GB-RyanNeural">Ryan (en-GB) — Британский английский (мужской)</option>
                  <option value="en-GB-SoniaNeural">Sonia (en-GB) — Британский английский (женский)</option>
                </select>

                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 10 }}>
                  <button
                    type="button"
                    onClick={handleTestEdgeVoice}
                    disabled={testingEdge}
                    className="btn-secondary"
                    style={{
                      padding: '8px 16px',
                      borderRadius: 10,
                      fontSize: 12,
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                    }}
                  >
                    <Play size={13} />
                    <span>{testingEdge ? 'Синтез...' : 'Прослушать голос (Тест)'}</span>
                  </button>
                </div>

                {edgeTestError && (
                  <div style={{ fontSize: 11.5, color: '#f87171', background: 'rgba(239,68,68,0.1)', padding: '6px 10px', borderRadius: 8, marginTop: 8 }}>
                    {edgeTestError}
                  </div>
                )}
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1' }}>Скорость воспроизведения</label>
                  <span style={{ fontSize: 12, color: 'var(--accent, #ffffff)', fontWeight: 700 }}>{settings.voice_speed}x</span>
                </div>
                <input
                  type="range"
                  min="0.8"
                  max="1.5"
                  step="0.05"
                  value={settings.voice_speed}
                  onChange={(e) => setSettings({ ...settings, voice_speed: parseFloat(e.target.value) })}
                  style={{ width: '100%', accentColor: 'var(--accent, #ffffff)' }}
                />
              </div>
            </div>
          )}
        </div>

        {/* 3. Browser & App Intelligence */}
        <div
          className="glass-card"
          style={{
            padding: 22,
            borderRadius: 18,
            border: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 10,
                background: 'rgba(251, 191, 36, 0.15)',
                border: '1px solid rgba(251, 191, 36, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fbbf24',
              }}
            >
              <Globe size={17} />
            </div>
            <div>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#ffffff' }}>Управление Браузерами и Приложениями</h3>
              <p style={{ fontSize: 11.5, color: '#94a3b8' }}>Поведение при открытии обозревателей на компьютере</p>
            </div>
          </div>

          <div
            style={{
              padding: '14px',
              borderRadius: 12,
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.06)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#ffffff' }}>
                Спрашивать, какой браузер открыть
              </div>
              <div style={{ fontSize: 11.5, color: '#94a3b8', marginTop: 2 }}>
                Если на компьютере несколько браузеров, ИИ перечислит их и уточнит ваш выбор
              </div>
            </div>
            <Switch
              checked={settings.browser_mode === 'ask'}
              onChange={(checked) => setSettings({ ...settings, browser_mode: checked ? 'ask' : 'default' })}
              size="md"
            />
          </div>

          {/* Default Browser Selector */}
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#cbd5e1', marginBottom: 6 }}>
              Браузер по умолчанию для открытия сайтов и ссылок
            </label>
            <select
              value={settings.default_browser || 'auto'}
              onChange={(e) => setSettings({ ...settings, default_browser: e.target.value })}
              style={{
                width: '100%',
                background: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: 10,
                padding: '9px 12px',
                color: '#ffffff',
                fontSize: 13,
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="auto">Автоматически (Системный браузер)</option>
              {browsers.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 5 }}>
              Все ссылки, сайты и поисковые запросы будут открываться через этот браузер.
            </div>
          </div>

          {/* Default Music App Selector */}
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#cbd5e1', marginBottom: 6 }}>
              Приложение по умолчанию для музыки
            </label>
            <select
              value={settings.default_music_app || 'auto'}
              onChange={(e) => setSettings({ ...settings, default_music_app: e.target.value })}
              style={{
                width: '100%',
                background: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: 10,
                padding: '9px 12px',
                color: '#ffffff',
                fontSize: 13,
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="auto">Спрашивать при первом запросе (или авто)</option>
              <option value="spotify">Spotify (Спотифай)</option>
              <option value="yandex">Яндекс Музыка (Yandex Music)</option>
              <option value="soundcloud">SoundCloud (Саундклауд)</option>
              <option value="apple_music">Apple Music (Эпл Музыка)</option>
              <option value="vk">VK Музыка (ВКонтакте)</option>
              <option value="youtube">YouTube Music (Ютуб Музыка)</option>
            </select>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 5 }}>
              При командах «включи музыку», «включи плейлист ...» или «включи песню ...» Argus автоматически использует этот сервис.
            </div>
          </div>

          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', marginBottom: 8 }}>
              Обнаруженные браузеры на компьютере ({browsers.length}):
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {browsers.map((b) => (
                <div
                  key={b.id}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 10,
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    fontSize: 12,
                    color: '#ffffff',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  <Globe size={13} color="#38bdf8" />
                  <span>{b.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 4. Cross-Platform Terminal & Self-Healing Plugins */}
        <div
          className="glass-card"
          style={{
            padding: 22,
            borderRadius: 18,
            border: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 10,
                background: 'rgba(74, 222, 128, 0.15)',
                border: '1px solid rgba(74, 222, 128, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#4ade80',
              }}
            >
              <Terminal size={17} />
            </div>
            <div>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#ffffff' }}>Кроссплатформенный Терминал и Self-Healing</h3>
              <p style={{ fontSize: 11.5, color: '#94a3b8' }}>PowerShell, Bash, Linux / macOS и авто-установка pip</p>
            </div>
          </div>

          <div
            style={{
              padding: '14px',
              borderRadius: 12,
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.06)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#ffffff' }}>
                Self-Healing: Авто-скачивание библиотек
              </div>
              <div style={{ fontSize: 11.5, color: '#94a3b8', marginTop: 2 }}>
                ИИ автоматически находит и через pip скачивает недостающие пакеты при падении скрипта
              </div>
            </div>
            <Switch
              checked={settings.auto_heal_plugins}
              onChange={(checked) => setSettings({ ...settings, auto_heal_plugins: checked })}
              size="md"
            />
          </div>

          {/* Interactive AI Terminal Assistant Sandbox */}
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 6 }}>
              Интерактивный ИИ-помощник командной строки
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                type="text"
                value={termPrompt}
                onChange={(e) => setTermPrompt(e.target.value)}
                placeholder="Напишите задачу на естественном языке..."
                style={{
                  flex: 1,
                  padding: '9px 12px',
                  borderRadius: 10,
                  background: 'rgba(0, 0, 0, 0.35)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#ffffff',
                  fontSize: 12.5,
                  outline: 'none',
                }}
              />
              <button
                onClick={handleAskAIForTerminal}
                disabled={generatingCmd || !termPrompt.trim()}
                className="btn-secondary"
                style={{
                  padding: '9px 14px',
                  borderRadius: 10,
                  fontSize: 12,
                  fontWeight: 700,
                  flexShrink: 0,
                }}
              >
                {generatingCmd ? 'Генерация...' : 'Сгенерировать'}
              </button>
            </div>

            {genCmd && (
              <div
                style={{
                  marginTop: 10,
                  padding: 10,
                  borderRadius: 10,
                  background: '#09090c',
                  border: '1px solid rgba(74, 222, 128, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 10,
                }}
              >
                <code style={{ fontSize: 11.5, color: '#4ade80', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {genCmd}
                </code>
                <button
                  onClick={handleRunGeneratedTerminal}
                  disabled={executingCmd}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 8,
                    background: '#4ade80',
                    color: '#000000',
                    border: 'none',
                    fontWeight: 700,
                    fontSize: 11.5,
                    cursor: 'pointer',
                    flexShrink: 0,
                  }}
                >
                  {executingCmd ? 'Выполнение...' : 'Запустить'}
                </button>
              </div>
            )}

            {termOutput && (
              <pre
                style={{
                  marginTop: 8,
                  padding: 10,
                  borderRadius: 10,
                  background: '#04020a',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  color: '#e2e8f0',
                  fontSize: 11,
                  maxHeight: 120,
                  overflowY: 'auto',
                  fontFamily: 'ui-monospace, monospace',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {termOutput}
              </pre>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
