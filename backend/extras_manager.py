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
            "color": "graphite",
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
    """Loads all tasks, notes, timers and reminders from the most recently updated persistent JSON store."""
    best_data = None
    best_mtime = -1.0
    for p in _PATHS_TO_TRY:
        if os.path.exists(p):
            try:
                mtime = os.path.getmtime(p)
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if mtime > best_mtime:
                        best_mtime = mtime
                        best_data = data
            except Exception:
                pass
    if best_data is not None:
        res = DEFAULT_EXTRAS_DATA.copy()
        res.update(best_data)
        return res
    return DEFAULT_EXTRAS_DATA.copy()

def save_extras_data(data: Dict[str, Any]) -> bool:
    """Saves all extras data persistently across all available writable locations."""
    saved_any = False
    for p in _PATHS_TO_TRY:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            saved_any = True
        except Exception:
            continue
    return saved_any

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

def add_note(title: str, content: str, category: str = "general", color: str = "graphite", pinned: bool = False) -> Dict[str, Any]:
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
    """Deletes task by id or by matching title substring, or all tasks if 'all'/'все'."""
    data = load_extras_data()
    tasks = data.get("tasks", [])
    ident_lower = identifier.strip().lower()
    if ident_lower in ["all", "все", "всё", "все задачи", "список задач", "очисти задачи", "очисти все задачи"]:
        count = len(tasks)
        data["tasks"] = []
        save_extras_data(data)
        return True, {"title": f"Все задачи ({count} шт.)"}
    for i, t in enumerate(tasks):
        if t.get("id") == identifier or (ident_lower and ident_lower in t.get("title", "").lower()):
            removed = tasks.pop(i)
            data["tasks"] = tasks
            save_extras_data(data)
            return True, removed
    return False, None

def update_task(task_id: str, title: Optional[str] = None, description: Optional[str] = None, priority: Optional[str] = None, category: Optional[str] = None, completed: Optional[bool] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Updates existing task fields by task id or title."""
    data = load_extras_data()
    tasks = data.get("tasks", [])
    for t in tasks:
        if t.get("id") == task_id or (task_id and task_id.lower() in t.get("title", "").lower()):
            if title is not None:
                t["title"] = title.strip()
            if description is not None:
                t["description"] = description.strip()
            if priority is not None:
                t["priority"] = priority
            if category is not None:
                t["category"] = category
            if completed is not None:
                t["completed"] = completed
            save_extras_data(data)
            return True, t
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
    """Deletes note by id or by matching title or content substring, or all notes if 'all'/'все'."""
    data = load_extras_data()
    notes = data.get("notes", [])
    ident_lower = identifier.strip().lower()
    if ident_lower in ["all", "все", "всё", "все заметки", "всё заметки", "каждую заметку", "очисти заметки", "очисти все заметки", "удали все заметки", "удалить все заметки"]:
        count = len(notes)
        data["notes"] = []
        save_extras_data(data)
        return True, {"title": f"Все заметки ({count} шт.)"}
    for i, n in enumerate(notes):
        if n.get("id") == identifier or (ident_lower and (ident_lower in n.get("title", "").lower() or ident_lower in n.get("content", "").lower())):
            removed = notes.pop(i)
            data["notes"] = notes
            save_extras_data(data)
            return True, removed
    return False, None

def update_note(note_id: str, title: Optional[str] = None, content: Optional[str] = None, color: Optional[str] = None, category: Optional[str] = None, pinned: Optional[bool] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Updates existing note fields by note id or title."""
    data = load_extras_data()
    notes = data.get("notes", [])
    for n in notes:
        if n.get("id") == note_id or (note_id and note_id.lower() in n.get("title", "").lower()):
            if title is not None:
                n["title"] = title.strip()
            if content is not None:
                n["content"] = content.strip()
            if color is not None:
                n["color"] = color
            if category is not None:
                n["category"] = category
            if pinned is not None:
                n["pinned"] = pinned
            n["updated_at"] = datetime.datetime.now().isoformat()
            save_extras_data(data)
            return True, n
    return False, None

def extract_specific_answer_from_notes(question: str) -> Optional[str]:
    """Extracts a precise specific answer (name, age, city, password, code) from notes rather than dumping raw notes."""
    q = question.lower().strip()
    notes = search_notes(q)
    if not notes:
        # try searching with key nouns
        for w in re.findall(r'\b[a-zA-Zа-яА-ЯёЁ]{3,}\b', q):
            found = search_notes(w)
            if found:
                notes = found
                break
    # If still not found, search all notes
    if not notes:
        data = load_extras_data()
        notes = data.get("notes", [])
    if not notes:
        return None

    # Check each matching note
    for best in notes:
        title = best.get("title", "Заметка")
        text = best.get("content", "").strip()
        full_text = f"{title}. {text}"

        # 1. Question about Name: "как зовут моего друга", "имя друга", "как зовут девушку", "как зовут маму"
        if any(k in q for k in ["как зовут", "как звать", "какое имя", "имя"]):
            target = "друга" if "друг" in q else "девушку" if "девушк" in q else "маму" if "мам" in q else "человека"
            # Pattern A: "друг Илья", "друга зовут Илья", "зовут Илья"
            m = re.search(r'\b(?:друг|друга|подруга|девушка|мама|папа)\s+([А-ЯЁ][а-яё]+|[A-Z][a-z0-9_]+)', full_text)
            if not m:
                m = re.search(r'\b(?:зовут|имя)\s+([А-ЯЁ][а-яё]+|[A-Z][a-z0-9_]+)', full_text)
            if not m:
                m = re.search(r'\b([А-ЯЁ][а-яё]+)\s+(?:ему|ей)\s+\d+', full_text)
            if m:
                name = m.group(1)
                return f"Вашего {target} зовут {name}, сэр."

        # 2. Question about Age: "сколько лет другу", "возраст друга", "сколько ему лет", "сколько лет моему другу"
        if any(k in q for k in ["сколько лет", "возраст", "сколько ему лет", "сколько ей лет"]):
            target = "Вашему другу" if "друг" in q else "Вашей девушке" if "девушк" in q else "Ему"
            m = re.search(r'(\d+)\s*(?:лет|года|год)', full_text)
            if not m:
                m = re.search(r'(?:ему|ей|возраст)\s*(?:составляет|:|=|\s+)?\s*(\d+)', full_text, re.IGNORECASE)
            if m:
                age = m.group(1)
                return f"{target} {age} лет, сэр."

        # 3. Question about Location / City: "где живет мой друг", "в каком городе живет", "где живет"
        if any(k in q for k in ["где живет", "где живёт", "в каком городе", "откуда", "место жительства"]):
            target = "Ваш друг" if "друг" in q else "Человек"
            m = re.search(r'\b(?:живет\s+в|живёт\s+в|проживает\s+в|в\s+городе|из)\s+([А-ЯЁа-яёA-Za-z\-]+)', full_text, re.IGNORECASE)
            if m:
                city = m.group(1).strip().capitalize()
                return f"{target} живет в городе {city}, сэр."

        # 4. Question about Password / Pin / Code: "какой пароль от роутера", "пароль от вайфая"
        if any(k in q for k in ["пароль", "пин", "код", "pass", "password", "ключ"]):
            m = re.search(r'(?:пароль|пин|код|pass|password|ключ)[^\n:=-]*?(?:[:=]|\s+это\s+|\s+—\s+|\s+-\s+|\.\s+)\s*([^\s,;\.]+)', full_text, re.IGNORECASE)
            if not m:
                m = re.search(r'\b(?:пароль|пин|код|pass|password|ключ)(?:\s*(?:от|для|:|=)\s*|\s+)([^\s,;\.]+)', full_text, re.IGNORECASE)
            if m:
                pwd = m.group(1)
                return f"Пароль: {pwd}, сэр."

    # If asking specific question and direct pattern didn't match, return first relevant note snippet
    best = notes[0]
    return f"Судя по вашей заметке «{best.get('title')}», сэр: {best.get('content')}"

def delete_timer(identifier: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Deletes or stops timer by id or matching title, or clears all if 'all'/'все'."""
    data = load_extras_data()
    timers = data.get("timers", [])
    ident_lower = identifier.strip().lower() if identifier else ""
    if not ident_lower or ident_lower in ["all", "все", "всё", "таймер", "таймеры", "активный", "текущий"]:
        # Find active or first timer
        if timers:
            # Stop all active timers or remove the first
            data["timers"] = []
            save_extras_data(data)
            return True, {"title": "Все таймеры"}
        return True, {"title": "Таймер"}
    for i, tm in enumerate(timers):
        if tm.get("id") == identifier or (ident_lower and ident_lower in tm.get("title", "").lower()):
            removed = timers.pop(i)
            data["timers"] = timers
            save_extras_data(data)
            return True, removed
    # If no exact match but timers exist, stop the first running timer
    for i, tm in enumerate(timers):
        if tm.get("is_running"):
            removed = timers.pop(i)
            data["timers"] = timers
            save_extras_data(data)
            return True, removed
    if timers:
        removed = timers.pop(0)
        data["timers"] = timers
        save_extras_data(data)
        return True, removed
    return False, None

def _stem_ru(w: str) -> str:
    w = w.lower().strip()
    for end in ['ами', 'ями', 'ого', 'его', 'ому', 'ему', 'ыми', 'ими', 'ах', 'ях', 'ов', 'ев', 'ей', 'ом', 'ем', 'ам', 'ям', 'ой', 'ей', 'ий', 'ый', 'а', 'я', 'у', 'ю', 'е', 'и', 'ы', 'о']:
        if w.endswith(end) and len(w) - len(end) >= 3:
            return w[:-len(end)]
    return w

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
            score += 20
        if clean_q in content:
            score += 15
            
        # Word and stem matches
        for w in q_words:
            st = _stem_ru(w)
            if w in title or st in title:
                score += 8
            if w in content or st in content:
                score += 6
                
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
