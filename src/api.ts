import { UserProfile, ChatSession, ChatMessage, SystemStats, Scenario } from './types';

export const LOCAL_SERVER_URL = 'http://127.0.0.1:18274';
export const CLOUD_SERVER_URL = 'http://153.52.69.55:18274';

export let API_BASE = `${LOCAL_SERVER_URL}/api`;

let isLocalAvailable = true;

/**
 * Intelligent dual-target fetch:
 * Prioritizes local machine Python backend (127.0.0.1) for native OS controls,
 * GUI automation, Safari/Telegram integration, and offline speed.
 * Automatically fails over to central cloud server (153.52.69.55) if local backend is starting.
 */
export async function smartFetch(endpointPath: string, options: RequestInit = {}): Promise<Response> {
  const normPath = endpointPath.startsWith('/') ? endpointPath : `/${endpointPath}`;

  if (isLocalAvailable) {
    try {
      const controller = new AbortController();
      const signal = options.signal || controller.signal;
      const timer = setTimeout(() => controller.abort(), 2500);
      const res = await fetch(`${LOCAL_SERVER_URL}${normPath}`, { ...options, signal });
      clearTimeout(timer);
      isLocalAvailable = true;
      API_BASE = `${LOCAL_SERVER_URL}/api`;
      return res;
    } catch (err: any) {
      if (options.signal?.aborted) throw err;
      isLocalAvailable = false;
      console.warn(`[Argus API]: Local backend unreachable on ${normPath}, failing over to central cloud server.`);
    }
  }

  // Cloud failover
  try {
    const res = await fetch(`${CLOUD_SERVER_URL}${normPath}`, options);
    API_BASE = `${CLOUD_SERVER_URL}/api`;
    return res;
  } catch (cloudErr: any) {
    // If cloud also failed, try local one last time before giving up
    if (!isLocalAvailable) {
      try {
        const localRetry = await fetch(`${LOCAL_SERVER_URL}${normPath}`, options);
        isLocalAvailable = true;
        API_BASE = `${LOCAL_SERVER_URL}/api`;
        return localRetry;
      } catch {}
    }
    throw cloudErr;
  }
}

export async function verifyKey(keyCode: string): Promise<UserProfile> {
  const cleanKey = keyCode.trim();
  const payload = JSON.stringify({ key_code: cleanKey });
  const headers = { 'Content-Type': 'application/json' };

  // 1. Try local server first (1.5s timeout)
  try {
    const res = await fetch(`${LOCAL_SERVER_URL}/api/auth/verify-key`, {
      method: 'POST',
      headers,
      body: payload,
      signal: AbortSignal.timeout(1500)
    });
    if (res.ok) {
      isLocalAvailable = true;
      API_BASE = `${LOCAL_SERVER_URL}/api`;
      return res.json();
    }
    if (res.status === 401 || res.status === 403) {
      const err = await res.json().catch(() => ({ detail: 'Недействительный ключ доступа' }));
      const error: any = new Error(err.detail || 'Недействительный ключ доступа');
      error.isInvalidKey = true;
      throw error;
    }
  } catch (err: any) {
    if (err.isInvalidKey) throw err;
  }

  // 2. Cloud server fallback (8s timeout)
  try {
    const res = await fetch(`${CLOUD_SERVER_URL}/api/auth/verify-key`, {
      method: 'POST',
      headers,
      body: payload,
      signal: AbortSignal.timeout(8000)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Недействительный ключ доступа' }));
      const error: any = new Error(err.detail || 'Недействительный ключ доступа');
      if (res.status === 403 || res.status === 401) {
        error.isInvalidKey = true;
      }
      throw error;
    }
    return res.json();
  } catch (err: any) {
    if (err.isInvalidKey) throw err;
    if (err.name === 'AbortError' || err.message?.includes('timeout') || err.message?.includes('timed out')) {
      throw new Error('Сервер проверки ключей не отвечает. Проверьте интернет или введите ключ повторно.');
    }
    throw err;
  }
}

export async function fetchCurrentSession(): Promise<UserProfile | null> {
  const key = localStorage.getItem('argus_access_key') || '';
  const headers: Record<string, string> = {};
  if (key) headers['X-Argus-Key'] = key;

  // Try local first
  try {
    const res = await fetch(`${LOCAL_SERVER_URL}/api/auth/session`, {
      headers,
      signal: AbortSignal.timeout(1500)
    });
    if (res.ok) {
      const data = await res.json();
      if (data && data.valid) {
        isLocalAvailable = true;
        API_BASE = `${LOCAL_SERVER_URL}/api`;
        return data;
      }
    }
  } catch {}

  // Fallback to cloud
  try {
    const res = await fetch(`${CLOUD_SERVER_URL}/api/auth/session`, {
      headers,
      signal: AbortSignal.timeout(2500)
    });
    if (res.ok) {
      const data = await res.json();
      if (data && data.valid) return data;
    }
  } catch {}

  return null;
}

export async function logoutSession(): Promise<void> {
  try {
    await smartFetch('/api/auth/logout', { method: 'POST', signal: AbortSignal.timeout(2000) });
  } catch (e) {}
}

export async function updateProfile(keyCode: string, displayName: string, voiceEnabled = true, voiceSpeed = 1.0) {
  const res = await smartFetch('/api/profile/update', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Argus-Key': keyCode
    },
    body: JSON.stringify({
      key_code: keyCode,
      display_name: displayName,
      voice_enabled: voiceEnabled,
      voice_speed: voiceSpeed
    }),
    signal: AbortSignal.timeout(5000)
  });
  if (!res.ok) throw new Error('Ошибка обновления профиля');
  return res.json();
}

export async function fetchChats(keyCode: string): Promise<ChatSession[]> {
  const res = await smartFetch('/api/chats', {
    headers: {
      'Content-Type': 'application/json',
      'X-Argus-Key': keyCode
    },
    signal: AbortSignal.timeout(4000)
  });
  if (!res.ok) throw new Error('Ошибка загрузки чатов');
  return res.json();
}

export async function createChatSession(keyCode: string, title = 'Новый диалог'): Promise<ChatSession> {
  const res = await smartFetch('/api/chats/create', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Argus-Key': keyCode
    },
    body: JSON.stringify({ key_code: keyCode, title }),
    signal: AbortSignal.timeout(4000)
  });
  if (!res.ok) throw new Error('Ошибка создания чата');
  return res.json();
}

export async function renameChatSession(chatId: string, keyCode: string, title: string): Promise<boolean> {
  const res = await smartFetch(`/api/chats/${chatId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-Argus-Key': keyCode
    },
    body: JSON.stringify({ key_code: keyCode, title })
  });
  return res.ok;
}

export async function deleteChatSession(chatId: string, keyCode: string): Promise<boolean> {
  const res = await smartFetch(`/api/chats/${chatId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-Argus-Key': keyCode
    }
  });
  return res.ok;
}

export async function fetchMessages(chatId: string): Promise<ChatMessage[]> {
  const res = await smartFetch(`/api/chats/${chatId}/messages`);
  if (!res.ok) throw new Error('Ошибка загрузки сообщений');
  return res.json();
}

export async function sendChatMessage(chatId: string, keyCode: string, message: string, voice = true, signal?: AbortSignal) {
  const res = await smartFetch('/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal,
    body: JSON.stringify({
      chat_id: chatId,
      key_code: keyCode,
      message,
      voice
    })
  });
  if (!res.ok) throw new Error('Ошибка отправки сообщения');
  return res.json();
}

export async function getSystemStats(): Promise<SystemStats> {
  const res = await smartFetch('/api/system/stats');
  if (!res.ok) throw new Error('Ошибка получения метрик системы');
  return res.json();
}

export async function setVolume(params: { level?: number; delta?: number; mute_toggle?: boolean }) {
  const res = await smartFetch('/api/system/volume', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  return res.json();
}

export async function setBrightness(params: { level?: number; delta?: number }) {
  const res = await smartFetch('/api/system/brightness', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  return res.json();
}

export async function launchApp(app: string) {
  const res = await smartFetch('/api/system/launch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ app })
  });
  return res.json();
}

export async function mediaAction(action: string) {
  const res = await smartFetch('/api/system/media', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action })
  });
  return res.json();
}

export async function lockPC() {
  const res = await smartFetch('/api/system/lock', { method: 'POST' });
  return res.json();
}

// ─── PLUGINS SYSTEM API ──────────────────────────────────────────
export async function fetchPlugins(): Promise<any[]> {
  const res = await smartFetch('/api/plugins');
  if (!res.ok) throw new Error('Ошибка получения списка плагинов');
  return res.json();
}

export async function createPlugin(formData: FormData): Promise<any> {
  const res = await smartFetch('/api/plugins/create', {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Ошибка создания плагина' }));
    throw new Error(err.detail || 'Не удалось создать плагин');
  }
  return res.json();
}

export async function startPlugin(pluginId: string): Promise<any> {
  const res = await smartFetch(`/api/plugins/${pluginId}/start`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Ошибка запуска плагина' }));
    throw new Error(err.detail || 'Не удалось запустить плагин');
  }
  return res.json();
}

export async function stopPlugin(pluginId: string): Promise<any> {
  const res = await smartFetch(`/api/plugins/${pluginId}/stop`, { method: 'POST' });
  return res.json();
}

export async function fetchPluginLogs(pluginId: string): Promise<{ logs: string }> {
  const res = await smartFetch(`/api/plugins/${pluginId}/logs`);
  if (!res.ok) return { logs: 'Ошибка загрузки логов' };
  return res.json();
}

export async function deletePlugin(pluginId: string): Promise<any> {
  const res = await smartFetch(`/api/plugins/${pluginId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Ошибка удаления плагина');
  return res.json();
}

export async function fetchPluginTree(pluginId: string): Promise<any> {
  const res = await smartFetch(`/api/plugins/${pluginId}/tree`);
  if (!res.ok) throw new Error('Ошибка чтения структуры проекта');
  return res.json();
}

export async function fetchPluginFile(pluginId: string, filePath: string): Promise<any> {
  const res = await smartFetch(`/api/plugins/${pluginId}/file?path=${encodeURIComponent(filePath)}`);
  if (!res.ok) throw new Error('Ошибка чтения файла');
  return res.json();
}

export async function savePluginFile(pluginId: string, filePath: string, content: string): Promise<any> {
  const res = await smartFetch(`/api/plugins/${pluginId}/file`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: filePath, content })
  });
  if (!res.ok) throw new Error('Ошибка сохранения файла');
  return res.json();
}

export async function setPluginEntrypoint(pluginId: string, entrypoint: string): Promise<any> {
  const res = await smartFetch(`/api/plugins/${pluginId}/entrypoint`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entrypoint })
  });
  if (!res.ok) throw new Error('Ошибка установки точки входа');
  return res.json();
}

// ─── SETTINGS & SYSTEM APIS ──────────────────────────────────────
export async function fetchSettings(): Promise<any> {
  const res = await smartFetch('/api/settings');
  if (!res.ok) throw new Error('Ошибка загрузки настроек');
  return res.json();
}

export async function updateSettings(data: any): Promise<any> {
  const res = await smartFetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error('Ошибка сохранения настроек');
  return res.json();
}

export async function fetchInstalledBrowsers(): Promise<any[]> {
  const res = await smartFetch('/api/system/browsers');
  if (!res.ok) return [];
  return res.json();
}

export async function executeTerminal(command: string, shell?: string): Promise<any> {
  const res = await smartFetch('/api/terminal/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command, shell })
  });
  if (!res.ok) throw new Error('Ошибка выполнения терминала');
  return res.json();
}

export async function getTerminalAIAssistant(prompt: string, osTarget?: string): Promise<any> {
  const res = await smartFetch('/api/terminal/ai-assistant', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, os_target: osTarget })
  });
  if (!res.ok) throw new Error('Ошибка ИИ помощника терминала');
  return res.json();
}

export async function testFishAudio(apiKey: string, modelId?: string, text?: string): Promise<any> {
  const res = await smartFetch('/api/voice/test-fish', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey, model_id: modelId, text })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Ошибка генерации' }));
    throw new Error(err.detail || 'Не удалось проверить Fish Audio');
  }
  return res.json();
}

export async function dictateVoiceSunder(text: string, pressEnter = false): Promise<any> {
  const res = await smartFetch('/api/plugins/voice-sunder/dictate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, press_enter: pressEnter })
  });
  return res.json();
}

// ─── SCENARIOS & WORKFLOWS ──────────────────────────────────────
export async function fetchScenarios(): Promise<Scenario[]> {
  const res = await smartFetch('/api/scenarios');
  if (!res.ok) throw new Error('Ошибка загрузки сценариев');
  return res.json();
}

export async function saveScenario(scenario: Partial<Scenario>): Promise<Scenario> {
  const res = await smartFetch('/api/scenarios', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(scenario),
  });
  if (!res.ok) throw new Error('Ошибка сохранения сценария');
  return res.json();
}

export async function deleteScenario(scenarioId: string): Promise<any> {
  const res = await smartFetch(`/api/scenarios/${scenarioId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Ошибка удаления сценария');
  return res.json();
}

export async function runScenario(scenarioId: string): Promise<any> {
  const res = await smartFetch(`/api/scenarios/${scenarioId}/run`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Ошибка выполнения сценария');
  return res.json();
}
