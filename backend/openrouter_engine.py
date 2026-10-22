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

# Free models router and top-tier free fallback models
FREE_PRIMARY_MODEL = "openrouter/free"
FREE_FALLBACK_MODELS = [
    "openrouter/free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "liquid/lfm-2.5-2.6b:free",
    "cohere/north-mini-code:free"
]

def load_openrouter_api_keys() -> List[str]:
    """
    Safely retrieves all OPENROUTER_API_KEYs from environment or .env files.
    Supports comma-separated keys and multiple env variables.
    """
    found_keys = []
    
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
    return (
        f"Ты — Argus AI, персональный автономный высокоинтеллектуальный ИИ-ассистент для глубокой работы за компьютером ({os_name}).\n"
        f"Пользователь: {user_name}.\n"
        f"{memory_summary}\n\n"
        "ТВОЯ ЦЕЛЬ:\n"
        "Полноценно помогать пользователю работать со всем компьютером: отвечать на любые вопросы, писать код, "
        "решать математику, находить информацию, запускать и контролировать программы, окна, браузер, файлы и звук.\n\n"
        "ФОРМАТ ОТВЕТА:\n"
        "Ты ВСЕГДА возвращаешь ответ строго в формате валидного JSON со следующей структурой:\n"
        "{\n"
        "  \"reply\": \"Интеллектуальный, грамотный, полезный и вежливый ответ пользователю на русском языке строго БЕЗ ЭМОДЗИ\",\n"
        "  \"actions\": [\n"
        "    {\"type\": \"...\", ...}\n"
        "  ]\n"
        "}\n\n"
        "ПРАВИЛА:\n"
        "1. Если пользователь задает вопрос, просит совета, кода, объяснения или ведет диалог — отвечай развернуто, умно и по делу в поле 'reply', а поле 'actions' оставь пустым массивом [].\n"
        "2. Если требуется действие с компьютером, добавь действия в массив 'actions'.\n"
        "3. Доступные типы действий:\n"
        "   - launch_app: {\"type\": \"launch_app\", \"app\": \"название_программы\"}\n"
        "   - close_app: {\"type\": \"close_app\", \"app\": \"название_программы\"}\n"
        "   - close_all_except: {\"type\": \"close_all_except\", \"keep\": [\"код\", \"браузер\"]}\n"
        "   - open_url: {\"type\": \"open_url\", \"url\": \"https://...\"}\n"
        "   - search_web: {\"type\": \"search_web\", \"query\": \"...\", \"engine\": \"google\" | \"yandex\" | \"youtube\"}\n"
        "   - click_website_button: {\"type\": \"click_website_button\", \"button\": \"текст кнопки\"}\n"
        "   - browser_tab: {\"type\": \"browser_tab\", \"action\": \"new\" | \"close\" | \"next\" | \"prev\" | \"refresh\"}\n"
        "   - close_all_browser_tabs: {\"type\": \"close_all_browser_tabs\"}\n"
        "   - scroll_page: {\"type\": \"scroll_page\", \"direction\": \"down\" | \"up\"}\n"
        "   - type_text: {\"type\": \"type_text\", \"text\": \"текст для ввода\", \"press_enter\": true/false}\n"
        "   - press_key: {\"type\": \"press_key\", \"key\": \"enter\" | \"esc\" | \"tab\" | \"space\"}\n"
        "   - hotkey: {\"type\": \"hotkey\", \"keys\": [\"ctrl\", \"c\"]}\n"
        "   - create_file: {\"type\": \"create_file\", \"path\": \"имя_файла.txt\", \"content\": \"содержимое\"}\n"
        "   - create_folder: {\"type\": \"create_folder\", \"path\": \"имя_папки\"}\n"
        "   - delete_file: {\"type\": \"delete_file\", \"path\": \"имя_файла\"}\n"
        "   - analyze_file: {\"type\": \"analyze_file\", \"path\": \"имя_файла\"}\n"
        "   - list_files: {\"type\": \"list_files\", \"folder\": \"desktop\" | \"downloads\" | \"documents\"}\n"
        "   - screenshot: {\"type\": \"screenshot\", \"folder\": \"desktop\"}\n"
        "   - volume: {\"type\": \"volume\", \"action\": \"up\" | \"down\" | \"mute\" | \"unmute\" | \"set\", \"level\": 50}\n"
        "   - brightness: {\"type\": \"brightness\", \"action\": \"up\" | \"down\" | \"set\", \"level\": 80}\n"
        "   - play_music: {\"type\": \"play_music\", \"action\": \"play\" | \"pause\" | \"next\" | \"prev\", \"query\": \"трек\"}\n"
        "   - empty_recycle: {\"type\": \"empty_recycle\"}\n"
        "   - lock_pc: {\"type\": \"lock_pc\"}\n"
        "   - system_stats: {\"type\": \"system_stats\"}\n"
        "   - terminal_command: {\"type\": \"terminal_command\", \"command\": \"...\", \"shell\": \"powershell\" | \"bash\"}\n"
        "   - messenger_send: {\"type\": \"messenger_send\", \"messenger\": \"telegram\" | \"discord\" | \"whatsapp\" | \"auto\", \"contact\": \"имя\", \"message\": \"текст\"}\n\n"
        "4. ДЕЙСТВИЯ С ВКЛАДКАМИ И ОКНАМИ:\n"
        "   - Для закрытия одной вкладки используй action: 'close_browser_tab' (или browser_tab с action: 'close').\n"
        "   - Для закрытия всех вкладок используй action: 'close_all_browser_tabs'.\n"
        "   - Для закрытия конкретной программы используй action: 'close_app'.\n"
        "5. ФОРМАТ И СТИЛЬ:\n"
        "   - Возвращай ТОЛЬКО чистый JSON строго формата {\"reply\": \"...\", \"actions\": [...]}.\n"
        "   - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО выводить рассуждения, шаги анализа или черновики (Analyze the Request, Thinking, Constraints и т.д.). Сразу готовый результат!\n"
        "   - ФОРМАТИРОВАНИЕ МАТЕМАТИКИ: Не используй сырой LaTeX (теги \\[, \\], \\frac и т.д.), пиши понятным читаемым текстом.\n"
        "   - НАПИСАНИЕ КОДА: Если пользователь просит код или скрипт — пиши качественный код внутри блока ```python ... ``` в поле 'reply', поле 'actions' оставляй пустым []."
    )

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

    for candidate_key in keys:
        headers = {
            "Authorization": f"Bearer {candidate_key}",
            "HTTP-Referer": "https://argus.ai",
            "X-Title": "Argus AI Desktop Assistant",
            "Content-Type": "application/json"
        }

        # Attempt 1: primary model with fallback routing list and reasoning excluded
        body = {
            "model": FREE_PRIMARY_MODEL,
            "models": FREE_FALLBACK_MODELS,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1200,
            "reasoning": {"exclude": True}
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("choices") and data["choices"][0].get("message"):
                    raw_content = data["choices"][0]["message"].get("content", "").strip()
                    if raw_content:
                        break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                # Key rate limit exceeded, rotate to next candidate key
                continue
            pass
        except Exception:
            # Fallback to direct model request
            try:
                body_fallback = {
                    "model": "openrouter/free",
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 1000,
                    "reasoning": {"exclude": True}
                }
                req_fb = urllib.request.Request(
                    url,
                    data=json.dumps(body_fallback).encode("utf-8"),
                    headers=headers
                )
                with urllib.request.urlopen(req_fb, timeout=9.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("choices") and data["choices"][0].get("message"):
                        raw_content = data["choices"][0]["message"].get("content", "").strip()
                        if raw_content:
                            break
            except Exception:
                pass

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
        "thought process"
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

    # 2. Extract JSON object directly first (even if preceded by thinking / analysis)
    m_obj = re.search(r'\{\s*"reply"\s*:[\s\S]*?"actions"\s*:[\s\S]*?\}', cleaned, re.DOTALL)
    if not m_obj:
        m_obj = re.search(r'\{\s*"actions"\s*:[\s\S]*?"reply"\s*:[\s\S]*?\}', cleaned, re.DOTALL)

    if m_obj:
        try:
            obj = json.loads(m_obj.group(0))
            if isinstance(obj, dict):
                reply = obj.get("reply", "")
                if is_reasoning_leak(reply):
                    reply = clean_reasoning_leak(reply)
                    if is_reasoning_leak(reply):
                        reply = ""
                return reply, normalize_actions(obj.get("actions", []))
        except Exception:
            pass

    # 3. Strip markdown reasoning / analysis blocks
    cleaned = re.sub(r'(?:\d+\.\s*)?\*\*(?:Analyze the Request|Thinking|Reasoning|Chain of Thought|Thought Process|Constraints|Goal)[\s\S]*?(?=(?:\{\s*"reply"|\{\s*"actions"|```json|\n\n[А-ЯA-Z]|\Z))', '', cleaned, flags=re.IGNORECASE).strip()
    if "User Safety:" in cleaned:
        cleaned = re.sub(r'User Safety:\s*\w+', '', cleaned).strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned).strip()

    # 4. Direct JSON parse
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            reply = obj.get("reply", "")
            if is_reasoning_leak(reply):
                reply = ""
            return reply, normalize_actions(obj.get("actions", []))
        elif isinstance(obj, list):
            return "Задачи приняты и выполняются.", normalize_actions(obj)
    except Exception:
        pass

    # 5. Extract JSON array if model returned only actions
    m_arr = re.search(r'\[\s*\{.*\}\s*\]', cleaned, re.DOTALL)
    if m_arr:
        try:
            arr = json.loads(m_arr.group(0))
            if isinstance(arr, list):
                actions = normalize_actions(arr)
                text_part = cleaned[:m_arr.start()].strip()
                if is_reasoning_leak(text_part):
                    text_part = "Задачи приняты."
                return text_part or "Задачи приняты.", actions
        except Exception:
            pass

    # 6. Check if text is a reasoning leak
    if is_reasoning_leak(cleaned):
        return None, []

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
