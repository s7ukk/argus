import sys
import os
import re
import time
import json
import urllib.request
import urllib.error
import urllib.parse
import datetime
import math
from typing import Optional, List, Dict, Any, Tuple
import backend.system_control as sc
import backend.plugins_manager as pm
import backend.scenarios_manager as sc_mgr
import backend.gui_agent as gui_agent

_AI_QUERY_CACHE: Dict[str, str] = {}
_AI_PLAN_CACHE: Dict[str, Any] = {}

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
    
    if act_type == "clarify":
        return act.get("message", "Какое приложение или сайт вы хотите открыть?"), "clarify", act

    if act_type == "scenario":
        sc_id = act.get("id") or act.get("scenario_id")
        for sc_obj in sc_mgr.load_scenarios():
            if sc_obj.get("id") == sc_id:
                res = sc_mgr.execute_scenario(sc_obj)
                return res["summary"], "scenario", res
        return "Сценарий не найден", "scenario", {}

    if act_type == "launch_app":
        app = act.get("app", "chrome")
        res = sc.launch_application(app)
        app_disp = app.capitalize()
        if app.lower() in ["chrome", "хром", "браузер", "browser", "хром браузер"]:
            app_disp = "Chrome"
        elif app.lower() in ["telegram", "телеграм", "телега", "тг"]:
            app_disp = "Telegram"
        elif app.lower() in ["discord", "дискорд"]:
            app_disp = "Discord"
        elif app.lower() in ["vscode", "код", "vs code"]:
            app_disp = "VS Code"
        elif app.lower() in ["goland", "голенд", "голэнд"]:
            app_disp = "GoLand"
        elif app.lower() in ["postman", "постман"]:
            app_disp = "Postman"

        if res.get("success"):
            return f"Запущено приложение: {app_disp}", "launch_app", res
        else:
            return f"Не удалось открыть {app_disp}: {res.get('error', 'приложение не найдено')}", "launch_app", res

    elif act_type == "close_app":
        app = act.get("app", "")
        res = sc.close_application(app)
        app_disp = app.capitalize()
        if app.lower() in ["vscode", "код", "vs code"]:
            app_disp = "VS Code"
        elif app.lower() in ["chrome", "хром", "браузер"]:
            app_disp = "Chrome"
        return f"Закрыто приложение: {app_disp}", "close_app", res

    elif act_type == "browser_choice":
        browsers = act.get("browsers", [])
        b_names = "\n".join([f"• {b['name']}" for b in browsers])
        msg = f"На вашем компьютере обнаружены следующие браузеры:\n{b_names}\n\nКакой именно браузер открыть? (Например: «Открой {browsers[0]['name']}» или «Открой {browsers[-1]['name']}»)"
        return msg, "browser_choice", {"browsers": browsers}

    elif act_type == "close_browser_tab":
        ok = sc.close_browser_tab()
        return "Вкладка браузера закрыта", "close_tab", {"success": ok}

    elif act_type == "new_browser_tab":
        ok = sc.new_browser_tab()
        return "Открыта новая вкладка в браузере", "new_tab", {"success": ok}

    elif act_type == "refresh_page":
        ok = sc.refresh_browser_page()
        return "Страница в браузере обновлена", "refresh_page", {"success": ok}

    elif act_type == "switch_browser_tab":
        direction = act.get("direction", "next")
        ok = sc.switch_browser_tab(direction)
        return f"Переключена вкладка браузера", "switch_tab", {"direction": direction}

    elif act_type == "scroll_page":
        direction = act.get("direction", "down")
        ok = sc.scroll_browser_page(direction)
        dir_ru = "вниз" if direction == "down" else "вверх"
        return f"Страница прокручена {dir_ru}", "scroll", {"direction": direction}

    elif act_type == "click_website_button":
        btn = act.get("button", "").strip()
        ok = sc.click_website_button(btn)
        return f"Нажата кнопка «{btn}» на открытой веб-странице", "click_button", {"button": btn, "success": ok}

    elif act_type == "terminal_command":
        cmd = act.get("command", "")
        shell = act.get("shell")
        res = sc.execute_terminal_command(cmd, shell_type=shell)
        out_text = res.get("output") or res.get("error") or "Команда выполнена успешно (без вывода)"
        if len(out_text) > 400:
            out_text = out_text[:400] + "..."
        status_word = "успешно" if res.get("success") else "с ошибкой"
        return f"Команда терминала выполнена {status_word}:\n```\n{out_text}\n```", "terminal_command", res

    elif act_type == "close_all_except":
        keep = act.get("keep", [])
        res = sc.close_all_except(keep)
        keep_str = ", ".join([k.upper() if k.lower() == "vscode" else k.capitalize() for k in keep])
        return f"Закрыты все приложения кроме: {keep_str}", "close_all_except", res

    elif act_type == "screenshot":
        folder = act.get("folder", "desktop")
        path = sc.take_screenshot(folder)
        folder_disp = "в Загрузки" if "download" in folder or "загруз" in folder else "в Документы" if "doc" in folder or "документ" in folder else "в Изображения" if "pic" in folder or "изображен" in folder or "картинк" in folder else "на Рабочий стол"
        return f"Снимок экрана сохранен {folder_disp}: {path}", "screenshot", {"path": path, "folder": folder}

    elif act_type == "wait":
        sec = min(5.0, max(0.2, float(act.get("seconds", 1.5))))
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
        return ("Корзина macOS очищена" if sys.platform == "darwin" else "Корзина очищена"), "empty_recycle", {}

    elif act_type == "lock_pc":
        sc.lock_workstation()
        return "Компьютер заблокирован", "system_lock", {}

    elif act_type == "open_url":
        url = act.get("url", "https://google.com")
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        sc.open_url(url)
        return f"Открыта страница: {url}", "open_url", {"url": url}

    elif act_type == "search_web":
        q = act.get("query", "")
        engine = act.get("engine", "google").lower()
        if "yandex" in engine or "яндекс" in engine:
            url = f"https://yandex.ru/search/?text={urllib.parse.quote_plus(q)}"
            eng_name = "в Яндекс"
        elif "youtube" in engine or "ютуб" in engine:
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
            eng_name = "в YouTube"
        elif "wildberries" in engine or "вайлдберриз" in engine or "вб" in engine:
            url = f"https://www.wildberries.ru/catalog/0/search.aspx?search={urllib.parse.quote_plus(q)}"
            eng_name = "на Wildberries"
        elif "ozon" in engine or "озон" in engine:
            url = f"https://www.ozon.ru/search/?text={urllib.parse.quote_plus(q)}"
            eng_name = "на Ozon"
        elif "avito" in engine or "авито" in engine:
            url = f"https://www.avito.ru/rossiya?q={urllib.parse.quote_plus(q)}"
            eng_name = "на Авито"
        elif "github" in engine or "гитхаб" in engine:
            url = f"https://github.com/search?q={urllib.parse.quote_plus(q)}"
            eng_name = "на GitHub"
        else:
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
            eng_name = "в Google"
        sc.open_url(url)
        return f"Выполнен поиск {eng_name}: «{q}»", "open_url", {"url": url, "query": q}

    elif act_type == "messenger_send":
        messenger = act.get("messenger", "auto").lower()
        contact = act.get("contact", "").strip()
        msg_text = act.get("message", "").strip()
        
        # 1. If messenger is "auto" or generic, pick active or installed messenger
        if messenger in ["auto", "any", "мессенджер", "chat"]:
            fg = sc.get_foreground_window_title().lower()
            if any(m in fg for m in ["discord", "дискорд"]):
                messenger = "discord"
            elif any(m in fg for m in ["whatsapp", "ватсап"]):
                messenger = "whatsapp"
            elif any(m in fg for m in ["vk", "вконтакте"]):
                messenger = "vk"
            else:
                messenger = "telegram"

        # 2. Execute via Autonomous Visual GUI Computer-Use Agent
        res = gui_agent.execute_autonomous_messenger_task(messenger, contact, msg_text)
        return res["summary"], "messenger_send", res

    elif act_type == "autonomous_browser_task":
        browser = act.get("browser", "safari")
        query = act.get("query", "")
        res = gui_agent.execute_autonomous_browser_task(browser, query)
        return res["summary"], "autonomous_browser_task", res

    elif act_type == "autonomous_notes_task":
        text = act.get("text", "")
        title = act.get("title")
        res = gui_agent.execute_autonomous_notes_task(text, title)
        return res["summary"], "autonomous_notes_task", res

    elif act_type == "open_folder":
        folder = act.get("folder", "desktop")
        sc.open_folder(folder)
        return f"Открыта папка: {folder}", "open_folder", {"folder": folder}

    elif act_type in ["media", "play_music"]:
        m_act = act.get("action", "play")
        service = act.get("service", "auto")
        query = act.get("query", "")
        playlist = act.get("playlist", "")
        res = sc.play_music(service=service, query=query, playlist=playlist, action=m_act)
        return res["message"], "play_music", res

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

    elif act_type == "type_text":
        text = act.get("text", "")
        target_app = act.get("target_app") or act.get("app")
        field = act.get("field")
        success = sc.type_text(text, target_app=target_app, field=field)
        if act.get("press_enter"):
            time.sleep(0.12)
            sc.press_key("enter")
        enter_note = " и нажат Enter" if act.get("press_enter") else ""
        app_note = f" в {target_app}" if target_app else ""
        return f"Напечатан текст{app_note}{enter_note}: «{text}»", "type_text", {"text": text, "target_app": target_app, "success": success, "press_enter": act.get("press_enter", False)}

    elif act_type == "press_key":
        key = act.get("key", "enter")
        success = sc.press_key(key)
        return f"Нажата клавиша: {key.upper()}", "press_key", {"key": key, "success": success}

    elif act_type == "hotkey":
        keys = act.get("keys", ["ctrl", "c"])
        success = sc.send_hotkey(*keys)
        keys_str = " + ".join([k.upper() for k in keys])
        return f"Выполнено сочетание клавиш: {keys_str}", "hotkey", {"keys": keys, "success": success}

    elif act_type == "plugin_start":
        p_name = act.get("plugin_name", "")
        # Find matching plugin in local plugins
        all_p = pm.list_plugins()
        matched = None
        for p in all_p:
            if p_name.lower() in p["name"].lower() or p_name.lower() in p["id"].lower():
                matched = p
                break
        if matched:
            res = pm.start_plugin(matched["id"])
            if res.get("success"):
                return f"Плагин «{matched['name']}» запущен (PID: {res.get('pid')})", "plugin_start", res
            return f"Ошибка запуска плагина «{matched['name']}»: {res.get('error')}", "plugin_start", res
        return f"Локальный плагин «{p_name}» не найден", "plugin_start", {"error": "not_found"}

    elif act_type == "plugin_stop":
        p_name = act.get("plugin_name", "")
        all_p = pm.list_plugins()
        matched = None
        for p in all_p:
            if p_name.lower() in p["name"].lower() or p_name.lower() in p["id"].lower():
                matched = p
                break
        if matched:
            res = pm.stop_plugin(matched["id"])
            return f"Плагин «{matched['name']}» остановлен", "plugin_stop", res
        return f"Локальный плагин «{p_name}» не найден", "plugin_stop", {"error": "not_found"}

    elif act_type == "plugin_list":
        plugins = pm.list_plugins()
        if not plugins:
            return "У вас пока нет установленных локальных плагинов. Загрузите скрипт во вкладке «Плагины».", "plugin_list", {"plugins": []}
        summary = ", ".join([f"{p['name']} [{p['status']}]" for p in plugins])
        return f"Локальные плагины на ПК: {summary}", "plugin_list", {"plugins": plugins}

    elif act_type == "create_file":
        path = act.get("path", "file.txt")
        content = act.get("content", "")
        res = sc.create_file(path, content)
        if res.get("success"):
            return f"Файл создан: {res.get('path')}", "create_file", res
        return f"Не удалось создать файл: {res.get('error')}", "create_file", res

    elif act_type == "create_folder":
        path = act.get("path", "Новая папка")
        res = sc.create_folder(path)
        if res.get("success"):
            return f"Папка создана: {res.get('path')}", "create_folder", res
        return f"Не удалось создать папку: {res.get('error')}", "create_folder", res

    elif act_type == "delete_file":
        path = act.get("path", "")
        res = sc.delete_file_or_folder(path)
        if res.get("success"):
            return f"Удалено: {res.get('path')}", "delete_file", res
        return f"Не удалось удалить: {res.get('error')}", "delete_file", res

    elif act_type == "analyze_file":
        path = act.get("path", "")
        res = sc.analyze_file(path)
        if res.get("success"):
            prev = f"\n```\n{res.get('preview')[:250]}\n```" if res.get('preview') else ""
            return f"Файл «{res.get('name')}» ({res.get('size_kb')} КБ, строк: {res.get('lines')}){prev}", "analyze_file", res
        return f"Не удалось проанализировать файл: {res.get('error')}", "analyze_file", res

    elif act_type == "list_files":
        folder = act.get("folder", "desktop")
        res = sc.list_folder_files(folder)
        if res.get("success"):
            files_list = ", ".join(res.get("files", [])[:12]) or "нет файлов"
            dirs_list = ", ".join(res.get("folders", [])[:6]) or "нет папок"
            return f"Содержимое папки {res.get('folder_name')} (всего {res.get('total')}):\n• Файлы: {files_list}\n• Папки: {dirs_list}", "list_files", res
        return f"Не удалось получить список файлов: {res.get('error')}", "list_files", res

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
    "soundcloud": "soundcloud", "саундклауд": "soundcloud", "саунд клауд": "soundcloud", "sound cloud": "soundcloud",
    "yandex music": "yandex music", "яндекс музыка": "yandex music", "я музыка": "yandex music",
    # Productivity & Dev
    "vscode": "vscode", "vs code": "vscode", "код": "vscode", "вскод": "vscode", "visual studio code": "vscode",
    "goland": "goland", "go land": "goland", "голенд": "goland", "голэнд": "goland", "jetbrains goland": "goland",
    "pycharm": "pycharm", "py charm": "pycharm", "пайчарм": "pycharm", "jetbrains pycharm": "pycharm",
    "webstorm": "webstorm", "web storm": "webstorm", "вебшторм": "webstorm", "jetbrains webstorm": "webstorm",
    "postman": "postman", "post man": "postman", "постман": "postman",
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

KNOWN_KEYBOARD_KEYS = {
    "enter", "return", "ввод", "ентер", "ентр",
    "esc", "escape", "эскейп",
    "tab", "таб",
    "space", "пробел",
    "backspace", "бэкспейс", "стереть",
    "delete", "делит",
    "up", "вверх", "стрелка вверх",
    "down", "вниз", "стрелка вниз",
    "left", "влево", "стрелка влево",
    "right", "вправо", "стрелка вправо",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "ctrl", "alt", "shift", "win", "windows"
}

def clean_clause_text(text: str) -> str:
    """Removes polite filler words and colloquial particles."""
    t = text.lower().strip()
    fillers = [
        r'\bпожалуйста\b', r'\bпж\b', r'\bплиз\b', r'\bplease\b',
        r'\bсейчас\b', r'\bбыстро\b', r'\bсрочно\b', r'\bзаебал\b', r'\bбля\b', r'\bблин\b',
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
    infinitives, imperatives, colloquial words, negative filters, and slang.
    """
    orig_c = clause.strip()
    raw_c = orig_c.lower()
    c = clean_clause_text(raw_c)
    if not c:
        return None

    # 0. "Закрой все кроме X" (Negative Exclusion Filter)
    if any(k in c for k in ["кроме", "except", "не закрывай", "за исключением"]):
        if any(v in c for k in ["закрой", "закрыть", "выключи", "выключить", "убей", "заверши"] for v in [k]):
            # Find what to keep
            keep_list = []
            for alias, canonical in APP_MAP.items():
                if alias in c:
                    keep_list.append(canonical)
            if keep_list:
                return {"type": "close_all_except", "keep": list(set(keep_list))}

    # 1. Screenshot / Screen capture with folder detection
    if any(k in c for k in [
        "скрин", "скриншот", "снимок экрана", "сфоткай экран", "снять экран",
        "заскринь", "заскринить", "сфоткать", "screenshot", "screen shot", "print screen"
    ]):
        folder = "desktop"
        if any(f in c for f in ["загрузк", "загруз", "download"]):
            folder = "downloads"
        elif any(f in c for f in ["документ", "document"]):
            folder = "documents"
        elif any(f in c for f in ["изображен", "картинк", "picture"]):
            folder = "pictures"
        return {"type": "screenshot", "folder": folder}

    # 1.1 Save destination specification (e.g. "сохрани его в папку загрузки")
    if any(k in c for k in ["сохрани", "сохранить", "save"]) and not any(k in c for k in ["файл", "file", "код"]):
        folder = "desktop"
        if any(f in c for f in ["загрузк", "загруз", "download"]):
            folder = "downloads"
        elif any(f in c for f in ["документ", "document"]):
            folder = "documents"
        elif any(f in c for f in ["изображен", "картинк", "picture"]):
            folder = "pictures"
        return {"type": "save_destination", "folder": folder}

    # 1.2 Browser Tabs & Page Navigation
    if any(k in c for k in ["закрой вкладку", "закрыть вкладку", "закрой эту вкладку", "закрыть эту вкладку", "закрой страницу", "закрыть страницу", "close tab", "закрой ютуб", "закрыть ютуб", "закрой youtube", "закрыть youtube", "закрой саундклауд", "закрыть саундклауд", "закрой soundcloud", "закрой вк", "закрыть вк"]):
        return {"type": "close_browser_tab"}
    if any(k in c for k in ["новая вкладка", "новую вкладку", "открой вкладку", "открыть новую вкладку", "new tab"]):
        return {"type": "new_browser_tab"}
    if any(k in c for k in ["обнови страницу", "обновить страницу", "перезагрузи страницу", "обнови вкладку", "refresh page", "reload page"]):
        return {"type": "refresh_page"}
    if any(k in c for k in ["следующая вкладка", "следующую вкладку", "переключи вкладку", "переключить вкладку", "next tab"]):
        return {"type": "switch_browser_tab", "direction": "next"}
    if any(k in c for k in ["предыдущая вкладка", "предыдущую вкладку", "prev tab", "previous tab"]):
        return {"type": "switch_browser_tab", "direction": "prev"}
    if any(k in c for k in ["скролл вниз", "прокрути вниз", "прокрутить вниз", "листай вниз", "scroll down"]):
        return {"type": "scroll_page", "direction": "down"}
    if any(k in c for k in ["скролл вверх", "прокрути вверх", "прокрутить вверх", "листай вверх", "scroll up"]):
        return {"type": "scroll_page", "direction": "up"}

    # 1.3 Click button / link / element on website or app, or press key
    btn_m = re.match(r'^(?:нажми\s+(?:на\s+кнопку|кнопку|на\s+ссылку|ссылку|на|по)?|кликни\s+(?:на\s+кнопку|кнопку|по\s+кнопке|на\s+ссылку|по\s+ссылке|ссылку|на|по)?|click\s+(?:on\s+button|button|on\s+link|link|on)?)\s*(.+)$', c)
    if btn_m:
        target = btn_m.group(1).strip().strip('"\'')
        target = re.sub(r'\s+(?:на\s+сайте|в\s+браузере|на\s+странице)$', '', target).strip()
        target_lower = target.lower()
        if "+" in target_lower and all(len(p.strip()) <= 8 for p in target_lower.split("+")):
            return {"type": "hotkey", "keys": [k.strip() for k in target_lower.split("+")]}
        if target_lower in KNOWN_KEYBOARD_KEYS:
            key_mapped = "enter" if target_lower in ["ентер", "ввод", "ентр", "return"] else \
                         "esc" if target_lower in ["эскейп", "escape"] else \
                         "tab" if target_lower in ["таб"] else \
                         "space" if target_lower in ["пробел"] else \
                         "backspace" if target_lower in ["бэкспейс", "стереть"] else target_lower
            return {"type": "press_key", "key": key_mapped}
        if target:
            return {"type": "click_website_button", "button": target}

    # 1.4 Terminal Execution (PowerShell, Bash, CMD)
    if any(c.startswith(k) for k in ["в терминале:", "в терминале ", "терминал:", "терминал ", "команда:", "powershell:", "bash:"]):
        cmd_text = re.sub(r'^(?:выполни\s+)?(?:в\s+терминале|терминал|команда|powershell|bash)[:\s]+', '', raw_c).strip()
        shell_choice = "bash" if "bash" in c else "powershell"
        if cmd_text:
            return {"type": "terminal_command", "command": cmd_text, "shell": shell_choice}

    # 2. Close / Kill applications
    if any(k in c for k in [
        "закрой", "закрыть", "выключи", "выключить", "убей", "прибей",
        "заверши", "завершить", "close", "kill", "exit", "quit"
    ]):
        if any(k in c for k in ["ютуб", "youtube", "саундклауд", "soundcloud", "вкладку", "страницу", "сайт"]):
            return {"type": "close_browser_tab"}
        for app_alias, app_canonical in APP_MAP.items():
            if app_alias in c:
                return {"type": "close_app", "app": app_canonical}
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
        if any(k in c for k in ["выключи звук", "выключить звук", "без звука", "заглуши", "мут", "mute"]):
            return {"type": "volume_mute"}
        if any(k in c for k in ["включи звук", "включить звук", "размут", "unmute"]):
            return {"type": "volume_mute"}

        if any(k in c for k in ["максимум", "на всю", "на полную", "полную", "полная", "на максимум", "100%", "сто", "на сотку", "максимальн"]):
            return {"type": "volume_set", "level": 100}
        if any(k in c for k in ["минимум", "на минимум", "на ноль", "на 0", "ноль", "в ноль", "минимальн"]):
            return {"type": "volume_set", "level": 0}
        if any(k in c for k in ["наполовину", "половина", "на 50", "средн"]):
            return {"type": "volume_set", "level": 50}

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
        if any(k in c for k in ["максимум", "на всю", "на полную", "полную", "полная", "на максимум", "100%", "сто", "на сотку", "максимальн"]):
            return {"type": "brightness_set", "level": 100}
        if any(k in c for k in ["минимум", "на минимум", "на ноль", "на 0", "ноль", "в ноль", "минимальн"]):
            return {"type": "brightness_set", "level": 10}
        if any(k in c for k in ["наполовину", "половина", "на 50", "средн"]):
            return {"type": "brightness_set", "level": 50}

        m_num = re.search(r'\b(\d{1,3})\b', c)
        num = int(m_num.group(1)) if m_num else None

        if any(k in c for k in ["прибавь", "прибавить", "ярче", "поярче", "увелич", "увеличить", "up", "brighter"]):
            return {"type": "brightness_change", "delta": num or 15}
        if any(k in c for k in ["убавь", "убавить", "темнее", "потемнее", "снизь", "снизить", "уменьши", "уменьшить", "down", "darker"]):
            return {"type": "brightness_change", "delta": -(num or 15)}
        if num is not None:
            return {"type": "brightness_set", "level": num}

    # 7.1 File & Directory Operations (Create, Delete, Inspect, List)
    # Create file: "создай файл notes.txt с текстом Привет на рабочем столе"
    if any(k in c for k in ["создай файл", "создать файл", "сделай файл", "сохрани в файл", "запиши файл", "create file"]):
        m_cf = re.search(r'(?:создай|создать|сделай|запиши)\s+(?:текстовый\s+)?файл\s+([^\s]+)(?:\s+(?:с\s+текстом|с\s+содержимым|текст)?\s+(.+?))?(?:\s+(?:на\s+рабочем\s+столе|в\s+загрузках|в\s+документах))?$', raw_c, re.IGNORECASE)
        target = "file.txt"
        content = ""
        if m_cf:
            target = m_cf.group(1).strip('"\'«»')
            if m_cf.group(2):
                content = m_cf.group(2).strip().strip('"\'«»')
        else:
            parts = c.split()
            for p in parts:
                if "." in p and len(p) > 2:
                    target = p.strip('"\'«»')
                    break
        if "на рабочем столе" in c or "на рабочий стол" in c or "desktop" in c:
            target = "на рабочем столе " + target
        elif "в загрузках" in c or "в загрузки" in c or "downloads" in c:
            target = "в загрузках " + target
        elif "в документах" in c or "в документы" in c:
            target = "в документах " + target
        return {"type": "create_file", "path": target, "content": content}

    # Create folder: "создай папку Проект на рабочем столе"
    if any(k in c for k in ["создай папку", "создать папку", "сделай папку", "новая папка", "create folder", "mkdir"]):
        m_cd = re.search(r'(?:создай|создать|сделай|новая)\s+папк[ау]\s+([^\s]+)(?:\s+(?:на\s+рабочем\s+столе|в\s+загрузках|в\s+документах))?', raw_c, re.IGNORECASE)
        f_name = "Новая папка"
        if m_cd:
            f_name = m_cd.group(1).strip('"\'«»')
        if "на рабочем столе" in c or "на рабочий стол" in c:
            f_name = "на рабочем столе " + f_name
        elif "в загрузках" in c or "в загрузки" in c:
            f_name = "в загрузках " + f_name
        elif "в документах" in c or "в документы" in c:
            f_name = "в документах " + f_name
        return {"type": "create_folder", "path": f_name}

    # Delete file or folder: "удали файл test.txt", "удали папку Test"
    if any(k in c for k in ["удали файл", "удалить файл", "сотри файл", "удали папку", "удалить папку", "delete file"]):
        m_del = re.search(r'(?:удали|удалить|сотри)\s+(?:файл|папку)\s+(.+)', raw_c, re.IGNORECASE)
        target = ""
        if m_del:
            target = m_del.group(1).strip().strip('"\'«»')
        return {"type": "delete_file", "path": target}

    # Analyze / inspect file: "проанализируй файл ...", "проверь файл ...", "посмотри файл ..."
    if any(k in c for k in ["проанализируй файл", "анализ файла", "проверь файл", "посмотри файл", "покажи что в файле", "прочитай файл"]):
        m_af = re.search(r'(?:проанализируй|анализ|проверь|посмотри|покажи что в|прочитай)\s+(?:файл[еа]?\s+)?(.+)', raw_c, re.IGNORECASE)
        target = ""
        if m_af:
            target = m_af.group(1).strip().strip('"\'«»')
        return {"type": "analyze_file", "path": target}

    # List folder files: "список файлов на рабочем столе", "какие файлы в загрузках"
    if any(k in c for k in ["список файлов", "какие файлы", "покажи файлы", "файлы на рабочем столе", "файлы в загрузках", "файлы в документах"]):
        target = "desktop"
        if any(f in c for f in ["загрузк", "загруз", "download"]):
            target = "downloads"
        elif any(f in c for f in ["документ", "document"]):
            target = "documents"
        return {"type": "list_files", "folder": target}

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
    if any(k in c for k in ["рабочий стол", "desktop"]) and not any(k in c for k in ["скрин", "сохрани", "save", "файл", "папк"]):
        return {"type": "open_folder", "folder": "desktop"}
    if any(k in c for k in ["документы", "documents"]):
        return {"type": "open_folder", "folder": "documents"}

    # 10. Universal Music & Media Controls
    # 10.1 Stop / Pause / Turn off music
    if any(k in c for k in [
        "выключи музыку", "выключить музыку", "отключи музыку", "останови музыку", "остановить музыку",
        "выруби музыку", "заглуши музыку", "выключи песню", "останови песню", "выруби трек", "выключи трек",
        "выключи то что сейчас играет", "выключи то что играет", "останови то что сейчас играет", "останови то что играет",
        "поставь на паузу", "поставить на паузу", "на паузу", "пауза", "pause", "стоп музыка", "останови воспроизведение"
    ]):
        return {"type": "play_music", "action": "pause"}

    # 10.2 Next track
    if any(k in c for k in [
        "следующий трек", "следующая песня", "следующую песню", "переключи трек", "переключи песню",
        "следующий", "next track", "скипни трек", "скипни песню", "скип трек", "скипни"
    ]) or (c in ["след", "next", "скип", "дальше"]):
        return {"type": "play_music", "action": "next"}

    # 10.3 Previous track
    if any(k in c for k in [
        "предыдущий трек", "предыдущая песня", "предыдущую песню", "прошлый трек", "прошлая песня",
        "верни трек", "верни песню", "prev track", "предыдущий", "назад песню"
    ]) or (c in ["пред", "prev", "назад"]):
        return {"type": "play_music", "action": "prev"}

    # 10.4 Resume / Continue playing
    if any(k in c for k in [
        "продолжи музыку", "продолжить музыку", "возобнови музыку", "возобновить музыку",
        "продолжи играть", "играй дальше", "сними с паузы", "возобнови трек", "продолжи трек"
    ]):
        return {"type": "play_music", "action": "resume"}

    # 10.5 Service & Playlist / Track Detection
    music_service = "auto"
    if any(k in c for k in ["спотифай", "spotify", "спотифае"]):
        music_service = "spotify"
    elif any(k in c for k in ["яндекс музык", "яндекс.музык", "я.музык", "ямузык", "yandex music"]):
        music_service = "yandex"
    elif any(k in c for k in ["саундклауд", "саундклауде", "саунд клауд", "soundcloud"]):
        music_service = "soundcloud"
    elif any(k in c for k in ["вк музык", "vk music", "музык вк", "музыку вк"]):
        music_service = "vk"
    elif any(k in c for k in ["ютуб музык", "youtube music"]):
        music_service = "youtube"

    # Playlists: "включи плейлист рок", "выбери плейлист для тренировок в спотифай"
    if any(k in c for k in ["плейлист", "playlist"]):
        m_pl = re.search(r'(?:включи|поставь|открой|выбери|запусти|найди|слушай)?\s*плейлист\s+(.+?)(?:\s+(?:в|на)\s+(?:спотифай|spotify|яндекс|soundcloud|саундклауд|вк|ютуб|youtube).*)?$', raw_c, re.IGNORECASE)
        pl_name = ""
        if m_pl:
            pl_name = m_pl.group(1).strip()
            pl_name = re.sub(r'\b(?:в|на)\s+(?:спотифа[еяй]|spotify|яндекс[е]?\s*(?:музык[еау])?|саундклауд[е]?|soundcloud|вк|vk|ютуб[е]?|youtube)\b', '', pl_name, flags=re.IGNORECASE).strip()
            pl_name = pl_name.strip('"\'«»')
        return {"type": "play_music", "service": music_service, "playlist": pl_name, "action": "play"}

    # Specific track / song request: "включи песню ...", "включи трек ...", "поставь песню ..."
    m_track = re.search(r'^(?:включи|включить|поставь|поставить|запусти|запустить|вруби|врубить|сыграй|найди\s+и\s+включи)\s+(?:песню|трек|композицию|музыку)\s+(.+)$', raw_c, re.IGNORECASE)
    if m_track:
        track_query = m_track.group(1).strip()
        track_query = re.sub(r'\b(?:в|на)\s+(?:спотифа[еяй]|spotify|яндекс[е]?\s*(?:музык[еау])?|саундклауд[е]?|soundcloud|вк|vk|ютуб[е]?|youtube)\b', '', track_query, flags=re.IGNORECASE).strip()
        track_query = track_query.strip('"\'«»')
        if track_query and track_query not in ["спотифай", "spotify", "яндекс музыка", "саундклауд", "soundcloud"]:
            return {"type": "play_music", "service": music_service, "query": track_query, "action": "play"}

    # Explicit service search: e.g. "включи рамштайн в спотифай" or "поставь фонк в саундклауд"
    if music_service != "auto" and any(verb in c for verb in ["включи", "поставь", "найди", "запусти", "послушай", "play"]):
        clean_q = re.sub(r'^(?:включи|включить|поставь|поставить|найди|найти|запусти|запустить|открой|открыть|послушай|послушать|play)\s+', '', raw_c, flags=re.IGNORECASE).strip()
        clean_q = re.sub(r'\b(?:в|на)?\s*(?:спотифа[еяй]|spotify|яндекс[е]?\s*(?:музык[еау])?|саундклауд[е]?|soundcloud|вк|vk|ютуб[е]?|youtube)\b', '', clean_q, flags=re.IGNORECASE).strip()
        clean_q = clean_q.strip('"\'«»')
        if clean_q and len(clean_q) > 1:
            return {"type": "play_music", "service": music_service, "query": clean_q, "action": "play"}
        else:
            return {"type": "play_music", "service": music_service, "action": "play"}

    # Direct service open / launch: "открой спотифай", "включи спотифай", "открой яндекс музыку"
    if any(k in c for k in ["спотифай", "spotify"]) and any(verb in c for verb in ["открой", "запусти", "включи", "open", "launch"]):
        return {"type": "play_music", "service": "spotify", "action": "play"}
    if any(k in c for k in ["яндекс музыка", "яндекс музыку", "yandex music"]) and any(verb in c for verb in ["открой", "запусти", "включи", "open", "launch"]):
        return {"type": "play_music", "service": "yandex", "action": "play"}
    if any(k in c for k in ["саундклауд", "саунд клауд", "soundcloud"]) and any(verb in c for verb in ["открой", "запусти", "включи", "open", "launch"]):
        return {"type": "play_music", "service": "soundcloud", "action": "play"}

    # General "включи музыку" / "поставь музыку"
    if any(k in c for k in ["включи музыку", "включить музыку", "поставь музыку", "поставить музыку", "запусти музыку", "запустить музыку", "play music"]):
        return {"type": "play_music", "service": "auto", "action": "play"}

    # 11. Direct Web URLs & Popular Sites (Evaluated BEFORE general search & app launch to prevent URLs from becoming apps)
    # Check explicit website opening command e.g. 'открой сайт "ссылка"', 'открой сайт хабр'
    site_pattern = r'^(?:открой|открыть|перейди\s+на|перейди|зайди\s+на|зайди|open)\s+(?:сайт|страниц[уа]|ссылк[уа])\s*(.*)$'
    m_site = re.match(site_pattern, c, re.IGNORECASE)
    if m_site:
        site_raw = m_site.group(1).strip().strip('"\'«»“”<> ')
        if not site_raw:
            return {"type": "launch_app", "app": "chrome"}
        site_aliases = {
            "вк": "https://vk.com", "vk": "https://vk.com",
            "ютуб": "https://youtube.com", "youtube": "https://youtube.com",
            "гугл": "https://google.com", "google": "https://google.com",
            "яндекс": "https://yandex.ru", "yandex": "https://yandex.ru",
            "хабр": "https://habr.com", "habr": "https://habr.com",
            "кинопоиск": "https://kinopoisk.ru",
            "тг": "https://web.telegram.org", "телеграм": "https://web.telegram.org", "телега": "https://web.telegram.org",
            "гитхаб": "https://github.com", "github": "https://github.com",
            "реддит": "https://reddit.com", "reddit": "https://reddit.com",
            "твич": "https://twitch.tv", "twitch": "https://twitch.tv",
            "рутуб": "https://rutube.ru", "rutube": "https://rutube.ru",
            "вайлдберриз": "https://wildberries.ru", "вб": "https://wildberries.ru", "wildberries": "https://wildberries.ru",
            "озон": "https://ozon.ru", "ozon": "https://ozon.ru",
            "авито": "https://avito.ru", "avito": "https://avito.ru"
        }
        if site_raw.lower() in site_aliases:
            return {"type": "open_url", "url": site_aliases[site_raw.lower()]}
        url_match = re.search(r'(https?://[^\s"\'«»]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s"\'«»]*)?)', site_raw)
        if url_match:
            u = url_match.group(1).strip('"\'«»“”<> ')
            if not u.startswith("http://") and not u.startswith("https://"):
                u = "https://" + u
            return {"type": "open_url", "url": u}
        # If site name has no domain, search Google for it
        return {"type": "search_web", "query": site_raw, "engine": "google"}

    # General URL in text
    m_url = re.search(r'(https?://[^\s"\'«»]+|(?:www\.)?[a-zA-Z0-9-]+\.(?:ru|com|org|net|io|me|ai|app|dev|by|kz|xyz|top|online|site|tech)(?:/[^\s"\'«»]*)?)', c)
    if m_url and any(verb in c for verb in ["открой", "перейди", "зайди", "open", "сайт", "ссылк", "http", "www", "браузер"]):
        url_dest = m_url.group(1).strip('"\'«»“”<> ')
        if not url_dest.startswith("http://") and not url_dest.startswith("https://"):
            url_dest = "https://" + url_dest
        return {"type": "open_url", "url": url_dest}

    if re.search(r'\b(вк|vk)\b', c) and (c.strip() in ["вк", "vk"] or any(verb in c for verb in ["открой", "зайди", "перейди", "open"])):
        return {"type": "open_url", "url": "https://vk.com"}
    if re.search(r'\b(github|гитхаб)\b', c) and (c.strip() in ["гитхаб", "github"] or any(verb in c for verb in ["открой", "зайди", "перейди", "open"])):
        return {"type": "open_url", "url": "https://github.com"}
    if re.search(r'\b(twitch|твич)\b', c) and (c.strip() in ["твич", "twitch"] or any(verb in c for verb in ["открой", "зайди", "перейди", "open"])):
        return {"type": "open_url", "url": "https://twitch.tv"}
    if re.search(r'\b(rutube|рутуб)\b', c) and (c.strip() in ["рутуб", "rutube"] or any(verb in c for verb in ["открой", "зайди", "перейди", "open"])):
        return {"type": "open_url", "url": "https://rutube.ru"}
    if re.search(r'\b(reddit|реддит)\b', c) and (c.strip() in ["реддит", "reddit"] or any(verb in c for verb in ["открой", "зайди", "перейди", "open"])):
        return {"type": "open_url", "url": "https://reddit.com"}

    # 12. Web Searches across Popular Platforms (YouTube, Google, Yandex, Wildberries, Ozon, Avito, GitHub)
    if any(k in c for k in ["ютуб", "youtube"]) and not any(k in c for k in ["закрой", "закрыть", "close", "выключи", "заверши", "адресн", "строк", "ссылк", "вставить", "напечатай в"]):
        q = re.sub(r'\b(ютубе|ютуб|youtube)\b', '', c, flags=re.IGNORECASE)
        q = re.sub(r'^(?:открой|открыть|перейди|зайди|включи|включить|найди|найти|поищи|поискать|покажи|показать|напиши|напечатай|введи|вбей|продиктуй|поиск|в\s+поиске|и\s+найди|и\s+поищи|и|в|на|\s+)+', '', q, flags=re.IGNORECASE).strip()
        if q and len(q) > 1:
            return {"type": "search_web", "query": q, "engine": "youtube"}
        return {"type": "open_url", "url": "https://www.youtube.com"}

    if any(k in c for k in ["яндекс", "yandex"]):
        q = re.sub(r'\b(яндексе|яндекс|yandex)\b', '', c, flags=re.IGNORECASE)
        q = re.sub(r'^(?:открой|открыть|перейди|зайди|включи|включить|найди|найти|поищи|поискать|загугли|загуглить|напиши|напечатай|введи|вбей|продиктуй|поиск|в\s+поиске|и\s+найди|и|в|на|\s+)+', '', q, flags=re.IGNORECASE).strip()
        if q and len(q) > 1:
            return {"type": "search_web", "query": q, "engine": "yandex"}
        return {"type": "open_url", "url": "https://yandex.ru"}

    if any(k in c for k in ["вб", "вайлдберриз", "вайлдбериз", "wildberries"]):
        q = re.sub(r'\b(вб|вайлдберриз|вайлдбериз|wildberries)\b', '', c, flags=re.IGNORECASE)
        q = re.sub(r'^(?:открой|открыть|найди|найти|поищи|поискать|купи|купить|посмотри|покажи|напиши|напечатай|введи|вбей|продиктуй|поиск|в\s+поиске|и\s+найди|и|в|на|\s+)+', '', q, flags=re.IGNORECASE).strip()
        if q and len(q) > 1:
            return {"type": "search_web", "query": q, "engine": "wildberries"}
        return {"type": "open_url", "url": "https://wildberries.ru"}

    if any(k in c for k in ["озон", "ozon"]):
        q = re.sub(r'\b(озоне|озон|ozon)\b', '', c, flags=re.IGNORECASE)
        q = re.sub(r'^(?:открой|открыть|найди|найти|поищи|поискать|купи|купить|покажи|напиши|напечатай|введи|вбей|продиктуй|поиск|в\s+поиске|и\s+найди|и|в|на|\s+)+', '', q, flags=re.IGNORECASE).strip()
        if q and len(q) > 1:
            return {"type": "search_web", "query": q, "engine": "ozon"}
        return {"type": "open_url", "url": "https://ozon.ru"}

    if any(k in c for k in ["авито", "avito"]):
        q = re.sub(r'\b(авито|avito)\b', '', c, flags=re.IGNORECASE)
        q = re.sub(r'^(?:открой|открыть|найди|найти|поищи|поискать|покажи|напиши|напечатай|введи|вбей|продиктуй|поиск|в\s+поиске|и\s+найди|и|в|на|\s+)+', '', q, flags=re.IGNORECASE).strip()
        if q and len(q) > 1:
            return {"type": "search_web", "query": q, "engine": "avito"}
        return {"type": "open_url", "url": "https://avito.ru"}

    if any(k in c for k in ["сафари", "safari"]):
        q = re.sub(r'\b(сафари|safari)\b', '', c, flags=re.IGNORECASE)
        q = re.sub(r'^(?:открой|открыть|найди|найти|поищи|поискать|загугли|напиши|напечатай|введи|вбей|поиск|в\s+поиске|и\s+найди|и|в|на|\s+)+', '', q, flags=re.IGNORECASE).strip()
        if q and len(q) > 1:
            return {"type": "autonomous_browser_task", "browser": "safari", "query": q}
        return {"type": "launch_app", "app": "safari"}

    if any(k in c for k in ["в заметках", "в заметки"]):
        t = re.sub(r'^(?:в\s+заметках|в\s+заметки)\s+(?:напиши|создай|запиши|добавь|сохрани)\s+(?:заметку\s+)?(?:с\s+текстом\s+|текст\s+)?', '', raw_c, flags=re.IGNORECASE).strip()
        if t:
            return {"type": "autonomous_notes_task", "text": t}
        return {"type": "launch_app", "app": "notes"}

    # 13. Google / Web Searches
    if any(k in c for k in ["гугл", "google", "загугли", "загуглить", "погугли", "поищи в интернете", "найди в интернете"]):
        q = re.sub(r'\b(гугле|гугл|google|интернете|сети)\b', '', c, flags=re.IGNORECASE)
        q = re.sub(r'^(?:открой|открыть|найди|найти|поищи|поискать|загугли|загуглить|погугли|погуглить|напиши|напечатай|введи|вбей|продиктуй|поиск|в\s+поиске|и\s+найди|и|в|на|\s+)+', '', q, flags=re.IGNORECASE).strip()
        if q and len(q) > 1:
            return {"type": "search_web", "query": q, "engine": "google"}
        return {"type": "open_url", "url": "https://www.google.com"}

    # Generic search bar query e.g. "введи в поиск купить кроссовки" / "напиши в поиске рецепты"
    if any(c.startswith(k) for k in ["введи в поиск ", "вбей в поиск ", "напиши в поиск ", "напиши в поиске ", "поиск: ", "поиск "]):
        q = re.sub(r'^(?:введи\s+в\s+поиск[е]?|вбей\s+в\s+поиск[е]?|напиши\s+в\s+поиск[е]?|поиск[:\s]+)', '', raw_c, flags=re.IGNORECASE).strip()
        q = re.sub(r'^["«\']|["»\']$', '', q).strip()
        if q:
            return {"type": "search_web", "query": q, "engine": "google"}

    # 13.1 Universal Messenger & Chat Automation (Telegram, Discord, WhatsApp, VK, Skype, Slack)
    MESSENGER_KEYWORDS = ['телеграмме', 'телеграме', 'телеграм', 'телеграмчик', 'телеге', 'тг', 'telegram', 'дискорде', 'дискорд', 'discord', 'ватсапе', 'ватсап', 'whatsapp', 'вк', 'vk', 'скайпе', 'скайп', 'skype', 'слаке', 'слак', 'slack']
    M_KW_PATTERN = r'(?:в\s+|на\s+)?(' + '|'.join(MESSENGER_KEYWORDS) + r')'

    COMMON_NAME_DATIVE_MAP = {
        "кириллу": "Кирилл", "кирилла": "Кирилл", "кирилл": "Кирилл",
        "никите": "Никита", "никиту": "Никита", "никита": "Никита",
        "саше": "Саша", "сашу": "Саша", "саша": "Саша",
        "маше": "Маша", "машу": "Маша", "маша": "Маша",
        "даше": "Даша", "дашу": "Даша", "даша": "Даша",
        "артему": "Артем", "артёму": "Артем", "артем": "Артем", "артём": "Артем",
        "диме": "Дима", "диму": "Дима", "дима": "Дима",
        "максиму": "Максим", "максима": "Максим", "максим": "Максим",
        "ивану": "Иван", "ивана": "Иван", "иван": "Иван",
        "владу": "Влад", "влада": "Влад", "влад": "Влад",
        "сергею": "Сергей", "сергея": "Сергей", "сергей": "Сергей",
        "андрею": "Андрей", "андрея": "Андрей", "андрей": "Андрей",
        "алексею": "Алексей", "алексея": "Алексей", "алексей": "Алексей",
        "олегу": "Олег", "олега": "Олег", "олег": "Олег",
        "денису": "Денис", "дениса": "Денис", "денис": "Денис",
        "мише": "Миша", "мишу": "Миша", "миша": "Миша",
        "роме": "Рома", "рому": "Рома", "рома": "Рома",
        "паше": "Паша", "пашу": "Паша", "паша": "Паша",
        "илье": "Илья", "илью": "Илья", "илья": "Илья",
        "антону": "Антон", "антона": "Антон", "антон": "Антон",
        "егору": "Егор", "егора": "Егор", "егор": "Егор",
        "маме": "Мама", "маму": "Мама", "мама": "Мама",
        "папе": "Папа", "папу": "Папа", "папа": "Папа",
        "брату": "Брат", "брата": "Брат", "брат": "Брат",
        "сестре": "Сестра", "сестру": "Сестра", "сестра": "Сестра",
        "бабушке": "Бабушка", "бабушку": "Бабушка", "бабушка": "Бабушка",
        "дедушке": "Дедушка", "дедушку": "Дедушка", "дедушка": "Дедушка",
        "насте": "Настя", "настю": "Настя", "настя": "Настя",
        "кате": "Катя", "катю": "Катя", "катя": "Катя",
        "оле": "Оля", "олю": "Оля", "оля": "Оля",
        "ане": "Аня", "аню": "Аня", "аня": "Аня",
        "юле": "Юля", "юлю": "Юля", "юля": "Юля",
        "лене": "Лена", "лену": "Лена", "лена": "Лена",
        "полине": "Полина", "полину": "Полина", "полина": "Полина",
        "соне": "Соня", "соню": "Соня", "соня": "Соня",
        "жене": "Женя", "женю": "Женя", "женя": "Женя",
        "косте": "Костя", "костю": "Костя", "костя": "Костя",
        "тимуру": "Тимур", "тимура": "Тимур", "тимур": "Тимур",
        "марку": "Марк", "марка": "Марк", "марк": "Марк",
        "глебу": "Глеб", "глеба": "Глеб", "глеб": "Глеб",
        "богдану": "Богдан", "богдана": "Богдан", "богдан": "Богдан",
        "ярославу": "Ярослав", "ярослава": "Ярослав", "ярослав": "Ярослав",
    }

    def normalize_contact_name(raw_name: str) -> str:
        s = raw_name.strip().strip('"\'«»')
        if not s:
            return ""
        low = s.lower()
        if low in COMMON_NAME_DATIVE_MAP:
            return COMMON_NAME_DATIVE_MAP[low]
        if re.search(r'[а-яё]', low):
            if len(low) > 4 and low.endswith('у') and not low.endswith('ау'):
                return low[:-1].capitalize()
            if len(low) > 4 and low.endswith('ю'):
                return (low[:-1] + 'й').capitalize()
            if len(low) > 4 and low.endswith('е'):
                return (low[:-1] + 'а').capitalize()
            return s.capitalize()
        return s

    def normalize_messenger(name: str) -> str:
        nl = name.lower()
        if any(k in nl for k in ['дискорд', 'discord']):
            return 'discord'
        elif any(k in nl for k in ['ватсап', 'whatsapp']):
            return 'whatsapp'
        elif any(k in nl for k in ['вк', 'vk']):
            return 'vk'
        elif any(k in nl for k in ['скайп', 'skype']):
            return 'skype'
        elif any(k in nl for k in ['слак', 'slack']):
            return 'slack'
        return 'telegram'

    def extract_case_match(original_str: str, lower_match: str) -> str:
        if not lower_match or not original_str:
            return lower_match
        m = re.search(re.escape(lower_match), original_str, re.IGNORECASE)
        return m.group(0) if m else lower_match

    # Pattern 1A (contact with prefix before verb): 'открой <messenger> и контакту/пользователю/в чат <contact> напиши/отправь <message>'
    m1_before = re.match(
        rf'^(?:зайди|открой|перейди)\s+{M_KW_PATTERN}\s+(?:и\s+)?(?:в\s+чат\s+|в\s+диалог\s+|пользователю\s+|контакту\s+|для\s+|в\s+)([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)\s+(?:и\s+)?(?:напиши|напечатай|отправь|скинь)\s+(?:слово\s+|текст\s+|сообщение\s+)?(.*)',
        c, re.IGNORECASE
    )
    if m1_before:
        m_app = normalize_messenger(m1_before.group(1))
        raw_contact = extract_case_match(orig_c, m1_before.group(2).strip())
        m_target = normalize_contact_name(raw_contact)
        m_msg = re.sub(r'^["«\']|["»\']$', '', m1_before.group(3).strip()).strip()
        m_msg = extract_case_match(orig_c, m_msg)
        return {"type": "messenger_send", "messenger": m_app, "contact": m_target, "message": m_msg}

    # Pattern 1B (verb before contact): 'зайди/открой/перейди [в] <messenger> и напиши/отправь [в <contact>] [слово/текст] <message>'
    m1_after = re.match(
        rf'^(?:зайди|открой|перейди)\s+{M_KW_PATTERN}\s+(?:и\s+)?(?:напиши|напечатай|отправь|скинь)\s+(?:в\s+чат\s+|в\s+диалог\s+|пользователю\s+|контакту\s+|для\s+|в\s+)?([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)\s+(?:слово\s+|текст\s+|сообщение\s+)?(.*)',
        c, re.IGNORECASE
    )
    if m1_after:
        m_app = normalize_messenger(m1_after.group(1))
        raw_contact = extract_case_match(orig_c, m1_after.group(2).strip())
        m_target = normalize_contact_name(raw_contact)
        m_msg = re.sub(r'^["«\']|["»\']$', '', m1_after.group(3).strip()).strip()
        m_msg = extract_case_match(orig_c, m_msg)
        return {"type": "messenger_send", "messenger": m_app, "contact": m_target, "message": m_msg}

    # Pattern 1C: 'в/на <messenger> [и] напиши/отправь [в/пользователю/контакту <contact>] [слово/текст] <message>'
    m1_c = re.match(
        rf'^(?:в\s+|на\s+){M_KW_PATTERN}\s+(?:и\s+)?(?:напиши|напечатай|отправь|скинь|черкани)\s+(?:в\s+чат\s+|в\s+диалог\s+|пользователю\s+|контакту\s+|для\s+|в\s+)?([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)\s+(?:слово\s+|текст\s+|сообщение\s+)?(.*)',
        c, re.IGNORECASE
    )
    if m1_c:
        m_app = normalize_messenger(m1_c.group(1))
        raw_contact = extract_case_match(orig_c, m1_c.group(2).strip())
        m_target = normalize_contact_name(raw_contact)
        m_msg = re.sub(r'^["«\']|["»\']$', '', m1_c.group(3).strip()).strip()
        m_msg = extract_case_match(orig_c, m_msg)
        return {"type": "messenger_send", "messenger": m_app, "contact": m_target, "message": m_msg}

    # Pattern 1D: 'в/на <messenger> [пользователю/контакту <contact>] напиши/отправь [слово/текст] <message>'
    m1_d = re.match(
        rf'^(?:в\s+|на\s+){M_KW_PATTERN}\s+(?:в\s+чат\s+|в\s+диалог\s+|пользователю\s+|контакту\s+|для\s+|в\s+)?([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)\s+(?:напиши|напечатай|отправь|скинь|черкани)\s+(?:слово\s+|текст\s+|сообщение\s+)?(.*)',
        c, re.IGNORECASE
    )
    if m1_d:
        m_app = normalize_messenger(m1_d.group(1))
        raw_contact = extract_case_match(orig_c, m1_d.group(2).strip())
        m_target = normalize_contact_name(raw_contact)
        m_msg = re.sub(r'^["«\']|["»\']$', '', m1_d.group(3).strip()).strip()
        m_msg = extract_case_match(orig_c, m_msg)
        return {"type": "messenger_send", "messenger": m_app, "contact": m_target, "message": m_msg}

    # Pattern 2: 'напиши/отправь [в <messenger>] [в <contact>] [слово/текст] <message>'
    m2 = re.match(
        rf'^(?:напиши|напечатай|отправь|скинь)\s+(?:сообщение\s+)?(?:в\s+|на\s+)?{M_KW_PATTERN}\s+(?:в\s+|пользователю\s+|контакту\s+|для\s+|в\s+чат\s+)?([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)\s+(?:слово\s+|текст\s+|сообщение\s+)?(.*)',
        c, re.IGNORECASE
    )
    if m2:
        m_app = normalize_messenger(m2.group(1))
        raw_contact = extract_case_match(orig_c, m2.group(2).strip())
        m_target = normalize_contact_name(raw_contact)
        m_msg = re.sub(r'^["«\']|["»\']$', '', m2.group(3).strip()).strip()
        m_msg = extract_case_match(orig_c, m_msg)
        return {"type": "messenger_send", "messenger": m_app, "contact": m_target, "message": m_msg}

    # Pattern 3: 'найди/открой чат/контакт <contact> [и напиши/отправь <message>]'
    m3 = re.match(
        r'^(?:найди|открой|выбери)\s+(?:чат|диалог|беседу|группу|канал|контакт|переписку)\s+(?:с\s+|для\s+)?([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)(?:\s+(?:и\s+)?(?:напиши|напечатай|отправь|скинь)\s+(?:сообщение\s+|текст\s+|слово\s+)?(.*))?$',
        c, re.IGNORECASE
    )
    if m3:
        raw_target = extract_case_match(orig_c, m3.group(1).strip())
        target_name = normalize_contact_name(raw_target)
        raw_msg = m3.group(2)
        msg_text = ""
        if raw_msg:
            msg_text = re.sub(r'^["«\']|["»\']$', '', raw_msg.strip()).strip()
            msg_text = extract_case_match(orig_c, msg_text)
        dest_m = "auto"
        for kw in MESSENGER_KEYWORDS:
            if kw in c:
                dest_m = normalize_messenger(kw)
                break
        return {"type": "messenger_send", "messenger": dest_m, "contact": target_name, "message": msg_text}

    # Pattern 4A: Explicit contact prefix: "напиши/отправь [сообщение] пользователю/контакту/для/в чат/в диалог <contact> <message>"
    m4_prefix = re.match(
        r'^(?:напиши|напечатай|отправь|скинь)\s+(?:сообщение\s+|текст\s+|слово\s+)?(?:пользователю|контакту|для|в\s+чат|в\s+диалог)\s+([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)\s+(?:сообщение\s+|текст\s+|слово\s+)?(.*)$',
        c, re.IGNORECASE
    )
    if m4_prefix:
        orig_contact = extract_case_match(orig_c, m4_prefix.group(1).strip())
        norm_contact = normalize_contact_name(orig_contact)
        clean_msg = re.sub(r'^["«\']|["»\']$', '', m4_prefix.group(2).strip()).strip()
        clean_msg = extract_case_match(orig_c, clean_msg)
        return {"type": "messenger_send", "messenger": "auto", "contact": norm_contact, "message": clean_msg}

    # Pattern 4B: Direct Russian name in dative case or Latin username:
    # e.g. "напиши Кириллу привет как дела", "отправь Никите файл готов", "напиши JessePinkman привет"
    m4_direct = re.match(
        r'^(?:напиши|напечатай|отправь|скинь)\s+([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)\s+(?:сообщение\s+|текст\s+|слово\s+)?(.*)$',
        c, re.IGNORECASE
    )
    if m4_direct:
        cand_target = m4_direct.group(1).strip()
        cand_target_low = cand_target.lower()
        cand_msg = m4_direct.group(2).strip()
        is_known_contact = cand_target_low in COMMON_NAME_DATIVE_MAP
        is_latin_username = bool(re.match(r'^[A-Z][a-zA-Z0-9_\-\.]{2,}$', cand_target) and cand_target_low not in APP_MAP)
        if (is_known_contact or is_latin_username) and cand_msg:
            orig_contact = extract_case_match(orig_c, cand_target)
            norm_contact = normalize_contact_name(orig_contact)
            clean_msg = re.sub(r'^["«\']|["»\']$', '', cand_msg).strip()
            clean_msg = extract_case_match(orig_c, clean_msg)
            return {"type": "messenger_send", "messenger": "auto", "contact": norm_contact, "message": clean_msg}

    # Clarify incomplete messenger write commands (e.g. "Зайди в Telegram и напиши")
    if any(app in c for app in ["телеграм", "telegram", "тг", "телеге", "дискорд", "discord", "ватсап", "whatsapp"]) and any(v in c for v in ["напиши", "напечатай", "отправь", "скинь", "черкани", "сообщение"]):
        target_app = "Telegram" if any(k in c for k in ["телеграм", "telegram", "тг", "телеге"]) else "Discord" if any(k in c for k in ["дискорд", "discord"]) else "WhatsApp"
        return {
            "type": "clarify",
            "message": f"Кому и какое сообщение вы хотите отправить в {target_app}?\nНапример: «В {target_app} напиши Siax текст Привет» или «{target_app} напиши Кириллу Привет»."
        }

    # 14. In-App Automation: Typing Text & Messages (Voice Sunder dictation)
    if any(c.startswith(verb) for verb in ["напиши ", "напечатай ", "введи ", "вбей ", "продиктуй ", "вставь ", "type ", "write "]):
        raw_text = re.sub(r'^(?:напиши|напечатай|введи|вбей|продиктуй|вставь|type|write)\s+(?:текст[:\s]+)?', '', orig_c, flags=re.IGNORECASE).strip()
        press_enter = False
        m_enter = re.search(r'\s+(?:и\s+)?(?:нажми\s+(?:enter|ввод|ентер)|нажми\s+кнопку\s+enter|отправь)$', raw_text, re.IGNORECASE)
        if m_enter:
            raw_text = raw_text[:m_enter.start()].strip()
            press_enter = True

        target_app = None
        field = None

        # Check for destination app / browser / search field
        m_dest = re.match(r'^(?:в\s+|на\s+)?(блокнот\w*|notepad|ворд\w*|word|документ\w*|телеграм\w*|тг|telegram|дискорд\w*|discord|хром\w*|chrome|браузер\w*|яндекс\w*|browser|поиск\w*|строк\w*\s+поиск\w*|адресн\w*\s+строк\w*|сайте?|страниц\w*)\s+(?:текст[:\s]+|сообщение[:\s]+|слово[:\s]+)?(.*)', raw_text, re.IGNORECASE)
        if m_dest:
            dest_tag = m_dest.group(1).lower()
            remaining_text = m_dest.group(2).strip()
            if any(k in dest_tag for k in ["блокнот", "notepad"]):
                target_app = "notepad"
            elif any(k in dest_tag for k in ["ворд", "word", "документ"]):
                target_app = "word"
            elif any(k in dest_tag for k in ["телеграм", "тг", "telegram"]):
                target_app = "telegram"
            elif any(k in dest_tag for k in ["дискорд", "discord"]):
                target_app = "discord"
            elif any(k in dest_tag for k in ["адресн", "строк"]):
                target_app = "chrome"
                field = "search"
                press_enter = True
            elif any(k in dest_tag for k in ["поиск", "сайт", "страниц"]):
                target_app = "chrome"
                field = "search"
            elif any(k in dest_tag for k in ["хром", "chrome", "браузер", "яндекс", "browser"]):
                target_app = "chrome"
            if remaining_text:
                raw_text = remaining_text

        # Strip prefixes like "слово", "текст", "сообщение"
        raw_text = re.sub(r'^(?:слово\s+|текст\s+|сообщение\s+|фразу\s+)', '', raw_text, flags=re.IGNORECASE).strip()
        # Strip outer quotes if present
        raw_text = re.sub(r'^["«\']|["»\']$', '', raw_text).strip()

        if raw_text:
            return {"type": "type_text", "text": raw_text, "target_app": target_app, "field": field, "press_enter": press_enter}

    # In-App Automation: Standalone Key Presses & Hotkeys
    if c in ["enter", "ввод", "ентер"]:
        return {"type": "press_key", "key": "enter"}
    if c in ["esc", "escape", "эскейп"]:
        return {"type": "press_key", "key": "esc"}
    if c in ["tab", "таб"]:
        return {"type": "press_key", "key": "tab"}

    if any(k in c for k in ["скопируй", "копируй", "copy"]):
        return {"type": "hotkey", "keys": ["ctrl", "c"]}
    if any(k in c for k in ["вставь", "paste"]):
        return {"type": "hotkey", "keys": ["ctrl", "v"]}
    if any(k in c for k in ["выдели все", "выдели всё", "select all"]):
        return {"type": "hotkey", "keys": ["ctrl", "a"]}
    if any(k in c for k in ["сохрани файл", "save file"]):
        return {"type": "hotkey", "keys": ["ctrl", "s"]}

    # 15. Plugin Commands
    if "плагин" in c or "plugin" in c:
        if any(k in c for k in ["запусти", "включи", "start", "run"]):
            p_name = re.sub(r'.*?(?:запусти|включи|start|run)\s+(?:плагин\s+)?', '', c).strip()
            if p_name:
                return {"type": "plugin_start", "plugin_name": p_name}
        elif any(k in c for k in ["останови", "выключи", "стоп", "stop"]):
            p_name = re.sub(r'.*?(?:останови|выключи|стоп|stop)\s+(?:плагин\s+)?', '', c).strip()
            if p_name:
                return {"type": "plugin_stop", "plugin_name": p_name}
        elif any(k in c for k in ["список", "какие", "покажи", "list", "status"]):
            return {"type": "plugin_list"}

    # 16. Universal Application Launch (Dynamic PC catalog & Start Menu discovery)
    # Check for bare verb without app name: e.g. "открой", "запусти"
    if c.strip() in ["открой", "открыть", "запусти", "запустить", "включи", "включить", "open", "launch", "start", "run"]:
        return {"type": "clarify", "message": "Какое приложение или сайт вы хотите открыть?"}

    has_open_verb = any(c.startswith(k) or f" {k} " in f" {c} " for k in [
        "открой", "открыть", "запусти", "запустить", "включи", "включить", "стартуй",
        "зайди в", "зайди на", "зайди", "перейди в", "перейди на", "перейди",
        "open", "launch", "start", "run"
    ])

    if has_open_verb:
        target_app = re.sub(r'^(?:открой|открыть|запусти|запустить|включи|включить|стартуй|зайди\s+в|зайди\s+на|зайди|перейди\s+в|перейди\s+на|перейди|open|launch|start|run)\s+(?:приложение\s+|программу\s+|софт\s+)?', '', c).strip()
        if not target_app or target_app in ["открой", "открыть", "запусти", "запустить", "open", "launch"]:
            return {"type": "clarify", "message": "Какое приложение или сайт вы хотите открыть?"}

        # Check for generic browser request
        if target_app in ["браузер", "browser", "интернет"]:
            if any(k in raw_c for k in ["какие браузеры", "какой браузер", "список браузеров", "выбери браузер", "выбрать браузер"]):
                browsers = sc.detect_installed_browsers()
                if len(browsers) > 1:
                    return {"type": "browser_choice", "browsers": browsers}
            return {"type": "launch_app", "app": "chrome"}

        for alias, canonical in APP_MAP.items():
            if alias == target_app or alias in target_app.split():
                return {"type": "launch_app", "app": canonical}
        return {"type": "launch_app", "app": target_app}

    # Short app names (e.g. "калькулятор", "chrome", "postman")
    if len(c.split()) <= 2:
        for alias, canonical in APP_MAP.items():
            if alias == c or alias in c:
                return {"type": "launch_app", "app": canonical}
        # Check if single word matches scanned apps
        catalog = sc.scan_all_installed_apps()
        if c in catalog:
            return {"type": "launch_app", "app": c}

    # 17. Math Calculation
    m_calc = safe_math_eval(c)
    if m_calc is not None:
        return {"type": "math", "expr": c, "res": m_calc}

    return None

def local_multi_action_planner(user_text: str) -> List[Dict[str, Any]]:
    """
    Intelligently splits complex compound user commands (chaining 2, 3, 4 actions)
    and maps them to sequential atomic executable operations with auto-delays.
    """
    # 0. If user_text directly maps to a unified action (e.g. messenger_send), execute directly without splitting
    single_act = parse_single_clause(user_text)
    if single_act and single_act.get("type") in ["messenger_send", "search_web", "clarify", "browser_choice", "terminal_command", "play_music"]:
        return [single_act]

    # 1. Normalize verb boundaries to avoid missing clauses without punctuation
    # e.g. "Открой браузер сделай скриншот" -> "Открой браузер; сделай скриншот"
    verb_boundary = r'(?<=\w)\s+(?=(?:открой|запусти|зайди в|зайди на|зайди|перейди в|перейди на|перейди|найди чат|найди диалог|найди контакт|сделай скриншот|сделай скрин|заскринь|сохрани|закрой вкладку|закрой|выключи|напиши|напечатай|отправь|нажми|кликни|почисти корзину|очисти корзину|заблокируй|обнови|прокрути|поставь яркость|поставь звук|поставь громкость|поставь|установи|прибавь|убавь|создай файл|создай папку|создай|удали файл|удали папку|удали|проверь|проанализируй|список файлов)\b)'
    user_text_norm = re.sub(verb_boundary, '; ', user_text, flags=re.IGNORECASE)

    clauses = re.split(r'\b(и\s+потом|а\s+затем|после\s+этого|потом|затем|а\s+также|также|дальше|and\s+then|then)\b|[;,]', user_text_norm, flags=re.IGNORECASE)
    actions = []
    
    for clause in clauses:
        if not clause:
            continue
        clean_cl = re.sub(r'^\s*\b(и|а|дальше|затем|потом)\b\s*', '', clause, flags=re.IGNORECASE)
        clean_cl = re.sub(r'\s*\b(и|а|потом|затем)\b\s*$', '', clean_cl, flags=re.IGNORECASE).strip()
        if not clean_cl or clean_cl.lower() in ["и", "потом", "затем", "and", "then", "также", "еще", "дальше", "и потом", "а затем"]:
            continue
        act = parse_single_clause(clean_cl)
        if act:
            if act.get("type") == "press_key" and act.get("key") == "enter" and actions and actions[-1].get("type") == "type_text":
                actions[-1]["press_enter"] = True
                continue
            if act.get("type") == "save_destination":
                for prev in reversed(actions):
                    if prev.get("type") == "screenshot":
                        prev["folder"] = act.get("folder", "desktop")
                        break
                continue

            # If an application launch precedes type_text, propagate target_app
            if act.get("type") == "type_text" and not act.get("target_app"):
                for prev in reversed(actions):
                    if prev.get("type") == "launch_app" and prev.get("app"):
                        act["target_app"] = prev["app"]
                        break

            # If an application launch or URL open precedes a web interaction or screenshot, insert automatic wait
            if actions and actions[-1].get("type") in ["launch_app", "open_url", "search_web"]:
                if act.get("type") in ["screenshot", "click_website_button", "type_text", "press_key", "hotkey", "scroll_page", "switch_browser_tab", "close_browser_tab"]:
                    actions.append({"type": "wait", "seconds": 2.5})

            # If a close_app follows a screenshot or actions, ensure previous action has settled
            if act.get("type") == "close_app" and actions and actions[-1].get("type") in ["screenshot", "click_website_button", "type_text"]:
                actions.append({"type": "wait", "seconds": 1.0})

            actions.append(act)

    return actions

def neural_action_planner(user_text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Uses neural reasoning to decompose intricate, multi-step instructions into concrete JSON actions.
    Uses single user message to bypass paywalls.
    """
    instruction = (
        "You are an expert Windows & macOS Desktop Automation Planner. "
        "Decompose user instruction into an array of concrete JSON action objects. "
        "Output ONLY a raw JSON array, with no markdown, no explanation, no backticks.\n"
        "Available action types:\n"
        "- {\"type\": \"play_music\", \"service\": \"spotify\" | \"yandex\" | \"soundcloud\" | \"vk\" | \"youtube\" | \"auto\", \"query\": \"...\", \"playlist\": \"...\", \"action\": \"play\" | \"pause\" | \"next\" | \"prev\"}\n"
        "- {\"type\": \"launch_app\", \"app\": \"chrome\" | \"telegram\" | \"discord\" | \"whatsapp\" | \"notepad\" | \"word\" | \"...\"}\n"
        "- {\"type\": \"messenger_send\", \"messenger\": \"telegram\" | \"discord\" | \"whatsapp\" | \"vk\" | \"auto\", \"contact\": \"...\", \"message\": \"...\"}\n"
        "- {\"type\": \"type_text\", \"text\": \"...\", \"target_app\": \"...\", \"press_enter\": true | false}\n"
        "- {\"type\": \"open_url\", \"url\": \"https://...\"}\n"
        "- {\"type\": \"search_web\", \"query\": \"...\", \"engine\": \"google\" | \"yandex\" | \"youtube\"}\n"
        "- {\"type\": \"screenshot\", \"folder\": \"downloads\" | \"desktop\" | \"documents\" | \"pictures\"}\n"
        "- {\"type\": \"close_app\", \"app\": \"...\"}\n"
        "- {\"type\": \"press_key\", \"key\": \"enter\" | \"tab\" | \"esc\" | \"space\"}\n"
        "- {\"type\": \"hotkey\", \"keys\": [\"ctrl\", \"v\"] | [\"cmd\", \"v\"]}\n"
        "- {\"type\": \"wait\", \"seconds\": 1.5}\n"
        "CRITICAL RULES:\n"
        "1. NEVER generate 'close_app' UNLESS the user explicitly asked to close or exit ('закрой', 'выйди', 'close'). Keep all opened messengers and apps OPEN.\n"
        "2. If user asks to find a chat and write a message (e.g. 'найди чат Кирилл и напиши привет' or 'зайди в телеграм и напиши в Node.js слово привет'), output a single 'messenger_send' or 'launch_app' + 'type_text', NEVER 'close_app'.\n"
        "3. If user asks to play music, a playlist, pause or next track in Spotify, Yandex Music, SoundCloud, use 'play_music'.\n"
        "Examples:\n"
        "- Instruction: включи плейлист рок в спотифай\n"
        "  JSON: [{\"type\":\"play_music\",\"service\":\"spotify\",\"playlist\":\"рок\",\"action\":\"play\"}]\n"
        "- Instruction: выключи то что играет\n"
        "  JSON: [{\"type\":\"play_music\",\"action\":\"pause\"}]\n"
        "- Instruction: найди чат кирилл и напиши сообщение привет\n"
        "  JSON: [{\"type\":\"messenger_send\",\"messenger\":\"auto\",\"contact\":\"Кирилл\",\"message\":\"привет\"}]\n"
        "- Instruction: зайди в телеграм и напиши в Node.js слово привет\n"
        "  JSON: [{\"type\":\"messenger_send\",\"messenger\":\"telegram\",\"contact\":\"Node.js\",\"message\":\"привет\"}]\n"
        "- Instruction: открой блокнот и напиши Привет мир\n"
        "  JSON: [{\"type\":\"launch_app\",\"app\":\"notepad\"},{\"type\":\"wait\",\"seconds\":1.2},{\"type\":\"type_text\",\"text\":\"Привет мир\",\"target_app\":\"notepad\"}]"
    )
    # Fast cache lookup (<1ms)
    cache_key = user_text.lower().strip()
    if cache_key in _AI_PLAN_CACHE:
        return _AI_PLAN_CACHE[cache_key]

    combined = f"[{instruction}]\n\nInstruction: {user_text}"
    payload = {
        "messages": [
            {"role": "user", "content": combined}
        ]
    }
    try:
        req = urllib.request.Request(
            "https://text.pollinations.ai/",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            raw = resp.read().decode("utf-8").strip()
            clean_json = re.sub(r'^```(?:json)?\s*', '', raw)
            clean_json = re.sub(r'\s*```$', '', clean_json).strip()
            m_arr = re.search(r'\[\s*\{.*\}\s*\]', clean_json, re.DOTALL)
            if m_arr:
                clean_json = m_arr.group(0)
            parsed = json.loads(clean_json)
            if isinstance(parsed, list) and len(parsed) > 0:
                # Prevent hallucinated close_app if user didn't ask to close
                wants_close = any(k in user_text.lower() for k in ["закрой", "выйди", "выруби", "close", "kill", "exit", "quit"])
                if not wants_close:
                    parsed = [a for a in parsed if a.get("type") != "close_app"]
                if len(_AI_PLAN_CACHE) > 200:
                    _AI_PLAN_CACHE.clear()
                _AI_PLAN_CACHE[cache_key] = parsed
                return parsed
    except Exception:
        pass
    return None

# ─── FREE NEURAL REASONING ENGINE ───────────────────────────────
def query_free_ai(prompt: str, user_name: str = "Пользователь", history: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    """
    Queries free online neural reasoning model with full multi-turn conversation memory.
    Sends user context and history to maintain deep conversational awareness.
    Provides deep, smart, accurate responses strictly without emojis.
    """
    cache_key = prompt.lower().strip()
    if not history and cache_key in _AI_QUERY_CACHE:
        return _AI_QUERY_CACHE[cache_key]

    instruction = (
        f"Ты — Argus AI, персональный автономный ИИ-ассистент Windows для пользователя {user_name}. "
        "Отвечай интеллектуально, точно, полезно, грамотно и строго БЕЗ ЭМОДЗИ на языке пользователя."
    )
    messages = [{"role": "user", "content": f"[{instruction}]"}]
    if history:
        for h in history[-8:]:
            r = "user" if h.get("role") == "user" else "assistant"
            cnt = h.get("content", "").strip()
            if cnt:
                messages.append({"role": r, "content": cnt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "messages": messages
    }
    try:
        req = urllib.request.Request(
            "https://text.pollinations.ai/",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            text = resp.read().decode("utf-8").strip()
            # Clean emojis
            cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', text).strip()
            cleaned = re.sub(r'^\[.*?\]\s*', '', cleaned).strip()
            if cleaned and len(cleaned) > 2:
                if len(_AI_QUERY_CACHE) > 200:
                    _AI_QUERY_CACHE.clear()
                _AI_QUERY_CACHE[cache_key] = cleaned
                return cleaned
    except Exception:
        pass
    return None

# ─── LOCAL PERSONA KNOWLEDGE BASE (OFFLINE FALLBACK) ────────────
CONVERSATIONAL_KNOWLEDGE = {
    "привет": "Приветствую. Все системы Argus активны и готовы к работе. Чем могу помочь?",
    "hello": "Hello. All Argus systems are operational and ready. How can I assist you?",
    "как дела": "Все модули Argus функционируют в штатном режиме с максимальной производительностью. Ожидаю ваших указаний.",
    "how are you": "All systems operating at peak performance. Ready for your instructions.",
    "кто ты": "Я Argus — ваш персональный автономный ИИ-ассистент для глубокого управления Windows, автоматизации задач, взаимодействия с сайтами и работы за компьютером.",
    "who are you": "I am Argus — your personal autonomous AI assistant for Windows control, workflow automation, and productivity.",
    "что ты умеешь": "Я умею полноценно управлять компьютером: открывать любые сайты и нажимать кнопки на страницах, запускать и закрывать любые программы (Chrome, Telegram, Discord, VS Code, GoLand, Postman, Steam и др.), создавать и удалять файлы и папки на компьютере, анализировать содержимое файлов, делать скриншоты в любую папку (Загрузки, Рабочий стол), настраивать громкость и яркость экрана («на полную», «в ноль»), закрывать программы с фильтрами исключений («кроме vs code»), очищать корзину, блокировать ПК, искать в Google, YouTube, Wildberries и Ozon, а также управлять плагинами.",
    "почему небо синее": "Небо кажется синим из-за рэлеевского рассеяния солнечного света в атмосфере: газы атмосферы рассеивают короткие синие и фиолетовые волны значительно сильнее, чем длинные красные.",
    "почему небо голубое": "Небо голубое благодаря рэлеевскому рассеянию: солнечный свет рассеивается молекулами воздуха, при этом коротковолновые синие и голубые лучи рассеиваются сильнее всего.",
}

def query_encyclopedia_knowledge(query: str, en: bool) -> Optional[str]:
    """
    Instantly fetches factual definitions and summaries (0.2s latency)
    for questions like 'что такое...', 'кто такой...', 'what is...', 'who is...'.
    """
    clean_q = query.strip().rstrip('?.!').strip()
    prefixes = [
        "что такое ", "кто такой ", "кто такая ", "кто такие ", "что значит ",
        "что это такое ", "что это ", "расскажи про ", "расскажи о ",
        "what is ", "who is ", "what are ", "tell me about "
    ]
    target_topic = None
    for p in prefixes:
        if clean_q.lower().startswith(p):
            target_topic = clean_q[len(p):].strip()
            break
            
    if not target_topic:
        words = clean_q.split()
        if len(words) <= 3 and query.strip().endswith('?'):
            target_topic = clean_q
            
    if not target_topic or len(target_topic) < 2:
        return None

    lang = "en" if en else "ru"
    try:
        topic_enc = urllib.parse.quote(target_topic.replace(' ', '_'))
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{topic_enc}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ArgusAI/2.4 (https://github.com/argus; contact@argus.ai)"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            extract = data.get("extract")
            title = data.get("title")
            if extract and len(extract) > 20:
                clean_extract = re.sub(r'[\u0300-\u036f]', '', extract).strip()
                clean_title = re.sub(r'[\u0300-\u036f]', '', title).strip()
                return f"{clean_title}: {clean_extract}"
    except Exception:
        pass
    return None

def get_conversational_reply(raw_text: str, en: bool, user_name: str = "Пользователь", history: Optional[List[Dict[str, Any]]] = None) -> str:
    """Provides high-quality, crisp, intelligent answers without default emojis."""
    t = raw_text.lower().strip()
    for k, reply in CONVERSATIONAL_KNOWLEDGE.items():
        if k in t:
            return reply

    # 1. Check instant factual encyclopedia (0.2s response time)
    wiki_resp = query_encyclopedia_knowledge(raw_text, en)
    if wiki_resp:
        return wiki_resp

    # 2. Try free online neural reasoning model (Pollinations) with history
    ai_resp = query_free_ai(raw_text, user_name, history=history)
    if ai_resp:
        return ai_resp

    # 3. Local fallback
    if en:
        return f"Argus AI is ready. I can launch any software, interact with websites, capture screenshots to Downloads or Desktop, manage audio, or execute automation. Regarding: '{raw_text}', I am ready to proceed."
    else:
        return f"Argus AI готов к работе. Я могу запустить любую программу, открыть сайт, нажать нужную кнопку, сделать снимок экрана в папку Загрузки или настроить звук. По вашему запросу «{raw_text}» готов приступить к выполнению."

# ─── MAIN MASTER ENTRY POINT ────────────────────────────────────
def process_command(user_text: str, user_name: str = "Пользователь", history: Optional[List[Dict[str, Any]]] = None) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
    """
    Main processing entrypoint for Argus AI.
    Executes local multi-step intent parsing in <1ms for 100% reliable system control,
    with smart free neural LLM reasoning fallback and multi-turn context memory.
    """
    raw = user_text.strip()
    en = is_english(raw)

    # 0. Contextual Pronoun Resolution (using dialogue history)
    # e.g. "закрой его", "закрой её", "удали его", "проверь его"
    resolved_text = raw
    if history and any(p in raw.lower() for p in ["его", "ее", "её", "это", "туда же"]):
        for prev_msg in reversed(history):
            prev_content = prev_msg.get("content", "")
            # Check if previous launched an app: e.g. "Запущено приложение: GoLand"
            m_app = re.search(r'Запущено приложение:\s*([a-zA-Z0-9_\- ]+)', prev_content)
            if m_app and any(k in raw.lower() for k in ["закрой", "close", "выключи"]):
                app_name = m_app.group(1).strip()
                resolved_text = re.sub(r'\b(его|ее|её|это)\b', app_name, resolved_text, flags=re.IGNORECASE)
                break
            # Check if previous was a screenshot or file path
            m_file = re.search(r'([a-zA-Z]:[\\/][^\s\)\"\']+\.[a-zA-Z0-9]{2,4})', prev_content)
            if m_file:
                target_f = m_file.group(1).strip()
                if any(k in raw.lower() for k in ["удали", "delete", "сотри"]):
                    resolved_text = f"удали файл {target_f}"
                    break
                if any(k in raw.lower() for k in ["проверь", "проанализируй", "посмотри"]):
                    resolved_text = f"проанализируй файл {target_f}"
                    break

    # 0.5 Custom & Built-in Scenarios (0ms execution e.g. "рабочий режим", "игровой режим", "чистый стол")
    matched_sc = sc_mgr.match_scenario_by_trigger(resolved_text)
    if matched_sc:
        res = sc_mgr.execute_scenario(matched_sc)
        return res["summary"], "scenario", {"scenario_id": matched_sc.get("id"), "scenario_name": matched_sc.get("name")}

    # 1. First, check if input contains any system actions (single or compound)
    actions_to_run = local_multi_action_planner(resolved_text)

    # 2. If no actions found locally and multiple action verbs exist, consult neural reasoning planner
    if not actions_to_run:
        action_verb_count = len(re.findall(r'\b(открой|запусти|скриншот|скрин|закрой|сохрани|напиши|отправь|перейди|найди|search|close|open)\b', resolved_text, re.IGNORECASE))
        if action_verb_count >= 2:
            ai_plan = neural_action_planner(resolved_text)
            if ai_plan:
                actions_to_run = ai_plan

    # 3. If no system actions found, check math
    if not actions_to_run:
        m_calc = safe_math_eval(resolved_text)
        if m_calc is not None:
            reply = f"Result: {m_calc}" if en else f"Результат вычисления: {m_calc}"
            return reply, "math", {"result": m_calc}

    # 3. Check time / date queries
    if not actions_to_run:
        if any(k in resolved_text.lower() for k in ["время", "time", "который час", "сколько времени"]):
            t_str = datetime.datetime.now().strftime("%H:%M")
            return f"Current time is {t_str}." if en else f"Текущее время: {t_str}.", "time", {"time": t_str}

        if any(k in resolved_text.lower() for k in ["число", "дата", "date", "какое число", "какой день"]):
            now = datetime.datetime.now()
            d_str = now.strftime("%d.%m.%Y")
            return f"Today is {d_str}." if en else f"Сегодня: {d_str}.", "date", {"date": d_str}

    # 4. If still no action found, handle conversational query via free AI reasoning engine with history
    if not actions_to_run:
        reply = get_conversational_reply(resolved_text, en, user_name, history=history)
        return reply, "general", {}

    # 5. Sequentially execute all planned actions
    executed_results = []
    primary_action_type = "multi_action" if len(actions_to_run) > 1 else actions_to_run[0].get("type", "general")
    primary_data = {}

    for act in actions_to_run:
        msg, a_type, a_data = execute_single_action(act)
        if a_type != "noop" and a_type != "wait":
            primary_data.update(a_data)
            if len(actions_to_run) == 1:
                primary_action_type = a_type
            elif a_type == "screenshot":
                primary_data["screenshot_path"] = a_data.get("path")
            if msg:
                executed_results.append(msg)

    # 6. Formulate clear Russian/English confirmation
    if executed_results:
        final_reply = ". ".join(executed_results)
        if not final_reply.endswith(('.', '!', '?', '»')):
            final_reply += "."
    else:
        final_reply = "Все задачи успешно выполнены." if not en else "All tasks completed successfully."

    return final_reply, primary_action_type, primary_data
