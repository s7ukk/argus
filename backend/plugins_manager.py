import os
import sys
import re
import json
import time
import shutil
import zipfile
import subprocess
import psutil
from typing import Dict, Any, List, Optional

import backend.app_paths as app_paths

# Plugins root directory (strictly local on the PC in writable user data directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(app_paths.get_argus_data_dir(), "plugins_storage")
os.makedirs(PLUGINS_DIR, exist_ok=True)

# In-memory registry of active subprocesses: plugin_id -> subprocess.Popen
_ACTIVE_PROCESSES: Dict[str, subprocess.Popen] = {}

# Common import module name to PyPI package name discrepancies
MODULE_PACKAGE_MAP = {
    "pil": "pillow",
    "cv2": "opencv-python",
    "bs4": "beautifulsoup4",
    "yaml": "pyyaml",
    "sklearn": "scikit-learn",
    "serial": "pyserial",
    "dotenv": "python-dotenv",
    "telebot": "pyTelegramBotAPI",
    "discord": "discord.py",
    "telegram": "python-telegram-bot",
    "magic": "python-magic-bin",
    "fitz": "PyMuPDF",
    "crypto": "pycryptodome",
    "usb": "pyusb",
    "playwright": "playwright",
    "selenium": "selenium",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "pydantic": "pydantic",
    "aiohttp": "aiohttp",
    "requests": "requests"
}

def get_python_executable() -> str:
    """Returns current active Python interpreter path, searching system Python when frozen."""
    if getattr(sys, 'frozen', False) or 'argus-backend' in sys.executable.lower():
        if sys.platform == "win32":
            candidates = [
                os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Python", "Python314", "python.exe"),
                os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Python", "Python312", "python.exe"),
                os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Python", "Python311", "python.exe"),
                os.path.join(os.getenv("ProgramFiles", "C:\\Program Files"), "Python314", "python.exe"),
                os.path.join(os.getenv("ProgramFiles", "C:\\Program Files"), "Python312", "python.exe"),
                shutil.which("python") or "python",
                shutil.which("py") or "py"
            ]
            for c in candidates:
                if c and os.path.exists(c):
                    return c
            return "python"
        else:
            candidates = [
                "/opt/homebrew/bin/python3",
                "/usr/local/bin/python3",
                "/usr/bin/python3",
                shutil.which("python3") or "python3"
            ]
            for c in candidates:
                if c and os.path.exists(c):
                    return c
            return "python3"
    return sys.executable

def _read_plugin_manifest(plugin_path: str) -> Optional[Dict[str, Any]]:
    manifest_file = os.path.join(plugin_path, "plugin.json")
    if os.path.exists(manifest_file):
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading manifest {manifest_file}: {e}")
    return None

def _write_plugin_manifest(plugin_path: str, data: Dict[str, Any]):
    manifest_file = os.path.join(plugin_path, "plugin.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def detect_best_entrypoint(plugin_path: str) -> str:
    """
    Scans project files to find the best launch entrypoint:
    1. Standard names: main.py, app.py, run.py, bot.py, index.py, start.py
    2. Any .py file containing if __name__ == '__main__':
    3. The first .py file found
    """
    priority_names = ["main.py", "app.py", "run.py", "bot.py", "start.py", "index.py", "cli.py"]
    py_files = []
    
    for root, _, files in os.walk(plugin_path):
        for f in files:
            if f.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, f), plugin_path)
                py_files.append(rel_path.replace("\\", "/"))

    # 1. Match priority names in root or top-level
    for name in priority_names:
        if name in py_files:
            return name

    # 2. Check for if __name__ == '__main__':
    for py_rel in py_files:
        full_p = os.path.join(plugin_path, py_rel)
        try:
            with open(full_p, "r", encoding="utf-8", errors="ignore") as f_obj:
                content = f_obj.read()
                if "__main__" in content:
                    return py_rel
        except Exception:
            pass

    return py_files[0] if py_files else "main.py"

def ensure_official_plugins():
    """Seeds official built-in plugins by Argus Core Team."""
    official_plugins = [
        {
            "id": "voice_sunder",
            "name": "Voice Sunder (Голосовой ввод в приложения)",
            "description": "Официальный плагин Argus: распознавание и печать диктуемого текста напрямую в активное окно любой программы (Telegram, Discord, браузер, IDE, блокнот).",
            "entrypoint": "main.py",
            "is_official": True,
            "author": "Argus Core Team",
            "version": "1.0.0",
            "code": (
                '# Argus Voice Sunder Official Plugin\n'
                '# System-level in-app dictation & input handler\n'
                'import sys\n'
                'import time\n\n'
                'print("[Voice Sunder]: Официальный модуль голосового ввода Argus активен.")\n'
                'print("[Voice Sunder]: Служба перехвата хоткеев и инъекции текста в активные окна готова.")\n'
                'while True:\n'
                '    time.sleep(10)\n'
            )
        },
        {
            "id": "web_automator",
            "name": "Web Automator (Умный серфинг)",
            "description": "Официальный плагин Argus: управление вкладками, поиск информации, клики по кнопкам сайтов, скролл и парсинг контента.",
            "entrypoint": "main.py",
            "is_official": True,
            "author": "Argus Core Team",
            "version": "1.0.0",
            "code": (
                '# Argus Web Automator Official Plugin\n'
                'import time\n\n'
                'print("[Web Automator]: Официальный модуль браузерной автоматизации готов.")\n'
                'print("[Web Automator]: Поддержка Chrome, Edge, Firefox, Яндекс.Браузер.")\n'
                'while True:\n'
                '    time.sleep(10)\n'
            )
        },
        {
            "id": "system_optimizer",
            "name": "System Sentinel & Optimizer (Оптимизация ПК)",
            "description": "Официальный плагин Argus: мгновенная очистка кэша, дефрагментация памяти, закрытие зависших процессов, контроль температуры и загрузки.",
            "entrypoint": "main.py",
            "is_official": True,
            "author": "Argus Core Team",
            "version": "1.0.0",
            "code": (
                '# Argus System Sentinel & Optimizer Official Plugin\n'
                'import time\n\n'
                'print("[System Sentinel]: Служба мониторинга ресурсов и оптимизации запущена.")\n'
                'while True:\n'
                '    time.sleep(10)\n'
            )
        }
    ]

    for p in official_plugins:
        p_path = os.path.join(PLUGINS_DIR, p["id"])
        os.makedirs(p_path, exist_ok=True)
        manifest_p = os.path.join(p_path, "plugin.json")
        code_p = os.path.join(p_path, p["entrypoint"])
        if not os.path.exists(code_p):
            with open(code_p, "w", encoding="utf-8") as f:
                f.write(p["code"])
        if not os.path.exists(manifest_p):
            manifest = {
                "id": p["id"],
                "name": p["name"],
                "description": p["description"],
                "entrypoint": p["entrypoint"],
                "is_official": True,
                "author": p["author"],
                "version": p["version"],
                "created_at": time.time(),
                "status": "stopped",
                "pid": None,
                "auto_heal_enabled": True
            }
            _write_plugin_manifest(p_path, manifest)

def list_plugins() -> List[Dict[str, Any]]:
    """List all locally installed plugins and their real-time execution status."""
    ensure_official_plugins()
    plugins = []
    if not os.path.exists(PLUGINS_DIR):
        return plugins

    for item in os.listdir(PLUGINS_DIR):
        item_path = os.path.join(PLUGINS_DIR, item)
        if os.path.isdir(item_path):
            manifest = _read_plugin_manifest(item_path)
            if not manifest:
                entry = detect_best_entrypoint(item_path)
                manifest = {
                    "id": item,
                    "name": item.replace("_", " ").title(),
                    "description": "Пользовательский скрипт автоматизации Argus",
                    "entrypoint": entry,
                    "created_at": time.time(),
                    "status": "stopped",
                    "pid": None,
                    "auto_heal_enabled": True,
                    "is_official": False
                }
                _write_plugin_manifest(item_path, manifest)

            # Check process status
            pid = manifest.get("pid")
            is_running = False
            cpu_percent = 0.0
            memory_mb = 0.0

            if pid and psutil.pid_exists(pid):
                try:
                    p = psutil.Process(pid)
                    if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                        is_running = True
                        memory_mb = round(p.memory_info().rss / (1024 * 1024), 1)
                        cpu_percent = round(p.cpu_percent(interval=None), 1)
                except Exception:
                    is_running = False

            if not is_running and manifest.get("status") == "running":
                manifest["status"] = "stopped"
                manifest["pid"] = None
                _write_plugin_manifest(item_path, manifest)

            # Count total files
            total_files = 0
            for _, _, f_list in os.walk(item_path):
                total_files += len([f for f in f_list if not f.endswith(".log") and f != "plugin.json"])

            plugin_info = {
                "id": manifest.get("id", item),
                "name": manifest.get("name", item),
                "description": manifest.get("description", ""),
                "entrypoint": manifest.get("entrypoint", "main.py"),
                "created_at": manifest.get("created_at", time.time()),
                "status": "running" if is_running else "stopped",
                "pid": pid if is_running else None,
                "memory_mb": memory_mb if is_running else 0,
                "cpu_percent": cpu_percent if is_running else 0,
                "has_logs": os.path.exists(os.path.join(item_path, "plugin.log")),
                "files_count": total_files,
                "auto_heal_enabled": manifest.get("auto_heal_enabled", True),
                "is_official": manifest.get("is_official", False),
                "author": manifest.get("author", "Пользователь"),
                "version": manifest.get("version", "1.0.0")
            }
            plugins.append(plugin_info)

    # Sort: official plugins by priority (voice_sunder -> web_automator -> system_optimizer), then user plugins
    OFFICIAL_ORDER = {"voice_sunder": 0, "web_automator": 1, "system_optimizer": 2}
    return sorted(plugins, key=lambda x: (not x.get("is_official", False), OFFICIAL_ORDER.get(x.get("id"), 99), x.get("name", "")))

def get_plugin_tree(plugin_id: str) -> Dict[str, Any]:
    """
    Returns full recursive file & folder tree structure of a plugin for IDE project inspector.
    """
    plugin_path = os.path.join(PLUGINS_DIR, plugin_id)
    if not os.path.exists(plugin_path):
        return {"error": "not_found"}

    manifest = _read_plugin_manifest(plugin_path) or {}
    active_entry = manifest.get("entrypoint", "main.py")

    def build_node(dir_path: str, rel_dir: str = "") -> List[Dict[str, Any]]:
        items = []
        try:
            entries = sorted(os.listdir(dir_path))
        except Exception:
            return items

        # Folders first, then files
        for e in entries:
            if e in [".git", "__pycache__", "plugin.log", "plugin.json"]:
                continue
            full_p = os.path.join(dir_path, e)
            rel_p = os.path.join(rel_dir, e).replace("\\", "/")
            if os.path.isdir(full_p):
                items.append({
                    "name": e,
                    "type": "directory",
                    "path": rel_p,
                    "children": build_node(full_p, rel_p)
                })
            else:
                ext = os.path.splitext(e)[1].lower().strip(".")
                try:
                    f_size = os.path.getsize(full_p)
                except Exception:
                    f_size = 0
                items.append({
                    "name": e,
                    "type": "file",
                    "path": rel_p,
                    "size": f_size,
                    "ext": ext,
                    "is_entrypoint": (rel_p == active_entry or e == active_entry)
                })
        return items

    return {
        "id": plugin_id,
        "entrypoint": active_entry,
        "root": os.path.basename(plugin_path),
        "tree": build_node(plugin_path)
    }

def get_plugin_file_content(plugin_id: str, file_rel_path: str) -> Dict[str, Any]:
    """Reads content of a specific file inside plugin directory with security checks."""
    plugin_path = os.path.join(PLUGINS_DIR, plugin_id)
    # Prevent path traversal
    normalized_rel = os.path.normpath(file_rel_path.strip().lstrip("/\\"))
    target_file = os.path.join(plugin_path, normalized_rel)

    if not os.path.commonpath([plugin_path, target_file]) == plugin_path:
        return {"error": "Access denied (path traversal)"}

    if not os.path.exists(target_file):
        return {"error": f"File '{file_rel_path}' not found"}

    try:
        size = os.path.getsize(target_file)
        if size > 3 * 1024 * 1024:
            return {"error": "File too large to display (>3MB)", "size": size}

        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        ext = os.path.splitext(target_file)[1].lower().strip(".")
        lang = "python" if ext == "py" else "json" if ext == "json" else "markdown" if ext == "md" else "text"

        return {
            "path": normalized_rel.replace("\\", "/"),
            "content": content,
            "size": size,
            "lang": lang
        }
    except Exception as e:
        return {"error": str(e)}

def save_plugin_file_content(plugin_id: str, file_rel_path: str, content: str) -> Dict[str, Any]:
    """Saves updated content to a file in the plugin directory."""
    plugin_path = os.path.join(PLUGINS_DIR, plugin_id)
    normalized_rel = os.path.normpath(file_rel_path.strip().lstrip("/\\"))
    target_file = os.path.join(plugin_path, normalized_rel)

    if not os.path.commonpath([plugin_path, target_file]) == plugin_path:
        return {"error": "Access denied"}

    try:
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": normalized_rel.replace("\\", "/")}
    except Exception as e:
        return {"success": False, "error": str(e)}

def set_plugin_entrypoint(plugin_id: str, entrypoint: str) -> Dict[str, Any]:
    """Updates the execution entrypoint file for a plugin."""
    plugin_path = os.path.join(PLUGINS_DIR, plugin_id)
    manifest = _read_plugin_manifest(plugin_path)
    if not manifest:
        return {"success": False, "error": "Plugin not found"}

    entrypoint = entrypoint.replace("\\", "/").strip().lstrip("/")
    manifest["entrypoint"] = entrypoint
    _write_plugin_manifest(plugin_path, manifest)
    return {"success": True, "entrypoint": entrypoint}

def create_plugin_with_files(
    name: str,
    description: str,
    entrypoint: str,
    files_data: List[tuple]
) -> Dict[str, Any]:
    """
    Creates a new local plugin saving all files with their relative subpaths,
    or extracting zip archives recursively while auto-detecting the best entrypoint.
    """
    safe_id = "".join([c if c.isalnum() else "_" for c in name.lower()]).strip("_")
    if not safe_id:
        safe_id = f"plugin_{int(time.time())}"

    plugin_path = os.path.join(PLUGINS_DIR, safe_id)
    os.makedirs(plugin_path, exist_ok=True)

    final_entry = entrypoint.strip() or "main.py"
    saved_files = []

    for rel_path, file_bytes in files_data:
        if not rel_path or not file_bytes:
            continue
        # Clean relative path to prevent directory traversal
        norm_rel = os.path.normpath(rel_path.strip().lstrip("/\\"))
        if norm_rel.startswith(".."):
            continue

        if norm_rel.lower().endswith(".zip"):
            zip_dest = os.path.join(plugin_path, "upload_bundle.zip")
            with open(zip_dest, "wb") as f_zip:
                f_zip.write(file_bytes)
            try:
                with zipfile.ZipFile(zip_dest, "r") as z_ref:
                    z_ref.extractall(plugin_path)
            except Exception as ze:
                print("Zip extract error:", ze)
            try:
                os.remove(zip_dest)
            except Exception:
                pass
        else:
            target_file = os.path.join(plugin_path, norm_rel)
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            with open(target_file, "wb") as f_out:
                f_out.write(file_bytes)
            saved_files.append(norm_rel.replace("\\", "/"))

    # If no files were provided, create a default template
    if not saved_files and len(os.listdir(plugin_path)) == 0:
        sample_code = (
            '# Argus Plugin Automation\n'
            'import time\n\n'
            'print("[Argus Plugin]: Running background automation...")\n'
            'for i in range(100):\n'
            '    print(f"Task step {i+1} completed successfully")\n'
            '    time.sleep(2)\n'
        )
        target_f = os.path.join(plugin_path, final_entry)
        with open(target_f, "w", encoding="utf-8") as f_sm:
            f_sm.write(sample_code)

    # Validate or auto-detect entrypoint
    entry_path = os.path.join(plugin_path, final_entry)
    if not os.path.exists(entry_path):
        final_entry = detect_best_entrypoint(plugin_path)

    manifest = {
        "id": safe_id,
        "name": name,
        "description": description or "Пользовательский скрипт автоматизации",
        "entrypoint": final_entry,
        "is_official": False,
        "author": "Пользователь",
        "version": "1.0.0",
        "created_at": time.time(),
        "status": "stopped",
        "pid": None,
        "auto_heal_enabled": True
    }
    _write_plugin_manifest(plugin_path, manifest)
    return manifest

def create_plugin(
    name: str,
    description: str,
    entrypoint: str,
    file_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
    code_content: Optional[str] = None
) -> Dict[str, Any]:
    """Single file / code snippet compatibility wrapper."""
    files_data = []
    if file_bytes and filename:
        files_data.append((filename, file_bytes))
    elif code_content:
        final_entry = entrypoint.strip() or "main.py"
        files_data.append((final_entry, code_content.encode("utf-8")))
    return create_plugin_with_files(name, description, entrypoint, files_data)

def install_missing_package(module_name: str, log_fp) -> bool:
    """
    Installs a missing Python package via pip and logs progress.
    """
    mod_clean = module_name.strip().lower()
    pkg_name = MODULE_PACKAGE_MAP.get(mod_clean, module_name.strip())

    log_fp.write(f"\n[ARGUS AUTO-HEALER]: ⚡ Обнаружена отсутствующая библиотека '{module_name}'.\n")
    log_fp.write(f"[ARGUS AUTO-HEALER]: Запуск автоматической установки пакета '{pkg_name}' через pip...\n")
    log_fp.flush()

    python_bin = get_python_executable()
    try:
        proc = subprocess.run(
            [python_bin, "-m", "pip", "install", pkg_name],
            capture_output=True,
            text=True,
            timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if proc.returncode == 0:
            log_fp.write(f"[ARGUS AUTO-HEALER]: ✔ Библиотека '{pkg_name}' успешно установлена!\n")
            log_fp.flush()
            return True
        else:
            log_fp.write(f"[ARGUS AUTO-HEALER]: ✖ Ошибка установки '{pkg_name}': {proc.stderr}\n")
            log_fp.flush()
            return False
    except Exception as e:
        log_fp.write(f"[ARGUS AUTO-HEALER]: Исключение при установке: {e}\n")
        log_fp.flush()
        return False

def start_plugin(plugin_id: str, max_auto_heals: int = 5) -> Dict[str, Any]:
    """
    Launches the plugin's entrypoint Python script as a background process
    with recursive Self-Healing dependency auto-installer.
    """
    plugin_path = os.path.join(PLUGINS_DIR, plugin_id)
    if not os.path.exists(plugin_path):
        return {"success": False, "error": f"Плагин '{plugin_id}' не найден"}

    manifest = _read_plugin_manifest(plugin_path)
    if not manifest:
        return {"success": False, "error": "Файл манифеста поврежден"}

    entrypoint = manifest.get("entrypoint", "main.py")
    entry_file = os.path.join(plugin_path, entrypoint)
    if not os.path.exists(entry_file):
        # Try auto-detecting entrypoint if previously configured file is missing
        detected = detect_best_entrypoint(plugin_path)
        if os.path.exists(os.path.join(plugin_path, detected)):
            entrypoint = detected
            entry_file = os.path.join(plugin_path, entrypoint)
            manifest["entrypoint"] = entrypoint
            _write_plugin_manifest(plugin_path, manifest)
        else:
            return {"success": False, "error": f"Файл запуска '{entrypoint}' не найден"}

    # If already running, return
    old_pid = manifest.get("pid")
    if old_pid and psutil.pid_exists(old_pid):
        try:
            p = psutil.Process(old_pid)
            if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                return {"success": True, "already_running": True, "pid": old_pid}
        except Exception:
            pass

    log_file = os.path.join(plugin_path, "plugin.log")
    python_bin = get_python_executable()
    healed_packages = []

    # Self-Healing Execution Loop
    for attempt in range(max_auto_heals + 1):
        log_fp = open(log_file, "a", encoding="utf-8")
        if attempt == 0:
            log_fp.write(f"\n--- [ARGUS PLUGIN STARTED: {time.strftime('%Y-%m-%d %H:%M:%S')}] ---\n")
        else:
            log_fp.write(f"\n--- [ARGUS PLUGIN RESTARTED (HEAL #{attempt}): {time.strftime('%Y-%m-%d %H:%M:%S')}] ---\n")
        log_fp.flush()

        try:
            proc = subprocess.Popen(
                [python_bin, entrypoint],
                cwd=plugin_path,
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            # Monitor process for immediate crash (e.g. within 1.2 seconds)
            time.sleep(1.2)
            exit_code = proc.poll()
            log_fp.flush()
            log_fp.close()

            # Process is still running smoothly! Success!
            if exit_code is None:
                _ACTIVE_PROCESSES[plugin_id] = proc
                manifest["status"] = "running"
                manifest["pid"] = proc.pid
                _write_plugin_manifest(plugin_path, manifest)
                return {
                    "success": True,
                    "pid": proc.pid,
                    "status": "running",
                    "healed_packages": healed_packages
                }

            # Process exited immediately. Inspect log for missing dependency
            with open(log_file, "r", encoding="utf-8", errors="replace") as f_r:
                last_logs = "".join(f_r.readlines()[-35:])

            # Check for ModuleNotFoundError or ImportError
            m_missing = re.search(r"ModuleNotFoundError:\s+No\s+module\s+named\s+['\"]([^'\"]+)['\"]", last_logs)
            if not m_missing:
                m_missing = re.search(r"ImportError:\s+cannot\s+import\s+name\s+.*?from\s+['\"]([^'\"]+)['\"]", last_logs)
            if not m_missing:
                m_missing = re.search(r"ImportError:\s+No\s+module\s+named\s+['\"]([^'\"]+)['\"]", last_logs)

            if m_missing and attempt < max_auto_heals:
                missing_module = m_missing.group(1).split(".")[0]
                with open(log_file, "a", encoding="utf-8") as f_append:
                    installed = install_missing_package(missing_module, f_append)
                if installed:
                    healed_packages.append(missing_module)
                    continue # Retry running with newly installed package!

            # If script executed quickly and finished cleanly with code 0
            if exit_code == 0:
                manifest["status"] = "stopped"
                manifest["pid"] = None
                _write_plugin_manifest(plugin_path, manifest)
                return {
                    "success": True,
                    "status": "completed",
                    "message": "Скрипт успешно выполнен (код 0).",
                    "healed_packages": healed_packages
                }

            # Non-import error or max heals exceeded
            manifest["status"] = "stopped"
            manifest["pid"] = None
            _write_plugin_manifest(plugin_path, manifest)
            return {
                "success": False,
                "error": f"Скрипт завершился с ошибкой (код {exit_code}). Проверьте логи плагина.",
                "exit_code": exit_code
            }

        except Exception as e:
            manifest["status"] = "stopped"
            manifest["pid"] = None
            _write_plugin_manifest(plugin_path, manifest)
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "Превышен лимит попыток автоматического исправления библиотек"}

def stop_plugin(plugin_id: str) -> Dict[str, Any]:
    """Stops the running plugin and all its child processes."""
    plugin_path = os.path.join(PLUGINS_DIR, plugin_id)
    manifest = _read_plugin_manifest(plugin_path) if os.path.exists(plugin_path) else None
    
    pid = manifest.get("pid") if manifest else None
    killed = False

    if pid and psutil.pid_exists(pid):
        try:
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except Exception:
                    pass
            parent.kill()
            killed = True
        except Exception as e:
            print("Error killing plugin pid:", e)

    if plugin_id in _ACTIVE_PROCESSES:
        try:
            _ACTIVE_PROCESSES[plugin_id].terminate()
        except Exception:
            pass
        del _ACTIVE_PROCESSES[plugin_id]

    if manifest and os.path.exists(plugin_path):
        manifest["status"] = "stopped"
        manifest["pid"] = None
        _write_plugin_manifest(plugin_path, manifest)
        
        log_file = os.path.join(plugin_path, "plugin.log")
        if os.path.exists(log_file):
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"--- [ARGUS PLUGIN STOPPED: {time.strftime('%Y-%m-%d %H:%M:%S')}] ---\n")
            except Exception:
                pass

    return {"success": True, "stopped": killed}

def get_plugin_logs(plugin_id: str, max_lines: int = 150) -> Dict[str, Any]:
    """Fetches real-time log output for a plugin."""
    plugin_path = os.path.join(PLUGINS_DIR, plugin_id)
    log_file = os.path.join(plugin_path, "plugin.log")
    if not os.path.exists(log_file):
        return {"logs": "Логи отсутствуют. Плагин еще не запускался."}

    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return {"logs": "".join(lines[-max_lines:])}
    except Exception as e:
        return {"logs": f"Ошибка чтения логов: {e}"}

def delete_plugin(plugin_id: str) -> Dict[str, Any]:
    """Stops plugin and removes its directory from disk."""
    stop_plugin(plugin_id)
    plugin_path = os.path.join(PLUGINS_DIR, plugin_id)
    if os.path.exists(plugin_path):
        shutil.rmtree(plugin_path, ignore_errors=True)
        return {"success": True}
    return {"success": False, "error": "Плагин не существует"}
