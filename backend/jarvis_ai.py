import re
from typing import Dict, Any, Tuple, Optional
import backend.system_control as sc

SYSTEM_PERSONA = """Ты — Argus, автономная система искусственного интеллекта и персональный ассистент следующего поколения.
Ты управляешь компьютером пользователя, выполняешь любые команды системы, помогаешь с кодом, информацией и повседневными задачами.
Твой тон: умный, уверенный, технологичный, лаконичный, сдержанный и уважительный.
"""

def extract_number(text: str, default: int = 10) -> int:
    match = re.search(r'\b(\d{1,3})\b', text)
    if match:
        return int(match.group(1))
    return default

def process_command(user_text: str, user_name: str = "Командир") -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
    """
    Parse user prompt for PC control commands or conversational intent.
    Returns: (response_text, action_type, action_data)
    """
    text = user_text.strip().lower()
    
    # 1. VOLUME CONTROLS
    if any(k in text for k in ["громкост", "звук", "тише", "громче"]):
        if any(k in text for k in ["выключи звук", "без звука", "мут", "заглуши"]):
            sc.toggle_mute()
            return f"Звук отключен, {user_name}.", "volume_mute", {"level": 0}
        
        if any(k in text for k in ["прибавь", "громче", "подними", "увелич"]):
            num = extract_number(text, 10)
            lvl = sc.change_volume(num)
            return f"Громкость увеличена на {num}%. Текущий уровень: {lvl}%.", "volume_change", {"level": lvl}
            
        if any(k in text for k in ["убавь", "тише", "потише", "снизь", "уменьш"]):
            num = extract_number(text, 10)
            lvl = sc.change_volume(-num)
            return f"Громкость снижена на {num}%. Текущий уровень: {lvl}%.", "volume_change", {"level": lvl}
            
        if any(k in text for k in ["на", "поставь", "сделай", "установи"]):
            lvl = extract_number(text, 50)
            final_lvl = sc.set_volume(lvl)
            return f"Громкость установлена на {final_lvl}%, {user_name}.", "volume_set", {"level": final_lvl}

    # 2. BRIGHTNESS CONTROLS
    if any(k in text for k in ["яркост", "экран"]):
        if any(k in text for k in ["прибавь", "ярче", "увелич"]):
            num = extract_number(text, 10)
            b = sc.change_brightness(num)
            return f"Яркость экрана увеличена. Текущий уровень: {b}%.", "brightness_change", {"level": b}
            
        if any(k in text for k in ["убавь", "темнее", "снизь", "уменьш"]):
            num = extract_number(text, 10)
            b = sc.change_brightness(-num)
            return f"Яркость экрана снижена. Текущий уровень: {b}%.", "brightness_change", {"level": b}
            
        if any(k in text for k in ["поставь", "сделай", "установи", "на"]):
            lvl = extract_number(text, 70)
            b = sc.set_brightness(lvl)
            return f"Яркость установлена на {b}%, {user_name}.", "brightness_set", {"level": b}

    # 3. LOCK WORKSTATION
    if any(k in text for k in ["заблокируй пк", "заблокируй комп", "заблокируй компьютер", "экран блокировки", "lock pc"]):
        sc.lock_workstation()
        return f"Компьютер заблокирован, {user_name}. Протокол безопасности активирован.", "system_lock", {}

    # 4. MEDIA CONTROLS
    if any(k in text for k in ["следующий трек", "след трек", "переключи песню", "переключи трек"]):
        sc.media_control("next")
        return "Включаю следующий трек.", "media_next", {}
    if any(k in text for k in ["предыдущий трек", "пред трек", "назад трек"]):
        sc.media_control("prev")
        return "Включаю предыдущий трек.", "media_prev", {}
    if any(k in text for k in ["пауза", "поставь на паузу", "останови музыку", "воспроизведи", "продолжи трек"]):
        sc.media_control("play")
        return "Медиаплеер переключен.", "media_play_pause", {}

    # 5. OPEN APPLICATIONS
    if any(k in text for k in ["открой", "запусти", "включи"]):
        for app in ["telegram", "телеграм", "телега", "дискорд", "discord", "стим", "steam", "спотифай", "spotify",
                    "калькулятор", "calculator", "блокнот", "notepad", "диспетчер", "браузер", "хром", "chrome",
                    "терминал", "пэйнт", "paint", "проводник", "настройки", "код", "vscode"]:
            if app in text:
                res = sc.launch_application(app)
                return f"Запускаю {app.capitalize()}, {user_name}.", "launch_app", res

    # 6. SYSTEM STATS & METRICS
    if any(k in text for k in ["статус системы", "нагрузка", "процессор", "память", "диагностика", "батаре", "характеристики"]):
        stats = sc.get_system_stats()
        cpu_p = stats["cpu"]["percent"]
        ram_p = stats["memory"]["percent"]
        ram_used = stats["memory"]["used_gb"]
        ram_total = stats["memory"]["total_gb"]
        disk_free = stats["disk"]["free_gb"]
        
        reply = (
            f"Телеметрия Argus готова, {user_name}:\n"
            f"• Процессор (ЦП): {cpu_p}%\n"
            f"• Оперативная память (ОЗУ): {ram_p}% ({ram_used} из {ram_total} ГБ)\n"
            f"• Свободно на накопителе: {disk_free} ГБ\n"
            f"• Громкость: {stats['volume']}% | Яркость: {stats['brightness']}%"
        )
        if stats["battery"]:
            reply += f"\n• Батарея: {stats['battery']['percent']}% ({'сеть' if stats['battery']['power_plugged'] else 'аккумулятор'})"
        return reply, "system_stats", stats

    # 7. WEB SEARCH & YOUTUBE
    if "найди в ютубе" in text or "найди на ютубе" in text:
        query = re.sub(r'.*найди (на|в) ютубе\s*', '', text)
        url = f"https://www.youtube.com/results?search_query={query}"
        sc.open_url(url)
        return f"Ищу «{query}» на YouTube.", "open_url", {"url": url}

    if "найди в гугле" in text or "поищи в гугле" in text or "загугли" in text:
        query = re.sub(r'.*(найди в гугле|поищи в гугле|загугли)\s*', '', text)
        url = f"https://www.google.com/search?q={query}"
        sc.open_url(url)
        return f"Открываю поиск в Google по запросу «{query}».", "open_url", {"url": url}

    # 8. CONVERSATIONAL INTELLIGENCE / PERSONA
    if any(k in text for k in ["кто ты", "что ты умеешь", "расскажи о себе"]):
        return (
            f"Я — Argus, ваш персональный искусственный интеллект и автономная система управления ПК. "
            f"Я контролирую системный звук и подсветку монитора, мгновенно запускаю ваши программы, слежу за "
            f"нагрузкой железа, блокирую компьютер, управляю медиаплеером и отвечаю на любые вопросы текстом и голосом. "
            f"Чем займемся, {user_name}?"
        ), "info", {}

    if any(k in text for k in ["привет", "здравствуй", "добрый день", "добрый вечер", "доброе утро"]):
        return f"Приветствую, {user_name}! Все системы Argus онлайн. Жду ваших указаний.", "greeting", {}

    if any(k in text for k in ["спасибо", "благодарю", "отлично", "молодец"]):
        return f"Рад служить, {user_name}. Обращайтесь в любой момент.", "compliment", {}

    return (
        f"Команда принята, {user_name}. Модели Argus непрерывно развиваются. "
        f"Запрос обработан: «{user_text}»."
    ), "general", {}
