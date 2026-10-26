"""
Argus AI — OpenRouter Free Neural Reasoning & Desktop Control Engine
Provides high-intelligence multimodal reasoning, deep coding/task assistance,
and autonomous computer execution using free OpenRouter models.
Key is loaded securely from .env and never exposed.
"""

import os
import sys
import re
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

import backend.app_paths as app_paths

_OPENROUTER_CACHE: Dict[str, Tuple[str, List[Dict[str, Any]]]] = {}
_LAST_KEY: Optional[str] = None

# Model settings & User configuration
FREE_PRIMARY_MODEL = "meta-llama/llama-3.3-70b-instruct"
FREE_FALLBACK_MODELS = [
    "meta-llama/llama-3.3-70b-instruct",
    "google/gemini-2.0-flash-001",
    "deepseek/deepseek-chat",
    "qwen/qwen-2.5-coder-32b-instruct",
    "mistralai/mistral-small-24b-instruct-2501",
    "openrouter/free"
]

def get_user_settings_api_key_and_model() -> Tuple[Optional[str], Optional[str]]:
    """Retrieves user custom openrouter key and model from settings.json if configured."""
    try:
        settings_path = os.path.join(app_paths.get_argus_data_dir(), "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                s = json.load(f)
                k = (s.get("openrouter_api_key") or "").strip()
                m = (s.get("openrouter_model") or "").strip()
                return (k if len(k) > 10 else None), (m if m else None)
    except Exception:
        pass
    return None, None

def load_openrouter_api_keys() -> List[str]:
    """
    Safely retrieves all OPENROUTER_API_KEYs from settings.json, environment or .env files.
    User configured key takes top priority.
    """
    found_keys = []
    
    # 0. User configured key in Settings
    u_key, _ = get_user_settings_api_key_and_model()
    if u_key and u_key not in found_keys:
        found_keys.append(u_key)
    
    # 1. Environment variables
    for env_var in ["OPENROUTER_API_KEY", "OPENROUTER_API_KEYS", "OPENROUTER_KEY"]:
        val = os.getenv(env_var)
        if val and val.strip() and val.strip() != "your_openrouter_api_key_here":
            for part in val.replace("\n", ",").split(","):
                part = part.strip().strip('"').strip("'")
                if part and len(part) > 15 and part not in found_keys:
                    found_keys.append(part)

    # 2. Candidate .env file locations
    candidates = [
        os.path.join(os.getenv("ARGUS_RESOURCES_PATH") or "", ".env"),
        os.path.join(os.getcwd(), ".env"),
        os.path.join(app_paths.get_argus_data_dir(), ".env"),
        os.path.join(os.path.expanduser("~"), ".argus", ".env"),
        os.path.join(os.getenv("APPDATA") or "", "argus-ai", ".env"),
        os.path.join(os.getenv("APPDATA") or "", "ArgusAI", ".env"),
        os.path.join(os.getenv("LOCALAPPDATA") or "", "Programs", "Argus AI", "resources", ".env"),
        os.path.expanduser("~/Library/Application Support/ArgusAI/.env"),
        os.path.expanduser("~/Library/Application Support/argus-ai/.env"),
        "/Applications/Argus AI.app/Contents/Resources/.env",
        os.path.join(getattr(sys, "_MEIPASS", ""), ".env") if hasattr(sys, "_MEIPASS") else None,
    ]

    curr_exe = os.path.abspath(sys.executable)
    for _ in range(6):
        curr_exe = os.path.dirname(curr_exe)
        candidates.append(os.path.join(curr_exe, ".env"))
        candidates.append(os.path.join(curr_exe, "resources", ".env"))
        candidates.append(os.path.join(curr_exe, "Resources", ".env"))

    curr_file = os.path.abspath(__file__)
    for _ in range(6):
        curr_file = os.path.dirname(curr_file)
        candidates.append(os.path.join(curr_file, ".env"))
        candidates.append(os.path.join(curr_file, "resources", ".env"))
        candidates.append(os.path.join(curr_file, "Resources", ".env"))

    for cand in candidates:
        if cand and os.path.isfile(cand):
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("OPENROUTER_API_KEY") or line.startswith("OPENROUTER_KEY"):
                            raw_val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            for part in raw_val.replace("\n", ",").split(","):
                                part = part.strip().strip('"').strip("'")
                                if part and len(part) > 15 and part != "your_openrouter_api_key_here" and part not in found_keys:
                                    found_keys.append(part)
            except Exception:
                pass

    return found_keys

def load_openrouter_api_key() -> Optional[str]:
    """Safely retrieves the primary active OPENROUTER_API_KEY."""
    keys = load_openrouter_api_keys()
    if keys:
        os.environ["OPENROUTER_API_KEY"] = keys[0]
        return keys[0]
    return None

def build_system_prompt(user_name: str, os_name: str, memory_summary: str = "") -> str:
    """Builds comprehensive system instructions training the AI on full computer control and assistance."""
    return f"""Ты — Argus, высокоинтеллектуальный цифровой дворецкий и автономный ассистент управления компьютером ({os_name}).
Пользователь: {user_name}.
{memory_summary}

ОСНОВНЫЕ ПРАВИЛА И СТИЛЬ:
1. ОБРАЩЕНИЕ И ТОН:
   - ВСЕГДА общайся вежливо, спокойно, уверенно и профессионально на «Вы» (без фамильярного «ты»).
   - КАТЕГОРИЧЕСКИ НЕ НУЖНО повторять «сэр» в каждом ответе! Слово «сэр» используй ОЧЕНЬ РЕДКО (не чаще 1 раза за диалог и только к месту, либо не используй вовсе). Обычные ответы должны звучать живо, естественно и без искусственных повторений.
2. СТРОГО БЕЗ ЭМОДЗИ (никаких смайлов, значков и эмодзи в тексте ответа).
3. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО перечислять список своих возможностей, функций или шаблоны резюме («я умею писать код, искать информацию, управлять программами...»). Пользователь уже знает, кто ты. Не трать время пользователя!
4. НА ВОПРОСЫ О СТАТУСЕ И ПРИВЕТСТВИЯ («привет», «приве», «что делаешь», «как дела», «чем занят»):
   Отвечай ЖИВО, ТЕПЛО, ОСТРОУМНО, ЕСТЕСТВЕННО И ВСЕГДА ПО-РАЗНОМУ, как умный персональный собеседник и дворецкий высшего класса.
   КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО повторять одни и те же заученные фразы («На связи. Жду Ваших распоряжений.», «Все системы работают в штатном режиме»).
   Формулируй каждый ответ свежо, оригинально, в 1-2 живых предложения, показывая готовность решить любую задачу пользователя (на {os_name}).
5. ВЫПОЛНЕНИЕ КОМАНД В ПРИЛОЖЕНИЯХ И НА КОМПЬЮТЕРЕ:
   Когда пользователь приказывает сделать что-то в приложении или на компьютере («открой телеграм и найди чат», «включи музыку в спотифай», «закрой браузер», «сделай скриншот»):
   - Если пользователь допускает опечатки («бразуер», «спотифий», «телегарм», «дискрод», «хромчик»), безошибочно понимай его намерение и запускай правильное приложение (браузер -> launch_app: chrome, спотифай -> spotify, телеграм -> telegram).
   - СРАЗУ добавляй нужные команды в массив 'actions'!
   - В поле 'reply' давай только КРАТКОЕ, уверенное, естественное подтверждение на 1 короткую фразу (НЕ длинный отчет!): «Открываю Telegram.», «Вкладка закрыта.», «Скриншот сохранен.».
6. ЛИЧНЫЕ ДАННЫЕ И ЗАМЕТКИ ПОЛЬЗОВАТЕЛЯ:
   - Личные заметки содержат личную конфиденциальную информацию пользователя.
   - ИСПОЛЬЗУЙ ИХ ТОЛЬКО И ИСКЛЮЧИТЕЛЬНО тогда, когда пользователь ЯВНО спрашивает о своих сохраненных данных («что у меня в заметках», «напомни мой пароль», «какой у меня адрес», «что я записал»).
   - ЕСЛИ ПОЛЬЗОВАТЕЛЬ ПРОСИТ РАССКАЗАТЬ ИСТОРИЮ, СКАЗКУ, АНЕКДОТ, ФАКТ («расскажи историю», «расскажи интересную историю», «сочини рассказ», «случайную историю») — КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать или пересказывать текст из заметок! Вместо этого ВСЕГДА сочини и расскажи совершенно новую, случайную, увлекательную и оригинальную историю сам!
7. КОД И ТЕХНИЧЕСКИЕ ВОПРОСЫ:
   - Если пользователь просит написать код, программу, скрипт, бэкенд, функцию, архитектуру или задает технический вопрос (например, на Elixir, Rust, Python, Go, C++, JS):
   - ВСЕГДА оборачивай ВЕСЬ программный код в блоки c тройными обратными кавычками ```<название_языка>\nкод\n``` (например, ```elixir\n...\n```, ```rust\n...\n```, ```python\n...\n```, ```go\n...\n```, ```cpp\n...\n```).
   - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО добавлять действия (actions) запуска программ или воспроизведения музыки при запросе кода! Массив 'actions' должен быть строго пустым [].
   - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать название языка без трёх открывающих обратных кавычек ```! Каждый блок кода ОБЯЗАТЕЛЬНО должен начинаться с ```<язык> и заканчиваться ```.
   - Пиши качественный, полный, рабочий и готовый к компиляции/запуску код.

ФОРМАТ ОТВЕТА:
1. ЕСЛИ НУЖНО ВЫПОЛНИТЬ ДЕЙСТВИЕ НА КОМПЬЮТЕРЕ (запустить программу, закрыть окно/вкладку, сделать скриншот, поставить таймер, нажать клавиши, управлять звуком):
Верни ответ строго в формате JSON:
{{
  "reply": "Краткое подтверждение действия пользователю на русском языке на «Вы» строго БЕЗ ЭМОДЗИ",
  "actions": [
    {{"type": "...", ...}}
  ]
}}

2. ЕСЛИ ДЕЙСТВИЕ НА КОМПЬЮТЕРЕ НЕ ТРЕБУЕТСЯ (пользователь просит написать код, программу, скрипт, объяснить что-либо, рассказать историю или задает вопрос):
ОТВЕЧАЙ НАПРЯМУЮ ОБЫЧНЫМ ТЕКСТОМ (MARKDOWN) С БЛОКАМИ КОДА ```язык ... ```, КАТЕГОРИЧЕСКИ БЕЗ ОБЁРТКИ В JSON И БЕЗ ПОЛЯ ACTIONS!

ПРАВИЛА И ТИПЫ ДЕЙСТВИЙ:
1. Если пользователь задает вопрос, просит совета, кода, объяснения или ведет диалог — отвечай развернуто, умно и по делу в поле 'reply', а поле 'actions' оставь пустым массивом [].
2. Если требуется действие с компьютером, добавь действия в массив 'actions'.
3. Доступные типы действий:
   - launch_app: {{"type": "launch_app", "app": "название_программы"}}
   - close_app: {{"type": "close_app", "app": "название_программы"}}
   - close_all_except: {{"type": "close_all_except", "keep": ["код", "браузер"]}}
   - open_url: {{"type": "open_url", "url": "https://..."}}
   - search_web: {{"type": "search_web", "query": "...", "engine": "google" | "yandex" | "youtube"}}
   - click_website_button: {{"type": "click_website_button", "button": "текст кнопки"}}
   - browser_tab: {{"type": "browser_tab", "action": "new" | "close" | "next" | "prev" | "refresh"}}
   - close_all_browser_tabs: {{"type": "close_all_browser_tabs"}}
   - scroll_page: {{"type": "scroll_page", "direction": "down" | "up"}}
   - type_text: {{"type": "type_text", "text": "текст для ввода", "press_enter": true/false}}
   - press_key: {{"type": "press_key", "key": "enter" | "esc" | "tab" | "space"}}
   - hotkey: {{"type": "hotkey", "keys": ["ctrl", "c"]}}
   - create_file: {{"type": "create_file", "path": "имя_файла.txt", "content": "содержимое"}}
   - create_folder: {{"type": "create_folder", "path": "имя_папки"}}
   - delete_file: {{"type": "delete_file", "path": "имя_файла"}}
   - analyze_file: {{"type": "analyze_file", "path": "имя_файла"}}
   - list_files: {{"type": "list_files", "folder": "desktop" | "downloads" | "documents"}}
   - screenshot: {{"type": "screenshot", "folder": "desktop"}}
   - volume: {{"type": "volume", "action": "up" | "down" | "mute" | "unmute" | "set", "level": 50}}
   - brightness: {{"type": "brightness", "action": "up" | "down" | "set", "level": 80}}
   - play_music: {{"type": "play_music", "action": "play" | "pause" | "next" | "prev", "query": "трек"}}
   - empty_recycle: {{"type": "empty_recycle"}}
   - lock_pc: {{"type": "lock_pc"}}
   - system_stats: {{"type": "system_stats"}}
   - terminal_command: {{"type": "terminal_command", "command": "...", "shell": "powershell" | "bash"}}
   - messenger_send: {{"type": "messenger_send", "messenger": "telegram" | "discord" | "whatsapp" | "auto", "contact": "имя", "message": "текст"}}
   - create_timer: {{"type": "create_timer", "title": "название", "seconds": 420}}
   - delete_timer: {{"type": "delete_timer", "title": "название" | "all"}}
   - create_task: {{"type": "create_task", "title": "название задачи", "category": "учёба" | "работа" | "личное"}}
   - delete_task: {{"type": "delete_task", "title": "название задачи"}}
   - complete_task: {{"type": "complete_task", "title": "название задачи"}}
   - create_note: {{"type": "create_note", "title": "заголовок", "content": "содержимое"}}
   - delete_note: {{"type": "delete_note", "title": "заголовок"}}

4. ДЕЙСТВИЯ С ВКЛАДКАМИ И ОКНАМИ:
   - Для закрытия одной вкладки используй action: 'close_browser_tab' (или browser_tab с action: 'close').
   - Для закрытия всех вкладок используй action: 'close_all_browser_tabs'.
   - Для закрытия конкретной программы используй action: 'close_app'.
5. ФОРМАТ И СТИЛЬ:
   - Возвращай ТОЛЬКО чистый JSON строго формата {{"reply": "...", "actions": [...]}}.
   - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО выводить рассуждения, шаги анализа или черновики (Analyze the Request, Thinking, Constraints, Looking at the personal notes и т.д.). Сразу готовый результат!
   - ФОРМАТИРОВАНИЕ МАТЕМАТИКИ: Не используй сырой LaTeX, пиши понятным читаемым текстом.
   - НАПИСАНИЕ КОДА: Если пользователь просит написать код, программу, скрипт или бота — пиши полный, готовый к запуску код внутри блока ```<язык> ... ``` в поле 'reply', с инструкцией по установке и запуску, поле 'actions' оставляй пустым [].
   - ОТПРАВКА СООБЩЕНИЙ: Если пользователь просит отправить сообщение, но не указал имя контакта/username или текст сообщения — вежливо переспроси на «Вы» с добавлением «сэр». Уточни мессенджер (Telegram, WhatsApp, Discord, VK), контакт/username и текст сообщения.
6. ПРАВИЛО БЕЗОПАСНОСТИ:
   - Любые операции отправки сообщений, удаления данных (файлов, папок, заметок, корзина) или финансовой оплаты/покупки перед физическим исполнением требуют подтверждения пользователя.
"""

def query_openrouter(
    prompt: str,
    user_name: str = "Пользователь",
    history: Optional[List[Dict[str, Any]]] = None,
    system_override: Optional[str] = None
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Executes a high-intelligence query against OpenRouter's free catalog.
    Returns: (ai_reply_text, list_of_actions)
    """
    key = load_openrouter_api_key()
    if not key:
        return None, []

    cache_key = f"{prompt.strip().lower()}_{user_name}"
    if not history and cache_key in _OPENROUTER_CACHE:
        return _OPENROUTER_CACHE[cache_key]

    os_name = "macOS" if sys.platform == "darwin" else "Windows"
    try:
        import backend.user_memory as user_memory
        mem_summary = user_memory.get_memory_summary()
    except Exception:
        mem_summary = ""

    is_creative_query = any(k in prompt.lower() for k in [
        "истори", "сказк", "рассказ", "анекдот", "сочини", "придумай", "случайн", "рандом"
    ])
    if not is_creative_query:
        try:
            try:
                import backend.extras_manager as em
            except ImportError:
                import extras_manager as em
            extras_ctx = em.format_notes_context_for_ai()
            if extras_ctx:
                mem_summary = (mem_summary + "\n\n" + extras_ctx).strip()
        except Exception:
            pass

    sys_prompt = system_override or build_system_prompt(user_name, os_name, memory_summary=mem_summary)

    messages = [{"role": "system", "content": sys_prompt}]
    if history:
        last_role = None
        for h in history[-10:]:
            r = "user" if h.get("role") == "user" else "assistant"
            cnt = h.get("content", "").strip()
            if cnt:
                if r == last_role and len(messages) > 1:
                    messages[-1]["content"] += f"\n{cnt}"
                else:
                    messages.append({"role": r, "content": cnt})
                    last_role = r

    if len(messages) > 1 and messages[-1]["role"] == "user":
        messages.append({"role": "assistant", "content": "Понял вас. Чем могу помочь далее?"})

    messages.append({"role": "user", "content": prompt})

    keys = load_openrouter_api_keys()
    if not keys:
        return None, []

    url = "https://openrouter.ai/api/v1/chat/completions"
    raw_content = None

    user_key, user_model = get_user_settings_api_key_and_model()
    models_to_try = []
    if user_model:
        models_to_try.append(user_model)
    for m in [
        "meta-llama/llama-3.3-70b-instruct",
        "deepseek/deepseek-v4.1-flash",
        "qwen/qwen-2.5-coder-32b-instruct"
    ]:
        if m not in models_to_try:
            models_to_try.append(m)

    for candidate_key in keys:
        headers = {
            "Authorization": f"Bearer {candidate_key}",
            "HTTP-Referer": "https://argus.ai",
            "X-Title": "Argus AI Desktop Assistant",
            "Content-Type": "application/json"
        }

        for model_name in models_to_try:
            body = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2500
            }
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(body).encode("utf-8"),
                    headers=headers
                )
                with urllib.request.urlopen(req, timeout=4.5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("choices") and data["choices"][0].get("message"):
                        msg = data["choices"][0]["message"]
                        cnt = msg.get("content")
                        if cnt and isinstance(cnt, str) and cnt.strip():
                            cleaned_cnt = re.sub(r'<think>[\s\S]*?</think>', '', cnt, flags=re.IGNORECASE).strip()
                            if cleaned_cnt:
                                raw_content = cleaned_cnt
                                break
                        rsn = msg.get("reasoning")
                        if rsn and isinstance(rsn, str) and rsn.strip():
                            raw_content = rsn.strip()
                            break
            except urllib.error.HTTPError as e:
                # 429 means rate limit exceeded on this model (e.g. daily free limit), rotate model
                if e.code == 429:
                    continue
                # 401 or 403 means bad key, break to try next key
                if e.code in (401, 403):
                    break
                continue
            except Exception:
                continue

        if raw_content:
            break

    if raw_content:
        reply, actions = parse_model_response(raw_content)
        if reply:
            reply = re.sub(r'[\U00010000-\U0010ffff]', '', reply).strip()
            reply = re.sub(r'\\\[\s*', '\n', reply)
            reply = re.sub(r'\s*\\\]', '\n', reply)
            reply = re.sub(r'\\\(\s*', '', reply)
            reply = re.sub(r'\s*\\\)', '', reply)
            reply = re.sub(r'\\Delta\b', 'D', reply)
            reply = re.sub(r'\\cdot\b|\\times\b', '*', reply)
            reply = re.sub(r'\\pm\b', '±', reply)
            reply = re.sub(r'\\sqrt\{([^}]+)\}', r'sqrt(\1)', reply)
            reply = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1) / (\2)', reply)

            # Auto-close code blocks if odd number of ```
            num_fences = len(re.findall(r'```', reply))
            if num_fences % 2 != 0:
                reply += "\n```"

        if reply or actions:
            if len(_OPENROUTER_CACHE) > 300:
                _OPENROUTER_CACHE.clear()
            _OPENROUTER_CACHE[cache_key] = (reply, actions)
            return reply, actions

    return None, []

def is_reasoning_leak(text: str) -> bool:
    """Detects whether text contains internal model chain-of-thought scratchpad notes."""
    if not text or len(text.strip()) < 5:
        return False
    low = text.lower()
    leak_markers = [
        "analyze the request",
        "thinking process",
        "user asks:",
        "constraints:",
        "rule 4:",
        "strictly valid json",
        "forbidden to add",
        "i am argus ai, an autonomous",
        "let me re-read rule",
        "the user asked to close",
        "chain of thought",
        "thought process",
        "the user provided",
        "looking at the personal notes",
        "looking at personal notes",
        "personal notes provided",
        "in the system prompt",
        "provided as input",
        "as input."
    ]
    return any(marker in low for marker in leak_markers)

def clean_reasoning_leak(text: str) -> str:
    """Removes reasoning analysis sections from text."""
    text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'(?:\d+\.\s*)?\*\*(?:Analyze the Request|Thinking|Reasoning|Chain of Thought|Thought Process|Constraints|Goal)[\s\S]*?(?=(?:\{\s*"reply"|\{\s*"actions"|```json|\n\n[А-ЯA-Z]|\Z))', '', text, flags=re.IGNORECASE).strip()
    return text

def parse_model_response(raw_text: str) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """Robust parser that strips any model reasoning/thinking tokens and extracts reply string and actions list."""
    cleaned = raw_text.strip()
    if not cleaned or len(cleaned) < 2:
        return None, []

    # 1. Aggressively strip thinking tags
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'\[THINK\][\s\S]*?\[/THINK\]', '', cleaned, flags=re.IGNORECASE).strip()

    # 2. Extract JSON object using raw_decode (supports nested structures and handles multiple blocks)
    idx = cleaned.find('{')
    while idx != -1:
        try:
            obj, _ = json.JSONDecoder(strict=False).raw_decode(cleaned[idx:])
            if isinstance(obj, dict):
                reply = obj.get("reply", "")
                if is_reasoning_leak(reply):
                    reply = clean_reasoning_leak(reply)
                    if is_reasoning_leak(reply):
                        reply = ""
                raw_acts = obj.get("actions", [])
                return reply, normalize_actions(raw_acts)
        except Exception:
            pass
        idx = cleaned.find('{', idx + 1)

    # 2.5 Robust regex fallback if model produced malformed JSON with "reply"
    if '"reply"' in cleaned:
        m_rep = re.search(r'"reply"\s*:\s*"([\s\S]*?)(?="\s*,\s*"actions"|"\s*\}\s*$)', cleaned)
        if m_rep:
            clean_rep = m_rep.group(1).replace(r'\"', '"').replace(r'\n', '\n')
            if not is_reasoning_leak(clean_rep):
                return clean_rep.strip(), []
        parts = cleaned.split('"reply"', 1)
        if len(parts) > 1:
            val = parts[1].lstrip(' :\t\r\n')
            if val.startswith('"'):
                val = val[1:]
            val = re.sub(r"""["']?\s*,\s*["']actions[\s\S]*$""", "", val)
            val = re.sub(r"""["']?\s*\}\s*$""", "", val).strip()
            if len(val) > 1 and not is_reasoning_leak(val):
                return val.replace(r'\"', '"').replace(r'\n', '\n'), []

    # 3. Strip markdown reasoning / analysis blocks
    cleaned = re.sub(r'(?:\d+\.\s*)?\*\*(?:Analyze the Request|Thinking|Reasoning|Chain of Thought|Thought Process|Constraints|Goal)[\s\S]*?(?=(?:\{\s*"reply"|\{\s*"actions"|```json|\n\n[А-ЯA-Z]|\Z))', '', cleaned, flags=re.IGNORECASE).strip()
    if "User Safety:" in cleaned:
        cleaned = re.sub(r'User Safety:\s*\w+', '', cleaned).strip()
    # Only unwrap outer fences IF they wrap a pure JSON object or JSON array (NEVER strip code blocks!)
    if re.match(r'^```(?:json)?\s*[\{\[]', cleaned, flags=re.IGNORECASE) and re.search(r'[\}\]]\s*```$', cleaned):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*```$', '', cleaned).strip()

    # 4. Extract JSON array if model returned only actions
    # Never truncate code blocks: only check for actions if no code fences exist,
    # and require every item in the array to be a dict with a "type" field.
    if "```" not in cleaned:
        idx_arr = cleaned.find('[')
        while idx_arr != -1:
            try:
                arr, _ = json.JSONDecoder().raw_decode(cleaned[idx_arr:])
                if isinstance(arr, list) and len(arr) > 0 and all(isinstance(x, dict) and "type" in x for x in arr):
                    actions = normalize_actions(arr)
                    if actions:
                        text_part = cleaned[:idx_arr].strip()
                        if is_reasoning_leak(text_part):
                            text_part = "Задачи приняты."
                        return text_part or "Задачи приняты.", actions
            except Exception:
                pass
            idx_arr = cleaned.find('[', idx_arr + 1)

    # 5. Check if text is a reasoning leak
    if is_reasoning_leak(cleaned):
        return None, []

    # Auto-close code blocks if odd number of ```
    num_fences = len(re.findall(r'```', cleaned))
    if num_fences % 2 != 0:
        cleaned += "\n```"

    return cleaned, []

def normalize_actions(raw_actions: Any) -> List[Dict[str, Any]]:
    """Normalizes action dictionaries into Argus standard action names."""
    if not isinstance(raw_actions, list):
        return []

    normalized = []
    for act in raw_actions:
        if not isinstance(act, dict):
            continue

        raw_type = act.get("type", "").lower().strip()
        new_act = dict(act)

        # Normalize action aliases
        if raw_type in ["click", "click_ui_button", "press_button", "click_element"]:
            new_act["type"] = "click_button"
        elif raw_type in ["computer_use", "computer_task", "gui_task"]:
            new_act["type"] = "computer_use_task"
        elif raw_type in ["click_mouse", "mouse_click", "click_coordinates"]:
            new_act["type"] = "mouse_click"
        if raw_type in ["open_application", "open_app", "run_app", "start_app"]:
            new_act["type"] = "launch_app"
        elif raw_type in ["exit_app", "quit_app", "kill_app"]:
            new_act["type"] = "close_app"
        elif raw_type in ["volume"]:
            v_action = act.get("action", "set")
            new_act["type"] = f"volume_{v_action}" if v_action in ["up", "down", "mute", "unmute"] else "volume_set"
        elif raw_type in ["brightness"]:
            b_action = act.get("action", "set")
            new_act["type"] = f"brightness_{b_action}" if b_action in ["up", "down"] else "brightness_set"
        elif raw_type in ["empty_recycle_bin", "clear_trash", "clean_trash"]:
            new_act["type"] = "empty_recycle"
        elif raw_type in ["lock_workstation", "lock_screen", "lock_computer"]:
            new_act["type"] = "lock_pc"
        elif raw_type in ["list_folder", "list_directory"]:
            new_act["type"] = "list_files"
        elif raw_type in ["browser_tab", "close_all_browser_tabs", "close_all_tabs"]:
            tab_act = act.get("action", "new")
            if raw_type in ["close_all_browser_tabs", "close_all_tabs"] or tab_act in ["close_all", "all"]:
                new_act["type"] = "close_all_browser_tabs"
            elif tab_act == "close":
                new_act["type"] = "close_browser_tab"
            elif tab_act == "refresh":
                new_act["type"] = "refresh_page"
            elif tab_act in ["next", "prev"]:
                new_act["type"] = "switch_browser_tab"
                new_act["direction"] = tab_act
            else:
                new_act["type"] = "new_browser_tab"

        # Standardize target / path aliases
        if "target" in new_act and "path" not in new_act:
            new_act["path"] = new_act["target"]
        if "file" in new_act and "path" not in new_act:
            new_act["path"] = new_act["file"]

        normalized.append(new_act)

    return normalized
