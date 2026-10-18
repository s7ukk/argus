import os
import re
import time
import json
import urllib.request
import urllib.error
import datetime
import math
from typing import Dict, Any, Tuple, Optional, List
import backend.system_control as sc

def is_english(text: str) -> bool:
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    cyrillic_chars = len(re.findall(r'[а-яА-ЯёЁ]', text))
    return latin_chars > cyrillic_chars

def safe_math_eval(expr: str) -> Optional[float]:
    cleaned = expr.replace('^', '**').replace('x', '*').replace('×', '*').replace('÷', '/')
    cleaned = re.sub(r'[^0-9+\-*/().,** ]', '', cleaned).replace(',', '.')
    if not cleaned or not any(c in cleaned for c in '+-*/'):
        return None
    try:
        allowed = {"__builtins__": None, "math": math}
        res = eval(cleaned, allowed, {})
        if isinstance(res, (int, float)):
            return round(res, 4)
    except Exception:
        pass
    return None

# ─── ACTION EXECUTOR ─────────────────────────────────────────────
def execute_single_action(act: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
    """
    Executes a single concrete system command on Windows.
    Returns: (status_message, action_type, data)
    """
    act_type = act.get("type", "").lower()
    
    if act_type == "launch_app":
        app = act.get("app", "chrome")
        res = sc.launch_application(app)
        app_disp = app.capitalize()
        if app.lower() in ["chrome", "хром", "браузер", "browser"]:
            app_disp = "Chrome"
        elif app.lower() in ["telegram", "телеграм", "телега"]:
            app_disp = "Telegram"
        elif app.lower() in ["discord", "дискорд"]:
            app_disp = "Discord"
        elif app.lower() in ["vscode", "код"]:
            app_disp = "VS Code"
        return f"Запущено приложение: {app_disp}", "launch_app", res

    elif act_type == "close_app":
        app = act.get("app", "")
        res = sc.close_application(app)
        return f"Закрыто приложение: {app.capitalize()}", "close_app", res

    elif act_type == "screenshot":
        path = sc.take_screenshot_to_desktop()
        return f"Снимок экрана сохранен на Рабочий стол: {path}", "screenshot", {"path": path}

    elif act_type == "wait":
        sec = min(5.0, max(0.5, float(act.get("seconds", 1.5))))
        time.sleep(sec)
        return "", "wait", {"seconds": sec}

    elif act_type == "volume_set":
        lvl = int(act.get("level", 50))
        final_lvl = sc.set_volume(lvl)
        return f"Громкость установлена на {final_lvl}%", "volume_set", {"level": final_lvl}

    elif act_type == "volume_change":
        delta = int(act.get("delta", 10))
        lvl = sc.change_volume(delta)
        direction = "увеличена" if delta > 0 else "уменьшена"
        return f"Громкость {direction} на {abs(delta)}%. Текущий уровень: {lvl}%", "volume_change", {"level": lvl}

    elif act_type == "volume_mute":
        muted = sc.toggle_mute()
        state = "выключен" if muted else "включен"
        return f"Звук {state}", "volume_mute", {"muted": muted}

    elif act_type == "brightness_set":
        lvl = int(act.get("level", 80))
        b = sc.set_brightness(lvl)
        return f"Яркость экрана установлена на {b}%", "brightness_set", {"level": b}

    elif act_type == "brightness_change":
        delta = int(act.get("delta", 10))
        b = sc.change_brightness(delta)
        direction = "увеличена" if delta > 0 else "уменьшена"
        return f"Яркость {direction} на {abs(delta)}%. Текущий уровень: {b}%", "brightness_change", {"level": b}

    elif act_type == "empty_recycle":
        sc.empty_recycle_bin()
        return "Корзина Windows очищена", "empty_recycle", {}

    elif act_type == "lock_pc":
        sc.lock_workstation()
        return "Компьютер заблокирован", "system_lock", {}

    elif act_type == "open_url":
        url = act.get("url", "https://google.com")
        sc.open_url(url)
        return f"Открыта ссылка: {url}", "open_url", {"url": url}

    elif act_type == "search_web":
        q = act.get("query", "")
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
        sc.open_url(url)
        return f"Выполнен поиск в Google: «{q}»", "open_url", {"url": url}

    elif act_type == "open_folder":
        folder = act.get("folder", "desktop")
        sc.open_folder(folder)
        return f"Открыта папка: {folder}", "open_folder", {"folder": folder}

    elif act_type == "media":
        m_act = act.get("action", "play")
        sc.media_control(m_act)
        return f"Медиаплеер: {m_act}", "media", {"action": m_act}

    elif act_type == "power":
        p_act = act.get("action", "shutdown")
        sc.system_power(p_act)
        act_ru = "выключение" if p_act == "shutdown" else "перезагрузка" if p_act == "restart" else "отмена выключения"
        return f"Команда питания: {act_ru}", "power", {"action": p_act}

    elif act_type == "system_stats":
        stats = sc.get_system_stats()
        cpu_p = stats.get("cpu", {}).get("percent", 0)
        cores = stats.get("cpu", {}).get("cores", 0)
        mem = stats.get("memory", {})
        used_gb = mem.get("used_gb", 0)
        tot_gb = mem.get("total_gb", 0)
        mem_p = mem.get("percent", 0)
        vol = stats.get("volume", 50)
        br = stats.get("brightness", 80)
        info = f"Процессор: {cpu_p}% ({cores} ядер) | ОЗУ: {used_gb}/{tot_gb} ГБ ({mem_p}%) | Звук: {vol}% | Яркость: {br}%"
        return info, "system_stats", stats

    return "", "noop", {}

# ─── COMPREHENSIVE LOCAL INTENT MATCHER ─────────────────────────
APP_MAP = {
    # Browsers
    "chrome": "chrome", "хром": "chrome", "гугл хром": "chrome", "google chrome": "chrome",
    "браузер": "chrome", "browser": "chrome", "интернет": "chrome",
    "edge": "edge", "эдж": "edge", "msedge": "edge",
    "yandex": "yandex", "яндекс": "yandex", "яндекс браузер": "yandex",
    # Messengers & Social
    "telegram": "telegram", "телеграм": "telegram", "телега": "telegram", "тг": "telegram", "tg": "telegram",
    "discord": "discord", "дискорд": "discord", "диск": "discord", "дс": "discord", "dc": "discord",
    "steam": "steam", "стим": "steam",
    "spotify": "spotify", "спотифай": "spotify", "музыка": "spotify",
    # Productivity & Dev
    "vscode": "vscode", "vs code": "vscode", "код": "vscode", "вскод": "vscode", "visual studio code": "vscode",
    "calculator": "calculator", "калькулятор": "calculator", "кальк": "calculator", "calc": "calculator",
    "notepad": "notepad", "блокнот": "notepad", "текстовый редактор": "notepad",
    "paint": "paint", "пейнт": "paint", "паинт": "paint", "рисовалка": "paint",
    # System
    "task manager": "task manager", "taskmgr": "task manager", "диспетчер задач": "task manager",
    "диспетчер процессов": "task manager", "диспетчер": "task manager",
    "explorer": "explorer", "проводник": "explorer", "папки": "explorer", "файлы": "explorer",
    "мой компьютер": "explorer", "этот компьютер": "explorer",
    "terminal": "terminal", "терминал": "terminal", "консоль": "terminal",
    "powershell": "terminal", "cmd": "terminal", "командная строка": "terminal",
    "settings": "settings", "настройки": "settings", "параметры": "settings", "настройки винды": "settings"
}

def clean_clause_text(text: str) -> str:
    """Removes polite filler words and colloquial particles."""
    t = text.lower().strip()
    fillers = [
        r'\bпожалуйста\b', r'\bпж\b', r'\bплиз\b', r'\bplease\b',
        r'\bсейчас\b', r'\bбыстро\b', r'\bсрочно\b',
        r'\bмне\b', r'\bнам\b', r'\bты\b', r'\bже\b', r'\bка\b', r'\bну-ка\b', r'\bдавай\b',
        r'\bможешь\b', r'\bможешь ли\b', r'\bсможешь\b', r'\bхочу\b', r'\bхотел бы\b',
        r'\bнужно\b', r'\bнадо\b', r'\bпопробуй\b', r'\bбудь добр\b'
    ]
    for pattern in fillers:
        t = re.sub(pattern, '', t, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', t).strip()

def parse_single_clause(clause: str) -> Optional[Dict[str, Any]]:
    """
    Parses an individual action clause locally with support for
    infinitives, imperatives, colloquial words, and slang.
    """
    raw_c = clause.strip().lower()
    c = clean_clause_text(raw_c)
    if not c:
        return None

    # 1. Screenshot / Screen capture
    if any(k in c for k in [
        "скрин", "скриншот", "снимок экрана", "сфоткай экран", "снять экран",
        "заскринь", "заскринить", "сфоткать", "screenshot", "screen shot", "print screen"
    ]):
        return {"type": "screenshot"}

    # 2. Close / Kill applications
    if any(k in c for k in [
        "закрой", "закрыть", "выключи", "выключить", "убей", "прибей",
        "заверши", "завершить", "close", "kill", "exit", "quit"
    ]):
        # Match which app to close
        for app_alias, app_canonical in APP_MAP.items():
            if app_alias in c:
                return {"type": "close_app", "app": app_canonical}
        # Check general browser close
        if "вкладки" in c or "окно" in c:
            return {"type": "close_app", "app": "chrome"}

    # 3. Recycle Bin
    if any(k in c for k in [
        "очисти корзину", "очистить корзину", "почисти корзину", "почистить корзину",
        "опустоши корзину", "опустошить корзину", "удали корзину", "empty recycle", "clean recycle"
    ]):
        return {"type": "empty_recycle"}

    # 4. Lock PC
    if any(k in c for k in [
        "заблокируй", "заблокировать", "залочь", "залочить",
        "lock pc", "lock computer", "экран блокировки"
    ]):
        return {"type": "lock_pc"}

    # 5. Power Commands
    if any(k in c for k in ["выключи пк", "выключить пк", "выключи компьютер", "выключить компьютер", "shutdown pc", "power off"]):
        return {"type": "power", "action": "shutdown"}
    if any(k in c for k in ["перезагрузи пк", "перезагрузить пк", "перезагрузи компьютер", "restart pc", "reboot"]):
        return {"type": "power", "action": "restart"}
    if any(k in c for k in ["отмени выключение", "не выключай", "cancel shutdown", "abort shutdown"]):
        return {"type": "power", "action": "cancel"}

    # 6. Volume Control
    if any(k in c for k in ["volume", "sound", "громкост", "звук", "тише", "громче", "мут", "заглуши", "размут"]):
        # Mute / Unmute
        if any(k in c for k in ["выключи звук", "выключить звук", "без звука", "заглуши", "мут", "mute"]):
            return {"type": "volume_mute"}
        if any(k in c for k in ["включи звук", "включить звук", "размут", "unmute"]):
            return {"type": "volume_mute"}

        # Max / Min
        if any(k in c for k in ["максимум", "на всю", "на полную", "100%", "сто"]):
            return {"type": "volume_set", "level": 100}
        if any(k in c for k in ["минимум", "на ноль", "на 0", "ноль"]):
            return {"type": "volume_set", "level": 0}

        # Numbers
        m_num = re.search(r'\b(\d{1,3})\b', c)
        num = int(m_num.group(1)) if m_num else None

        if any(k in c for k in ["прибавь", "прибавить", "громче", "погромче", "увелич", "увеличить", "up", "louder", "increase"]):
            return {"type": "volume_change", "delta": num or 15}
        if any(k in c for k in ["убавь", "убавить", "тише", "потише", "снизь", "снизить", "уменьши", "уменьшить", "down", "quieter", "decrease"]):
            return {"type": "volume_change", "delta": -(num or 15)}
        if num is not None:
            return {"type": "volume_set", "level": num}

    # 7. Brightness Control
    if any(k in c for k in ["яркост", "подсветк", "brightness", "экран"]):
        m_num = re.search(r'\b(\d{1,3})\b', c)
        num = int(m_num.group(1)) if m_num else None

        if any(k in c for k in ["прибавь", "прибавить", "ярче", "поярче", "увелич", "увеличить", "up", "brighter"]):
            return {"type": "brightness_change", "delta": num or 15}
        if any(k in c for k in ["убавь", "убавить", "темнее", "потемнее", "снизь", "снизить", "уменьши", "уменьшить", "down", "darker"]):
            return {"type": "brightness_change", "delta": -(num or 15)}
        if num is not None:
            return {"type": "brightness_set", "level": num}

    # 8. System Stats / Hardware Telemetry
    if any(k in c for k in [
        "нагрузка пк", "характеристики пк", "загрузка процессора", "сколько памяти",
        "состояние системы", "системные ресурсы", "характеристики", "системная информация",
        "system stats", "pc stats", "cpu usage", "ram usage"
    ]):
        return {"type": "system_stats"}

    # 9. Folders
    if any(k in c for k in ["загрузки", "downloads"]):
        return {"type": "open_folder", "folder": "downloads"}
    if any(k in c for k in ["рабочий стол", "desktop"]) and not any(k in c for k in ["скрин", "сохрани", "save"]):
        return {"type": "open_folder", "folder": "desktop"}
    if any(k in c for k in ["документы", "documents"]):
        return {"type": "open_folder", "folder": "documents"}

    # 10. Media Controls
    if any(k in c for k in ["пауза", "pause", "play", "стоп", "воспроизве", "продолжи музыку", "играй"]):
        return {"type": "media", "action": "play"}
    if any(k in c for k in ["след", "next", "переключи песню", "следующий"]):
        return {"type": "media", "action": "next"}
    if any(k in c for k in ["пред", "prev", "назад", "предыдущий"]):
        return {"type": "media", "action": "prev"}

    # 11. YouTube Searches
    if any(k in c for k in ["ютуб", "youtube"]):
        q = re.sub(r'^(?:найди|найти|поищи|поискать|включи|включить|открой|открыть)?\s*(?:в|на)?\s*(?:ютубе|ютуб|youtube)\s*', '', c).strip()
        q = re.sub(r'\b(ютубе|ютуб|youtube)\b', '', q).strip()
        if q and len(q) > 1:
            return {"type": "open_url", "url": f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"}
        return {"type": "open_url", "url": "https://www.youtube.com"}

    # 12. Google / Web Searches
    if any(k in c for k in ["гугл", "google", "загугли", "загуглить", "погугли", "поищи в интернете", "найди в интернете"]):
        q = re.sub(r'^(?:найди|найти|поищи|поискать|загугли|загуглить|погугли|погуглить|открой|открыть)?\s*(?:в|на)?\s*(?:гугле|гугл|google|интернете|сети)?\s*', '', c).strip()
        q = re.sub(r'\b(гугле|гугл|google)\b', '', q).strip()
        if q and len(q) > 1:
            return {"type": "search_web", "query": q}
        return {"type": "open_url", "url": "https://www.google.com"}

    # 13. Direct URLs & Popular Sites
    if "вк" in c or "vk" in c:
        return {"type": "open_url", "url": "https://vk.com"}
    if "github" in c or "гитхаб" in c:
        return {"type": "open_url", "url": "https://github.com"}
    if "twitch" in c or "твич" in c:
        return {"type": "open_url", "url": "https://twitch.tv"}

    # 14. Launch Application
    # Verbs indicating opening: "открой", "открыть", "запусти", "запустить", "включи", "включить", "open", "launch", "start", "run"
    has_open_verb = any(k in c for k in [
        "открой", "открыть", "запусти", "запустить", "включи", "включить", "стартуй",
        "open", "launch", "start", "run"
    ])
    
    # Or short sentence like "хром", "калькулятор", "браузер"
    is_short = len(c.split()) <= 2

    if has_open_verb or is_short:
        for alias, canonical in APP_MAP.items():
            if alias in c:
                return {"type": "launch_app", "app": canonical}

    # 15. Math Calculation
    m_calc = safe_math_eval(c)
    if m_calc is not None:
        return {"type": "math", "expr": c, "res": m_calc}

    return None

def local_multi_action_planner(user_text: str) -> List[Dict[str, Any]]:
    """
    Intelligently splits complex compound user commands (chaining 2, 3, 4 actions)
    and maps them to sequential atomic executable operations with auto-delays.
    """
    # Conjunction regex: "и потом", "а затем", "после этого", "потом", "затем", "а также", "также", "еще", "and then", "then", "and", "и", ",", ";"
    clauses = re.split(r'\b(и\s+потом|а\s+затем|после\s+этого|потом|затем|а\s+также|также|еще|дальше|and\s+then|then|and|и)\b|[;,]', user_text, flags=re.IGNORECASE)
    actions = []
    
    for clause in clauses:
        if not clause or clause.strip().lower() in ["и", "потом", "затем", "and", "then", "также", "еще", "дальше"]:
            continue
        act = parse_single_clause(clause)
        if act:
            # If an application launch precedes a screenshot, insert automatic wait to allow window rendering
            if act.get("type") == "screenshot" and actions and actions[-1].get("type") in ["launch_app", "open_url"]:
                actions.append({"type": "wait", "seconds": 1.5})
            actions.append(act)

    return actions

# ─── FAST CONVERSATIONAL CHAT (WHEN NOT SYSTEM ACTION) ──────────
CONVERSATIONAL_KNOWLEDGE = {
    "привет": "Приветствую. Все системы Starburn активны. Чем могу помочь?",
    "hello": "Hello. All Starburn systems are operational. How can I assist you?",
    "как дела": "Все модули работают штатно на максимальной производительности. Готов выполнять любые ваши команды.",
    "how are you": "All systems operating at peak performance. Ready for your instructions.",
    "кто ты": "Я Starburn — ваш персональный автономный ИИ-ассистент для управления Windows, автоматизации задач и работы за компьютером.",
    "who are you": "I am Starburn — your personal autonomous AI assistant for Windows control, workflow automation, and productivity.",
    "что ты умеешь": "Я умею управлять компьютером: делать скриншоты экрана на Рабочий стол, открывать и закрывать любые программы (Chrome, Telegram, Discord, VS Code и др.), регулировать громкость и яркость, очищать корзину, блокировать ПК, искать в Google и YouTube, а также предоставлять телеметрию нагрузки процессора и памяти."
}

def get_conversational_reply(raw_text: str, en: bool) -> str:
    """Provides high-quality, crisp, intelligent answers without default emojis."""
    t = raw_text.lower().strip()
    for k, reply in CONVERSATIONAL_KNOWLEDGE.items():
        if k in t:
            return reply

    # Fast free online inference for general questions (timeout 3.5s)
    try:
        payload = {
            "messages": [
                {"role": "system", "content": "Ты — Starburn, высокотехнологичный персональный ИИ-ассистент Windows. Отвечай точно, умно, вежливо и строго БЕЗ ЭМОДЗИ на языке пользователя."},
                {"role": "user", "content": raw_text}
            ],
            "model": "openai"
        }
        req = urllib.request.Request(
            "https://text.pollinations.ai/",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Starburn/2.0"}
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            text = resp.read().decode("utf-8").strip()
            # Clean emojis
            cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', text).strip()
            if cleaned:
                return cleaned
    except Exception:
        pass

    if en:
        return f"Request processed: '{raw_text}'. I can launch or close software, capture screenshots to your Desktop, adjust volume and brightness, or monitor PC health."
    else:
        return f"Запрос обработан: «{raw_text}». Вы можете попросить открыть браузер и сделать скриншот, настроить звук, запустить программы или очистить корзину."

# ─── MAIN MASTER ENTRY POINT ────────────────────────────────────
def process_command(user_text: str, user_name: str = "Пользователь") -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
    """
    Main processing entrypoint.
    Executes local multi-step intent parsing in <1ms for 100% reliable system control,
    with smart conversational fallback.
    """
    raw = user_text.strip()
    en = is_english(raw)

    # 1. First, check if input contains any system actions (single or compound)
    actions_to_run = local_multi_action_planner(raw)

    # 2. If no system actions found, check math
    if not actions_to_run:
        m_calc = safe_math_eval(raw)
        if m_calc is not None:
            reply = f"Result: {m_calc}" if en else f"Результат вычисления: {m_calc}"
            return reply, "math", {"result": m_calc}

    # 3. Check time / date queries
    if not actions_to_run:
        if any(k in raw.lower() for k in ["время", "time", "который час", "сколько времени"]):
            t_str = datetime.datetime.now().strftime("%H:%M")
            return f"Current time is {t_str}." if en else f"Текущее время: {t_str}.", "time", {"time": t_str}

        if any(k in raw.lower() for k in ["число", "дата", "date", "какое число", "какой день"]):
            now = datetime.datetime.now()
            d_str = now.strftime("%d.%m.%Y")
            return f"Today is {d_str}." if en else f"Сегодня: {d_str}.", "date", {"date": d_str}

    # 4. If still no action found, handle conversational query
    if not actions_to_run:
        reply = get_conversational_reply(raw, en)
        return reply, "general", {}

    # 5. Sequentially execute all planned actions
    executed_results = []
    primary_action_type = "multi_action" if len(actions_to_run) > 1 else actions_to_run[0].get("type", "general")
    primary_data = {}

    for act in actions_to_run:
        msg, a_type, a_data = execute_single_action(act)
        if a_type != "noop" and a_type != "wait":
            primary_data.update(a_data)
            # If single action, set exact type
            if len(actions_to_run) == 1:
                primary_action_type = a_type
            elif a_type == "screenshot":
                # Keep screenshot info in primary_data so UI can surface preview
                primary_data["screenshot_path"] = a_data.get("path")
            if msg:
                executed_results.append(msg)

    # 6. Formulate clear Russian/English confirmation
    if executed_results:
        final_reply = ". ".join(executed_results) + "."
    else:
        final_reply = "Все задачи успешно выполнены." if not en else "All tasks completed successfully."

    return final_reply, primary_action_type, primary_data
