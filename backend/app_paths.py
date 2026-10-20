import os
import sys
import shutil

def get_argus_data_dir() -> str:
    if sys.platform == "win32":
        base = os.getenv("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.getenv("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")

    target = os.path.join(base, "ArgusAI")
    try:
        os.makedirs(target, exist_ok=True)
    except Exception:
        target = os.path.expanduser("~/.argus")
        try:
            os.makedirs(target, exist_ok=True)
        except Exception:
            target = os.path.expanduser("~")
    return target

def get_data_file_path(filename: str) -> str:
    data_dir = get_argus_data_dir()
    target_path = os.path.join(data_dir, filename)
    
    # If file doesn't exist in user data directory, check if legacy local file exists
    if not os.path.exists(target_path):
        legacy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        if os.path.exists(legacy_path):
            try:
                shutil.copy2(legacy_path, target_path)
            except Exception:
                pass
    return target_path
