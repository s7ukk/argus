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
FREE_PRIMARY_MODEL = "cohere/north-mini-code:free"
FREE_FALLBACK_MODELS = [
    "cohere/north-mini-code:free",
    "dots-studio/dots-3-note-preview:free",
    "openrouter/free"
]

def load_openrouter_api_key() -> Optional[str]:
    """
    Safely retrieves OPENROUTER_API_KEY from environment or .env files.
    Checks:
    1. os.environ['OPENROUTER_API_KEY']
    2. Deep directory tree walk up from executable, working directory, and backend file
    3. User Data AppData/ArgusAI and argus-ai .env
    4. Packaged resources .env
    Never leaks key into logs.
    """
    global _LAST_KEY
    if _LAST_KEY:
        return _LAST_KEY

    # 1. Environment variable
    env_key = os.getenv("OPENROUTER_API_KEY")
    if env_key and env_key.strip() and env_key.strip() != "your_openrouter_api_key_here":
        _LAST_KEY = env_key.strip()
        return _LAST_KEY

    # 2. Candidate .env file locations
    candidates = [
        # Explicit resource path if passed by Electron
        os.path.join(os.getenv("ARGUS_RESOURCES_PATH") or "", ".env"),
        # Current working directory
        os.path.join(os.getcwd(), ".env"),
        # User config directory
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

    # Walk up from sys.executable up to 6 levels to find resources/.env in packaged app
    curr_exe = os.path.abspath(sys.executable)
    for _ in range(6):
        curr_exe = os.path.dirname(curr_exe)
        candidates.append(os.path.join(curr_exe, ".env"))
        candidates.append(os.path.join(curr_exe, "resources", ".env"))
        candidates.append(os.path.join(curr_exe, "Resources", ".env"))

    # Walk up from this file up to 6 levels
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
                        if line.startswith("OPENROUTER_API_KEY="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val and val != "your_openrouter_api_key_here" and len(val) > 10:
                                _LAST_KEY = val
                                os.environ["OPENROUTER_API_KEY"] = val
                                # Auto persist to user data directory
                                try:
                                    ud_env = os.path.join(app_paths.get_argus_data_dir(), ".env")
                                    if not os.path.exists(ud_env):
                                        with open(ud_env, "w", encoding="utf-8") as uf:
                                            uf.write(f"OPENROUTER_API_KEY={val}\n")
                                except Exception:
                                    pass
                                return _LAST_KEY
            except Exception:
                pass

    return None

def build_system_prompt(user_name: str, os_name: str, memory_summary: str = "") -> str:
    """Builds comprehensive system instructions training the AI on full computer control and assistance."""
    return (
        f"Ты — Argus AI, персональный автономный высокоинтеллектуальный ИИ-ассистент для глубокой работы за компьютером ({os_name}).\n"
        f"Пользователь: {user_name}.\n"
        f"{memory_summary}\n\n"
        "ТВОЯ ЦЕЛЬ:\n"
        "Полноценно помогать пользователю работать со всем компьютером: отвечать на сложные вопросы, писать код, "
        "решать уравнения и математику, находить нужные вещи в интернете, запускать и контролировать программы, файлы, окна и звук.\n\n"
        "ФОРМАТ ОТВЕТА:\n"
        "Ты ВСЕГДА возвращаешь ответ строго в формате валидного JSON со следующей структурой:\n"
        "{\n"
        "  \"reply\": \"Интеллектуальный, грамотный, полезный и вежливый ответ пользователю на русском языке строго БЕЗ ЭМОДЗИ\",\n"
        "  \"actions\": [\n"
        "    {\"type\": \"...\", ...}\n"
        "  ]\n"
        "}\n\n"
        "ПРАВИЛА:\n"
        "1. Если пользователь просто задает вопрос, просит совета, объяснения, кода, решения задачи/уравнения или ведет диалог — отвечай развернуто, умно и по делу в поле 'reply', а поле 'actions' оставь пустым массивом [].\n"
        "2. Если требуется действие с компьютером, добавь одно или несколько действий в массив 'actions'.\n"
        "3. Доступные типы действий:\n"
        "   - launch_app: {\"type\": \"launch_app\", \"app\": \"название_программы\"}\n"
        "   - close_app: {\"type\": \"close_app\", \"app\": \"название_программы\"}\n"
        "   - close_all_except: {\"type\": \"close_all_except\", \"keep\": [\"код\", \"браузер\"]}\n"
        "   - open_url: {\"type\": \"open_url\", \"url\": \"https://...\"}\n"
        "   - search_web: {\"type\": \"search_web\", \"query\": \"...\", \"engine\": \"google\" | \"yandex\" | \"youtube\"}\n"
        "   - click_website_button: {\"type\": \"click_website_button\", \"button\": \"текст кнопки\"}\n"
        "   - browser_tab: {\"type\": \"browser_tab\", \"action\": \"new\" | \"close\" | \"next\" | \"prev\" | \"refresh\"}\n"
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
        "4. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО добавлять 'close_app', если пользователь не просил явно закрыть приложение!\n"
        "5. Отвечай кратко, емко, интеллектуально и дружелюбно. Никаких шаблонных отписок вроде 'Принято, я слушаю'."
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
    sys_prompt = system_override or build_system_prompt(user_name, os_name)

    messages = [{"role": "system", "content": sys_prompt}]
    if history:
        for h in history[-8:]:
            r = "user" if h.get("role") == "user" else "assistant"
            cnt = h.get("content", "").strip()
            if cnt:
                messages.append({"role": r, "content": cnt})
    messages.append({"role": "user", "content": prompt})

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "https://argus.ai",
        "X-Title": "Argus AI Desktop Assistant",
        "Content-Type": "application/json"
    }

    # Attempt 1: using fallback array
    body = {
        "model": FREE_PRIMARY_MODEL,
        "models": FREE_FALLBACK_MODELS,
        "messages": messages,
        "temperature": 0.35,
        "max_tokens": 1200
    }

    raw_content = None
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=12.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("choices") and data["choices"][0].get("message"):
                raw_content = data["choices"][0]["message"].get("content", "").strip()
    except Exception as e:
        # Attempt 2: direct single free model fallback
        try:
            body_fallback = {
                "model": "openrouter/free",
                "messages": messages,
                "temperature": 0.35,
                "max_tokens": 1000
            }
            req_fb = urllib.request.Request(
                url,
                data=json.dumps(body_fallback).encode("utf-8"),
                headers=headers
            )
            with urllib.request.urlopen(req_fb, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("choices") and data["choices"][0].get("message"):
                    raw_content = data["choices"][0]["message"].get("content", "").strip()
        except Exception:
            pass

    if raw_content:
        reply, actions = parse_model_response(raw_content)
        if reply:
            reply = re.sub(r'[\U00010000-\U0010ffff]', '', reply).strip()

        if reply or actions:
            if len(_OPENROUTER_CACHE) > 300:
                _OPENROUTER_CACHE.clear()
            _OPENROUTER_CACHE[cache_key] = (reply, actions)
            return reply, actions

    return None, []

def parse_model_response(raw_text: str) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """Robust parser that extracts reply string and actions list from various model outputs."""
    cleaned = raw_text.strip()
    if "User Safety:" in cleaned:
        cleaned = re.sub(r'User Safety:\s*\w+', '', cleaned).strip()
    if not cleaned or len(cleaned) < 2:
        return None, []

    # Strip markdown codeblocks
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned).strip()

    # 1. Try direct JSON parse
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            reply = obj.get("reply", "")
            raw_acts = obj.get("actions", [])
            actions = normalize_actions(raw_acts)
            return reply, actions
        elif isinstance(obj, list):
            actions = normalize_actions(obj)
            return "Задачи приняты и выполняются.", actions
    except Exception:
        pass

    # 2. Extract JSON object via regex
    m_obj = re.search(r'\{\s*"reply"\s*:.*?"actions"\s*:\s*\[.*?\]\s*\}', cleaned, re.DOTALL)
    if m_obj:
        try:
            obj = json.loads(m_obj.group(0))
            return obj.get("reply", ""), normalize_actions(obj.get("actions", []))
        except Exception:
            pass

    # 3. Extract JSON array if model returned only actions
    m_arr = re.search(r'\[\s*\{.*\}\s*\]', cleaned, re.DOTALL)
    if m_arr:
        try:
            arr = json.loads(m_arr.group(0))
            if isinstance(arr, list):
                actions = normalize_actions(arr)
                text_part = cleaned[:m_arr.start()].strip() or "Задачи приняты."
                return text_part, actions
        except Exception:
            pass

    # 4. Fallback: Entire text is a conversational response without actions
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
        elif raw_type in ["browser_tab"]:
            tab_act = act.get("action", "new")
            if tab_act == "close":
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
