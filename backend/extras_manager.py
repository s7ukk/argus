import os
import json
import uuid
import datetime
import re
from typing import Dict, Any, List, Optional, Tuple
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

def delete_task(identifier: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Deletes task by id or by matching title substring."""
    data = load_extras_data()
    tasks = data.get("tasks", [])
    ident_lower = identifier.strip().lower()
    for i, t in enumerate(tasks):
        if t.get("id") == identifier or (ident_lower and ident_lower in t.get("title", "").lower()):
            removed = tasks.pop(i)
            data["tasks"] = tasks
            save_extras_data(data)
            return True, removed
    return False, None

def complete_task(identifier: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Marks task as completed by id or by matching title substring."""
    data = load_extras_data()
    tasks = data.get("tasks", [])
    ident_lower = identifier.strip().lower()
    for t in tasks:
        if t.get("id") == identifier or (ident_lower and ident_lower in t.get("title", "").lower()):
            t["completed"] = True
            save_extras_data(data)
            return True, t
    return False, None

def delete_note(identifier: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Deletes note by id or by matching title or content substring."""
    data = load_extras_data()
    notes = data.get("notes", [])
    ident_lower = identifier.strip().lower()
    for i, n in enumerate(notes):
        if n.get("id") == identifier or (ident_lower and (ident_lower in n.get("title", "").lower() or ident_lower in n.get("content", "").lower())):
            removed = notes.pop(i)
            data["notes"] = notes
            save_extras_data(data)
            return True, removed
    return False, None

def delete_timer(identifier: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Deletes or stops timer by id or matching title, or clears all if 'all'/'все'."""
    data = load_extras_data()
    timers = data.get("timers", [])
    ident_lower = identifier.strip().lower()
    if ident_lower in ["all", "все", "всё"]:
        data["timers"] = []
        save_extras_data(data)
        return True, {"title": "Все таймеры"}
    for i, tm in enumerate(timers):
        if tm.get("id") == identifier or (ident_lower and ident_lower in tm.get("title", "").lower()):
            removed = timers.pop(i)
            data["timers"] = timers
            save_extras_data(data)
            return True, removed
    return False, None

def search_notes(query: str) -> List[Dict[str, Any]]:
    """
    Intelligently searches user notes by keywords across title and content.
    Returns ranked list of matching notes.
    """
    data = load_extras_data()
    notes = data.get("notes", [])
    if not query or not query.strip():
        return notes
    
    clean_q = query.lower()
    # Remove common conversational filler words
    stopwords = {
        "какой", "какая", "какое", "какие", "где", "когда", "что", "кто",
        "почему", "как", "у", "меня", "в", "моих", "заметках", "заметке",
        "заметка", "заметки", "найди", "поищи", "про", "о", "об", "сэр",
        "аргус", "argus", "пожалуйста", "подскажи", "скажи", "покажи",
        "записано", "записал", "сохранено", "сохранил"
    }
    q_words = [w for w in re.findall(r'\b\w+\b', clean_q) if w not in stopwords and len(w) > 2]
    
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for n in notes:
        title = n.get("title", "").lower()
        content = n.get("content", "").lower()
        score = 0
        
        # Direct exact phrase match
        if clean_q in title:
            score += 15
        if clean_q in content:
            score += 10
            
        # Word matches
        for w in q_words:
            if w in title:
                score += 6
            if w in content:
                score += 4
                
        if score > 0:
            scored.append((score, n))
            
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored]

def format_notes_context_for_ai() -> str:
    """Formats user notes and tasks into a concise context block for AI reasoning."""
    data = load_extras_data()
    notes = data.get("notes", [])
    tasks = data.get("tasks", [])
    timers = data.get("timers", [])
    
    parts = []
    if notes:
        notes_lines = []
        for n in notes[:20]:
            t = n.get("title", "Заметка")
            c = n.get("content", "").replace("\n", " ").strip()
            notes_lines.append(f"- «{t}»: {c}")
        parts.append("[ЛИЧНЫЕ ЗАМЕТКИ И СОХРАНЁННЫЕ ДАННЫЕ ПОЛЬЗОВАТЕЛЯ]:\n" + "\n".join(notes_lines))
        
    if tasks:
        active_tasks = [t for t in tasks if not t.get("completed")]
        done_tasks = [t for t in tasks if t.get("completed")]
        task_lines = []
        for t in active_tasks[:10]:
            task_lines.append(f"- [В процессе] {t.get('title')} ({t.get('category', 'общее')})")
        for t in done_tasks[:5]:
            task_lines.append(f"- [Выполнено] {t.get('title')}")
        parts.append("[СПИСОК ТЕКУЩИХ ЗАДАЧ]:\n" + "\n".join(task_lines))
        
    if timers:
        active_timers = [tm for tm in timers if tm.get("is_running") and tm.get("remaining_seconds", 0) > 0]
        if active_timers:
            timer_lines = [f"- «{tm.get('title')}»: осталось {tm.get('remaining_seconds')} сек." for tm in active_timers]
            parts.append("[АКТИВНЫЕ ТАЙМЕРЫ]:\n" + "\n".join(timer_lines))
            
    return "\n\n".join(parts)
