import os
import json
import uuid
import datetime
from typing import Dict, Any, List, Optional
import backend.app_paths as app_paths

EXTRAS_FILE = app_paths.get_data_file_path("extras_data.json")

DEFAULT_EXTRAS_DATA: Dict[str, Any] = {
    "tasks": [
        {
            "id": "task_demo_1",
            "title": "Сделать домашнее задание",
            "description": "Математика и физика",
            "priority": "high",
            "category": "study",
            "completed": False,
            "due_date": "",
            "created_at": datetime.datetime.now().isoformat()
        },
        {
            "id": "task_demo_2",
            "title": "Проверить функционал Argus AI",
            "description": "Проверить таймеры, заметки и задачи",
            "priority": "urgent",
            "category": "work",
            "completed": True,
            "due_date": "",
            "created_at": datetime.datetime.now().isoformat()
        }
    ],
    "notes": [
        {
            "id": "note_demo_1",
            "title": "План на день",
            "content": "1. Проверить меню Дополнительно\n2. Проверить отправку сообщений в Telegram\n3. Запустить таймер на ДЗ",
            "category": "work",
            "color": "purple",
            "pinned": True,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat()
        },
        {
            "id": "note_demo_2",
            "title": "Горячие клавиши",
            "content": "• Telegram поиск: Ctrl+F / Cmd+F\n• Двойной Ctrl: голосовой ввод в активное окно\n• Пробел PTT: голосовой ассистент",
            "category": "info",
            "color": "blue",
            "pinned": False,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat()
        }
    ],
    "timers": [
        {
            "id": "timer_demo_1",
            "title": "Сделать ДЗ",
            "total_seconds": 420,
            "remaining_seconds": 420,
            "is_running": False,
            "is_completed": False,
            "created_at": datetime.datetime.now().isoformat()
        }
    ],
    "reminders": []
}

_PATHS_TO_TRY = [
    EXTRAS_FILE,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "extras_data.json"),
    os.path.join(os.path.expanduser("~"), ".argus_extras.json")
]

def load_extras_data() -> Dict[str, Any]:
    """Loads all tasks, notes, timers and reminders from persistent JSON store."""
    for p in _PATHS_TO_TRY:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    res = DEFAULT_EXTRAS_DATA.copy()
                    res.update(data)
                    return res
            except Exception:
                pass
    return DEFAULT_EXTRAS_DATA.copy()

def save_extras_data(data: Dict[str, Any]) -> bool:
    """Saves all extras data persistently with reliable fallback."""
    for p in _PATHS_TO_TRY:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            continue
    return False

def add_task(title: str, description: str = "", priority: str = "medium", category: str = "general", due_date: str = "") -> Dict[str, Any]:
    data = load_extras_data()
    task = {
        "id": f"task_{uuid.uuid4().hex[:8]}",
        "title": title.strip(),
        "description": description.strip(),
        "priority": priority,
        "category": category,
        "completed": False,
        "due_date": due_date,
        "created_at": datetime.datetime.now().isoformat()
    }
    data.setdefault("tasks", []).insert(0, task)
    save_extras_data(data)
    return task

def add_note(title: str, content: str, category: str = "general", color: str = "purple", pinned: bool = False) -> Dict[str, Any]:
    data = load_extras_data()
    now_iso = datetime.datetime.now().isoformat()
    note = {
        "id": f"note_{uuid.uuid4().hex[:8]}",
        "title": title.strip(),
        "content": content.strip(),
        "category": category,
        "color": color,
        "pinned": pinned,
        "created_at": now_iso,
        "updated_at": now_iso
    }
    data.setdefault("notes", []).insert(0, note)
    save_extras_data(data)
    return note

def add_timer(title: str, total_seconds: int) -> Dict[str, Any]:
    data = load_extras_data()
    timer = {
        "id": f"timer_{uuid.uuid4().hex[:8]}",
        "title": title.strip() or "Таймер",
        "total_seconds": max(1, total_seconds),
        "remaining_seconds": max(1, total_seconds),
        "is_running": True,
        "is_completed": False,
        "created_at": datetime.datetime.now().isoformat()
    }
    data.setdefault("timers", []).insert(0, timer)
    save_extras_data(data)
    return timer

def add_reminder(title: str, remind_at: str) -> Dict[str, Any]:
    data = load_extras_data()
    reminder = {
        "id": f"rem_{uuid.uuid4().hex[:8]}",
        "title": title.strip(),
        "remind_at": remind_at,
        "is_completed": False,
        "created_at": datetime.datetime.now().isoformat()
    }
    data.setdefault("reminders", []).insert(0, reminder)
    save_extras_data(data)
    return reminder
