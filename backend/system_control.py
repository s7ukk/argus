import threading
import os
import sys
import re
import subprocess
import webbrowser
import psutil
import ctypes
import datetime
import glob
import time
import shutil
import json
import urllib.parse
from typing import Dict, Any, Optional, List
from PIL import Image

try:
    import winreg
    _HAS_WINREG = True
except Exception:
    _HAS_WINREG = False

try:
    import win32gui
    import win32con
    _HAS_WIN32 = True
    _HAS_WIN32GUI = True
except Exception:
    _HAS_WIN32 = False
    _HAS_WIN32GUI = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    _HAS_PYAUTOGUI = True
except Exception:
    _HAS_PYAUTOGUI = False

try:
    import pyperclip
    _HAS_PYPERCLIP = True
except Exception:
    _HAS_PYPERCLIP = False

try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities
    _HAS_PYCAW = True
except Exception:
    _HAS_PYCAW = False

try:
    import screen_brightness_control as sbc
    _HAS_SBC = True
except Exception:
    _HAS_SBC = False

# Native macOS CoreDisplay setup for hardware display brightness
_MAC_CORE_DISPLAY = None
if sys.platform == "darwin":
    try:
        import ctypes
        import ctypes.util
        cd_path = ctypes.util.find_library("CoreDisplay") or "/System/Library/Frameworks/CoreDisplay.framework/CoreDisplay"
        _MAC_CORE_DISPLAY = ctypes.CDLL(cd_path)
        _MAC_CORE_DISPLAY.CoreDisplay_Display_GetUserBrightness.argtypes = [ctypes.c_uint32]
        _MAC_CORE_DISPLAY.CoreDisplay_Display_GetUserBrightness.restype = ctypes.c_double
        _MAC_CORE_DISPLAY.CoreDisplay_Display_SetUserBrightness.argtypes = [ctypes.c_uint32, ctypes.c_double]
        _MAC_CORE_DISPLAY.CoreDisplay_Display_SetUserBrightness.restype = None
    except Exception:
        _MAC_CORE_DISPLAY = None

# Windows Virtual Keys with Extended Key flag
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

def universal_open_target(target: str) -> bool:
    """Universally opens a file, protocol, or application path across Windows, macOS, and Linux."""
    if sys.platform == "darwin":
        try:
            subprocess.Popen(["open", target])
            return True
        except Exception:
            return False
    elif sys.platform == "win32":
        try:
            os.startfile(target)
            return True
        except Exception:
            try:
                subprocess.Popen(["explorer.exe", target])
                return True
            except Exception:
                return False
    else:
        try:
            subprocess.Popen(["xdg-open", target])
            return True
        except Exception:
            return False

def _press_key(vk_code: int):
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        except Exception:
            pass

# ─── VOLUME CONTROLS (CROSS-PLATFORM) ───────────────────────────
def get_volume() -> int:
    """Get current master audio volume percentage (0-100)."""
    if sys.platform == "darwin":
        try:
            out = subprocess.check_output(["osascript", "-e", "output volume of (get volume settings)"]).decode().strip()
            return int(out)
        except Exception:
            return 50
    if _HAS_PYCAW:
        try:
            speakers = AudioUtilities.GetSpeakers()
            vol = speakers.EndpointVolume
            return int(round(vol.GetMasterVolumeLevelScalar() * 100))
        except Exception as e:
            print("pycaw get volume error:", e)
    return 50

def set_volume(level: int) -> int:
    """Set master volume percentage (0-100)."""
    level = max(0, min(100, level))
    if sys.platform == "darwin":
        try:
            subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=False)
            return level
        except Exception:
            return level
    if _HAS_PYCAW:
        try:
            speakers = AudioUtilities.GetSpeakers()
            vol = speakers.EndpointVolume
            vol.SetMasterVolumeLevelScalar(level / 100.0, None)
            return level
        except Exception as e:
            print("pycaw set volume error:", e)
    return level

def change_volume(delta: int) -> int:
    """Increase or decrease volume by delta."""
    curr = get_volume()
    target = max(0, min(100, curr + delta))
    return set_volume(target)

def toggle_mute() -> bool:
    """Toggle master audio mute."""
    if sys.platform == "darwin":
        try:
            subprocess.run(["osascript", "-e", "set volume output muted (not (output muted of (get volume settings)))"], check=False)
            return True
        except Exception:
            return False
    if _HAS_PYCAW:
        try:
            speakers = AudioUtilities.GetSpeakers()
            vol = speakers.EndpointVolume
            curr = vol.GetMute()
            vol.SetMute(not curr, None)
            return bool(not curr)
        except Exception:
            pass
    _press_key(VK_VOLUME_MUTE)
    return True

# ─── BRIGHTNESS CONTROLS ────────────────────────────────────────
def get_brightness() -> int:
    """Get current screen brightness (0-100)."""
    if sys.platform == "darwin":
        if _MAC_CORE_DISPLAY:
            try:
                b_val = _MAC_CORE_DISPLAY.CoreDisplay_Display_GetUserBrightness(0)
                if b_val >= 0.0:
                    return int(round(b_val * 100))
            except Exception:
                pass
        try:
            out = subprocess.check_output(["brightness", "-l"], timeout=2).decode()
            m = re.search(r'brightness ([\d\.]+)', out)
            if m:
                return int(float(m.group(1)) * 100)
        except Exception:
            pass
        if _HAS_SBC:
            try:
                val = sbc.get_brightness()
                if isinstance(val, list) and len(val) > 0:
                    return int(val[0])
                elif isinstance(val, int):
                    return val
            except Exception:
                pass
        return 80

def set_brightness(level: int) -> int:
    """Set screen brightness (0-100)."""
    level = max(0, min(100, level))
    if sys.platform == "darwin":
        if _MAC_CORE_DISPLAY:
            try:
                _MAC_CORE_DISPLAY.CoreDisplay_Display_SetUserBrightness(0, float(level) / 100.0)
                return level
            except Exception:
                pass
        try:
            val_float = round(level / 100.0, 2)
            res = subprocess.run(["brightness", str(val_float)], capture_output=True, timeout=2)
            if res.returncode == 0:
                return level
        except Exception:
            pass
        if _HAS_SBC:
            try:
                sbc.set_brightness(level)
                return level
            except Exception:
                pass
        return level

    if _HAS_SBC:
        try:
            sbc.set_brightness(level)
            return level
        except Exception as e:
            print("sbc set brightness error:", e)
            
    try:
        ps_cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=3)
    except Exception:
        pass
    return level

def change_brightness(delta: int) -> int:
    """Increase or decrease brightness."""
    curr = get_brightness()
    target = max(0, min(100, curr + delta))
    return set_brightness(target)

# ─── SCREENSHOT SYSTEM (NATIVE GDI TO ANY FOLDER) ────────────────
def take_screenshot(target_folder: Optional[str] = "desktop") -> str:
    """Capture full monitor and save directly to specified Windows folder (Desktop, Downloads, Documents, Pictures) as PNG."""
    user_home = os.path.expanduser('~')
    folder_map = {
        "desktop": os.path.join(user_home, "Desktop"),
        "рабочий стол": os.path.join(user_home, "Desktop"),
        "downloads": os.path.join(user_home, "Downloads"),
        "загрузки": os.path.join(user_home, "Downloads"),
        "documents": os.path.join(user_home, "Documents"),
        "документы": os.path.join(user_home, "Documents"),
        "pictures": os.path.join(user_home, "Pictures"),
        "изображения": os.path.join(user_home, "Pictures"),
        "картинки": os.path.join(user_home, "Pictures"),
    }
    dest_dir = folder_map.get((target_folder or "desktop").lower().strip(), os.path.join(user_home, "Desktop"))
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = os.path.join(dest_dir, filename)

    if sys.platform == "darwin":
        try:
            subprocess.run(["screencapture", "-x", filepath], check=True)
            return filepath
        except Exception as e:
            print("macOS screenshot error:", e)
            return dest_dir

    try:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)

        hdc_screen = user32.GetDC(0)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbm = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
        hbm_old = gdi32.SelectObject(hdc_mem, hbm)

        SRCCOPY = 0x00CC0020
        CAPTUREBLT = 0x40000000
        gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, 0, 0, SRCCOPY | CAPTUREBLT)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ('biSize', ctypes.c_uint32),
                ('biWidth', ctypes.c_int32),
                ('biHeight', ctypes.c_int32),
                ('biPlanes', ctypes.c_uint16),
                ('biBitCount', ctypes.c_uint16),
                ('biCompression', ctypes.c_uint32),
                ('biSizeImage', ctypes.c_uint32),
                ('biXPelsPerMeter', ctypes.c_int32),
                ('biYPelsPerMeter', ctypes.c_int32),
                ('biClrUsed', ctypes.c_uint32),
                ('biClrImportant', ctypes.c_uint32),
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buf = ctypes.create_string_buffer(width * height * 4)
        gdi32.GetDIBits(hdc_mem, hbm, 0, height, buf, ctypes.byref(bmi), 0)

        gdi32.SelectObject(hdc_mem, hbm_old)
        gdi32.DeleteObject(hbm)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)

        img = Image.frombuffer('RGBA', (width, height), buf, 'raw', 'BGRA', 0, 1)
        img.convert('RGB').save(filepath, 'PNG')
        return filepath
    except Exception as e:
        print("GDI screenshot error:", e)
        trigger_screenshot_tool()
        return dest_dir

def take_screenshot_to_desktop() -> str:
    return take_screenshot("desktop")

def trigger_screenshot_tool():
    """Trigger system Snipping Tool (Win + Shift + S on Windows, screencapture on Mac)."""
    if sys.platform == "darwin":
        try:
            subprocess.Popen(["screencapture", "-i", "-c"])
            return
        except Exception:
            return
    VK_LWIN = 0x5B
    VK_SHIFT = 0x10
    VK_S = 0x53
    try:
        ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_SHIFT, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_S, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_S, 0, 2, 0)
        ctypes.windll.user32.keybd_event(VK_SHIFT, 0, 2, 0)
        ctypes.windll.user32.keybd_event(VK_LWIN, 0, 2, 0)
    except Exception:
        pass

# ─── DYNAMIC PC APPLICATION SCANNER & CATALOG ────────────────────
_APP_CATALOG: Dict[str, str] = {}
_LAST_SCAN_TIME: float = 0.0

def scan_all_installed_apps(force: bool = False) -> Dict[str, str]:
    """
    Dynamically scans all user and system locations for installed applications:
    - Start Menu Shortcuts (User & All Users)
    - Desktop Shortcuts (.lnk)
    - Registry App Paths (HKLM & HKCU)
    - User AppData (Local/Programs, Local, Roaming)
    - Program Files & Program Files (x86)
    Caches results in memory for instant lookups.
    """
    global _APP_CATALOG, _LAST_SCAN_TIME
    now = time.time()
    if not force and _APP_CATALOG and (now - _LAST_SCAN_TIME < 300):
        return _APP_CATALOG

    catalog: Dict[str, str] = {}

    # macOS Applications scanning
    if sys.platform == "darwin":
        mac_dirs = ["/Applications", "/System/Applications", "/Applications/Utilities", os.path.expanduser("~/Applications")]
        for m_dir in mac_dirs:
            if os.path.exists(m_dir):
                for app_bundle in glob.glob(os.path.join(m_dir, "*.app")):
                    b_name = os.path.splitext(os.path.basename(app_bundle))[0].lower().strip()
                    catalog[b_name] = app_bundle
                    no_sp = re.sub(r'[^a-z0-9а-яё]', '', b_name)
                    if no_sp:
                        catalog[no_sp] = app_bundle
        catalog["safari"] = "/Applications/Safari.app"
        catalog["сафари"] = "/Applications/Safari.app"
        catalog["chrome"] = catalog.get("google chrome", "/Applications/Google Chrome.app")
        catalog["хром"] = catalog.get("chrome")
        catalog["telegram"] = catalog.get("telegram", "/Applications/Telegram.app")
        catalog["телеграм"] = catalog.get("telegram")
        catalog["vscode"] = catalog.get("visual studio code", "/Applications/Visual Studio Code.app")
        catalog["terminal"] = "/System/Applications/Utilities/Terminal.app"
        catalog["терминал"] = "/System/Applications/Utilities/Terminal.app"
        catalog["калькулятор"] = "/System/Applications/Calculator.app"
        catalog["calculator"] = "/System/Applications/Calculator.app"
        catalog["музыка"] = "/System/Applications/Music.app"
        catalog["music"] = "/System/Applications/Music.app"
        catalog["spotify"] = catalog.get("spotify", "/Applications/Spotify.app")
        catalog["спотифай"] = catalog.get("spotify")
        _APP_CATALOG = catalog
        _LAST_SCAN_TIME = now
        return _APP_CATALOG

    # 1. Registry App Paths
    if _HAS_WINREG:
        reg_roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        ]
        for hkey, subkey in reg_roots:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    count = winreg.QueryInfoKey(key)[0]
                    for i in range(count):
                        try:
                            k_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, k_name) as app_key:
                                raw_val = winreg.QueryValue(app_key, None)
                                if raw_val:
                                    path = raw_val.strip('"').strip("'")
                                    if os.path.exists(path):
                                        base = k_name.lower().replace(".exe", "")
                                        catalog[base] = path
                        except Exception:
                            pass
            except Exception:
                pass

    # 2. Start Menu Shortcuts (.lnk) - User & All Users
    start_menu_dirs = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%USERPROFILE%\Desktop"),
        os.path.expandvars(r"%PUBLIC%\Desktop"),
        r"C:\Users\Public\Desktop",
        os.path.join(os.path.expanduser("~"), "Desktop")
    ]
    for s_dir in start_menu_dirs:
        if os.path.exists(s_dir):
            for lnk in glob.glob(os.path.join(s_dir, "**", "*.lnk"), recursive=True):
                base = os.path.splitext(os.path.basename(lnk))[0].lower().strip()
                if not any(x in base for x in ["uninstall", "деинсталл", "readme", "help", "documentation"]):
                    catalog[base] = lnk
                    # Also register version-stripped and space-stripped variants
                    clean_no_version = re.sub(r'[\d\.\-_]+', ' ', base).strip()
                    if clean_no_version and clean_no_version != base:
                        catalog[clean_no_version] = lnk
                    # Without spaces (e.g. "goland" for "goland 2026.2.1" or "visualstudiocode")
                    no_spaces = re.sub(r'[^a-z0-9а-яё]', '', base)
                    if no_spaces:
                        catalog[no_spaces] = lnk

    # 3. Direct AppData and Program Files Executables
    user_home = os.path.expanduser("~")
    common_patterns = [
        os.path.join(user_home, "AppData", "Local", "*", "*.exe"),
        os.path.join(user_home, "AppData", "Local", "Programs", "*", "*.exe"),
        os.path.join(user_home, "AppData", "Local", "Programs", "*", "*", "*.exe"),
        os.path.join(user_home, "AppData", "Local", "Postman", "app-*", "Postman.exe"),
        os.path.join(user_home, "AppData", "Local", "Postman", "Postman.exe"),
        os.path.join(user_home, "AppData", "Roaming", "*", "*.exe"),
        os.path.join(user_home, "AppData", "Roaming", "Telegram Desktop", "Telegram.exe"),
        r"C:\Program Files\*\*.exe",
        r"C:\Program Files\*\*\*.exe",
        r"C:\Program Files (x86)\*\*.exe",
        r"C:\Program Files (x86)\*\*\*.exe"
    ]
    for pat in common_patterns:
        for p in glob.glob(pat):
            f_name = os.path.splitext(os.path.basename(p))[0].lower()
            if not any(x in f_name for x in ["update", "unins", "setup", "helper", "crash", "installer"]):
                catalog[f_name] = p
                no_spaces = re.sub(r'[^a-z0-9а-яё]', '', f_name)
                if no_spaces:
                    catalog[no_spaces] = p

    # Standard built-ins
    catalog["calc"] = "calc.exe"
    catalog["калькулятор"] = "calc.exe"
    catalog["calculator"] = "calc.exe"
    catalog["notepad"] = "notepad.exe"
    catalog["блокнот"] = "notepad.exe"
    catalog["paint"] = "mspaint.exe"
    catalog["пейнт"] = "mspaint.exe"
    catalog["taskmgr"] = "taskmgr.exe"
    catalog["диспетчер задач"] = "taskmgr.exe"
    catalog["explorer"] = "explorer.exe"
    catalog["проводник"] = "explorer.exe"
    catalog["cmd"] = "cmd.exe"
    catalog["powershell"] = "powershell.exe"
    catalog["терминал"] = "wt.exe"
    catalog["terminal"] = "wt.exe"
    catalog["goland"] = catalog.get("goland") or catalog.get("goland 2026.2.1") or "goland"
    catalog["go land"] = catalog.get("goland") or "goland"

    _APP_CATALOG = catalog
    _LAST_SCAN_TIME = now
    return _APP_CATALOG

# ─── BROWSER DETECTION & AMBIGUITY RESOLVER ───────────────────────
def detect_installed_browsers() -> List[Dict[str, str]]:
    """Detect all web browsers installed on the machine."""
    if sys.platform == "darwin":
        mac_browsers = [
            {"id": "safari", "name": "Apple Safari", "path": "/Applications/Safari.app"},
            {"id": "chrome", "name": "Google Chrome", "path": "/Applications/Google Chrome.app"},
            {"id": "yandex", "name": "Яндекс Браузер", "path": "/Applications/Yandex.app"},
            {"id": "firefox", "name": "Mozilla Firefox", "path": "/Applications/Firefox.app"},
            {"id": "msedge", "name": "Microsoft Edge", "path": "/Applications/Microsoft Edge.app"},
            {"id": "brave", "name": "Brave Browser", "path": "/Applications/Brave Browser.app"},
            {"id": "opera", "name": "Opera", "path": "/Applications/Opera.app"},
        ]
        res = []
        for b in mac_browsers:
            if os.path.exists(b["path"]):
                res.append(b)
        if not res:
            res.append({"id": "safari", "name": "Apple Safari", "path": "/Applications/Safari.app"})
        return res

    catalog = scan_all_installed_apps()
    found: Dict[str, Dict[str, str]] = {}

    browser_defs = [
        {"id": "chrome", "name": "Google Chrome", "tokens": ["chrome", "google chrome"]},
        {"id": "msedge", "name": "Microsoft Edge", "tokens": ["msedge", "edge", "microsoft edge"]},
        {"id": "yandex", "name": "Яндекс Браузер", "tokens": ["yandex", "yandex browser", "browser.exe", "яндекс"]},
        {"id": "firefox", "name": "Mozilla Firefox", "tokens": ["firefox", "mozilla firefox"]},
        {"id": "opera", "name": "Opera", "tokens": ["opera", "opera gx"]},
        {"id": "brave", "name": "Brave Browser", "tokens": ["brave", "brave.exe"]},
    ]

    prog_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
    prog_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
    local_appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))

    default_paths = {
        "chrome": [
            os.path.join(prog_files, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(prog_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local_appdata, "Google", "Chrome", "Application", "chrome.exe")
        ],
        "msedge": [
            os.path.join(prog_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(prog_files, "Microsoft", "Edge", "Application", "msedge.exe")
        ],
        "yandex": [
            os.path.join(local_appdata, "Yandex", "YandexBrowser", "Application", "browser.exe")
        ],
        "firefox": [
            os.path.join(prog_files, "Mozilla Firefox", "firefox.exe"),
            os.path.join(prog_files_x86, "Mozilla Firefox", "firefox.exe")
        ],
        "brave": [
            os.path.join(prog_files, "BraveSoftware", "Brave-Browser", "Application", "brave.exe")
        ],
        "opera": [
            os.path.join(local_appdata, "Programs", "Opera", "launcher.exe"),
            os.path.join(local_appdata, "Programs", "Opera GX", "launcher.exe")
        ]
    }

    # 1. Check known executable paths
    for b in browser_defs:
        b_id = b["id"]
        for p in default_paths.get(b_id, []):
            if os.path.exists(p):
                found[b_id] = {"id": b_id, "name": b["name"], "path": p}
                break

    # 2. Check catalog shortcuts
    for cat_name, cat_path in catalog.items():
        for b in browser_defs:
            b_id = b["id"]
            if b_id not in found and any(t in cat_name for t in b["tokens"]):
                if not any(x in cat_path.lower() for x in ["uninstall", "helper", "crash"]):
                    found[b_id] = {"id": b_id, "name": b["name"], "path": cat_path}

    return list(found.values())

# Initial scan
try:
    scan_all_installed_apps()
except Exception:
    pass


# ─── MESSENGER DETECTION & DISCOVERY (WINDOWS & MACOS) ───────────
def detect_installed_messengers() -> List[Dict[str, str]]:
    """
    Detects all messaging applications installed/active on Windows and macOS.
    Returns list of dicts: [{"id": "telegram", "name": "Telegram", "cmd": "1", "label": "1. Telegram"}, ...]
    """
    found: List[Dict[str, str]] = []

    # Check running processes first
    running_procs = set()
    try:
        for p in psutil.process_iter(['name']):
            p_name = p.info.get('name')
            if p_name:
                running_procs.add(p_name.lower())
    except Exception:
        pass

    if sys.platform == "darwin":
        # macOS Applications check
        mac_messengers = [
            {"id": "telegram", "name": "Telegram", "paths": ["/Applications/Telegram.app", os.path.expanduser("~/Applications/Telegram.app")]},
            {"id": "discord", "name": "Discord", "paths": ["/Applications/Discord.app", os.path.expanduser("~/Applications/Discord.app")]},
            {"id": "whatsapp", "name": "WhatsApp", "paths": ["/Applications/WhatsApp.app", os.path.expanduser("~/Applications/WhatsApp.app")]},
            {"id": "vk", "name": "VK (ВКонтакте)", "paths": ["/Applications/VK.app", "/Applications/VK Messenger.app", os.path.expanduser("~/Applications/VK.app")]},
            {"id": "skype", "name": "Skype", "paths": ["/Applications/Skype.app", os.path.expanduser("~/Applications/Skype.app")]},
            {"id": "slack", "name": "Slack", "paths": ["/Applications/Slack.app", os.path.expanduser("~/Applications/Slack.app")]},
            {"id": "viber", "name": "Viber", "paths": ["/Applications/Viber.app", os.path.expanduser("~/Applications/Viber.app")]},
        ]
        for m in mac_messengers:
            is_installed = any(os.path.exists(p) for p in m["paths"])
            is_running = any(m["id"] in proc for proc in running_procs)
            if is_installed or is_running:
                found.append({"id": m["id"], "name": m["name"]})

    else:
        # Windows Applications check
        local_appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
        appdata = os.environ.get('APPDATA', os.path.expanduser('~\\AppData\\Roaming'))
        prog_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
        prog_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')

        win_messengers = [
            {
                "id": "telegram", "name": "Telegram",
                "procs": ["telegram.exe"],
                "paths": [
                    os.path.join(appdata, "Telegram Desktop", "Telegram.exe"),
                    os.path.join(local_appdata, "Programs", "Telegram Desktop", "Telegram.exe"),
                    os.path.join(prog_files, "Telegram Desktop", "Telegram.exe"),
                ]
            },
            {
                "id": "discord", "name": "Discord",
                "procs": ["discord.exe"],
                "paths": [
                    os.path.join(local_appdata, "Discord", "Update.exe"),
                    os.path.join(local_appdata, "Programs", "Discord", "Discord.exe"),
                ]
            },
            {
                "id": "whatsapp", "name": "WhatsApp",
                "procs": ["whatsapp.exe"],
                "paths": [
                    os.path.join(local_appdata, "WhatsApp", "WhatsApp.exe"),
                ]
            },
            {
                "id": "vk", "name": "VK (ВКонтакте)",
                "procs": ["vk.exe", "vkmessenger.exe", "vk messenger.exe"],
                "paths": [
                    os.path.join(local_appdata, "Programs", "VK", "VK.exe"),
                    os.path.join(local_appdata, "Programs", "VK Messenger", "VK Messenger.exe"),
                ]
            },
            {
                "id": "skype", "name": "Skype",
                "procs": ["skype.exe"],
                "paths": [
                    os.path.join(prog_files, "Microsoft", "Skype for Desktop", "Skype.exe"),
                    os.path.join(prog_files_x86, "Microsoft", "Skype for Desktop", "Skype.exe"),
                ]
            },
            {
                "id": "slack", "name": "Slack",
                "procs": ["slack.exe"],
                "paths": [
                    os.path.join(local_appdata, "slack", "slack.exe"),
                ]
            },
            {
                "id": "viber", "name": "Viber",
                "procs": ["viber.exe"],
                "paths": [
                    os.path.join(local_appdata, "Viber", "Viber.exe"),
                ]
            },
        ]

        for m in win_messengers:
            is_running = any(p in running_procs for p in m["procs"])
            is_installed = any(os.path.exists(p) for p in m["paths"])
            if is_running or is_installed:
                found.append({"id": m["id"], "name": m["name"]})

    standard = [
        {"id": "telegram", "name": "Telegram"},
        {"id": "discord", "name": "Discord"},
        {"id": "whatsapp", "name": "WhatsApp"},
        {"id": "vk", "name": "VK (ВКонтакте)"},
    ]
    found_ids = {m["id"] for m in found}
    for sm in standard:
        if sm["id"] not in found_ids:
            found.append(sm)

    numbered = []
    for idx, m in enumerate(found[:6], 1):
        numbered.append({
            "num": str(idx),
            "id": m["id"],
            "name": m["name"],
            "cmd": str(idx),
            "label": f"{idx}. {m['name']}"
        })
    return numbered

# ─── FOREGROUND WINDOW ACTIVATOR ─────────────────────────────────
_LAST_NON_ARGUS_HWND = None

def force_foreground_window(hwnd: int) -> bool:
    """Forces target HWND into absolute foreground using Win32 API with lock bypass."""
    global _LAST_NON_ARGUS_HWND
    if not _HAS_WIN32GUI:
        return False
    try:
        user32 = ctypes.windll.user32
        # Restore window if minimized
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            user32.ShowWindow(hwnd, win32con.SW_SHOW)

        # Bypass Windows foreground lock timeout by synthesizing an Alt key tap
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 2, 0)

        fg_hwnd = user32.GetForegroundWindow()
        if fg_hwnd != hwnd:
            fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
            target_tid = user32.GetWindowThreadProcessId(hwnd, None)
            if fg_tid and target_tid and fg_tid != target_tid:
                try:
                    user32.AttachThreadInput(fg_tid, target_tid, True)
                except Exception:
                    pass
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            user32.SetFocus(hwnd)
            if fg_tid and target_tid and fg_tid != target_tid:
                try:
                    user32.AttachThreadInput(fg_tid, target_tid, False)
                except Exception:
                    pass
        _LAST_NON_ARGUS_HWND = hwnd
        return True
    except Exception:
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            _LAST_NON_ARGUS_HWND = hwnd
            return True
        except Exception:
            return False

WINDOW_TITLE_ALIASES: Dict[str, List[str]] = {
    "telegram": ["telegram", "telegramdesktop", "телеграм", "телега"],
    "телеграм": ["telegram", "telegramdesktop", "телеграм", "телега"],
    "телега": ["telegram", "telegramdesktop", "телеграм", "телега"],
    "тг": ["telegram", "telegramdesktop", "телеграм", "телега"],
    "discord": ["discord", "дискорд"],
    "дискорд": ["discord", "дискорд"],
    "whatsapp": ["whatsapp", "ватсап"],
    "ватсап": ["whatsapp", "ватсап"],
    "vk": ["vk", "вконтакте", "вк"],
    "вконтакте": ["vk", "вконтакте", "вк"],
    "вк": ["vk", "вконтакте", "вк"],
    "notepad": ["notepad", "блокнот", "текстовый документ", "untitled - notepad", "безымянный - блокнот"],
    "блокнот": ["notepad", "блокнот", "текстовый документ", "untitled - notepad", "безымянный - блокнот"],
    "word": ["word", "ворд", "документ microsoft word", "документ - word"],
    "ворд": ["word", "ворд", "документ microsoft word", "документ - word"],
    "excel": ["excel", "эксель", "книга excel"],
    "эксель": ["excel", "эксель", "книга excel"],
    "chrome": ["chrome", "хром", "google chrome"],
    "хром": ["chrome", "хром", "google chrome"],
    "edge": ["edge", "эдж", "microsoft edge"],
    "yandex": ["yandex", "яндекс"],
    "яндекс": ["yandex", "яндекс"],
    "code": ["visual studio code", "vscode", "code"],
    "vscode": ["visual studio code", "vscode", "code"],
    "вскод": ["visual studio code", "vscode", "code"],
    "terminal": ["windows terminal", "powershell", "cmd", "терминал", "консоль", "командная строка"],
    "терминал": ["windows terminal", "powershell", "cmd", "терминал", "консоль", "командная строка"],
    "explorer": ["проводник", "explorer", "этот компьютер", "папка"],
    "проводник": ["проводник", "explorer", "этот компьютер", "папка"],
}

def activate_running_window(app_query: str) -> bool:
    """
    If an application window is already open, brings it to foreground.
    Supports Windows (Win32 + AttachThreadInput) and macOS (AppleScript / osascript).
    If the application is not running or minimized to tray, automatically launches it.
    """
    if sys.platform == "darwin":
        try:
            mac_app_map = {
                "telegram": "Telegram",
                "discord": "Discord",
                "whatsapp": "WhatsApp",
                "chrome": "Google Chrome",
                "browser": "Safari",
                "safari": "Safari",
                "notepad": "TextEdit",
                "word": "Microsoft Word",
                "vscode": "Visual Studio Code"
            }
            target = mac_app_map.get(app_query.lower().strip(), app_query)
            script = f'tell application "{target}" to activate'
            subprocess.run(['osascript', '-e', script], capture_output=True, timeout=5)
            return True
        except Exception as e:
            print("macOS activate error:", e)
            return False

    if not _HAS_WIN32GUI:
        return False
    query = app_query.lower().strip()
    found_hwnds = []

    browser_aliases = ["chrome", "edge", "yandex", "opera", "firefox", "brave", "vivaldi"]
    target_aliases = WINDOW_TITLE_ALIASES.get(query, [query])

    try:
        from ctypes import wintypes
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def worker_scan():
            try:
                hDesk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x01FF)
                if hDesk:
                    ctypes.windll.user32.SetThreadDesktop(hDesk)
            except Exception:
                pass

            def enum_cb_ctypes(hwnd, _):
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                if length > 0:
                    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.lower()

                # 1. Match by window title
                if query in ["браузер", "browser", "интернет"]:
                    if any(b in title for b in browser_aliases):
                        found_hwnds.append(hwnd)
                        return False
                elif any(alias in title for alias in target_aliases):
                    found_hwnds.append(hwnd)
                    return False
                elif title and (query in title or title.startswith(query)):
                    found_hwnds.append(hwnd)
                    return False

                # 2. Match by process name for Telegram and other apps whose title changes dynamically
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    pid = wintypes.DWORD()
                    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value > 0:
                        try:
                            pname = psutil.Process(pid.value).name().lower()
                            if query in ["telegram", "телеграм", "телега", "тг"] and pname == "telegram.exe":
                                cls_buff = ctypes.create_unicode_buffer(256)
                                ctypes.windll.user32.GetClassNameW(hwnd, cls_buff, 256)
                                if "Qt" in cls_buff.value and "Icon" in cls_buff.value:
                                    if _HAS_WIN32GUI:
                                        rect = win32gui.GetWindowRect(hwnd)
                                        if (rect[2] - rect[0]) > 100 and (rect[3] - rect[1]) > 100:
                                            found_hwnds.append(hwnd)
                                            return False
                                    else:
                                        found_hwnds.append(hwnd)
                                        return False
                            elif query in ["discord", "дискорд"] and "discord" in pname:
                                found_hwnds.append(hwnd)
                                return False
                        except Exception:
                            pass
                return True

            cb_proc = WNDENUMPROC(enum_cb_ctypes)
            ctypes.windll.user32.EnumWindows(cb_proc, 0)

        t_scan = threading.Thread(target=worker_scan)
        t_scan.start()
        t_scan.join(timeout=1.5)
    except Exception:
        pass

    if found_hwnds:
        target = found_hwnds[0]
        force_foreground_window(target)
        return True
    return False

# ─── UNIVERSAL APPLICATION LAUNCHER ──────────────────────────────
# ─── UNIVERSAL APPLICATION LAUNCHER ──────────────────────────────
APP_CANONICAL_KEYS = {
    # Browsers
    "хром": "chrome", "хром браузер": "chrome", "хромбраузер": "chrome",
    "chrome": "chrome", "google chrome": "chrome", "googlechrome": "chrome",
    "гугл": "chrome", "гугл хром": "chrome", "гуглхром": "chrome",
    "браузер": "chrome", "browser": "chrome", "интернет": "chrome",
    "эдж": "msedge", "edge": "msedge", "microsoft edge": "msedge",
    "яндекс": "yandex", "yandex": "yandex", "яндекс браузер": "yandex",
    "опера": "opera", "opera": "opera", "файрфокс": "firefox", "firefox": "firefox",
    "сафари": "safari", "safari": "safari",
    # Music & Streaming
    "саундклауд": "soundcloud", "саунд клауд": "soundcloud", "саунд-клауд": "soundcloud",
    "soundcloud": "soundcloud", "sound cloud": "soundcloud", "sound-cloud": "soundcloud",
    "спотифай": "spotify", "spotify": "spotify", "музыка": "spotify",
    "яндекс музыка": "yandexmusic", "яндекс.музыка": "yandexmusic", "яндексмузыка": "yandexmusic",
    "yandex music": "yandexmusic", "ямузыка": "yandexmusic",
    "вк музыка": "vkmusic", "музыка вк": "vkmusic", "vk music": "vkmusic",
    "ютуб музыка": "ytmusic", "youtube music": "ytmusic",
    # Messengers & Social
    "телега": "telegram", "телеграм": "telegram", "тг": "telegram", "telegram": "telegram",
    "дискорд": "discord", "диск": "discord", "дс": "discord", "discord": "discord",
    "ватсап": "whatsapp", "whatsapp": "whatsapp",
    "стим": "steam", "steam": "steam",
    "твич": "twitch", "twitch": "twitch", "ютуб": "youtube", "youtube": "youtube",
    "рутуб": "rutube", "rutube": "rutube",
    # Dev & Productivity
    "постман": "postman", "postman": "postman", "post man": "postman",
    "код": "code", "вскод": "code", "vscode": "code", "vs code": "code", "visual studio code": "code",
    "голенд": "goland", "голэнд": "goland", "го ленд": "goland", "goland": "goland", "go land": "goland",
    "пайчарм": "pycharm", "pycharm": "pycharm", "вебшторм": "webstorm", "webstorm": "webstorm",
    "гитхаб": "github", "github": "github",
    "калькулятор": "calc", "кальк": "calc", "calc": "calc", "calculator": "calc",
    "блокнот": "notepad", "notepad": "notepad", "заметки": "notes", "notes": "notes",
    "пейнт": "mspaint", "паинт": "mspaint", "paint": "mspaint",
    "проводник": "explorer", "explorer": "explorer", "папки": "explorer", "файлы": "explorer",
    "терминал": "wt", "консоль": "powershell", "powershell": "powershell", "cmd": "cmd",
    "диспетчер задач": "taskmgr", "диспетчер": "taskmgr",
    "настройки": "ms-settings:", "параметры": "ms-settings:",
    "зум": "zoom", "zoom": "zoom", "обска": "obs", "obs": "obs", "obs studio": "obs"
}

WEB_SERVICE_FALLBACKS = {
    "soundcloud": "https://soundcloud.com",
    "саундклауд": "https://soundcloud.com",
    "саунд клауд": "https://soundcloud.com",
    "sound cloud": "https://soundcloud.com",
    "spotify": "https://open.spotify.com",
    "спотифай": "https://open.spotify.com",
    "yandexmusic": "https://music.yandex.ru",
    "яндекс музыка": "https://music.yandex.ru",
    "яндекс.музыка": "https://music.yandex.ru",
    "яндексмузыка": "https://music.yandex.ru",
    "vkmusic": "https://vk.com/music",
    "вк музыка": "https://vk.com/music",
    "ytmusic": "https://music.youtube.com",
    "ютуб музыка": "https://music.youtube.com",
    "youtube music": "https://music.youtube.com",
    "youtube": "https://www.youtube.com",
    "ютуб": "https://www.youtube.com",
    "twitch": "https://twitch.tv",
    "твич": "https://twitch.tv",
    "github": "https://github.com",
    "гитхаб": "https://github.com",
    "netflix": "https://netflix.com",
    "нетфликс": "https://netflix.com",
    "kinopoisk": "https://kinopoisk.ru",
    "кинопоиск": "https://kinopoisk.ru",
    "vk": "https://vk.com",
    "вк": "https://vk.com",
    "wildberries": "https://wildberries.ru",
    "вайлдберриз": "https://wildberries.ru",
    "вб": "https://wildberries.ru",
    "ozon": "https://ozon.ru",
    "озон": "https://ozon.ru",
    "avito": "https://avito.ru",
    "авито": "https://avito.ru",
    "whatsapp": "https://web.whatsapp.com",
    "ватсап": "https://web.whatsapp.com",
    "rutube": "https://rutube.ru",
    "рутуб": "https://rutube.ru",
    "deepseek": "https://chat.deepseek.com",
    "deep seek": "https://chat.deepseek.com",
    "дипсик": "https://chat.deepseek.com",
    "дип сик": "https://chat.deepseek.com",
    "tiktok": "https://www.tiktok.com",
    "тикток": "https://www.tiktok.com",
    "тик ток": "https://www.tiktok.com",
    "дикси": "https://dixy.ru",
    "dixy": "https://dixy.ru",
    "chatgpt": "https://chatgpt.com",
    "чатгпт": "https://chatgpt.com",
    "steam": "https://store.steampowered.com",
    "стим": "https://store.steampowered.com",
    "telegram": "https://web.telegram.org",
    "телеграм": "https://web.telegram.org",
    "телега": "https://web.telegram.org",
    "discord": "https://discord.com",
    "дискорд": "https://discord.com",
    "yandex": "https://yandex.ru",
    "яндекс": "https://yandex.ru",
    "google": "https://google.com",
    "гугл": "https://google.com"
}

def launch_application(app_name: str) -> Dict[str, Any]:
    """
    Universally launches ANY application installed on Windows or macOS.
    Resolves Russian and English synonyms, scans installed programs catalog,
    and seamlessly falls back to official web services (SoundCloud, Spotify, YouTube, etc.) if not installed.
    """
    raw_query = app_name.strip()
    app_lower = raw_query.lower()
    
    # 0. Lone command verb protection (never try to launch an app called "открой" or "запусти")
    if app_lower in ["открой", "открыть", "запусти", "запустить", "включи", "включить", "стартуй", "open", "launch", "start", "run", "приложение", "программу", "софт"]:
        return {"success": False, "error": "Пожалуйста, укажите, какое приложение или сайт открыть (например: «открой soundcloud» или «открой блокнот»)"}

    # Strip common launch command verbs
    clean_app = re.sub(r'^(?:открой|открыть|запусти|запустить|включи|включить|стартуй|стартани|зайди\s+в|зайди\s+на|зайди|перейди\s+в|перейди\s+на|перейди|open|launch|start|run)\s+(?:приложение\s+|программу\s+|софт\s+)?', '', app_lower).strip()
    clean_app = clean_app.replace('пожалуйста', '').replace('пж', '').strip()
    if not clean_app:
        return {"success": False, "error": "Пожалуйста, укажите название приложения или сайта"}

    # Special handling for macOS
    if sys.platform == "darwin":
        mac_aliases = {
            "chrome": "Google Chrome", "хром": "Google Chrome", "google chrome": "Google Chrome",
            "telegram": "Telegram", "телеграм": "Telegram", "телега": "Telegram", "тг": "Telegram", "телеграмм": "Telegram",
            "discord": "Discord", "дискорд": "Discord",
            "spotify": "Spotify", "спотифай": "Spotify",
            "steam": "Steam", "стим": "Steam",
            "vscode": "Visual Studio Code", "код": "Visual Studio Code", "vs code": "Visual Studio Code",
            "code": "Visual Studio Code", "вскод": "Visual Studio Code",
            "calculator": "Calculator", "калькулятор": "Calculator", "кальк": "Calculator",
            "notes": "Notes", "заметки": "Notes", "блокнот": "TextEdit", "textedit": "TextEdit",
            "terminal": "Terminal", "терминал": "Terminal", "cmd": "Terminal", "cmd.exe": "Terminal", "powershell": "Terminal",
            "safari": "Safari", "сафари": "Safari", "браузер": "Safari", "browser": "Safari", "интернет": "Safari",
            "finder": "Finder", "файлы": "Finder", "проводник": "Finder", "файндер": "Finder", "explorer": "Finder", "explorer.exe": "Finder",
            "activity monitor": "Activity Monitor", "диспетчер задач": "Activity Monitor", "мониторинг системы": "Activity Monitor",
            "taskmgr": "Activity Monitor", "taskmgr.exe": "Activity Monitor",
            "settings": "System Settings", "настройки": "System Settings", "параметры": "System Settings",
            "music": "Music", "музыка": "Music",
            "яндекс": "Yandex", "яндекс браузер": "Yandex",
            "яндекс музыка": "Yandex Music", "саундклауд": "SoundCloud", "sound cloud": "SoundCloud", "soundcloud": "SoundCloud"
        }
        target_mac = mac_aliases.get(clean_app, clean_app)
        try:
            res = subprocess.run(["open", "-a", target_mac], capture_output=True)
            if res.returncode == 0:
                # Also bring window directly to foreground
                subprocess.run(["osascript", "-e", f'tell application "{target_mac}" to activate'], capture_output=True)
                return {"success": True, "launched": target_mac, "os": "mac"}
        except Exception:
            pass
        # Check web fallback on macOS
        target_key_check = APP_CANONICAL_KEYS.get(clean_app) or clean_app
        if clean_app in WEB_SERVICE_FALLBACKS or target_key_check in WEB_SERVICE_FALLBACKS:
            web_u = WEB_SERVICE_FALLBACKS.get(clean_app) or WEB_SERVICE_FALLBACKS.get(target_key_check)
            open_url(web_u)
            return {"success": True, "launched": f"{clean_app.title()} (веб-сервис)", "type": "web_service", "url": web_u}

    # 1. Try bringing running window to foreground first (Windows & Mac)
    try:
        if activate_running_window(clean_app or app_lower):
            return {"success": True, "launched": app_name, "type": "activated_window"}
    except Exception:
        pass

    # 2. Protocol handlers
    protocols = {
        "telegram": "tg:", "телеграм": "tg:", "телега": "tg:", "тг": "tg:",
        "discord": "discord:", "дискорд": "discord:",
        "steam": "steam://open/main", "стим": "steam://open/main",
        "spotify": "spotify:", "спотифай": "spotify:",
        "settings": "ms-settings:", "настройки": "ms-settings:", "параметры": "ms-settings:"
    }
    for proto_k, proto_uri in protocols.items():
        if proto_k == clean_app or proto_k == app_lower:
            if universal_open_target(proto_uri):
                return {"success": True, "launched": app_name, "type": "protocol", "path": proto_uri}

    # 3. Dynamic Catalog Lookup (matches 300+ programs, shortcuts and PWAs on user's PC)
    catalog = scan_all_installed_apps()
    
    # Check canonical mapping
    target_key = APP_CANONICAL_KEYS.get(clean_app) or APP_CANONICAL_KEYS.get(app_lower)
    
    matched_path = None
    if target_key and target_key in catalog:
        matched_path = catalog[target_key]
    elif clean_app in catalog:
        matched_path = catalog[clean_app]
    elif app_lower in catalog:
        matched_path = catalog[app_lower]

    # Substring / fuzzy search in catalog
    if not matched_path:
        no_space = re.sub(r'[^a-z0-9а-яё]', '', clean_app or app_lower)
        for cat_k, cat_p in catalog.items():
            cat_norm = re.sub(r'[^a-z0-9а-яё]', '', cat_k)
            if target_key and (target_key == cat_k or target_key in cat_k):
                matched_path = cat_p
                break
            if no_space and (no_space == cat_norm or (len(no_space) >= 3 and no_space in cat_norm)):
                matched_path = cat_p
                break

    # 4. Built-in Windows System commands
    system_execs = {
        "calc": "calc.exe", "калькулятор": "calc.exe",
        "notepad": "notepad.exe", "блокнот": "notepad.exe",
        "mspaint": "mspaint.exe", "пейнт": "mspaint.exe",
        "explorer": "explorer.exe", "проводник": "explorer.exe",
        "taskmgr": "taskmgr.exe", "диспетчер": "taskmgr.exe",
        "cmd": "cmd.exe", "powershell": "powershell.exe",
        "chrome": "chrome.exe", "msedge": "msedge.exe"
    }

    if not matched_path:
        for sys_k, sys_exe in system_execs.items():
            if sys_k == clean_app or sys_k == app_lower or (target_key and target_key == sys_k):
                matched_path = sys_exe
                break

    # 5. Execute resolved path using native ShellExecute or open
    if matched_path:
        if universal_open_target(matched_path):
            return {"success": True, "launched": app_name, "type": "executable", "path": matched_path}
        else:
            try:
                if matched_path.endswith('.lnk') and sys.platform == "win32":
                    subprocess.Popen(['explorer.exe', matched_path])
                else:
                    item_dir = os.path.dirname(matched_path) if os.path.isabs(matched_path) else None
                    subprocess.Popen([matched_path], cwd=item_dir)
                return {"success": True, "launched": app_name, "type": "executable", "path": matched_path}
            except Exception as e:
                return {"success": False, "error": f"Ошибка запуска {matched_path}: {e}"}

    # 6. Web Service Fallback (SoundCloud, Spotify, Yandex Music, YouTube, Twitch, etc.)
    # If desktop app is not installed, open the official web app seamlessly without error!
    web_fallback = WEB_SERVICE_FALLBACKS.get(clean_app) or WEB_SERVICE_FALLBACKS.get(target_key or "") or WEB_SERVICE_FALLBACKS.get(app_lower)
    if not web_fallback:
        no_space = re.sub(r'[^a-z0-9а-яё]', '', clean_app)
        web_fallback = WEB_SERVICE_FALLBACKS.get(no_space)

    if web_fallback:
        open_url(web_fallback)
        return {"success": True, "launched": f"{clean_app.title()} (веб-сервис)", "type": "web_service", "url": web_fallback}

    # 7. Direct Website / URL
    if clean_app.startswith('http://') or clean_app.startswith('https://') or clean_app.endswith('.com') or clean_app.endswith('.ru'):
        url = clean_app if clean_app.startswith('http') else f"https://{clean_app}"
        try:
            open_url(url)
            return {"success": True, "launched": url, "type": "url"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": f"Приложение '{app_name}' не найдено на вашем компьютере"}

# ─── IN-APP AUTOMATION: TYPING, HOTKEYS & KEY PRESSES ───────────
def get_foreground_window_title() -> str:
    """Returns the title of the current foreground Windows or macOS window."""
    global _LAST_NON_ARGUS_HWND
    if sys.platform == "darwin":
        try:
            script = 'tell application "System Events" to get name of first process whose frontmost is true'
            res = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=2)
            return res.stdout.strip()
        except Exception:
            return ""
    if not _HAS_WIN32GUI:
        return ""
    try:
        hwnd = win32gui.GetForegroundWindow()
        t = win32gui.GetWindowText(hwnd) or ""
        if t:
            tl = t.lower()
            if not any(k in tl for k in ["argus", "vite", "electron"]):
                _LAST_NON_ARGUS_HWND = hwnd
        return t
    except Exception:
        return ""

def focus_input_in_active_window(field_hint: Optional[str] = None):
    """
    Intelligently focuses the target text field or address bar in external apps and browsers.
    Supports Windows and macOS with native AppleScript fallbacks.
    """
    title = get_foreground_window_title().lower()
    hint = (field_hint or "").lower()
    is_mac = sys.platform == "darwin"
    mod_key = 'command' if is_mac else 'ctrl'

    if is_mac:
        try:
            if any(b in title for b in ["chrome", "edge", "yandex", "firefox", "opera", "brave", "safari"]) or any(k in hint for k in ["поиск", "search", "сайт", "url", "строк", "адрес"]):
                if any(k in hint for k in ["внутри", "страниц", "page", "inpage"]):
                    subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "/"'], capture_output=True)
                else:
                    subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "l" using {command down}'], capture_output=True)
                return
            elif any(m in title for m in ["telegram", "телеграм", "discord", "дискорд", "slack"]):
                if any(k in hint for k in ["поиск", "search", "чат", "chat", "контакт", "contact"]):
                    subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 53'], capture_output=True)
                    time.sleep(0.05)
                    subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "k" using {command down}'], capture_output=True)
                else:
                    subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 53'], capture_output=True)
                return
        except Exception:
            pass

    if not _HAS_PYAUTOGUI:
        return

    # Browser search bar / address bar
    if any(b in title for b in ["chrome", "edge", "yandex", "firefox", "opera", "brave", "safari"]) or any(k in hint for k in ["поиск", "search", "сайт", "url", "строк", "адрес"]):
        if any(k in hint for k in ["внутри", "страниц", "page", "inpage"]):
            pyautogui.press('/')
            time.sleep(0.08)
        else:
            pyautogui.hotkey(mod_key, 'l')
            time.sleep(0.08)
    elif any(m in title for m in ["telegram", "телеграм", "discord", "дискорд", "slack"]):
        if any(k in hint for k in ["поиск", "search", "чат", "chat", "контакт", "contact"]):
            pyautogui.press('esc')
            time.sleep(0.05)
            pyautogui.hotkey(mod_key, 'k')
            time.sleep(0.12)
        else:
            pyautogui.press('esc')
            time.sleep(0.05)

def type_text(text: str, target_app: Optional[str] = None, field: Optional[str] = None) -> bool:
    """
    Types arbitrary Unicode text (Russian, English, symbols) into active window or specified target application
    using clipboard + paste to avoid layout desynchronization.
    If target_app is omitted and Argus is foreground, automatically restores the previous active app.
    Supports Windows and macOS with native fallbacks.
    """
    global _LAST_NON_ARGUS_HWND
    is_mac = sys.platform == "darwin"
    mod_key = 'command' if is_mac else 'ctrl'

    # Check if a dictation target window was captured when Double-Ctrl was pressed
    dictation_target = None
    try:
        try:
            import backend.voice_dictation_hook as voice_dictation_hook
        except ImportError:
            import voice_dictation_hook
        dictation_target = voice_dictation_hook.get_last_dictation_target()
    except Exception:
        pass

    if target_app:
        if not activate_running_window(target_app):
            launch_application(target_app)
            time.sleep(1.3)
        else:
            time.sleep(0.35)
    else:
        # Check if we should restore focus to the window where dictation was triggered
        curr_title = get_foreground_window_title().lower()
        if is_mac:
            target_app_name = dictation_target.get("app") if dictation_target else None
            if target_app_name:
                subprocess.run(["osascript", "-e", f'tell application "{target_app_name}" to activate'], capture_output=True, timeout=2)
                time.sleep(0.15)
        else:
            target_hwnd = (dictation_target.get("hwnd") if dictation_target else None) or _LAST_NON_ARGUS_HWND
            if any(k in curr_title for k in ["argus", "vite", "electron"]) or not curr_title:
                if target_hwnd and _HAS_WIN32GUI and win32gui.IsWindow(target_hwnd):
                    force_foreground_window(target_hwnd)
                    time.sleep(0.15)
                elif _HAS_PYAUTOGUI:
                    pyautogui.hotkey('alt', 'tab')
                    time.sleep(0.2)

    if field:
        focus_input_in_active_window(field)
        time.sleep(0.12)

    # 1. Copy text to clipboard
    copied = False
    if is_mac:
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(input=text.encode("utf-8"), timeout=2)
            copied = True
        except Exception:
            pass
        if not copied and _HAS_PYPERCLIP:
            pyperclip.copy(text)
            copied = True
    else:
        if _HAS_PYPERCLIP:
            try:
                pyperclip.copy(text)
                copied = True
            except Exception:
                pass
        # Native Windows ctypes clipboard fallback
        if not copied:
            try:
                CF_UNICODETEXT = 13
                GMEM_MOVEABLE = 0x0002
                u32 = ctypes.windll.user32
                k32 = ctypes.windll.kernel32
                if u32.OpenClipboard(0):
                    u32.EmptyClipboard()
                    encoded = text.encode('utf-16le') + b'\x00\x00'
                    hGlobal = k32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
                    pGlobal = k32.GlobalLock(hGlobal)
                    ctypes.memmove(pGlobal, encoded, len(encoded))
                    k32.GlobalUnlock(hGlobal)
                    u32.SetClipboardData(CF_UNICODETEXT, hGlobal)
                    u32.CloseClipboard()
                    copied = True
            except Exception:
                pass

    time.sleep(0.08)

    # 2. Paste text into focused input
    if is_mac:
        try:
            script = 'tell application "System Events" to keystroke "v" using {command down}'
            res = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2)
            if res.returncode == 0:
                return True
        except Exception:
            pass
        if _HAS_PYAUTOGUI:
            pyautogui.hotkey('command', 'v')
            return True
        return False

    # Windows paste: synthesize Ctrl+V using user32 keybd_event & pyautogui
    try:
        u32 = ctypes.windll.user32
        VK_CONTROL = 0x11
        VK_V = 0x56
        u32.keybd_event(VK_CONTROL, 0, 0, 0)
        u32.keybd_event(VK_V, 0, 0, 0)
        time.sleep(0.03)
        u32.keybd_event(VK_V, 0, 2, 0)
        u32.keybd_event(VK_CONTROL, 0, 2, 0)
        return True
    except Exception:
        if _HAS_PYAUTOGUI:
            pyautogui.hotkey('ctrl', 'v')
            return True
    return False

def press_key(key_name: str) -> bool:
    """Presses a single keyboard key (Enter, Esc, Tab, Space, Backspace, etc.)."""
    key_lower = key_name.lower().strip()
    if sys.platform == "darwin":
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
        if key_lower in mac_keycodes:
            code = mac_keycodes[key_lower]
            try:
                subprocess.run(["osascript", "-e", f'tell application "System Events" to key code {code}'], capture_output=True, timeout=2)
                return True
            except Exception:
                pass
        else:
            try:
                subprocess.run(["osascript", "-e", f'tell application "System Events" to keystroke "{key_name}"'], capture_output=True, timeout=2)
                return True
            except Exception:
                pass

    if not _HAS_PYAUTOGUI:
        return False
    key_map = {
        "enter": "enter", "ввод": "enter", "ентр": "enter",
        "esc": "escape", "escape": "escape", "эскейп": "escape",
        "tab": "tab", "таб": "tab",
        "space": "space", "пробел": "space",
        "backspace": "backspace", "бэкспейс": "backspace", "стереть": "backspace",
        "delete": "delete", "делит": "delete",
        "up": "up", "вверх": "up",
        "down": "down", "вниз": "down",
        "left": "left", "влево": "left",
        "right": "right", "вправо": "right"
    }
    k = key_map.get(key_lower, key_lower)
    try:
        pyautogui.press(k)
        return True
    except Exception as e:
        print("press_key error:", e)
        return False

def send_hotkey(*keys: str) -> bool:
    """
    Sends keyboard shortcut with automatic cross-platform adaptation
    (e.g. maps 'ctrl' -> 'command' on macOS, and 'cmd' -> 'ctrl' on Windows).
    """
    if sys.platform == "darwin":
        try:
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
                res = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2)
                if res.returncode == 0:
                    return True
        except Exception:
            pass

    if not _HAS_PYAUTOGUI:
        return False
    try:
        is_mac = sys.platform == "darwin"
        adapted = []
        for k in keys:
            kl = k.lower().strip()
            if is_mac:
                if kl in ["ctrl", "control"]:
                    adapted.append("command")
                elif kl in ["win", "windows"]:
                    adapted.append("command")
                else:
                    adapted.append(kl)
            else:
                if kl in ["cmd", "command"]:
                    adapted.append("ctrl")
                else:
                    adapted.append(kl)
        pyautogui.hotkey(*adapted)
        return True
    except Exception as e:
        print("send_hotkey error:", e)
        return False

def click_mouse(x: Optional[int] = None, y: Optional[int] = None) -> bool:
    """Clicks the mouse at current or specified coordinate."""
    if not _HAS_PYAUTOGUI:
        return False
    try:
        if x is not None and y is not None:
            pyautogui.click(x, y)
        else:
            pyautogui.click()
        return True
    except Exception as e:
        print("click_mouse error:", e)
        return False

# ─── CLOSE APPLICATION / KILL PROCESS ───────────────────────────
def close_application(app_name: str) -> Dict[str, Any]:
    """Close running Windows or macOS applications by process name."""
    app_lower = app_name.lower().strip()
    
    if sys.platform == "darwin":
        mac_close_map = {
            "telegram": "Telegram", "телеграм": "Telegram", "телега": "Telegram", "тг": "Telegram", "телеграмм": "Telegram",
            "chrome": "Google Chrome", "хром": "Google Chrome", "google chrome": "Google Chrome",
            "safari": "Safari", "сафари": "Safari", "браузер": "Safari",
            "discord": "Discord", "дискорд": "Discord",
            "spotify": "Spotify", "спотифай": "Spotify",
            "steam": "Steam", "стим": "Steam",
            "vscode": "Visual Studio Code", "код": "Visual Studio Code", "vs code": "Visual Studio Code", "code": "Visual Studio Code",
            "calculator": "Calculator", "калькулятор": "Calculator",
            "notes": "Notes", "заметки": "Notes", "блокнот": "TextEdit", "textedit": "TextEdit",
            "terminal": "Terminal", "терминал": "Terminal",
            "activity monitor": "Activity Monitor", "диспетчер задач": "Activity Monitor", "мониторинг системы": "Activity Monitor", "taskmgr": "Activity Monitor", "taskmgr.exe": "Activity Monitor",
            "music": "Music", "музыка": "Music",
            "finder": "Finder", "explorer": "Finder", "explorer.exe": "Finder"
        }
        target_mac = mac_close_map.get(app_lower, app_name)
        closed = False
        try:
            res = subprocess.run(["osascript", "-e", f'tell application "{target_mac}" to quit'], capture_output=True, timeout=3)
            if res.returncode == 0:
                closed = True
        except Exception:
            pass
        try:
            res_pk = subprocess.run(["pkill", "-f", target_mac], capture_output=True, timeout=2)
            if res_pk.returncode == 0:
                closed = True
        except Exception:
            pass
        return {"success": closed, "killed_count": 1 if closed else 0, "app": target_mac}

    if not app_name or not app_lower or len(app_lower) < 2:
        return {"success": False, "error": "Не указано приложение для закрытия"}

    # If generic "приложение" or "окно", close the active foreground window only!
    if app_lower in ["приложение", "программу", "софт", "окно", "active_window"]:
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "w" using {command down}'], capture_output=True)
        else:
            if _HAS_PYAUTOGUI:
                pyautogui.hotkey('alt', 'f4')
        return {"success": True, "app": "active_window", "action": "close_active_window"}

    target_procs = {
        "telegram": ["telegram.exe"],
        "телеграм": ["telegram.exe"],
        "телега": ["telegram.exe"],
        "discord": ["discord.exe"],
        "дискорд": ["discord.exe"],
        "chrome": ["chrome.exe"],
        "хром": ["chrome.exe"],
        "браузер": ["chrome.exe", "msedge.exe", "browser.exe"],
        "steam": ["steam.exe"],
        "стим": ["steam.exe"],
        "spotify": ["spotify.exe"],
        "спотифай": ["spotify.exe"],
        "vscode": ["code.exe"],
        "код": ["code.exe"],
        "calculator": ["calculatorapp.exe", "calc.exe", "calculator.exe"],
        "калькулятор": ["calculatorapp.exe", "calc.exe", "calculator.exe"],
        "notepad": ["notepad.exe"],
        "блокнот": ["notepad.exe"],
        "paint": ["mspaint.exe"],
        "пейнт": ["mspaint.exe"],
        "диспетчер": ["taskmgr.exe"],
        "task manager": ["taskmgr.exe"],
    }
    
    targets = None
    for key, proc_list in target_procs.items():
        if key == app_lower or f" {key} " in f" {app_lower} ":
            targets = proc_list
            break
            
    if not targets:
        if len(app_lower) >= 3 and app_lower not in ["exe", "app", "com"]:
            targets = [app_lower if app_lower.endswith(".exe") else f"{app_lower}.exe"]
        else:
            return {"success": False, "error": "Некорректное имя приложения"}

    # Strict non-empty target check - never kill everything!
    targets = [t.lower() for t in targets if t and len(t) >= 3 and t.lower() not in ["", ".exe", "exe"]]
    if not targets:
        return {"success": False, "error": "Не найдено приложение для закрытия"}

    killed = 0
    # Method 1: psutil terminate with exact name matching
    for p in psutil.process_iter(['name']):
        try:
            p_name = p.name().lower()
            if any(t == p_name for t in targets):
                p.terminate()
                killed += 1
        except Exception:
            pass

    # Method 2: Windows taskkill for stubborn or UWP apps
    for t in targets:
        try:
            res = subprocess.run(f"taskkill /F /IM {t} /T", shell=True, capture_output=True, timeout=2)
            if res.returncode == 0:
                killed += 1
        except Exception:
            pass

    return {"success": killed > 0, "killed_count": killed, "app": app_name}

def close_all_except(keep_apps: List[str]) -> Dict[str, Any]:
    """Closes all user applications except specified ones."""
    keep_lower = [k.lower().strip() for k in keep_apps]
    apps_pool = [
        ("telegram", ["telegram.exe"]),
        ("discord", ["discord.exe"]),
        ("chrome", ["chrome.exe", "msedge.exe"]),
        ("steam", ["steam.exe"]),
        ("spotify", ["spotify.exe"]),
        ("vscode", ["code.exe"]),
        ("calculator", ["calculatorapp.exe", "calc.exe"]),
        ("notepad", ["notepad.exe"]),
        ("paint", ["mspaint.exe"])
    ]
    closed = []
    for app_id, proc_list in apps_pool:
        # Check if should be kept
        should_keep = any(k in app_id or app_id in k for k in keep_lower)
        if not should_keep:
            res = close_application(app_id)
            if res.get("success"):
                closed.append(app_id.capitalize())
    return {"success": True, "closed": closed, "kept": keep_apps}

# ─── EMPTY RECYCLE BIN ──────────────────────────────────────────
def empty_recycle_bin() -> bool:
    """Silently empty Trash / Recycle Bin."""
    if sys.platform == "darwin":
        try:
            subprocess.run(["osascript", "-e", 'tell application "Finder" to empty trash'], check=False)
            return True
        except Exception as e:
            print("Mac trash error:", e)
            return False
    try:
        flags = 0x00000001 | 0x00000002 | 0x00000004
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        return res == 0
    except Exception as e:
        print("Recycle bin error:", e)
        return False

# ─── FOLDER OPENING ─────────────────────────────────────────────
def open_folder(folder_name: str) -> bool:
    """Open standard user folder."""
    user_home = os.path.expanduser("~")
    folder_map = {
        "downloads": os.path.join(user_home, "Downloads"),
        "загрузки": os.path.join(user_home, "Downloads"),
        "desktop": os.path.join(user_home, "Desktop"),
        "рабочий стол": os.path.join(user_home, "Desktop"),
        "documents": os.path.join(user_home, "Documents"),
        "документы": os.path.join(user_home, "Documents"),
        "pictures": os.path.join(user_home, "Pictures"),
        "изображения": os.path.join(user_home, "Pictures"),
        "music": os.path.join(user_home, "Music"),
        "музыка": os.path.join(user_home, "Music"),
        "c": "C:\\" if sys.platform == "win32" else "/",
        "диск c": "C:\\" if sys.platform == "win32" else "/"
    }
    target = folder_map.get(folder_name.lower().strip())
    if target and os.path.exists(target):
        if sys.platform == "darwin":
            subprocess.Popen(["open", target])
            return True
        elif sys.platform == "win32":
            os.startfile(target)
            return True
        else:
            subprocess.Popen(["xdg-open", target])
            return True
    return False

# ─── MEDIA PLAYBACK & MUSIC SERVICES ────────────────────────────
def media_control(action: str) -> bool:
    """Control system media playback with cross-platform support."""
    action = action.lower()
    if sys.platform == "darwin":
        if any(k in action for k in ["stop", "стоп", "pause", "пауз", "выключи", "останови", "выруби"]):
            script = '''
            if application "Spotify" is running then
                tell application "Spotify" to pause
            else if application "Music" is running then
                tell application "Music" to pause
            end if
            '''
            try:
                subprocess.run(["osascript", "-e", script], check=False)
                return True
            except Exception:
                return False
        elif any(k in action for k in ["play", "воспроизве", "продолжи", "играй"]):
            script = '''
            if application "Spotify" is running then
                tell application "Spotify" to play
            else if application "Music" is running then
                tell application "Music" to play
            end if
            '''
            try:
                subprocess.run(["osascript", "-e", script], check=False)
                return True
            except Exception:
                return False
        elif any(k in action for k in ["next", "след", "скип"]):
            script = '''
            if application "Spotify" is running then
                tell application "Spotify" to next track
            else if application "Music" is running then
                tell application "Music" to next track
            end if
            '''
            try:
                subprocess.run(["osascript", "-e", script], check=False)
                return True
            except Exception:
                return False
        elif any(k in action for k in ["prev", "пред", "back", "назад"]):
            script = '''
            if application "Spotify" is running then
                tell application "Spotify" to previous track
            else if application "Music" is running then
                tell application "Music" to previous track
            end if
            '''
            try:
                subprocess.run(["osascript", "-e", script], check=False)
                return True
            except Exception:
                return False
        return False

    if any(k in action for k in ["stop", "стоп"]):
        _press_key(VK_MEDIA_STOP)
        _press_key(VK_MEDIA_PLAY_PAUSE)
    elif any(k in action for k in ["play", "pause", "пауз", "воспроизве", "выключи", "останови", "продолжи", "играй"]):
        _press_key(VK_MEDIA_PLAY_PAUSE)
    elif any(k in action for k in ["next", "след", "скип"]):
        _press_key(VK_MEDIA_NEXT_TRACK)
    elif any(k in action for k in ["prev", "пред", "back", "назад"]):
        _press_key(VK_MEDIA_PREV_TRACK)
    else:
        return False
    return True

def play_music(service: str = "auto", query: str = "", playlist: str = "", action: str = "play") -> Dict[str, Any]:
    """
    Universal music controller with deep support for:
    - Spotify (Спотифай)
    - Yandex Music (Яндекс Музыка)
    - SoundCloud (Саундклауд)
    - VK Music (ВК Музыка)
    - YouTube Music (Ютуб Музыка)
    Handles play, pause, stop, next/prev track, search by song/artist, and playlists.
    """
    action = action.lower().strip()
    service = (service or "auto").lower().strip()
    query = (query or "").strip()
    playlist = (playlist or "").strip()

    # 1. Action: Pause / Stop / Turn off
    if any(k in action for k in ["pause", "stop", "пауз", "выключи", "стоп", "останови", "выруби"]):
        media_control("stop")
        return {
            "success": True,
            "action": "pause",
            "message": "Музыка поставлена на паузу."
        }

    # 2. Action: Next track
    if any(k in action for k in ["next", "след", "скип"]):
        media_control("next")
        return {
            "success": True,
            "action": "next",
            "message": "Включен следующий трек."
        }

    # 3. Action: Previous track
    if any(k in action for k in ["prev", "пред", "назад"]):
        media_control("prev")
        return {
            "success": True,
            "action": "prev",
            "message": "Включен предыдущий трек."
        }

    # 4. Action: Resume without query/playlist
    if not query and not playlist and any(k in action for k in ["resume", "возобнови", "продолжи", "сними с паузы"]):
        media_control("play")
        return {
            "success": True,
            "action": "resume",
            "message": "Воспроизведение музыки продолжено."
        }

    # 5. Determine Target Music Platform
    if any(k in service for k in ["спотифай", "spotify"]):
        target_service = "spotify"
        service_label = "Spotify"
    elif any(k in service for k in ["яндекс", "yandex", "я.музыка", "ямузыка"]):
        target_service = "yandex"
        service_label = "Яндекс Музыке"
    elif any(k in service for k in ["саундклауд", "саунд", "soundcloud"]):
        target_service = "soundcloud"
        service_label = "SoundCloud"
    elif any(k in service for k in ["вк", "vk"]):
        target_service = "vk"
        service_label = "VK Музыке"
    elif any(k in service for k in ["ютуб", "youtube", "yt"]):
        target_service = "youtube"
        service_label = "YouTube Music"
    else:
        # Auto service resolution: check if Spotify desktop app is running
        spotify_running = False
        try:
            for p in psutil.process_iter(['name']):
                if "spotify" in (p.name() or "").lower():
                    spotify_running = True
                    break
        except Exception:
            pass

        if spotify_running:
            target_service = "spotify"
            service_label = "Spotify"
        else:
            target_service = "yandex"
            service_label = "Яндекс Музыке"

    target_url = ""
    app_to_launch = ""
    encoded_search = urllib.parse.quote_plus(playlist or query)

    if target_service == "spotify":
        app_to_launch = "spotify"
        if playlist:
            target_url = f"https://open.spotify.com/search/{encoded_search}/playlists"
        elif query:
            target_url = f"https://open.spotify.com/search/{encoded_search}"
        else:
            target_url = "https://open.spotify.com"

    elif target_service == "yandex":
        if playlist:
            target_url = f"https://music.yandex.ru/search?text={encoded_search}&type=playlists"
        elif query:
            target_url = f"https://music.yandex.ru/search?text={encoded_search}"
        else:
            target_url = "https://music.yandex.ru"

    elif target_service == "soundcloud":
        if playlist:
            target_url = f"https://soundcloud.com/search/sets?q={encoded_search}"
        elif query:
            target_url = f"https://soundcloud.com/search?q={encoded_search}"
        else:
            target_url = "https://soundcloud.com"

    elif target_service == "vk":
        if playlist or query:
            target_url = f"https://vk.com/audio"
        else:
            target_url = "https://vk.com/music"

    elif target_service == "youtube":
        if playlist:
            target_url = f"https://music.youtube.com/search?q={encoded_search}"
        elif query:
            target_url = f"https://music.youtube.com/search?q={encoded_search}"
        else:
            target_url = "https://music.youtube.com"

    # Launch desktop app if available (for generic play without query) or open target URL
    desktop_launched = False
    if app_to_launch and not playlist and not query:
        res = launch_application(app_to_launch)
        if res.get("success"):
            desktop_launched = True
            time.sleep(0.8)
            _press_key(VK_MEDIA_PLAY_PAUSE)

    if not desktop_launched and target_url:
        open_url(target_url)

    if playlist:
        resp_msg = f"Открыт плейлист «{playlist}» в {service_label}."
    elif query:
        resp_msg = f"Включен поиск и воспроизведение «{query}» в {service_label}."
    else:
        resp_msg = f"Запущена музыка в {service_label}."

    return {
        "success": True,
        "service": target_service,
        "query": query,
        "playlist": playlist,
        "action": action,
        "url": target_url,
        "message": resp_msg
    }

# ─── POWER & WORKSTATION ────────────────────────────────────────
def lock_workstation() -> bool:
    """Lock the computer (cross-platform)."""
    if sys.platform == "darwin":
        try:
            subprocess.run(["pmset", "displaysleepnow"], check=False)
            return True
        except Exception:
            return False
    try:
        ctypes.windll.user32.LockWorkStation()
        return True
    except Exception:
        return False

def system_power(action: str) -> bool:
    """Manage system power states (cross-platform)."""
    action = action.lower()
    if sys.platform == "darwin":
        if "reboot" in action or "restart" in action or "перезагруз" in action:
            subprocess.Popen(["osascript", "-e", 'tell application "System Events" to restart'])
            return True
        elif "shutdown" in action or "выключ" in action or "отключ" in action:
            subprocess.Popen(["osascript", "-e", 'tell application "System Events" to shut down'])
            return True
        elif "sleep" in action or "сон" in action or "спящ" in action:
            subprocess.Popen(["pmset", "sleepnow"])
            return True
        return False

    if "reboot" in action or "restart" in action or "перезагруз" in action:
        subprocess.Popen("shutdown /r /t 5", shell=True)
        return True
    elif "shutdown" in action or "выключ" in action or "отключ" in action:
        subprocess.Popen("shutdown /s /t 10", shell=True)
        return True
    elif "cancel" in action or "отмен" in action:
        subprocess.Popen("shutdown /a", shell=True)
        return True
    elif "sleep" in action or "сон" in action or "спящ" in action:
        subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return True
    return False

def get_user_settings() -> Dict[str, Any]:
    try:
        import backend.app_paths as app_paths
        settings_file = app_paths.get_data_file_path("user_settings.json")
    except Exception:
        settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_settings.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def open_url(url: str, browser: Optional[str] = None) -> bool:
    """Open website in user-selected default browser or system default."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    target_browser = browser
    if not target_browser:
        settings = get_user_settings()
        target_browser = settings.get("default_browser", "auto")

    if target_browser and target_browser != "auto":
        browsers = detect_installed_browsers()
        matched = next((b for b in browsers if b["id"].lower() == target_browser.lower() or b["name"].lower() == target_browser.lower()), None)
        if matched and os.path.exists(matched.get("path", "")):
            if sys.platform == "darwin":
                try:
                    subprocess.Popen(["open", "-a", matched["path"], url])
                    return True
                except Exception:
                    pass
            else:
                try:
                    subprocess.Popen([matched["path"], url])
                    return True
                except Exception:
                    pass

    # Fallback to default
    if sys.platform == "darwin":
        try:
            subprocess.Popen(["open", url])
            return True
        except Exception:
            pass
    webbrowser.open(url)
    return True

# ─── HARDWARE TELEMETRY ─────────────────────────────────────────
def get_system_stats() -> Dict[str, Any]:
    """Retrieve full system hardware health and metrics across Windows, macOS, and Linux."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_freq = psutil.cpu_freq()
    vm = psutil.virtual_memory()

    # Precise cross-platform disk usage detection
    disk_stats = None
    if sys.platform == "darwin":
        # macOS APFS architecture: user data & storage reside at /System/Volumes/Data or ~.
        # Root '/' is a sealed read-only snapshot that reports distorted or 0 GB free metrics.
        for cand in ["/System/Volumes/Data", os.path.expanduser("~"), "/"]:
            if os.path.exists(cand):
                try:
                    usage = shutil.disk_usage(cand)
                    if usage.total > 0:
                        used = usage.total - usage.free
                        pct = round((used / usage.total) * 100, 1)
                        disk_stats = {
                            "total_gb": round(usage.total / (1024**3), 1),
                            "used_gb": round(used / (1024**3), 1),
                            "free_gb": round(usage.free / (1024**3), 1),
                            "percent": pct
                        }
                        break
                except Exception:
                    continue
    elif sys.platform == "win32":
        try:
            usage = shutil.disk_usage("C:\\")
            used = usage.total - usage.free
            pct = round((used / usage.total) * 100, 1) if usage.total > 0 else 0.0
            disk_stats = {
                "total_gb": round(usage.total / (1024**3), 1),
                "used_gb": round(used / (1024**3), 1),
                "free_gb": round(usage.free / (1024**3), 1),
                "percent": pct
            }
        except Exception:
            pass

    if not disk_stats:
        try:
            d = psutil.disk_usage(os.path.expanduser("~") if sys.platform == "darwin" else ("C:\\" if sys.platform == "win32" else "/"))
            disk_stats = {
                "total_gb": round(d.total / (1024**3), 1),
                "used_gb": round(d.used / (1024**3), 1),
                "free_gb": round(d.free / (1024**3), 1),
                "percent": d.percent
            }
        except Exception:
            disk_stats = {"total_gb": 0.0, "used_gb": 0.0, "free_gb": 0.0, "percent": 0.0}

    battery = psutil.sensors_battery()
    battery_info = None
    if battery:
        battery_info = {
            "percent": int(battery.percent),
            "power_plugged": battery.power_plugged,
            "secsleft": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
        }

    # Enhanced CPU model detection (e.g. Apple Silicon M1/M2/M3 on Mac)
    cpu_model = ""
    if sys.platform == "darwin":
        try:
            cpu_model = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            cpu_model = "Apple Silicon / Intel"
    elif sys.platform == "win32":
        try:
            import platform
            cpu_model = platform.processor() or ""
        except Exception:
            pass

    return {
        "os": "macOS" if sys.platform == "darwin" else ("Windows" if sys.platform == "win32" else "Linux"),
        "disk_label": "Macintosh HD" if sys.platform == "darwin" else ("Диск C:" if sys.platform == "win32" else "Диск (/)"),
        "cpu": {
            "percent": cpu_percent,
            "cores": psutil.cpu_count(logical=True) or 1,
            "freq_mhz": int(cpu_freq.current) if cpu_freq else 0,
            "model": cpu_model
        },
        "memory": {
            "total_gb": round(vm.total / (1024**3), 1),
            "used_gb": round(vm.used / (1024**3), 1),
            "free_gb": round(vm.available / (1024**3), 1),
            "percent": vm.percent
        },
        "disk": disk_stats,
        "battery": battery_info,
        "volume": get_volume(),
        "brightness": get_brightness()
    }

# ─── WINDOW MANAGEMENT ────────────────────────────────────────────
def minimize_application(app_query: str) -> bool:
    """Minimizes/hides a specific target application on Windows or macOS."""
    if not app_query:
        return False
    query = app_query.lower().strip()

    if sys.platform == "darwin":
        # macOS: hide process or miniaturize its windows
        app_disp = query.capitalize()
        if query in ["telegram", "телеграм", "телега", "тг"]:
            app_disp = "Telegram"
        elif query in ["chrome", "хром", "браузер"]:
            app_disp = "Google Chrome"
        elif query in ["discord", "дискорд"]:
            app_disp = "Discord"
        elif query in ["vscode", "код", "vs code"]:
            app_disp = "Visual Studio Code"
        elif query in ["postman", "постман"]:
            app_disp = "Postman"
        
        script = f'''
        tell application "System Events"
            set matchedProcesses to (every application process whose name contains "{app_disp}" or name contains "{query}")
            repeat with p in matchedProcesses
                set visible of p to false
            end repeat
        end tell
        try
            tell application "{app_disp}" to set miniaturized of every window to true
        end try
        '''
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)
            return True
        except Exception as e:
            print("macOS minimize app error:", e)
            return False

    # Windows implementation
    proc_aliases = {
        "telegram": ["telegram.exe"],
        "телеграм": ["telegram.exe"],
        "телега": ["telegram.exe"],
        "тг": ["telegram.exe"],
        "chrome": ["chrome.exe"],
        "хром": ["chrome.exe"],
        "браузер": ["chrome.exe", "msedge.exe", "browser.exe"],
        "discord": ["discord.exe"],
        "дискорд": ["discord.exe"],
        "vscode": ["code.exe"],
        "код": ["code.exe"],
        "vs code": ["code.exe"],
        "postman": ["postman.exe"],
        "постман": ["postman.exe"],
        "notepad": ["notepad.exe"],
        "блокнот": ["notepad.exe"],
        "steam": ["steam.exe"],
        "стим": ["steam.exe"],
        "spotify": ["spotify.exe"],
        "спотифай": ["spotify.exe"]
    }
    target_procs = proc_aliases.get(query, [f"{query}.exe", query])

    try:
        hDesk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x01FF)
        if hDesk:
            ctypes.windll.user32.SetThreadDesktop(hDesk)
    except Exception:
        pass

    found_hwnds = []
    try:
        import win32gui
        import win32process

        def enum_cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    p = psutil.Process(pid)
                    pname = p.name().lower()
                    title = win32gui.GetWindowText(hwnd).lower()
                    if any(tp in pname for tp in target_procs) or (query in title and len(title) > 0):
                        found_hwnds.append(hwnd)
                except Exception:
                    pass

        win32gui.EnumWindows(enum_cb, None)
    except Exception:
        pass

    if found_hwnds:
        for hwnd in found_hwnds:
            try:
                ctypes.windll.user32.ShowWindowAsync(hwnd, 6)  # SW_MINIMIZE = 6
                ctypes.windll.user32.PostMessageW(hwnd, 0x0112, 0xF020, 0)  # WM_SYSCOMMAND, SC_MINIMIZE
            except Exception:
                pass
        return True
    return False

def minimize_current_window() -> bool:
    """Minimizes the currently active/focused window."""
    if sys.platform == "darwin":
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                if name of frontApp does not contain "Argus" then
                    set visible of frontApp to false
                else
                    set frontProcesses to every application process whose visible is true and name does not contain "Argus" and name is not "Finder"
                    if (count of frontProcesses) > 0 then
                        set visible of (item 1 of frontProcesses) to false
                    end if
                end if
            end tell
            '''
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2)
            return True
        except Exception:
            pass
        return False

    # Windows implementation
    try:
        hDesk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x01FF)
        if hDesk:
            ctypes.windll.user32.SetThreadDesktop(hDesk)

        hwnd = ctypes.windll.user32.GetForegroundWindow()
        argus_pid = os.getpid()
        from ctypes import wintypes
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        # If active window is Argus itself, minimize the top non-Argus visible window
        if pid.value == argus_pid or pid.value == 0:
            target_hwnd = [None]
            def cb(h, _):
                if ctypes.windll.user32.IsWindowVisible(h):
                    p = wintypes.DWORD()
                    ctypes.windll.user32.GetWindowThreadProcessId(h, ctypes.byref(p))
                    if p.value != argus_pid and p.value != 0:
                        length = ctypes.windll.user32.GetWindowTextLengthW(h)
                        if length > 0:
                            target_hwnd[0] = h
                            return False
                return True
            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            ctypes.windll.user32.EnumWindows(WNDENUMPROC(cb), 0)
            if target_hwnd[0]:
                hwnd = target_hwnd[0]

        if hwnd:
            ctypes.windll.user32.ShowWindowAsync(hwnd, 6)  # SW_MINIMIZE = 6
            ctypes.windll.user32.PostMessageW(hwnd, 0x0112, 0xF020, 0)
            return True
    except Exception as e:
        print("minimize_current_window error:", e)
    return False

def minimize_all_windows() -> bool:
    """Minimizes all windows and reveals the desktop on Windows and macOS."""
    if sys.platform == "darwin":
        try:
            # Hide all visible applications on macOS (shows clean desktop)
            script = '''
            tell application "System Events"
                set visible of every process whose visible is true and name is not "Finder" to false
            end tell
            '''
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2)
            return True
        except Exception:
            pass
        return False

    # Windows implementation: Shell COM MinimizeAll is 100% reliable
    try:
        import win32com.client
        shell = win32com.client.Dispatch("Shell.Application")
        shell.MinimizeAll()
        return True
    except Exception:
        pass

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(New-Object -ComObject Shell.Application).MinimizeAll()"],
            capture_output=True,
            timeout=2
        )
        return True
    except Exception:
        pass

    try:
        # Win+M keybd_event synthesis via ctypes
        ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x4D, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0x4D, 0, 2, 0)
        ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)
        return True
    except Exception:
        pass

    return False

# ─── BROWSER & YOUTUBE DEEP INTERACTION ────────────────────────────
def is_argus_window(hwnd) -> bool:
    """Checks if given Win32 HWND belongs to Argus AI application."""
    if not _HAS_WIN32GUI or not hwnd:
        return False
    try:
        import win32gui
        import win32process
        title = win32gui.GetWindowText(hwnd).lower()
        if "argus" in title:
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid == os.getpid():
            return True
        try:
            p = psutil.Process(pid)
            pname = p.name().lower()
            if "argus" in pname or "electron" in pname:
                return True
        except Exception:
            pass
    except Exception:
        pass
    return False

def is_argus_foreground() -> bool:
    """Checks if current foreground window belongs to Argus AI."""
    if sys.platform == "darwin":
        try:
            script = 'tell application "System Events" to get name of first application process whose frontmost is true'
            res = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2, text=True)
            front_app = res.stdout.strip().lower()
            if "argus" in front_app or "electron" in front_app:
                return True
        except Exception:
            pass
        return False

    if not _HAS_WIN32GUI:
        return False
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd:
            return is_argus_window(hwnd)
    except Exception:
        pass
    return False

def is_browser_foreground() -> bool:
    """Verifies that the current foreground window is indeed a recognized web browser."""
    browser_names = ["chrome", "edge", "yandex", "brave", "safari", "firefox", "opera", "vivaldi"]
    if sys.platform == "darwin":
        try:
            script = 'tell application "System Events" to get name of first application process whose frontmost is true'
            res = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2, text=True)
            front_app = res.stdout.strip().lower()
            return any(b in front_app for b in browser_names)
        except Exception:
            return False

    if not _HAS_WIN32GUI:
        return False
    try:
        import win32gui
        import win32process
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd or is_argus_window(hwnd):
            return False
        title = win32gui.GetWindowText(hwnd).lower()
        if any(b in title for b in browser_names):
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            p = psutil.Process(pid)
            pname = p.name().lower()
            return any(b in pname for b in browser_names)
        except Exception:
            pass
    except Exception:
        pass
    return False

def activate_browser(browser_preference: Optional[str] = None) -> bool:
    """Brings any running browser (Chrome, Edge, Yandex, Brave, Safari, Firefox, Opera) to the foreground."""
    browsers = ["chrome", "edge", "yandex", "brave", "safari", "firefox", "opera", "browser"]
    if browser_preference:
        browsers.insert(0, browser_preference.lower())

    if sys.platform == "darwin":
        script = '''
        tell application "System Events"
            set runningApps to (every application process whose name is in {"Google Chrome", "Safari", "Brave Browser", "Microsoft Edge", "Firefox", "Opera", "Yandex"})
            if (count of runningApps) > 0 then
                set frontmost of (item 1 of runningApps) to true
                return true
            end if
        end tell
        '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2, text=True)
            if "true" in res.stdout.lower():
                return True
        except Exception:
            pass

    for b in browsers:
        if activate_running_window(b):
            time.sleep(0.12)
            if not is_argus_foreground():
                return True
    return False

def activate_youtube_window() -> bool:
    """Finds and brings any window or tab with 'YouTube' in title to the foreground, or active browser."""
    if sys.platform == "darwin":
        script = '''
        tell application "System Events"
            set isChrome to (count of (every process whose name is "Google Chrome")) > 0
            set isSafari to (count of (every process whose name is "Safari")) > 0
            set isBrave to (count of (every process whose name is "Brave Browser")) > 0
            set isEdge to (count of (every process whose name is "Microsoft Edge")) > 0
        end tell
        if isChrome then
            tell application "Google Chrome"
                repeat with w in windows
                    set idx to 1
                    repeat with t in tabs of w
                        if URL of t contains "youtube.com" then
                            set active tab index of w to idx
                            set index of w to 1
                            activate
                            return true
                        end if
                        set idx to idx + 1
                    end repeat
                end repeat
            end tell
        end if
        if isSafari then
            tell application "Safari"
                repeat with w in windows
                    repeat with t in tabs of w
                        if URL of t contains "youtube.com" then
                            set current tab of w to t
                            set index of w to 1
                            activate
                            return true
                        end if
                    end repeat
                end repeat
            end tell
        end if
        return false
        '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3, text=True)
            if "true" in res.stdout.lower():
                return True
        except Exception:
            pass
        return activate_browser()

    # Windows implementation
    try:
        hDesk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x01FF)
        if hDesk:
            ctypes.windll.user32.SetThreadDesktop(hDesk)
    except Exception:
        pass

    try:
        import win32gui
        found_yt = []
        found_browsers = []
        def cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and not is_argus_window(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                if "youtube" in title:
                    found_yt.append(hwnd)
                elif any(b in title for b in ["chrome", "edge", "yandex", "brave", "firefox", "opera"]):
                    found_browsers.append(hwnd)
        win32gui.EnumWindows(cb, None)
        target = found_yt[0] if found_yt else (found_browsers[0] if found_browsers else None)
        if target:
            ctypes.windll.user32.ShowWindow(target, 9)
            ctypes.windll.user32.SetForegroundWindow(target)
            time.sleep(0.12)
            return True
    except Exception:
        pass
    return activate_browser()

def youtube_control(action: str) -> bool:
    """
    Direct in-browser YouTube control on Windows and macOS:
    - play_pause (k / Space)
    - mute (m)
    - fullscreen (f)
    - next (Shift+N)
    - prev (Shift+P)
    - seek_forward (l / Right)
    - seek_backward (j / Left)
    - speed_up (Shift+>)
    - speed_down (Shift+<)
    - subtitles (c)
    """
    act = action.lower().strip()
    
    if sys.platform == "darwin":
        key_char = "k"
        use_shift = False
        if act in ["play_pause", "pause", "play", "toggle"]:
            key_char = "k"
        elif act in ["mute", "unmute", "sound"]:
            key_char = "m"
        elif act in ["fullscreen", "screen"]:
            key_char = "f"
        elif act in ["next"]:
            key_char = "N"
            use_shift = True
        elif act in ["prev", "previous"]:
            key_char = "P"
            use_shift = True
        elif act in ["seek_forward", "forward"]:
            key_char = "l"
        elif act in ["seek_backward", "backward", "rewind"]:
            key_char = "j"
        elif act in ["subtitles", "captions"]:
            key_char = "c"
        elif act in ["speed_up"]:
            key_char = ">"
            use_shift = True
        elif act in ["speed_down"]:
            key_char = "<"
            use_shift = True

        shift_str = "using {shift down}" if use_shift else ""
        script = f'''
        tell application "Google Chrome"
            repeat with w in windows
                set idx to 1
                repeat with t in tabs of w
                    if URL of t contains "youtube.com" then
                        set active tab index of w to idx
                        set index of w to 1
                        activate
                        tell application "System Events" to keystroke "{key_char.lower()}" {shift_str}
                        return true
                    end if
                    set idx to idx + 1
                end repeat
            end repeat
        end tell
        tell application "Safari"
            repeat with w in windows
                repeat with t in tabs of w
                    if URL of t contains "youtube.com" then
                        set current tab of w to t
                        set index of w to 1
                        activate
                        tell application "System Events" to keystroke "{key_char.lower()}" {shift_str}
                        return true
                    end if
                end repeat
            end repeat
        end tell
        tell application "System Events"
            keystroke "{key_char.lower()}" {shift_str}
        end tell
        '''
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)
            return True
        except Exception as e:
            print("macOS youtube_control error:", e)

    # Windows implementation:
    activate_youtube_window()
    time.sleep(0.12)

    # Absolute safety check: never send player keys to Argus window
    if is_argus_foreground():
        return False

    try:
        if act in ["play_pause", "pause", "play", "toggle"]:
            press_key("k")
        elif act in ["mute", "unmute", "sound"]:
            press_key("m")
        elif act in ["fullscreen", "screen"]:
            press_key("f")
        elif act in ["next"]:
            send_hotkey("shift", "n")
        elif act in ["prev", "previous"]:
            send_hotkey("shift", "p")
        elif act in ["seek_forward", "forward"]:
            press_key("l")
        elif act in ["seek_backward", "backward", "rewind"]:
            press_key("j")
        elif act in ["subtitles", "captions"]:
            press_key("c")
        elif act in ["speed_up"]:
            send_hotkey("shift", ">")
        elif act in ["speed_down"]:
            send_hotkey("shift", "<")
        return True
    except Exception as e:
        print("Windows youtube_control error:", e)
        return False

def close_specific_browser_tab(target_query: str) -> bool:
    """
    Finds and closes browser tab matching a website name or URL (e.g. 'youtube', 'vk', 'yandex').
    Works across Google Chrome, Safari, Brave, Edge on Windows and macOS.
    """
    if not target_query:
        activate_browser()
        return close_browser_tab()
    q = target_query.lower().strip()
    
    target_domains = {
        "дипсик": "deepseek", "дипсика": "deepseek", "дипсике": "deepseek", "дипсиком": "deepseek", "deepseek": "deepseek",
        "чатгпт": "chatgpt", "чат гпт": "chatgpt", "chatgpt": "chatgpt", "openai": "openai",
        "гугл": "google", "гугле": "google", "google": "google",
        "яндекс": "yandex", "яндексе": "yandex", "yandex": "yandex",
        "википедия": "wikipedia", "википедии": "wikipedia", "вики": "wikipedia", "wikipedia": "wikipedia",
        "стак": "stackoverflow", "стаковерфлоу": "stackoverflow", "stackoverflow": "stackoverflow",
        "хабр": "habr", "хабре": "habr", "habr": "habr",
        "кинопоиск": "kinopoisk", "кинопоиске": "kinopoisk", "kinopoisk": "kinopoisk",
        "ношен": "notion", "ноушен": "notion", "notion": "notion",
        "фигма": "figma", "фигме": "figma", "figma": "figma",
        "клауд": "claude", "клод": "claude", "claude": "claude",
        "реддит": "reddit", "редит": "reddit", "reddit": "reddit",
        "стим": "steam", "steam": "steam",
        "нетфликс": "netflix", "netflix": "netflix",
        "спотифай": "spotify", "spotify": "spotify",
        "авито": "avito", "avito": "avito",
        "госуслуги": "gosuslugi",
        "тинькофф": "tinkoff", "тбанк": "tbank", "tbank": "tbank", "tinkoff": "tinkoff",
        "сбер": "sber", "сбербанк": "sberbank", "sber": "sber",
        "ютуб": "youtube", "ютубе": "youtube", "ютуби": "youtube", "youtube": "youtube",
        "вк": "vk", "вконтакте": "vk", "vk": "vk",
        "телеграм": "telegram", "телега": "telegram", "тг": "telegram",
        "гитхаб": "github", "github": "github",
        "почта": "mail", "почту": "mail", "mail": "mail", "gmail": "gmail",
        "озон": "ozon", "ozon": "ozon",
        "вайлдберриз": "wildberries", "вайлдбериз": "wildberries", "вб": "wildberries", "wildberries": "wildberries",
        "дискорд": "discord", "discord": "discord"
    }
    match_term = target_domains.get(q, q)
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
        'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
        'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts',
        'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
    }
    translit_q = "".join(translit_map.get(ch, ch) for ch in q)
    search_tokens = [tok for tok in [q, match_term, translit_q] if len(tok) >= 2]

    if sys.platform == "darwin":
        script = f'''
        set foundTab to false
        tell application "System Events"
            set isChromeRunning to (count of (every process whose name is "Google Chrome")) > 0
            set isSafariRunning to (count of (every process whose name is "Safari")) > 0
            set isBraveRunning to (count of (every process whose name is "Brave Browser")) > 0
            set isEdgeRunning to (count of (every process whose name is "Microsoft Edge")) > 0
        end tell
        if isChromeRunning then
            tell application "Google Chrome"
                repeat with w in windows
                    repeat with t in (tabs of w as list)
                        if (URL of t contains "{match_term}") or (title of t contains "{q}") or (title of t contains "{match_term}") then
                            close t
                            set foundTab to true
                        end if
                    end repeat
                end repeat
            end tell
        end if
        if isSafariRunning then
            tell application "Safari"
                repeat with w in windows
                    repeat with t in (tabs of w as list)
                        if (URL of t contains "{match_term}") or (name of t contains "{q}") or (name of t contains "{match_term}") then
                            close t
                            set foundTab to true
                        end if
                    end repeat
                end repeat
            end tell
        end if
        return foundTab
        '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3, text=True)
            if "true" in res.stdout.lower():
                return True
        except Exception as e:
            print("macOS close_specific_browser_tab error:", e)

    # Windows:
    try:
        hDesk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x01FF)
        if hDesk:
            ctypes.windll.user32.SetThreadDesktop(hDesk)
        import win32gui
        matched_hwnds = []
        def cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and not is_argus_window(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                if any(tok in title for tok in search_tokens):
                    matched_hwnds.append(hwnd)
        win32gui.EnumWindows(cb, None)
        if matched_hwnds:
            for h in matched_hwnds:
                ctypes.windll.user32.ShowWindow(h, 9)
                ctypes.windll.user32.SetForegroundWindow(h)
                time.sleep(0.12)
                if not is_argus_foreground():
                    send_hotkey("ctrl", "w")
            return True
    except Exception as e:
        print("Windows close_specific_browser_tab error:", e)

    # Safety: If specific tab was not found, DO NOT close arbitrary windows or Argus!
    return False

def close_browser_tab() -> bool:
    """Closes active browser tab (Cmd+W on macOS, Ctrl+W on Windows/Linux). Never closes Argus AI."""
    if is_argus_foreground():
        return False

    if sys.platform == "darwin":
        script = '''
        tell application "System Events"
            set runningBrowsers to (every application process whose name is in {"Google Chrome", "Safari", "Brave Browser", "Microsoft Edge", "Firefox", "Opera", "Yandex"})
            if (count of runningBrowsers) > 0 then
                set frontBrowser to name of (item 1 of runningBrowsers)
                tell application frontBrowser to close active tab of front window
                return true
            end if
        end tell
        '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2, text=True)
            if "true" in res.stdout.lower():
                return True
        except Exception:
            pass

    if activate_browser():
        time.sleep(0.12)
        if is_browser_foreground() and not is_argus_foreground():
            if _HAS_PYAUTOGUI:
                try:
                    pyautogui.hotkey('ctrl', 'w')
                    return True
                except Exception as e:
                    print("close_browser_tab error:", e)
    return False

def close_all_browser_tabs() -> bool:
    """Closes all browser tabs / browser window (Cmd+Shift+W on macOS, Ctrl+Shift+W on Windows/Linux)."""
    if is_argus_foreground():
        return False

    if sys.platform == "darwin":
        script = '''
        tell application "System Events"
            set runningBrowsers to (every application process whose name is in {"Google Chrome", "Safari", "Brave Browser", "Microsoft Edge", "Firefox", "Opera", "Yandex"})
            if (count of runningBrowsers) > 0 then
                set frontBrowser to name of (item 1 of runningBrowsers)
                tell application frontBrowser to close front window
                return true
            end if
        end tell
        '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2, text=True)
            if "true" in res.stdout.lower():
                return True
        except Exception:
            pass

    if activate_browser():
        time.sleep(0.12)
        if is_browser_foreground() and not is_argus_foreground():
            return send_hotkey("ctrl", "shift", "w")
    return False
    if _HAS_PYAUTOGUI:
        try:
            pyautogui.hotkey('ctrl', 'shift', 'w')
            return True
        except Exception as e:
            print("close_all_browser_tabs error:", e)
    return False

def new_browser_tab() -> bool:
    """Opens a new browser tab (Cmd+T on macOS, Ctrl+T on Windows/Linux)."""
    activate_browser()
    time.sleep(0.1)
    if sys.platform == "darwin":
        try:
            script = 'tell application "System Events" to keystroke "t" using {command down}'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2)
            return True
        except Exception:
            pass
    if _HAS_PYAUTOGUI:
        try:
            pyautogui.hotkey('ctrl', 't')
            return True
        except Exception:
            pass
    return False

def reopen_browser_tab() -> bool:
    """Reopens last closed tab (Cmd+Shift+T on macOS, Ctrl+Shift+T on Windows/Linux)."""
    activate_browser()
    time.sleep(0.1)
    return send_hotkey("ctrl", "shift", "t")

def refresh_browser_page() -> bool:
    """Refreshes the current web page (Cmd+R on macOS, F5 / Ctrl+R on Windows/Linux)."""
    activate_browser()
    time.sleep(0.1)
    if sys.platform == "darwin":
        try:
            script = 'tell application "System Events" to keystroke "r" using {command down}'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2)
            return True
        except Exception:
            pass
    if _HAS_PYAUTOGUI:
        try:
            pyautogui.hotkey('ctrl', 'r')
            return True
        except Exception:
            pass
    return False

def switch_browser_tab(direction: str = "next") -> bool:
    """Switches to next or previous browser tab."""
    activate_browser()
    time.sleep(0.1)
    if sys.platform == "darwin":
        try:
            key_char = "{" if direction == "prev" else "}"
            script = f'tell application "System Events" to keystroke "{key_char}" using {{command down, shift down}}'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2)
            return True
        except Exception:
            pass
    if _HAS_PYAUTOGUI:
        try:
            if direction == "prev":
                pyautogui.hotkey('ctrl', 'shift', 'tab')
            else:
                pyautogui.hotkey('ctrl', 'tab')
            return True
        except Exception:
            pass
    return False

def scroll_browser_page(direction: str = "down") -> bool:
    """Scrolls active page up or down."""
    activate_browser()
    time.sleep(0.1)
    if sys.platform == "darwin":
        try:
            code = 121 if direction == "down" else 116
            subprocess.run(["osascript", "-e", f'tell application "System Events" to key code {code}'], capture_output=True, timeout=2)
            return True
        except Exception:
            pass
    if _HAS_PYAUTOGUI:
        try:
            amount = -650 if direction == "down" else 650
            pyautogui.scroll(amount)
            return True
        except Exception:
            pass
    return False

def scroll_browser_to(position: str = "top") -> bool:
    """Scrolls active page to top (Home / Cmd+Up) or bottom (End / Cmd+Down)."""
    activate_browser()
    time.sleep(0.1)
    if sys.platform == "darwin":
        return send_hotkey("cmd", "up") if position == "top" else send_hotkey("cmd", "down")
    else:
        return press_key("home") if position == "top" else press_key("end")

def find_in_browser_page(query: str = "") -> bool:
    """Opens browser search bar (Ctrl+F / Cmd+F) and optionally searches for text."""
    activate_browser()
    time.sleep(0.1)
    ok = send_hotkey("ctrl", "f")
    if query and ok:
        time.sleep(0.15)
        type_text(query)
        time.sleep(0.1)
        press_key("enter")
    return ok

def zoom_browser_page(direction: str = "in") -> bool:
    """Zooms page in (Ctrl++), out (Ctrl+-), or resets (Ctrl+0)."""
    activate_browser()
    time.sleep(0.1)
    if direction == "in":
        return send_hotkey("ctrl", "=") or send_hotkey("ctrl", "+")
    elif direction == "out":
        return send_hotkey("ctrl", "-")
    elif direction in ["reset", "normal"]:
        return send_hotkey("ctrl", "0")
    return False

def navigate_browser_history(direction: str = "back") -> bool:
    """Goes back or forward in browser history (Alt+Left / Alt+Right or Cmd+[ / Cmd+])."""
    activate_browser()
    time.sleep(0.1)
    if sys.platform == "darwin":
        key = "[" if direction == "back" else "]"
        return send_hotkey("cmd", key)
    else:
        arrow = "left" if direction == "back" else "right"
        return send_hotkey("alt", arrow)

def open_browser_feature(feature: str) -> bool:
    """Opens browser history, downloads, bookmarks, or incognito mode."""
    activate_browser()
    time.sleep(0.1)
    feat = feature.lower().strip()
    if feat == "history":
        return send_hotkey("ctrl", "h")
    elif feat == "downloads":
        return send_hotkey("ctrl", "j")
    elif feat == "bookmarks":
        return send_hotkey("ctrl", "d")
    elif feat == "incognito":
        return send_hotkey("ctrl", "shift", "n")
    return False

def click_website_button(button_name: str) -> bool:
    """
    Interacts with active browser page to find and click a button or link by text.
    Brings browser window to front, searches for element text via Cmd+F / Ctrl+F, and activates it.
    """
    if not button_name:
        return False
    try:
        # 1. Bring running browser to front
        browsers = ["safari", "chrome", "edge", "yandex", "opera", "firefox", "brave", "vivaldi"]
        for b_name in browsers:
            if activate_running_window(b_name):
                time.sleep(0.4)
                break

        # 2. Focus browser inline search (Cmd+F on macOS, Ctrl+F on Windows)
        send_hotkey("cmd", "f")
        time.sleep(0.2)

        # 3. Copy and paste button text via clipboard
        clean_btn = button_name.strip()
        type_text(clean_btn)
        time.sleep(0.25)

        # 4. Hit Enter to scroll element into view & highlight
        press_key("enter")
        time.sleep(0.2)

        # 5. Dismiss search box while keeping element active
        press_key("escape")
        time.sleep(0.15)

        # 6. Click/activate the focused button or link
        press_key("enter")
        time.sleep(0.2)
        return True
    except Exception as e:
        print("click_website_button error:", e)
        return False

# ─── CROSS-PLATFORM TERMINAL COMMAND RUNNER ───────────────────────
def detect_system_os() -> str:
    """Returns detected operating system ('windows', 'macos', or 'linux')."""
    if sys.platform.startswith('win'):
        return 'windows'
    elif sys.platform == 'darwin':
        return 'macos'
    elif sys.platform.startswith('linux'):
        return 'linux'
    return 'unknown'

def execute_terminal_command(command: str, shell_type: Optional[str] = None, timeout: int = 30) -> Dict[str, Any]:
    """
    Safely executes terminal commands cross-platform:
    - Windows: PowerShell or CMD
    - macOS: Bash or Zsh
    - Linux: Bash
    Returns stdout, stderr, execution time, and exit code.
    """
    os_name = detect_system_os()
    start_time = time.time()

    # ─── ADVANCED SECURITY GUARD: CATASTROPHIC COMMAND INTERCEPTOR ───
    dangerous_patterns = [
        r"\bformat\s+[a-z]:",
        r"\bformat-volume\b",
        r"\brmdir\s+/[sS]\s+/[qQ]\s+[cC]:\\",
        r"\bdel\s+/[fF]\s+/[sS]\s+/[qQ]\s+[cC]:\\(windows|system32)?",
        r"\brm\s+-(rf|fr|r)\s+(/|/\*|~|\$HOME)",
        r"\bmkfs\b",
        r"\bdd\s+if=.*of=/dev/[sh]d",
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
    ]
    norm_cmd = command.strip().lower()
    for pat in dangerous_patterns:
        if re.search(pat, norm_cmd):
            return {
                "success": False,
                "exit_code": 403,
                "output": "",
                "error": "Команда заблокирована встроенной защитой Argus Guard: обнаружена деструктивная операция.",
                "duration_ms": 0,
                "os": os_name
            }
    
    cmd_args: List[str] = []
    if os_name == "windows":
        chosen_shell = (shell_type or "powershell").lower()
        if chosen_shell == "cmd":
            cmd_args = ["cmd.exe", "/c", command]
        else:
            cmd_args = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
    elif os_name == "macos":
        chosen_shell = (shell_type or "zsh").lower()
        shell_bin = "/bin/zsh" if chosen_shell == "zsh" else "/bin/bash"
        cmd_args = [shell_bin, "-c", command]
    else: # Linux
        cmd_args = ["/bin/bash", "-c", command]

    try:
        proc = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "output": proc.stdout.strip() if proc.stdout else "",
            "error": proc.stderr.strip() if proc.stderr else "",
            "duration_ms": duration_ms,
            "os": os_name
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "exit_code": -1,
            "output": "",
            "error": f"Превышено время ожидания выполнения команды ({timeout}s)",
            "duration_ms": int((time.time() - start_time) * 1000),
            "os": os_name
        }
    except Exception as e:
        return {
            "success": False,
            "exit_code": -1,
            "output": "",
            "error": str(e),
            "duration_ms": int((time.time() - start_time) * 1000),
            "os": os_name
        }

# ─── FILE & FOLDER AUTOMATION ────────────────────────────────────
def resolve_file_path(path_str: str) -> str:
    """Resolves natural language or relative paths to real absolute Windows paths."""
    s = path_str.strip().strip('"\'«»')
    user_home = os.path.expanduser('~')
    desktop = os.path.join(user_home, 'Desktop')
    downloads = os.path.join(user_home, 'Downloads')
    documents = os.path.join(user_home, 'Documents')
    pictures = os.path.join(user_home, 'Pictures')
    videos = os.path.join(user_home, 'Videos')

    s_lower = s.lower()
    if 'рабоч' in s_lower or 'desktop' in s_lower:
        base = desktop
    elif 'загруз' in s_lower or 'download' in s_lower:
        base = downloads
    elif 'документ' in s_lower or 'document' in s_lower:
        base = documents
    elif 'картинк' in s_lower or 'фото' in s_lower or 'picture' in s_lower:
        base = pictures
    elif 'видео' in s_lower or 'video' in s_lower:
        base = videos
    else:
        base = desktop

    # Clean location words and noun prefixes from filename
    clean_name = re.sub(
        r'^(?:desktop/|desktop\\|downloads/|downloads\\|documents/|documents\\|'
        r'папку|папка|папке|папкой|файл|файла|файлу|файлом|'
        r'на\s+рабочем\s+столе|на\s+рабочий\s+стол|в\s+загрузках|в\s+загрузки|'
        r'в\s+документах|в\s+документы|в\s+папке|в\s+папку)\s*',
        '', s, flags=re.IGNORECASE
    ).strip()
    clean_name = re.sub(
        r'\s+(?:на\s+рабочем\s+столе|на\s+рабочий\s+стол|в\s+загрузках|в\s+загрузки|в\s+документах|в\s+документы)$',
        '', clean_name, flags=re.IGNORECASE
    ).strip()

    if os.path.isabs(clean_name):
        return os.path.normpath(clean_name)

    # 1. Primary path in chosen base
    primary_path = os.path.normpath(os.path.join(base, clean_name))
    if os.path.exists(primary_path):
        return primary_path

    # 2. Check other common user folders if primary does not exist (e.g. user created in Documents, then asked to delete without specifying location)
    for alt_base in [documents, downloads, desktop, pictures, videos, user_home]:
        alt_path = os.path.normpath(os.path.join(alt_base, clean_name))
        if os.path.exists(alt_path):
            return alt_path

    return primary_path

_LAST_CREATED_ITEM: Optional[str] = None

def get_last_created_item() -> Optional[str]:
    global _LAST_CREATED_ITEM
    return _LAST_CREATED_ITEM

def set_last_created_item(path: str):
    global _LAST_CREATED_ITEM
    _LAST_CREATED_ITEM = path

def create_file(target: str, content: str = "") -> Dict[str, Any]:
    try:
        path = resolve_file_path(target)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        set_last_created_item(path)
        return {"success": True, "path": path, "name": os.path.basename(path), "size": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def create_folder(target: str) -> Dict[str, Any]:
    try:
        path = resolve_file_path(target)
        os.makedirs(path, exist_ok=True)
        set_last_created_item(path)
        return {"success": True, "path": path, "name": os.path.basename(path)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_file_or_folder(target: str) -> Dict[str, Any]:
    try:
        global _LAST_CREATED_ITEM
        clean_target = (target or "").strip().lower().strip('"\'«»')
        if not clean_target or clean_target in [
            "эту", "эту папку", "это", "ее", "её", "ту", "папку", "папка",
            "файл", "данную папку", "данный файл", "созданную папку", "эту папочку"
        ]:
            if _LAST_CREATED_ITEM and os.path.exists(_LAST_CREATED_ITEM):
                target = _LAST_CREATED_ITEM

        path = resolve_file_path(target)
        norm = os.path.normpath(path).lower()
        if norm in ["c:\\", "c:", "c:\\windows", "c:\\program files", "c:\\users"]:
            return {"success": False, "error": "Запрещено удалять системные директории"}
        if not os.path.exists(path):
            return {"success": False, "error": f"Файл или папка '{os.path.basename(path)}' не найдены"}
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        if _LAST_CREATED_ITEM and os.path.normpath(_LAST_CREATED_ITEM).lower() == norm:
            _LAST_CREATED_ITEM = None
        return {"success": True, "path": path, "name": os.path.basename(path)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def analyze_file(target: str) -> Dict[str, Any]:
    try:
        path = resolve_file_path(target)
        if not os.path.exists(path):
            return {"success": False, "error": f"Файл '{os.path.basename(path)}' не найден"}
        size_bytes = os.path.getsize(path)
        ext = os.path.splitext(path)[1].lower()
        content_preview = ""
        lines_count = 0
        if size_bytes < 2 * 1024 * 1024:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    lines_count = len(lines)
                    content_preview = "".join(lines[:30])
            except Exception:
                pass
        return {
            "success": True,
            "path": path,
            "name": os.path.basename(path),
            "size_kb": round(size_bytes / 1024, 2),
            "ext": ext,
            "lines": lines_count,
            "preview": content_preview
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_folder_files(target: str = "desktop") -> Dict[str, Any]:
    try:
        path = resolve_file_path(target)
        if not os.path.exists(path):
            return {"success": False, "error": "Папка не найдена"}
        items = os.listdir(path)
        files = []
        dirs = []
        for item in items[:40]:
            fp = os.path.join(path, item)
            if os.path.isdir(fp):
                dirs.append(item)
            else:
                files.append(item)
        return {"success": True, "path": path, "folder_name": os.path.basename(path), "files": files, "folders": dirs, "total": len(items)}
    except Exception as e:
        return {"success": False, "error": str(e)}


