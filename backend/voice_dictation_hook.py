import sys
import time
import threading
from typing import Optional

_DICTATION_EVENT = threading.Event()
_HOOK_THREAD: Optional[threading.Thread] = None
_RUNNING = False

def get_dictation_event() -> threading.Event:
    return _DICTATION_EVENT

def trigger_dictation():
    """Manually or externally trigger dictation mode."""
    _DICTATION_EVENT.set()

def _run_listener():
    global _RUNNING
    is_mac = sys.platform == "darwin"
    
    # macOS CoreGraphics setup
    cg = None
    if is_mac:
        try:
            import ctypes
            cg = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
        except Exception as e:
            print(f"[Argus Dictation Hook]: Failed to load CoreGraphics on macOS: {e}")

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

    print("[Argus Dictation Hook]: Global Double-Ctrl background monitor started.")

    while _RUNNING:
        is_ctrl_down = False
        try:
            if is_mac:
                if cg:
                    flags = cg.CGEventSourceFlagsState(0)
                    # Support double Control or double Command on macOS
                    is_ctrl_down = bool((flags & kCGEventFlagMaskControl) or (flags & kCGEventFlagMaskCommand))
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
            # Forgiving human double tap interval between 50ms and 650ms
            if 0.05 <= diff <= 0.65:
                print(f"[Argus Dictation Hook]: Double-Ctrl/Cmd detected (interval: {diff*1000:.1f}ms)! Triggering voice dictation...")
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
