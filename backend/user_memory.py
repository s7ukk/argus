import os
import json
import re
from typing import Dict, Any, Optional

try:
    import backend.app_paths as app_paths
    _MEMORY_FILE = app_paths.get_data_file_path("user_memory.json")
except Exception:
    _MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_memory.json")

_PATHS_TO_TRY = [
    _MEMORY_FILE,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_memory.json"),
    os.path.join(os.path.expanduser("~"), ".argus_user_memory.json")
]
_MEMORY_CACHE: Optional[Dict[str, Any]] = None

def load_memory() -> Dict[str, Any]:
    global _MEMORY_CACHE
    if _MEMORY_CACHE is not None:
        return _MEMORY_CACHE
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
        _MEMORY_CACHE = best_data
        return _MEMORY_CACHE
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
    for p in _PATHS_TO_TRY:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(_MEMORY_CACHE, f, ensure_ascii=False, indent=2)
        except Exception:
            continue

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
    Can extract MULTIPLE facts in a single utterance (e.g. 'меня зовут Игорь мне 25').
    If facts are learned, saves them persistently and returns a friendly conversational response.
    """
    t = user_text.strip()
    low = t.lower()
    mem = load_memory()
    learned_items = []

    # 1. Name extraction: "меня зовут <Имя>", "моё имя <Имя>", "зови меня <Имя>", "my name is <Name>"
    m_name = re.search(r'\b(?:меня\s+зовут|мо[её]\s+имя|зови\s+меня|my\s+name\s+is)\s+([a-zA-Zа-яА-ЯёЁ]+)\b', t, re.IGNORECASE)
    if m_name:
        name_val = m_name.group(1).capitalize()
        if name_val.lower() not in ["аргус", "argus", "пользователь", "друг", "мне", "я"]:
            mem["name"] = name_val
            learned_items.append(f"вас зовут {name_val}")

    # 1.5 Friend extraction: "моего друга зовут <Имя>", "мой друг <Имя>"
    m_friend = re.search(r'\b(?:моего\s+друга\s+зовут|мой\s+друг(?:\s+это|\s+зовут)?)\s+([a-zA-Zа-яА-ЯёЁ0-9_]+)\b', t, re.IGNORECASE)
    if m_friend:
        friend_val = m_friend.group(1).capitalize()
        if friend_val.lower() not in ["аргус", "argus", "пользователь", "я", "друг"]:
            mem["friend_name"] = friend_val
            if "notes" not in mem or not isinstance(mem["notes"], list):
                mem["notes"] = []
            mem["notes"].append(f"Друга зовут {friend_val}")
            learned_items.append(f"вашего друга зовут {friend_val}")

    # 2. Age extraction: "мне 18 лет", "мне 18", "мой возраст 18", "мне исполнилось 18"
    m_age = re.search(r'\b(?:мне\s+(?:уже\s+)?(?:исполнилось\s+)?|мой\s+возраст\s+|i\s+am\s+|i\'m\s+)(\d{1,3})(?:\s+(?:лет|года|год|years\s+old))?\b', low)
    if not m_age:
        m_age = re.search(r'(?:^|\s)(\d{1,3})\s+(?:лет|года|год)\b', low)
    if m_age:
        age_val = int(m_age.group(1))
        if 1 <= age_val <= 120:
            mem["age"] = age_val
            learned_items.append(f"вам {age_val} лет")

    # 3. City extraction: "я живу в <Городе>", "я из <Города>"
    m_city = re.search(r'\b(?:я\s+живу\s+в|я\s+из)\s+([a-zA-Zа-яА-ЯёЁ\s\-]+?)(?:\.|$|,)', t, re.IGNORECASE)
    if m_city:
        city_val = m_city.group(1).strip().capitalize()
        if len(city_val) >= 2 and city_val.lower() not in ["доме", "квартире", "интернете", "сети"]:
            mem["city"] = city_val
            learned_items.append(f"город: {city_val}")

    # 4. Occupation: "я работаю <профессия>", "я программист/дизайнер/студент"
    m_occ = re.search(r'\b(?:я\s+работаю\s+|я\s+по\s+профессии\s+|я\s+учусь\s+на\s+)([a-zA-Zа-яА-ЯёЁ\s]+?)(?:\.|$|,)', t, re.IGNORECASE)
    if m_occ:
        occ_val = m_occ.group(1).strip()
        if len(occ_val) >= 3:
            mem["occupation"] = occ_val
            learned_items.append(f"деятельность: {occ_val}")

    # 5. Explicit memo: "запомни, что ...", "запомни: ...", "remember that ..."
    m_memo = re.search(r'\b(?:запомни(?:,\s*что|\s*:|\s+что)?|remember\s+that)\s+(.+)$', t, re.IGNORECASE)
    if m_memo:
        note_val = m_memo.group(1).strip()
        if len(note_val) >= 3:
            if "notes" not in mem or not isinstance(mem["notes"], list):
                mem["notes"] = []
            if note_val not in mem["notes"]:
                mem["notes"].append(note_val)
            learned_items.append(f"заметка «{note_val}»")

    if learned_items:
        save_memory()
        return f"Запомнил: {', '.join(learned_items)}. Буду учитывать это в нашей дальнейшей работе."

    return None

def query_memory_question(user_text: str, has_history: bool = False) -> Optional[str]:
    """
    Answers questions about stored user facts (e.g. 'сколько мне лет', 'как меня зовут').
    If the fact is not in local memory and has_history is True, returns None to allow
    the LLM to answer using the multi-turn conversation context.
    """
    low = user_text.lower().strip()
    mem = load_memory()

    # 1. Question about Age
    if any(q in low for q in ["сколько мне лет", "какой мой возраст", "мой возраст", "how old am i", "my age"]):
        if mem.get("age"):
            return f"Вам {mem['age']} лет."
        elif not has_history:
            return "Вы пока не говорили мне, сколько вам лет. Напишите, например: «мне 18 лет», и я запомню."

    # 2. Question about Name
    if any(q in low for q in ["как меня зовут", "какое мое имя", "какое моё имя", "кто я", "what is my name", "who am i"]):
        if mem.get("name"):
            return f"Вас зовут {mem['name']}."
        elif not has_history:
            return "Вы пока не назвали свое имя. Скажите, например: «меня зовут Алексей», и я запомню."

    # 2.5 Question about Friend
    if any(q in low for q in ["как зовут моего друга", "как зовут друга", "моего друга зовут", "кто мой друг", "имя моего друга", "как звать моего друга", "как звать друга"]):
        if mem.get("friend_name"):
            return f"Вашего друга зовут {mem['friend_name']}, сэр."
        try:
            try:
                import backend.extras_manager as em
            except ImportError:
                import extras_manager as em
            ans = em.extract_specific_answer_from_notes(user_text)
            if ans:
                return ans
        except Exception:
            pass
        for n in mem.get("notes", []):
            if "друг" in n.lower():
                return f"Судя по моим записям, сэр: {n}."
        return "Вы пока не говорили мне, как зовут вашего друга, сэр. Скажите, например: «Моего друга зовут Алексей», или создайте заметку, и я обязательно запомню это."

    # 2.6 Question about Relatives
    if any(q in low for q in ["как зовут мою девушку", "имя моей девушки", "как зовут мою жену", "как зовут маму", "как зовут папу"]):
        try:
            try:
                import backend.extras_manager as em
            except ImportError:
                import extras_manager as em
            ans = em.extract_specific_answer_from_notes(user_text)
            if ans:
                return ans
        except Exception:
            pass
        return "У меня пока нет информации об этом в ваших заметках или памяти, сэр. Вы можете сказать мне или записать в заметки, и я сохраню это."

    # 3. Question about City / Location
    if any(q in low for q in ["где я живу", "из какого я города", "в каком я городе", "мой город", "where do i live"]):
        if mem.get("city"):
            return f"Вы живете в {mem['city']}."
        elif not has_history:
            return "Вы еще не говорили, в каком городе живете."

    # 4. Question about Occupation
    if any(q in low for q in ["кем я работаю", "где я работаю", "какая у меня профессия", "чем я занимаюсь"]):
        if mem.get("occupation"):
            return f"Вы работаете: {mem['occupation']}."
        elif not has_history:
            return "Вы еще не рассказывали о своей профессии."

    # 5. General memory summary: "что ты обо мне знаешь", "какую информацию обо мне знаешь", "что знаешь обо мне"
    if any(q in low for q in [
        "что ты обо мне знаешь", "что ты знаешь обо мне", "что ты знаешь про меня",
        "что ты помнишь обо мне", "что ты помнишь про меня", "какая у тебя информация обо мне",
        "какую информацию обо мне знаешь", "какую инфу обо мне знаешь", "какие данные обо мне",
        "какую информацию ты обо мне знаешь", "что обо мне знаешь", "что помнишь обо мне",
        "что знаешь обо мне", "что знаешь про меня", "мои данные", "моя инфа", "моя информация"
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
