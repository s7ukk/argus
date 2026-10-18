import os
import winreg
import glob

def scan_all_pc_apps():
    apps = {}
    
    # 1. Registry App Paths
    reg_locations = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
    ]
    for hkey, subkey in reg_locations:
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
                                    name_key = k_name.lower().replace(".exe", "")
                                    apps[name_key] = path
                    except Exception:
                        pass
        except Exception:
            pass

    # 2. Start Menu Shortcuts (.lnk)
    start_menu_dirs = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs")
    ]
    for s_dir in start_menu_dirs:
        if os.path.exists(s_dir):
            for lnk in glob.glob(os.path.join(s_dir, "**", "*.lnk"), recursive=True):
                base = os.path.splitext(os.path.basename(lnk))[0].lower()
                if "uninstall" not in base and "деинсталл" not in base:
                    apps[base] = lnk

    # 3. Common user AppData installations (Postman, Discord, Telegram, VS Code, etc.)
    user_home = os.path.expanduser("~")
    common_patterns = [
        os.path.join(user_home, "AppData", "Local", "*", "*.exe"),
        os.path.join(user_home, "AppData", "Local", "Programs", "*", "*.exe"),
        os.path.join(user_home, "AppData", "Local", "Postman", "app-*", "Postman.exe"),
        os.path.join(user_home, "AppData", "Local", "Postman", "Postman.exe"),
        os.path.join(user_home, "AppData", "Roaming", "*", "*.exe"),
        r"C:\Program Files\*\*.exe",
        r"C:\Program Files (x86)\*\*.exe"
    ]
    for pat in common_patterns:
        for p in glob.glob(pat):
            f_name = os.path.splitext(os.path.basename(p))[0].lower()
            if not any(x in f_name for x in ["update", "unins", "setup", "helper", "crash", "installer"]):
                apps[f_name] = p

    return apps

if __name__ == "__main__":
    found = scan_all_pc_apps()
    print("Found total apps on PC:", len(found))
    for k in sorted(found.keys()):
        if any(term in k for term in ["postman", "chrome", "telegram", "code", "calc", "discord"]):
            print(f"  {k} => {found[k]}")
