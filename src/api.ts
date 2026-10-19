import { UserProfile, ChatSession, ChatMessage, SystemStats, Scenario } from './types';

const API_BASE = 'http://127.0.0.1:18274/api';

export async function verifyKey(keyCode: string): Promise<UserProfile> {
  try {
    const res = await fetch(`${API_BASE}/auth/verify-key`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key_code: keyCode }),
      signal: AbortSignal.timeout(8000)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Ошибка проверки ключа' }));
      const error: any = new Error(err.detail || 'Неверный ключ доступа');
      if (res.status === 403 || res.status === 401) {
        error.isInvalidKey = true;
      }
      throw error;
    }
    return res.json();
  } catch (err: any) {
    if (err.name === 'AbortError' || err.message?.includes('timeout') || err.message?.includes('timed out')) {
      throw new Error('Сервер проверки ключей не отвечает. Проверьте интернет или введите ключ повторно.');
    }
    throw err;
  }
}

export async function fetchCurrentSession(): Promise<UserProfile | null> {
  try {
    const key = localStorage.getItem('argus_access_key') || '';
    const headers: Record<string, string> = {};
    if (key) headers['X-Argus-Key'] = key;
    const res = await fetch(`${API_BASE}/auth/session`, {
      headers,
      signal: AbortSignal.timeout(2000)
    });
    if (res.ok) {
      const data = await res.json();
      if (data && data.valid) return data;
    }
  } catch (e) {}
  return null;
}

export async function logoutSession(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/logout`, { method: 'POST', signal: AbortSignal.timeout(2000) });
  } catch (e) {}
}

export async function updateProfile(keyCode: string, displayName: string, voiceEnabled = true, voiceSpeed = 1.0) {
  const res = await fetch(`${API_BASE}/profile/update`, {
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
  const res = await fetch(`${API_BASE}/chats`, {
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
  const res = await fetch(`${API_BASE}/chats/create`, {
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
  const res = await fetch(`${API_BASE}/chats/${chatId}`, {
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
  const res = await fetch(`${API_BASE}/chats/${chatId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-Argus-Key': keyCode
    }
  });
  return res.ok;
}

export async function fetchMessages(chatId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${API_BASE}/chats/${chatId}/messages`);
  if (!res.ok) throw new Error('Ошибка загрузки сообщений');
  return res.json();
}

export async function sendChatMessage(chatId: string, keyCode: string, message: string, voice = true, signal?: AbortSignal) {
  const res = await fetch(`${API_BASE}/ai/chat`, {
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
  const res = await fetch(`${API_BASE}/system/stats`);
  if (!res.ok) throw new Error('Ошибка получения метрик системы');
  return res.json();
}

export async function setVolume(params: { level?: number; delta?: number; mute_toggle?: boolean }) {
  const res = await fetch(`${API_BASE}/system/volume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  return res.json();
}

export async function setBrightness(params: { level?: number; delta?: number }) {
  const res = await fetch(`${API_BASE}/system/brightness`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  return res.json();
}

export async function launchApp(app: string) {
  const res = await fetch(`${API_BASE}/system/launch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ app })
  });
  return res.json();
}

export async function mediaAction(action: string) {
  const res = await fetch(`${API_BASE}/system/media`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action })
  });
  return res.json();
}

export async function lockPC() {
  const res = await fetch(`${API_BASE}/system/lock`, { method: 'POST' });
  return res.json();
}

// ─── PLUGINS SYSTEM API ──────────────────────────────────────────
export async function fetchPlugins(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/plugins`);
  if (!res.ok) throw new Error('Ошибка получения списка плагинов');
  return res.json();
}

export async function createPlugin(formData: FormData): Promise<any> {
  const res = await fetch(`${API_BASE}/plugins/create`, {
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
  const res = await fetch(`${API_BASE}/plugins/${pluginId}/start`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Ошибка запуска плагина' }));
    throw new Error(err.detail || 'Не удалось запустить плагин');
  }
  return res.json();
}

export async function stopPlugin(pluginId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/plugins/${pluginId}/stop`, { method: 'POST' });
  return res.json();
}

export async function fetchPluginLogs(pluginId: string): Promise<{ logs: string }> {
  const res = await fetch(`${API_BASE}/plugins/${pluginId}/logs`);
  if (!res.ok) return { logs: 'Ошибка загрузки логов' };
  return res.json();
}

export async function deletePlugin(pluginId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/plugins/${pluginId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Ошибка удаления плагина');
  return res.json();
}

export async function fetchPluginTree(pluginId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/plugins/${pluginId}/tree`);
  if (!res.ok) throw new Error('Ошибка чтения структуры проекта');
  return res.json();
}

export async function fetchPluginFile(pluginId: string, filePath: string): Promise<any> {
  const res = await fetch(`${API_BASE}/plugins/${pluginId}/file?path=${encodeURIComponent(filePath)}`);
  if (!res.ok) throw new Error('Ошибка чтения файла');
  return res.json();
}

export async function savePluginFile(pluginId: string, filePath: string, content: string): Promise<any> {
  const res = await fetch(`${API_BASE}/plugins/${pluginId}/file`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: filePath, content })
  });
  if (!res.ok) throw new Error('Ошибка сохранения файла');
  return res.json();
}

export async function setPluginEntrypoint(pluginId: string, entrypoint: string): Promise<any> {
  const res = await fetch(`${API_BASE}/plugins/${pluginId}/entrypoint`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entrypoint })
  });
  if (!res.ok) throw new Error('Ошибка установки точки входа');
  return res.json();
}

// ─── SETTINGS & SYSTEM APIS ──────────────────────────────────────
export async function fetchSettings(): Promise<any> {
  const res = await fetch(`${API_BASE}/settings`);
  if (!res.ok) throw new Error('Ошибка загрузки настроек');
  return res.json();
}

export async function updateSettings(data: any): Promise<any> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error('Ошибка сохранения настроек');
  return res.json();
}

export async function fetchInstalledBrowsers(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/system/browsers`);
  if (!res.ok) return [];
  return res.json();
}

export async function executeTerminal(command: string, shell?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/terminal/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command, shell })
  });
  if (!res.ok) throw new Error('Ошибка выполнения терминала');
  return res.json();
}

export async function getTerminalAIAssistant(prompt: string, osTarget?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/terminal/ai-assistant`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, os_target: osTarget })
  });
  if (!res.ok) throw new Error('Ошибка ИИ помощника терминала');
  return res.json();
}

export async function testFishAudio(apiKey: string, modelId?: string, text?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/test-fish`, {
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
  const res = await fetch(`${API_BASE}/plugins/voice-sunder/dictate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, press_enter: pressEnter })
  });
  return res.json();
}

// ─── SCENARIOS & WORKFLOWS ──────────────────────────────────────
export async function fetchScenarios(): Promise<Scenario[]> {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) throw new Error('Ошибка загрузки сценариев');
  return res.json();
}

export async function saveScenario(scenario: Partial<Scenario>): Promise<Scenario> {
  const res = await fetch(`${API_BASE}/scenarios`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(scenario),
  });
  if (!res.ok) throw new Error('Ошибка сохранения сценария');
  return res.json();
}

export async function deleteScenario(scenarioId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/scenarios/${scenarioId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Ошибка удаления сценария');
  return res.json();
}

export async function runScenario(scenarioId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/scenarios/${scenarioId}/run`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Ошибка выполнения сценария');
  return res.json();
}


