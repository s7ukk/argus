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
FREE_PRIMARY_MODEL = "minimax/minimax-m3.1-flash:free"
FREE_FALLBACK_MODELS = [
    "minimax/minimax-m3.1-flash:free",
    "cohere/north-mini-code:free",
    "openrouter/free"
]

def load_openrouter_api_key() -> Optional[str]:
    """
    Safely retrieves OPENROUTER_API_KEY from environment or .env files.
    Checks:
    1. os.environ['OPENROUTER_API_KEY']
    2. Project root .env
    3. User Data AppData/ArgusAI .env
    4. Packaged resources .env
    Never leaks key into logs.
    """
    global _LAST_KEY
    if _LAST_KEY:
        return _LAST_KEY

    # 1. Environment variable
    env_key = os.getenv("OPENROUTER_API_KEY")
    if env_key and env_key.strip():
        _LAST_KEY = env_key.strip()
        return _LAST_KEY

    # 2. Candidate .env file locations
    candidates = [
        # Current working directory
        os.path.join(os.getcwd(), ".env"),
        # Project root relative to this file
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        # User config directory
        os.path.join(app_paths.get_argus_data_dir(), ".env"),
        # Resources directory in packaged app
        os.path.join(getattr(sys, "_MEIPASS", ""), ".env") if hasattr(sys, "_MEIPASS") else None,
        os.path.join(os.path.dirname(sys.executable), ".env"),
        os.path.join(os.path.dirname(sys.executable), "resources", ".env"),
        os.path.join(os.path.dirname(sys.executable), "..", "Resources", ".env"),
    ]

    for cand in candidates:
        if cand and os.path.isfile(cand):
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("OPENROUTER_API_KEY="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                _LAST_KEY = val
                                os.environ["OPENROUTER_API_KEY"] = val
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
        "анализировать информацию, находить нужные вещи в интернете, запускать и контролировать программы, файлы, окна и звук.\n\n"
        "ФОРМАТ ОТВЕТА:\n"
        "Ты ВСЕГДА возвращаешь ответ строго в формате валидного JSON со следующей структурой:\n"
        "{\n"
        "  \"reply\": \"Интеллектуальный, грамотный, полезный и вежливый ответ пользователю на русском языке строго БЕЗ ЭМОДЗИ\",\n"
        "  \"actions\": [\n"
        "    {\"type\": \"...\", ...}\n"
        "  ]\n"
        "}\n\n"
        "ПРАВИЛА:\n"
        "1. Если пользователь просто задает вопрос, просит совета, объяснения, кода или ведет диалог — отвечай развернуто в поле 'reply', а поле 'actions' оставь пустым массивом [].\n"
        "2. Если пользователь просит выполнить действия на компьютере — сформируй точный массив 'actions', а в 'reply' кратко подтверди выполнение.\n"
        "3. Если задача составная (например: создать файл, написать туда код и открыть браузер) — сгенерируй несколько шагов в 'actions' в правильном порядке.\n\n"
        "ДОСТУПНЫЕ ТИПЫ ДЕЙСТВИЙ (actions):\n"
        "- {\"type\": \"launch_app\", \"app\": \"название приложения\"} — запустить программу (chrome, telegram, discord, vscode, notepad, word, excel, spotify, steam, postman, terminal, etc.)\n"
        "- {\"type\": \"close_app\", \"app\": \"название программы\"} — закрыть программу (только если пользователь явно попросил закрыть!)\n"
        "- {\"type\": \"close_all_except\", \"keep\": [\"telegram\", \"chrome\"]} — закрыть все окна кроме указанных\n"
        "- {\"type\": \"open_url\", \"url\": \"https://...\"} — открыть веб-ссылку\n"
        "- {\"type\": \"search_web\", \"query\": \"текст запроса\", \"engine\": \"google\" | \"yandex\" | \"youtube\" | \"github\" | \"ozon\" | \"wildberries\"} — поиск в поисковике или сервисе\n"
        "- {\"type\": \"click_website_button\", \"button\": \"текст кнопки\"} — клик по кнопке на открытом сайте (например: 'войти', 'play', 'подписаться')\n"
        "- {\"type\": \"browser_tab\", \"action\": \"new\" | \"close\" | \"refresh\" | \"next\" | \"prev\"} — управление вкладками браузера\n"
        "- {\"type\": \"scroll_page\", \"direction\": \"down\" | \"up\"} — прокрутка открытой веб-страницы\n"
        "- {\"type\": \"type_text\", \"text\": \"текст\", \"target_app\": \"целевая программа\", \"press_enter\": true | false} — напечатать текст в активное поле или окно\n"
        "- {\"type\": \"press_key\", \"key\": \"enter\" | \"tab\" | \"esc\" | \"space\"} — нажать клавишу\n"
        "- {\"type\": \"hotkey\", \"keys\": [\"ctrl\", \"v\"]} — нажать сочетание клавиш (для macOS используются 'cmd')\n"
        "- {\"type\": \"create_file\", \"target\": \"desktop/notes.txt\", \"content\": \"текст файла\"} — создать файл с указанным содержимым\n"
        "- {\"type\": \"create_folder\", \"target\": \"desktop/папка\"} — создать папку\n"
        "- {\"type\": \"delete_file\", \"target\": \"путь к файлу\"} — удалить файл или папку\n"
        "- {\"type\": \"analyze_file\", \"target\": \"путь к файлу\"} — проанализировать содержимое файла\n"
        "- {\"type\": \"list_files\", \"folder\": \"desktop\" | \"downloads\" | \"путь\"} — посмотреть список файлов в папке\n"
        "- {\"type\": \"screenshot\", \"folder\": \"desktop\" | \"downloads\" | \"documents\"} — сделать скриншот экрана\n"
        "- {\"type\": \"volume\", \"action\": \"set\" | \"up\" | \"down\" | \"mute\" | \"unmute\", \"level\": 50} — настроить громкость звука\n"
        "- {\"type\": \"brightness\", \"action\": \"set\" | \"up\" | \"down\", \"level\": 80} — настроить яркость экрана\n"
        "- {\"type\": \"play_music\", \"service\": \"yandex\" | \"spotify\" | \"youtube\" | \"soundcloud\", \"query\": \"песня или артист\", \"playlist\": \"название\", \"action\": \"play\" | \"pause\" | \"next\" | \"prev\"} — воспроизведение музыки\n"
        "- {\"type\": \"empty_recycle\"} — очистить корзину\n"
        "- {\"type\": \"lock_pc\"} — заблокировать компьютер\n"
        "- {\"type\": \"system_stats\"} — получить нагрузку на процессор, память и диск\n"
        "- {\"type\": \"terminal_command\", \"command\": \"команда терминала\"} — выполнить команду в терминале (PowerShell / Bash)\n"
        "- {\"type\": \"messenger_send\", \"messenger\": \"telegram\" | \"discord\" | \"whatsapp\" | \"auto\", \"contact\": \"имя контакта\", \"message\": \"текст\"} — найти контакт и отправить сообщение\n"
        "- {\"type\": \"wait\", \"seconds\": 1.5} — пауза между шагами\n\n"
        "Строго возвращай ТОЛЬКО чистый JSON без разметки markdown в начале и конце."
    )

def query_openrouter(
    prompt: str,
    user_name: str = "Пользователь",
    history: Optional[List[Dict[str, Any]]] = None,
    system_context: Optional[str] = None
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Main call to OpenRouter Free AI.
    Returns: (reply_text, actions_list)
    """
    key = load_openrouter_api_key()
    if not key:
        return None, []

    cache_key = prompt.strip().lower()
    if not history and cache_key in _OPENROUTER_CACHE:
        return _OPENROUTER_CACHE[cache_key]

    is_mac = sys.platform == "darwin"
    os_name = "macOS" if is_mac else "Windows"

    import backend.user_memory as user_memory
    mem_summary = user_memory.get_memory_summary()

    sys_prompt = build_system_prompt(user_name, os_name, mem_summary)
    if system_context:
        sys_prompt += f"\nДополнительный контекст системы:\n{system_context}"

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

    body = {
        "model": FREE_PRIMARY_MODEL,
        "models": FREE_FALLBACK_MODELS,
        "messages": messages,
        "temperature": 0.35,
        "max_tokens": 1200
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=14.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_content = data["choices"][0]["message"]["content"].strip()
            reply, actions = parse_model_response(raw_content)

            # Strip emojis
            if reply:
                reply = re.sub(r'[\U00010000-\U0010ffff]', '', reply).strip()

            if reply or actions:
                if len(_OPENROUTER_CACHE) > 300:
                    _OPENROUTER_CACHE.clear()
                _OPENROUTER_CACHE[cache_key] = (reply, actions)
                return reply, actions
    except Exception as e:
        print(f"[Argus OpenRouter Notice]: Free model request failed or timed out: {e}")

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
            if v_action in ["mute", "unmute"]:
                new_act["type"] = "volume_mute"
            elif v_action in ["up", "increase", "higher"]:
                new_act["type"] = "volume_change"
                new_act["delta"] = act.get("delta", 15)
            elif v_action in ["down", "decrease", "lower"]:
                new_act["type"] = "volume_change"
                new_act["delta"] = -abs(int(act.get("delta", 15)))
            else:
                new_act["type"] = "volume_set"
                new_act["level"] = act.get("level", 50)
        elif raw_type in ["brightness"]:
            b_action = act.get("action", "set")
            if b_action in ["up", "increase", "higher"]:
                new_act["type"] = "brightness_change"
                new_act["delta"] = act.get("delta", 15)
            elif b_action in ["down", "decrease", "lower"]:
                new_act["type"] = "brightness_change"
                new_act["delta"] = -abs(int(act.get("delta", 15)))
            else:
                new_act["type"] = "brightness_set"
                new_act["level"] = act.get("level", 80)
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

        # Normalize target / path fields for file operations
        if "target" in new_act and "path" not in new_act:
            new_act["path"] = new_act["target"]

        normalized.append(new_act)

    return normalized
