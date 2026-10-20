import os
import json
import re
from typing import Dict, Any, Optional

try:
    import backend.app_paths as app_paths
    _MEMORY_FILE = app_paths.get_data_file_path("user_memory.json")
except Exception:
    _MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_memory.json")
_MEMORY_CACHE: Optional[Dict[str, Any]] = None

def load_memory() -> Dict[str, Any]:
    global _MEMORY_CACHE
    if _MEMORY_CACHE is not None:
        return _MEMORY_CACHE
    if os.path.exists(_MEMORY_FILE):
        try:
            with open(_MEMORY_FILE, "r", encoding="utf-8") as f:
                _MEMORY_CACHE = json.load(f)
                return _MEMORY_CACHE
        except Exception:
            pass
    _MEMORY_CACHE = {
        "name": None,
        "age": None,
        "birth_year": None,
        "city": None,
        "occupation": None,
        "interests": [],
        "notes": []
    }
    return _MEMORY_CACHE

def save_memory() -> None:
    global _MEMORY_CACHE
    if _MEMORY_CACHE is None:
        return
    try:
        with open(_MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(_MEMORY_CACHE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[Argus Memory]: Error saving user memory:", e)

def set_fact(key: str, value: Any) -> None:
    mem = load_memory()
    mem[key] = value
    save_memory()

def get_fact(key: str, default: Any = None) -> Any:
    mem = load_memory()
    return mem.get(key, default)

def get_memory_summary() -> str:
    mem = load_memory()
    facts = []
    if mem.get("name"):
        facts.append(f"Имя: {mem['name']}")
    if mem.get("age"):
        facts.append(f"Возраст: {mem['age']} лет")
    if mem.get("city"):
        facts.append(f"Город: {mem['city']}")
    if mem.get("occupation"):
        facts.append(f"Род деятельности: {mem['occupation']}")
    if mem.get("interests"):
        facts.append(f"Интересы: {', '.join(mem['interests'])}")
    if mem.get("notes"):
        facts.append(f"Заметки: {'; '.join(mem['notes'])}")
    if not facts:
        return "У меня пока нет сохраненной информации о вас."
    return "Вот что я о вас знаю:\n" + "\n".join(f"• {f}" for f in facts)

def extract_and_learn(user_text: str) -> Optional[str]:
    """
    Analyzes user text to extract personal facts (age, name, city, occupation, notes).
    If a fact is learned, saves it persistently and returns a friendly conversational response.
    """
    t = user_text.strip()
    low = t.lower()
    mem = load_memory()

    # 1. Age extraction: "мне 18 лет", "мне 18", "мой возраст 18", "мне исполнилось 18"
    m_age = re.search(r'\b(?:мне\s+(?:уже\s+)?(?:исполнилось\s+)?|мой\s+возраст\s+|i\s+am\s+|i\'m\s+)(\d{1,3})(?:\s+(?:лет|года|год|years\s+old))?\b', low)
    if m_age:
        age_val = int(m_age.group(1))
        if 1 <= age_val <= 120:
            mem["age"] = age_val
            save_memory()
            return f"Запомнил. Вам {age_val} лет. Буду учитывать ваш возраст в нашей дальнейшей работе."

    # Direct short statement: "18 лет"
    m_age_short = re.match(r'^(\d{1,3})\s+(?:лет|года|год)$', low)
    if m_age_short:
        age_val = int(m_age_short.group(1))
        if 1 <= age_val <= 120:
            mem["age"] = age_val
            save_memory()
            return f"Запомнил ваш возраст: {age_val} лет."

    # 2. Name extraction: "меня зовут <Имя>", "моё имя <Имя>", "зови меня <Имя>", "my name is <Name>"
    m_name = re.search(r'\b(?:меня\s+зовут|мо[её]\s+имя|зови\s+меня|my\s+name\s+is)\s+([a-zA-Zа-яА-ЯёЁ]+)\b', t, re.IGNORECASE)
    if m_name:
        name_val = m_name.group(1).capitalize()
        if name_val.lower() not in ["аргус", "argus", "пользователь", "друг"]:
            mem["name"] = name_val
            save_memory()
            return f"Приятно познакомиться, {name_val}. Я запомнил ваше имя и буду обращаться к вам так."

    # 3. City extraction: "я живу в <Городе>", "я из <Города>"
    m_city = re.search(r'\b(?:я\s+живу\s+в|я\s+из)\s+([a-zA-Zа-яА-ЯёЁ\s\-]+?)(?:\.|$|,)', t, re.IGNORECASE)
    if m_city:
        city_val = m_city.group(1).strip().capitalize()
        if len(city_val) >= 2 and city_val.lower() not in ["доме", "квартире", "интернете", "сети"]:
            mem["city"] = city_val
            save_memory()
            return f"Запомнил ваш город: {city_val}."

    # 4. Occupation: "я работаю <профессия>", "я программист/дизайнер/студент"
    m_occ = re.search(r'\b(?:я\s+работаю\s+|я\s+по\s+профессии\s+|я\s+учусь\s+на\s+)([a-zA-Zа-яА-ЯёЁ\s]+?)(?:\.|$|,)', t, re.IGNORECASE)
    if m_occ:
        occ_val = m_occ.group(1).strip()
        if len(occ_val) >= 3:
            mem["occupation"] = occ_val
            save_memory()
            return f"Отлично, запомнил вашу деятельность: {occ_val}."

    # 5. Explicit memo: "запомни, что ...", "запомни: ...", "remember that ..."
    m_memo = re.search(r'\b(?:запомни(?:,\s*что|\s*:|\s+что)?|remember\s+that)\s+(.+)$', t, re.IGNORECASE)
    if m_memo:
        note_val = m_memo.group(1).strip()
        if len(note_val) >= 3:
            if "notes" not in mem:
                mem["notes"] = []
            if note_val not in mem["notes"]:
                mem["notes"].append(note_val)
                save_memory()
            return f"Запомнил: «{note_val}»."

    return None

def query_memory_question(user_text: str) -> Optional[str]:
    """
    Answers questions about stored user facts (e.g. 'сколько мне лет', 'как меня зовут').
    """
    low = user_text.lower().strip()
    mem = load_memory()

    # 1. Question about Age
    if any(q in low for q in ["сколько мне лет", "какой мой возраст", "мой возраст", "how old am i", "my age"]):
        if mem.get("age"):
            return f"Вам {mem['age']} лет."
        else:
            return "Вы пока не говорили мне, сколько вам лет. Напишите, например: «мне 18 лет», и я запомню."

    # 2. Question about Name
    if any(q in low for q in ["как меня зовут", "какое мое имя", "какое моё имя", "кто я", "what is my name", "who am i"]):
        if mem.get("name"):
            return f"Вас зовут {mem['name']}."
        else:
            return "Вы пока не назвали свое имя. Скажите, например: «меня зовут Алексей», и я запомню."

    # 3. Question about City / Location
    if any(q in low for q in ["где я живу", "из какого я города", "в каком я городе", "мой город", "where do i live"]):
        if mem.get("city"):
            return f"Вы живете в {mem['city']}."
        else:
            return "Вы еще не говорили, в каком городе живете."

    # 4. Question about Occupation
    if any(q in low for q in ["кем я работаю", "где я работаю", "какая у меня профессия", "чем я занимаюсь"]):
        if mem.get("occupation"):
            return f"Вы работаете: {mem['occupation']}."
        else:
            return "Вы еще не рассказывали о своей профессии."

    # 5. General memory summary: "что ты обо мне знаешь", "что ты помнишь обо мне", "что ты знаешь про меня"
    if any(q in low for q in [
        "что ты обо мне знаешь", "что ты знаешь обо мне", "что ты знаешь про меня",
        "что ты помнишь обо мне", "что ты помнишь про меня", "какая у тебя информация обо мне",
        "мои данные", "моя инфа", "моя информация"
    ]):
        return get_memory_summary()

    # 6. Forget memory: "забудь обо мне", "очисти память", "забудь мой возраст"
    if any(q in low for q in ["забудь обо мне", "очисти память", "удали информацию обо мне"]):
        mem.clear()
        mem.update({"name": None, "age": None, "birth_year": None, "city": None, "occupation": None, "interests": [], "notes": []})
        save_memory()
        return "Вся сохраненная персональная информация о вас успешно удалена."

    if any(q in low for q in ["забудь мой возраст", "удали мой возраст"]):
        mem["age"] = None
        save_memory()
        return "Информация о вашем возрасте удалена."

    return None
