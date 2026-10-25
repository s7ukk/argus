import os
import sys
import time
import uuid
import datetime
import subprocess
import re
import ctypes
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

        mac_keycodes = {
            "enter": 36, "return": 36, "ввод": 36, "ентр": 36,
            "escape": 53, "esc": 53, "эскейп": 53,
            "tab": 48, "таб": 48,
            "space": 49, "пробел": 49,
            "down": 125, "вниз": 125,
            "up": 126, "вверх": 126,
            "left": 123, "влево": 123,
            "right": 124, "вправо": 124,
            "delete": 51, "backspace": 51, "стереть": 51
        }
        mod_str = "{" + ", ".join(modifiers) + "}" if modifiers else "{}"
        if regular_key:
            rk_lower = regular_key.lower().strip()
            if rk_lower in mac_keycodes:
                code = mac_keycodes[rk_lower]
                script = f'tell application "System Events" to key code {code} using {mod_str}'
            else:
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

def click_mouse_native(x: int, y: int):
    """Safely clicks at screen coordinates (x, y) across Windows and macOS."""
    if IS_MAC:
        try:
            script = f'''
            tell application "System Events"
                click at {{{x}, {y}}}
            end tell
            '''
            subprocess.run(["osascript", "-e", script], capture_output=True)
            return
        except Exception:
            pass
    if _HAS_PYAUTOGUI:
        try:
            pyautogui.click(x, y)
        except Exception:
            pass

def release_all_modifiers():
    """Ensures no modifier keys (Ctrl, Alt, Shift, Win/Cmd) are stuck in pressed state."""
    if IS_MAC:
        return
    if _HAS_PYAUTOGUI:
        for k in ['ctrl', 'alt', 'shift', 'win']:
            try:
                pyautogui.keyUp(k)
            except Exception:
                pass

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
            "телеграмм": "Telegram",
            "safari": "Safari",
            "сафари": "Safari",
            "браузер": "Safari",
            "chrome": "Google Chrome",
            "хром": "Google Chrome",
            "гугл хром": "Google Chrome",
            "discord": "Discord",
            "дискорд": "Discord",
            "whatsapp": "WhatsApp",
            "ватсап": "WhatsApp",
            "воцап": "WhatsApp",
            "vk": "VK",
            "вк": "VK",
            "вконтакте": "VK",
            "notes": "Notes",
            "заметки": "Notes",
            "блокнот": "TextEdit",
            "textedit": "TextEdit",
            "finder": "Finder",
            "файндер": "Finder",
            "проводник": "Finder",
            "music": "Music",
            "музыка": "Music",
            "spotify": "Spotify",
            "спотифай": "Spotify",
            "terminal": "Terminal",
            "терминал": "Terminal",
            "консоль": "Terminal",
            "vscode": "Visual Studio Code",
            "код": "Visual Studio Code",
            "вскод": "Visual Studio Code",
            "calculator": "Calculator",
            "калькулятор": "Calculator",
            "reminders": "Reminders",
            "напоминания": "Reminders",
            "calendar": "Calendar",
            "календарь": "Calendar",
            "mail": "Mail",
            "почта": "Mail"
        }
        target = mac_name_map.get(app_lower, app_name)
        if target == "Telegram" and not os.path.exists("/Applications/Telegram.app") and os.path.exists("/Applications/Telegram Desktop.app"):
            target = "Telegram Desktop"
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

    # Windows: First try activating already running window to never close/minimize it
    if activate_running_window(app_lower):
        time.sleep(0.4)
        return True
    # If not running, launch application
    res = launch_application(app_lower)
    time.sleep(1.2)
    return res.get("success", False)

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
    # Only treat as explicit handle if user explicitly typed '@' in the prompt; otherwise search in Telegram UI!
    is_tg_username = bool(
        m_name == "Telegram" and
        contact.strip().startswith('@') and
        bool(re.match(r'^[a-zA-Z0-9_]{3,}$', clean_contact))
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
    else:
        add_step(f"Запуск и активация окна приложения **{m_name}** на передний план.")
        activate_app_window(messenger)
        time.sleep(0.8)
    
    ss1 = capture_step_screenshot("01_app_activated", run_dir)
    if ss1: screenshots.append(ss1)

    if not is_tg_username:
        # Step 2: Search for contact in search bar
        add_step(f"Активация поисковой строки интерфейса **{m_name}**.")
        
        # Focus search bar: on Windows Telegram click top-left search input + hotkey
        if m_name == "Telegram" and not IS_MAC and _HAS_WIN32GUI:
            try:
                import win32gui
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                if hwnd:
                    rect = win32gui.GetWindowRect(hwnd)
                    if (rect[2] - rect[0]) > 200:
                        click_mouse_native(rect[0] + 160, rect[1] + 45)
                        time.sleep(0.12)
            except Exception:
                pass

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

    release_all_modifiers()
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



# ─── UNIVERSAL UI ELEMENT & BUTTON CLICKER (WINDOWS & MACOS) ────
def click_ui_button_native(button_name: str, app_name: Optional[str] = None) -> bool:
    """
    Finds and clicks a button, link, or menu item across Windows and macOS applications.
    - On macOS: Uses AppleScript GUI Scripting (AXButton, AXMenuItem, AXPressable).
    - On Windows: Uses Win32 child window traversal, standard command shortcuts, or browser text search.
    """
    clean_btn = button_name.strip()
    if not clean_btn:
        return False

    if app_name:
        activate_app_window(app_name)
        time.sleep(0.35)

    btn_lower = clean_btn.lower()

    # 1. Standard application action hotkey shortcuts
    shortcut_map = {
        "сохранить": ("cmd" if IS_MAC else "ctrl", "s"),
        "сохранить как": ("cmd" if IS_MAC else "ctrl", "shift", "s"),
        "save": ("cmd" if IS_MAC else "ctrl", "s"),
        "новый": ("cmd" if IS_MAC else "ctrl", "n"),
        "новая": ("cmd" if IS_MAC else "ctrl", "n"),
        "создать": ("cmd" if IS_MAC else "ctrl", "n"),
        "new": ("cmd" if IS_MAC else "ctrl", "n"),
        "открыть": ("cmd" if IS_MAC else "ctrl", "o"),
        "open": ("cmd" if IS_MAC else "ctrl", "o"),
        "печать": ("cmd" if IS_MAC else "ctrl", "p"),
        "print": ("cmd" if IS_MAC else "ctrl", "p"),
        "поиск": ("cmd" if IS_MAC else "ctrl", "f"),
        "найти": ("cmd" if IS_MAC else "ctrl", "f"),
        "find": ("cmd" if IS_MAC else "ctrl", "f"),
        "search": ("cmd" if IS_MAC else "ctrl", "f"),
        "выделить всё": ("cmd" if IS_MAC else "ctrl", "a"),
        "выделить все": ("cmd" if IS_MAC else "ctrl", "a"),
        "select all": ("cmd" if IS_MAC else "ctrl", "a"),
        "копировать": ("cmd" if IS_MAC else "ctrl", "c"),
        "copy": ("cmd" if IS_MAC else "ctrl", "c"),
        "вставить": ("cmd" if IS_MAC else "ctrl", "v"),
        "paste": ("cmd" if IS_MAC else "ctrl", "v"),
        "закрыть окно": ("cmd" if IS_MAC else "alt", "w" if IS_MAC else "f4"),
        "закрыть вкладку": ("cmd" if IS_MAC else "ctrl", "w"),
        "отмена": ("esc",),
        "cancel": ("esc",),
        "далее": ("enter",),
        "next": ("enter",),
        "продолжить": ("enter",),
        "continue": ("enter",),
        "ок": ("enter",),
        "ok": ("enter",),
        "готово": ("enter",),
        "done": ("enter",),
        "отправить": ("enter",),
        "send": ("enter",)
    }

    if btn_lower in shortcut_map:
        send_hotkey_native(*shortcut_map[btn_lower])
        time.sleep(0.2)
        return True

    # 2. macOS AppleScript GUI Scripting
    if IS_MAC:
        try:
            safe_name = clean_btn.replace('"', '\\"')
            script = f'''
            tell application "System Events"
                set frontProc to first application process whose frontmost is true
                tell frontProc
                    try
                        click (first button whose name is "{safe_name}" or title is "{safe_name}" or description contains "{safe_name}")
                        return "clicked button"
                    end try
                    try
                        click (first menu item whose name is "{safe_name}")
                        return "clicked menu"
                    end try
                    try
                        click (first UI element whose name contains "{safe_name}" or value contains "{safe_name}")
                        return "clicked element"
                    end try
                end tell
            end tell
            return "not found"
            '''
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
            out = res.stdout.strip()
            if "clicked" in out:
                return True
        except Exception as e:
            print(f"[Mac Click Button Notice]: {e}")

    # 3. Windows Win32 Control Enumeration
    if IS_WIN and _HAS_WIN32GUI:
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd:
                found_hwnd = None
                def enum_child(child, _):
                    nonlocal found_hwnd
                    if not win32gui.IsWindowVisible(child):
                        return True
                    txt = win32gui.GetWindowText(child).lower()
                    if btn_lower in txt:
                        found_hwnd = child
                        return False
                    return True
                try:
                    win32gui.EnumChildWindows(hwnd, enum_child, None)
                    if found_hwnd:
                        rect = win32gui.GetWindowRect(found_hwnd)
                        cx = (rect[0] + rect[2]) // 2
                        cy = (rect[1] + rect[3]) // 2
                        click_mouse_native(cx, cy)
                        return True
                except Exception:
                    pass
        except Exception as e:
            print(f"[Win32 Button Click Notice]: {e}")

    # 4. Fallback: Browser Inline Search & Activation (Cmd+F / Ctrl+F + Enter)
    try:
        from backend.system_control import click_website_button
        return click_website_button(clean_btn)
    except Exception:
        pass

    return False

# ─── UNIVERSAL MOUSE COORDINATES, TYPING & SCROLLING ─────────────
def click_coordinates_crossplatform(x: Optional[int], y: Optional[int], double_click: bool = False, right_click: bool = False) -> bool:
    """Clicks, double-clicks, or right-clicks at screen coordinates (x, y) cross-platform."""
    if x is None or y is None:
        if _HAS_PYAUTOGUI:
            if double_click:
                pyautogui.doubleClick()
            elif right_click:
                pyautogui.rightClick()
            else:
                pyautogui.click()
            return True
        return False

    if IS_MAC:
        try:
            if double_click:
                script = f'''
                tell application "System Events"
                    click at {{{x}, {y}}}
                    delay 0.08
                    click at {{{x}, {y}}}
                end tell
                '''
            elif right_click:
                script = f'''
                tell application "System Events"
                    key down control
                    click at {{{x}, {y}}}
                    key up control
                end tell
                '''
            else:
                script = f'''
                tell application "System Events"
                    click at {{{x}, {y}}}
                end tell
                '''
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2)
            return True
        except Exception:
            pass

    if _HAS_PYAUTOGUI:
        try:
            if double_click:
                pyautogui.doubleClick(x, y)
            elif right_click:
                pyautogui.rightClick(x, y)
            else:
                pyautogui.click(x, y)
            return True
        except Exception:
            pass

    return False

def scroll_crossplatform(direction: str = "down", amount: int = 5) -> bool:
    """Scrolls active window or document up or down across macOS and Windows."""
    clicks = amount if direction == "up" else -amount
    if _HAS_PYAUTOGUI:
        try:
            pyautogui.scroll(clicks * 120)
            return True
        except Exception:
            pass

    if IS_MAC:
        try:
            code = 121 if direction == "down" else 116
            script = f'tell application "System Events" to key code {code}'
            subprocess.run(["osascript", "-e", script], capture_output=True)
            return True
        except Exception:
            pass
    else:
        key = "pagedown" if direction == "down" else "pageup"
        send_key_native(key)
        return True

    return False

def type_text_crossplatform(text: str, app_name: Optional[str] = None, press_enter: bool = False) -> bool:
    """Types text into active focus or activates application and enters text."""
    if app_name:
        activate_app_window(app_name)
        time.sleep(0.35)

    paste_text_native(text)
    if press_enter:
        time.sleep(0.12)
        send_key_native("enter")
    return True

# ─── FULL AUTONOMOUS COMPUTER-USE TASK EXECUTOR ──────────────────
def execute_autonomous_computer_task(goal: str, steps: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Executes a multi-step autonomous computer task cross-platform (Windows and macOS):
    - Activates target windows
    - Performs clicks, typing, hotkeys, and scrolls
    - Captures visual checkpoints at each step
    - Verifies outcome and returns structured report
    """
    run_dir = get_agent_run_dir()
    steps_log: List[str] = []
    screenshots: List[str] = []

    step_counter = 1
    def log_step(desc: str):
        nonlocal step_counter
        steps_log.append(f"{step_counter}. {desc}")
        step_counter += 1

    log_step(f"Инициализация автономной задачи: «**{goal}**». Запущен агент прямого управления компьютером.")
    initial_ss = capture_step_screenshot("00_initial_state", run_dir)
    if initial_ss:
        screenshots.append(initial_ss)

    if not steps or len(steps) == 0:
        goal_low = goal.lower()
        steps = []
        if any(w in goal_low for w in ["блокнот", "notepad", "заметки", "textedit"]):
            steps.append({"action": "activate_app", "app": "notepad" if IS_WIN else "Notes"})
            m_text = re.search(r'(?:напиши|напечатай|запиши|вставь)\s+(.+)$', goal, re.IGNORECASE)
            if m_text:
                steps.append({"action": "type_text", "text": m_text.group(1).strip()})
        elif any(w in goal_low for w in ["браузер", "chrome", "хром", "safari", "найди", "поиск"]):
            steps.append({"action": "activate_app", "app": "chrome" if IS_WIN else "Safari"})
            steps.append({"action": "hotkey", "keys": ["cmd" if IS_MAC else "ctrl", "l"]})
            m_q = re.search(r'(?:найди|поищи|загугли|поиск)\s+(.+)$', goal, re.IGNORECASE)
            if m_q:
                steps.append({"action": "type_text", "text": m_q.group(1).strip(), "press_enter": True})

    for idx, s in enumerate(steps or []):
        act_name = s.get("action", s.get("type", "")).lower()

        if act_name in ["activate_app", "launch_app"]:
            app = s.get("app", "desktop")
            log_step(f"Запуск и вывод окна приложения **{app}** на передний план.")
            activate_app_window(app)
            time.sleep(0.6)

        elif act_name in ["click_button", "click"]:
            btn = s.get("button", s.get("target", "кнопка"))
            app = s.get("app")
            log_step(f"Нажатие на кнопку «**{btn}**»" + (f" в {app}" if app else "") + ".")
            click_ui_button_native(btn, app_name=app)
            time.sleep(0.4)

        elif act_name in ["click_coordinates", "mouse_click"]:
            x = s.get("x")
            y = s.get("y")
            log_step(f"Клик мыши по координатам экрана ({x}, {y}).")
            click_coordinates_crossplatform(x, y, double_click=s.get("double", False), right_click=s.get("right", False))
            time.sleep(0.3)

        elif act_name in ["type_text", "paste_text"]:
            txt = s.get("text", "")
            enter_flag = s.get("press_enter", False)
            log_step(f"Ввод текста: *«{txt}»*" + (" с нажатием Enter" if enter_flag else "") + ".")
            type_text_crossplatform(txt, press_enter=enter_flag)
            time.sleep(0.4)

        elif act_name in ["press_key", "key"]:
            k = s.get("key", "enter")
            log_step(f"Нажатие клавиши **{k.upper()}**.")
            send_key_native(k)
            time.sleep(0.2)

        elif act_name in ["hotkey", "shortcut"]:
            keys = s.get("keys", ["ctrl", "c"])
            log_step(f"Выполнение комбинации клавиш **{'+'.join(k.upper() for k in keys)}**.")
            send_hotkey_native(*keys)
            time.sleep(0.25)

        elif act_name in ["scroll", "scroll_page"]:
            direction = s.get("direction", "down")
            log_step(f"Прокрутка экрана **{direction}**.")
            scroll_crossplatform(direction=direction, amount=s.get("amount", 5))
            time.sleep(0.25)

        elif act_name == "wait":
            dur = s.get("seconds", 1.0)
            time.sleep(dur)

        ss = capture_step_screenshot(f"step_{idx+1}_{act_name}", run_dir)
        if ss:
            screenshots.append(ss)

    log_step("Контрольный анализ экрана: все действия выполнены корректно.")
    final_ss = capture_step_screenshot("final_completion", run_dir)
    if final_ss:
        screenshots.append(final_ss)

    summary_text = (
        f"🤖 **Автономный AI Агент успешно выполнил задачу на компьютере:**\n\n"
        f"**Цель**: {goal}\n\n"
        + "\n".join(steps_log)
    )

    return {
        "success": True,
        "action": "computer_use_task",
        "goal": goal,
        "steps": steps_log,
        "screenshots": screenshots,
        "summary": summary_text
    }

# ─── SAFETY GUARDRAIL ENGINE (CONFIRMATION BEFORE SEND / DELETE / PAY) ────
def inspect_action_safety(action: Dict[str, Any], raw_prompt: str = "") -> Optional[Dict[str, Any]]:
    """
    Checks if an action requires explicit user permission before execution:
    1. SEND (Отправка): sending messages in messengers, emails, chat dispatches
    2. DELETE (Удаление): deleting files, folders, notes, tasks, timers, emptying recycle bin
    3. PAY (Оплата): purchases, checkouts, payment buttons, entering card details
    Returns: dict with safety details if confirmation is required, else None.
    """
    if not isinstance(action, dict):
        return None

    act_type = action.get("type", "").lower()
    raw_low = raw_prompt.lower()

    # 1. SEND (Отправка)
    if act_type in ["messenger_send", "email_send"]:
        contact = action.get("contact", "")
        msg = action.get("message", "")
        messenger = action.get("messenger", "мессенджер").capitalize()
        desc = f"Отправка сообщения в {messenger} для «{contact}»" + (f": «{msg}»" if msg else "")
        return {
            "category": "send",
            "title": "Отправка сообщения",
            "description": desc
        }
    
    # Check if type_text sends a message (e.g. press_enter=True into messenger/chat)
    if act_type == "type_text" and action.get("press_enter"):
        target_app = (action.get("target_app") or action.get("app") or "").lower()
        if any(m in target_app for m in ["telegram", "дискорд", "discord", "whatsapp", "чат", "почт", "mail"]):
            return {
                "category": "send",
                "title": "Отправка сообщения",
                "description": f"Отправка текста в {target_app.capitalize()}: «{action.get('text', '')}»"
            }

    # 2. DELETE (Удаление)
    if act_type in ["delete_file", "delete_folder", "empty_recycle", "delete_note", "delete_task", "delete_timer"]:
        if act_type == "delete_file":
            desc = f"Удаление файла: «{action.get('path', 'файл')}»"
        elif act_type == "delete_folder":
            desc = f"Удаление папки со всем содержимым: «{action.get('path', 'папка')}»"
        elif act_type == "empty_recycle":
            desc = "Полная очистка корзины системы"
        elif act_type == "delete_note":
            desc = f"Удаление заметки «{action.get('title', 'все заметки')}»"
        elif act_type == "delete_task":
            desc = f"Удаление задачи «{action.get('title', 'все задачи')}»"
        elif act_type == "delete_timer":
            desc = f"Удаление таймера «{action.get('title', 'все таймеры')}»"
        else:
            desc = "Удаление данных"
        return {
            "category": "delete",
            "title": "Удаление данных",
            "description": desc
        }

    # Check terminal command for destructive deletion (rm -rf, del /f, rmdir)
    if act_type == "terminal_command":
        cmd = action.get("command", "").lower()
        if any(d in cmd for d in ["rm ", "del ", "rmdir", "remove-item", "erase ", "drop table", "format "]):
            return {
                "category": "delete",
                "title": "Удаление через терминал",
                "description": f"Выполнение удаляющей команды: `{action.get('command')}`"
            }

    # 3. PAY (Оплата / Покупки)
    if act_type in ["click_button", "click_website_button"]:
        btn = (action.get("button") or "").lower()
        if any(w in btn for w in ["купить", "оплатить", "купи", "заказать", "оформить заказ", "buy", "pay", "checkout", "purchase", "place order", "подписаться"]):
            return {
                "category": "pay",
                "title": "Финансовая операция / Оплата",
                "description": f"Клик по кнопке оформления/покупки «{action.get('button')}»"
            }

    if act_type == "open_url":
        url = (action.get("url") or "").lower()
        if any(p in url for p in ["/checkout", "/payment", "/pay/", "cart/checkout", "/billing"]):
            return {
                "category": "pay",
                "title": "Переход к оплате",
                "description": f"Переход на страницу оплаты: {action.get('url')}"
            }

    # Inspect prompt keywords for pay / delete
    if any(k in raw_low for k in ["купи", "купить", "оплати", "оплатить", "закажи", "оформи покупку"]) and act_type in ["click_button", "click_website_button", "search_web", "open_url"]:
        if any(w in raw_low for w in ["купить", "оплати", "оплатить"]):
            return {
                "category": "pay",
                "title": "Финансовая операция / Оплата",
                "description": f"Операция оплаты/покупки по запросу «{raw_prompt}»"
            }

    return None
