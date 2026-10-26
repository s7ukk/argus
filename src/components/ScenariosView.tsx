import React, { useState, useEffect } from 'react';
import {
  Workflow,
  Sparkles,
  Play,
  Plus,
  Trash2,
  CheckCircle2,
  Briefcase,
  Gamepad2,
  Coffee,
  Volume2,
  ExternalLink,
  Music,
  AppWindow,
  Sun,
  Loader2,
  X,
  Mic,
  AlertCircle
} from 'lucide-react';
import { Scenario, ScenarioStep, SystemAppInfo } from '../types';
import { fetchScenarios, saveScenario, deleteScenario, runScenario, fetchSystemApps, parseScenarioTZ } from '../api';
import {
  Search,
  MessageSquare,
  Headphones,
  Globe,
  Code2,
  Folder,
  Activity,
  Settings,
  Check,
  Radio,
  Cloud,
  Film,
  Disc,
  Compass,
  Layers,
  Terminal,
  Calculator,
  FileText,
  Laptop
} from 'lucide-react';


const getAppIcon = (iconName?: string) => {
  switch (iconName) {
    case 'MessageSquare':
    case 'MessageCircle':
    case 'Hash':
    case 'Phone':
      return <MessageSquare size={17} color="#38bdf8" />;
    case 'Headphones':
      return <Headphones size={17} color="#818cf8" />;
    case 'Music':
    case 'Music2':
    case 'PlayCircle':
    case 'Radio':
      return <Music size={17} color="#f472b6" />;
    case 'Cloud':
      return <Cloud size={17} color="#fb923c" />;
    case 'Film':
    case 'Disc':
    case 'Cast':
      return <Film size={17} color="#c084fc" />;
    case 'Globe':
    case 'Globe2':
    case 'Compass':
    case 'Navigation':
    case 'Flame':
    case 'CircleDot':
    case 'Shield':
      return <Globe size={17} color="#fbbf24" />;
    case 'Code2':
    case 'Cpu':
    case 'TerminalSquare':
    case 'FileCode':
    case 'FileCode2':
      return <Code2 size={17} color="#4ade80" />;
    case 'BookOpen':
    case 'Layers':
      return <Layers size={17} color="#a78bfa" />;
    case 'Terminal':
      return <Terminal size={17} color="#34d399" />;
    case 'Gamepad2':
    case 'Trophy':
    case 'ShieldCheck':
      return <Gamepad2 size={17} color="#f87171" />;
    case 'Calculator':
      return <Calculator size={17} color="#67e8f9" />;
    case 'FileText':
      return <FileText size={17} color="#94a3b8" />;
    case 'Folder':
      return <Folder size={17} color="#facc15" />;
    case 'Activity':
      return <Activity size={17} color="#f43f5e" />;
    case 'Settings':
      return <Settings size={17} color="#94a3b8" />;
    default:
      return <AppWindow size={17} color="var(--accent, #ffffff)" />;
  }
};

const ICON_MAP: Record<string, React.ReactNode> = {
  Briefcase: <Briefcase size={20} color="#38bdf8" />,
  Gamepad2: <Gamepad2 size={20} color="var(--accent, #ffffff)" />,
  Coffee: <Coffee size={20} color="#fbbf24" />,
  Sparkles: <Sparkles size={20} color="var(--accent, #ffffff)" />,
  Workflow: <Workflow size={20} color="var(--accent, #ffffff)" />,
};

export const ScenariosView: React.FC = () => {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<{ id: string; message: string } | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // New Scenario State
  const [newName, setNewName] = useState('');
  const [newTriggers, setNewTriggers] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newIcon, setNewIcon] = useState('Sparkles');
  const [customPromptInput, setCustomPromptInput] = useState('');
  const [newSteps, setNewSteps] = useState<ScenarioStep[]>([]);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // App Picker State
  const [showAppPickerModal, setShowAppPickerModal] = useState(false);
  const [systemApps, setSystemApps] = useState<SystemAppInfo[]>([]);
  const [loadingApps, setLoadingApps] = useState(false);
  const [appSearch, setAppSearch] = useState('');
  const [appCategory, setAppCategory] = useState<string>('all');
  const [customAppName, setCustomAppName] = useState('');
  const [parsingTZ, setParsingTZ] = useState(false);
  const runningRef = React.useRef(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const list = await fetchScenarios();
      setScenarios(list);
    } catch (e) {
      console.error('Failed to load scenarios:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRun = async (s: Scenario) => {
    if (runningRef.current || runningId) return;
    try {
      runningRef.current = true;
      setRunningId(s.id);
      setRunResult(null);
      const res = await runScenario(s.id);
      setRunResult({ id: s.id, message: res.summary || 'Сценарий успешно выполнен !' });
      setTimeout(() => setRunResult(null), 6000);
    } catch (e: any) {
      setRunResult({ id: s.id, message: `Ошибка: ${e.message || 'Сбой выполнения'}` });
    } finally {
      runningRef.current = false;
      setRunningId(null);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Удалить этот пользовательский сценарий?')) return;
    try {
      await deleteScenario(id);
      setScenarios((prev) => prev.filter((s) => s.id !== id));
    } catch (err: any) {
      alert(`Ошибка удаления: ${err.message}`);
    }
  };

  const handleOpenAppPicker = async () => {
    setShowAppPickerModal(true);
    if (systemApps.length === 0) {
      try {
        setLoadingApps(true);
        const apps = await fetchSystemApps();
        setSystemApps(apps);
      } catch (err) {
        console.error('Failed to load system apps:', err);
      } finally {
        setLoadingApps(false);
      }
    }
  };

  const handleSelectApp = (app: SystemAppInfo) => {
    setNewSteps((prev) => [
      ...prev,
      { type: 'launch_app', app: app.id, label: `Запуск ${app.name}` }
    ]);
    setShowAppPickerModal(false);
  };

  const handleAddCustomApp = () => {
    if (!customAppName.trim()) return;
    const name = customAppName.trim();
    setNewSteps((prev) => [
      ...prev,
      { type: 'launch_app', app: name, label: `Запуск ${name}` }
    ]);
    setCustomAppName('');
    setShowAppPickerModal(false);
  };

  const handleAddStep = (stepType: string) => {
    if (stepType === 'volume') {
      setNewSteps((prev) => [...prev, { type: 'volume_set', level: 50, label: 'Громкость 50%' }]);
    } else if (stepType === 'app') {
      handleOpenAppPicker();
    } else if (stepType === 'music') {
      setNewSteps((prev) => [...prev, { type: 'play_music', service: 'auto', query: 'Любимая музыка', action: 'play', label: 'Включить музыку (Любимые / Плейлист)' }]);
    } else if (stepType === 'url') {
      setNewSteps((prev) => [...prev, { type: 'open_url', url: 'https://youtube.com', label: 'Открыть YouTube' }]);
    } else if (stepType === 'clean') {
      setNewSteps((prev) => [...prev, { type: 'empty_recycle', label: 'Очистить корзину' }]);
    }
  };

  const handleAddCustomPromptStep = async () => {
    if (!customPromptInput.trim() || parsingTZ) return;
    const txt = customPromptInput.trim();
    setParsingTZ(true);
    try {
      const parsedSteps = await parseScenarioTZ(txt);
      if (Array.isArray(parsedSteps) && parsedSteps.length > 0) {
        setNewSteps((prev) => [...prev, ...parsedSteps]);
        setCustomPromptInput('');
      } else {
        setNewSteps((prev) => [...prev, { type: 'custom_command', prompt: txt, label: `ТЗ: ${txt}` }]);
        setCustomPromptInput('');
      }
    } catch (err) {
      console.warn('Failed to parse TZ steps, saving as raw prompt:', err);
      setNewSteps((prev) => [...prev, { type: 'custom_command', prompt: txt, label: `ТЗ: ${txt}` }]);
      setCustomPromptInput('');
    } finally {
      setParsingTZ(false);
    }
  };

  const handleRemoveStep = (index: number) => {
    setNewSteps((prev) => prev.filter((_, i) => i !== index));
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) {
      setCreateError('Укажите название сценария');
      return;
    }
    const trigs = newTriggers.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean);
    if (trigs.length === 0) {
      setCreateError('Укажите хотя бы одно голосовое слово активации');
      return;
    }
    let effectiveSteps = [...newSteps];
    if (effectiveSteps.length === 0 && customPromptInput.trim()) {
      const txt = customPromptInput.trim();
      effectiveSteps.push({ type: 'custom_command', prompt: txt, label: `ТЗ: ${txt}` });
    }
    if (effectiveSteps.length === 0) {
      setCreateError('Добавьте хотя бы одно действие или напишите своё ТЗ');
      return;
    }

    try {
      setCreating(true);
      setCreateError(null);
      const created = await saveScenario({
        name: newName.trim(),
        description: newDesc.trim() || `Сценарий ${newName}`,
        triggers: trigs,
        icon: newIcon,
        is_builtin: false,
        steps: effectiveSteps,
      });
      setScenarios((prev) => [...prev, created]);
      setShowCreateModal(false);
      setNewName('');
      setNewTriggers('');
      setNewDesc('');
      setCustomPromptInput('');
      setNewSteps([]);
    } catch (err: any) {
      setCreateError(err.message || 'Не удалось сохранить сценарий');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div
      style={{
        flex: 1,
        height: '100%',
        overflowY: 'auto',
        background: 'radial-gradient(ellipse at 50% 0%, rgba(255, 255, 255, 0.03) 0%, rgba(8, 8, 12, 0.98) 75%)',
        padding: '24px 32px',
        color: '#f8fafc',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 26,
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(56, 189, 248, 0.2) 100%)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Workflow size={20} color="var(--accent, #ffffff)" />
            </div>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: '#ffffff', margin: 0 }}>
              Сценарии & Автоматизация
            </h1>
          </div>
          <p style={{ fontSize: 13, color: '#94a3b8', margin: 0, maxWidth: 650 }}>
            Создавайте цепочки команд для Argus: настройте звук, запустите нужные программы, включите музыку и сайты одной голосовой фразой или в 1 клик.
          </p>
        </div>

        <button
          onClick={() => {
            setShowCreateModal(true);
            setCreateError(null);
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '10px 18px',
            borderRadius: 12,
            background: 'linear-gradient(135deg, var(--accent, #ffffff) 0%, var(--accent, #ffffff) 100%)',
            border: 'none',
            color: '#ffffff',
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 0 16px rgba(255, 255, 255, 0.2)',
            transition: 'all 0.2s ease',
          }}
        >
          <Plus size={16} />
          <span>Создать сценарий</span>
        </button>
      </div>

      {/* Scenarios Grid */}
      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 260 }}>
          <Loader2 className="animate-spin" size={32} color="var(--accent, #ffffff)" />
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
            gap: 20,
          }}
        >
          {scenarios.map((s) => {
            const isRunning = runningId === s.id;
            const hasResult = runResult?.id === s.id;

            return (
              <div
                key={s.id}
                className="glass-card"
                style={{
                  padding: 22,
                  borderRadius: 18,
                  background: 'rgba(14, 14, 18, 0.65)',
                  border: isRunning
                    ? '1px solid rgba(255, 255, 255, 0.4)'
                    : '1px solid rgba(255, 255, 255, 0.08)',
                  boxShadow: isRunning ? '0 0 24px var(--accent-glow, rgba(255, 255, 255, 0.15))' : 'none',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: 16,
                  transition: 'all 0.25s ease',
                }}
              >
                <div>
                  {/* Card Header */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <div
                        style={{
                          width: 42,
                          height: 42,
                          borderRadius: 12,
                          background: 'rgba(255, 255, 255, 0.04)',
                          border: '1px solid rgba(255, 255, 255, 0.1)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        {ICON_MAP[s.icon || 'Sparkles'] || <Sparkles size={20} color="var(--accent, #ffffff)" />}
                      </div>
                      <div>
                        <div style={{ fontSize: 16, fontWeight: 700, color: '#ffffff' }}>{s.name}</div>
                        <div style={{ fontSize: 11, color: s.is_builtin ? '#38bdf8' : 'var(--accent, #ffffff)', fontWeight: 600 }}>
                          {s.is_builtin ? 'Базовый сценарий' : 'Пользовательский'}
                        </div>
                      </div>
                    </div>

                    {!s.is_builtin && (
                      <button
                        onClick={(e) => handleDelete(s.id, e)}
                        style={{
                          background: 'rgba(239, 68, 68, 0.12)',
                          border: '1px solid rgba(239, 68, 68, 0.25)',
                          borderRadius: 8,
                          padding: 6,
                          color: '#ef4444',
                          cursor: 'pointer',
                        }}
                        title="Удалить сценарий"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>

                  {/* Description */}
                  {s.description && (
                    <div style={{ fontSize: 12.5, color: '#94a3b8', lineHeight: 1.45, marginBottom: 14 }}>
                      {s.description}
                    </div>
                  )}

                  {/* Triggers list */}
                  <div style={{ marginBottom: 14 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 6 }}>
                      Голосовые триггеры (скажите вслух):
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {s.triggers.map((trig, idx) => (
                        <div
                          key={idx}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                            padding: '3px 8px',
                            borderRadius: 6,
                            background: 'rgba(255, 255, 255, 0.06)',
                            border: '1px solid var(--accent-glow, rgba(255, 255, 255, 0.12))',
                            fontSize: 11.5,
                            color: 'var(--accent, #ffffff)',
                            fontFamily: 'ui-monospace, monospace',
                          }}
                        >
                          <Mic size={10} />
                          <span>«{trig}»</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Steps List */}
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 6 }}>
                      Действия ({s.steps.length}):
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {s.steps.map((st, sIdx) => {
                        return (
                          <div
                            key={sIdx}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 5,
                              padding: '4px 10px',
                              borderRadius: 8,
                              background: 'rgba(255, 255, 255, 0.04)',
                              border: '1px solid rgba(255, 255, 255, 0.07)',
                              fontSize: 11.5,
                              color: '#cbd5e1',
                            }}
                          >
                            {st.type === 'volume_set' && <Volume2 size={12} color="#38bdf8" />}
                            {st.type === 'launch_app' && <AppWindow size={12} color="#4ade80" />}
                            {st.type === 'play_music' && <Music size={12} color="#cbd5e1" />}
                            {st.type === 'open_url' && <ExternalLink size={12} color="#fbbf24" />}
                            {st.type === 'brightness_set' && <Sun size={12} color="#fb923c" />}
                            <span>{st.label || st.type}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Footer Execution Action */}
                <div>
                  {hasResult && (
                    <div
                      style={{
                        padding: '10px 12px',
                        borderRadius: 10,
                        background: 'rgba(56, 189, 248, 0.12)',
                        border: '1px solid rgba(56, 189, 248, 0.25)',
                        fontSize: 12,
                        color: '#38bdf8',
                        marginBottom: 10,
                        whiteSpace: 'pre-line',
                        lineHeight: 1.4,
                      }}
                    >
                      {runResult.message}
                    </div>
                  )}

                  <button
                    onClick={() => handleRun(s)}
                    disabled={isRunning}
                    style={{
                      width: '100%',
                      padding: '10px',
                      borderRadius: 12,
                      background: isRunning
                        ? 'var(--accent-glow, rgba(255, 255, 255, 0.12))'
                        : 'linear-gradient(135deg, rgba(255, 255, 255, 0.4) 0%, rgba(255, 255, 255, 0.35) 100%)',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      color: '#ffffff',
                      fontSize: 13,
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 8,
                      cursor: isRunning ? 'wait' : 'pointer',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    {isRunning ? (
                      <>
                        <Loader2 className="animate-spin" size={16} />
                        <span>Выполняются команды...</span>
                      </>
                    ) : (
                      <>
                        <Play size={15} fill="#ffffff" />
                        <span>Запустить сценарий</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal: Create Custom Scenario */}
      {showCreateModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: 20,
          }}
        >
          <div
            className="glass-card"
            style={{
              width: '100%',
              maxWidth: 580,
              maxHeight: '90vh',
              overflowY: 'auto',
              borderRadius: 20,
              background: 'rgba(12, 12, 16, 0.95)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              boxShadow: '0 0 35px var(--accent-glow, rgba(255, 255, 255, 0.12))',
              padding: 26,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Workflow size={22} color="var(--accent, #ffffff)" />
                <h2 style={{ fontSize: 18, fontWeight: 700, color: '#ffffff', margin: 0 }}>
                  Новый сценарий автоматизации
                </h2>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            {createError && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '10px 14px',
                  borderRadius: 10,
                  background: 'rgba(239, 68, 68, 0.12)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#f87171',
                  fontSize: 12.5,
                  marginBottom: 16,
                }}
              >
                <AlertCircle size={16} />
                <span>{createError}</span>
              </div>
            )}

            <form onSubmit={handleCreateSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#cbd5e1', marginBottom: 6 }}>
                  Название сценария *
                </label>
                <input
                  type="text"
                  placeholder="Например: Утренний фокус"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: 10,
                    padding: '9px 12px',
                    color: '#ffffff',
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#cbd5e1', marginBottom: 6 }}>
                  Голосовые фразы активации (через запятую) *
                </label>
                <input
                  type="text"
                  placeholder="доброе утро, включи утро, режим утро"
                  value={newTriggers}
                  onChange={(e) => setNewTriggers(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: 10,
                    padding: '9px 12px',
                    color: '#ffffff',
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                  Когда вы произнесёте любую из этих фраз («Аргус, доброе утро»), сценарий запустится мгновенно.
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#cbd5e1', marginBottom: 6 }}>
                  Описание
                </label>
                <input
                  type="text"
                  placeholder="Например: Включает спокойную музыку, открывает почту и ставит тихий звук"
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: 10,
                    padding: '9px 12px',
                    color: '#ffffff',
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>

              {/* Steps builder */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1' }}>
                    Шаги сценария ({newSteps.length}):
                  </label>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      onClick={() => handleAddStep('volume')}
                      style={{
                        padding: '4px 8px',
                        borderRadius: 6,
                        background: 'rgba(56, 189, 248, 0.15)',
                        border: '1px solid rgba(56, 189, 248, 0.3)',
                        color: '#38bdf8',
                        fontSize: 11,
                        cursor: 'pointer',
                      }}
                    >
                      + Звук
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAddStep('app')}
                      style={{
                        padding: '4px 8px',
                        borderRadius: 6,
                        background: 'rgba(74, 222, 128, 0.15)',
                        border: '1px solid rgba(74, 222, 128, 0.3)',
                        color: '#4ade80',
                        fontSize: 11,
                        cursor: 'pointer',
                      }}
                    >
                      + Программа
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAddStep('music')}
                      style={{
                        padding: '4px 8px',
                        borderRadius: 6,
                        background: 'rgba(255, 255, 255, 0.08)',
                        border: '1px solid rgba(255, 255, 255, 0.18)',
                        color: '#cbd5e1',
                        fontSize: 11,
                        cursor: 'pointer',
                      }}
                    >
                      + Музыка
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAddStep('url')}
                      style={{
                        padding: '4px 8px',
                        borderRadius: 6,
                        background: 'rgba(251, 191, 36, 0.15)',
                        border: '1px solid rgba(251, 191, 36, 0.3)',
                        color: '#fbbf24',
                        fontSize: 11,
                        cursor: 'pointer',
                      }}
                    >
                      + Сайт
                    </button>
                  </div>
                </div>

                {/* Custom prompt (ТЗ) input */}
                <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
                  <input
                    type="text"
                    value={customPromptInput}
                    onChange={(e) => setCustomPromptInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddCustomPromptStep();
                      }
                    }}
                    placeholder="Напишите своё ТЗ / команду (например: в Telegram напиши @username привет)"
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      borderRadius: 8,
                      background: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid var(--accent-glow, rgba(255, 255, 255, 0.15))',
                      color: '#ffffff',
                      fontSize: 12,
                      outline: 'none',
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleAddCustomPromptStep}
                    disabled={parsingTZ}
                    style={{
                      padding: '8px 14px',
                      borderRadius: 8,
                      background: parsingTZ ? 'rgba(255, 255, 255, 0.2)' : 'linear-gradient(135deg, var(--accent, #ffffff), rgba(200, 200, 210, 0.9))',
                      border: 'none',
                      color: '#ffffff',
                      fontSize: 11.5,
                      fontWeight: 600,
                      cursor: parsingTZ ? 'wait' : 'pointer',
                      whiteSpace: 'nowrap',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                    }}
                  >
                    {parsingTZ ? <Loader2 className="animate-spin" size={13} /> : null}
                    <span>{parsingTZ ? 'Разбор ТЗ...' : '+ Добавить ТЗ'}</span>
                  </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {newSteps.map((step, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        borderRadius: 8,
                        background: 'rgba(255, 255, 255, 0.04)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        fontSize: 12.5,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ color: '#64748b', fontSize: 11 }}>#{idx + 1}</span>
                        <span>{step.label || step.type}</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveStep(idx)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#ef4444',
                          cursor: 'pointer',
                          padding: 2,
                        }}
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 12 }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  style={{
                    padding: '9px 16px',
                    borderRadius: 10,
                    background: 'rgba(255, 255, 255, 0.06)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#cbd5e1',
                    fontSize: 13,
                    cursor: 'pointer',
                  }}
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  style={{
                    padding: '9px 20px',
                    borderRadius: 10,
                    background: 'linear-gradient(135deg, var(--accent, #ffffff) 0%, var(--accent, #ffffff) 100%)',
                    border: 'none',
                    color: '#ffffff',
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: creating ? 'wait' : 'pointer',
                    boxShadow: '0 0 16px rgba(255, 255, 255, 0.2)',
                  }}
                >
                  {creating ? 'Сохранение...' : 'Сохранить сценарий'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    
      {/* Modal: App Picker for Windows & macOS */}
      {showAppPickerModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.82)',
            backdropFilter: 'blur(10px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 110,
            padding: 20,
          }}
        >
          <div
            className="glass-card"
            style={{
              width: '100%',
              maxWidth: 680,
              maxHeight: '85vh',
              display: 'flex',
              flexDirection: 'column',
              borderRadius: 20,
              background: 'rgba(14, 15, 20, 0.96)',
              border: '1px solid rgba(255, 255, 255, 0.18)',
              boxShadow: '0 0 40px rgba(0, 0, 0, 0.8), 0 0 30px var(--accent-glow, rgba(255, 255, 255, 0.08))',
              overflow: 'hidden',
            }}
          >
            {/* Header */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '20px 24px 16px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Laptop size={20} color="var(--accent, #ffffff)" />
                  <h3 style={{ fontSize: 17, fontWeight: 700, color: '#ffffff', margin: 0 }}>
                    Выберите приложение для запуска
                  </h3>
                </div>
                <p style={{ fontSize: 12, color: '#94a3b8', margin: '4px 0 0' }}>
                  Популярные приложения и установленные на вашем компьютере (Windows & macOS)
                </p>
              </div>
              <button
                onClick={() => setShowAppPickerModal(false)}
                style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: 'none',
                  borderRadius: 8,
                  width: 32,
                  height: 32,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#94a3b8',
                  cursor: 'pointer',
                }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Search and Category Filters */}
            <div style={{ padding: '14px 24px', borderBottom: '1px solid rgba(255, 255, 255, 0.06)', display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 12px',
                  borderRadius: 10,
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                }}
              >
                <Search size={16} color="#94a3b8" />
                <input
                  type="text"
                  placeholder="Поиск приложения (Telegram, Spotify, VS Code, Steam, Safari, etc)..."
                  value={appSearch}
                  onChange={(e) => setAppSearch(e.target.value)}
                  style={{
                    background: 'none',
                    border: 'none',
                    outline: 'none',
                    color: '#ffffff',
                    fontSize: 13,
                    width: '100%',
                  }}
                  autoFocus
                />
                {appSearch && (
                  <button
                    onClick={() => setAppSearch('')}
                    style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: 0 }}
                  >
                    <X size={14} />
                  </button>
                )}
              </div>

              {/* Category Pills */}
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {[
                  { id: 'all', label: 'Все' },
                  { id: 'chat', label: 'Мессенджеры' },
                  { id: 'music', label: 'Музыка и Медиа' },
                  { id: 'browser', label: 'Браузеры' },
                  { id: 'dev', label: 'Разработка' },
                  { id: 'games', label: 'Игры' },
                  { id: 'system', label: 'Системные' },
                ].map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => setAppCategory(cat.id)}
                    style={{
                      padding: '5px 11px',
                      borderRadius: 8,
                      background: appCategory === cat.id ? 'var(--accent, #ffffff)' : 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid ' + (appCategory === cat.id ? 'var(--accent, #ffffff)' : 'rgba(255, 255, 255, 0.1)'),
                      color: appCategory === cat.id ? '#000000' : '#cbd5e1',
                      fontSize: 11.5,
                      fontWeight: appCategory === cat.id ? 600 : 400,
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Apps Grid */}
            <div
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: '16px 24px',
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                gap: 10,
                alignContent: 'start',
              }}
            >
              {loadingApps ? (
                <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 0', gap: 10, color: '#94a3b8' }}>
                  <Loader2 className="animate-spin" size={20} color="var(--accent, #ffffff)" />
                  <span>Сканирование установленных приложений...</span>
                </div>
              ) : (
                (() => {
                  const filtered = systemApps.filter((app) => {
                    const matchCat = appCategory === 'all' || app.category === appCategory;
                    const matchSearch =
                      !appSearch.trim() ||
                      app.name.toLowerCase().includes(appSearch.toLowerCase()) ||
                      app.id.toLowerCase().includes(appSearch.toLowerCase()) ||
                      (app.description && app.description.toLowerCase().includes(appSearch.toLowerCase()));
                    return matchCat && matchSearch;
                  });

                  if (filtered.length === 0) {
                    return (
                      <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '30px 0', color: '#94a3b8', fontSize: 13 }}>
                        Приложения не найдены. Вы можете ввести своё имя программы ниже.
                      </div>
                    );
                  }

                  return filtered.map((app) => (
                    <button
                      key={app.id}
                      onClick={() => handleSelectApp(app)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '10px 12px',
                        borderRadius: 12,
                        background: 'rgba(255, 255, 255, 0.04)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        color: '#f8fafc',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'all 0.15s ease',
                        position: 'relative',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.09)';
                        e.currentTarget.style.borderColor = 'var(--accent, rgba(255, 255, 255, 0.3))';
                        e.currentTarget.style.transform = 'translateY(-1px)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                        e.currentTarget.style.transform = 'translateY(0)';
                      }}
                    >
                      <div
                        style={{
                          width: 32,
                          height: 32,
                          borderRadius: 8,
                          background: 'rgba(255, 255, 255, 0.08)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                        }}
                      >
                        {getAppIcon(app.icon)}
                      </div>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontSize: 12.5, fontWeight: 600, color: '#ffffff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {app.name}
                          </span>
                        </div>
                        <div style={{ fontSize: 11, color: '#94a3b8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {app.description || app.id}
                        </div>
                      </div>
                      {app.installed && (
                        <div
                          title="Установлено на этом компьютере"
                          style={{
                            width: 6,
                            height: 6,
                            borderRadius: '50%',
                            background: '#4ade80',
                            boxShadow: '0 0 6px #4ade80',
                            flexShrink: 0,
                          }}
                        />
                      )}
                    </button>
                  ));
                })()
              )}
            </div>

            {/* Custom App input section */}
            <div
              style={{
                padding: '14px 24px',
                borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                background: 'rgba(0, 0, 0, 0.25)',
                display: 'flex',
                gap: 8,
                alignItems: 'center',
              }}
            >
              <input
                type="text"
                placeholder="Или введите своё приложение (например: blender, notepad.exe, obsidian, photoshop)..."
                value={customAppName}
                onChange={(e) => setCustomAppName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddCustomApp();
                  }
                }}
                style={{
                  flex: 1,
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: 10,
                  padding: '9px 12px',
                  color: '#ffffff',
                  fontSize: 12.5,
                  outline: 'none',
                }}
              />
              <button
                type="button"
                onClick={handleAddCustomApp}
                disabled={!customAppName.trim()}
                style={{
                  padding: '9px 16px',
                  borderRadius: 10,
                  background: customAppName.trim() ? 'var(--accent, #ffffff)' : 'rgba(255, 255, 255, 0.08)',
                  color: customAppName.trim() ? '#000000' : '#64748b',
                  border: 'none',
                  fontSize: 12.5,
                  fontWeight: 600,
                  cursor: customAppName.trim() ? 'pointer' : 'default',
                  whiteSpace: 'nowrap',
                }}
              >
                + Добавить своё
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
