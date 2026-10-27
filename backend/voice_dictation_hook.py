import sys
import time
import threading
import subprocess
from typing import Optional, Dict, Any

_DICTATION_EVENT = threading.Event()
_HOOK_THREAD: Optional[threading.Thread] = None
_RUNNING = False
_LAST_TARGET_HWND: Optional[int] = None
_LAST_TARGET_APP: Optional[str] = None

def get_dictation_event() -> threading.Event:
    return _DICTATION_EVENT

def get_last_dictation_target() -> Dict[str, Any]:
    return {"hwnd": _LAST_TARGET_HWND, "app": _LAST_TARGET_APP}

def _capture_active_target():
    global _LAST_TARGET_HWND, _LAST_TARGET_APP
    if sys.platform == "darwin":
        try:
            res = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'],
                capture_output=True, text=True, timeout=1
            )
            app = res.stdout.strip()
            if app and not any(k in app.lower() for k in ["argus", "electron"]):
                _LAST_TARGET_APP = app
        except Exception:
            pass
    else:
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd:
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.lower()
                if not any(k in title for k in ["argus dictation", "argus ai"]):
                    _LAST_TARGET_HWND = hwnd
        except Exception:
            pass

def trigger_dictation():
    """Manually or externally trigger dictation mode."""
    _capture_active_target()
    _DICTATION_EVENT.set()

def _run_listener():
    global _RUNNING
    is_mac = sys.platform == "darwin"
    
    # macOS CoreGraphics & ApplicationServices setup
    cg = None
    if is_mac:
        import ctypes
        import ctypes.util
        for name in [
            'CoreGraphics',
            '/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics',
            '/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices',
            ctypes.util.find_library('CoreGraphics'),
            ctypes.util.find_library('ApplicationServices')
        ]:
            if not name:
                continue
            try:
                cand = ctypes.cdll.LoadLibrary(name)
                if hasattr(cand, 'CGEventSourceFlagsState'):
                    cg = cand
                    break
            except Exception:
                pass

        if cg:
            try:
                cg.CGEventSourceFlagsState.argtypes = [ctypes.c_int32]
                cg.CGEventSourceFlagsState.restype = ctypes.c_uint64
            except Exception as e:
                print(f"[Argus Dictation Hook]: CGEventSourceFlagsState setup: {e}")
            try:
                if hasattr(cg, 'CGEventSourceKeyState'):
                    cg.CGEventSourceKeyState.argtypes = [ctypes.c_int32, ctypes.c_uint16]
                    cg.CGEventSourceKeyState.restype = ctypes.c_bool
            except Exception as e:
                print(f"[Argus Dictation Hook]: CGEventSourceKeyState setup: {e}")
            print("[Argus Dictation Hook]: macOS CoreGraphics loaded successfully.")
        else:
            print("[Argus Dictation Hook]: Notice: CoreGraphics not loaded via CDLL.")

    # Windows user32 setup
    user32 = None
    if not is_mac:
        try:
            import ctypes
            user32 = ctypes.windll.user32
        except Exception as e:
            print(f"[Argus Dictation Hook]: Failed to load user32 on Windows: {e}")

    VK_CONTROL = 0x11
    VK_LCONTROL = 0xA2
    VK_RCONTROL = 0xA3
    kCGEventFlagMaskControl = 0x00040000
    kCGEventFlagMaskCommand = 0x00100000

    last_ctrl_down_time = 0.0
    ctrl_was_down = False

    print("[Argus Dictation Hook]: Global Double-Ctrl/Cmd background monitor started.")

    while _RUNNING:
        is_ctrl_down = False
        try:
            if is_mac:
                if cg:
                    f0 = cg.CGEventSourceFlagsState(0)
                    f1 = cg.CGEventSourceFlagsState(1)
                    has_flags = bool(
                        (f0 & kCGEventFlagMaskControl) or (f1 & kCGEventFlagMaskControl) or
                        (f0 & kCGEventFlagMaskCommand) or (f1 & kCGEventFlagMaskCommand)
                    )
                    has_keys = False
                    if hasattr(cg, 'CGEventSourceKeyState'):
                        # 59: Left Control, 62: Right Control, 55: Left Command, 54: Right Command
                        has_keys = bool(
                            cg.CGEventSourceKeyState(1, 59) or cg.CGEventSourceKeyState(1, 62) or
                            cg.CGEventSourceKeyState(1, 55) or cg.CGEventSourceKeyState(1, 54) or
                            cg.CGEventSourceKeyState(0, 59) or cg.CGEventSourceKeyState(0, 62) or
                            cg.CGEventSourceKeyState(0, 55) or cg.CGEventSourceKeyState(0, 54)
                        )
                    is_ctrl_down = has_flags or has_keys
            else:
                if user32:
                    is_ctrl_down = bool(
                        (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) or
                        (user32.GetAsyncKeyState(VK_LCONTROL) & 0x8000) or
                        (user32.GetAsyncKeyState(VK_RCONTROL) & 0x8000)
                    )
        except Exception:
            is_ctrl_down = False

        now = time.time()
        # On key press transition (up -> down)
        if is_ctrl_down and not ctrl_was_down:
            diff = now - last_ctrl_down_time
            # Forgiving human double tap interval between 50ms and 700ms
            if 0.05 <= diff <= 0.70:
                print(f"[Argus Dictation Hook]: Double-Ctrl/Cmd detected (interval: {diff*1000:.1f}ms)! Triggering voice dictation...")
                _capture_active_target()
                _DICTATION_EVENT.set()
                last_ctrl_down_time = 0.0
            else:
                last_ctrl_down_time = now

        ctrl_was_down = is_ctrl_down
        time.sleep(0.012)

def start_dictation_hook():
    global _HOOK_THREAD, _RUNNING
    if _HOOK_THREAD and _HOOK_THREAD.is_alive():
        return
    _RUNNING = True
    _HOOK_THREAD = threading.Thread(target=_run_listener, daemon=True, name="DoubleCtrlDictationHook")
    _HOOK_THREAD.start()

def stop_dictation_hook():
    global _RUNNING
    _RUNNING = False
