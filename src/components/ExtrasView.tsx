import React, { useState, useEffect, useRef } from 'react';
import {
  CheckSquare,
  Square,
  Trash2,
  Plus,
  Play,
  Pause,
  RotateCcw,
  Clock,
  Bell,
  FileText,
  Pin,
  Copy,
  Check,
  Tag,
  AlertCircle,
  Volume2,
  Sparkles,
  Calendar,
  Flame,
  Search,
  Filter,
  CheckCircle2
} from 'lucide-react';
import { TaskItem, NoteItem, TimerItem, ReminderItem, ExtrasData } from '../types';
import { smartFetch } from '../api';

interface ExtrasViewProps {
  onNotifyTimerFinish?: (timerTitle: string) => void;
}

export const ExtrasView: React.FC<ExtrasViewProps> = ({ onNotifyTimerFinish }) => {
  const [subTab, setSubTab] = useState<'tasks' | 'notes' | 'timers'>('timers');
  const [loading, setLoading] = useState<boolean>(false);

  // Core Data States
  const [tasks, setTasks] = useState<TaskItem[]>(() => {
    try {
      const saved = localStorage.getItem('argus_extras_tasks');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [notes, setNotes] = useState<NoteItem[]>(() => {
    try {
      const saved = localStorage.getItem('argus_extras_notes');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [timers, setTimers] = useState<TimerItem[]>(() => {
    try {
      const saved = localStorage.getItem('argus_extras_timers');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Task creation state
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskDesc, setNewTaskDesc] = useState('');
  const [newTaskPriority, setNewTaskPriority] = useState<'low' | 'medium' | 'high' | 'urgent'>('medium');
  const [newTaskCategory, setNewTaskCategory] = useState<'study' | 'work' | 'personal' | 'health' | 'other'>('study');
  const [taskFilter, setTaskFilter] = useState<'all' | 'active' | 'completed'>('all');

  // Note creation state
  const [newNoteTitle, setNewNoteTitle] = useState('');
  const [newNoteContent, setNewNoteContent] = useState('');
  const [newNoteColor, setNewNoteColor] = useState<'purple' | 'blue' | 'emerald' | 'amber' | 'rose'>('purple');
  const [newNoteCategory, setNewNoteCategory] = useState('Общее');
  const [isCreatingNote, setIsCreatingNote] = useState(false);
  const [noteSearch, setNoteSearch] = useState('');
  const [copiedNoteId, setCopiedNoteId] = useState<string | null>(null);

  // Timer creation state
  const [timerTitle, setTimerTitle] = useState('Сделать ДЗ');
  const [timerMinutes, setTimerMinutes] = useState('7');
  const [timerSeconds, setTimerSeconds] = useState('0');

  // Alert Modal state when a timer completes
  const [alarmModalTimer, setAlarmModalTimer] = useState<string | null>(null);

  // Sound chime synthesizer via Web Audio API
  const playAlarmSound = () => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new AudioCtx();
      
      const playTone = (freq: number, start: number, duration: number) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, ctx.currentTime + start);
        gain.gain.setValueAtTime(0.3, ctx.currentTime + start);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + duration);
        osc.start(ctx.currentTime + start);
        osc.stop(ctx.currentTime + start + duration);
      };

      // Gentle double bell chime (E5 -> A5 -> E5 -> C#6)
      playTone(659.25, 0.0, 0.35);
      playTone(880.00, 0.2, 0.45);
      playTone(659.25, 0.5, 0.35);
      playTone(1108.73, 0.7, 0.6);
    } catch (e) {
      console.warn('Web Audio chime notice:', e);
    }
  };

  // Immediate Voice Speech Alert
  const speakVoiceAlert = async (title: string) => {
    const phrase = `Время вышло, сэр! Пора выполнять: ${title}.`;
    try {
      const res = await smartFetch('/api/voice/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: phrase, user_name: 'Пользователь' })
      });
      const data = await res.json();
      if (data && data.audio_base64) {
        const cleanB64 = data.audio_base64.replace(/\s+/g, '');
        const audio = new Audio(`data:audio/mpeg;base64,${cleanB64}`);
        await audio.play();
        return;
      }
    } catch (err) {
      console.warn('Backend TTS error, falling back to Web Speech Synthesis:', err);
    }
    // Fallback speech synthesis
    if ('speechSynthesis' in window) {
      const utt = new SpeechSynthesisUtterance(phrase);
      utt.lang = 'ru-RU';
      utt.rate = 1.05;
      window.speechSynthesis.speak(utt);
    }
  };

  // Synchronize with backend API on mount
  useEffect(() => {
    const fetchBackendData = async () => {
      try {
        setLoading(true);
        const res = await smartFetch('/api/extras/data');
        if (res.ok) {
          const data: ExtrasData = await res.json();
          if (data.tasks && data.tasks.length > 0) setTasks(data.tasks);
          if (data.notes && data.notes.length > 0) setNotes(data.notes);
          if (data.timers && data.timers.length > 0) setTimers(data.timers);
        }
      } catch (e) {
        console.warn('Failed to sync extras data with backend, using local store:', e);
      } finally {
        setLoading(false);
      }
    };
    fetchBackendData();
    window.addEventListener('argus_extras_updated', fetchBackendData);
    return () => {
      window.removeEventListener('argus_extras_updated', fetchBackendData);
    };
  }, []);

  // Save to localStorage & backend
  useEffect(() => {
    localStorage.setItem('argus_extras_tasks', JSON.stringify(tasks));
  }, [tasks]);

  useEffect(() => {
    localStorage.setItem('argus_extras_notes', JSON.stringify(notes));
  }, [notes]);

  useEffect(() => {
    localStorage.setItem('argus_extras_timers', JSON.stringify(timers));
  }, [timers]);

  const syncBackend = async (payload: Partial<ExtrasData>) => {
    try {
      await smartFetch('/api/extras/data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch (e) {
      console.warn('Sync backend error:', e);
    }
  };

  // Timer interval countdown tick (runs every second)
  useEffect(() => {
    const interval = setInterval(() => {
      setTimers((prevTimers) => {
        let hasChanges = false;
        const updated = prevTimers.map((t) => {
          if (t.is_running && t.remaining_seconds > 0) {
            hasChanges = true;
            const nextSecs = t.remaining_seconds - 1;
            if (nextSecs === 0) {
              // Timer just finished!
              playAlarmSound();
              speakVoiceAlert(t.title);
              setAlarmModalTimer(t.title);
              if (onNotifyTimerFinish) {
                onNotifyTimerFinish(t.title);
              }
              return { ...t, remaining_seconds: 0, is_running: false, is_completed: true };
            }
            return { ...t, remaining_seconds: nextSecs };
          }
          return t;
        });
        return hasChanges ? updated : prevTimers;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [onNotifyTimerFinish]);

  // Task actions
  const handleAddTask = () => {
    if (!newTaskTitle.trim()) return;
    const newTask: TaskItem = {
      id: `task_${Date.now()}`,
      title: newTaskTitle.trim(),
      description: newTaskDesc.trim(),
      priority: newTaskPriority,
      category: newTaskCategory,
      completed: false,
      created_at: new Date().toISOString()
    };
    const nextTasks = [newTask, ...tasks];
    setTasks(nextTasks);
    setNewTaskTitle('');
    setNewTaskDesc('');
    syncBackend({ tasks: nextTasks });
  };

  const handleToggleTask = (id: string) => {
    const nextTasks = tasks.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t));
    setTasks(nextTasks);
    syncBackend({ tasks: nextTasks });
  };

  const handleDeleteTask = (id: string) => {
    const nextTasks = tasks.filter((t) => t.id !== id);
    setTasks(nextTasks);
    syncBackend({ tasks: nextTasks });
  };

  // Note actions
  const handleAddNote = () => {
    if (!newNoteTitle.trim()) return;
    const newNote: NoteItem = {
      id: `note_${Date.now()}`,
      title: newNoteTitle.trim(),
      content: newNoteContent.trim(),
      color: newNoteColor,
      category: newNoteCategory.trim() || 'Общее',
      pinned: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    const nextNotes = [newNote, ...notes];
    setNotes(nextNotes);
    setNewNoteTitle('');
    setNewNoteContent('');
    setIsCreatingNote(false);
    syncBackend({ notes: nextNotes });
  };

  const handleTogglePinNote = (id: string) => {
    const nextNotes = notes.map((n) => (n.id === id ? { ...n, pinned: !n.pinned } : n));
    setNotes(nextNotes);
    syncBackend({ notes: nextNotes });
  };

  const handleDeleteNote = (id: string) => {
    const nextNotes = notes.filter((n) => n.id !== id);
    setNotes(nextNotes);
    syncBackend({ notes: nextNotes });
  };

  const handleCopyNote = (n: NoteItem) => {
    navigator.clipboard.writeText(`${n.title}\n\n${n.content}`);
    setCopiedNoteId(n.id);
    setTimeout(() => setCopiedNoteId(null), 1800);
  };

  // Timer actions
  const handleStartTimer = (titleStr?: string, minutesNum?: number, secondsNum?: number) => {
    const title = titleStr || timerTitle.trim() || 'Таймер';
    const m = minutesNum !== undefined ? minutesNum : parseInt(timerMinutes) || 0;
    const s = secondsNum !== undefined ? secondsNum : parseInt(timerSeconds) || 0;
    const total = m * 60 + s;
    if (total <= 0) return;

    const newTimer: TimerItem = {
      id: `timer_${Date.now()}`,
      title,
      total_seconds: total,
      remaining_seconds: total,
      is_running: true,
      is_completed: false,
      created_at: new Date().toISOString()
    };
    const nextTimers = [newTimer, ...timers];
    setTimers(nextTimers);
    syncBackend({ timers: nextTimers });
  };

  const handleToggleTimerRunning = (id: string) => {
    const nextTimers = timers.map((t) => (t.id === id ? { ...t, is_running: !t.is_running } : t));
    setTimers(nextTimers);
    syncBackend({ timers: nextTimers });
  };

  const handleResetTimer = (id: string) => {
    const nextTimers = timers.map((t) =>
      t.id === id ? { ...t, remaining_seconds: t.total_seconds, is_running: false, is_completed: false } : t
    );
    setTimers(nextTimers);
    syncBackend({ timers: nextTimers });
  };

  const handleDeleteTimer = (id: string) => {
    const nextTimers = timers.filter((t) => t.id !== id);
    setTimers(nextTimers);
    syncBackend({ timers: nextTimers });
  };

  // Format seconds to MM:SS or HH:MM:SS
  const formatTime = (secs: number) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    if (h > 0) {
      return `${h}:${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
    }
    return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // Preset quick timer buttons
  const timerPresets = [
    { label: '5 мин (Перерыв)', title: 'Короткий перерыв', mins: 5 },
    { label: '7 мин (Сделать ДЗ)', title: 'Сделать ДЗ', mins: 7 },
    { label: '15 мин (Фокус)', title: 'Быстрый фокус', mins: 15 },
    { label: '25 мин (Помодоро)', title: 'Помодоро-сессия', mins: 25 },
    { label: '45 мин (Урок)', title: 'Урок / Лекция', mins: 45 },
    { label: '1 час (Работа)', title: 'Глубокая работа', mins: 60 }
  ];

  // Filtering tasks
  const filteredTasks = tasks.filter((t) => {
    if (taskFilter === 'active') return !t.completed;
    if (taskFilter === 'completed') return t.completed;
    return true;
  });

  const completedCount = tasks.filter((t) => t.completed).length;
  const taskProgress = tasks.length > 0 ? Math.round((completedCount / tasks.length) * 100) : 0;

  // Filtered notes
  const filteredNotes = notes.filter((n) => {
    if (!noteSearch.trim()) return true;
    const q = noteSearch.toLowerCase();
    return n.title.toLowerCase().includes(q) || n.content.toLowerCase().includes(q) || (n.category && n.category.toLowerCase().includes(q));
  }).sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));

  const noteColorMap = {
    purple: { bg: 'rgba(168, 85, 247, 0.12)', border: 'rgba(168, 85, 247, 0.35)', dot: '#c084fc' },
    blue: { bg: 'rgba(56, 189, 248, 0.12)', border: 'rgba(56, 189, 248, 0.35)', dot: '#38bdf8' },
    emerald: { bg: 'rgba(16, 185, 129, 0.12)', border: 'rgba(16, 185, 129, 0.35)', dot: '#34d399' },
    amber: { bg: 'rgba(245, 158, 11, 0.12)', border: 'rgba(245, 158, 11, 0.35)', dot: '#fbbf24' },
    rose: { bg: 'rgba(244, 63, 94, 0.12)', border: 'rgba(244, 63, 94, 0.35)', dot: '#fb7185' }
  };

  const priorityColor = (p: string) => {
    if (p === 'urgent') return { color: '#ef4444', label: 'Срочно' };
    if (p === 'high') return { color: '#f97316', label: 'Высокий' };
    if (p === 'medium') return { color: '#eab308', label: 'Средний' };
    return { color: '#22c55e', label: 'Низкий' };
  };

  const activeRunningTimersCount = timers.filter((t) => t.is_running && t.remaining_seconds > 0).length;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        background: 'linear-gradient(180deg, #090714 0%, #0c0a1a 100%)',
        color: '#f8fafc',
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
        overflowY: 'auto',
        position: 'relative',
        boxSizing: 'border-box'
      }}
    >
      {/* Top Header & Stats */}
      <div
        style={{
          padding: '24px 32px 16px 32px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(15, 11, 30, 0.75)',
          backdropFilter: 'blur(20px)',
          display: 'flex',
          flexDirection: 'column',
          gap: 16
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1
              style={{
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: '-0.02em',
                margin: 0,
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                background: 'linear-gradient(135deg, #ffffff 0%, #c084fc 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}
            >
              <Sparkles size={22} color="#c084fc" />
              Дополнительно
            </h1>
            <p style={{ margin: '4px 0 0 0', fontSize: 13, color: '#94a3b8' }}>
              Интеллектуальное управление задачами, заметками и голосовыми таймерами с автоматической озвучкой
            </p>
          </div>

          {/* Quick Stats Badges */}
          <div style={{ display: 'flex', gap: 12 }}>
            <div
              style={{
                padding: '8px 14px',
                borderRadius: 12,
                background: 'rgba(168, 85, 247, 0.1)',
                border: '1px solid rgba(168, 85, 247, 0.25)',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 12
              }}
            >
              <CheckSquare size={14} color="#c084fc" />
              <span>
                Задач: <strong style={{ color: '#fff' }}>{tasks.length}</strong> ({taskProgress}%)
              </span>
            </div>

            <div
              style={{
                padding: '8px 14px',
                borderRadius: 12,
                background: 'rgba(56, 189, 248, 0.1)',
                border: '1px solid rgba(56, 189, 248, 0.25)',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 12
              }}
            >
              <FileText size={14} color="#38bdf8" />
              <span>
                Заметок: <strong style={{ color: '#fff' }}>{notes.length}</strong>
              </span>
            </div>

            <div
              style={{
                padding: '8px 14px',
                borderRadius: 12,
                background: activeRunningTimersCount > 0 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                border: activeRunningTimersCount > 0 ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(255, 255, 255, 0.1)',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 12,
                animation: activeRunningTimersCount > 0 ? 'pulse 2s infinite' : 'none'
              }}
            >
              <Clock size={14} color={activeRunningTimersCount > 0 ? '#ef4444' : '#94a3b8'} />
              <span>
                Таймеров:{' '}
                <strong style={{ color: activeRunningTimersCount > 0 ? '#f87171' : '#fff' }}>
                  {activeRunningTimersCount} активных
                </strong>
              </span>
            </div>
          </div>
        </div>

        {/* Sub-tabs Selector */}
        <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid rgba(255, 255, 255, 0.06)' }}>
          <button
            onClick={() => setSubTab('timers')}
            style={{
              padding: '10px 18px',
              border: 'none',
              background: 'none',
              color: subTab === 'timers' ? '#c084fc' : '#94a3b8',
              fontSize: 13,
              fontWeight: subTab === 'timers' ? 600 : 500,
              cursor: 'pointer',
              borderBottom: subTab === 'timers' ? '2px solid #a855f7' : '2px solid transparent',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              transition: 'all 0.15s ease'
            }}
          >
            <Clock size={16} />
            Таймеры и напоминания
            {activeRunningTimersCount > 0 && (
              <span
                style={{
                  background: '#ef4444',
                  color: '#fff',
                  borderRadius: 10,
                  padding: '1px 6px',
                  fontSize: 10,
                  fontWeight: 700
                }}
              >
                {activeRunningTimersCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setSubTab('tasks')}
            style={{
              padding: '10px 18px',
              border: 'none',
              background: 'none',
              color: subTab === 'tasks' ? '#c084fc' : '#94a3b8',
              fontSize: 13,
              fontWeight: subTab === 'tasks' ? 600 : 500,
              cursor: 'pointer',
              borderBottom: subTab === 'tasks' ? '2px solid #a855f7' : '2px solid transparent',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              transition: 'all 0.15s ease'
            }}
          >
            <CheckSquare size={16} />
            Задачи
            <span
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                color: '#cbd5e1',
                borderRadius: 10,
                padding: '1px 6px',
                fontSize: 10
              }}
            >
              {tasks.length}
            </span>
          </button>

          <button
            onClick={() => setSubTab('notes')}
            style={{
              padding: '10px 18px',
              border: 'none',
              background: 'none',
              color: subTab === 'notes' ? '#c084fc' : '#94a3b8',
              fontSize: 13,
              fontWeight: subTab === 'notes' ? 600 : 500,
              cursor: 'pointer',
              borderBottom: subTab === 'notes' ? '2px solid #a855f7' : '2px solid transparent',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              transition: 'all 0.15s ease'
            }}
          >
            <FileText size={16} />
            Заметки
            <span
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                color: '#cbd5e1',
                borderRadius: 10,
                padding: '1px 6px',
                fontSize: 10
              }}
            >
              {notes.length}
            </span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, padding: 32, maxWidth: 1200, width: '100%', margin: '0 auto', boxSizing: 'border-box' }}>
        {/* ========================================================= */}
        {/* TAB 1: TIMERS & REMINDERS                                 */}
        {/* ========================================================= */}
        {subTab === 'timers' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {/* Quick 1-Click Preset Buttons */}
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#94a3b8', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Быстрый запуск в 1 клик
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 10 }}>
                {timerPresets.map((preset, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleStartTimer(preset.title, preset.mins, 0)}
                    style={{
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: 12,
                      padding: '12px 14px',
                      color: '#ffffff',
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'flex-start',
                      gap: 4,
                      transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(168, 85, 247, 0.4)';
                      e.currentTarget.style.transform = 'translateY(-2px)';
                      e.currentTarget.style.background = 'rgba(168, 85, 247, 0.08)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                    }}
                  >
                    <span style={{ color: '#c084fc', fontSize: 13 }}>⏱️ {preset.mins} мин</span>
                    <span style={{ color: '#94a3b8', fontSize: 11, fontWeight: 400 }}>{preset.title}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Custom Timer Input Card */}
            <div
              style={{
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(168, 85, 247, 0.25)',
                borderRadius: 16,
                padding: '20px 24px',
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                gap: 16,
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.25)'
              }}
            >
              <div style={{ flex: '1 1 240px' }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#c084fc', marginBottom: 6 }}>
                  Название задачи / таймера
                </label>
                <input
                  type="text"
                  value={timerTitle}
                  onChange={(e) => setTimerTitle(e.target.value)}
                  placeholder="Например: Сделать ДЗ по физике"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 10,
                    background: 'rgba(0, 0, 0, 0.35)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    color: '#fff',
                    fontSize: 13,
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
                <div>
                  <label style={{ display: 'block', fontSize: 11, color: '#94a3b8', marginBottom: 6 }}>Минут</label>
                  <input
                    type="number"
                    min="0"
                    max="999"
                    value={timerMinutes}
                    onChange={(e) => setTimerMinutes(e.target.value)}
                    style={{
                      width: 70,
                      padding: '10px 12px',
                      borderRadius: 10,
                      background: 'rgba(0, 0, 0, 0.35)',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                      color: '#fff',
                      fontSize: 14,
                      fontWeight: 600,
                      textAlign: 'center',
                      outline: 'none'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 11, color: '#94a3b8', marginBottom: 6 }}>Секунд</label>
                  <input
                    type="number"
                    min="0"
                    max="59"
                    value={timerSeconds}
                    onChange={(e) => setTimerSeconds(e.target.value)}
                    style={{
                      width: 70,
                      padding: '10px 12px',
                      borderRadius: 10,
                      background: 'rgba(0, 0, 0, 0.35)',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                      color: '#fff',
                      fontSize: 14,
                      fontWeight: 600,
                      textAlign: 'center',
                      outline: 'none'
                    }}
                  />
                </div>

                <button
                  onClick={() => handleStartTimer()}
                  style={{
                    padding: '10px 22px',
                    borderRadius: 10,
                    background: 'linear-gradient(135deg, #a855f7 0%, #38bdf8 100%)',
                    border: 'none',
                    color: '#fff',
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    height: 40,
                    boxShadow: '0 4px 16px rgba(168, 85, 247, 0.35)',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-1px)';
                    e.currentTarget.style.boxShadow = '0 6px 20px rgba(168, 85, 247, 0.5)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 4px 16px rgba(168, 85, 247, 0.35)';
                  }}
                >
                  <Play size={14} fill="#fff" />
                  Запустить таймер
                </button>
              </div>
            </div>

            {/* Active Running Timers List */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Активные таймеры ({timers.length})
                </div>
                {timers.length > 0 && (
                  <button
                    onClick={() => {
                      setTimers([]);
                      syncBackend({ timers: [] });
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#ef4444',
                      fontSize: 12,
                      cursor: 'pointer',
                      opacity: 0.8
                    }}
                  >
                    Очистить все
                  </button>
                )}
              </div>

              {timers.length === 0 ? (
                <div
                  style={{
                    padding: '40px 20px',
                    textAlign: 'center',
                    borderRadius: 16,
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px dashed rgba(255, 255, 255, 0.1)',
                    color: '#64748b',
                    fontSize: 13
                  }}
                >
                  <Clock size={36} color="#475569" style={{ margin: '0 auto 10px auto', display: 'block' }} />
                  Нет запущенных таймеров. Запустите готовый пресет на 7 минут или скажите голосом «Таймер на 7 минут сделать ДЗ»!
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
                  {timers.map((timer) => {
                    const percentRemaining = (timer.remaining_seconds / timer.total_seconds) * 100;
                    const isFinished = timer.remaining_seconds === 0;

                    return (
                      <div
                        key={timer.id}
                        style={{
                          background: isFinished
                            ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(30, 27, 75, 0.8) 100%)'
                            : 'linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(15, 11, 30, 0.8) 100%)',
                          border: isFinished
                            ? '1px solid rgba(239, 68, 68, 0.5)'
                            : timer.is_running
                            ? '1px solid rgba(168, 85, 247, 0.4)'
                            : '1px solid rgba(255, 255, 255, 0.08)',
                          borderRadius: 16,
                          padding: '18px 20px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 12,
                          boxShadow: timer.is_running ? '0 8px 24px rgba(168, 85, 247, 0.15)' : 'none',
                          position: 'relative',
                          overflow: 'hidden'
                        }}
                      >
                        {/* Progress Bar Line */}
                        <div
                          style={{
                            position: 'absolute',
                            bottom: 0,
                            left: 0,
                            height: 3,
                            width: `${percentRemaining}%`,
                            background: isFinished ? '#ef4444' : 'linear-gradient(90deg, #a855f7, #38bdf8)',
                            transition: 'width 1s linear'
                          }}
                        />

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div>
                            <div style={{ fontSize: 15, fontWeight: 600, color: '#ffffff' }}>{timer.title}</div>
                            <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                              Всего: {formatTime(timer.total_seconds)}
                            </div>
                          </div>

                          <button
                            onClick={() => handleDeleteTimer(timer.id)}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: '#64748b',
                              cursor: 'pointer',
                              padding: 4
                            }}
                            title="Удалить таймер"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>

                        {/* Digital Countdown Display */}
                        <div
                          style={{
                            fontSize: 36,
                            fontWeight: 700,
                            fontVariantNumeric: 'tabular-nums',
                            letterSpacing: '0.04em',
                            color: isFinished ? '#ef4444' : timer.is_running ? '#ffffff' : '#94a3b8',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 12
                          }}
                        >
                          <span>{formatTime(timer.remaining_seconds)}</span>
                          {isFinished && (
                            <span
                              style={{
                                fontSize: 12,
                                color: '#ef4444',
                                background: 'rgba(239, 68, 68, 0.15)',
                                padding: '4px 8px',
                                borderRadius: 6,
                                fontWeight: 600
                              }}
                            >
                              Время вышло!
                            </span>
                          )}
                        </div>

                        {/* Timer Control Buttons */}
                        <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                          {!isFinished ? (
                            <button
                              onClick={() => handleToggleTimerRunning(timer.id)}
                              style={{
                                flex: 1,
                                padding: '8px 12px',
                                borderRadius: 8,
                                background: timer.is_running
                                  ? 'rgba(234, 179, 8, 0.15)'
                                  : 'rgba(168, 85, 247, 0.25)',
                                border: timer.is_running
                                  ? '1px solid rgba(234, 179, 8, 0.4)'
                                  : '1px solid rgba(168, 85, 247, 0.5)',
                                color: timer.is_running ? '#fbbf24' : '#c084fc',
                                fontSize: 12,
                                fontWeight: 600,
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: 6
                              }}
                            >
                              {timer.is_running ? <Pause size={13} fill="#fbbf24" /> : <Play size={13} fill="#c084fc" />}
                              {timer.is_running ? 'Пауза' : 'Продолжить'}
                            </button>
                          ) : (
                            <button
                              onClick={() => handleResetTimer(timer.id)}
                              style={{
                                flex: 1,
                                padding: '8px 12px',
                                borderRadius: 8,
                                background: 'rgba(56, 189, 248, 0.15)',
                                border: '1px solid rgba(56, 189, 248, 0.4)',
                                color: '#38bdf8',
                                fontSize: 12,
                                fontWeight: 600,
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: 6
                              }}
                            >
                              <RotateCcw size={13} />
                              Перезапустить
                            </button>
                          )}

                          <button
                            onClick={() => handleResetTimer(timer.id)}
                            style={{
                              padding: '8px 12px',
                              borderRadius: 8,
                              background: 'rgba(255, 255, 255, 0.05)',
                              border: '1px solid rgba(255, 255, 255, 0.1)',
                              color: '#94a3b8',
                              fontSize: 12,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center'
                            }}
                            title="Сбросить время"
                          >
                            <RotateCcw size={13} />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 2: TASKS                                              */}
        {/* ========================================================= */}
        {subTab === 'tasks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Add Task Input Bar */}
            <div
              style={{
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: 16,
                padding: '16px 20px',
                display: 'flex',
                flexDirection: 'column',
                gap: 12
              }}
            >
              <div style={{ display: 'flex', gap: 10 }}>
                <input
                  type="text"
                  placeholder="Добавить новую задачу (например: Сделать ДЗ по математике)"
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleAddTask();
                  }}
                  style={{
                    flex: 1,
                    padding: '10px 14px',
                    borderRadius: 10,
                    background: 'rgba(0, 0, 0, 0.35)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    color: '#fff',
                    fontSize: 13,
                    outline: 'none'
                  }}
                />

                <button
                  onClick={handleAddTask}
                  style={{
                    padding: '10px 20px',
                    borderRadius: 10,
                    background: 'linear-gradient(135deg, #a855f7 0%, #38bdf8 100%)',
                    border: 'none',
                    color: '#fff',
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6
                  }}
                >
                  <Plus size={16} />
                  Добавить
                </button>
              </div>

              {/* Priority & Category Pickers */}
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#94a3b8' }}>
                  <span>Приоритет:</span>
                  <select
                    value={newTaskPriority}
                    onChange={(e: any) => setNewTaskPriority(e.target.value)}
                    style={{
                      background: 'rgba(0, 0, 0, 0.4)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#fff',
                      borderRadius: 8,
                      padding: '4px 8px',
                      fontSize: 12,
                      outline: 'none'
                    }}
                  >
                    <option value="low">Низкий</option>
                    <option value="medium">Средний</option>
                    <option value="high">Высокий</option>
                    <option value="urgent">Срочно</option>
                  </select>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#94a3b8' }}>
                  <span>Категория:</span>
                  <select
                    value={newTaskCategory}
                    onChange={(e: any) => setNewTaskCategory(e.target.value)}
                    style={{
                      background: 'rgba(0, 0, 0, 0.4)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#fff',
                      borderRadius: 8,
                      padding: '4px 8px',
                      fontSize: 12,
                      outline: 'none'
                    }}
                  >
                    <option value="study">🎓 Учеба / ДЗ</option>
                    <option value="work">💼 Работа</option>
                    <option value="personal">🏠 Личное</option>
                    <option value="health">🏃 Здоровье</option>
                    <option value="other">💡 Другое</option>
                  </select>
                </div>

                <div style={{ flex: 1 }}>
                  <input
                    type="text"
                    placeholder="Описание или заметка к задаче (необязательно)"
                    value={newTaskDesc}
                    onChange={(e) => setNewTaskDesc(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '6px 12px',
                      borderRadius: 8,
                      background: 'rgba(0, 0, 0, 0.25)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      color: '#cbd5e1',
                      fontSize: 12,
                      outline: 'none',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Filter Pills */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  onClick={() => setTaskFilter('all')}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 8,
                    background: taskFilter === 'all' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                    border: taskFilter === 'all' ? '1px solid rgba(168, 85, 247, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)',
                    color: taskFilter === 'all' ? '#c084fc' : '#94a3b8',
                    fontSize: 12,
                    cursor: 'pointer'
                  }}
                >
                  Все ({tasks.length})
                </button>
                <button
                  onClick={() => setTaskFilter('active')}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 8,
                    background: taskFilter === 'active' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                    border: taskFilter === 'active' ? '1px solid rgba(168, 85, 247, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)',
                    color: taskFilter === 'active' ? '#c084fc' : '#94a3b8',
                    fontSize: 12,
                    cursor: 'pointer'
                  }}
                >
                  В работе ({tasks.length - completedCount})
                </button>
                <button
                  onClick={() => setTaskFilter('completed')}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 8,
                    background: taskFilter === 'completed' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                    border: taskFilter === 'completed' ? '1px solid rgba(168, 85, 247, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)',
                    color: taskFilter === 'completed' ? '#c084fc' : '#94a3b8',
                    fontSize: 12,
                    cursor: 'pointer'
                  }}
                >
                  Завершённые ({completedCount})
                </button>
              </div>

              {/* Progress Indicator */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12, color: '#94a3b8' }}>
                <div style={{ width: 120, height: 6, borderRadius: 3, background: 'rgba(255, 255, 255, 0.08)', overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${taskProgress}%`,
                      background: 'linear-gradient(90deg, #a855f7, #38bdf8)',
                      transition: 'width 0.3s ease'
                    }}
                  />
                </div>
                <span>{taskProgress}% выполнено</span>
              </div>
            </div>

            {/* Tasks List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {filteredTasks.length === 0 ? (
                <div
                  style={{
                    padding: '40px 20px',
                    textAlign: 'center',
                    borderRadius: 16,
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px dashed rgba(255, 255, 255, 0.1)',
                    color: '#64748b',
                    fontSize: 13
                  }}
                >
                  <CheckCircle2 size={32} color="#475569" style={{ margin: '0 auto 10px auto', display: 'block' }} />
                  Задач в этом списке нет
                </div>
              ) : (
                filteredTasks.map((task) => {
                  const pInfo = priorityColor(task.priority);
                  return (
                    <div
                      key={task.id}
                      style={{
                        background: task.completed ? 'rgba(255, 255, 255, 0.02)' : 'rgba(255, 255, 255, 0.04)',
                        border: '1px solid rgba(255, 255, 255, 0.07)',
                        borderRadius: 12,
                        padding: '12px 16px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 14,
                        transition: 'all 0.15s ease'
                      }}
                    >
                      {/* Checkbox */}
                      <button
                        onClick={() => handleToggleTask(task.id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          color: task.completed ? '#10b981' : '#64748b',
                          padding: 2,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}
                      >
                        {task.completed ? <CheckSquare size={20} /> : <Square size={20} />}
                      </button>

                      {/* Content */}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            fontSize: 14,
                            fontWeight: 500,
                            color: task.completed ? '#64748b' : '#ffffff',
                            textDecoration: task.completed ? 'line-through' : 'none'
                          }}
                        >
                          {task.title}
                        </div>
                        {task.description && (
                          <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>{task.description}</div>
                        )}
                      </div>

                      {/* Priority Badge */}
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 600,
                          color: pInfo.color,
                          background: `${pInfo.color}18`,
                          border: `1px solid ${pInfo.color}35`,
                          padding: '3px 8px',
                          borderRadius: 6
                        }}
                      >
                        {pInfo.label}
                      </span>

                      {/* Category Badge */}
                      <span
                        style={{
                          fontSize: 11,
                          color: '#94a3b8',
                          background: 'rgba(255, 255, 255, 0.05)',
                          padding: '3px 8px',
                          borderRadius: 6
                        }}
                      >
                        {task.category === 'study' ? '🎓 Учеба' : task.category === 'work' ? '💼 Работа' : '💡 Общее'}
                      </span>

                      {/* Delete */}
                      <button
                        onClick={() => handleDeleteTask(task.id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#64748b',
                          cursor: 'pointer',
                          padding: 4
                        }}
                        title="Удалить задачу"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 3: NOTES                                              */}
        {/* ========================================================= */}
        {subTab === 'notes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Notes Control Bar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
              <div style={{ position: 'relative', flex: '1 1 280px' }}>
                <Search size={15} color="#94a3b8" style={{ position: 'absolute', left: 12, top: 11 }} />
                <input
                  type="text"
                  placeholder="Поиск по заметкам..."
                  value={noteSearch}
                  onChange={(e) => setNoteSearch(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px 8px 36px',
                    borderRadius: 10,
                    background: 'rgba(0, 0, 0, 0.35)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#fff',
                    fontSize: 13,
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <button
                onClick={() => setIsCreatingNote(!isCreatingNote)}
                style={{
                  padding: '9px 18px',
                  borderRadius: 10,
                  background: 'linear-gradient(135deg, #a855f7 0%, #38bdf8 100%)',
                  border: 'none',
                  color: '#fff',
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                <Plus size={16} />
                Новая заметка
              </button>
            </div>

            {/* Note Creation Card (Expands when clicked) */}
            {isCreatingNote && (
              <div
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(168, 85, 247, 0.35)',
                  borderRadius: 16,
                  padding: 20,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 12,
                  boxShadow: '0 8px 32px rgba(168, 85, 247, 0.1)'
                }}
              >
                <input
                  type="text"
                  placeholder="Заголовок заметки"
                  value={newNoteTitle}
                  onChange={(e) => setNewNoteTitle(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 10,
                    background: 'rgba(0, 0, 0, 0.4)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#fff',
                    fontSize: 14,
                    fontWeight: 600,
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />

                <textarea
                  rows={4}
                  placeholder="Текст заметки..."
                  value={newNoteContent}
                  onChange={(e) => setNewNoteContent(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '12px 14px',
                    borderRadius: 10,
                    background: 'rgba(0, 0, 0, 0.4)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#fff',
                    fontSize: 13,
                    outline: 'none',
                    resize: 'vertical',
                    boxSizing: 'border-box',
                    fontFamily: 'inherit'
                  }}
                />

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                  {/* Color selector */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, color: '#94a3b8' }}>Цвет акцента:</span>
                    {(['purple', 'blue', 'emerald', 'amber', 'rose'] as const).map((colorKey) => (
                      <button
                        key={colorKey}
                        onClick={() => setNewNoteColor(colorKey)}
                        style={{
                          width: 22,
                          height: 22,
                          borderRadius: '50%',
                          background: noteColorMap[colorKey].dot,
                          border: newNoteColor === colorKey ? '2px solid #ffffff' : 'none',
                          cursor: 'pointer',
                          boxShadow: newNoteColor === colorKey ? '0 0 10px #ffffff' : 'none'
                        }}
                      />
                    ))}
                  </div>

                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      onClick={() => setIsCreatingNote(false)}
                      style={{
                        padding: '8px 16px',
                        borderRadius: 8,
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: '#94a3b8',
                        fontSize: 12,
                        cursor: 'pointer'
                      }}
                    >
                      Отмена
                    </button>
                    <button
                      onClick={handleAddNote}
                      style={{
                        padding: '8px 18px',
                        borderRadius: 8,
                        background: 'linear-gradient(135deg, #a855f7 0%, #38bdf8 100%)',
                        border: 'none',
                        color: '#fff',
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: 'pointer'
                      }}
                    >
                      Сохранить заметку
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Notes Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
              {filteredNotes.length === 0 ? (
                <div
                  style={{
                    gridColumn: '1 / -1',
                    padding: '40px 20px',
                    textAlign: 'center',
                    borderRadius: 16,
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px dashed rgba(255, 255, 255, 0.1)',
                    color: '#64748b',
                    fontSize: 13
                  }}
                >
                  <FileText size={32} color="#475569" style={{ margin: '0 auto 10px auto', display: 'block' }} />
                  Заметок не найдено. Нажмите «Новая заметка» или продиктуйте «Создай заметку ...»!
                </div>
              ) : (
                filteredNotes.map((note) => {
                  const styleColor = noteColorMap[note.color] || noteColorMap.purple;
                  return (
                    <div
                      key={note.id}
                      style={{
                        background: styleColor.bg,
                        border: `1px solid ${styleColor.border}`,
                        borderRadius: 16,
                        padding: '16px 18px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        minHeight: 160,
                        position: 'relative',
                        transition: 'all 0.2s ease',
                        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)'
                      }}
                    >
                      <div>
                        {/* Title & Actions */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                          <div style={{ fontSize: 15, fontWeight: 600, color: '#ffffff', wordBreak: 'break-word', paddingRight: 8 }}>
                            {note.title}
                          </div>

                          <div style={{ display: 'flex', gap: 4 }}>
                            <button
                              onClick={() => handleTogglePinNote(note.id)}
                              style={{
                                background: 'none',
                                border: 'none',
                                color: note.pinned ? '#c084fc' : '#64748b',
                                cursor: 'pointer',
                                padding: 3
                              }}
                              title={note.pinned ? 'Открепить' : 'Закрепить'}
                            >
                              <Pin size={13} fill={note.pinned ? '#c084fc' : 'none'} />
                            </button>

                            <button
                              onClick={() => handleCopyNote(note)}
                              style={{
                                background: 'none',
                                border: 'none',
                                color: copiedNoteId === note.id ? '#10b981' : '#64748b',
                                cursor: 'pointer',
                                padding: 3
                              }}
                              title="Копировать текст"
                            >
                              {copiedNoteId === note.id ? <Check size={13} /> : <Copy size={13} />}
                            </button>

                            <button
                              onClick={() => handleDeleteNote(note.id)}
                              style={{
                                background: 'none',
                                border: 'none',
                                color: '#64748b',
                                cursor: 'pointer',
                                padding: 3
                              }}
                              title="Удалить"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </div>

                        {/* Content text */}
                        <div
                          style={{
                            fontSize: 13,
                            color: '#cbd5e1',
                            whiteSpace: 'pre-wrap',
                            lineHeight: 1.5,
                            wordBreak: 'break-word'
                          }}
                        >
                          {note.content}
                        </div>
                      </div>

                      {/* Footer tags */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, paddingTop: 8, borderTop: '1px solid rgba(255, 255, 255, 0.05)' }}>
                        <span style={{ fontSize: 10, color: '#64748b' }}>
                          {note.category || 'Заметка'}
                        </span>
                        <div style={{ width: 6, height: 6, borderRadius: '50%', background: styleColor.dot }} />
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>

      {/* Timer Finished Alarm Notification Modal */}
      {alarmModalTimer && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(10px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100
          }}
        >
          <div
            style={{
              background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(15, 11, 30, 0.95) 100%)',
              border: '2px solid rgba(239, 68, 68, 0.6)',
              borderRadius: 24,
              padding: '36px 40px',
              maxWidth: 440,
              width: '90%',
              textAlign: 'center',
              boxShadow: '0 0 50px rgba(239, 68, 68, 0.35)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 16
            }}
          >
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: '50%',
                background: 'rgba(239, 68, 68, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 30px rgba(239, 68, 68, 0.5)'
              }}
            >
              <Bell size={32} color="#ef4444" />
            </div>

            <h2 style={{ fontSize: 24, fontWeight: 700, margin: 0, color: '#ffffff' }}>Время вышло!</h2>

            <p style={{ fontSize: 16, color: '#fca5a5', margin: 0, lineHeight: 1.4 }}>
              Пора выполнять: <strong>«{alarmModalTimer}»</strong>, сэр!
            </p>

            <div style={{ display: 'flex', gap: 12, marginTop: 8, width: '100%' }}>
              <button
                onClick={() => {
                  // Snooze 5 minutes
                  handleStartTimer(alarmModalTimer, 5, 0);
                  setAlarmModalTimer(null);
                }}
                style={{
                  flex: 1,
                  padding: '12px 16px',
                  borderRadius: 12,
                  background: 'rgba(255, 255, 255, 0.08)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  color: '#fff',
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Отложить на 5 мин
              </button>

              <button
                onClick={() => setAlarmModalTimer(null)}
                style={{
                  flex: 1,
                  padding: '12px 16px',
                  borderRadius: 12,
                  background: 'linear-gradient(135deg, #ef4444 0%, #f97316 100%)',
                  border: 'none',
                  color: '#fff',
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 4px 16px rgba(239, 68, 68, 0.4)'
                }}
              >
                Готово, принято!
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
