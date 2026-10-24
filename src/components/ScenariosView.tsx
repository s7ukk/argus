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
import { Scenario, ScenarioStep } from '../types';
import { fetchScenarios, saveScenario, deleteScenario, runScenario } from '../api';

const ICON_MAP: Record<string, React.ReactNode> = {
  Briefcase: <Briefcase size={20} color="#38bdf8" />,
  Gamepad2: <Gamepad2 size={20} color="#f43f5e" />,
  Coffee: <Coffee size={20} color="#fbbf24" />,
  Sparkles: <Sparkles size={20} color="#c084fc" />,
  Workflow: <Workflow size={20} color="#a855f7" />,
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
  const [newSteps, setNewSteps] = useState<ScenarioStep[]>([
    { type: 'volume_set', level: 40, label: 'Громкость 40%' },
    { type: 'launch_app', app: 'vscode', label: 'Запуск VS Code' },
  ]);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

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
    try {
      setRunningId(s.id);
      setRunResult(null);
      const res = await runScenario(s.id);
      setRunResult({ id: s.id, message: res.summary || 'Сценарий успешно выполнен!' });
      setTimeout(() => setRunResult(null), 6000);
    } catch (e: any) {
      setRunResult({ id: s.id, message: `Ошибка: ${e.message || 'Сбой выполнения'}` });
    } finally {
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

  const handleAddStep = (stepType: string) => {
    if (stepType === 'volume') {
      setNewSteps((prev) => [...prev, { type: 'volume_set', level: 50, label: 'Громкость 50%' }]);
    } else if (stepType === 'app') {
      setNewSteps((prev) => [...prev, { type: 'launch_app', app: 'chrome', label: 'Запустить браузер' }]);
    } else if (stepType === 'music') {
      setNewSteps((prev) => [...prev, { type: 'play_music', service: 'auto', query: 'chill vibes', action: 'play', label: 'Включить музыку' }]);
    } else if (stepType === 'url') {
      setNewSteps((prev) => [...prev, { type: 'open_url', url: 'https://youtube.com', label: 'Открыть YouTube' }]);
    } else if (stepType === 'clean') {
      setNewSteps((prev) => [...prev, { type: 'empty_recycle', label: 'Очистить корзину' }]);
    } else if (stepType === 'custom') {
      if (customPromptInput.trim()) {
        const txt = customPromptInput.trim();
        setNewSteps((prev) => [...prev, { type: 'custom_command', prompt: txt, label: `ТЗ: ${txt}` }]);
        setCustomPromptInput('');
      }
    }
  };

  const handleAddCustomPromptStep = () => {
    if (!customPromptInput.trim()) return;
    const txt = customPromptInput.trim();
    setNewSteps((prev) => [...prev, { type: 'custom_command', prompt: txt, label: `ТЗ: ${txt}` }]);
    setCustomPromptInput('');
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
      setNewSteps([{ type: 'volume_set', level: 50, label: 'Громкость 50%' }]);
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
        background: 'radial-gradient(ellipse at 50% 0%, rgba(20, 10, 35, 0.6) 0%, rgba(6, 4, 14, 0.95) 75%)',
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
                background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.3) 0%, rgba(56, 189, 248, 0.2) 100%)',
                border: '1px solid rgba(168, 85, 247, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Workflow size={20} color="#c084fc" />
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
            background: 'linear-gradient(135deg, #a855f7 0%, #7c3aed 100%)',
            border: 'none',
            color: '#ffffff',
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 0 16px rgba(168, 85, 247, 0.4)',
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
          <Loader2 className="animate-spin" size={32} color="#a855f7" />
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
                  background: 'rgba(15, 12, 28, 0.65)',
                  border: isRunning
                    ? '1px solid rgba(168, 85, 247, 0.8)'
                    : '1px solid rgba(255, 255, 255, 0.08)',
                  boxShadow: isRunning ? '0 0 24px rgba(168, 85, 247, 0.35)' : 'none',
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
                        {ICON_MAP[s.icon || 'Sparkles'] || <Sparkles size={20} color="#c084fc" />}
                      </div>
                      <div>
                        <div style={{ fontSize: 16, fontWeight: 700, color: '#ffffff' }}>{s.name}</div>
                        <div style={{ fontSize: 11, color: s.is_builtin ? '#38bdf8' : '#a855f7', fontWeight: 600 }}>
                          {s.is_builtin ? 'Базовый сценарий' : 'Пользовательский'}
                        </div>
                      </div>
                    </div>

                    {!s.is_builtin && (
                      <button
                        onClick={(e) => handleDelete(s.id, e)}
                        style={{
                          background: 'rgba(244, 63, 94, 0.12)',
                          border: '1px solid rgba(244, 63, 94, 0.25)',
                          borderRadius: 8,
                          padding: 6,
                          color: '#f43f5e',
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
                            background: 'rgba(168, 85, 247, 0.12)',
                            border: '1px solid rgba(168, 85, 247, 0.25)',
                            fontSize: 11.5,
                            color: '#c084fc',
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
                            {st.type === 'play_music' && <Music size={12} color="#f472b6" />}
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
                        ? 'rgba(168, 85, 247, 0.25)'
                        : 'linear-gradient(135deg, rgba(168, 85, 247, 0.8) 0%, rgba(124, 58, 237, 0.9) 100%)',
                      border: '1px solid rgba(168, 85, 247, 0.4)',
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
              background: 'rgba(15, 12, 28, 0.95)',
              border: '1px solid rgba(168, 85, 247, 0.4)',
              boxShadow: '0 0 35px rgba(168, 85, 247, 0.25)',
              padding: 26,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Workflow size={22} color="#c084fc" />
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
                  background: 'rgba(244, 63, 94, 0.15)',
                  border: '1px solid rgba(244, 63, 94, 0.3)',
                  color: '#fb7185',
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
                        background: 'rgba(244, 114, 182, 0.15)',
                        border: '1px solid rgba(244, 114, 182, 0.3)',
                        color: '#f472b6',
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
                      border: '1px solid rgba(168, 85, 247, 0.35)',
                      color: '#ffffff',
                      fontSize: 12,
                      outline: 'none',
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleAddCustomPromptStep}
                    style={{
                      padding: '8px 12px',
                      borderRadius: 8,
                      background: 'linear-gradient(135deg, #a855f7, #6366f1)',
                      border: 'none',
                      color: '#ffffff',
                      fontSize: 11.5,
                      fontWeight: 600,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    + Добавить ТЗ
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
                          color: '#f43f5e',
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
                    background: 'linear-gradient(135deg, #a855f7 0%, #7c3aed 100%)',
                    border: 'none',
                    color: '#ffffff',
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: creating ? 'wait' : 'pointer',
                    boxShadow: '0 0 16px rgba(168, 85, 247, 0.4)',
                  }}
                >
                  {creating ? 'Сохранение...' : 'Сохранить сценарий'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
