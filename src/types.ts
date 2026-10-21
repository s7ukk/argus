export interface UserProfile {
  valid: boolean;
  key_code: string;
  tier: string;
  assigned_to: string;
  display_name: string;
  voice_enabled: boolean;
  voice_speed: number;
  theme: string;
  expires_at: string;
  days_left: number;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  action_type?: string;
  action_data?: any;
  created_at: string;
  audio_base64?: string;
}

export interface SystemStats {
  os?: string;
  disk_label?: string;
  cpu: {
    percent: number;
    cores: number;
    freq_mhz: number;
    model?: string;
  };
  memory: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
  };
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
  };
  battery: {
    percent: number;
    power_plugged: boolean;
    secsleft: number | null;
  } | null;
  volume: number;
  brightness: number;
}

export interface PluginInfo {
  id: string;
  name: string;
  description: string;
  entrypoint: string;
  created_at: number;
  status: 'running' | 'stopped' | 'error';
  pid?: number | null;
  memory_mb?: number;
  cpu_percent?: number;
  has_logs?: boolean;
  files_count?: number;
  auto_heal_enabled?: boolean;
  is_official?: boolean;
  author?: string;
  version?: string;
}

export interface PluginTreeItem {
  name: string;
  type: 'file' | 'directory';
  path: string;
  size?: number;
  ext?: string;
  is_entrypoint?: boolean;
  children?: PluginTreeItem[];
}

export interface PluginTreeResponse {
  id: string;
  entrypoint: string;
  root: string;
  tree: PluginTreeItem[];
}

export interface PluginFileResponse {
  path: string;
  content: string;
  size: number;
  lang: string;
}

export interface BrowserInfo {
  id: string;
  name: string;
  path: string;
}

export interface AppSettings {
  voice_input_mode: 'trigger' | 'ptt' | 'click';
  trigger_words: string;
  ptt_hotkey: string;
  voice_provider: 'edge-tts' | 'fish-audio';
  fish_api_key: string;
  fish_model_id: string;
  edge_voice: string;
  voice_speed: number;
  browser_mode: 'ask' | 'default';
  default_browser: string;
  auto_heal_plugins: boolean;
  default_shell: string;
}

export interface TerminalExecResult {
  success: boolean;
  exit_code: number;
  output: string;
  error: string;
  duration_ms: number;
  os: string;
}

export interface TerminalAIAssistantResult {
  command: string;
  description: string;
  shell: string;
  os: string;
}

export interface ScenarioStep {
  type: string;
  label?: string;
  prompt?: string;
  command?: string;
  level?: number;
  delta?: number;
  app?: string;
  service?: string;
  query?: string;
  playlist?: string;
  action?: string;
  url?: string;
  folder?: string;
  keep?: string[];
}

export interface Scenario {
  id: string;
  name: string;
  icon?: string;
  triggers: string[];
  description?: string;
  custom_prompt?: string;
  is_builtin?: boolean;
  steps: ScenarioStep[];
}

export type NavTab = 'chat' | 'scenarios' | 'plugins' | 'system' | 'about' | 'settings';
