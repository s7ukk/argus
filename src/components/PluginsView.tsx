import React, { useState, useEffect, useRef } from 'react';
import {
  Boxes,
  Play,
  Square,
  Trash2,
  Terminal,
  Upload,
  Plus,
  RefreshCw,
  FolderOpen,
  FileCode,
  CheckCircle,
  AlertCircle,
  X,
  Cpu,
  Database,
  ChevronRight,
  ChevronDown,
  FileText,
  Save,
  Check,
  Zap,
  Folder,
  Code2,
  Mic,
  Globe,
  ShieldCheck,
  Sparkles,
  Send,
  Keyboard,
  Sliders,
  Radio,
  Activity,
  Layers,
  ArrowUpRight
} from 'lucide-react';
import { PluginInfo, PluginTreeItem, PluginTreeResponse, PluginFileResponse } from '../types';
import {
  fetchPlugins,
  createPlugin,
  startPlugin,
  stopPlugin,
  deletePlugin,
  fetchPluginLogs,
  fetchPluginTree,
  fetchPluginFile,
  savePluginFile,
  setPluginEntrypoint,
  dictateVoiceSunder
} from '../api';
import { Switch } from './Switch';

export const PluginsView: React.FC = () => {
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [selectedPlugin, setSelectedPlugin] = useState<PluginInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'ide' | 'logs'>('ide');
  const [section, setSection] = useState<'official' | 'custom'>('official');

  // Voice Sunder Settings State
  const [voiceSunderEnabled, setVoiceSunderEnabled] = useState(() => {
    return localStorage.getItem('argus_vs_enabled') !== 'false';
  });
  const [voiceSunderAutoEnter, setVoiceSunderAutoEnter] = useState(() => {
    return localStorage.getItem('argus_vs_auto_enter') === 'true';
  });
  const [voiceSunderHotkey, setVoiceSunderHotkey] = useState(() => {
    return localStorage.getItem('argus_vs_hotkey') || 'Ctrl + Shift + V';
  });
  const [voiceSunderMode, setVoiceSunderMode] = useState<'toggle' | 'ptt'>(() => {
    return (localStorage.getItem('argus_vs_mode') as any) || 'toggle';
  });
  const [testDictationStatus, setTestDictationStatus] = useState<string | null>(null);

  const handleTestVoiceSunder = async () => {
    setTestDictationStatus('Печать в активное окно...');
    try {
      await dictateVoiceSunder('Тестовый ввод текста через официальный плагин Argus Voice Sunder.', voiceSunderAutoEnter);
      setTestDictationStatus('Успешно введено!');
      setTimeout(() => setTestDictationStatus(null), 3000);
    } catch (e: any) {
      setTestDictationStatus('Ошибка ввода');
      setTimeout(() => setTestDictationStatus(null), 3000);
    }
  };

  const updateVoiceSunderSetting = (key: string, val: any) => {
    if (key === 'enabled') {
      setVoiceSunderEnabled(val);
      localStorage.setItem('argus_vs_enabled', String(val));
    } else if (key === 'autoEnter') {
      setVoiceSunderAutoEnter(val);
      localStorage.setItem('argus_vs_auto_enter', String(val));
    } else if (key === 'mode') {
      setVoiceSunderMode(val);
      localStorage.setItem('argus_vs_mode', String(val));
    } else if (key === 'hotkey') {
      setVoiceSunderHotkey(val);
      localStorage.setItem('argus_vs_hotkey', String(val));
    }
  };

  // Logs state
  const [logsText, setLogsText] = useState<string>('');

  // IDE Tree & File Viewer state
  const [treeData, setTreeData] = useState<PluginTreeItem[]>([]);
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});
  const [activeFile, setActiveFile] = useState<PluginFileResponse | null>(null);
  const [fileEditorContent, setFileEditorContent] = useState<string>('');
  const [savingFile, setSavingFile] = useState(false);
  const [fileSavedNotice, setFileSavedNotice] = useState(false);
  const [loadingTree, setLoadingTree] = useState(false);

  // Upload Modal state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadMode, setUploadMode] = useState<'file' | 'folder' | 'code'>('folder');
  const [pluginName, setPluginName] = useState('');
  const [pluginDesc, setPluginDesc] = useState('');
  const [entrypoint, setEntrypoint] = useState('main.py');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [folderFiles, setFolderFiles] = useState<FileList | null>(null);
  const [customCode, setCustomCode] = useState(
    '# Argus Automation Plugin\nimport time\n\nprint("Argus Plugin is executing in background...")\nfor i in range(100):\n    print(f"Task step {i+1} completed")\n    time.sleep(2)\n'
  );
  const [creating, setCreating] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const selectedPluginIdRef = useRef<string | null>(null);
  const sectionRef = useRef<'official' | 'custom'>('official');
  sectionRef.current = section;

  const selectPluginSafe = (plugin: PluginInfo | null) => {
    selectedPluginIdRef.current = plugin ? plugin.id : null;
    setSelectedPlugin(plugin);
  };

  const loadPlugins = async (isInitial = false) => {
    try {
      if (isInitial) setLoading(true);
      const list = await fetchPlugins();
      setPlugins(list);
      
      setSelectedPlugin((prev) => {
        const targetId = selectedPluginIdRef.current || prev?.id;
        if (targetId) {
          const updated = list.find((p) => p.id === targetId);
          if (updated) return updated;
        }
        const currentSection = sectionRef.current;
        const currentSectionPlugins = list.filter((p) => {
          const isOff = p.is_official || ['voice_sunder', 'web_automator', 'system_optimizer'].includes(p.id);
          return currentSection === 'official' ? isOff : !isOff;
        });

        if (!prev && currentSectionPlugins.length > 0) {
          selectedPluginIdRef.current = currentSectionPlugins[0].id;
          return currentSectionPlugins[0];
        }
        return prev;
      });
    } catch (e: any) {
      console.error('Failed to load plugins:', e);
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  useEffect(() => {
    loadPlugins(true);
    const interval = setInterval(() => loadPlugins(false), 4000);
    return () => clearInterval(interval);
  }, []);

  // Load project tree when selected plugin changes
  useEffect(() => {
    if (!selectedPlugin) {
      setTreeData([]);
      setActiveFile(null);
      return;
    }

    const loadTree = async () => {
      setLoadingTree(true);
      try {
        const res: PluginTreeResponse = await fetchPluginTree(selectedPlugin.id);
        if (res && res.tree) {
          setTreeData(res.tree);
          // Expand root folders by default
          const exp: Record<string, boolean> = {};
          res.tree.forEach((node) => {
            if (node.type === 'directory') exp[node.path] = true;
          });
          setExpandedFolders(exp);

          // Auto-open entrypoint file or first file
          const findEntry = (items: PluginTreeItem[]): PluginTreeItem | null => {
            for (const item of items) {
              if (item.type === 'file' && (item.is_entrypoint || item.name.endsWith('.py'))) return item;
              if (item.children) {
                const found = findEntry(item.children);
                if (found) return found;
              }
            }
            return null;
          };
          const target = findEntry(res.tree);
          if (target) {
            loadFileContent(selectedPlugin.id, target.path);
          }
        }
      } catch (e) {
        console.error('Tree load error:', e);
      } finally {
        setLoadingTree(false);
      }
    };

    loadTree();
    loadPluginLogs(selectedPlugin.id);
  }, [selectedPlugin?.id]);

  // Poll logs if logs tab is active
  useEffect(() => {
    if (!selectedPlugin || activeTab !== 'logs') return;
    const interval = setInterval(() => {
      loadPluginLogs(selectedPlugin.id);
    }, 2000);
    return () => clearInterval(interval);
  }, [selectedPlugin?.id, activeTab]);

  const loadPluginLogs = async (id: string) => {
    try {
      const res = await fetchPluginLogs(id);
      setLogsText(res.logs || '');
    } catch (e) {
      setLogsText('Ошибка загрузки логов');
    }
  };

  const loadFileContent = async (pluginId: string, path: string) => {
    try {
      const res: PluginFileResponse = await fetchPluginFile(pluginId, path);
      setActiveFile(res);
      setFileEditorContent(res.content || '');
    } catch (e: any) {
      console.error('File load error:', e);
    }
  };

  const handleSaveFile = async () => {
    if (!selectedPlugin || !activeFile) return;
    try {
      setSavingFile(true);
      await savePluginFile(selectedPlugin.id, activeFile.path, fileEditorContent);
      setFileSavedNotice(true);
      setTimeout(() => setFileSavedNotice(false), 2000);
    } catch (e: any) {
      alert(e.message || 'Ошибка сохранения файла');
    } finally {
      setSavingFile(false);
    }
  };

  const handleSetEntrypoint = async (path: string) => {
    if (!selectedPlugin) return;
    try {
      await setPluginEntrypoint(selectedPlugin.id, path);
      // Reload tree & plugins
      const res: PluginTreeResponse = await fetchPluginTree(selectedPlugin.id);
      setTreeData(res.tree);
      loadPlugins();
    } catch (e: any) {
      alert(e.message || 'Ошибка смены точки входа');
    }
  };

  const handleStart = async (p: PluginInfo) => {
    try {
      await startPlugin(p.id);
      loadPlugins();
      loadPluginLogs(p.id);
    } catch (e: any) {
      alert(e.message || 'Ошибка запуска плагина');
    }
  };

  const handleStop = async (p: PluginInfo) => {
    try {
      await stopPlugin(p.id);
      loadPlugins();
      loadPluginLogs(p.id);
    } catch (e: any) {
      alert(e.message || 'Ошибка остановки плагина');
    }
  };

  const handleDelete = async (p: PluginInfo) => {
    if (!confirm(`Удалить плагин «${p.name}» с компьютера?`)) return;
    try {
      await deletePlugin(p.id);
      if (selectedPlugin?.id === p.id) selectPluginSafe(null);
      loadPlugins();
    } catch (e: any) {
      alert(e.message || 'Ошибка удаления плагина');
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pluginName.trim()) {
      setErrorMsg('Укажите название плагина');
      return;
    }
    setErrorMsg(null);
    setCreating(true);

    try {
      const fd = new FormData();
      fd.append('name', pluginName.trim());
      fd.append('description', pluginDesc.trim());
      fd.append('entrypoint', entrypoint.trim() || 'main.py');

      if (uploadMode === 'file' && selectedFile) {
        fd.append('file', selectedFile);
      } else if (uploadMode === 'folder' && folderFiles && folderFiles.length > 0) {
        const fileArr = Array.from(folderFiles);
        const pathsArr: string[] = [];
        fileArr.forEach((f: File) => {
          fd.append('files', f);
          const rel = (f as any).webkitRelativePath || f.name;
          pathsArr.push(rel);
        });
        fd.append('paths_json', JSON.stringify(pathsArr));
      } else if (uploadMode === 'code') {
        const blob = new Blob([customCode], { type: 'text/plain' });
        fd.append('file', blob, entrypoint.trim() || 'main.py');
      }

      const res = await createPlugin(fd);
      setIsUploadModalOpen(false);
      setPluginName('');
      setPluginDesc('');
      setEntrypoint('main.py');
      setSelectedFile(null);
      setFolderFiles(null);
      setSection('custom');
      if (res && res.id) {
        selectedPluginIdRef.current = res.id;
      }
      await loadPlugins();
    } catch (err: any) {
      setErrorMsg(err.message || 'Не удалось создать плагин');
    } finally {
      setCreating(false);
    }
  };

  const toggleFolder = (path: string) => {
    setExpandedFolders((prev) => ({ ...prev, [path]: !prev[path] }));
  };

  const renderTreeNodes = (items: PluginTreeItem[], depth = 0) => {
    return items.map((item) => {
      if (item.type === 'directory') {
        const isExp = !!expandedFolders[item.path];
        return (
          <div key={item.path}>
            <div
              onClick={() => toggleFolder(item.path)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '5px 8px',
                paddingLeft: 8 + depth * 14,
                borderRadius: 6,
                cursor: 'pointer',
                color: '#cbd5e1',
                fontSize: 12,
                background: isExp ? 'rgba(255, 255, 255, 0.03)' : 'transparent',
              }}
              className="hover:bg-white/5"
            >
              {isExp ? <ChevronDown size={14} color="#a855f7" /> : <ChevronRight size={14} color="#64748b" />}
              <Folder size={14} color="#38bdf8" />
              <span style={{ fontWeight: 600 }}>{item.name}</span>
            </div>
            {isExp && item.children && (
              <div>{renderTreeNodes(item.children, depth + 1)}</div>
            )}
          </div>
        );
      }

      const isSelected = activeFile?.path === item.path;
      return (
        <div
          key={item.path}
          onClick={() => selectedPlugin && loadFileContent(selectedPlugin.id, item.path)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '5px 8px',
            paddingLeft: 22 + depth * 14,
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: 12,
            background: isSelected ? 'rgba(168, 85, 247, 0.2)' : 'transparent',
            border: isSelected ? '1px solid rgba(168, 85, 247, 0.4)' : '1px solid transparent',
            color: isSelected ? '#ffffff' : '#94a3b8',
          }}
          className="hover:bg-white/5"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, overflow: 'hidden' }}>
            <FileCode size={13} color={item.ext === 'py' ? '#fbbf24' : '#94a3b8'} />
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {item.name}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {item.is_entrypoint && (
              <span
                style={{
                  fontSize: 9,
                  fontWeight: 800,
                  padding: '1px 5px',
                  borderRadius: 4,
                  background: 'rgba(74, 222, 128, 0.2)',
                  color: '#4ade80',
                  border: '1px solid rgba(74, 222, 128, 0.4)',
                }}
              >
                ENTRY
              </span>
            )}
            {item.ext === 'py' && !item.is_entrypoint && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleSetEntrypoint(item.path);
                }}
                title="Сделать точкой входа (запуска)"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#64748b',
                  cursor: 'pointer',
                  fontSize: 10,
                  padding: '1px 4px',
                }}
                className="hover:text-purple-400"
              >
                <Zap size={11} />
              </button>
            )}
          </div>
        </div>
      );
    });
  };

  const officialPlugins = plugins.filter(
    (p) => p.is_official || ['voice_sunder', 'web_automator', 'system_optimizer'].includes(p.id)
  );
  const customPlugins = plugins.filter(
    (p) => !p.is_official && !['voice_sunder', 'web_automator', 'system_optimizer'].includes(p.id)
  );
  const activePluginsList = section === 'official' ? officialPlugins : customPlugins;

  return (
    <div
      style={{
        flex: 1,
        height: '100%',
        display: 'flex',
        overflow: 'hidden',
        background: 'radial-gradient(circle at 15% 15%, rgba(168, 85, 247, 0.08) 0%, transparent 40%), radial-gradient(circle at 85% 85%, rgba(56, 189, 248, 0.06) 0%, transparent 40%), rgba(7, 5, 15, 0.75)',
        position: 'relative',
        userSelect: 'none',
      }}
    >
      <style>{`
        @keyframes argus-pulse-dot {
          0%, 100% { transform: scale(1); opacity: 0.85; box-shadow: 0 0 8px #4ade80; }
          50% { transform: scale(1.25); opacity: 1; box-shadow: 0 0 16px #4ade80, 0 0 24px rgba(74, 222, 128, 0.5); }
        }
        .argus-plugin-card {
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .argus-plugin-card:hover {
          transform: translateY(-1.5px);
          box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
        }
        .argus-interactive-btn {
          transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .argus-interactive-btn:hover {
          transform: translateY(-1px) scale(1.02);
        }
        .argus-interactive-btn:active {
          transform: translateY(0) scale(0.98);
        }
      `}</style>

      {/* ─── LEFT COLUMN: PLUGINS LIST & SECTION SWITCHER ─── */}
      <div
        style={{
          width: 330,
          borderRight: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(10, 8, 20, 0.65)',
          backdropFilter: 'blur(16px)',
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0,
        }}
      >
        {/* Top Header */}
        <div
          style={{
            padding: '16px 18px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(255, 255, 255, 0.01)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: 11,
                background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.35) 0%, rgba(56, 189, 248, 0.25) 100%)',
                border: '1px solid rgba(168, 85, 247, 0.45)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#c084fc',
                boxShadow: '0 0 16px rgba(168, 85, 247, 0.35)',
              }}
            >
              <Boxes size={18} />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 800, color: '#ffffff', letterSpacing: '0.01em' }}>Плагины Argus</div>
              <div style={{ fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#a855f7' }} />
                <span>{section === 'official' ? `${officialPlugins.length} официальных` : `${customPlugins.length} пользовательских`}</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="argus-interactive-btn"
            style={{
              padding: '7px 12px',
              borderRadius: 10,
              fontSize: 11.5,
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              background: 'linear-gradient(135deg, #a855f7 0%, #38bdf8 100%)',
              color: '#ffffff',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              boxShadow: '0 4px 16px rgba(168, 85, 247, 0.4)',
              cursor: 'pointer',
            }}
          >
            <Plus size={14} />
            <span>Загрузить</span>
          </button>
        </div>

        {/* Section Switcher Tabs */}
        <div
          style={{
            display: 'flex',
            padding: '10px 14px',
            gap: 8,
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            background: 'rgba(0, 0, 0, 0.25)',
          }}
        >
          <button
            onClick={() => {
              setSection('official');
              if (officialPlugins.length > 0) selectPluginSafe(officialPlugins[0]);
            }}
            className="argus-interactive-btn"
            style={{
              flex: 1,
              padding: '9px 12px',
              borderRadius: 10,
              fontSize: 11.5,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              border: section === 'official' ? '1px solid rgba(168, 85, 247, 0.6)' : '1px solid rgba(255, 255, 255, 0.05)',
              background: section === 'official' ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.25) 0%, rgba(139, 92, 246, 0.15) 100%)' : 'rgba(255, 255, 255, 0.02)',
              color: section === 'official' ? '#ffffff' : '#94a3b8',
              boxShadow: section === 'official' ? '0 0 18px rgba(168, 85, 247, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2)' : 'none',
            }}
          >
            <ShieldCheck size={14} color={section === 'official' ? '#c084fc' : '#94a3b8'} />
            <span>Официальные</span>
            <span
              style={{
                fontSize: 10,
                fontWeight: 800,
                padding: '1px 6px',
                borderRadius: 99,
                background: section === 'official' ? 'rgba(168, 85, 247, 0.35)' : 'rgba(255, 255, 255, 0.08)',
                color: section === 'official' ? '#f3e8ff' : '#64748b',
              }}
            >
              {officialPlugins.length}
            </span>
          </button>
          <button
            onClick={() => {
              setSection('custom');
              if (customPlugins.length > 0) selectPluginSafe(customPlugins[0]);
              else selectPluginSafe(null);
            }}
            className="argus-interactive-btn"
            style={{
              flex: 1,
              padding: '9px 12px',
              borderRadius: 10,
              fontSize: 11.5,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              border: section === 'custom' ? '1px solid rgba(56, 189, 248, 0.6)' : '1px solid rgba(255, 255, 255, 0.05)',
              background: section === 'custom' ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.25) 0%, rgba(14, 165, 233, 0.15) 100%)' : 'rgba(255, 255, 255, 0.02)',
              color: section === 'custom' ? '#ffffff' : '#94a3b8',
              boxShadow: section === 'custom' ? '0 0 18px rgba(56, 189, 248, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2)' : 'none',
            }}
          >
            <Code2 size={14} color={section === 'custom' ? '#38bdf8' : '#94a3b8'} />
            <span>Свои плагины</span>
            <span
              style={{
                fontSize: 10,
                fontWeight: 800,
                padding: '1px 6px',
                borderRadius: 99,
                background: section === 'custom' ? 'rgba(56, 189, 248, 0.35)' : 'rgba(255, 255, 255, 0.08)',
                color: section === 'custom' ? '#e0f2fe' : '#64748b',
              }}
            >
              {customPlugins.length}
            </span>
          </button>
        </div>

        {/* Plugins List Items */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
          {activePluginsList.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: '48px 16px',
                color: '#64748b',
                fontSize: 12,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 12,
              }}
            >
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 14,
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#64748b',
                }}
              >
                <Boxes size={22} />
              </div>
              <div>
                {section === 'official'
                  ? 'Загрузка официальных плагинов...'
                  : 'Нет пользовательских плагинов. Нажмите «Загрузить», чтобы добавить проект, скрипт или ZIP архив.'}
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {activePluginsList.map((p) => {
                const isSelected = selectedPlugin?.id === p.id;
                const isRunning = p.status === 'running' || p.is_official;
                const accentColor = p.id === 'voice_sunder' ? '#c084fc' : p.id === 'web_automator' ? '#38bdf8' : p.id === 'system_optimizer' ? '#4ade80' : '#f59e0b';
                const accentRgb = p.id === 'voice_sunder' ? '192, 132, 252' : p.id === 'web_automator' ? '56, 189, 248' : p.id === 'system_optimizer' ? '74, 222, 128' : '245, 158, 11';

                return (
                  <div
                    key={p.id}
                    onClick={() => selectPluginSafe(p)}
                    className="argus-plugin-card"
                    style={{
                      padding: '12px 14px',
                      borderRadius: 13,
                      cursor: 'pointer',
                      borderLeft: isSelected ? `3px solid ${accentColor}` : '3px solid transparent',
                      border: isSelected
                        ? `1px solid rgba(${accentRgb}, 0.5)`
                        : '1px solid rgba(255, 255, 255, 0.05)',
                      borderLeftWidth: 3,
                      borderLeftColor: isSelected ? accentColor : 'transparent',
                      background: isSelected
                        ? `linear-gradient(135deg, rgba(${accentRgb}, 0.16) 0%, rgba(20, 15, 35, 0.8) 100%)`
                        : 'rgba(255, 255, 255, 0.025)',
                      boxShadow: isSelected ? `0 4px 20px rgba(${accentRgb}, 0.2)` : 'none',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, overflow: 'hidden' }}>
                        <div
                          style={{
                            width: 32,
                            height: 32,
                            borderRadius: 10,
                            background: isSelected ? `rgba(${accentRgb}, 0.25)` : 'rgba(255, 255, 255, 0.04)',
                            border: `1px solid rgba(${accentRgb}, ${isSelected ? 0.5 : 0.15})`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: accentColor,
                            flexShrink: 0,
                            boxShadow: isSelected ? `0 0 12px rgba(${accentRgb}, 0.35)` : 'none',
                          }}
                        >
                          {p.id === 'voice_sunder' ? (
                            <Mic size={16} />
                          ) : p.id === 'web_automator' ? (
                            <Globe size={16} />
                          ) : p.id === 'system_optimizer' ? (
                            <Cpu size={16} />
                          ) : (
                            <FileCode size={16} />
                          )}
                        </div>

                        <div style={{ overflow: 'hidden' }}>
                          <span style={{ fontSize: 13, fontWeight: 700, color: '#ffffff', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {p.name}
                          </span>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2, fontSize: 11, color: '#64748b' }}>
                            {p.is_official ? (
                              <span style={{ color: '#94a3b8' }}>Argus Core Built-in</span>
                            ) : (
                              <>
                                <span>Файлов: {p.files_count || 1}</span>
                                <span>•</span>
                                <span style={{ color: accentColor }}>{p.entrypoint}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>

                      {p.is_official ? (
                        <span
                          style={{
                            fontSize: 9,
                            fontWeight: 800,
                            padding: '3px 7px',
                            borderRadius: 6,
                            background: `rgba(${accentRgb}, 0.18)`,
                            color: accentColor,
                            border: `1px solid rgba(${accentRgb}, 0.35)`,
                            letterSpacing: '0.04em',
                          }}
                        >
                          OFFICIAL
                        </span>
                      ) : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          {isRunning ? (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleStop(p);
                              }}
                              className="argus-interactive-btn"
                              title="Остановить"
                              style={{
                                background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.25) 0%, rgba(220, 38, 38, 0.18) 100%)',
                                border: '1px solid rgba(239, 68, 68, 0.45)',
                                color: '#f87171',
                                borderRadius: 7,
                                padding: '5px 7px',
                                cursor: 'pointer',
                              }}
                            >
                              <Square size={12} />
                            </button>
                          ) : (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleStart(p);
                              }}
                              className="argus-interactive-btn"
                              title="Запустить (с авто-лечением Pip)"
                              style={{
                                background: 'linear-gradient(135deg, rgba(74, 222, 128, 0.25) 0%, rgba(34, 197, 94, 0.18) 100%)',
                                border: '1px solid rgba(74, 222, 128, 0.45)',
                                color: '#4ade80',
                                borderRadius: 7,
                                padding: '5px 7px',
                                cursor: 'pointer',
                              }}
                            >
                              <Play size={12} />
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ─── RIGHT AREA: OFFICIAL DASHBOARD OR IDE INSPECTOR ─── */}
      {selectedPlugin ? (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Top Control Bar */}
          <div
            style={{
              padding: '14px 24px',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              background: 'linear-gradient(180deg, rgba(18, 14, 32, 0.85) 0%, rgba(10, 8, 20, 0.75) 100%)',
              backdropFilter: 'blur(16px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <h3 style={{ fontSize: 17, fontWeight: 900, color: '#ffffff', letterSpacing: '-0.01em' }}>
                    {selectedPlugin.name}
                  </h3>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 800,
                      padding: '3px 9px',
                      borderRadius: 999,
                      background: 'linear-gradient(135deg, rgba(74, 222, 128, 0.2) 0%, rgba(34, 197, 94, 0.1) 100%)',
                      border: '1px solid rgba(74, 222, 128, 0.45)',
                      color: '#4ade80',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                    }}
                  >
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#4ade80', boxShadow: '0 0 6px #4ade80' }} />
                    Active
                  </span>
                  {selectedPlugin.is_official ? (
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        padding: '3px 9px',
                        borderRadius: 999,
                        background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.18) 0%, rgba(147, 51, 234, 0.1) 100%)',
                        border: '1px solid rgba(168, 85, 247, 0.4)',
                        color: '#c084fc',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 5,
                      }}
                    >
                      <ShieldCheck size={12} color="#c084fc" />
                      <span>Argus Core Built-in</span>
                    </span>
                  ) : (
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        padding: '3px 9px',
                        borderRadius: 999,
                        background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.18) 0%, rgba(14, 165, 233, 0.1) 100%)',
                        border: '1px solid rgba(56, 189, 248, 0.4)',
                        color: '#38bdf8',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 5,
                      }}
                    >
                      <Zap size={12} color="#38bdf8" />
                      <span>Self-Healing Pip Active</span>
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 3 }}>
                  {selectedPlugin.description}
                </div>
              </div>
            </div>

            {!selectedPlugin.is_official && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {selectedPlugin.status === 'running' ? (
                  <button
                    onClick={() => handleStop(selectedPlugin)}
                    className="argus-interactive-btn"
                    style={{
                      padding: '8px 16px',
                      borderRadius: 10,
                      fontSize: 12,
                      fontWeight: 700,
                      background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.25) 0%, rgba(220, 38, 38, 0.15) 100%)',
                      border: '1px solid rgba(239, 68, 68, 0.45)',
                      color: '#f87171',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      boxShadow: '0 2px 10px rgba(239, 68, 68, 0.2)',
                    }}
                  >
                    <Square size={13} />
                    <span>Остановить</span>
                  </button>
                ) : (
                  <button
                    onClick={() => handleStart(selectedPlugin)}
                    className="argus-interactive-btn"
                    style={{
                      padding: '8px 18px',
                      borderRadius: 10,
                      fontSize: 12,
                      fontWeight: 700,
                      background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                      border: '1px solid rgba(52, 211, 153, 0.5)',
                      color: '#ffffff',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      boxShadow: '0 4px 14px rgba(16, 185, 129, 0.35)',
                    }}
                  >
                    <Play size={13} fill="#ffffff" />
                    <span>Запустить проект</span>
                  </button>
                )}

                <button
                  onClick={() => handleDelete(selectedPlugin)}
                  className="argus-interactive-btn"
                  style={{
                    padding: '8px 12px',
                    borderRadius: 10,
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    color: '#f87171',
                    cursor: 'pointer',
                  }}
                  title="Удалить плагин"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            )}
          </div>

          {/* Sub Navigation */}
          <div
            style={{
              padding: '0 24px',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              gap: 24,
              background: 'rgba(10, 8, 20, 0.65)',
            }}
          >
            <button
              onClick={() => setActiveTab('ide')}
              className="argus-interactive-btn"
              style={{
                padding: '12px 4px',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'ide' ? '2px solid #a855f7' : '2px solid transparent',
                color: activeTab === 'ide' ? '#ffffff' : '#94a3b8',
                fontSize: 13,
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 7,
                boxShadow: activeTab === 'ide' ? '0 2px 10px rgba(168, 85, 247, 0.3)' : 'none',
                transition: 'all 0.18s ease',
              }}
            >
              <Code2 size={15} color={activeTab === 'ide' ? '#c084fc' : '#94a3b8'} />
              <span>{selectedPlugin.is_official ? 'Параметры и управление' : 'Структура проекта (IDE)'}</span>
            </button>
            <button
              onClick={() => setActiveTab('logs')}
              className="argus-interactive-btn"
              style={{
                padding: '12px 4px',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'logs' ? '2px solid #38bdf8' : '2px solid transparent',
                color: activeTab === 'logs' ? '#ffffff' : '#94a3b8',
                fontSize: 13,
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 7,
                boxShadow: activeTab === 'logs' ? '0 2px 10px rgba(56, 189, 248, 0.3)' : 'none',
                transition: 'all 0.18s ease',
              }}
            >
              <Terminal size={15} color={activeTab === 'logs' ? '#38bdf8' : '#94a3b8'} />
              <span>Живые логи и Консоль</span>
            </button>
          </div>

          {/* Tab 1: Official Controls OR IDE Project Inspector */}
          {activeTab === 'ide' && (
            selectedPlugin.id === 'voice_sunder' ? (
              /* ─── VOICE SUNDER OFFICIAL DASHBOARD ─── */
              <div style={{ flex: 1, overflowY: 'auto', padding: '22px', display: 'flex', flexDirection: 'column', gap: 16 }}>
                {/* Status Hero Card */}
                <div
                  style={{
                    padding: '18px 22px',
                    borderRadius: 16,
                    background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.16) 0%, rgba(56, 189, 248, 0.08) 100%)',
                    border: '1px solid rgba(168, 85, 247, 0.35)',
                    boxShadow: '0 8px 32px rgba(168, 85, 247, 0.12)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div
                      style={{
                        width: 46,
                        height: 46,
                        borderRadius: 14,
                        background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.3) 0%, rgba(147, 51, 234, 0.15) 100%)',
                        border: '1px solid rgba(168, 85, 247, 0.5)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#c084fc',
                        boxShadow: '0 0 16px rgba(168, 85, 247, 0.35)',
                      }}
                    >
                      <Mic size={24} />
                    </div>
                    <div>
                      <h4 style={{ fontSize: 16, fontWeight: 800, color: '#ffffff' }}>
                        Voice Sunder
                      </h4>
                      <p style={{ fontSize: 12.5, color: '#94a3b8', marginTop: 2 }}>
                        Голосовая печать в любое активное окно Windows (Telegram, Discord, Браузер, IDE, Блокнот)
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={() => updateVoiceSunderSetting('enabled', !voiceSunderEnabled)}
                    className="argus-interactive-btn"
                    style={{
                      padding: '8px 18px',
                      borderRadius: 9999,
                      fontSize: 12.5,
                      fontWeight: 800,
                      cursor: 'pointer',
                      border: voiceSunderEnabled ? '1px solid rgba(74, 222, 128, 0.5)' : '1px solid rgba(255, 255, 255, 0.15)',
                      background: voiceSunderEnabled ? 'linear-gradient(135deg, rgba(74, 222, 128, 0.25) 0%, rgba(34, 197, 94, 0.15) 100%)' : 'rgba(255, 255, 255, 0.05)',
                      color: voiceSunderEnabled ? '#4ade80' : '#94a3b8',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      boxShadow: voiceSunderEnabled ? '0 0 16px rgba(74, 222, 128, 0.25)' : 'none',
                    }}
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: voiceSunderEnabled ? '#4ade80' : '#64748b',
                        boxShadow: voiceSunderEnabled ? '0 0 8px #4ade80' : 'none',
                      }}
                    />
                    <span>{voiceSunderEnabled ? 'Модуль Активен' : 'Отключен'}</span>
                  </button>
                </div>

                {/* Configuration Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14 }}>
                  {/* Card 1: Hotkey Settings */}
                  <div
                    style={{
                      padding: 18,
                      borderRadius: 16,
                      background: 'linear-gradient(135deg, rgba(20, 16, 36, 0.7) 0%, rgba(12, 9, 24, 0.8) 100%)',
                      border: '1px solid rgba(168, 85, 247, 0.25)',
                      boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 12,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                        <div style={{ width: 28, height: 28, borderRadius: 8, background: 'rgba(168, 85, 247, 0.2)', border: '1px solid rgba(168, 85, 247, 0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <Keyboard size={15} color="#c084fc" />
                        </div>
                        <span style={{ fontSize: 13.5, fontWeight: 800, color: '#ffffff' }}>Горячая клавиша</span>
                      </div>
                      <div
                        style={{
                          padding: '5px 12px',
                          borderRadius: 8,
                          background: 'rgba(0, 0, 0, 0.6)',
                          border: '1px solid rgba(168, 85, 247, 0.5)',
                          color: '#e9d5ff',
                          fontFamily: 'monospace',
                          fontSize: 12,
                          fontWeight: 800,
                          letterSpacing: '0.04em',
                          boxShadow: '0 0 10px rgba(168, 85, 247, 0.2)',
                        }}
                      >
                        {voiceSunderHotkey}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                      <button
                        onClick={() => updateVoiceSunderSetting('mode', 'toggle')}
                        className="argus-interactive-btn"
                        style={{
                          flex: 1,
                          padding: '9px 12px',
                          borderRadius: 9,
                          fontSize: 12,
                          fontWeight: 700,
                          cursor: 'pointer',
                          border: voiceSunderMode === 'toggle' ? '1px solid #a855f7' : '1px solid rgba(255, 255, 255, 0.08)',
                          background: voiceSunderMode === 'toggle' ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.3) 0%, rgba(147, 51, 234, 0.15) 100%)' : 'rgba(255, 255, 255, 0.03)',
                          color: voiceSunderMode === 'toggle' ? '#ffffff' : '#94a3b8',
                          boxShadow: voiceSunderMode === 'toggle' ? '0 0 12px rgba(168, 85, 247, 0.25)' : 'none',
                        }}
                      >
                        Клик (Toggle)
                      </button>
                      <button
                        onClick={() => updateVoiceSunderSetting('mode', 'ptt')}
                        className="argus-interactive-btn"
                        style={{
                          flex: 1,
                          padding: '9px 12px',
                          borderRadius: 9,
                          fontSize: 12,
                          fontWeight: 700,
                          cursor: 'pointer',
                          border: voiceSunderMode === 'ptt' ? '1px solid #a855f7' : '1px solid rgba(255, 255, 255, 0.08)',
                          background: voiceSunderMode === 'ptt' ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.3) 0%, rgba(147, 51, 234, 0.15) 100%)' : 'rgba(255, 255, 255, 0.03)',
                          color: voiceSunderMode === 'ptt' ? '#ffffff' : '#94a3b8',
                          boxShadow: voiceSunderMode === 'ptt' ? '0 0 12px rgba(168, 85, 247, 0.25)' : 'none',
                        }}
                      >
                        Push-to-Talk
                      </button>
                    </div>
                  </div>

                  {/* Card 2: Auto-Enter & Live Test */}
                  <div
                    style={{
                      padding: 18,
                      borderRadius: 16,
                      background: 'linear-gradient(135deg, rgba(16, 24, 38, 0.7) 0%, rgba(9, 14, 24, 0.8) 100%)',
                      border: '1px solid rgba(56, 189, 248, 0.25)',
                      boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 12,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                        <div style={{ width: 28, height: 28, borderRadius: 8, background: 'rgba(56, 189, 248, 0.2)', border: '1px solid rgba(56, 189, 248, 0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <Send size={15} color="#38bdf8" />
                        </div>
                        <span style={{ fontSize: 13.5, fontWeight: 800, color: '#ffffff' }}>Отправка</span>
                      </div>
                      <button
                        onClick={handleTestVoiceSunder}
                        className="argus-interactive-btn"
                        style={{
                          padding: '6px 14px',
                          borderRadius: 8,
                          fontSize: 12,
                          fontWeight: 700,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                          background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.25) 0%, rgba(14, 165, 233, 0.15) 100%)',
                          border: '1px solid rgba(56, 189, 248, 0.45)',
                          color: '#38bdf8',
                          cursor: 'pointer',
                          boxShadow: '0 2px 10px rgba(56, 189, 248, 0.2)',
                        }}
                      >
                        <Play size={11} fill="#38bdf8" />
                        <span>{testDictationStatus || 'Тест печати'}</span>
                      </button>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4 }}>
                      <Switch
                        checked={voiceSunderAutoEnter}
                        onChange={(checked) => updateVoiceSunderSetting('autoEnter', checked)}
                        size="sm"
                      />
                      <span style={{ fontSize: 12.5, color: '#cbd5e1', fontWeight: 500 }}>
                        Нажимать Enter после окончания диктовки
                      </span>
                    </div>
                  </div>
                </div>

                {/* Voice Commands Reference */}
                <div
                  style={{
                    padding: 18,
                    borderRadius: 16,
                    background: 'linear-gradient(135deg, rgba(20, 16, 36, 0.6) 0%, rgba(10, 8, 20, 0.8) 100%)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 10,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                    <Sparkles size={16} color="#fbbf24" />
                    <span style={{ fontSize: 13.5, fontWeight: 800, color: '#ffffff' }}>Голосовые команды быстрого вызова</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
                    <div
                      className="argus-plugin-card"
                      style={{
                        padding: '12px 14px',
                        borderRadius: 12,
                        background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(0, 0, 0, 0.4) 100%)',
                        border: '1px solid rgba(168, 85, 247, 0.3)',
                      }}
                    >
                      <div style={{ fontSize: 11.5, fontWeight: 800, color: '#c084fc', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Zap size={13} color="#c084fc" />
                        Обычный ввод
                      </div>
                      <div style={{ fontSize: 12, color: '#e2e8f0', marginTop: 4, fontWeight: 500 }}>«Аргус, напиши [текст]»</div>
                    </div>
                    <div
                      className="argus-plugin-card"
                      style={{
                        padding: '12px 14px',
                        borderRadius: 12,
                        background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.1) 0%, rgba(0, 0, 0, 0.4) 100%)',
                        border: '1px solid rgba(56, 189, 248, 0.3)',
                      }}
                    >
                      <div style={{ fontSize: 11.5, fontWeight: 800, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Send size={13} color="#38bdf8" />
                        С отправкой
                      </div>
                      <div style={{ fontSize: 12, color: '#e2e8f0', marginTop: 4, fontWeight: 500 }}>«Аргус, напечатай Привет и нажми enter»</div>
                    </div>
                    <div
                      className="argus-plugin-card"
                      style={{
                        padding: '12px 14px',
                        borderRadius: 12,
                        background: 'linear-gradient(135deg, rgba(74, 222, 128, 0.1) 0%, rgba(0, 0, 0, 0.4) 100%)',
                        border: '1px solid rgba(74, 222, 128, 0.3)',
                      }}
                    >
                      <div style={{ fontSize: 11.5, fontWeight: 800, color: '#4ade80', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Activity size={13} color="#4ade80" />
                        В приложения
                      </div>
                      <div style={{ fontSize: 12, color: '#e2e8f0', marginTop: 4, fontWeight: 500 }}>«Аргус, напиши в блокнот/тг [текст]»</div>
                    </div>
                  </div>
                </div>
              </div>
            ) : selectedPlugin.id === 'web_automator' ? (
              /* ─── WEB AUTOMATOR OFFICIAL DASHBOARD ─── */
              <div style={{ flex: 1, overflowY: 'auto', padding: '22px', display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div
                  style={{
                    padding: '18px 22px',
                    borderRadius: 16,
                    background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.16) 0%, rgba(168, 85, 247, 0.08) 100%)',
                    border: '1px solid rgba(56, 189, 248, 0.35)',
                    boxShadow: '0 8px 32px rgba(56, 189, 248, 0.12)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div
                      style={{
                        width: 46,
                        height: 46,
                        borderRadius: 14,
                        background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.3) 0%, rgba(14, 165, 233, 0.15) 100%)',
                        border: '1px solid rgba(56, 189, 248, 0.5)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#38bdf8',
                        boxShadow: '0 0 16px rgba(56, 189, 248, 0.35)',
                      }}
                    >
                      <Globe size={24} />
                    </div>
                    <div>
                      <h4 style={{ fontSize: 16, fontWeight: 800, color: '#ffffff' }}>
                        Web Automator
                      </h4>
                      <p style={{ fontSize: 12.5, color: '#94a3b8', marginTop: 2 }}>
                        Управление вкладками, клики по кнопкам сайтов, поиск в Google/YouTube/Яндекс
                      </p>
                    </div>
                  </div>
                  <span
                    style={{
                      fontSize: 11.5,
                      fontWeight: 800,
                      padding: '5px 12px',
                      borderRadius: 9999,
                      background: 'linear-gradient(135deg, rgba(74, 222, 128, 0.25) 0%, rgba(34, 197, 94, 0.15) 100%)',
                      color: '#4ade80',
                      border: '1px solid rgba(74, 222, 128, 0.45)',
                      boxShadow: '0 0 12px rgba(74, 222, 128, 0.2)',
                    }}
                  >
                    Активен
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                  <div
                    className="argus-plugin-card"
                    style={{
                      padding: 16,
                      borderRadius: 14,
                      background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.1) 0%, rgba(10, 8, 20, 0.8) 100%)',
                      border: '1px solid rgba(56, 189, 248, 0.3)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <Zap size={15} color="#38bdf8" />
                      <div style={{ fontSize: 13, fontWeight: 800, color: '#38bdf8' }}>Клики по кнопкам</div>
                    </div>
                    <p style={{ fontSize: 12, color: '#cbd5e1', lineHeight: 1.5 }}>
                      «Нажми кнопку Войти на странице», «Кликни на Корзина»
                    </p>
                  </div>
                  <div
                    className="argus-plugin-card"
                    style={{
                      padding: 16,
                      borderRadius: 14,
                      background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(10, 8, 20, 0.8) 100%)',
                      border: '1px solid rgba(168, 85, 247, 0.3)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <Layers size={15} color="#c084fc" />
                      <div style={{ fontSize: 13, fontWeight: 800, color: '#c084fc' }}>Вкладки и навигация</div>
                    </div>
                    <p style={{ fontSize: 12, color: '#cbd5e1', lineHeight: 1.5 }}>
                      «Закрой вкладку», «Новая вкладка», «Обнови страницу»
                    </p>
                  </div>
                  <div
                    className="argus-plugin-card"
                    style={{
                      padding: 16,
                      borderRadius: 14,
                      background: 'linear-gradient(135deg, rgba(74, 222, 128, 0.1) 0%, rgba(10, 8, 20, 0.8) 100%)',
                      border: '1px solid rgba(74, 222, 128, 0.3)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <Activity size={15} color="#4ade80" />
                      <div style={{ fontSize: 13, fontWeight: 800, color: '#4ade80' }}>Поиск и запросы</div>
                    </div>
                    <p style={{ fontSize: 12, color: '#cbd5e1', lineHeight: 1.5 }}>
                      «Найди на Wildberries кроссовки», «Поищи в YouTube»
                    </p>
                  </div>
                </div>
              </div>
            ) : selectedPlugin.id === 'system_optimizer' ? (
              /* ─── SYSTEM SENTINEL OFFICIAL DASHBOARD ─── */
              <div style={{ flex: 1, overflowY: 'auto', padding: '22px', display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div
                  style={{
                    padding: '18px 22px',
                    borderRadius: 16,
                    background: 'linear-gradient(135deg, rgba(74, 222, 128, 0.16) 0%, rgba(56, 189, 248, 0.08) 100%)',
                    border: '1px solid rgba(74, 222, 128, 0.35)',
                    boxShadow: '0 8px 32px rgba(74, 222, 128, 0.12)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div
                      style={{
                        width: 46,
                        height: 46,
                        borderRadius: 14,
                        background: 'linear-gradient(135deg, rgba(74, 222, 128, 0.3) 0%, rgba(34, 197, 94, 0.15) 100%)',
                        border: '1px solid rgba(74, 222, 128, 0.5)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#4ade80',
                        boxShadow: '0 0 16px rgba(74, 222, 128, 0.35)',
                      }}
                    >
                      <Cpu size={24} />
                    </div>
                    <div>
                      <h4 style={{ fontSize: 16, fontWeight: 800, color: '#ffffff' }}>
                        System Sentinel
                      </h4>
                      <p style={{ fontSize: 12.5, color: '#94a3b8', marginTop: 2 }}>
                        Очистка корзины, освобождение памяти, завершение зависших процессов
                      </p>
                    </div>
                  </div>
                  <span
                    style={{
                      fontSize: 11.5,
                      fontWeight: 800,
                      padding: '5px 12px',
                      borderRadius: 9999,
                      background: 'linear-gradient(135deg, rgba(74, 222, 128, 0.25) 0%, rgba(34, 197, 94, 0.15) 100%)',
                      color: '#4ade80',
                      border: '1px solid rgba(74, 222, 128, 0.45)',
                      boxShadow: '0 0 12px rgba(74, 222, 128, 0.2)',
                    }}
                  >
                    Активен
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                  <div
                    className="argus-plugin-card"
                    style={{
                      padding: 16,
                      borderRadius: 14,
                      background: 'linear-gradient(135deg, rgba(74, 222, 128, 0.1) 0%, rgba(10, 8, 20, 0.8) 100%)',
                      border: '1px solid rgba(74, 222, 128, 0.3)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <Activity size={15} color="#4ade80" />
                      <div style={{ fontSize: 13, fontWeight: 800, color: '#4ade80' }}>Очистка корзины</div>
                    </div>
                    <p style={{ fontSize: 12, color: '#cbd5e1', lineHeight: 1.5 }}>
                      «Очисти корзину» — моментальное высвобождение места
                    </p>
                  </div>
                  <div
                    className="argus-plugin-card"
                    style={{
                      padding: 16,
                      borderRadius: 14,
                      background: 'linear-gradient(135deg, rgba(248, 113, 113, 0.1) 0%, rgba(10, 8, 20, 0.8) 100%)',
                      border: '1px solid rgba(248, 113, 113, 0.3)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <Square size={15} color="#f87171" />
                      <div style={{ fontSize: 13, fontWeight: 800, color: '#f87171' }}>Закрытие программ</div>
                    </div>
                    <p style={{ fontSize: 12, color: '#cbd5e1', lineHeight: 1.5 }}>
                      «Закрой все программы кроме chrome»
                    </p>
                  </div>
                  <div
                    className="argus-plugin-card"
                    style={{
                      padding: 16,
                      borderRadius: 14,
                      background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.1) 0%, rgba(10, 8, 20, 0.8) 100%)',
                      border: '1px solid rgba(56, 189, 248, 0.3)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <ShieldCheck size={15} color="#38bdf8" />
                      <div style={{ fontSize: 13, fontWeight: 800, color: '#38bdf8' }}>Блокировка ПК</div>
                    </div>
                    <p style={{ fontSize: 12, color: '#cbd5e1', lineHeight: 1.5 }}>
                      «Заблокируй компьютер» — моментальная блокировка экрана
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              /* ─── CUSTOM USER PLUGIN: PROJECT TREE + MONACO CODE EDITOR ─── */
              <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                {/* Project File Tree */}
                <div
                  style={{
                    width: 260,
                    borderRight: '1px solid rgba(255, 255, 255, 0.08)',
                    background: 'rgba(6, 4, 14, 0.7)',
                    overflowY: 'auto',
                    padding: '12px 8px',
                  }}
                >
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', padding: '4px 8px', marginBottom: 4 }}>
                    Файлы проекта
                  </div>
                  {loadingTree ? (
                    <div style={{ textAlign: 'center', padding: '20px', color: '#94a3b8', fontSize: 11 }}>
                      Чтение файлов...
                    </div>
                  ) : treeData.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '20px', color: '#64748b', fontSize: 11 }}>
                      Нет файлов в проекте
                    </div>
                  ) : (
                    renderTreeNodes(treeData)
                  )}
                </div>

                {/* Code Editor / File Viewer */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#070512', overflow: 'hidden' }}>
                  {activeFile ? (
                    <>
                      {/* File Header */}
                      <div
                        style={{
                          padding: '8px 18px',
                          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                          background: 'rgba(15, 12, 28, 0.5)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <FileCode size={14} color="#fbbf24" />
                          <span style={{ fontSize: 12.5, fontWeight: 600, color: '#f1f5f9' }}>
                            {activeFile.path}
                          </span>
                          <span style={{ fontSize: 11, color: '#64748b' }}>({activeFile.size} байт)</span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <button
                            onClick={handleSaveFile}
                            disabled={savingFile}
                            style={{
                              padding: '4px 10px',
                              borderRadius: 6,
                              background: 'rgba(168, 85, 247, 0.2)',
                              border: '1px solid rgba(168, 85, 247, 0.4)',
                              color: '#c084fc',
                              fontSize: 11.5,
                              fontWeight: 700,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: 4,
                            }}
                          >
                            {fileSavedNotice ? <Check size={12} color="#4ade80" /> : <Save size={12} />}
                            <span>{fileSavedNotice ? 'Сохранено!' : savingFile ? 'Сохранение...' : 'Сохранить'}</span>
                          </button>
                        </div>
                      </div>

                      {/* Text Editor Textarea */}
                      <textarea
                        value={fileEditorContent}
                        onChange={(e) => setFileEditorContent(e.target.value)}
                        style={{
                          flex: 1,
                          background: '#06040d',
                          color: '#e2e8f0',
                          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
                          fontSize: 12.5,
                          lineHeight: 1.6,
                          padding: '16px',
                          border: 'none',
                          outline: 'none',
                          resize: 'none',
                          whiteSpace: 'pre',
                          overflowWrap: 'normal',
                          overflowX: 'auto',
                        }}
                        spellCheck={false}
                      />
                    </>
                  ) : (
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: 12 }}>
                      Выберите файл слева для просмотра и редактирования
                    </div>
                  )}
                </div>
              </div>
            )
          )}

          {/* Tab 2: Live Logs Terminal */}
          {activeTab === 'logs' && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#05030a', overflow: 'hidden' }}>
              <div
                style={{
                  padding: '8px 16px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: 11,
                  color: '#94a3b8',
                }}
              >
                <span>Консоль вывода процесса Python</span>
                <button
                  onClick={() => loadPluginLogs(selectedPlugin.id)}
                  style={{ background: 'transparent', border: 'none', color: '#c084fc', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
                >
                  <RefreshCw size={12} /> Обновить
                </button>
              </div>

              <pre
                style={{
                  flex: 1,
                  padding: '16px',
                  margin: 0,
                  overflowY: 'auto',
                  fontFamily: 'ui-monospace, monospace',
                  fontSize: 12,
                  color: '#f1f5f9',
                  lineHeight: 1.5,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {logsText || 'Логи отсутствуют.'}
              </pre>
            </div>
          )}
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
          Выберите плагин из списка слева
        </div>
      )}

      {/* ─── UPLOAD / CREATE PLUGIN MODAL ─────────────────────── */}
      {isUploadModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.7)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 99,
          }}
        >
          <div
            className="glass-card"
            style={{
              width: 520,
              padding: 26,
              borderRadius: 20,
              border: '1px solid rgba(255, 255, 255, 0.1)',
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Boxes size={20} color="#c084fc" />
                <h3 style={{ fontSize: 16, fontWeight: 800, color: '#ffffff' }}>Загрузить пользовательский плагин</h3>
              </div>
              <button
                onClick={() => setIsUploadModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Mode Selector */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
              {[
                { id: 'folder', label: 'Папка проекта' },
                { id: 'file', label: 'ZIP / Файл' },
                { id: 'code', label: 'Написать код' },
              ].map((m) => (
                <button
                  key={m.id}
                  onClick={() => setUploadMode(m.id as any)}
                  style={{
                    padding: '8px',
                    borderRadius: 10,
                    border: uploadMode === m.id ? '1px solid #a855f7' : '1px solid rgba(255, 255, 255, 0.08)',
                    background: uploadMode === m.id ? 'rgba(168, 85, 247, 0.2)' : 'rgba(255, 255, 255, 0.02)',
                    color: uploadMode === m.id ? '#ffffff' : '#94a3b8',
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {m.label}
                </button>
              ))}
            </div>

            <form onSubmit={handleCreateSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 4 }}>
                  Название плагина
                </label>
                <input
                  type="text"
                  value={pluginName}
                  onChange={(e) => setPluginName(e.target.value)}
                  placeholder="Мой бот автоматизации"
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 8,
                    background: '#0c0a18',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#ffffff',
                    fontSize: 13,
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 4 }}>
                  Точка входа (главный файл запуска)
                </label>
                <input
                  type="text"
                  value={entrypoint}
                  onChange={(e) => setEntrypoint(e.target.value)}
                  placeholder="main.py"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 8,
                    background: '#0c0a18',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#ffffff',
                    fontSize: 13,
                  }}
                />
              </div>

              {uploadMode === 'file' && (
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 4 }}>
                    Выберите ZIP архив проекта или .py файл
                  </label>
                  <input
                    type="file"
                    accept=".zip,.py"
                    onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
                    style={{ color: '#94a3b8', fontSize: 12 }}
                  />
                  <span style={{ fontSize: 11, color: '#64748b', marginTop: 4, display: 'block' }}>
                    При загрузке .zip архива все внутренние подпапки будут распакованы автоматически.
                  </span>
                </div>
              )}

              {uploadMode === 'folder' && (
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 4 }}>
                    Выберите папку проекта на компьютере (со всеми файлами и подпапками)
                  </label>
                  <input
                    type="file"
                    multiple
                    {...({ webkitdirectory: '', directory: '' } as any)}
                    onChange={(e) => {
                      if (e.target.files && e.target.files.length > 0) {
                        setFolderFiles(e.target.files);
                        if (!pluginName) {
                          const rel = (e.target.files[0] as any).webkitRelativePath || '';
                          const rootDir = rel.split('/')[0] || rel.split('\\')[0];
                          if (rootDir) setPluginName(rootDir);
                        }
                      }
                    }}
                    style={{ color: '#94a3b8', fontSize: 12 }}
                  />
                  {folderFiles && folderFiles.length > 0 && (
                    <div style={{ marginTop: 6, fontSize: 11, color: '#4ade80' }}>
                      Выбрано файлов: {folderFiles.length} (структура папок и подпапок будет сохранена полностью)
                    </div>
                  )}
                </div>
              )}

              {uploadMode === 'code' && (
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 4 }}>
                    Python скрипт
                  </label>
                  <textarea
                    value={customCode}
                    onChange={(e) => setCustomCode(e.target.value)}
                    rows={6}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 8,
                      background: '#0c0a18',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#ffffff',
                      fontSize: 12,
                      fontFamily: 'monospace',
                    }}
                  />
                </div>
              )}

              {errorMsg && (
                <div style={{ color: '#f87171', fontSize: 12 }}>{errorMsg}</div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
                <button
                  type="button"
                  onClick={() => setIsUploadModalOpen(false)}
                  className="btn-secondary"
                  style={{ padding: '8px 16px', borderRadius: 8, fontSize: 12 }}
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="btn-primary"
                  style={{ padding: '8px 18px', borderRadius: 8, fontSize: 12, fontWeight: 700 }}
                >
                  {creating ? 'Загрузка...' : 'Создать плагин'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
