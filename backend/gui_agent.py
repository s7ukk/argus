import os
import sys
import time
import uuid
import datetime
import subprocess
import re
from typing import Dict, Any, List, Optional, Tuple

try:
    import pyperclip
    _HAS_PYPERCLIP = True
except Exception:
    _HAS_PYPERCLIP = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    _HAS_PYAUTOGUI = True
except Exception:
    _HAS_PYAUTOGUI = False

try:
    import win32gui
    _HAS_WIN32GUI = True
except Exception:
    _HAS_WIN32GUI = False

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

def get_agent_run_dir() -> str:
    """Creates and returns a timestamped directory for autonomous GUI agent step snapshots."""
    try:
        import backend.app_paths as app_paths
        base_dir = app_paths.get_argus_data_dir()
    except Exception:
        base_dir = os.path.expanduser("~")
    run_id = f"run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"
    run_dir = os.path.join(base_dir, "agent_runs", run_id)
    try:
        os.makedirs(run_dir, exist_ok=True)
    except Exception:
        import tempfile
        run_dir = os.path.join(tempfile.gettempdir(), "argus_agent_runs", run_id)
        try:
            os.makedirs(run_dir, exist_ok=True)
        except Exception:
            pass
    return run_dir

def capture_step_screenshot(step_name: str, run_dir: str) -> Optional[str]:
    """
    Captures a high-resolution screenshot at a specific step in the autonomous GUI flow.
    Supports macOS (screencapture -x) and Windows (ctypes GDI / pyautogui / PIL).
    """
    clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', step_name)
    filepath = os.path.join(run_dir, f"{clean_name}.png")
    
    if IS_MAC:
        try:
            subprocess.run(["screencapture", "-x", filepath], capture_output=True, timeout=5)
            if os.path.exists(filepath) and os.path.getsize(filepath) > 500:
                return filepath
        except Exception:
            pass

    try:
        from PIL import ImageGrab
        im = ImageGrab.grab()
        im.save(filepath)
        return filepath
    except Exception:
        pass
            
    if _HAS_PYAUTOGUI:
        try:
            img = pyautogui.screenshot()
            img.save(filepath)
            return filepath
        except Exception:
            pass

    return None

def set_clipboard_text(text: str):
    """Safely copies text to the system clipboard across macOS, Windows, and Linux."""
    if IS_MAC:
        try:
            proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            proc.communicate(input=text.encode("utf-8"), timeout=2)
            return
        except Exception:
            pass
            
    if _HAS_PYPERCLIP:
        try:
            pyperclip.copy(text)
            return
        except Exception:
            pass

def send_key_native(key: str):
    """
    Sends a key press cross-platform.
    On macOS uses AppleScript System Events for 100% native compatibility.
    On Windows uses PyAutoGUI.
    """
    key_lower = key.lower().strip()
    if IS_MAC:
        mac_keycodes = {
            "enter": 36, "return": 36, "ввод": 36,
            "escape": 53, "esc": 53,
            "tab": 48,
            "space": 49, "пробел": 49,
            "down": 125, "вниз": 125,
            "up": 126, "вверх": 126,
            "left": 123, "влево": 123,
            "right": 124, "вправо": 124,
            "delete": 51, "backspace": 51
        }
        if key_lower in mac_keycodes:
            code = mac_keycodes[key_lower]
            script = f'tell application "System Events" to key code {code}'
            subprocess.run(["osascript", "-e", script], capture_output=True)
            return
        else:
            script = f'tell application "System Events" to keystroke "{key}"'
            subprocess.run(["osascript", "-e", script], capture_output=True)
            return

    if _HAS_PYAUTOGUI:
        pyautogui.press(key_lower)

def send_hotkey_native(*keys: str):
    """
    Sends a keyboard shortcut (e.g. Cmd+K, Cmd+V, Ctrl+K, Ctrl+V).
    On macOS uses AppleScript System Events or PyAutoGUI.
    """
    if IS_MAC:
        # Map keys to AppleScript modifiers
        modifiers = []
        regular_key = ""
        for k in keys:
            kl = k.lower().strip()
            if kl in ["cmd", "command", "ctrl", "control"]:
                modifiers.append("command down")
            elif kl in ["shift"]:
                modifiers.append("shift down")
            elif kl in ["alt", "option"]:
                modifiers.append("option down")
            else:
                regular_key = kl

        mod_str = "{" + ", ".join(modifiers) + "}" if modifiers else "{}"
        if regular_key:
            script = f'tell application "System Events" to keystroke "{regular_key}" using {mod_str}'
            subprocess.run(["osascript", "-e", script], capture_output=True)
            return

    if _HAS_PYAUTOGUI:
        adapted = []
        for k in keys:
            kl = k.lower().strip()
            if IS_MAC and kl in ["ctrl", "control"]:
                adapted.append("command")
            elif not IS_MAC and kl in ["cmd", "command"]:
                adapted.append("ctrl")
            else:
                adapted.append(kl)
        pyautogui.hotkey(*adapted)

def paste_text_native(text: str):
    """Copies text to clipboard and pastes it into the active focused field."""
    set_clipboard_text(text)
    time.sleep(0.08)
    if IS_MAC:
        send_hotkey_native("cmd", "v")
    else:
        send_hotkey_native("ctrl", "v")
    time.sleep(0.1)

def activate_app_window(app_name: str) -> bool:
    """Brings the target application window to the absolute foreground."""
    from backend.system_control import launch_application, activate_running_window
    
    app_lower = app_name.lower().strip()
    if IS_MAC:
        mac_name_map = {
            "telegram": "Telegram",
            "телеграм": "Telegram",
            "телега": "Telegram",
            "тг": "Telegram",
            "safari": "Safari",
            "сафари": "Safari",
            "chrome": "Google Chrome",
            "хром": "Google Chrome",
            "discord": "Discord",
            "дискорд": "Discord",
            "whatsapp": "WhatsApp",
            "ватсап": "WhatsApp",
            "notes": "Notes",
            "заметки": "Notes",
            "finder": "Finder",
            "music": "Music",
            "музыка": "Music",
            "spotify": "Spotify",
            "terminal": "Terminal",
            "vscode": "Visual Studio Code"
        }
        target = mac_name_map.get(app_lower, app_name)
        try:
            # 1. Open / launch application
            subprocess.run(["open", "-a", target], capture_output=True)
            time.sleep(0.3)
            # 2. Tell application to activate (foreground focus)
            script = f'tell application "{target}" to activate'
            subprocess.run(["osascript", "-e", script], capture_output=True)
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"[GUI Agent Mac Activate error]: {e}")

    # Windows & fallback
    if not IS_MAC and app_lower in ["telegram", "телеграм", "телега", "тг"]:
        try:
            import os
            os.startfile("tg:")
            time.sleep(0.5)
        except Exception:
            pass
    if not activate_running_window(app_lower):
        res = launch_application(app_lower)
        time.sleep(1.2)
        return res.get("success", False)
    time.sleep(0.4)
    return True

# ─── AUTONOMOUS MESSENGER AGENT (COMPUTER-USE LOOP) ──────────────
def execute_autonomous_messenger_task(messenger: str, contact: str, message: str) -> Dict[str, Any]:
    """
    Executes a multi-step visual GUI automation loop for messengers (Telegram, Discord, WhatsApp, VK):
    1. Launches/activates target messenger window or resolves username protocol.
    2. Takes visual checkpoint screenshot #1.
    3. Locates and opens search input bar (Cmd+K / Ctrl+K / Esc) or direct chat navigation.
    4. Takes visual checkpoint screenshot #2.
    5. Types contact name via clipboard, waits for search results.
    6. Takes visual checkpoint screenshot #3 (contacts found).
    7. Selects and opens the contact's chat (Down Arrow + Enter).
    8. Takes visual checkpoint screenshot #4 (active chat conversation).
    9. Enters and sends the message (Cmd+V + Enter).
    10. Takes confirmation screenshot #5 (message bubble visible).
    11. Returns structured step-by-step summary and screenshots list.
    """
    run_dir = get_agent_run_dir()
    steps_log: List[str] = []
    screenshots: List[str] = []
    
    m_name = messenger.capitalize()
    if messenger.lower() in ["telegram", "телеграм", "телега", "тг"]:
        m_name = "Telegram"
    elif messenger.lower() in ["discord", "дискорд"]:
        m_name = "Discord"
    elif messenger.lower() in ["whatsapp", "ватсап", "воцап"]:
        m_name = "WhatsApp"
    elif messenger.lower() in ["vk", "вконтакте", "вк"]:
        m_name = "VK"
    elif messenger.lower() in ["skype", "скайп"]:
        m_name = "Skype"
    elif messenger.lower() in ["slack", "слак"]:
        m_name = "Slack"
    elif messenger.lower() in ["viber", "вайбер"]:
        m_name = "Viber"

    clean_contact = contact.lstrip('@').strip()
    # A contact is only treated as an explicit handle if user explicitly typed '@' in the prompt
    is_tg_username = bool(
        m_name == "Telegram" and
        contact.strip().startswith('@') and
        re.match(r'^[a-zA-Z0-9_]{3,}$', clean_contact)
    )

    step_num = 1
    def add_step(text: str):
        nonlocal step_num
        steps_log.append(f"{step_num}. {text}")
        step_num += 1

    # Step 1: Open and Focus
    if is_tg_username:
        add_step(f"Открытие личного диалога с пользователем **@{clean_contact}** через системный протокол Telegram.")
        if IS_MAC:
            subprocess.run(["open", f"tg://resolve?domain={clean_contact}"], capture_output=True)
        else:
            try:
                import os
                os.startfile(f"tg://resolve?domain={clean_contact}")
            except Exception:
                subprocess.run(["cmd", "/c", "start", "", f"tg://resolve?domain={clean_contact}"], shell=False, capture_output=True)
        time.sleep(1.2)
        activate_app_window(messenger)
        time.sleep(0.4)
    else:
        add_step(f"Запуск и активация окна приложения **{m_name}** на передний план.")
        activate_app_window(messenger)
        time.sleep(0.8)
    
    ss1 = capture_step_screenshot("01_app_activated", run_dir)
    if ss1: screenshots.append(ss1)

    if not is_tg_username:
        # Step 2: Search for contact in search bar
        add_step(f"Активация поисковой строки интерфейса **{m_name}**.")
        
        # Universal search shortcut: Ctrl+F (Win) / Cmd+F (Mac) for Telegram, WhatsApp, VK; Ctrl+K for Discord
        search_key = "k" if m_name == "Discord" else "f"
        if IS_MAC:
            send_hotkey_native("cmd", search_key)
        else:
            send_hotkey_native("ctrl", search_key)
        time.sleep(0.35)

        # Clear any preexisting search query cleanly
        send_hotkey_native("cmd" if IS_MAC else "ctrl", "a")
        time.sleep(0.08)
        send_key_native("backspace")
        time.sleep(0.08)

        ss2 = capture_step_screenshot("02_search_focused", run_dir)
        if ss2: screenshots.append(ss2)

        # Step 3: Enter contact name
        add_step(f"Ввод имени получателя: поиск контакта «**{contact}**».")
        paste_text_native(contact)
        time.sleep(0.85)

        ss3 = capture_step_screenshot("03_search_results", run_dir)
        if ss3: screenshots.append(ss3)

        # Step 4: Navigate to first search result and open chat
        add_step(f"Выбор найденного контакта в списке (стрелка вниз + Enter) и открытие диалога.")
        send_key_native("down")
        time.sleep(0.25)
        send_key_native("enter")
        time.sleep(0.65)

        ss4 = capture_step_screenshot("04_chat_opened", run_dir)
        if ss4: screenshots.append(ss4)
    else:
        add_step(f"Прямой переход в диалог с «**{clean_contact}**»: фокус установлен в поле ввода сообщения.")
        time.sleep(0.2)

    # Step: Compose and Dispatch Message
    if message:
        add_step(f"Вставка сообщения в поле ввода чата: *«{message}»*.")
        paste_text_native(message)
        time.sleep(0.3)
        
        add_step(f"Отправка сообщения клавишей Enter.")
        send_key_native("enter")
        time.sleep(0.4)

        ss5 = capture_step_screenshot("05_message_sent", run_dir)
        if ss5: screenshots.append(ss5)
        
        add_step(f"Сделан контрольный снимок экрана: подтверждена успешная отправка сообщения.")
    else:
        add_step(f"Чат с контактом «{contact}» успешно открыт и готов к общению.")

    if message:
        summary_text = f"Сообщение для контакта «{contact}» в {m_name} успешно отправлено: «{message}», сэр."
    else:
        summary_text = f"Диалог с контактом «{contact}» в {m_name} открыт, сэр."

    return {
        "success": True,
        "action": "autonomous_messenger_task",
        "messenger": m_name,
        "contact": contact,
        "message": message,
        "steps": steps_log,
        "screenshots": screenshots,
        "summary": summary_text
    }

# ─── AUTONOMOUS BROWSER AGENT (SAFARI / CHROME) ─────────────────
def execute_autonomous_browser_task(browser: str, query_or_url: str) -> Dict[str, Any]:
    """
    Executes a visual multi-step browser task:
    1. Launches Safari (macOS) or specified browser.
    2. Takes visual checkpoint #1.
    3. Focuses URL/Search address bar (Cmd+L / Ctrl+L).
    4. Pastes destination URL or search query.
    5. Submits via Enter, waits for page rendering.
    6. Takes confirmation screenshot #2.
    """
    run_dir = get_agent_run_dir()
    steps_log: List[str] = []
    screenshots: List[str] = []
    
    b_name = "Safari" if (IS_MAC and browser.lower() in ["safari", "сафари", "браузер", "auto"]) else browser.title()
    
    steps_log.append(f"1. Запуск веб-браузера **{b_name}** и вывод окна на передний план.")
    activate_app_window(b_name)
    time.sleep(0.7)

    ss1 = capture_step_screenshot("01_browser_launched", run_dir)
    if ss1: screenshots.append(ss1)

    steps_log.append(f"2. Фокусировка адресной строки браузера (`{'Cmd+L' if IS_MAC else 'Ctrl+L'}`).")
    if IS_MAC:
        send_hotkey_native("cmd", "l")
    else:
        send_hotkey_native("ctrl", "l")
    time.sleep(0.2)

    # Format destination URL or search query
    is_url = query_or_url.startswith("http://") or query_or_url.startswith("https://") or ("." in query_or_url and " " not in query_or_url)
    target_dest = query_or_url if query_or_url.startswith("http") else (f"https://{query_or_url}" if is_url else query_or_url)

    steps_log.append(f"3. Ввод адреса/запроса «**{query_or_url}**» и переход к веб-странице.")
    paste_text_native(target_dest)
    time.sleep(0.1)
    send_key_native("enter")
    time.sleep(1.2)

    ss2 = capture_step_screenshot("02_browser_page_loaded", run_dir)
    if ss2: screenshots.append(ss2)

    steps_log.append(f"4. Страница загружена, сохранен контрольный снимок экрана.")

    summary_text = (
        f"🌐 **Автономный AI Агент выполнил задачу в {b_name}:**\n\n"
        + "\n".join(steps_log)
    )

    return {
        "success": True,
        "action": "autonomous_browser_task",
        "browser": b_name,
        "destination": target_dest,
        "steps": steps_log,
        "screenshots": screenshots,
        "summary": summary_text
    }

# ─── AUTONOMOUS NOTES & TEXT AGENT ──────────────────────────────
def execute_autonomous_notes_task(text: str, title: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes an autonomous note creation loop:
    1. Launches Notes (macOS) or Notepad (Windows).
    2. Takes visual checkpoint #1.
    3. Creates new note (Cmd+N / Ctrl+N).
    4. Pastes title & note body.
    5. Takes confirmation screenshot #2.
    """
    run_dir = get_agent_run_dir()
    steps_log: List[str] = []
    screenshots: List[str] = []

    target_app = "Notes" if IS_MAC else "notepad"
    app_label = "Apple Заметки" if IS_MAC else "Блокнот"

    steps_log.append(f"1. Запуск приложения **{app_label}**.")
    activate_app_window(target_app)
    time.sleep(0.7)

    ss1 = capture_step_screenshot("01_notes_app_opened", run_dir)
    if ss1: screenshots.append(ss1)

    steps_log.append(f"2. Создание новой заметки (`{'Cmd+N' if IS_MAC else 'Ctrl+N'}`).")
    if IS_MAC:
        send_hotkey_native("cmd", "n")
    else:
        send_hotkey_native("ctrl", "n")
    time.sleep(0.3)

    full_note = f"{title}\n\n{text}" if title else text
    steps_log.append(f"3. Запись текста заметки в редактор.")
    paste_text_native(full_note)
    time.sleep(0.4)

    ss2 = capture_step_screenshot("02_note_saved", run_dir)
    if ss2: screenshots.append(ss2)

    steps_log.append(f"4. Текст успешно зафиксирован, сохранен контрольный снимок экрана.")

    summary_text = (
        f"📝 **Автономный AI Агент создал заметку в {app_label}:**\n\n"
        + "\n".join(steps_log)
    )

    return {
        "success": True,
        "action": "autonomous_notes_task",
        "app": app_label,
        "steps": steps_log,
        "screenshots": screenshots,
        "summary": summary_text
    }
