try:
    import backend.user_memory as user_memory
except ImportError:
    import user_memory
import sys
import os
import re
import time
import json
import urllib.request
import urllib.error
import urllib.parse
import datetime
import math
from typing import Optional, List, Dict, Any, Tuple
import backend.system_control as sc
import backend.plugins_manager as pm
import backend.scenarios_manager as sc_mgr
import backend.gui_agent as gui_agent
try:
    import backend.extras_manager as extras_mgr
except ImportError:
    import extras_manager as extras_mgr
try:
    import backend.openrouter_engine as openrouter_engine
except ImportError:
    import openrouter_engine

_AI_QUERY_CACHE: Dict[str, str] = {}
_MESSENGER_WIZARD_STATE: Dict[str, Dict[str, Any]] = {}

INVALID_CONTACT_KEYWORDS = {
    'контакт', 'контакту', 'контакта', 'контактом', 'контакте', 'контакты',
    'пользователь', 'пользователю', 'пользователя', 'пользователем', 'пользователи',
    'человек', 'человеку', 'человека', 'людям', 'друг', 'другу', 'друга', 'друзьям',
    'собеседник', 'собеседнику', 'юзер', 'юзеру', 'ник', 'нику', 'никнейм',
    'сообщение', 'текст', 'слово', 'привет', 'хеллоу', 'hello', 'hi',
    'кому-то', 'кому-нибудь', 'кому', 'куда', 'ему', 'ей', 'им', 'ним'
}

_AI_PLAN_CACHE: Dict[str, Any] = {}

def is_english(text: str) -> bool:
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    cyrillic_chars = len(re.findall(r'[а-яА-ЯёЁ]', text))
    return latin_chars > cyrillic_chars

def solve_algebraic_equation(query: str) -> Optional[str]:
    """
    Directly solves biquadratic, quadratic, and linear equations with full steps in 0ms.
    Examples:
      'x4 - 5x2 + 4 = 0 реши'
      'x^4 - 5x^2 + 4 = 0'
      'x^2 - 3x + 2 = 0'
      'x^2 - 3x + 5 = 0'
      '2x + 10 = 0'
    """
    q = query.lower().strip()
    if not any(k in q for k in ['x', 'y', '=']) or not re.search(r'[xy]\^?\d?|[xy]\b', q):
        return None

    q = re.sub(r'^(?:пожалуйста\s+|плиз\s+|аргус\s+|эй\s+аргус\s+)*', '', q).strip()
    q = re.sub(r'(?:реши|решить|найди\s+корни|найди\s+корень|уравнение|пожалуйст[а-я]*|найди|корни|\?|!)+', '', q).strip()
    q = q.replace(' ', '')
    if not q:
        return None

    if '=' not in q:
        if re.search(r'x\^?4|x\^?2|x\b', q):
            q += "=0"
        else:
            return None

    sides = q.split('=')
    if len(sides) != 2:
        return None

    left, right = sides[0].strip(), sides[1].strip()
    if not left:
        return None

    r_val = 0.0
    if right and right != '0':
        try:
            r_val = float(right)
        except ValueError:
            return None

    norm_left = re.sub(r'x4\b', 'x^4', left)
    norm_left = re.sub(r'x2\b', 'x^2', norm_left)
    norm_left = norm_left.replace('*', '')

    # 1. Biquadratic: a*x^4 + b*x^2 + c = 0
    bi_pattern = r'^([+-]?(?:\d+(?:\.\d+)?)?)x\^4([+-](?:\d+(?:\.\d+)?)?)x\^2([+-]\d+(?:\.\d+)?)?$'
    m_bi = re.match(bi_pattern, norm_left)
    if m_bi:
        a_str, b_str, c_str = m_bi.group(1), m_bi.group(2), m_bi.group(3)
        a = 1.0 if not a_str or a_str == '+' else (-1.0 if a_str == '-' else float(a_str))
        b = 1.0 if b_str == '+' else (-1.0 if b_str == '-' else float(b_str))
        c = float(c_str) if c_str else 0.0
        c -= r_val

        if a != 0:
            D = b*b - 4*a*c
            steps = [
                f"Дано биквадратное уравнение: {norm_left} = {int(r_val) if r_val.is_integer() else r_val}",
                f"Сделаем замену переменной: t = x^2, где t >= 0.",
                f"Получаем квадратное уравнение относительно t: {int(a) if a.is_integer() else a}t^2 + ({int(b) if b.is_integer() else b})t + ({int(c) if c.is_integer() else c}) = 0.",
                f"Дискриминант: D = b^2 - 4ac = ({int(b) if b.is_integer() else b})^2 - 4 * ({int(a) if a.is_integer() else a}) * ({int(c) if c.is_integer() else c}) = {int(D) if D.is_integer() else D}."
            ]

            if D < 0:
                steps.append("Так как дискриминант D < 0, действительных корней нет.")
                return "\n".join(steps)

            sqrt_D = math.isqrt(int(D)) if D.is_integer() and math.isqrt(int(D))**2 == int(D) else math.sqrt(D)
            t1 = (-b + sqrt_D) / (2*a)
            t2 = (-b - sqrt_D) / (2*a)

            t1_fmt = int(t1) if isinstance(t1, float) and t1.is_integer() else round(t1, 4)
            t2_fmt = int(t2) if isinstance(t2, float) and t2.is_integer() else round(t2, 4)

            steps.append(f"Корни уравнения относительно t: t1 = {t1_fmt}, t2 = {t2_fmt}.")
            steps.append("Выполняем обратную замену x^2 = t:")

            roots = []
            for idx, t_val in enumerate([t1, t2], 1):
                if t_val > 0:
                    sq = math.isqrt(int(t_val)) if isinstance(t_val, (int, float)) and float(t_val).is_integer() and math.isqrt(int(t_val))**2 == int(t_val) else math.sqrt(t_val)
                    sq_fmt = int(sq) if isinstance(sq, float) and sq.is_integer() else round(sq, 4)
                    steps.append(f"• При t{idx} = {int(t_val) if float(t_val).is_integer() else t_val}: x^2 = {int(t_val) if float(t_val).is_integer() else t_val} => x = ±{sq_fmt}")
                    roots.extend([sq_fmt, -sq_fmt])
                elif t_val == 0:
                    steps.append(f"• При t{idx} = 0: x^2 = 0 => x = 0")
                    roots.append(0)
                else:
                    steps.append(f"• При t{idx} = {int(t_val) if float(t_val).is_integer() else t_val}: решений в действительных числах нет (t должно быть >= 0).")

            if roots:
                unique_roots = sorted(list(set(roots)))
                ans_str = ", ".join(f"x = {r}" for r in unique_roots)
                steps.append(f"\nОтвет: {ans_str}.")
            else:
                steps.append("\nОтвет: действительных корней нет.")

            return "\n".join(steps)

    # 2. Quadratic Equation: a*x^2 + b*x + c = 0
    quad_pattern = r'^([+-]?(?:\d+(?:\.\d+)?)?)x\^2([+-](?:\d+(?:\.\d+)?)?)x([+-]\d+(?:\.\d+)?)?$'
    m_quad = re.match(quad_pattern, norm_left)
    if m_quad:
        a_str, b_str, c_str = m_quad.group(1), m_quad.group(2), m_quad.group(3)
        a = 1.0 if not a_str or a_str == '+' else (-1.0 if a_str == '-' else float(a_str))
        b = 1.0 if b_str == '+' else (-1.0 if b_str == '-' else float(b_str))
        c = float(c_str) if c_str else 0.0
        c -= r_val

        if a != 0:
            D = b*b - 4*a*c
            steps = [
                f"Квадратное уравнение: {norm_left} = {int(r_val) if r_val.is_integer() else r_val}",
                f"Коэффициенты: a = {int(a) if a.is_integer() else a}, b = {int(b) if b.is_integer() else b}, c = {int(c) if c.is_integer() else c}.",
                f"Дискриминант: D = b^2 - 4ac = ({int(b) if b.is_integer() else b})^2 - 4 * ({int(a) if a.is_integer() else a}) * ({int(c) if c.is_integer() else c}) = {int(D) if D.is_integer() else D}."
            ]
            if D > 0:
                sq = math.isqrt(int(D)) if D.is_integer() and math.isqrt(int(D))**2 == int(D) else math.sqrt(D)
                x1 = (-b + sq) / (2*a)
                x2 = (-b - sq) / (2*a)
                x1_fmt = int(x1) if x1.is_integer() else round(x1, 4)
                x2_fmt = int(x2) if x2.is_integer() else round(x2, 4)
                steps.append(f"Так как D > 0, уравнение имеет два различных действительных корня:")
                steps.append(f"x1 = (-b + √D) / (2a) = {x1_fmt}")
                steps.append(f"x2 = (-b - √D) / (2a) = {x2_fmt}")
                steps.append(f"\nОтвет: x1 = {x1_fmt}, x2 = {x2_fmt}.")
            elif D == 0:
                x = -b / (2*a)
                x_fmt = int(x) if x.is_integer() else round(x, 4)
                steps.append(f"Так как D = 0, уравнение имеет один корень:")
                steps.append(f"x = -b / (2a) = {x_fmt}")
                steps.append(f"\nОтвет: x = {x_fmt}.")
            else:
                steps.append("Так как D < 0, уравнение не имеет действительных корней.")
                sq_neg = math.sqrt(-D)
                sq_neg_fmt = f"√{-int(D)}" if not sq_neg.is_integer() else f"{int(sq_neg)}"
                steps.append(f"Комплексные корни: x1 = ({int(-b)} + {sq_neg_fmt}i) / {int(2*a)}, x2 = ({int(-b)} - {sq_neg_fmt}i) / {int(2*a)}.")
            return "\n".join(steps)

    # 3. Incomplete Quadratic: a*x^2 + c = 0 (e.g. x^2 = 9, x^2 - 16 = 0)
    m_quad_simple = re.match(r'^([+-]?(?:\d+(?:\.\d+)?)?)x\^2([+-]\d+(?:\.\d+)?)?$', norm_left)
    if m_quad_simple:
        a_str, c_str = m_quad_simple.group(1), m_quad_simple.group(2)
        a = 1.0 if not a_str or a_str == '+' else (-1.0 if a_str == '-' else float(a_str))
        c = float(c_str) if c_str else 0.0
        c -= r_val
        val = -c / a
        if val > 0:
            sq = math.isqrt(int(val)) if val.is_integer() and math.isqrt(int(val))**2 == int(val) else math.sqrt(val)
            sq_fmt = int(sq) if isinstance(sq, float) and sq.is_integer() else round(sq, 4)
            return f"Квадратное уравнение: {norm_left} = {int(r_val) if r_val.is_integer() else r_val}\nx^2 = {int(val) if val.is_integer() else val}\nx = ±{sq_fmt}\nОтвет: x1 = {sq_fmt}, x2 = -{sq_fmt}."
        elif val == 0:
            return f"Квадратное уравнение: {norm_left} = 0\nОтвет: x = 0."
        else:
            return f"Квадратное уравнение: {norm_left} = {int(r_val) if r_val.is_integer() else r_val}\nx^2 = {val}\nОтвет: действительных корней нет."

    # 4. Simple Linear: a*x + b = c
    m_lin = re.match(r'^([+-]?(?:\d+(?:\.\d+)?)?)x([+-]\d+(?:\.\d+)?)?$', norm_left)
    if m_lin:
        a_str, b_str = m_lin.group(1), m_lin.group(2)
        a = 1.0 if not a_str or a_str == '+' else (-1.0 if a_str == '-' else float(a_str))
        b = float(b_str) if b_str else 0.0
        if a != 0:
            x = (r_val - b) / a
            x_fmt = int(x) if x.is_integer() else round(x, 4)
            return f"Линейное уравнение: {norm_left} = {int(r_val) if r_val.is_integer() else r_val}\n{int(a) if a.is_integer() else a}x = {int(r_val - b) if (r_val - b).is_integer() else (r_val - b)}\nx = {x_fmt}\nОтвет: x = {x_fmt}."

    return None

def safe_math_eval(expr: str) -> Optional[float]:
    # If expression contains '=' or variable symbols (e.g. 'x', 'y'), it's an equation or complex math
    # Leave it to OpenRouter Free Engine for step-by-step solution
    if '=' in expr:
        return None
    if re.search(r'\b[a-zA-Z]\b|\d+[a-zA-Z]', expr):
        return None

    cleaned = expr.replace('^', '**').replace('×', '*').replace('÷', '/')
    cleaned = re.sub(r'[^0-9+\-*/().,** ]', '', cleaned).replace(',', '.')
    if not cleaned or not any(c in cleaned for c in '+-*/'):
        return None
    try:
        allowed = {"__builtins__": None, "math": math}
        res = eval(cleaned, allowed, {})
        if isinstance(res, (int, float)):
            return round(res, 4)
    except Exception:
        pass
    return None

# ─── ACTION EXECUTOR ─────────────────────────────────────────────
def execute_single_action(act: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
    """
    Executes a single concrete system command on Windows.
    Returns: (status_message, action_type, data)
    """
    act_type = act.get("type", "").lower()
    
    if act_type == "clarify":
        return act.get("message", "Уточните, пожалуйста, сэр: укажите команду, приложение или действие."), "clarify", act

    if act_type == "messenger_wizard":
        return act.get("message", "Выберите мессенджер, сэр."), "messenger_wizard", act

    if act_type == "scenario":
        sc_id = act.get("id") or act.get("scenario_id")
        for sc_obj in sc_mgr.load_scenarios():
            if sc_obj.get("id") == sc_id:
                res = sc_mgr.execute_scenario(sc_obj)
                return res["summary"], "scenario", res
        return "Сценарий не найден", "scenario", {}

    if act_type == "launch_app":
        app = act.get("app", "chrome")
        res = sc.launch_application(app)
        app_disp = app.capitalize()
        if app.lower() in ["chrome", "хром", "браузер", "browser", "хром браузер"]:
            app_disp = "Chrome"
        elif app.lower() in ["telegram", "телеграм", "телега", "тг"]:
            app_disp = "Telegram"
        elif app.lower() in ["discord", "дискорд"]:
            app_disp = "Discord"
        elif app.lower() in ["vscode", "код", "vs code"]:
            app_disp = "VS Code"
        elif app.lower() in ["goland", "голенд", "голэнд"]:
            app_disp = "GoLand"
        elif app.lower() in ["postman", "постман"]:
            app_disp = "Postman"

        if res.get("success"):
            return f"Запущено приложение: {app_disp}", "launch_app", res
        else:
            return f"Не удалось открыть {app_disp}: {res.get('error', 'приложение не найдено')}", "launch_app", res

    elif act_type == "close_active_window":
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "w" using {command down}'], capture_output=True)
        else:
            if sc._HAS_PYAUTOGUI:
                import pyautogui
                pyautogui.hotkey('alt', 'f4')
        return "Активное окно закрыто", "close_active_window", {}

    elif act_type == "minimize_window":
        ok = sc.minimize_current_window()
        return "Окно свёрнуто", "minimize_window", {"success": ok}

    elif act_type == "minimize_all_windows":
        ok = sc.minimize_all_windows()
        return "Все окна свёрнуты", "minimize_all", {"success": ok}

    elif act_type == "minimize_app":
        app = act.get("app", "")
        ok = sc.minimize_application(app)
        app_disp = app.capitalize()
        if app.lower() in ["vscode", "код", "vs code"]:
            app_disp = "VS Code"
        elif app.lower() in ["chrome", "хром", "браузер"]:
            app_disp = "Chrome"
        elif app.lower() in ["telegram", "телеграм", "телега", "тг"]:
            app_disp = "Telegram"
        elif app.lower() in ["discord", "дискорд"]:
            app_disp = "Discord"
        return f"Окно {app_disp} свёрнуто", "minimize_app", {"success": ok, "app": app}

    elif act_type == "close_app":
        app = act.get("app", "")
        res = sc.close_application(app)
        app_disp = app.capitalize()
        if app.lower() in ["vscode", "код", "vs code"]:
            app_disp = "VS Code"
        elif app.lower() in ["chrome", "хром", "браузер"]:
            app_disp = "Chrome"
        return f"Закрыто приложение: {app_disp}", "close_app", res

    elif act_type == "browser_choice":
        browsers = act.get("browsers", [])
        b_names = "\n".join([f"• {b['name']}" for b in browsers])
        msg = f"На вашем компьютере обнаружены следующие браузеры:\n{b_names}\n\nКакой именно браузер открыть? (Например: «Открой {browsers[0]['name']}» или «Открой {browsers[-1]['name']}»)"
        return msg, "browser_choice", {"browsers": browsers}

    elif act_type == "close_browser_tab":
        ok = sc.close_browser_tab()
        return "Вкладка браузера закрыта", "close_tab", {"success": ok}

    elif act_type == "close_specific_browser_tab":
        target = act.get("target", "")
        ok = sc.close_specific_browser_tab(target)
        target_disp = target.capitalize()
        if target.lower() in ["deepseek", "дипсик", "дипсика", "дипсике", "дипсиком"]:
            target_disp = "DeepSeek"
        elif target.lower() in ["chatgpt", "чатгпт", "чат гпт"]:
            target_disp = "ChatGPT"
        elif target.lower() in ["google", "гугл", "гугле"]:
            target_disp = "Google"
        elif target.lower() in ["youtube", "ютуб", "ютубе", "ютуби"]:
            target_disp = "YouTube"
        elif target.lower() in ["vk", "вк", "вконтакте"]:
            target_disp = "VK"
        elif target.lower() in ["yandex", "яндекс"]:
            target_disp = "Яндекс"
        elif target.lower() in ["telegram", "телеграм", "тг"]:
            target_disp = "Telegram"
        elif target.lower() in ["github", "гитхаб"]:
            target_disp = "GitHub"
        elif target.lower() in ["mail", "gmail", "почта", "почту"]:
            target_disp = "Почта"
        msg = f"Вкладка {target_disp} закрыта в браузере, сэр." if ok else f"Вкладка {target_disp} не найдена в запущенных браузерах, сэр."
        return msg, "close_specific_tab", {"target": target, "success": ok}

    elif act_type == "youtube_control":
        yt_act = act.get("action", "play_pause")
        ok = sc.youtube_control(yt_act)
        messages = {
            "play_pause": "Воспроизведение/пауза переключены в YouTube",
            "pause": "Видео в YouTube поставлено на паузу",
            "play": "Видео в YouTube запущено",
            "mute": "Звук в YouTube переключён",
            "fullscreen": "Полноэкранный режим переключён в YouTube",
            "next": "Включено следующее видео в YouTube",
            "prev": "Включено предыдущее видео в YouTube",
            "seek_forward": "Видео перемотано вперёд на 10 секунд",
            "seek_backward": "Видео перемотано назад на 10 секунд",
            "speed_up": "Скорость воспроизведения в YouTube увеличена",
            "speed_down": "Скорость воспроизведения в YouTube уменьшена",
            "subtitles": "Субтитры в YouTube переключены"
        }
        msg = messages.get(yt_act, "Команда YouTube выполнена") if ok else "Окно YouTube не найдено или не активно"
        return msg, "youtube_control", {"action": yt_act, "success": ok}

    elif act_type == "reopen_browser_tab":
        ok = sc.reopen_browser_tab()
        return "Закрытая вкладка восстановлена в браузере", "reopen_tab", {"success": ok}

    elif act_type == "find_in_browser_page":
        query = act.get("query", "")
        ok = sc.find_in_browser_page(query)
        msg = f"Открыт поиск по странице: «{query}»" if query else "Открыта строка поиска по странице"
        return msg, "find_in_page", {"query": query, "success": ok}

    elif act_type == "zoom_browser_page":
        direction = act.get("direction", "in")
        ok = sc.zoom_browser_page(direction)
        desc = "увеличен" if direction == "in" else ("уменьшен" if direction == "out" else "сброшен к 100%")
        return f"Масштаб страницы {desc}", "zoom_page", {"direction": direction, "success": ok}

    elif act_type == "navigate_browser_history":
        direction = act.get("direction", "back")
        ok = sc.navigate_browser_history(direction)
        desc = "назад" if direction == "back" else "вперёд"
        return f"Переход по истории {desc}", "navigate_history", {"direction": direction, "success": ok}

    elif act_type == "open_browser_feature":
        feat = act.get("feature", "history")
        ok = sc.open_browser_feature(feat)
        feat_names = {
            "history": "История браузера открыта",
            "downloads": "Загрузки браузера открыты",
            "bookmarks": "Страница добавлена в закладки",
            "incognito": "Открыто окно в режиме инкогнито"
        }
        return feat_names.get(feat, "Функция браузера активирована"), "browser_feature", {"feature": feat, "success": ok}

    elif act_type == "scroll_browser_to":
        position = act.get("position", "top")
        ok = sc.scroll_browser_to(position)
        desc = "в самый верх" if position == "top" else "в самый низ"
        return f"Страница прокручена {desc}", "scroll_to", {"position": position, "success": ok}

    elif act_type in ["close_all_browser_tabs", "close_all_tabs"]:
        ok = sc.close_all_browser_tabs()
        return "Все вкладки браузера закрыты", "close_all_tabs", {"success": ok}

    elif act_type == "new_browser_tab":
        ok = sc.new_browser_tab()
        return "Открыта новая вкладка в браузере", "new_tab", {"success": ok}

    elif act_type == "refresh_page":
        ok = sc.refresh_browser_page()
        return "Страница в браузере обновлена", "refresh_page", {"success": ok}

    elif act_type == "switch_browser_tab":
        direction = act.get("direction", "next")
        ok = sc.switch_browser_tab(direction)
        return f"Переключена вкладка браузера", "switch_tab", {"direction": direction}

    elif act_type == "scroll_page":
        direction = act.get("direction", "down")
        ok = sc.scroll_browser_page(direction)
        dir_ru = "вниз" if direction == "down" else "вверх"
        return f"Страница прокручена {dir_ru}", "scroll", {"direction": direction}

    elif act_type == "click_website_button":
        btn = act.get("button", "").strip()
        ok = sc.click_website_button(btn)
        return f"Нажата кнопка «{btn}» на открытой веб-странице", "click_button", {"button": btn, "success": ok}

    elif act_type == "terminal_command":
        cmd = act.get("command", "")
        shell = act.get("shell")
        res = sc.execute_terminal_command(cmd, shell_type=shell)
        out_text = res.get("output") or res.get("error") or "Команда выполнена успешно (без вывода)"
        if len(out_text) > 400:
            out_text = out_text[:400] + "..."
        status_word = "успешно" if res.get("success") else "с ошибкой"
        return f"Команда терминала выполнена {status_word}:\n```\n{out_text}\n```", "terminal_command", res

    elif act_type == "close_all_except":
        keep = act.get("keep", [])
        res = sc.close_all_except(keep)
        keep_str = ", ".join([k.upper() if k.lower() == "vscode" else k.capitalize() for k in keep])
        return f"Закрыты все приложения кроме: {keep_str}", "close_all_except", res

    elif act_type == "screenshot":
        folder = act.get("folder", "desktop")
        path = sc.take_screenshot(folder)
        folder_disp = "в Загрузки" if "download" in folder or "загруз" in folder else "в Документы" if "doc" in folder or "документ" in folder else "в Изображения" if "pic" in folder or "изображен" in folder or "картинк" in folder else "на Рабочий стол"
        return f"Снимок экрана сохранен {folder_disp}: {path}", "screenshot", {"path": path, "folder": folder}

    elif act_type == "wait":
        sec = min(5.0, max(0.2, float(act.get("seconds", 1.5))))
        time.sleep(sec)
        return "", "wait", {"seconds": sec}

    elif act_type == "volume_set":
        lvl = int(act.get("level", 50))
        final_lvl = sc.set_volume(lvl)
        return f"Громкость установлена на {final_lvl}%", "volume_set", {"level": final_lvl}

    elif act_type == "volume_change":
        delta = int(act.get("delta", 10))
        lvl = sc.change_volume(delta)
        direction = "увеличена" if delta > 0 else "уменьшена"
        return f"Громкость {direction} на {abs(delta)}%. Текущий уровень: {lvl}%", "volume_change", {"level": lvl}

    elif act_type == "volume_mute":
        muted = sc.toggle_mute()
        state = "выключен" if muted else "включен"
        return f"Звук {state}", "volume_mute", {"muted": muted}

    elif act_type == "brightness_set":
        lvl = int(act.get("level", 80))
        b = sc.set_brightness(lvl)
        return f"Яркость экрана установлена на {b}%", "brightness_set", {"level": b}

    elif act_type == "brightness_change":
        delta = int(act.get("delta", 10))
        b = sc.change_brightness(delta)
        direction = "увеличена" if delta > 0 else "уменьшена"
        return f"Яркость {direction} на {abs(delta)}%. Текущий уровень: {b}%", "brightness_change", {"level": b}

    elif act_type == "empty_recycle":
        sc.empty_recycle_bin()
        return ("Корзина macOS очищена" if sys.platform == "darwin" else "Корзина очищена"), "empty_recycle", {}

    elif act_type == "lock_pc":
        sc.lock_workstation()
        return "Компьютер заблокирован", "system_lock", {}

    elif act_type == "open_url":
        url = act.get("url", "https://google.com")
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        sc.open_url(url)
        return f"Открыта страница: {url}", "open_url", {"url": url}

    elif act_type == "search_web":
        q = act.get("query", "")
        engine = act.get("engine", "google").lower()
        if "yandex" in engine or "яндекс" in engine:
            url = f"https://yandex.ru/search/?text={urllib.parse.quote_plus(q)}"
            eng_name = "в Яндекс"
        elif "youtube" in engine or "ютуб" in engine:
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
            is_play = act.get("is_play", False)
            sc.open_url(url)
            verb = "Включаю на YouTube" if is_play else "Выполнен поиск в YouTube"
            return f"{verb}: «{q}»", "open_url", {"url": url, "query": q, "engine": "youtube"}
        elif "wildberries" in engine or "вайлдберриз" in engine or "вб" in engine:
            url = f"https://www.wildberries.ru/catalog/0/search.aspx?search={urllib.parse.quote_plus(q)}"
            eng_name = "на Wildberries"
        elif "ozon" in engine or "озон" in engine:
            url = f"https://www.ozon.ru/search/?text={urllib.parse.quote_plus(q)}"
            eng_name = "на Ozon"
        elif "avito" in engine or "авито" in engine:
            url = f"https://www.avito.ru/rossiya?q={urllib.parse.quote_plus(q)}"
            eng_name = "на Авито"
        elif "github" in engine or "гитхаб" in engine:
            url = f"https://github.com/search?q={urllib.parse.quote_plus(q)}"
            eng_name = "на GitHub"
        else:
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
            eng_name = "в Google"
        sc.open_url(url)
        return f"Выполнен поиск {eng_name}: «{q}»", "open_url", {"url": url, "query": q}

    elif act_type == "messenger_send":
        messenger = act.get("messenger", "auto").lower()
        contact = act.get("contact", "").strip()
        msg_text = act.get("message", "").strip()
        
        if not contact or not msg_text:
            m_disp = "Telegram" if messenger in ["telegram", "тг"] else "Discord" if messenger in ["discord", "дискорд"] else "WhatsApp" if messenger in ["whatsapp", "ватсап"] else "VK" if messenger in ["vk", "вк"] else "мессенджере"
            if not contact:
                return (
                    f"Уточните, пожалуйста, сэр: укажите имя контакта или username получателя в {m_disp}.\n"
                    f"Например: «В {m_disp if m_disp != 'мессенджере' else 'Telegram'} напиши @username текст {msg_text or 'Привет'}»."
                ), "clarify", act
            else:
                return (
                    f"Уточните, пожалуйста, сэр: какой текст сообщения отправить контакту «{contact}» в {m_disp}?\n"
                    f"Например: «В {m_disp if m_disp != 'мессенджере' else 'Telegram'} напиши {contact} текст Привет»."
                ), "clarify", act

        # 1. If messenger is "auto" or generic, pick active or installed messenger
        if messenger in ["auto", "any", "мессенджер", "chat"]:
            fg = sc.get_foreground_window_title().lower()
            if any(m in fg for m in ["discord", "дискорд"]):
                messenger = "discord"
            elif any(m in fg for m in ["whatsapp", "ватсап"]):
                messenger = "whatsapp"
            elif any(m in fg for m in ["vk", "вконтакте"]):
                messenger = "vk"
            else:
                messenger = "telegram"

        # 2. Execute via Autonomous Visual GUI Computer-Use Agent
        res = gui_agent.execute_autonomous_messenger_task(messenger, contact, msg_text)
        return res["summary"], "messenger_send", res

    elif act_type == "autonomous_browser_task":
        browser = act.get("browser", "safari")
        query = act.get("query", "")
        res = gui_agent.execute_autonomous_browser_task(browser, query)
        return res["summary"], "autonomous_browser_task", res

    elif act_type == "autonomous_notes_task":
        text = act.get("text", "")
        title = act.get("title")
        res = gui_agent.execute_autonomous_notes_task(text, title)
        return res["summary"], "autonomous_notes_task", res

    elif act_type == "open_folder":
        folder = act.get("folder", "desktop")
        sc.open_folder(folder)
        return f"Открыта папка: {folder}", "open_folder", {"folder": folder}

    elif act_type in ["media", "play_music"]:
        m_act = act.get("action", "play")
        service = act.get("service", "auto")
        query = act.get("query", "")
        playlist = act.get("playlist", "")
        res = sc.play_music(service=service, query=query, playlist=playlist, action=m_act)
        return res["message"], "play_music", res

    elif act_type in [
        "create_timer", "delete_timer", "create_task", "delete_task",
        "complete_task", "create_note", "delete_note", "list_tasks",
        "list_notes", "list_timers", "search_notes"
    ]:
        try:
            if act_type == "delete_task":
                extras_mgr.delete_task(act.get("title", ""))
            elif act_type == "complete_task":
                extras_mgr.complete_task(act.get("title", ""))
            elif act_type == "delete_note":
                extras_mgr.delete_note(act.get("title", ""))
            elif act_type == "delete_timer":
                extras_mgr.delete_timer(act.get("title", "all"))
        except Exception:
            pass
        msg = act.get("message", "Действие успешно выполнено, сэр.")
        return msg, act_type, act

    elif act_type == "power":
        p_act = act.get("action", "shutdown")
        sc.system_power(p_act)
        act_ru = "выключение" if p_act == "shutdown" else "перезагрузка" if p_act == "restart" else "отмена выключения"
        return f"Команда питания: {act_ru}", "power", {"action": p_act}

    elif act_type == "system_stats":
        stats = sc.get_system_stats()
        cpu_p = stats.get("cpu", {}).get("percent", 0)
        cores = stats.get("cpu", {}).get("cores", 0)
        mem = stats.get("memory", {})
        used_gb = mem.get("used_gb", 0)
        tot_gb = mem.get("total_gb", 0)
        mem_p = mem.get("percent", 0)
        vol = stats.get("volume", 50)
        br = stats.get("brightness", 80)
        info = f"Процессор: {cpu_p}% ({cores} ядер) | ОЗУ: {used_gb}/{tot_gb} ГБ ({mem_p}%) | Звук: {vol}% | Яркость: {br}%"
        return info, "system_stats", stats

    elif act_type == "type_text":
        text = act.get("text", "")
        target_app = act.get("target_app") or act.get("app")
        field = act.get("field")
        success = sc.type_text(text, target_app=target_app, field=field)
        if act.get("press_enter"):
            time.sleep(0.12)
            sc.press_key("enter")
        enter_note = " и нажат Enter" if act.get("press_enter") else ""
        app_note = f" в {target_app}" if target_app else ""
        return f"Напечатан текст{app_note}{enter_note}: «{text}»", "type_text", {"text": text, "target_app": target_app, "success": success, "press_enter": act.get("press_enter", False)}

    elif act_type == "press_key":
        key = act.get("key", "enter")
        success = sc.press_key(key)
        return f"Нажата клавиша: {key.upper()}", "press_key", {"key": key, "success": success}

    elif act_type == "hotkey":
        keys = act.get("keys", ["ctrl", "c"])
        success = sc.send_hotkey(*keys)
        keys_str = " + ".join([k.upper() for k in keys])
        return f"Выполнено сочетание клавиш: {keys_str}", "hotkey", {"keys": keys, "success": success}

    elif act_type == "plugin_start":
        p_name = act.get("plugin_name", "")
        # Find matching plugin in local plugins
        all_p = pm.list_plugins()
        matched = None
        for p in all_p:
            if p_name.lower() in p["name"].lower() or p_name.lower() in p["id"].lower():
                matched = p
                break
        if matched:
            res = pm.start_plugin(matched["id"])
            if res.get("success"):
                return f"Плагин «{matched['name']}» запущен (PID: {res.get('pid')})", "plugin_start", res
            return f"Ошибка запуска плагина «{matched['name']}»: {res.get('error')}", "plugin_start", res
        return f"Локальный плагин «{p_name}» не найден", "plugin_start", {"error": "not_found"}

    elif act_type == "plugin_stop":
        p_name = act.get("plugin_name", "")
        all_p = pm.list_plugins()
        matched = None
        for p in all_p:
            if p_name.lower() in p["name"].lower() or p_name.lower() in p["id"].lower():
                matched = p
                break
        if matched:
            res = pm.stop_plugin(matched["id"])
            return f"Плагин «{matched['name']}» остановлен", "plugin_stop", res
        return f"Локальный плагин «{p_name}» не найден", "plugin_stop", {"error": "not_found"}

    elif act_type == "plugin_list":
        plugins = pm.list_plugins()
        if not plugins:
            return "У вас пока нет установленных локальных плагинов. Загрузите скрипт во вкладке «Плагины».", "plugin_list", {"plugins": []}
        summary = ", ".join([f"{p['name']} [{p['status']}]" for p in plugins])
        return f"Локальные плагины на ПК: {summary}", "plugin_list", {"plugins": plugins}

    elif act_type == "create_file":
        path = act.get("path") or act.get("target") or "file.txt"
        content = act.get("content", "")
        res = sc.create_file(path, content)
        if res.get("success"):
            return f"Файл создан: {res.get('path')}", "create_file", res
        return f"Не удалось создать файл: {res.get('error')}", "create_file", res

    elif act_type == "create_folder":
        path = act.get("path") or act.get("target") or "Новая папка"
        res = sc.create_folder(path)
        if res.get("success"):
            return f"Папка создана: {res.get('path')}", "create_folder", res
        return f"Не удалось создать папку: {res.get('error')}", "create_folder", res

    elif act_type == "delete_file":
        path = act.get("path") or act.get("target") or ""
        res = sc.delete_file_or_folder(path)
        if res.get("success"):
            return f"Удалено: {res.get('path')}", "delete_file", res
        return f"Не удалось удалить: {res.get('error')}", "delete_file", res

    elif act_type == "analyze_file":
        path = act.get("path") or act.get("target") or ""
        res = sc.analyze_file(path)
        if res.get("success"):
            prev = f"\n```\n{res.get('preview')[:250]}\n```" if res.get('preview') else ""
            return f"Файл «{res.get('name')}» ({res.get('size_kb')} КБ, строк: {res.get('lines')}){prev}", "analyze_file", res
        return f"Не удалось проанализировать файл: {res.get('error')}", "analyze_file", res

    elif act_type == "list_files":
        folder = act.get("folder") or act.get("target") or "desktop"
        res = sc.list_folder_files(folder)
        if res.get("success"):
            files_list = ", ".join(res.get("files", [])[:12]) or "нет файлов"
            dirs_list = ", ".join(res.get("folders", [])[:6]) or "нет папок"
            return f"Содержимое папки {res.get('folder_name')} (всего {res.get('total')}):\n• Файлы: {files_list}\n• Папки: {dirs_list}", "list_files", res
        return f"Не удалось получить список файлов: {res.get('error')}", "list_files", res

    elif act_type == "math":
        res = act.get("res")
        return f"Результат вычисления: {res}", "math", act

    return "", "noop", {}

# ─── COMPREHENSIVE LOCAL INTENT MATCHER ─────────────────────────
APP_MAP = {
    # Browsers
    "chrome": "chrome", "хром": "chrome", "гугл хром": "chrome", "google chrome": "chrome",
    "браузер": "chrome", "browser": "chrome", "интернет": "chrome",
    "edge": "edge", "эдж": "edge", "msedge": "edge",
    "yandex": "yandex", "яндекс": "yandex", "яндекс браузер": "yandex",
    # Messengers & Social
    "telegram": "telegram", "телеграм": "telegram", "телега": "telegram", "тг": "telegram", "tg": "telegram",
    "discord": "discord", "дискорд": "discord", "диск": "discord", "дс": "discord", "dc": "discord",
    "steam": "steam", "стим": "steam",
    "spotify": "spotify", "спотифай": "spotify", "музыка": "spotify",
    "soundcloud": "soundcloud", "саундклауд": "soundcloud", "саунд клауд": "soundcloud", "sound cloud": "soundcloud",
    "yandex music": "yandex music", "яндекс музыка": "yandex music", "я музыка": "yandex music",
    # Productivity & Dev
    "vscode": "vscode", "vs code": "vscode", "код": "vscode", "вскод": "vscode", "visual studio code": "vscode",
    "goland": "goland", "go land": "goland", "голенд": "goland", "голэнд": "goland", "jetbrains goland": "goland",
    "pycharm": "pycharm", "py charm": "pycharm", "пайчарм": "pycharm", "jetbrains pycharm": "pycharm",
    "webstorm": "webstorm", "web storm": "webstorm", "вебшторм": "webstorm", "jetbrains webstorm": "webstorm",
    "postman": "postman", "post man": "postman", "постман": "postman",
    "calculator": "calculator", "калькулятор": "calculator", "кальк": "calculator", "calc": "calculator",
    "notepad": "notepad", "блокнот": "notepad", "текстовый редактор": "notepad",
    "paint": "paint", "пейнт": "paint", "паинт": "paint", "рисовалка": "paint",
    # System
    "task manager": "task manager", "taskmgr": "task manager", "диспетчер задач": "task manager",
    "диспетчер процессов": "task manager", "диспетчер": "task manager",
    "explorer": "explorer", "проводник": "explorer", "папки": "explorer", "файлы": "explorer",
    "мой компьютер": "explorer", "этот компьютер": "explorer",
    "terminal": "terminal", "терминал": "terminal", "консоль": "terminal",
    "powershell": "terminal", "cmd": "terminal", "командная строка": "terminal",
    "settings": "settings", "настройки": "settings", "параметры": "settings", "настройки винды": "settings",
    # Modern AI & Social Apps
    "deepseek": "deepseek", "deep seek": "deepseek", "дипсик": "deepseek", "дип сик": "deepseek",
    "tiktok": "tiktok", "тикток": "tiktok", "тик ток": "tiktok",
    "дикси": "дикси", "dixy": "дикси",
    "chatgpt": "chatgpt", "chat gpt": "chatgpt", "чатгпт": "chatgpt", "чат гпт": "chatgpt",
    "vk": "vk", "вк": "vk"
}

KNOWN_KEYBOARD_KEYS = {
    "enter", "return", "ввод", "ентер", "ентр",
    "esc", "escape", "эскейп",
    "tab", "таб",
    "space", "пробел",
    "backspace", "бэкспейс", "стереть",
    "delete", "делит",
    "up", "вверх", "стрелка вверх",
    "down", "вниз", "стрелка вниз",
    "left", "влево", "стрелка влево",
    "right", "вправо", "стрелка вправо",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "ctrl", "alt", "shift", "win", "windows"
}

def extract_youtube_query(text: str) -> str:
    """
    Cleans spoken YouTube commands to extract pure song/artist/topic query,
    preserving case while stripping preambles, action verbs, platform words, and generic descriptors.
    e.g. 'А включи на ютубе музыку Rock' -> 'Rock'
         'включи в ютубе рамштайн' -> 'рамштайн'
         'поставь на ютубе песню bohemian rhapsody' -> 'bohemian rhapsody'
         'найди на ютубе видео как настроить роутер' -> 'как настроить роутер'
    """
    q = text.strip()
    q = re.sub(r'^\s*(?:а\s+ну|а\s+ну-ка|а|ну-ка|ну|так|слушай|слушай-ка|эй|давай|пожалуйста|пж)[,\s:]+', '', q, flags=re.IGNORECASE).strip()
    q = re.sub(r'^\s*(?:аргус|argus)[,\s:]+', '', q, flags=re.IGNORECASE).strip()
    q = re.sub(r'^(?:включи|включить|поставь|поставить|запусти|запустить|вруби|врубить|сыграй|сыграть|найди|найти|поищи|поискать|покажи|показать|открой|открыть|послушай|послушать|play|search)\s+', '', q, flags=re.IGNORECASE).strip()
    q = re.sub(r'\b(?:в|на|через|по)?\s*(?:ютуб[еауи]?|youtube|в\s+ютубе|на\s+ютубе|на\s+youtube|в\s+youtube)\b', '', q, flags=re.IGNORECASE).strip()
    q = re.sub(r'^(?:включи|включить|поставь|поставить|запусти|запустить|вруби|врубить|сыграй|сыграть|найди|найти|поищи|поискать|покажи|показать|открой|открыть|послушай|послушать|play|search)\s+', '', q, flags=re.IGNORECASE).strip()
    q = re.sub(r'^(?:музыку|музыка|песню|песня|трек|композицию|клип|видео|ролик|плейлист|фильм|сериал)\s+', '', q, flags=re.IGNORECASE).strip()
    q = re.sub(r'\s+(?:на\s+ютубе|в\s+ютубе|на\s+youtube|в\s+youtube)$', '', q, flags=re.IGNORECASE).strip()
    q = q.strip('"\'«» .,:;!?')
    return q

def clean_clause_text(text: str) -> str:
    """Removes polite filler words, Russian/English profanity, introductory particles, and normalizes brand names."""
    t = text.lower().strip()
    
    # Strip leading bot address
    t = re.sub(r'^\s*(?:аргус|argus|эй\s+аргус|эй|слушай|слушай\s+аргус|бот|ассистент)[,\s:]+', '', t, flags=re.IGNORECASE)

    # Strip introductory conversational prefixes e.g. "а ", "а ну ", "ну-ка ", "так ", "слушай "
    t = re.sub(r'^\s*(?:а\s+ну\s+|а\s+ну-ка\s+|а\s+|ну-ка\s+|ну\s+|так\s+|слушай\s+|слушай-ка\s+|эй\s+|давай\s+)', '', t, flags=re.IGNORECASE)

    # Profanity and fillers removal (never let swearing break command intent or become an app name)
    fillers = [
        r'\bпожалуйста\b', r'\bпж\b', r'\bплиз\b', r'\bplease\b',
        r'\bсейчас\b', r'\bбыстро\b', r'\bсрочно\b', r'\bблин\b',
        r'\bтам\b', r'\bтут\b', r'\bздесь\b',
        r'\bмне\b', r'\bнам\b', r'\bты\b', r'\bже\b', r'\bка\b', r'\bну-ка\b', r'\bдавай\b',
        r'\bможешь\b', r'\bможешь ли\b', r'\bсможешь\b', r'\bхочу\b', r'\bхотел бы\b',
        r'\bнужно\b', r'\bнадо\b', r'\bпопробуй\b', r'\bбудь добр\b',
        # Russian profanities & abusive words
        r'\bдолбо[её]б(?:а|у|ом|ы|ов)?\b', r'\bдолба[её]б(?:а|у|ом|ы|ов)?\b',
        r'\bблять?\b', r'\bблядь\b', r'\bбля\b', r'\bнахуй\b', r'\bнах\b', r'\bпохуй\b',
        r'\bсука\b', r'\bсуки\b', r'\bпид[оа]р(?:ас|аз)?(?:а|у|ом|ы|ов)?\b',
        r'\bг[оа]ндон(?:а|у|ом|ы)?\b', r'\b[её]бан(?:ый|ая|ое|ые|ого)?\b', r'\b[её]бать\b',
        r'\bза[её]бал(?:а|и)?\b', r'\bхуй(?:ня|ни|ню|нем|не|я)?\b', r'\bхер(?:ня|ни)?\b',
        r'\bмудак(?:а|у|ом|и)?\b', r'\bмудила\b', r'\bдебил(?:а|у|ом|ы)?\b',
        r'\bидиот(?:а|у|ом|ы)?\b', r'\bпридурок(?:а|у|ом|и)?\b',
        # English profanities
        r'\bfuck(?:ing|er)?\b', r'\bshit\b', r'\bbitch\b', r'\basshole\b', r'\bdick\b'
    ]
    for pattern in fillers:
        t = re.sub(pattern, '', t, flags=re.IGNORECASE)

    # Normalize popular brand synonyms
    t = re.sub(r'\b(?:deep\s*seek\w*|дип\s*сик\w*)\b', 'deepseek', t, flags=re.IGNORECASE)
    t = re.sub(r'\b(?:тик\s*ток)\b', 'tiktok', t, flags=re.IGNORECASE)
    t = re.sub(r'\b(?:чат\s*гпт|chat\s*gpt)\b', 'chatgpt', t, flags=re.IGNORECASE)

    return re.sub(r'\s+', ' ', t).strip()

def parse_single_clause(clause: str) -> Optional[Dict[str, Any]]:
    """
    Parses an individual action clause locally with support for
    infinitives, imperatives, colloquial words, negative filters, and slang.
    """
    orig_c = clause.strip()
    clean_orig_c = re.sub(r'^\s*(?:а\s+ну\s+|а\s+ну-ка\s+|а\s+|ну-ка\s+|ну\s+|так\s+|слушай\s+|слушай-ка\s+|эй\s+|давай\s+)', '', orig_c, flags=re.IGNORECASE).strip()
    raw_c = clean_orig_c.lower()
    c = clean_clause_text(raw_c)
    if not c:
        return None

    # 0. Global Coding Guard: Requests to write code, bots, programs, or scripts must NEVER be hijacked by messengers!
    coding_verbs = ["напиши", "написать", "создай", "создать", "сделай", "сделать", "сгенерируй", "покажи", "напишите", "write", "create", "generate"]
    coding_nouns = ["код", "скрипт", "программ", "функци", "класс", "алгоритм", "бота", "бот ", "парсер", "сервер", "приложение на"]
    coding_langs = ["node", "nodejs", "node.js", "js", "javascript", "python", "питон", "typescript", "ts", "c++", "c#", "java", "джав", "go", "golang", "rust", "html", "css", "sql", "php"]
    if (any(n in c for n in coding_nouns) and (any(v in c for v in coding_verbs) or any(l in c for l in coding_langs))) or ("бот на" in c or "бота на" in c or "телеграм бота" in c or "telegram bot" in c or "телеграм бот" in c):
        return None

    # 0. "Закрой все кроме X" (Negative Exclusion Filter)
    if any(k in c for k in ["кроме", "except", "не закрывай", "за исключением"]):
        if any(v in c for k in ["закрой", "закрыть", "выключи", "выключить", "убей", "заверши"] for v in [k]):
            # Find what to keep
            keep_list = []
            for alias, canonical in APP_MAP.items():
                if alias in c:
                    keep_list.append(canonical)
            if keep_list:
                return {"type": "close_all_except", "keep": list(set(keep_list))}

    # 0.6 Extras: Timers, Tasks, Notes, Reminders
    # Timer e.g. "поставь таймер на 7 минут сделать дз", "таймер на 7 минут сделать дз", "таймер 5 минут", "напомни через 10 минут сделать дз"
    m_timer = re.match(
        r'^(?:поставь|поставить|запусти|запустить|включи|включить|установи|установить|сделай|сделать|создай|создать|заведи|завести|засеки|засечь|новый|новая)?\s*(?:мне\s+)?(?:таймер(?:\s+на)?|на)?\s*(\d+)\s*(минут\w*|мин|м|секунд\w*|сек|с|час\w*|ч)?(?:\s+(?:на|чтобы|для|сделать|выполнить)?\s*(.*))?$',
        c, re.IGNORECASE
    )
    if m_timer:
        val = int(m_timer.group(1))
        unit = (m_timer.group(2) or "мин").lower()
        task_label = (m_timer.group(3) or "").strip()
        secs = val * 60
        if "сек" in unit:
            secs = val
        elif "час" in unit or unit == "ч":
            secs = val * 3600
        clean_label = re.sub(r'^(?:на|чтобы|для|сделать|выполнить)\s+', '', task_label, flags=re.IGNORECASE).strip()
        title_disp = clean_label.capitalize() if clean_label else "Таймер"
        try:
            extras_mgr.add_timer(title_disp, secs)
        except Exception:
            pass
        mins_disp = f"{val} мин" if "мин" in unit else f"{val} сек" if "сек" in unit else f"{val} ч"
        msg = f"Таймер на {mins_disp} для «{title_disp}» успешно запущен, сэр. Я напомню вам голосом, когда время истечёт."
        return {"type": "create_timer", "title": title_disp, "seconds": secs, "message": msg}

    # Reminder e.g. "напомни через 7 минут сделать дз", "напомни через 10 минут выключить духовку"
    m_remind = re.match(
        r'^(?:напомни|напомнить)(?:\s+мне)?\s+через\s+(\d+)\s*(минут\w*|мин|секунд\w*|сек|час\w*|ч)\s+(?:что\s+|чтобы\s+|по\s+|о\s+том\s+что\s+)?(.*)$',
        c, re.IGNORECASE
    )
    if m_remind:
        val = int(m_remind.group(1))
        unit = (m_remind.group(2) or "мин").lower()
        task_label = (m_remind.group(3) or "").strip()
        secs = val * 60
        if "сек" in unit:
            secs = val
        elif "час" in unit or unit == "ч":
            secs = val * 3600
        clean_label = re.sub(r'^(?:на|чтобы|для|сделать|выполнить)\s+', '', task_label, flags=re.IGNORECASE).strip()
        title_disp = clean_label.capitalize() if clean_label else "Напоминание"
        try:
            extras_mgr.add_timer(title_disp, secs)
        except Exception:
            pass
        mins_disp = f"{val} мин" if "мин" in unit else f"{val} сек" if "сек" in unit else f"{val} ч"
        msg = f"Напоминание установлено на {mins_disp} для «{title_disp}», сэр. Я озвучу его сразу, как только время пройдёт."
        return {"type": "create_timer", "title": title_disp, "seconds": secs, "message": msg}

    # Task creation e.g. "добавь задачу сделать дз", "создай задачу купить хлеб"
    m_task = re.match(
        r'^(?:добавь|создай|запиши|новая)?\s*задач[ауие]?[:\s]+(.*)$',
        c, re.IGNORECASE
    )
    if m_task and not any(k in c for k in ["реши", "математик", "алгебр"]):
        raw_task = m_task.group(1).strip()
        clean_t = re.sub(r'^(?:на|чтобы|для|сделать|выполнить)\s+', '', raw_task, flags=re.IGNORECASE).strip()
        if clean_t:
            title_disp = clean_t.capitalize()
            try:
                    extras_mgr.add_task(title_disp)
            except Exception:
                pass
            msg = f"Задача «{title_disp}» успешно добавлена в меню Дополнительно, сэр."
            return {"type": "create_task", "title": title_disp, "message": msg}

    # Note creation e.g. "создай заметку купить хлеб", "запиши заметку номер телефона 123"
    m_note = re.match(
        r'^(?:добавь|создай|запиши|новая)?\s*заметк[ауие]?[:\s]+(.*)$',
        c, re.IGNORECASE
    )
    if m_note:
        raw_note = m_note.group(1).strip()
        if raw_note:
            title_disp = raw_note.capitalize()
            try:
                    extras_mgr.add_note(title_disp, raw_note)
            except Exception:
                pass
            msg = f"Заметка «{title_disp}» успешно сохранена в меню Дополнительно, сэр."
            return {"type": "create_note", "title": title_disp, "content": raw_note, "message": msg}

    # Task completion e.g. "выполнил задачу сделать дз", "заверши задачу сделать дз", "отметь задачу сделать дз выполненной", "сделал задачу ..."
    m_comp_task = re.match(
        r'^(?:выполнил|выполнена|заверши|завершил|отметь(?:\s+как)?(?:\s+выполненн\w*)?|сделал)\s+(?:задачу|задание)\s+(.*)$',
        c, re.IGNORECASE
    )
    if m_comp_task:
        target_t = m_comp_task.group(1).strip()
        target_t = re.sub(r'^(?:как\s+)?(?:выполненн\w*|сделанн\w*)\s*', '', target_t, flags=re.IGNORECASE).strip()
        target_t = re.sub(r'\s+(?:как\s+)?(?:выполненн\w*|сделанн\w*)$', '', target_t, flags=re.IGNORECASE).strip()
        ok, found = extras_mgr.complete_task(target_t)
        t_name = found.get("title") if found else target_t.capitalize()
        msg = f"Задача «{t_name}» успешно отмечена как выполненная, сэр." if ok else f"Задача «{target_t}» не найдена в списке, сэр."
        return {"type": "complete_task", "title": target_t, "message": msg}

    # Task deletion e.g. "удали задачу сделать дз", "удали из задач сделать дз", "стереть задачу ..."
    m_del_task = re.match(
        r'^(?:удали|удалить|сотри|стереть|убери|убрать)\s+(?:из\s+задач\s+|задачу\s+)(.*)$',
        c, re.IGNORECASE
    )
    if m_del_task:
        target_t = m_del_task.group(1).strip()
        ok, found = extras_mgr.delete_task(target_t)
        t_name = found.get("title") if found else target_t.capitalize()
        msg = f"Задача «{t_name}» успешно удалена из вашего списка задач, сэр." if ok else f"Задача «{target_t}» не найдена в вашем списке задач, сэр."
        return {"type": "delete_task", "title": target_t, "message": msg}

    # Note deletion e.g. "удали заметку про роутер", "удали из заметок пароль", "сотри заметку ..."
    m_del_note = re.match(
        r'^(?:удали|удалить|сотри|стереть|убери|убрать)\s+(?:из\s+заметок\s+|заметку\s+)(.*)$',
        c, re.IGNORECASE
    )
    if m_del_note:
        target_n = m_del_note.group(1).strip()
        ok, found = extras_mgr.delete_note(target_n)
        n_name = found.get("title") if found else target_n.capitalize()
        msg = f"Заметка «{n_name}» успешно удалена, сэр." if ok else f"Заметка «{target_n}» не найдена, сэр."
        return {"type": "delete_note", "title": target_n, "message": msg}

    # Timer deletion e.g. "удали таймер", "останови таймер", "отмени таймер", "выключи таймер", "сбрось таймер"
    m_del_timer = re.match(
        r'^(?:удали|удалить|останови|остановить|отмени|отменить|выключи|выключить|сбрось|сбросить)\s+(?:все\s+)?таймер\w*(?:\s+(.*))?$',
        c, re.IGNORECASE
    )
    if m_del_timer:
        target_tm = (m_del_timer.group(1) or "all").strip()
        ok, found = extras_mgr.delete_timer(target_tm)
        msg = "Таймер успешно остановлен и удалён, сэр." if ok else "Активный таймер не найден, сэр."
        return {"type": "delete_timer", "title": target_tm, "message": msg}

    # List tasks e.g. "покажи задачи", "какие задачи", "список задач", "что по задачам"
    if any(k == c or c.startswith(k) for k in [
        "покажи задачи", "какие задачи", "какие у меня задачи", "список задач",
        "мои задачи", "что по задачам", "посмотреть задачи"
    ]):
        data = extras_mgr.load_extras_data()
        tasks = data.get("tasks", [])
        if not tasks:
            msg = "У вас пока нет сохранённых задач, сэр."
        else:
            lines = [f"• {'[✓]' if t.get('completed') else '[ ]'} {t.get('title')}" for t in tasks[:8]]
            msg = "Ваши текущие задачи, сэр:\n" + "\n".join(lines)
        return {"type": "list_tasks", "message": msg}

    # Smart Search / Questions about personal notes (checked before generic listing):
    # e.g. "что в заметках про проект", "найди в заметках пароль", "какой пароль от роутера", "где мои ключи", "что я записал про..."
    m_search_note = re.match(
        r'^(?:найди|поищи|что|подскажи|скажи)?\s*(?:у\s+меня\s+)?(?:в\s+заметках\s+|в\s+моих\s+заметках\s+)(?:про\s+|о\s+|по\s+поводу\s+)?(.+)$',
        c, re.IGNORECASE
    )
    is_personal_q = bool(m_search_note and m_search_note.group(1).strip()) or any(c.startswith(k) for k in ["какой пароль", "где мои", "где мой", "когда др", "когда день рождения", "что я записал"])
    if is_personal_q:
        q_target = m_search_note.group(1).strip() if (m_search_note and m_search_note.group(1).strip()) else c
        matches = extras_mgr.search_notes(q_target)
        if matches:
            best = matches[0]
            msg = f"Судя по вашей заметке «{best.get('title')}», сэр:\n{best.get('content')}"
            return {"type": "search_notes", "query": q_target, "message": msg}
        elif m_search_note:
            msg = f"В ваших заметках не найдено информации по запросу «{q_target}», сэр."
            return {"type": "search_notes", "query": q_target, "message": msg}

    # List notes e.g. "покажи заметки", "какие заметки", "список заметок"
    if any(k == c or c.startswith(k + " ") for k in [
        "покажи заметки", "какие заметки", "какие у меня заметки", "список заметок",
        "мои заметки", "что в заметках", "посмотреть заметки", "все заметки"
    ]) and not is_personal_q:
        data = extras_mgr.load_extras_data()
        notes = data.get("notes", [])
        if not notes:
            msg = "В ваших заметках пока пусто, сэр."
        else:
            lines = [f"• «{n.get('title')}»: {n.get('content')[:60]}" for n in notes[:8]]
            msg = "Ваши сохранённые заметки, сэр:\n" + "\n".join(lines)
        return {"type": "list_notes", "message": msg}

    # List timers e.g. "покажи таймеры", "активные таймеры"
    if any(k == c or c.startswith(k + " ") for k in [
        "покажи таймеры", "какие таймеры", "активные таймеры", "список таймеров"
    ]):
        data = extras_mgr.load_extras_data()
        timers = [t for t in data.get("timers", []) if t.get("is_running") and t.get("remaining_seconds", 0) > 0]
        if not timers:
            msg = "Сейчас нет активных таймеров, сэр."
        else:
            lines = [f"• «{t.get('title')}»: осталось {t.get('remaining_seconds')} сек." for t in timers]
            msg = "Активные таймеры, сэр:\n" + "\n".join(lines)
        return {"type": "list_timers", "message": msg}

    # 1. Screenshot / Screen capture with folder detection
    if any(k in c for k in [
        "скрин", "скриншот", "снимок экрана", "сфоткай экран", "снять экран",
        "заскринь", "заскринить", "сфоткать", "screenshot", "screen shot", "print screen"
    ]):
        folder = "desktop"
        if any(f in c for f in ["загрузк", "загруз", "download"]):
            folder = "downloads"
        elif any(f in c for f in ["документ", "document"]):
            folder = "documents"
        elif any(f in c for f in ["изображен", "картинк", "picture"]):
            folder = "pictures"
        return {"type": "screenshot", "folder": folder}

    # 1.1 Save destination specification (e.g. "сохрани его в папку загрузки")
    if any(k in c for k in ["сохрани", "сохранить", "save"]) and not any(k in c for k in ["файл", "file", "код", "папку", "папка", "создай", "создать"]):
        folder = "desktop"
        if any(f in c for f in ["загрузк", "загруз", "download"]):
            folder = "downloads"
        elif any(f in c for f in ["документ", "document"]):
            folder = "documents"
        elif any(f in c for f in ["изображен", "картинк", "picture"]):
            folder = "pictures"
        return {"type": "save_destination", "folder": folder}

    # 1.1 App-specific Minimize ("сверни телеграм", "скрой хром", "убери дискорд", "смахни телеграм", etc.)
    minimize_verbs = ["сверни", "смахни", "убери", "скрой", "свернуть", "смахнуть", "убрать", "скрыть", "спрячь", "спрятать"]
    if any(verb in c for verb in minimize_verbs):
        for alias in sorted(APP_MAP.keys(), key=lambda x: len(x), reverse=True):
            if alias in ["все", "всё", "окна", "вкладки", "окно", "вкладка", "страницу", "интернет"]:
                continue
            pattern = r'(?:\b|^)' + re.escape(alias) + r'(?:\b|$)'
            if re.search(pattern, c):
                return {"type": "minimize_app", "app": APP_MAP[alias]}

    # 1.2 Window Minimize (смахнуть = swipe away / dismiss = minimize, NOT close)
    # "смахни вкладки" / "махни вкладки" / "убери окна" = minimize windows (NOT close browser tabs!)
    # Only "закрой вкладку/вкладки" = close browser tab(s)
    if any(k in c for k in [
        "смахни вкладки", "махни вкладки", "смахни все вкладки", "махни все вкладки",
        "смахни окна", "махни окна", "смахни все окна", "махни все окна",
        "убери вкладки", "убери окна", "убрать вкладки", "убрать окна",
        "сверни все", "сверни всё", "сверни окна", "сверни вкладки",
        "minimize all", "show desktop", "покажи рабочий стол"
    ]):
        return {"type": "minimize_all_windows"}
    if any(k in c for k in [
        "смахни вкладку", "махни вкладку", "смахни эту вкладку", "махни эту вкладку",
        "смахни окно", "махни окно", "смахни это окно", "махни это окно",
        "смахнуть вкладку", "смахни страницу", "махни страницу",
        "убери вкладку", "убери окно", "убрать вкладку",
        "сверни", "сверни окно", "сверни вкладку", "сверни это", "сверни приложение",
        "minimize", "minimize window"
    ]):
        return {"type": "minimize_window"}

    # 1.25 YouTube in-browser playback controls
    if any(k in c for k in ["ютуб", "youtube", "видео", "ролик"]):
        # Pause / Play
        if any(k in c for k in ["пауза", "паузу", "останови видео", "останови ролик", "стоп видео", "видео на паузу"]):
            return {"type": "youtube_control", "action": "play_pause"}
        if any(k in c for k in ["продолжи", "возобнови", "сними с паузы", "воспроизведение", "плей"]) and any(k in c for k in ["видео", "ролик", "ютуб", "youtube"]):
            return {"type": "youtube_control", "action": "play_pause"}
        # Mute
        if any(k in c for k in ["без звука", "выключи звук", "заглуши", "включи звук", "верни звук"]) and any(k in c for k in ["ютуб", "youtube", "видео", "ролик"]):
            return {"type": "youtube_control", "action": "mute"}
        # Fullscreen
        if any(k in c for k in ["на весь экран", "полный экран", "разверни видео", "во весь экран", "полноэкранный"]):
            return {"type": "youtube_control", "action": "fullscreen"}
        # Next / Prev
        if any(k in c for k in ["следующее видео", "следующий ролик", "включи следующее", "next video"]):
            return {"type": "youtube_control", "action": "next"}
        if any(k in c for k in ["предыдущее видео", "предыдущий ролик", "прошлое видео", "prev video"]):
            return {"type": "youtube_control", "action": "prev"}
        # Rewind / Fast-forward
        if any(k in c for k in ["перемотай вперед", "перемотай вперёд", "на 10 секунд вперед", "на 10 секунд вперёд", "перемотай ролик вперед", "перемотай видео вперед"]):
            return {"type": "youtube_control", "action": "seek_forward"}
        if any(k in c for k in ["перемотай назад", "на 10 секунд назад", "перемотай ролик назад", "перемотай видео назад"]):
            return {"type": "youtube_control", "action": "seek_backward"}
        # Subtitles
        if any(k in c for k in ["субтитры", "субтитров", "включи субтитры", "выключи субтитры"]):
            return {"type": "youtube_control", "action": "subtitles"}
        # Speed
        if any(k in c for k in ["ускорь", "быстрее видео", "увеличь скорость", "ускорить видео"]):
            return {"type": "youtube_control", "action": "speed_up"}
        if any(k in c for k in ["замедли", "медленнее видео", "уменьши скорость", "замедлить видео"]):
            return {"type": "youtube_control", "action": "speed_down"}

    # 1.28 Specific Browser Tab Close ("закрой вкладку дипсик", "закрой ютуб в браузере", "закрой вкладку deepseek")
    m_close_tab = re.search(
        r'(?:закрой|закрыть|прикрой|прикрыть)\s+(?:там\s+|тут\s+|здесь\s+|пожалуйста\s+)?(?:вкладку\s+(?:с\s+|в\s+|под\s+названием\s+)?|страницу\s+(?:с\s+|в\s+)?|сайт\s+)?([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)(?:\s+в\s+браузере)?',
        c, re.IGNORECASE
    )
    if m_close_tab and any(k in c for k in ["вкладк", "страниц", "браузер", "ютуб", "youtube", "дипсик", "deepseek", "чатгпт", "chatgpt", "вк", "vk", "яндекс", "yandex", "гитхаб", "github", "почт"]):
        matched_target = m_close_tab.group(1).lower().strip()
        if matched_target in ["там", "тут", "здесь", "пожалуйста"]:
            m_after = re.search(r'(?:вкладку\s+(?:с\s+|в\s+)?|страницу\s+(?:с\s+|в\s+)?|сайт\s+)([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)', c, re.IGNORECASE)
            if m_after:
                matched_target = m_after.group(1).lower().strip()
        if matched_target not in ["все", "всё", "браузер", "вкладку", "страницу", "окно", "это", "эту", "там", "тут"]:
            return {"type": "close_specific_browser_tab", "target": matched_target}

    # 1.3 Browser Tab Close (только "закрой" = close, НЕ "смахни")
    if any(k in c for k in [
        "закрой все вкладки", "закрыть все вкладки", "закрой все вкладки браузера",
        "закрыть все вкладки браузера", "прикрой все вкладки", "close all tabs", "close tabs"
    ]):
        return {"type": "close_all_browser_tabs"}
    if any(k in c for k in [
        "закрой вкладку", "закрыть вкладку", "закрой эту вкладку", "закрыть эту вкладку",
        "прикрой вкладку", "закрой текущую вкладку",
        "закрой страницу", "закрыть страницу", "close tab",
        "закрой вкладку браузера", "закрыть вкладку браузера"
    ]):
        return {"type": "close_browser_tab"}
    if any(k in c for k in ["новая вкладка", "новую вкладку", "открой вкладку", "открыть новую вкладку", "new tab"]):
        return {"type": "new_browser_tab"}
    if any(k in c for k in [
        "верни вкладку", "вернуть вкладку", "верни закрытую", "вернуть закрытую",
        "верни закрытую вкладку", "вернуть закрытую вкладку", "восстанови закрытую",
        "восстанови вкладку", "восстановить вкладку", "восстанови закрытую вкладку",
        "открой закрытую вкладку", "открыть закрытую вкладку", "открой последнюю вкладку",
        "reopen tab", "restore tab"
    ]):
        return {"type": "reopen_browser_tab"}
    if any(k in c for k in ["обнови страницу", "обновить страницу", "перезагрузи страницу", "обнови вкладку", "refresh page", "reload page"]):
        return {"type": "refresh_page"}
    if any(k in c for k in ["следующая вкладка", "следующую вкладку", "переключи вкладку", "переключить вкладку", "next tab"]):
        return {"type": "switch_browser_tab", "direction": "next"}
    if any(k in c for k in ["предыдущая вкладка", "предыдущую вкладку", "prev tab", "previous tab"]):
        return {"type": "switch_browser_tab", "direction": "prev"}
    if any(k in c for k in ["скролл вниз", "прокрути вниз", "прокрутить вниз", "листай вниз", "scroll down"]):
        return {"type": "scroll_page", "direction": "down"}
    if any(k in c for k in ["скролл вверх", "прокрути вверх", "прокрутить вверх", "листай вверх", "scroll up"]):
        return {"type": "scroll_page", "direction": "up"}
    if any(k in c for k in ["в самый верх", "вверх страницы", "в начало страницы", "скролл в начало"]):
        return {"type": "scroll_browser_to", "position": "top"}
    if any(k in c for k in ["в самый низ", "вниз страницы", "в конец страницы", "скролл в конец"]):
        return {"type": "scroll_browser_to", "position": "bottom"}

    # Browser search in page
    if any(k in c for k in ["найди на странице", "поиск на странице", "найди в браузере", "поиск по странице", "найди на сайте", "find on page"]):
        m_find = re.search(r'(?:найди\s+на\s+странице|поиск\s+на\s+странице|найди\s+в\s+браузере|поиск\s+по\s+странице|найди\s+на\s+сайте|find\s+on\s+page)\s*(.+)?', orig_c, re.IGNORECASE)
        q_find = m_find.group(1).strip() if m_find and m_find.group(1) else ""
        return {"type": "find_in_browser_page", "query": q_find}

    # Browser zoom
    if any(k in c for k in ["увеличь масштаб", "приблизь страницу", "крупнее текст в браузере", "zoom in"]):
        return {"type": "zoom_browser_page", "direction": "in"}
    if any(k in c for k in ["уменьши масштаб", "отдали страницу", "мельче текст в браузере", "zoom out"]):
        return {"type": "zoom_browser_page", "direction": "out"}
    if any(k in c for k in ["сбрось масштаб", "сбросить масштаб", "стандартный масштаб", "масштаб 100", "reset zoom"]):
        return {"type": "zoom_browser_page", "direction": "reset"}

    # Browser features (history, downloads, bookmarks, incognito)
    if any(k in c for k in ["история браузера", "открой историю в браузере", "покажи историю браузера", "browser history"]):
        return {"type": "open_browser_feature", "feature": "history"}
    if any(k in c for k in ["загрузки в браузере", "открой загрузки браузера", "покажи загрузки в браузере", "browser downloads"]):
        return {"type": "open_browser_feature", "feature": "downloads"}
    if any(k in c for k in ["добавь в закладки", "добавить в закладки", "сохрани страницу в закладки", "сохрани в закладки", "bookmark page"]):
        return {"type": "open_browser_feature", "feature": "bookmarks"}
    if any(k in c for k in ["режим инкогнито", "открой инкогнито", "приватное окно", "приватный режим", "incognito"]):
        return {"type": "open_browser_feature", "feature": "incognito"}

    # Browser navigation back / forward
    if any(k in c for k in ["страница назад", "назад в браузере", "вернись назад в браузере", "go back"]):
        return {"type": "navigate_browser_history", "direction": "back"}
    if any(k in c for k in ["страница вперед", "страница вперёд", "вперед в браузере", "вперёд в браузере", "go forward"]):
        return {"type": "navigate_browser_history", "direction": "forward"}
        return {"type": "scroll_page", "direction": "up"}

    # 1.3 Click button / link / element on website or app, or press key
    btn_m = re.match(r'^(?:нажми\s+(?:на\s+кнопку|кнопку|на\s+ссылку|ссылку|на|по)?|кликни\s+(?:на\s+кнопку|кнопку|по\s+кнопке|на\s+ссылку|по\s+ссылке|ссылку|на|по)?|click\s+(?:on\s+button|button|on\s+link|link|on)?)\s*(.+)$', c)
    if btn_m:
        target = btn_m.group(1).strip().strip('"\'')
        target = re.sub(r'^(?:там|тут|здесь|пожалуйста)\s+', '', target, flags=re.IGNORECASE).strip()
        target = re.sub(r'\s+(?:на\s+сайте|в\s+браузере|на\s+странице)$', '', target).strip()
        target_lower = target.lower()
        if "+" in target_lower and all(len(p.strip()) <= 8 for p in target_lower.split("+")):
            return {"type": "hotkey", "keys": [k.strip() for k in target_lower.split("+")]}
        if target_lower in KNOWN_KEYBOARD_KEYS:
            key_mapped = "enter" if target_lower in ["ентер", "ввод", "ентр", "return"] else \
                         "esc" if target_lower in ["эскейп", "escape"] else \
                         "tab" if target_lower in ["таб"] else \
                         "space" if target_lower in ["пробел"] else \
                         "backspace" if target_lower in ["бэкспейс", "стереть"] else target_lower
            return {"type": "press_key", "key": key_mapped}
        if target:
            return {"type": "click_website_button", "button": target}

    # 1.4 Terminal Execution (PowerShell, Bash, CMD)
    if any(c.startswith(k) for k in ["в терминале:", "в терминале ", "терминал:", "терминал ", "команда:", "powershell:", "bash:"]):
        cmd_text = re.sub(r'^(?:выполни\s+)?(?:в\s+терминале|терминал|команда|powershell|bash)[:\s]+', '', raw_c).strip()
        shell_choice = "bash" if "bash" in c else "powershell"
        if cmd_text:
            return {"type": "terminal_command", "command": cmd_text, "shell": shell_choice}

    # 2. Close / Kill applications
    if any(k in c for k in [
        "закрой", "закрыть", "выключи", "выключить", "убей", "прибей",
        "заверши", "завершить", "close", "kill", "exit", "quit"
    ]):
        if any(k in c for k in ["ютуб", "youtube", "саундклауд", "soundcloud", "вкладку", "страницу", "сайт"]):
            return {"type": "close_browser_tab"}
        if any(k in c for k in ["приложение", "программу", "окно", "текущее", "this window", "this app"]):
            return {"type": "close_active_window"}
        for app_alias, app_canonical in APP_MAP.items():
            if app_alias in c:
                return {"type": "close_app", "app": app_canonical}

    # 3. Recycle Bin
    if any(k in c for k in [
        "очисти корзину", "очистить корзину", "почисти корзину", "почистить корзину",
        "опустоши корзину", "опустошить корзину", "удали корзину", "empty recycle", "clean recycle"
    ]):
        return {"type": "empty_recycle"}

    # 4. Lock PC
    if any(k in c for k in [
        "заблокируй", "заблокировать", "залочь", "залочить",
        "lock pc", "lock computer", "экран блокировки"
    ]):
        return {"type": "lock_pc"}

    # 5. Power Commands
    if any(k in c for k in ["выключи пк", "выключить пк", "выключи компьютер", "выключить компьютер", "shutdown pc", "power off"]):
        return {"type": "power", "action": "shutdown"}
    if any(k in c for k in ["перезагрузи пк", "перезагрузить пк", "перезагрузи компьютер", "restart pc", "reboot"]):
        return {"type": "power", "action": "restart"}
    if any(k in c for k in ["отмени выключение", "не выключай", "cancel shutdown", "abort shutdown"]):
        return {"type": "power", "action": "cancel"}

    # 6. Volume Control
    if any(k in c for k in ["volume", "sound", "громкост", "звук", "тише", "громче", "мут", "заглуши", "размут"]):
        if any(k in c for k in ["выключи звук", "выключить звук", "без звука", "заглуши", "мут", "mute"]):
            return {"type": "volume_mute"}
        if any(k in c for k in ["включи звук", "включить звук", "размут", "unmute"]):
            return {"type": "volume_mute"}

        if any(k in c for k in ["максимум", "на всю", "на полную", "полную", "полная", "на максимум", "100%", "сто", "на сотку", "максимальн"]):
            return {"type": "volume_set", "level": 100}
        if any(k in c for k in ["минимум", "на минимум", "на ноль", "на 0", "ноль", "в ноль", "минимальн"]):
            return {"type": "volume_set", "level": 0}
        if any(k in c for k in ["наполовину", "половина", "на 50", "средн"]):
            return {"type": "volume_set", "level": 50}

        m_num = re.search(r'\b(\d{1,3})\b', c)
        num = int(m_num.group(1)) if m_num else None

        if any(k in c for k in ["прибавь", "прибавить", "громче", "погромче", "увелич", "увеличить", "up", "louder", "increase"]):
            return {"type": "volume_change", "delta": num or 15}
        if any(k in c for k in ["убавь", "убавить", "тише", "потише", "снизь", "снизить", "уменьши", "уменьшить", "down", "quieter", "decrease"]):
            return {"type": "volume_change", "delta": -(num or 15)}
        if num is not None:
            return {"type": "volume_set", "level": num}

    # 7. Brightness Control
    if any(k in c for k in ["яркост", "подсветк", "brightness", "экран"]):
        if any(k in c for k in ["максимум", "на всю", "на полную", "полную", "полная", "на максимум", "100%", "сто", "на сотку", "максимальн"]):
            return {"type": "brightness_set", "level": 100}
        if any(k in c for k in ["минимум", "на минимум", "на ноль", "на 0", "ноль", "в ноль", "минимальн"]):
            return {"type": "brightness_set", "level": 10}
        if any(k in c for k in ["наполовину", "половина", "на 50", "средн"]):
            return {"type": "brightness_set", "level": 50}

        m_num = re.search(r'\b(\d{1,3})\b', c)
        num = int(m_num.group(1)) if m_num else None

        if any(k in c for k in ["прибавь", "прибавить", "ярче", "поярче", "увелич", "увеличить", "up", "brighter"]):
            return {"type": "brightness_change", "delta": num or 15}
        if any(k in c for k in ["убавь", "убавить", "темнее", "потемнее", "снизь", "снизить", "уменьши", "уменьшить", "down", "darker"]):
            return {"type": "brightness_change", "delta": -(num or 15)}
        if num is not None:
            return {"type": "brightness_set", "level": num}

    # 7.1 File & Directory Operations (Create, Delete, Inspect, List)
    # Create file: "создай файл notes.txt с текстом Привет на рабочем столе"
    if any(k in c for k in ["создай файл", "создать файл", "сделай файл", "сохрани в файл", "запиши файл", "create file"]):
        m_cf = re.search(r'(?:создай|создать|сделай|запиши)\s+(?:текстовый\s+)?файл\s+([^\s]+)(?:\s+(?:с\s+текстом|с\s+содержимым|текст)?\s+(.+?))?(?:\s+(?:на\s+рабочем\s+столе|в\s+загрузках|в\s+документах))?$', raw_c, re.IGNORECASE)
        target = "file.txt"
        content = ""
        if m_cf:
            target = m_cf.group(1).strip('"\'«»')
            if m_cf.group(2):
                content = m_cf.group(2).strip().strip('"\'«»')
        else:
            parts = c.split()
            for p in parts:
                if "." in p and len(p) > 2:
                    target = p.strip('"\'«»')
                    break
        if "на рабочем столе" in c or "на рабочий стол" in c or "desktop" in c:
            target = "на рабочем столе " + target
        elif "в загрузках" in c or "в загрузки" in c or "downloads" in c:
            target = "в загрузках " + target
        elif "в документах" in c or "в документы" in c:
            target = "в документах " + target
        return {"type": "create_file", "path": target, "content": content}

    # Create folder: "создай папку TEXT и сохрани в загрузки", "создай папку Проект на рабочем столе"
    if any(k in c for k in ["создай папку", "создать папку", "сделай папку", "новая папка", "create folder", "mkdir"]):
        m_cd = re.search(r'(?:создай|создать|сделай|новая)\s+папк[ау]\s+([^\s]+)(?:\s+(?:и\s+)?(?:сохрани\s+)?(?:в|на)\s+([^\s]+))?', raw_c, re.IGNORECASE)
        f_name = "Новая папка"
        dest_hint = ""
        if m_cd:
            f_name = m_cd.group(1).strip('"\'«»')
            dest_hint = (m_cd.group(2) or "").lower()
        if any(w in c or w in dest_hint for w in ["рабоч", "desktop", "стол"]):
            f_name = "на рабочем столе " + f_name
        elif any(w in c or w in dest_hint for w in ["загруз", "download"]):
            f_name = "в загрузках " + f_name
        elif any(w in c or w in dest_hint for w in ["документ", "document"]):
            f_name = "в документах " + f_name
        return {"type": "create_folder", "path": f_name}

    # Delete file or folder: "удали файл test.txt", "удали папку Test", "удали эту папку", "удали её", "сотри папку"
    if any(k in c for k in [
        "удали файл", "удалить файл", "сотри файл",
        "удали папку", "удалить папку", "сотри папку", "стереть папку",
        "удали эту папку", "удалить эту папку", "удали данную папку",
        "удали эту", "удали это", "удали ее", "удали её", "удали его",
        "delete file", "delete folder"
    ]) or re.search(r'\b(?:удали|удалить|сотри)\s+(?:эту|данную|ту)?\s*(?:папку|файл)\b', c):
        m_del = re.search(r'(?:удали|удалить|сотри)\s+(?:эту|данную|ту)?\s*(?:файл|папку)?\s*(.*)', raw_c, re.IGNORECASE)
        target = m_del.group(1).strip().strip('"\'«»') if m_del else ""
        if not target or target.lower() in ["эту", "эту папку", "это", "ее", "её", "ту", "папку", "папка", "файл", "данную папку"]:
            target = sc.get_last_created_item() or ""
        return {"type": "delete_file", "path": target}

    # Analyze / inspect file: "проанализируй файл ...", "проверь файл ...", "посмотри файл ..."
    if any(k in c for k in ["проанализируй файл", "анализ файла", "проверь файл", "посмотри файл", "покажи что в файле", "прочитай файл"]):
        m_af = re.search(r'(?:проанализируй|анализ|проверь|посмотри|покажи что в|прочитай)\s+(?:файл[еа]?\s+)?(.+)', raw_c, re.IGNORECASE)
        target = ""
        if m_af:
            target = m_af.group(1).strip().strip('"\'«»')
        return {"type": "analyze_file", "path": target}

    # List folder files: "список файлов на рабочем столе", "какие файлы в загрузках"
    if any(k in c for k in ["список файлов", "какие файлы", "покажи файлы", "файлы на рабочем столе", "файлы в загрузках", "файлы в документах"]):
        target = "desktop"
        if any(f in c for f in ["загрузк", "загруз", "download"]):
            target = "downloads"
        elif any(f in c for f in ["документ", "document"]):
            target = "documents"
        return {"type": "list_files", "folder": target}

    # 8. System Stats / Hardware Telemetry
    if any(k in c for k in [
        "нагрузка пк", "характеристики пк", "загрузка процессора", "сколько памяти",
        "состояние системы", "системные ресурсы", "характеристики", "системная информация",
        "system stats", "pc stats", "cpu usage", "ram usage"
    ]):
        return {"type": "system_stats"}

    # 9. Folders
    if any(k in c for k in ["загрузки", "downloads"]):
        return {"type": "open_folder", "folder": "downloads"}
    if any(k in c for k in ["рабочий стол", "desktop"]) and not any(k in c for k in ["скрин", "сохрани", "save", "файл", "папк"]):
        return {"type": "open_folder", "folder": "desktop"}
    if any(k in c for k in ["документы", "documents"]):
        return {"type": "open_folder", "folder": "documents"}

    # 10. Universal Music & Media Controls
    # 10.1 Stop / Pause / Turn off music
    if any(k in c for k in [
        "выключи музыку", "выключить музыку", "отключи музыку", "останови музыку", "остановить музыку",
        "выруби музыку", "заглуши музыку", "выключи песню", "останови песню", "выруби трек", "выключи трек",
        "выключи то что сейчас играет", "выключи то что играет", "останови то что сейчас играет", "останови то что играет",
        "поставь на паузу", "поставить на паузу", "на паузу", "пауза", "pause", "стоп музыка", "останови воспроизведение"
    ]):
        return {"type": "play_music", "action": "pause"}

    # 10.2 Next track
    if any(k in c for k in [
        "следующий трек", "следующая песня", "следующую песню", "переключи трек", "переключи песню",
        "следующий", "next track", "скипни трек", "скипни песню", "скип трек", "скипни"
    ]) or (c in ["след", "next", "скип", "дальше"]):
        return {"type": "play_music", "action": "next"}

    # 10.3 Previous track
    if any(k in c for k in [
        "предыдущий трек", "предыдущая песня", "предыдущую песню", "прошлый трек", "прошлая песня",
        "верни трек", "верни песню", "prev track", "предыдущий", "назад песню"
    ]) or (c in ["пред", "prev", "назад"]):
        return {"type": "play_music", "action": "prev"}

    # 10.4 Resume / Continue playing
    if any(k in c for k in [
        "продолжи музыку", "продолжить музыку", "возобнови музыку", "возобновить музыку",
        "продолжи играть", "играй дальше", "сними с паузы", "возобнови трек", "продолжи трек"
    ]):
        return {"type": "play_music", "action": "resume"}

    # 10.5 Service & Playlist / Track Detection
    music_service = "auto"
    if any(k in c for k in ["спотифай", "spotify", "спотифае"]):
        music_service = "spotify"
    elif any(k in c for k in ["яндекс музык", "яндекс.музык", "я.музык", "ямузык", "yandex music"]):
        music_service = "yandex"
    elif any(k in c for k in ["саундклауд", "саундклауде", "саунд клауд", "soundcloud"]):
        music_service = "soundcloud"
    elif any(k in c for k in ["вк музык", "vk music", "музык вк", "музыку вк"]):
        music_service = "vk"
    elif any(k in c for k in ["ютуб", "ютубе", "ютуби", "youtube"]):
        music_service = "youtube"

    # If YouTube was explicitly requested for music / video, use extract_youtube_query directly
    if music_service == "youtube":
        yt_q = extract_youtube_query(orig_c)
        if yt_q:
            return {"type": "search_web", "query": yt_q, "engine": "youtube", "is_play": True}
        return {"type": "open_url", "url": "https://www.youtube.com"}

    # Playlists: "включи плейлист рок", "выбери плейлист для тренировок в спотифай"
    if any(k in c for k in ["плейлист", "playlist"]):
        m_pl = re.search(r'(?:включи|поставь|открой|выбери|запусти|найди|слушай)?\s*плейлист\s+(.+?)(?:\s+(?:в|на)\s+(?:спотифай|spotify|яндекс|soundcloud|саундклауд|вк|ютуб|youtube).*)?$', raw_c, re.IGNORECASE)
        pl_name = ""
        if m_pl:
            pl_name = m_pl.group(1).strip()
            pl_name = re.sub(r'\b(?:в|на)\s+(?:спотифа[еяй]|spotify|яндекс[е]?\s*(?:музык[еау])?|саундклауд[е]?|soundcloud|вк|vk|ютуб[е]?|youtube)\b', '', pl_name, flags=re.IGNORECASE).strip()
            pl_name = pl_name.strip('"\'«»')
        if music_service == "youtube":
            return {"type": "search_web", "query": pl_name or "плейлист", "engine": "youtube", "is_play": True}
        return {"type": "play_music", "service": music_service, "playlist": pl_name, "action": "play"}

    # Specific track / song request: "включи песню ...", "включи трек ...", "поставь песню ..."
    m_track = re.search(r'^(?:включи|включить|поставь|поставить|запусти|запустить|вруби|врубить|сыграй|найди\s+и\s+включи)\s+(?:песню|трек|композицию|музыку)\s+(.+)$', raw_c, re.IGNORECASE)
    if m_track:
        track_query = m_track.group(1).strip()
        track_query = re.sub(r'\b(?:в|на)\s+(?:спотифа[еяй]|spotify|яндекс[е]?\s*(?:музык[еау])?|саундклауд[е]?|soundcloud|вк|vk|ютуб[е]?|youtube)\b', '', track_query, flags=re.IGNORECASE).strip()
        track_query = track_query.strip('"\'«»')
        if track_query and track_query not in ["спотифай", "spotify", "яндекс музыка", "саундклауд", "soundcloud"]:
            if music_service == "youtube":
                return {"type": "search_web", "query": track_query, "engine": "youtube", "is_play": True}
            return {"type": "play_music", "service": music_service, "query": track_query, "action": "play"}

    # Explicit service search: e.g. "включи рамштайн в спотифай" or "поставь фонк в саундклауд"
    if music_service != "auto" and any(verb in c for verb in ["включи", "поставь", "найди", "запусти", "послушай", "play"]):
        clean_q = re.sub(r'^(?:включи|включить|поставь|поставить|найди|найти|запусти|запустить|открой|открыть|послушай|послушать|play)\s+', '', raw_c, flags=re.IGNORECASE).strip()
        clean_q = re.sub(r'\b(?:в|на)?\s*(?:спотифа[еяй]|spotify|яндекс[е]?\s*(?:музык[еау])?|саундклауд[е]?|soundcloud|вк|vk|ютуб[е]?|youtube)\b', '', clean_q, flags=re.IGNORECASE).strip()
        clean_q = clean_q.strip('"\'«»')
        if clean_q and len(clean_q) > 1:
            if music_service == "youtube":
                return {"type": "search_web", "query": clean_q, "engine": "youtube", "is_play": True}
            return {"type": "play_music", "service": music_service, "query": clean_q, "action": "play"}
        else:
            if music_service == "youtube":
                return {"type": "open_url", "url": "https://www.youtube.com"}
            return {"type": "play_music", "service": music_service, "action": "play"}

    # Direct service open / launch: "открой спотифай", "включи спотифай", "открой яндекс музыку"
    if any(k in c for k in ["спотифай", "spotify"]) and any(verb in c for verb in ["открой", "запусти", "включи", "open", "launch"]):
        return {"type": "play_music", "service": "spotify", "action": "play"}
    if any(k in c for k in ["яндекс музыка", "яндекс музыку", "yandex music"]) and any(verb in c for verb in ["открой", "запусти", "включи", "open", "launch"]):
        return {"type": "play_music", "service": "yandex", "action": "play"}
    if any(k in c for k in ["саундклауд", "саунд клауд", "soundcloud"]) and any(verb in c for verb in ["открой", "запусти", "включи", "open", "launch"]):
        return {"type": "play_music", "service": "soundcloud", "action": "play"}

    # General "включи музыку" / "поставь музыку"
    if any(k in c for k in ["включи музыку", "включить музыку", "поставь музыку", "поставить музыку", "запусти музыку", "запустить музыку", "play music"]):
        return {"type": "play_music", "service": "auto", "action": "play"}

    # 11. Direct Web URLs & Popular Sites (Evaluated BEFORE general search & app launch to prevent URLs from becoming apps)
    # Check explicit website opening command e.g. 'открой сайт "ссылка"', 'открой сайт хабр'
    site_pattern = r'^(?:открой|открыть|перейди\s+на|перейди|зайди\s+на|зайди|open)\s+(?:сайт|страниц[уа]|ссылк[уа])\s*(.*)$'
    m_site = re.match(site_pattern, c, re.IGNORECASE)
    if m_site:
        site_raw = m_site.group(1).strip().strip('"\'«»“”<> ')
        if not site_raw:
            return {"type": "launch_app", "app": "chrome"}
        site_aliases = {
            "вк": "https://vk.com", "vk": "https://vk.com",
            "ютуб": "https://youtube.com", "youtube": "https://youtube.com",
            "гугл": "https://google.com", "google": "https://google.com",
            "яндекс": "https://yandex.ru", "yandex": "https://yandex.ru",
            "хабр": "https://habr.com", "habr": "https://habr.com",
            "кинопоиск": "https://kinopoisk.ru",
            "тг": "https://web.telegram.org", "телеграм": "https://web.telegram.org", "телега": "https://web.telegram.org",
            "гитхаб": "https://github.com", "github": "https://github.com",
            "реддит": "https://reddit.com", "reddit": "https://reddit.com",
            "твич": "https://twitch.tv", "twitch": "https://twitch.tv",
            "рутуб": "https://rutube.ru", "rutube": "https://rutube.ru",
            "вайлдберриз": "https://wildberries.ru", "вб": "https://wildberries.ru", "wildberries": "https://wildberries.ru",
            "озон": "https://ozon.ru", "ozon": "https://ozon.ru",
            "авито": "https://avito.ru", "avito": "https://avito.ru",
            "tiktok": "https://www.tiktok.com", "тикток": "https://www.tiktok.com", "тик ток": "https://www.tiktok.com",
            "deepseek": "https://chat.deepseek.com", "дипсик": "https://chat.deepseek.com", "дип сик": "https://chat.deepseek.com", "deep seek": "https://chat.deepseek.com",
            "дикси": "https://dixy.ru", "dixy": "https://dixy.ru",
            "chatgpt": "https://chatgpt.com", "чатгпт": "https://chatgpt.com",
            "spotify": "https://open.spotify.com", "спотифай": "https://open.spotify.com",
            "discord": "https://discord.com", "дискорд": "https://discord.com",
            "steam": "https://store.steampowered.com", "стим": "https://store.steampowered.com"
        }
        site_lower = site_raw.lower()
        if site_lower in site_aliases:
            return {"type": "open_url", "url": site_aliases[site_lower]}
        url_match = re.search(r'(https?://[^\s"\'«»“”<>]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s"\'«»“”<>]*)?)', site_raw)
        if url_match:
            u = url_match.group(1).strip('"\'«»“”<> ')
            if not u.startswith("http://") and not u.startswith("https://"):
                u = "https://" + u
            return {"type": "open_url", "url": u}
        # If single word without dot (e.g. "tiktok"), open as www.{word}.com
        clean_word = re.sub(r'[^a-zA-Z0-9-]', '', site_lower)
        if clean_word and len(clean_word) >= 3:
            return {"type": "open_url", "url": f"https://www.{clean_word}.com"}
        return {"type": "search_web", "query": site_raw, "engine": "google"}

    # General URL in text
    m_url = re.search(r'(https?://[^\s"\'«»]+|(?:www\.)?[a-zA-Z0-9-]+\.(?:ru|com|org|net|io|me|ai|app|dev|by|kz|xyz|top|online|site|tech)(?:/[^\s"\'«»]*)?)', c)
    if m_url and (c.strip() == m_url.group(1).lower() or any(verb in c for verb in ["открой", "перейди", "зайди", "open", "сайт", "ссылк", "http", "www", "браузер"])):
        url_dest = m_url.group(1).strip('"\'«»“”<> ')
        if not url_dest.startswith("http://") and not url_dest.startswith("https://"):
            url_dest = "https://" + url_dest
        return {"type": "open_url", "url": url_dest}

    if re.search(r'\b(вк|vk)\b', c) and (c.strip() in ["вк", "vk"] or any(verb in c for verb in ["открой", "зайди", "перейди", "open"])):
        return {"type": "open_url", "url": "https://vk.com"}
    if re.search(r'\b(github|гитхаб)\b', c) and (c.strip() in ["гитхаб", "github"] or any(verb in c for verb in ["открой", "зайди", "перейди", "open"])):
        return {"type": "open_url", "url": "https://github.com"}
    if re.search(r'\b(twitch|твич)\b', c) and (c.strip() in ["твич", "twitch"] or any(verb in c for verb in ["открой", "зайди", "перейди", "open"])):
        return {"type": "open_url", "url": "https://twitch.tv"}
    if re.search(r'\b(rutube|рутуб)\b', c) and (c.strip() in ["рутуб", "rutube"] or any(verb in c for verb in ["открой", "зайди", "перейди", "open"])):
        return {"type": "open_url", "url": "https://rutube.ru"}
    if re.search(r'\b(reddit|реддит)\b', c) and (c.strip() in ["реддит", "reddit"] or any(verb in c for verb in ["открой", "зайди", "перейди", "open"])):
        return {"type": "open_url", "url": "https://reddit.com"}

    # 12. Web Searches across Popular Platforms (YouTube, Google, Yandex, Wildberries, Ozon, Avito, GitHub)
    if any(k in c for k in ["ютуб", "youtube", "ютубе", "ютуби"]) and not any(k in c for k in ["закрой", "закрыть", "close", "выключи", "заверши", "адресн", "строк", "ссылк", "вставить", "напечатай в"]):
        q = extract_youtube_query(orig_c)
        if q:
            is_play = any(verb in c for verb in ["включи", "поставь", "запусти", "вруби", "сыграй", "послушай", "play"])
            if any(k in c for k in ["ютуб музык", "youtube music"]):
                return {"type": "play_music", "service": "youtube", "query": q, "action": "play"}
            return {"type": "search_web", "query": q, "engine": "youtube", "is_play": is_play}
        return {"type": "open_url", "url": "https://www.youtube.com"}

    if any(k in c for k in ["яндекс", "yandex"]):
        q = re.sub(r'\b(яндексе|яндекс|yandex)\b', '', c, flags=re.IGNORECASE)
        q = re.sub(r'^(?:открой|открыть|перейди|зайди|включи|включить|найди|найти|поищи|поискать|загугли|загуглить|напиши|напечатай|введи|вбей|продиктуй|поиск|в\s+поиске|и\s+найди|и|в|на|\s+)+', '', q, flags=re.IGNORECASE).strip()
        if q and len(q) > 1:
            return {"type": "search_web", "query": q, "engine": "yandex"}
        return {"type": "open_url", "url": "https://yandex.ru"}

    if any(k in c for k in ["вб", "вайлдберриз", "вайлдбериз", "wildberries"]):
        q = re.sub(r'\b(вб|вайлдберриз|вайлдбериз|wildberries)\b', '', c, flags=re.IGNORECASE)
        q = re.sub(r'^(?:открой|открыть|найди|найти|поищи|поискать|купи|купить|посмотри|покажи|напиши|напечатай|введи|вбей|продиктуй|поиск|в\s+поиске|и\s+найди|и|в|на|\s+)+', '', q, flags=re.IGNORECASE).strip()
        if q and len(q) > 1:
            return {"type": "search_web", "query": q, "engine": "wildberries"}
        return {"type": "open_url", "url": "https://wildberries.ru"}

    if any(k in c for k in ["озон", "ozon"]):
        q = re.sub(r'\b(озоне|озон|ozon)\b', '', c, flags=re.IGNORECASE)
        q = re.sub(r'^(?:открой|открыть|найди|найти|поищи|поискать|купи|купить|покажи|напиши|напечатай|введи|вбей|продиктуй|поиск|в\s+поиске|и\s+найди|и|в|на|\s+)+', '', q, flags=re.IGNORECASE).strip()
        if q and len(q) > 1:
            return {"type": "search_web", "query": q, "engine": "ozon"}
        return {"type": "open_url", "url": "https://ozon.ru"}

    if any(k in c for k in ["авито", "avito"]):
        q = re.sub(r'\b(авито|avito)\b', '', c, flags=re.IGNORECASE)
        q = re.sub(r'^(?:открой|открыть|найди|найти|поищи|поискать|покажи|напиши|напечатай|введи|вбей|продиктуй|поиск|в\s+поиске|и\s+найди|и|в|на|\s+)+', '', q, flags=re.IGNORECASE).strip()
        if q and len(q) > 1:
            return {"type": "search_web", "query": q, "engine": "avito"}
        return {"type": "open_url", "url": "https://avito.ru"}

    if any(k in c for k in ["сафари", "safari"]):
        q = re.sub(r'\b(сафари|safari)\b', '', c, flags=re.IGNORECASE)
        q = re.sub(r'^(?:открой|открыть|найди|найти|поищи|поискать|загугли|напиши|напечатай|введи|вбей|поиск|в\s+поиске|и\s+найди|и|в|на|\s+)+', '', q, flags=re.IGNORECASE).strip()
        if q and len(q) > 1:
            return {"type": "autonomous_browser_task", "browser": "safari", "query": q}
        return {"type": "launch_app", "app": "safari"}

    if any(k in c for k in ["в заметках", "в заметки"]):
        t = re.sub(r'^(?:в\s+заметках|в\s+заметки)\s+(?:напиши|создай|запиши|добавь|сохрани)\s+(?:заметку\s+)?(?:с\s+текстом\s+|текст\s+)?', '', raw_c, flags=re.IGNORECASE).strip()
        if t:
            return {"type": "autonomous_notes_task", "text": t}
        return {"type": "launch_app", "app": "notes"}

    # 13. Google / Web Searches
    if any(k in c for k in ["гугл", "google", "загугли", "загуглить", "погугли", "поищи в интернете", "найди в интернете"]):
        q = re.sub(r'\b(гугле|гугл|google|интернете|сети)\b', '', c, flags=re.IGNORECASE)
        q = re.sub(r'^(?:открой|открыть|найди|найти|поищи|поискать|загугли|загуглить|погугли|погуглить|напиши|напечатай|введи|вбей|продиктуй|поиск|в\s+поиске|и\s+найди|и|в|на|\s+)+', '', q, flags=re.IGNORECASE).strip()
        if q and len(q) > 1:
            return {"type": "search_web", "query": q, "engine": "google"}
        return {"type": "open_url", "url": "https://www.google.com"}

    # Generic search bar query e.g. "введи в поиск купить кроссовки" / "напиши в поиске рецепты"
    if any(c.startswith(k) for k in ["введи в поиск ", "вбей в поиск ", "напиши в поиск ", "напиши в поиске ", "поиск: ", "поиск "]):
        q = re.sub(r'^(?:введи\s+в\s+поиск[е]?|вбей\s+в\s+поиск[е]?|напиши\s+в\s+поиск[е]?|поиск[:\s]+)', '', raw_c, flags=re.IGNORECASE).strip()
        q = re.sub(r'^["«\']|["»\']$', '', q).strip()
        if q:
            return {"type": "search_web", "query": q, "engine": "google"}

    # 13.1 Universal Messenger & Chat Automation (Telegram, Discord, WhatsApp, VK, Skype, Slack)
    MESSENGER_KEYWORDS = ['телеграмме', 'телеграме', 'телеграм', 'телеграмчик', 'телеге', 'тг', 'telegram', 'дискорде', 'дискорд', 'discord', 'ватсапе', 'ватсап', 'whatsapp', 'вк', 'vk', 'скайпе', 'скайп', 'skype', 'слаке', 'слак', 'slack']
    M_KW_PATTERN = r'(?:в\s+|на\s+)?(' + '|'.join(MESSENGER_KEYWORDS) + r')'

    COMMON_NAME_DATIVE_MAP = {
                "никите": "Никита", "никиту": "Никита", "никита": "Никита",
        "саше": "Саша", "сашу": "Саша", "саша": "Саша",
        "маше": "Маша", "машу": "Маша", "маша": "Маша",
        "даше": "Даша", "дашу": "Даша", "даша": "Даша",
        "артему": "Артем", "артёму": "Артем", "артем": "Артем", "артём": "Артем",
        "диме": "Дима", "диму": "Дима", "дима": "Дима",
        "максиму": "Максим", "максима": "Максим", "максим": "Максим",
        "ивану": "Иван", "ивана": "Иван", "иван": "Иван",
        "владу": "Влад", "влада": "Влад", "влад": "Влад",
        "сергею": "Сергей", "сергея": "Сергей", "сергей": "Сергей",
        "андрею": "Андрей", "андрея": "Андрей", "андрей": "Андрей",
        "алексею": "Алексей", "алексея": "Алексей", "алексей": "Алексей",
        "олегу": "Олег", "олега": "Олег", "олег": "Олег",
        "денису": "Денис", "дениса": "Денис", "денис": "Денис",
        "мише": "Миша", "мишу": "Миша", "миша": "Миша",
        "роме": "Рома", "рому": "Рома", "рома": "Рома",
        "паше": "Паша", "пашу": "Паша", "паша": "Паша",
        "илье": "Илья", "илью": "Илья", "илья": "Илья",
        "антону": "Антон", "антона": "Антон", "антон": "Антон",
        "егору": "Егор", "егора": "Егор", "егор": "Егор",
        "маме": "Мама", "маму": "Мама", "мама": "Мама",
        "папе": "Папа", "папу": "Папа", "папа": "Папа",
        "брату": "Брат", "брата": "Брат", "брат": "Брат",
        "сестре": "Сестра", "сестру": "Сестра", "сестра": "Сестра",
        "бабушке": "Бабушка", "бабушку": "Бабушка", "бабушка": "Бабушка",
        "дедушке": "Дедушка", "дедушку": "Дедушка", "дедушка": "Дедушка",
        "насте": "Настя", "настю": "Настя", "настя": "Настя",
        "кате": "Катя", "катю": "Катя", "катя": "Катя",
        "оле": "Оля", "олю": "Оля", "оля": "Оля",
        "ане": "Аня", "аню": "Аня", "аня": "Аня",
        "юле": "Юля", "юлю": "Юля", "юля": "Юля",
        "лене": "Лена", "лену": "Лена", "лена": "Лена",
        "полине": "Полина", "полину": "Полина", "полина": "Полина",
        "соне": "Соня", "соню": "Соня", "соня": "Соня",
        "жене": "Женя", "женю": "Женя", "женя": "Женя",
        "косте": "Костя", "костю": "Костя", "костя": "Костя",
        "тимуру": "Тимур", "тимура": "Тимур", "тимур": "Тимур",
        "марку": "Марк", "марка": "Марк", "марк": "Марк",
        "глебу": "Глеб", "глеба": "Глеб", "глеб": "Глеб",
        "богдану": "Богдан", "богдана": "Богдан", "богдан": "Богдан",
        "ярославу": "Ярослав", "ярослава": "Ярослав", "ярослав": "Ярослав",
    }

    INVALID_CONTACT_KEYWORDS = {
        'контакт', 'контакту', 'контакта', 'контактом', 'контакте', 'контакты',
        'пользователь', 'пользователю', 'пользователя', 'пользователем', 'пользователи',
        'человек', 'человеку', 'человека', 'людям', 'друг', 'другу', 'друга', 'друзьям',
        'собеседник', 'собеседнику', 'юзер', 'юзеру', 'ник', 'нику', 'никнейм',
        'сообщение', 'текст', 'слово', 'привет', 'хеллоу', 'hello', 'hi',
        'кому-то', 'кому-нибудь', 'кому', 'куда', 'ему', 'ей', 'им', 'ним'
    }

    def normalize_contact_name(raw_name: str) -> str:
        s = raw_name.strip().strip('"\'«»')
        if not s:
            return ""
        low = s.lower()
        if low in INVALID_CONTACT_KEYWORDS:
            return ""
        if low in COMMON_NAME_DATIVE_MAP:
            return COMMON_NAME_DATIVE_MAP[low]
        if re.search(r'[а-яё]', low):
            if len(low) > 4 and low.endswith('у') and not low.endswith('ау'):
                res = low[:-1].capitalize()
                return "" if res.lower() in INVALID_CONTACT_KEYWORDS else res
            if len(low) > 4 and low.endswith('ю'):
                res = (low[:-1] + 'й').capitalize()
                return "" if res.lower() in INVALID_CONTACT_KEYWORDS else res
            if len(low) > 4 and low.endswith('е'):
                res = (low[:-1] + 'а').capitalize()
                return "" if res.lower() in INVALID_CONTACT_KEYWORDS else res
            return "" if low in INVALID_CONTACT_KEYWORDS else s.capitalize()
        return s

    def normalize_messenger(name: str) -> str:
        nl = name.lower()
        if any(k in nl for k in ['дискорд', 'discord']):
            return 'discord'
        elif any(k in nl for k in ['ватсап', 'whatsapp']):
            return 'whatsapp'
        elif any(k in nl for k in ['вк', 'vk']):
            return 'vk'
        elif any(k in nl for k in ['скайп', 'skype']):
            return 'skype'
        elif any(k in nl for k in ['слак', 'slack']):
            return 'slack'
        return 'telegram'

    def extract_case_match(original_str: str, lower_match: str) -> str:
        if not lower_match or not original_str:
            return lower_match
        m = re.search(re.escape(lower_match), original_str, re.IGNORECASE)
        return m.group(0) if m else lower_match

    # 12.5. In-Page / In-Browser / Active Window Typing Check
    # e.g. "в активной странице браузера напиши контакту Алексей Привет", "в браузере напиши Привет"
    m_in_page = re.match(
        r'^(?:в\s+активн\w*\s+страниц\w*(?:\s+браузер\w*)?|на\s+активн\w*\s+страниц\w*(?:\s+браузер\w*)?|в\s+браузер\w*|на\s+страниц\w*|в\s+текущ\w*\s+вкладк\w*|в\s+активн\w*\s+окн\w*|в\s+текущ\w*\s+окн\w*)\s+(?:и\s+)?(?:напиши|напечатай|введи|вбей|вставь|отправь)\s+(?:сообщение\s+|текст\s+|слово\s+)?(?:контакту\s+|пользователю\s+|для\s+|в\s+чат\s+)?(?:([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)\s+)?(.*)$',
        c, re.IGNORECASE
    )
    if m_in_page:
        contact_name = m_in_page.group(1) or ""
        msg_body = m_in_page.group(2).strip()
        clean_body = re.sub(r'^["\'\u00ab\u00bb]|["\'\u00ab\u00bb]$', '', msg_body).strip()
        clean_body = extract_case_match(orig_c, clean_body)
        if contact_name:
            norm_contact = normalize_contact_name(contact_name)
            final_text = f"{norm_contact}, {clean_body}" if clean_body else norm_contact
        else:
            final_text = clean_body
        return {
            "type": "type_text",
            "text": final_text,
            "press_enter": True
        }

    # Pattern 1A (contact with prefix before verb): 'открой <messenger> и контакту/пользователю/в чат <contact> напиши/отправь <message>'
    m1_before = re.match(
        rf'^(?:зайди|открой|перейди)\s+{M_KW_PATTERN}\s+(?:и\s+)?(?:в\s+чат\s+|в\s+диалог\s+|пользователю\s+|контакту\s+|для\s+|в\s+)([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)\s+(?:и\s+)?(?:напиши|напечатай|отправь|скинь)\s+(?:слово\s+|текст\s+|сообщение\s+)?(.*)',
        c, re.IGNORECASE
    )
    if m1_before:
        m_app = normalize_messenger(m1_before.group(1))
        raw_contact = extract_case_match(orig_c, m1_before.group(2).strip())
        m_target = normalize_contact_name(raw_contact)
        m_msg = re.sub(r'^["«\']|["»\']$', '', m1_before.group(3).strip()).strip()
        m_msg = extract_case_match(orig_c, m_msg)
        return {"type": "messenger_send", "messenger": m_app, "contact": m_target, "message": m_msg}

    # Pattern 1B (verb before contact): 'зайди/открой/перейди [в] <messenger> и напиши/отправь [в <contact>] [слово/текст] <message>'
    m1_after = re.match(
        rf'^(?:зайди|открой|перейди)\s+{M_KW_PATTERN}\s+(?:и\s+)?(?:напиши|напечатай|отправь|скинь)\s+(?:в\s+чат\s+|в\s+диалог\s+|пользователю\s+|контакту\s+|для\s+|в\s+)?([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)\s+(?:слово\s+|текст\s+|сообщение\s+)?(.*)',
        c, re.IGNORECASE
    )
    if m1_after:
        m_app = normalize_messenger(m1_after.group(1))
        raw_contact = extract_case_match(orig_c, m1_after.group(2).strip())
        m_target = normalize_contact_name(raw_contact)
        m_msg = re.sub(r'^["«\']|["»\']$', '', m1_after.group(3).strip()).strip()
        m_msg = extract_case_match(orig_c, m_msg)
        return {"type": "messenger_send", "messenger": m_app, "contact": m_target, "message": m_msg}

    # Pattern 1C: 'в/на <messenger> [и] напиши/отправь [в/пользователю/контакту <contact>] [слово/текст] <message>'
    m1_c = re.match(
        rf'^(?:в\s+|на\s+){M_KW_PATTERN}\s+(?:и\s+)?(?:напиши|напечатай|отправь|скинь|черкани)\s+(?:в\s+чат\w*\s+|в\s+диалог\w*\s+|пользовател\w*\s+|контакт\w*\s+|для\s+|в\s+|@)?([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)(?:\s+(?:слово\s+|текст\s+|сообщение\s+)?(.*))?$',
        c, re.IGNORECASE
    )
    if m1_c:
        m_app = normalize_messenger(m1_c.group(1))
        raw_contact = extract_case_match(orig_c, m1_c.group(2).strip())
        m_target = normalize_contact_name(raw_contact)
        raw_msg = (m1_c.group(3) or "").strip()
        if not m_target and raw_msg:
            parts = raw_msg.split(None, 1)
            raw_contact = extract_case_match(orig_c, parts[0])
            m_target = normalize_contact_name(raw_contact)
            raw_msg = parts[1] if len(parts) > 1 else ""
        if not raw_msg:
            return {
                "type": "clarify",
                "message": (
                    f"Уточните, пожалуйста, сэр: какой текст сообщения вы хотите отправить контакту «{m_target}» в {m_app.title()}?\n"
                    f"Например: «В {m_app.title()} напиши {m_target} текст Привет»."
                )
            }
        m_msg = re.sub(r'^["«\']|["»\']$', '', raw_msg).strip()
        m_msg = extract_case_match(orig_c, m_msg)
        return {"type": "messenger_send", "messenger": m_app, "contact": m_target, "message": m_msg}

    # Pattern 1D: 'в/на <messenger> [пользователю/контакту <contact>] напиши/отправь [слово/текст] <message>'
    m1_d = re.match(
        rf'^(?:в\s+|на\s+){M_KW_PATTERN}\s+(?:в\s+чат\s+|в\s+диалог\s+|пользователю\s+|контакту\s+|для\s+|в\s+)?([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)\s+(?:напиши|напечатай|отправь|скинь|черкани)(?:\s+(?:слово\s+|текст\s+|сообщение\s+)?(.*))?$',
        c, re.IGNORECASE
    )
    if m1_d:
        m_app = normalize_messenger(m1_d.group(1))
        raw_contact = extract_case_match(orig_c, m1_d.group(2).strip())
        m_target = normalize_contact_name(raw_contact)
        raw_msg = (m1_d.group(3) or "").strip()
        if not raw_msg:
            return {
                "type": "clarify",
                "message": (
                    f"Уточните, пожалуйста, сэр: какой текст сообщения вы хотите отправить контакту «{m_target}» в {m_app.title()}?\n"
                    f"Например: «В {m_app.title()} напиши {m_target} текст Привет»."
                )
            }
        m_msg = re.sub(r'^["«\']|["»\']$', '', raw_msg).strip()
        m_msg = extract_case_match(orig_c, m_msg)
        return {"type": "messenger_send", "messenger": m_app, "contact": m_target, "message": m_msg}

    # Pattern 2: 'напиши/отправь [в <messenger>] [в <contact>] [слово/текст] <message>'
    m2 = re.match(
        rf'^(?:напиши|напечатай|отправь|скинь)\s+(?:сообщение\s+)?(?:в\s+|на\s+)?{M_KW_PATTERN}\s+(?:в\s+|пользовател\w*\s+|контакт\w*\s+|для\s+|в\s+чат\w*\s+|@)?([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)(?:\s+(?:слово\s+|текст\s+|сообщение\s+)?(.*))?$',
        c, re.IGNORECASE
    )
    if m2:
        m_app = normalize_messenger(m2.group(1))
        raw_contact = extract_case_match(orig_c, m2.group(2).strip())
        m_target = normalize_contact_name(raw_contact)
        raw_msg = (m2.group(3) or "").strip()
        if not m_target and raw_msg:
            parts = raw_msg.split(None, 1)
            raw_contact = extract_case_match(orig_c, parts[0])
            m_target = normalize_contact_name(raw_contact)
            raw_msg = parts[1] if len(parts) > 1 else ""
        if not raw_msg:
            return {
                "type": "clarify",
                "message": (
                    f"Уточните, пожалуйста, сэр: какой текст сообщения вы хотите отправить контакту «{m_target}» в {m_app.title()}?\n"
                    f"Например: «В {m_app.title()} напиши {m_target} текст Привет»."
                )
            }
        m_msg = re.sub(r'^["«\']|["»\']$', '', raw_msg).strip()
        m_msg = extract_case_match(orig_c, m_msg)
        return {"type": "messenger_send", "messenger": m_app, "contact": m_target, "message": m_msg}

    # Pattern 3A: Explicit chat keyword e.g. 'найди/открой чат/диалог/контакт <contact> [и напиши ему <msg>]'
    m3_chat = re.match(
        r'^(?:найди|открой|выбери|поищи)\s+(?:там\s+|тут\s+|здесь\s+)?(?:чат|диалог|беседу|группу|канал|контакт|переписку)\s+(?:с\s+|для\s+)?([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)(?:\s+(?:и\s+)?(?:напиши|напечатай|отправь|скинь)\s+(?:ему\s+|ей\s+|им\s+)?(?:сообщение\s+|текст\s+|слово\s+)?(.*))?$',
        c, re.IGNORECASE
    )
    if m3_chat:
        raw_target = extract_case_match(orig_c, m3_chat.group(1).strip())
        target_name = normalize_contact_name(raw_target)
        raw_msg = m3_chat.group(2)
        if target_name.lower() not in ['приложение', 'программу', 'файл', 'папку', 'вкладку', 'окно', 'видео', 'музыку']:
            msg_text = ''
            if raw_msg:
                clean_raw = re.sub(r'^(?:ему\s+|ей\s+|им\s+|пользователю\s+)', '', raw_msg.strip(), flags=re.IGNORECASE).strip()
                clean_raw = re.sub(r'^["«\']|["»\']$', '', clean_raw).strip()
                msg_text = extract_case_match(orig_c, clean_raw)
            dest_m = 'auto'
            for kw in MESSENGER_KEYWORDS:
                if kw in c:
                    dest_m = normalize_messenger(kw)
                    break
            if not msg_text:
                m_disp = "Telegram" if dest_m == "telegram" else "Discord" if dest_m == "discord" else "WhatsApp" if dest_m == "whatsapp" else "VK" if dest_m == "vk" else "мессенджере"
                return {
                    "type": "clarify",
                    "message": (
                        f"Уточните, пожалуйста, сэр: какой текст сообщения вы хотите отправить контакту «{target_name}» в {m_disp}?\n"
                        f"Например: «В {m_disp if m_disp != 'мессенджере' else 'Telegram'} напиши {target_name} текст Привет»."
                    )
                }
            return {'type': 'messenger_send', 'messenger': dest_m, 'contact': target_name, 'message': msg_text}

    # Pattern 3B: Find contact and send message (MUST have message verb): 'найди/поищи <contact> и напиши [ему] <msg>'
    m3_write = re.match(
        r'^(?:найди|поищи)\s+(?:там\s+|тут\s+|здесь\s+)?(?:с\s+|для\s+)?([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)\s+(?:и\s+)?(?:напиши|напечатай|отправь|скинь)\s+(?:ему\s+|ей\s+|им\s+)?(?:сообщение\s+|текст\s+|слово\s+)?(.*)$',
        c, re.IGNORECASE
    )
    if m3_write:
        raw_target = extract_case_match(orig_c, m3_write.group(1).strip())
        target_name = normalize_contact_name(raw_target)
        raw_msg = m3_write.group(2)
        if target_name.lower() not in ['приложение', 'программу', 'файл', 'папку', 'вкладку', 'окно', 'видео', 'музыку', 'постман', 'хром', 'калькулятор', 'браузер']:
            msg_text = ''
            if raw_msg:
                clean_raw = re.sub(r'^(?:ему\s+|ей\s+|им\s+|пользователю\s+)', '', raw_msg.strip(), flags=re.IGNORECASE).strip()
                clean_raw = re.sub(r'^["«\']|["»\']$', '', clean_raw).strip()
                msg_text = extract_case_match(orig_c, clean_raw)
            dest_m = 'auto'
            for kw in MESSENGER_KEYWORDS:
                if kw in c:
                    dest_m = normalize_messenger(kw)
                    break
            if not msg_text:
                m_disp = "Telegram" if dest_m == "telegram" else "Discord" if dest_m == "discord" else "WhatsApp" if dest_m == "whatsapp" else "VK" if dest_m == "vk" else "мессенджере"
                return {
                    "type": "clarify",
                    "message": (
                        f"Уточните, пожалуйста, сэр: какой текст сообщения вы хотите отправить контакту «{target_name}» в {m_disp}?\n"
                        f"Например: «В {m_disp if m_disp != 'мессенджере' else 'Telegram'} напиши {target_name} текст Привет»."
                    )
                }
            return {'type': 'messenger_send', 'messenger': dest_m, 'contact': target_name, 'message': msg_text}

    # Pattern 4A: Explicit contact prefix: "напиши/отправь [сообщение] пользователю/контакту/для/в чат/в диалог <contact> <message>"
    m4_prefix = re.match(
        r'^(?:напиши|напечатай|отправь|скинь)\s+(?:сообщение\s+|текст\s+|слово\s+)?(?:пользовател\w*|контакт\w*|для|в\s+чат\w*|в\s+диалог\w*|@)\s+([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)(?:\s+(?:сообщение\s+|текст\s+|слово\s+)?(.*))?$',
        c, re.IGNORECASE
    )
    if m4_prefix:
        orig_contact = extract_case_match(orig_c, m4_prefix.group(1).strip())
        norm_contact = normalize_contact_name(orig_contact)
        raw_msg = (m4_prefix.group(2) or "").strip()
        if not norm_contact and raw_msg:
            parts = raw_msg.split(None, 1)
            orig_contact = extract_case_match(orig_c, parts[0])
            norm_contact = normalize_contact_name(orig_contact)
            raw_msg = parts[1] if len(parts) > 1 else ""
        if not raw_msg:
            return {
                "type": "clarify",
                "message": (
                    f"Уточните, пожалуйста, сэр: в какой именно мессенджер (Telegram, WhatsApp, Discord или VK) "
                    f"и какой текст сообщения отправить контакту «{norm_contact}»?\n"
                    f"Например: «В Telegram напиши {norm_contact} текст Привет» или «В Discord напиши {norm_contact} текст Привет»."
                )
            }
        clean_msg = re.sub(r'^["«\']|["»\']$', '', raw_msg).strip()
        clean_msg = extract_case_match(orig_c, clean_msg)
        return {"type": "messenger_send", "messenger": "auto", "contact": norm_contact, "message": clean_msg}

    # Pattern 4B: Direct Russian name in dative case or Latin username:
    # e.g. "напиши Алексею привет как дела", "отправь Никите файл готов", "напиши JessePinkman привет", "напиши Алексею в тг"
    m4_direct = re.match(
        r'^(?:напиши|напечатай|отправь|скинь)\s+([a-zA-Zа-яА-ЯёЁ0-9_\-\.]+)(?:\s+(?:сообщение\s+|текст\s+|слово\s+)?(.*))?$',
        c, re.IGNORECASE
    )
    if m4_direct:
        cand_target = m4_direct.group(1).strip()
        cand_target_low = cand_target.lower()
        cand_msg = (m4_direct.group(2) or "").strip()
        if cand_target_low in INVALID_CONTACT_KEYWORDS and cand_msg:
            parts = cand_msg.split(None, 1)
            cand_target = parts[0]
            cand_target_low = cand_target.lower()
            cand_msg = parts[1] if len(parts) > 1 else ""
        is_known_contact = cand_target_low in COMMON_NAME_DATIVE_MAP
        is_latin_username = bool(re.match(r'^[a-zA-Z0-9_\-\.]+$', cand_target) and cand_target_low not in APP_MAP)
        if is_known_contact or is_latin_username:
            orig_contact = extract_case_match(orig_c, cand_target)
            norm_contact = normalize_contact_name(orig_contact)
            if cand_msg:
                m_embedded_app = re.match(
                    r'^(?:в\s+|на\s+)?(тг|телеграм\w*|телег\w*|telegram|дискорд\w*|discord|ватсап\w*|whatsapp|воцап|вк|vk|вконтакте|скайп\w*|skype|слак\w*|slack|вайбер\w*|viber)(?:\s+(?:текст[:\s]+|сообщение[:\s]+|слово[:\s]+)?(.*))?$',
                    cand_msg, re.IGNORECASE
                )
                if m_embedded_app:
                    raw_app = m_embedded_app.group(1).lower()
                    target_app = "Telegram" if any(k in raw_app for k in ["теле", "тг"]) else "Discord" if "дискорд" in raw_app or "discord" in raw_app else "WhatsApp" if "ватсап" in raw_app or "whatsapp" in raw_app else "VK" if "вк" in raw_app or "vk" in raw_app else raw_app.capitalize()
                    remaining_msg = (m_embedded_app.group(2) or "").strip()
                    if not remaining_msg:
                        return {
                            "type": "clarify",
                            "message": (
                                f"Уточните, пожалуйста, сэр: какой текст сообщения вы хотите отправить контакту «{norm_contact}» в {target_app}?\n"
                                f"Например: «В {target_app} напиши {norm_contact} текст Привет»."
                            )
                        }
                    else:
                        remaining_msg = re.sub(r'^["«\']|["»\']$', '', remaining_msg).strip()
                        remaining_msg = extract_case_match(orig_c, remaining_msg)
                        return {
                            "type": "messenger_send",
                            "messenger": target_app.lower(),
                            "contact": norm_contact,
                            "message": remaining_msg
                        }
                else:
                    clean_msg = re.sub(r'^["«\']|["»\']$', '', cand_msg).strip()
                    clean_msg = extract_case_match(orig_c, clean_msg)
                    return {"type": "messenger_send", "messenger": "auto", "contact": norm_contact, "message": clean_msg}
            else:
                detected_m = sc.detect_installed_messengers()
                _MESSENGER_WIZARD_STATE["default"] = {
                    "stage": "awaiting_messenger",
                    "messengers": detected_m,
                    "contact": norm_contact
                }
                msg_lines = [f"Выберите мессенджер для отправки сообщения контакту «{norm_contact}», сэр:"]
                for m in detected_m:
                    msg_lines.append(f"{m['num']}. {m['name']}")
                msg_lines.append("\nНажмите кнопку ниже или отправьте цифру/название.")
                return {
                    "type": "messenger_wizard",
                    "message": "\n".join(msg_lines),
                    "stage": "select_messenger",
                    "options": [{"label": m["label"], "cmd": m["num"]} for m in detected_m],
                    "messengers": detected_m,
                    "contact": norm_contact
                }

    # Universal Clarify for incomplete messenger / messaging requests
    has_msg_verb = any(v in c for v in ["напиши", "напечатай", "отправь", "скинь", "черкани", "передай", "отошли", "пошли"])
    has_message_noun = any(n in c for n in ["сообщение", "смс", "сообщени", "весть", "письмецо", "текст в чат", "текст в диалог"])
    has_generic_recipient = any(r in c for r in ["кому-то", "кому-нибудь", "кому то", "кому нибудь", "человеку", "другу", "пользователю", "контакту"])
    has_messenger_kw = any(app in c for app in [
        "телеграм", "telegram", "тг", "телеге", "телега", "дискорд", "discord",
        "ватсап", "whatsapp", "воцап", "вк", "vk", "вконтакте", "скайп", "skype",
        "слак", "slack", "вайбер", "viber", "мессенджер", "чат", "диалог"
    ])

    is_incomplete_message = (
        (has_messenger_kw and has_msg_verb) or
        (has_msg_verb and has_message_noun) or
        (has_msg_verb and has_generic_recipient) or
        (has_message_noun and has_generic_recipient) or
        any(phrase in c for phrase in ["напиши кому", "отправь кому", "напиши сообщение", "отправь сообщение", "скинь сообщение"])
    )

    if is_incomplete_message:
        target_app = None
        if any(k in c for k in ["телеграм", "telegram", "тг", "телеге", "телега"]):
            target_app = "Telegram"
        elif any(k in c for k in ["дискорд", "discord"]):
            target_app = "Discord"
        elif any(k in c for k in ["ватсап", "whatsapp", "воцап"]):
            target_app = "WhatsApp"
        elif any(k in c for k in ["вк", "vk", "вконтакте"]):
            target_app = "VK"
        elif any(k in c for k in ["скайп", "skype"]):
            target_app = "Skype"
        elif any(k in c for k in ["слак", "slack"]):
            target_app = "Slack"
        elif any(k in c for k in ["вайбер", "viber"]):
            target_app = "Viber"

        if target_app:
            _MESSENGER_WIZARD_STATE["default"] = {
                "stage": "awaiting_contact",
                "messenger": target_app.lower(),
                "messenger_name": target_app
            }
            return {
                "type": "messenger_wizard",
                "message": (
                    f"Мессенджер {target_app} выбран, сэр.\n\n"
                    f"Введите имя контакта или ник/юзернейм получателя (например: @username или Алексей):"
                ),
                "stage": "enter_contact",
                "messenger": target_app.lower()
            }
        else:
            detected_m = sc.detect_installed_messengers()
            _MESSENGER_WIZARD_STATE["default"] = {
                "stage": "awaiting_messenger",
                "messengers": detected_m
            }
            msg_lines = ["Выберите мессенджер для отправки сообщения, сэр:"]
            for m in detected_m:
                msg_lines.append(f"{m['num']}. {m['name']}")
            msg_lines.append("\nНажмите кнопку ниже или отправьте цифру/название.")
            return {
                "type": "messenger_wizard",
                "message": "\n".join(msg_lines),
                "stage": "select_messenger",
                "options": [{"label": m["label"], "cmd": m["num"]} for m in detected_m],
                "messengers": detected_m
            }

    # 14. In-App Automation: Typing Text & Messages (Voice Sunder dictation)
    if any(c.startswith(verb) for verb in ["напиши ", "напечатай ", "введи ", "вбей ", "продиктуй ", "вставь ", "type ", "write "]):
        # Guard: If user asks AI to write/create code, scripts, programs, essays, poems, etc.
        # it is an AI GENERATION request, NOT a keyboard automation!
        ai_coding_terms = [
            "код", "скрипт", "программ", "функци", "класс", "алгоритм", "бот", "парсер",
            "запрос", "сочинени", "стих", "эссе", "рассказ", "стать", "текст про", "текст о",
            "письмо", "резюме", "план", "решение", "пример", "code", "script", "program", "function"
        ]
        lang_terms = [
            "на python", "на питон", "на js", "на javascript", "на c++", "на c#", "на html",
            "на css", "на sql", "на bash", "на баше", "на джаве", "на java", "на go", "на rust"
        ]
        if any(term in c for term in ai_coding_terms) or any(l in c for l in lang_terms):
            return None

        raw_text = re.sub(r'^(?:напиши|напечатай|введи|вбей|продиктуй|вставь|type|write)\s+(?:текст[:\s]+)?', '', orig_c, flags=re.IGNORECASE).strip()
        press_enter = False
        m_enter = re.search(r'\s+(?:и\s+)?(?:нажми\s+(?:enter|ввод|ентер)|нажми\s+кнопку\s+enter|отправь)$', raw_text, re.IGNORECASE)
        if m_enter:
            raw_text = raw_text[:m_enter.start()].strip()
            press_enter = True

        target_app = None
        field = None

        # Check for destination app / browser / search field
        m_dest = re.match(r'^(?:в\s+|на\s+)?(блокнот\w*|notepad|ворд\w*|word|документ\w*|телеграм\w*|тг|telegram|дискорд\w*|discord|хром\w*|chrome|браузер\w*|яндекс\w*|browser|поиск\w*|строк\w*\s+поиск\w*|адресн\w*\s+строк\w*|сайте?|страниц\w*)\s+(?:текст[:\s]+|сообщение[:\s]+|слово[:\s]+)?(.*)', raw_text, re.IGNORECASE)
        if m_dest:
            dest_tag = m_dest.group(1).lower()
            remaining_text = m_dest.group(2).strip()
            if any(k in dest_tag for k in ["блокнот", "notepad"]):
                target_app = "notepad"
            elif any(k in dest_tag for k in ["ворд", "word", "документ"]):
                target_app = "word"
            elif any(k in dest_tag for k in ["телеграм", "тг", "telegram"]):
                target_app = "telegram"
            elif any(k in dest_tag for k in ["дискорд", "discord"]):
                target_app = "discord"
            elif any(k in dest_tag for k in ["адресн", "строк"]):
                target_app = "chrome"
                field = "search"
                press_enter = True
            elif any(k in dest_tag for k in ["поиск", "сайт", "страниц"]):
                target_app = "chrome"
                field = "search"
            elif any(k in dest_tag for k in ["хром", "chrome", "браузер", "яндекс", "browser"]):
                target_app = "chrome"
            if remaining_text:
                raw_text = remaining_text

        # Strip prefixes like "ему", "ей", "им", "слово", "текст", "сообщение"
        raw_text = re.sub(r'^(?:ему\s+|ей\s+|им\s+|пользователю\s+|контакту\s+|в\s+чат\s+|в\s+диалог\s+)', '', raw_text, flags=re.IGNORECASE).strip()
        raw_text = re.sub(r'^(?:слово\s+|текст\s+|сообщение\s+|фразу\s+)', '', raw_text, flags=re.IGNORECASE).strip()
        # Strip outer quotes if present
        raw_text = re.sub(r'^["«\']|["»\']$', '', raw_text).strip()

        if raw_text:
            return {"type": "type_text", "text": raw_text, "target_app": target_app, "field": field, "press_enter": press_enter}

    # In-App Automation: Standalone Key Presses & Hotkeys
    if c in ["enter", "ввод", "ентер"]:
        return {"type": "press_key", "key": "enter"}
    if c in ["esc", "escape", "эскейп"]:
        return {"type": "press_key", "key": "esc"}
    if c in ["tab", "таб"]:
        return {"type": "press_key", "key": "tab"}

    if any(k in c for k in ["скопируй", "копируй", "copy"]):
        return {"type": "hotkey", "keys": ["ctrl", "c"]}
    if any(k in c for k in ["вставь", "paste"]):
        return {"type": "hotkey", "keys": ["ctrl", "v"]}
    if any(k in c for k in ["выдели все", "выдели всё", "select all"]):
        return {"type": "hotkey", "keys": ["ctrl", "a"]}
    if any(k in c for k in ["сохрани файл", "save file"]):
        return {"type": "hotkey", "keys": ["ctrl", "s"]}

    # 15. Plugin Commands
    if "плагин" in c or "plugin" in c:
        if any(k in c for k in ["запусти", "включи", "start", "run"]):
            p_name = re.sub(r'.*?(?:запусти|включи|start|run)\s+(?:плагин\s+)?', '', c).strip()
            if p_name:
                return {"type": "plugin_start", "plugin_name": p_name}
        elif any(k in c for k in ["останови", "выключи", "стоп", "stop"]):
            p_name = re.sub(r'.*?(?:останови|выключи|стоп|stop)\s+(?:плагин\s+)?', '', c).strip()
            if p_name:
                return {"type": "plugin_stop", "plugin_name": p_name}
        elif any(k in c for k in ["список", "какие", "покажи", "list", "status"]):
            return {"type": "plugin_list"}

    # 16. Universal Application Launch (Dynamic PC catalog & Start Menu discovery)
    # Check for bare verb without app name: e.g. "открой", "запусти"
    if c.strip() in ["открой", "открыть", "запусти", "запустить", "включи", "включить", "open", "launch", "start", "run"]:
        return {"type": "clarify", "message": "Уточните, пожалуйста, сэр: какое приложение или сайт вы хотите открыть?"}

    open_verbs = [
        "открой", "открыть", "запусти", "запустить", "включи", "включить", "стартуй",
        "зайди в", "зайди на", "зайди", "перейди в", "перейди на", "перейди",
        "open", "launch", "start", "run"
    ]
    has_open_verb = any(c.startswith(k) or f" {k} " in f" {c} " or c.endswith(k) for k in open_verbs)

    if has_open_verb:
        # Strip verb from either beginning OR end (handles "tiktok зайди" as well as "зайди в tiktok")
        target_app = re.sub(r'^(?:открой|открыть|запусти|запустить|включи|включить|стартуй|зайди\s+в|зайди\s+на|зайди|перейди\s+в|перейди\s+на|перейди|open|launch|start|run)\s+(?:приложение\s+|программу\s+|софт\s+)?', '', c).strip()
        target_app = re.sub(r'\s+(?:открой|открыть|запусти|запустить|включи|включить|зайди\s+в|зайди\s+на|зайди|перейди\s+в|перейди\s+на|перейди|open|launch|start|run)$', '', target_app).strip()
        target_app = re.sub(r'^(?:в\s+приложение|в\s+программу|приложение|программу|на\s+сайт|сайт)\s+', '', target_app).strip()
        target_app = re.sub(r'\s+(?:приложение|программу|на\s+сайт|сайт)$', '', target_app).strip()
        if not target_app or target_app in open_verbs:
            return {"type": "clarify", "message": "Уточните, пожалуйста, сэр: какое приложение или сайт вы хотите открыть?"}

        # Check for generic browser request
        if target_app in ["браузер", "browser", "интернет"]:
            if any(k in raw_c for k in ["какие браузеры", "какой браузер", "список браузеров", "выбери браузер", "выбрать браузер"]):
                browsers = sc.detect_installed_browsers()
                if len(browsers) > 1:
                    return {"type": "browser_choice", "browsers": browsers}
            return {"type": "launch_app", "app": "chrome"}

        for alias, canonical in APP_MAP.items():
            if alias == target_app or alias in target_app.split():
                return {"type": "launch_app", "app": canonical}
        return {"type": "launch_app", "app": target_app}

    # Short app names (e.g. "калькулятор", "chrome", "postman")
    if len(c.split()) <= 2:
        for alias, canonical in APP_MAP.items():
            if alias == c or alias in c:
                return {"type": "launch_app", "app": canonical}
        # Check if single word matches scanned apps
        catalog = sc.scan_all_installed_apps()
        if c in catalog:
            return {"type": "launch_app", "app": c}

    # 17. Math Calculation
    m_calc = safe_math_eval(c)
    if m_calc is not None:
        return {"type": "math", "expr": c, "res": m_calc}

    return None

def local_multi_action_planner(user_text: str) -> List[Dict[str, Any]]:
    """
    Intelligently splits complex compound user commands (chaining 2, 3, 4 actions)
    and maps them to sequential atomic executable operations with auto-delays.
    """
    # 0. If user_text directly maps to a unified action (e.g. messenger_send), execute directly without splitting
    single_act = parse_single_clause(user_text)
    if single_act and single_act.get("type") in ["messenger_send", "type_text", "search_web", "clarify", "browser_choice", "terminal_command", "play_music", "create_timer", "delete_timer", "create_task", "delete_task", "complete_task", "create_note", "delete_note", "list_tasks", "list_notes", "list_timers", "search_notes"]:
        return [single_act]

    # 1. Normalize verb boundaries to avoid missing clauses without punctuation
    # e.g. "Открой браузер сделай скриншот" -> "Открой браузер; сделай скриншот"
    verb_boundary = r'(?<=\w)\s+(?=(?:открой|запусти|зайди в|зайди на|зайди|перейди в|перейди на|перейди|найди чат|найди диалог|найди контакт|сделай скриншот|сделай скрин|заскринь|сохрани скриншот|закрой вкладку|смахни вкладку|закрой|выключи|напиши|напечатай|отправь|нажми|кликни|почисти корзину|очисти корзину|заблокируй|обнови|прокрути|поставь яркость|поставь звук|поставь громкость|поставь|установи|прибавь|убавь|создай файл|создай папку|создай|удали файл|удали папку|удали|проверь|проанализируй|список файлов)\b)'
    user_text_norm = re.sub(verb_boundary, '; ', user_text, flags=re.IGNORECASE)

    clauses = re.split(r'\b(и\s+потом|а\s+затем|после\s+этого|потом|затем|а\s+также|также|дальше|and\s+then|then)\b|[;,]', user_text_norm, flags=re.IGNORECASE)
    actions = []
    
    for clause in clauses:
        if not clause:
            continue
        clean_cl = re.sub(r'^\s*\b(и|а|дальше|затем|потом)\b\s*', '', clause, flags=re.IGNORECASE)
        clean_cl = re.sub(r'\s*\b(и|а|потом|затем)\b\s*$', '', clean_cl, flags=re.IGNORECASE).strip()
        if not clean_cl or clean_cl.lower() in ["и", "потом", "затем", "and", "then", "также", "еще", "дальше", "и потом", "а затем"]:
            continue
        act = parse_single_clause(clean_cl)
        if act:
            if act.get("type") == "press_key" and act.get("key") == "enter" and actions and actions[-1].get("type") == "type_text":
                actions[-1]["press_enter"] = True
                continue
            if act.get("type") == "save_destination":
                for prev in reversed(actions):
                    if prev.get("type") == "screenshot":
                        prev["folder"] = act.get("folder", "desktop")
                        break
                continue

            # If an application launch precedes type_text, propagate target_app
            if act.get("type") == "type_text" and not act.get("target_app"):
                for prev in reversed(actions):
                    if prev.get("type") == "launch_app" and prev.get("app"):
                        act["target_app"] = prev["app"]
                        break

            # If an application launch or URL open precedes a web interaction or screenshot, insert automatic wait
            if actions and actions[-1].get("type") in ["launch_app", "open_url", "search_web"]:
                if act.get("type") in ["screenshot", "click_website_button", "type_text", "press_key", "hotkey", "scroll_page", "switch_browser_tab", "close_browser_tab"]:
                    actions.append({"type": "wait", "seconds": 2.5})

            # If a close_app follows a screenshot or actions, ensure previous action has settled
            if act.get("type") == "close_app" and actions and actions[-1].get("type") in ["screenshot", "click_website_button", "type_text"]:
                actions.append({"type": "wait", "seconds": 1.0})

            actions.append(act)

    return actions

def neural_action_planner(user_text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Uses neural reasoning to decompose intricate, multi-step instructions into concrete JSON actions.
    First utilizes high-intelligence OpenRouter free engine, with local fallback.
    """
    cache_key = user_text.lower().strip()
    if cache_key in _AI_PLAN_CACHE:
        return _AI_PLAN_CACHE[cache_key]

    # 1. Primary high-intelligence OpenRouter Free Engine
    try:
        _, acts = openrouter_engine.query_openrouter(user_text)
        if acts and len(acts) > 0:
            wants_close = any(k in user_text.lower() for k in ["закрой", "выйди", "выруби", "close", "kill", "exit", "quit"])
            if not wants_close:
                acts = [a for a in acts if a.get("type") != "close_app"]
            if acts:
                if len(_AI_PLAN_CACHE) > 200:
                    _AI_PLAN_CACHE.clear()
                _AI_PLAN_CACHE[cache_key] = acts
                return acts
    except Exception as e:
        print(f"[Argus Planner Notice]: OpenRouter planner: {e}")

    instruction = (
        "You are an expert Windows & macOS Desktop Automation Planner. "
        "Decompose user instruction into an array of concrete JSON action objects. "
        "Output ONLY a raw JSON array, with no markdown, no explanation, no backticks.\n"
        "Available action types:\n"
        "- {\"type\": \"play_music\", \"service\": \"spotify\" | \"yandex\" | \"soundcloud\" | \"vk\" | \"youtube\" | \"auto\", \"query\": \"...\", \"playlist\": \"...\", \"action\": \"play\" | \"pause\" | \"next\" | \"prev\"}\n"
        "- {\"type\": \"launch_app\", \"app\": \"chrome\" | \"telegram\" | \"discord\" | \"whatsapp\" | \"notepad\" | \"word\" | \"...\"}\n"
        "- {\"type\": \"messenger_send\", \"messenger\": \"telegram\" | \"discord\" | \"whatsapp\" | \"vk\" | \"auto\", \"contact\": \"...\", \"message\": \"...\"}\n"
        "- {\"type\": \"type_text\", \"text\": \"...\", \"target_app\": \"...\", \"press_enter\": true | false}\n"
        "- {\"type\": \"open_url\", \"url\": \"https://...\"}\n"
        "- {\"type\": \"search_web\", \"query\": \"...\", \"engine\": \"google\" | \"yandex\" | \"youtube\"}\n"
        "- {\"type\": \"screenshot\", \"folder\": \"downloads\" | \"desktop\" | \"documents\" | \"pictures\"}\n"
        "- {\"type\": \"close_app\", \"app\": \"...\"}\n"
        "- {\"type\": \"press_key\", \"key\": \"enter\" | \"tab\" | \"esc\" | \"space\"}\n"
        "- {\"type\": \"hotkey\", \"keys\": [\"ctrl\", \"v\"] | [\"cmd\", \"v\"]}\n"
        "- {\"type\": \"wait\", \"seconds\": 1.5}\n"
        "CRITICAL RULES:\n"
        "1. NEVER generate 'close_app' UNLESS the user explicitly asked to close or exit ('закрой', 'выйди', 'close'). Keep all opened messengers and apps OPEN.\n"
        "2. If user asks to find a chat and write a message (e.g. 'найди чат Alex и напиши привет' or 'зайди в телеграм и напиши в Node.js слово привет'), output a single 'messenger_send' or 'launch_app' + 'type_text', NEVER 'close_app'.\n"
        "3. If user asks to play music, a playlist, pause or next track in Spotify, Yandex Music, SoundCloud, use 'play_music'.\n"
        "Examples:\n"
        "- Instruction: включи плейлист рок в спотифай\n"
        "  JSON: [{\"type\":\"play_music\",\"service\":\"spotify\",\"playlist\":\"рок\",\"action\":\"play\"}]\n"
        "- Instruction: выключи то что играет\n"
        "  JSON: [{\"type\":\"play_music\",\"action\":\"pause\"}]\n"
        "- Instruction: найди чат alex и напиши сообщение привет\n"
        "  JSON: [{\"type\":\"messenger_send\",\"messenger\":\"auto\",\"contact\":\"Alex\",\"message\":\"привет\"}]\n"
        "- Instruction: зайди в телеграм и напиши в Node.js слово привет\n"
        "  JSON: [{\"type\":\"messenger_send\",\"messenger\":\"telegram\",\"contact\":\"Node.js\",\"message\":\"привет\"}]\n"
        "- Instruction: открой блокнот и напиши Привет мир\n"
        "  JSON: [{\"type\":\"launch_app\",\"app\":\"notepad\"},{\"type\":\"wait\",\"seconds\":1.2},{\"type\":\"type_text\",\"text\":\"Привет мир\",\"target_app\":\"notepad\"}]"
    )

    combined = f"[{instruction}]\n\nInstruction: {user_text}"
    payload = {
        "messages": [
            {"role": "user", "content": combined}
        ]
    }
    try:
        req = urllib.request.Request(
            "https://text.pollinations.ai/",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=6.5) as resp:
            raw = resp.read().decode("utf-8").strip()
            clean_json = re.sub(r'^```(?:json)?\s*', '', raw)
            clean_json = re.sub(r'\s*```$', '', clean_json).strip()
            m_arr = re.search(r'\[\s*\{.*\}\s*\]', clean_json, re.DOTALL)
            if m_arr:
                clean_json = m_arr.group(0)
            parsed = json.loads(clean_json)
            if isinstance(parsed, list) and len(parsed) > 0:
                wants_close = any(k in user_text.lower() for k in ["закрой", "выйди", "выруби", "close", "kill", "exit", "quit"])
                if not wants_close:
                    parsed = [a for a in parsed if a.get("type") != "close_app"]
                if len(_AI_PLAN_CACHE) > 200:
                    _AI_PLAN_CACHE.clear()
                _AI_PLAN_CACHE[cache_key] = parsed
                return parsed
    except Exception:
        pass
    return None

# ─── FREE NEURAL REASONING ENGINE ───────────────────────────────
def query_free_ai(prompt: str, user_name: str = "Пользователь", history: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    """
    Queries OpenRouter free neural reasoning model with full multi-turn conversation memory.
    Provides deep, smart, accurate responses strictly without emojis.
    """
    cache_key = prompt.lower().strip()
    if not history and cache_key in _AI_QUERY_CACHE:
        return _AI_QUERY_CACHE[cache_key]

    # 1. Primary high-intelligence OpenRouter Free Assistant
    try:
        reply, _ = openrouter_engine.query_openrouter(prompt, user_name=user_name, history=history)
        if reply and len(reply.strip()) > 1:
            if len(_AI_QUERY_CACHE) > 200:
                _AI_QUERY_CACHE.clear()
            _AI_QUERY_CACHE[cache_key] = reply.strip()
            return reply.strip()
    except Exception as e:
        print(f"[Argus OpenRouter Query Notice]: {e}")

    mem_summary = user_memory.get_memory_summary()
    instruction = (
        f"Ты — Argus AI, персональный автономный высокоинтеллектуальный ИИ-ассистент для пользователя {user_name}.\n"
        f"{mem_summary}\n"
        "Отвечай интеллектуально, точно, полезно, грамотно, вежливо и строго БЕЗ ЭМОДЗИ на языке пользователя."
    )
    messages = [{"role": "user", "content": f"[{instruction}]"}]
    if history:
        for h in history[-8:]:
            r = "user" if h.get("role") == "user" else "assistant"
            cnt = h.get("content", "").strip()
            if cnt:
                messages.append({"role": r, "content": cnt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "messages": messages
    }
    try:
        req = urllib.request.Request(
            "https://text.pollinations.ai/",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            text = resp.read().decode("utf-8").strip()
            cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', text).strip()
            cleaned = re.sub(r'^\[.*?\]\s*', '', cleaned).strip()
            if cleaned and len(cleaned) > 2:
                if len(_AI_QUERY_CACHE) > 200:
                    _AI_QUERY_CACHE.clear()
                _AI_QUERY_CACHE[cache_key] = cleaned
                return cleaned
    except Exception:
        pass
    return None

# ─── LOCAL PERSONA KNOWLEDGE BASE (OFFLINE FALLBACK) ────────────
CONVERSATIONAL_KNOWLEDGE = {
    "привет": "Приветствую, сэр. Все системы Argus активны и готовы к работе. Чем могу помочь?",
    "hello": "Hello. All Argus systems are operational and ready. How can I assist you?",
    "как дела": "Все модули Argus функционируют в штатном режиме, сэр. Ожидаю ваших указаний.",
    "how are you": "All systems operating at peak performance. Ready for your instructions.",
    "что делаешь": "Работаю в фоновом режиме, сэр. Жду ваших команд. Чем могу помочь?",
    "чем занимаешься": "Работаю в фоновом режиме, сэр. Жду ваших команд. Готов к любой задаче.",
    "что делаем": "Жду ваших указаний, сэр. Готов запустить приложение, открыть сайт, написать код или выполнить любую задачу.",
    "кто ты": "Я Argus, сэр — ваш персональный автономный ИИ-ассистент для глубокого управления Windows и macOS, автоматизации задач, работы с браузером и написания кода.",
    "who are you": "I am Argus, sir — your personal autonomous AI assistant for Windows and macOS control, workflow automation, and productivity.",
    "что ты умеешь": "Я умею полноценно управлять компьютером: открывать любые сайты и нажимать кнопки на страницах, запускать и закрывать любые программы (Chrome, Telegram, Discord, VS Code, GoLand, Postman, Steam и др.), создавать и удалять файлы и папки на компьютере, анализировать содержимое файлов, делать скриншоты в любую папку (Загрузки, Рабочий стол), настраивать громкость и яркость экрана («на полную», «в ноль»), закрывать программы с фильтрами исключений («кроме vs code»), очищать корзину, блокировать ПК, искать в Google, YouTube, Wildberries и Ozon, а также управлять плагинами.",
    "почему небо синее": "Небо кажется синим из-за рэлеевского рассеяния солнечного света в атмосфере: газы атмосферы рассеивают короткие синие и фиолетовые волны значительно сильнее, чем длинные красные.",
    "почему небо голубое": "Небо голубое благодаря рэлеевскому рассеянию: солнечный свет рассеивается молекулами воздуха, при этом коротковолновые синие и голубые лучи рассеиваются сильнее всего.",
    "нет": "Хорошо, сэр, отменил. Ожидаю ваших указаний.",
    "не надо": "Понял вас, сэр, отменяю. Чем могу помочь?",
    "не нужно": "Хорошо, сэр, не буду. Ожидаю следующих команд.",
    "отмена": "Действие отменено, сэр. Жду ваших указаний.",
    "отбой": "Принято, сэр, отбой. Системы готовы к работе.",
    "стоп": "Остановил выполнение, сэр. Ожидаю дальнейших указаний.",
    "хватит": "Хорошо, сэр, остановился. Чем займёмся дальше?",
    "понял": "Отлично, сэр. Всегда готов к новым задачам.",
    "понятно": "Договорились, сэр. Если что-то понадобится — обращайтесь.",
    "ясно": "Принято, сэр. Готов к выполнению любых команд.",
    "ок": "Принято, сэр. Что делаем дальше?",
    "хорошо": "Вас понял, сэр. Готов продолжить работу.",
    "ладно": "Хорошо, сэр. Ожидаю ваших команд.",
    "да": "Слушаю вас, сэр. Какую задачу выполняем?",
}

def generate_smart_code_reply(prompt: str) -> Optional[str]:
    """Generates clean, well-commented, working scripts for code requests."""
    low = prompt.lower().strip()
    is_code_req = any(k in low for k in [
        "напиши код", "напиши скрипт", "напиши программу", "напиши функцию",
        "создай скрипт", "создай код", "write code", "write a script", "python script",
        "код на python", "скрипт на python", "код на питоне", "скрипт на питоне"
    ])
    if not is_code_req:
        return None

    if any(k in low for k in ["парсер", "парсинг", "скачай сайт", "scraping", "scraper"]):
        return (
            "Вот готовый скрипт для веб-скрейпинга и парсинга на Python:\n\n"
            "```python\n"
            "import requests\n"
            "from bs4 import BeautifulSoup\n\n"
            "def scrape_website(url: str):\n"
            "    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}\n"
            "    try:\n"
            "        response = requests.get(url, headers=headers, timeout=10)\n"
            "        response.raise_for_status()\n"
            "        soup = BeautifulSoup(response.text, 'html.parser')\n"
            "        \n"
            "        title = soup.title.string if soup.title else 'Без заголовка'\n"
            "        print(f'Заголовок: {title}')\n"
            "        \n"
            "        links = [a.get('href') for a in soup.find_all('a', href=True)]\n"
            "        print(f'Найдено ссылок: {len(links)}')\n"
            "        return links\n"
            "    except Exception as e:\n"
            "        print(f'Ошибка запроса: {e}')\n"
            "        return []\n\n"
            "if __name__ == '__main__':\n"
            "    scrape_website('https://example.com')\n"
            "```\n\n"
            "Скрипт использует библиотеки `requests` и `beautifulsoup4`. Установка: `pip install requests beautifulsoup4`."
        )

    if any(k in low for k in ["сортировк", "быстрая сортировка", "пузырек", "quicksort", "сортируй"]):
        return (
            "Вот реализация алгоритма быстрой сортировки (QuickSort) на Python:\n\n"
            "```python\n"
            "def quicksort(arr: list) -> list:\n"
            "    if len(arr) <= 1:\n"
            "        return arr\n"
            "    pivot = arr[len(arr) // 2]\n"
            "    left = [x for x in arr if x < pivot]\n"
            "    middle = [x for x in arr if x == pivot]\n"
            "    right = [x for x in arr if x > pivot]\n"
            "    return quicksort(left) + middle + quicksort(right)\n\n"
            "if __name__ == '__main__':\n"
            "    data = [64, 34, 25, 12, 22, 11, 90]\n"
            "    print('Исходный массив:', data)\n"
            "    print('Отсортированный:', quicksort(data))\n"
            "```\n\n"
            "Средняя сложность алгоритма — O(n log n)."
        )

    if any(k in low for k in ["node", "nodejs", "node.js", "js", "javascript"]) and any(k in low for k in ["бот", "telegram", "телеграм"]):
        return (
            "Вот готовый и проверенный код Telegram-бота на Node.js, сэр:\n\n"
            "```javascript\n"
            "// 1. Инициализация проекта: npm init -y\n"
            "// 2. Установка библиотеки: npm install node-telegram-bot-api\n\n"
            "const TelegramBot = require('node-telegram-bot-api');\n\n"
            "// Замените на токен вашего бота от @BotFather\n"
            "const token = process.env.TELEGRAM_BOT_TOKEN || 'ВАШ_ТОКЕН_БОТА';\n\n"
            "// Создаем экземпляр бота с включенным поллингом\n"
            "const bot = new TelegramBot(token, { polling: true });\n\n"
            "console.log('Бот успешно запущен и ожидает сообщений...');\n\n"
            "// Обработка команды /start\n"
            "bot.onText(/\\/start/, (msg) => {\n"
            "    const chatId = msg.chat.id;\n"
            "    const userName = msg.from.first_name || 'Пользователь';\n"
            "    bot.sendMessage(chatId, `Здравствуйте, ${userName}! Я простой эхо-бот на Node.js.`);\n"
            "});\n\n"
            "// Обработка команды /help\n"
            "bot.onText(/\\/help/, (msg) => {\n"
            "    const chatId = msg.chat.id;\n"
            "    bot.sendMessage(chatId, 'Доступные команды:\\n/start — начать диалог\\n/help — справка\\nИли просто напишите мне любое сообщение.');\n"
            "});\n\n"
            "// Эхо-ответ на любые входящие текстовые сообщения\n"
            "bot.on('message', (msg) => {\n"
            "    // Пропускаем команды, чтобы не дублировать ответ\n"
            "    if (msg.text && !msg.text.startsWith('/')) {\n"
            "        const chatId = msg.chat.id;\n"
            "        bot.sendMessage(chatId, `Вы написали: ${msg.text}`);\n"
            "    }\n"
            "});\n\n"
            "// Обработка ошибок опроса сервера\n"
            "bot.on('polling_error', (error) => {\n"
            "    console.error('Ошибка поллинга:', error.code, error.message);\n"
            "});\n"
            "```\n\n"
            "**Инструкция по запуску:**\n"
            "1. Создайте файл `bot.js` и вставьте в него код выше.\n"
            "2. Установите зависимость: `npm install node-telegram-bot-api`.\n"
            "3. Запустите бота командой: `node bot.js`.\n\n"
            "Все модули готовы к работе, сэр."
        )

    if any(k in low for k in ["бот", "telegram bot", "тг бот"]):
        return (
            "Вот базовый шаблон асинхронного Telegram-бота на Python, сэр:\n\n"
            "```python\n"
            "import asyncio\n"
            "from aiogram import Bot, Dispatcher, types\n"
            "from aiogram.filters import Command\n\n"
            "BOT_TOKEN = 'ВАШ_ТОКЕН_БОТА'\n\n"
            "bot = Bot(token=BOT_TOKEN)\n"
            "dp = Dispatcher()\n\n"
            "@dp.message(Command('start'))\n"
            "async def send_welcome(message: types.Message):\n"
            "    await message.reply('Привет! Я бот, запущенный на Python.')\n\n"
            "@dp.message()\n"
            "async def echo(message: types.Message):\n"
            "    await message.answer(f'Вы написали: {message.text}')\n\n"
            "async def main():\n"
            "    await dp.start_polling(bot)\n\n"
            "if __name__ == '__main__':\n"
            "    asyncio.run(main())\n"
            "```\n\n"
            "Для запуска установите aiogram: `pip install aiogram`."
        )

    # General elegant Python script template
    return (
        "Вот готовый, чистый и расширяемый скрипт на Python с обработкой ошибок и логированием:\n\n"
        "```python\n"
        "import os\n"
        "import sys\n"
        "import logging\n"
        "from pathlib import Path\n\n"
        "# Настройка логирования\n"
        "logging.basicConfig(\n"
        "    level=logging.INFO,\n"
        "    format='%(asctime)s [%(levelname)s] %(message)s',\n"
        "    datefmt='%H:%M:%S'\n"
        ")\n\n"
        "def main_task(target_dir: str = '.'):\n"
        "    path = Path(target_dir).resolve()\n"
        "    logging.info(f'Запуск скрипта в директории: {path}')\n"
        "    \n"
        "    if not path.exists():\n"
        "        logging.error(f'Директория {path} не найдена!')\n"
        "        return False\n"
        "        \n"
        "    files = list(path.glob('*'))\n"
        "    logging.info(f'Найдено объектов: {len(files)}')\n"
        "    for item in files[:10]:\n"
        "        item_type = 'Папка' if item.is_dir() else 'Файл'\n"
        "        logging.info(f' - [{item_type}] {item.name}')\n"
        "    \n"
        "    logging.info('Задача успешно завершена.')\n"
        "    return True\n\n"
        "if __name__ == '__main__':\n"
        "    main_task()\n"
        "```\n\n"
        "Скрипт готов к запуску в терминале: `python script.py`. Если вам требуется конкретная функциональность — напишите детали задачи."
    )

def query_encyclopedia_knowledge(query: str, en: bool) -> Optional[str]:
    """
    Instantly fetches factual definitions and summaries (0.2s latency)
    for knowledge questions across science, technology, hardware, and concepts.
    Supports multi-concept queries, interrogative questions, and typo auto-correction.
    """
    clean_q = query.strip().rstrip('?.!').strip()
    low_q = clean_q.lower()
    
    # Exclude conversational greetings, smalltalk, and personal questions
    _CONVERSATIONAL_BLACKLIST = [
        "как дела", "как жизнь", "как ты", "как поживаешь", "как успехи", "как настроение",
        "кто ты", "что ты умеешь", "привет", "здравствуй", "что делаешь", "чем занимаешься",
        "что делаем", "что нового", "как у тебя", "что ты", "ты кто", "ты что",
        "как тебя зовут", "что можешь", "что умеешь", "ты живой", "ты бот", "ты робот",
        "что слышно", "что скажешь", "что думаешь", "какие новости",
        "what are you doing", "how are you", "who are you", "what can you do"
    ]
    if any(s in low_q for s in _CONVERSATIONAL_BLACKLIST):
        return None
    
    prefixes = [
        "что такое ", "кто такой ", "кто такая ", "кто такие ", "что значит ",
        "что это такое ", "что это ", "расскажи про ", "расскажи о ", "расскажи об ",
        "объясни что такое ", "объясни ", "для чего нужен ", "для чего нужна ", "для чего нужно ",
        "для чего нужны ", "зачем нужен ", "зачем нужна ", "зачем нужно ", "зачем нужны ",
        "как работает ", "как устроен ", "как устроена ", "как устроены ",
        "what is ", "who is ", "what are ", "tell me about ", "how does ", "why is "
    ]
    target_topic = None
    for p in prefixes:
        if low_q.startswith(p):
            target_topic = clean_q[len(p):].strip()
            break
            
    # Only fall back to keyword extraction for SHORT explicit factual questions (<=3 words ending in ?)
    # Do NOT trigger on conversational/action phrases like "что делаешь", "как смотришь"
    if not target_topic:
        words = clean_q.split()
        if len(words) <= 3 and query.strip().endswith('?'):
            _fact_stop = {
                'для', 'чего', 'нужен', 'нужна', 'нужно', 'нужны', 'что', 'такое', 'такой', 'такая', 'такие',
                'как', 'почему', 'где', 'когда', 'кто', 'это', 'бывает', 'ли', 'же', 'мне'
            }
            nouns = [w for w in re.findall(r'[a-zA-Zа-яА-ЯёЁ0-9\-]+', clean_q) if w.lower() not in _fact_stop]
            # Must have at least 1 real noun AND it must not be a common verb
            _common_verbs = {
                'делаешь', 'делаем', 'делать', 'делаю', 'знаешь', 'думаешь', 'хочешь', 'можешь',
                'смотришь', 'слышишь', 'видишь', 'скажешь', 'думаем', 'идет', 'идёт', 'будет',
                'стоит', 'говоришь', 'означает', 'занимаешься', 'помнишь', 'работаешь',
                'doing', 'going', 'mean', 'think', 'happen'
            }
            if nouns and not any(n.lower() in _common_verbs for n in nouns):
                target_topic = ' '.join(nouns)
            
    if not target_topic or len(target_topic) < 2:
        return None

    lang = "en" if en else "ru"
    terms = [t.strip() for t in re.split(r'\s+(?:и|или|and|or)\s+|,', target_topic) if t.strip()]
    if not terms:
        terms = [target_topic]

    summaries = []

    for term in terms:
        # 1. Direct page summary
        found = False
        try:
            topic_enc = urllib.parse.quote(term.replace(' ', '_'))
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{topic_enc}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ArgusAI/2.4 (https://github.com/argus; contact@argus.ai)"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                extract = data.get("extract")
                title = data.get("title")
                if extract and len(extract) > 20:
                    clean_extract = re.sub(r'[\u0300-\u036f]', '', extract).replace('\xa0', ' ').strip()
                    clean_title = re.sub(r'[\u0300-\u036f]', '', title).replace('\xa0', ' ').strip()
                    summaries.append(f"{clean_title}: {clean_extract}")
                    found = True
        except Exception:
            pass

        if found:
            continue

        # 2. Wikipedia Search API with typo suggestion (e.g. 'Депортамент' -> 'департамент')
        try:
            s_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(term)}&format=json&utf8=1"
            req_s = urllib.request.Request(s_url, headers={"User-Agent": "ArgusAI/2.4 (https://github.com/argus)"})
            with urllib.request.urlopen(req_s, timeout=3.5) as resp_s:
                s_data = json.loads(resp_s.read().decode("utf-8"))
                query_info = s_data.get("query", {})
                suggestion = query_info.get("searchinfo", {}).get("suggestion")
                hits = query_info.get("search", [])

                best_term = suggestion or (hits[0]["title"] if hits else None)
                if best_term:
                    b_enc = urllib.parse.quote(best_term.replace(' ', '_'))
                    u_best = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{b_enc}"
                    req_b = urllib.request.Request(u_best, headers={"User-Agent": "ArgusAI/2.4 (https://github.com/argus)"})
                    with urllib.request.urlopen(req_b, timeout=3.5) as resp_b:
                        d_b = json.loads(resp_b.read().decode("utf-8"))
                        ext_b = d_b.get("extract")
                        t_b = d_b.get("title")
                        if ext_b and len(ext_b) > 20:
                            clean_extract = re.sub(r'[\u0300-\u036f]', '', ext_b).replace('\xa0', ' ').strip()
                            clean_title = re.sub(r'[\u0300-\u036f]', '', t_b).replace('\xa0', ' ').strip()
                            summaries.append(f"{clean_title}: {clean_extract}")
        except Exception:
            pass

    if summaries:
        if len(summaries) == 1:
            return summaries[0]
        return "\n\n".join(f"• {s}" for s in summaries)

    return None

def get_conversational_reply(raw_text: str, en: bool, user_name: str = "Пользователь", history: Optional[List[Dict[str, Any]]] = None) -> str:
    """Provides high-quality, crisp, intelligent answers without default emojis."""
    # 1. Primary: Query OpenRouter Free High-Intelligence Engine
    try:
        or_reply, _ = openrouter_engine.query_openrouter(raw_text, user_name=user_name, history=history)
        if or_reply and len(or_reply.strip()) > 1 and not openrouter_engine.is_reasoning_leak(or_reply):
            return or_reply.strip()
    except Exception as e:
        print(f"[Argus OpenRouter Brain Notice]: {e}")

    # 1.1 Local conversational phrases & greetings
    t = raw_text.lower().strip()
    clean_t = re.sub(r'[^\w\s]', '', t)
    for k, reply in CONVERSATIONAL_KNOWLEDGE.items():
        if re.search(r'(?:\b|^)' + re.escape(k) + r'(?:\b|$)', clean_t):
            return reply

    # 1.2 Code Generation check
    code_reply = generate_smart_code_reply(raw_text)
    if code_reply:
        return code_reply

    # 1.5 Math / Equation Solver check
    eq = solve_algebraic_equation(raw_text)
    if eq:
        return eq

    # 2. Factual encyclopedia fallback (Wikipedia definition & typo search)
    wiki_resp = query_encyclopedia_knowledge(raw_text, en)
    if wiki_resp:
        return wiki_resp

    # 4. Smart local conversational fallback
    mem = user_memory.load_memory()
    u_name = mem.get("name") or user_name
    if en:
        return f"Understood, {u_name}. I am on standby and ready to assist you with system tasks, apps, or answer any questions."
    else:
        low_t = raw_text.lower().strip()
        if any(g in low_t for g in ["спасибо", "благодарю"]):
            return "Пожалуйста, сэр. Всегда к вашим услугам. Чем ещё могу быть полезен?"
        if any(g in low_t for g in ["отлично", "хорошо", "супер", "класс", "молодец"]):
            return "Рад помочь, сэр. Все системы функционируют штатно и ждут ваших задач."
        if any(g in low_t for g in ["пока", "до свидания", "до встречи"]):
            return "До связи, сэр. Все службы Argus остаются на страже и ждут ваших указаний."
        if any(h in low_t for h in ["привет", "здравствуй", "добрый день", "добрый вечер", "доброе утро"]):
            return f"Здравствуйте, сэр! Чем могу помочь вам сегодня за компьютером?"
        if any(re.search(r'\b' + re.escape(w) + r'\b', low_t) for w in ["нет", "не", "не надо", "не нужно", "отмена", "отбой"]):
            return "Хорошо, сэр, отменил. Ожидаю ваших указаний."
        if any(re.search(r'\b' + re.escape(w) + r'\b', low_t) for w in ["стоп", "хватит", "остановись", "прекрати"]):
            return "Остановил выполнение, сэр. Ожидаю дальнейших указаний."

        # Questions fallback: Check user notes first
        is_q = "?" in raw_text or any(low_t.startswith(w + " ") or low_t == w for w in [
            "как", "кто", "где", "когда", "почему", "зачем", "сколько",
            "какой", "какая", "какое", "какие", "что", "чем", "куда", "откуда"
        ])
        if is_q:
            try:
                matches = extras_mgr.search_notes(raw_text)
                if matches:
                    best = matches[0]
                    return f"Судя по вашей заметке «{best.get('title')}», сэр:\n{best.get('content')}"
            except Exception:
                pass
            return "В ваших сохранённых заметках и памяти пока нет информации по этому вопросу, сэр. Вы можете сказать мне нужные данные или добавить заметку, и я обязательно сохраню их."

        return f"Готов к выполнению ваших задач, сэр. Скажите, что требуется сделать, или задайте вопрос."

# ─── MAIN MASTER ENTRY POINT ────────────────────────────────────
def process_command(user_text: str, user_name: str = "Пользователь", history: Optional[List[Dict[str, Any]]] = None) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
    """
    Main processing entrypoint for Argus AI.
    Executes local multi-step intent parsing in <1ms for 100% reliable system control,
    with smart free neural LLM reasoning fallback and multi-turn context memory.
    """
    raw = user_text.strip()
    en = is_english(raw)

    # 0. User Memory & Learning (0ms response time)
    learned_reply = user_memory.extract_and_learn(raw)
    if learned_reply:
        return learned_reply, "general", {}

    memory_reply = user_memory.query_memory_question(raw, has_history=bool(history))
    if memory_reply:
        return memory_reply, "general", {}

    # 0. Contextual Pronoun & Folder/File Resolution (using dialogue history)
    # e.g. "закрой его", "закрой её", "удали его", "удали эту папку", "удали папку", "удали эту", "проверь его"
    resolved_text = raw
    low_raw = raw.lower()
    if history and any(p in low_raw for p in ["его", "ее", "её", "это", "туда же", "эту", "ту", "папку", "папка", "файл"]):
        for prev_msg in reversed(history):
            prev_content = prev_msg.get("content", "")

            # 1. Check if user wants to delete previously created folder
            # e.g. previous was "Папка создана: C:\Users\stuck\Desktop\text"
            if any(k in low_raw for k in ["удали", "delete", "сотри", "уничтожь"]):
                m_fld = re.search(r'Папка создана:\s*([a-zA-Z]:[\\/][^\s\.\n\r]+|/[^\s\.\n\r]+|[a-zA-Z]:[\\/][^\n\r]+|/[^\n\r]+)', prev_content)
                if m_fld:
                    target_folder = m_fld.group(1).strip().rstrip('.')
                    resolved_text = f"удали папку {target_folder}"
                    break

            # 2. Check if previous launched an app: e.g. "Запущено приложение: GoLand"
            m_app = re.search(r'Запущено приложение:\s*([a-zA-Z0-9_\- ]+)', prev_content)
            if m_app and any(k in low_raw for k in ["закрой", "close", "выключи"]):
                app_name = m_app.group(1).strip()
                resolved_text = re.sub(r'\b(его|ее|её|это|эту|ту)\b', app_name, resolved_text, flags=re.IGNORECASE)
                break

            # 3. Check if previous was a screenshot or file path
            m_file = re.search(r'([a-zA-Z]:[\\/][^\s\)\"\']+\.[a-zA-Z0-9]{2,4}|/[^\s\)\"\']+\.[a-zA-Z0-9]{2,4})', prev_content)
            if m_file:
                target_f = m_file.group(1).strip()
                if any(k in low_raw for k in ["удали", "delete", "сотри"]):
                    resolved_text = f"удали файл {target_f}"
                    break
                if any(k in low_raw for k in ["проверь", "проанализируй", "посмотри"]):
                    resolved_text = f"проанализируй файл {target_f}"
                    break

    # 0.5 Custom & Built-in Scenarios (0ms execution e.g. "рабочий режим", "игровой режим", "чистый стол")
    matched_sc = sc_mgr.match_scenario_by_trigger(resolved_text)
    if matched_sc:
        res = sc_mgr.execute_scenario(matched_sc)
        return res["summary"], "scenario", {"scenario_id": matched_sc.get("id"), "scenario_name": matched_sc.get("name")}

    # 0.7 Interactive Stateful Messenger Wizard (Windows & macOS)
    # Allows selecting messenger by button or number/text -> entering contact/username -> entering message text
    raw_low = raw.lower()
    
    # Cancellation check
    if any(k == raw_low or raw_low.startswith(k + " ") for k in ["отмена", "отбой", "стоп", "назад", "хватит", "не надо", "забудь", "cancel"]):
        if user_name in _MESSENGER_WIZARD_STATE or "default" in _MESSENGER_WIZARD_STATE:
            _MESSENGER_WIZARD_STATE.pop(user_name, None)
            _MESSENGER_WIZARD_STATE.pop("default", None)
            return "Мастер отправки сообщений отменён, сэр. Ожидаю ваших указаний.", "clarify", {}

    active_user_key = user_name if user_name in _MESSENGER_WIZARD_STATE else ("default" if "default" in _MESSENGER_WIZARD_STATE else None)
    if active_user_key:
        state = _MESSENGER_WIZARD_STATE[active_user_key]
        stage = state.get("stage")

        if stage == "awaiting_messenger":
            messengers = state.get("messengers", [])
            selected = None
            for m in messengers:
                if raw_low in [m["num"], f"{m['num']}.", f"{m['num']})", f"{m['num']} "]:
                    selected = m
                    break
                if m["id"] in raw_low or m["name"].lower() in raw_low:
                    selected = m
                    break
                if ("тг" in raw_low or "телеграм" in raw_low) and m["id"] == "telegram":
                    selected = m
                    break
                if ("вк" in raw_low or "вконтакте" in raw_low) and m["id"] == "vk":
                    selected = m
                    break
                if ("дискорд" in raw_low or "discord" in raw_low) and m["id"] == "discord":
                    selected = m
                    break
                if ("ватсап" in raw_low or "whatsapp" in raw_low) and m["id"] == "whatsapp":
                    selected = m
                    break

            if selected:
                state["messenger"] = selected["id"]
                state["messenger_name"] = selected["name"]
                if state.get("contact"):
                    state["stage"] = "awaiting_text"
                    reply_text = (
                        f"Мессенджер {selected['name']} выбран для контакта «{state['contact']}», сэр.\n\n"
                        f"Введите текст сообщения, которое нужно отправить:"
                    )
                    return reply_text, "messenger_wizard", {
                        "stage": "enter_text",
                        "messenger": selected["id"],
                        "contact": state["contact"]
                    }
                else:
                    state["stage"] = "awaiting_contact"
                    reply_text = (
                        f"Мессенджер {selected['name']} выбран, сэр.\n\n"
                        f"Введите имя контакта или ник/юзернейм получателя (например: @username или Алексей):"
                    )
                    return reply_text, "messenger_wizard", {
                        "stage": "enter_contact",
                        "messenger": selected["id"]
                    }
            else:
                return (
                    f"Пожалуйста, выберите мессенджер из списка (введите цифру 1-{len(messengers)} или нажмите кнопку):",
                    "messenger_wizard",
                    {"stage": "select_messenger", "options": [{"label": m["label"], "cmd": m["num"]} for m in messengers], "messengers": messengers}
                )

        elif stage == "awaiting_contact":
            clean_contact = re.sub(r'^(?:контакт\w*|пользовател\w*|для|человек\w*|друг\w*|ник\w*|юзер\w*)\s+', '', raw.strip(), flags=re.IGNORECASE).strip()
            clean_contact = re.sub(r'^(?:в\s+чат\s+|в\s+диалог\s+)', '', clean_contact, flags=re.IGNORECASE).strip()
            clean_contact = clean_contact.strip('"\'«»')
            
            # Check if user entered both contact AND message e.g. "Siax Привет"
            parts = clean_contact.split(None, 1)
            if len(parts) > 1 and not clean_contact.startswith('@'):
                contact = parts[0]
                msg_text = parts[1]
                m_id = state["messenger"]
                m_name = state.get("messenger_name", m_id.capitalize())
                _MESSENGER_WIZARD_STATE.pop(active_user_key, None)
                res = gui_agent.execute_autonomous_messenger_task(m_id, contact, msg_text)
                return (
                    f"Сообщение для контакта «{contact}» в {m_name} успешно отправлено: «{msg_text}», сэр.",
                    "messenger_send",
                    res
                )

            if clean_contact.lower() in INVALID_CONTACT_KEYWORDS or not clean_contact:
                return (
                    "Пожалуйста, укажите имя контакта или ник/юзернейм (например: @username или Алексей), сэр:",
                    "messenger_wizard",
                    {"stage": "enter_contact", "messenger": state["messenger"]}
                )

            state["contact"] = clean_contact
            state["stage"] = "awaiting_text"
            reply_text = (
                f"Контакт «{clean_contact}» принят, сэр.\n\n"
                f"Введите текст сообщения, которое нужно отправить:"
            )
            return reply_text, "messenger_wizard", {
                "stage": "enter_text",
                "messenger": state["messenger"],
                "contact": clean_contact
            }

        elif stage == "awaiting_text":
            msg_text = raw.strip()
            m_id = state["messenger"]
            m_name = state.get("messenger_name", m_id.capitalize())
            contact = state["contact"]
            _MESSENGER_WIZARD_STATE.pop(active_user_key, None)
            res = gui_agent.execute_autonomous_messenger_task(m_id, contact, msg_text)
            return (
                f"Сообщение для контакта «{contact}» в {m_name} успешно отправлено: «{msg_text}», сэр.",
                "messenger_send",
                res
            )


    # 1. First, check if input contains any system actions (single or compound) locally (<1ms)
    actions_to_run = local_multi_action_planner(resolved_text)
    ai_confirmed_reply = None

    # 2. If no actions found locally, check equations, math & time
    if not actions_to_run:
        eq_sol = solve_algebraic_equation(resolved_text)
        if eq_sol:
            return eq_sol, "math", {"solution": eq_sol}

        m_calc = safe_math_eval(resolved_text)
        if m_calc is not None:
            reply = f"Result: {m_calc}" if en else f"Результат вычисления: {m_calc}"
            return reply, "math", {"result": m_calc}

        if any(k in resolved_text.lower() for k in ["время", "time", "который час", "сколько времени"]):
            t_str = datetime.datetime.now().strftime("%H:%M")
            return f"Current time is {t_str}." if en else f"Текущее время: {t_str}.", "time", {"time": t_str}

        if any(k in resolved_text.lower() for k in ["число", "дата", "date", "какое число", "какой день"]):
            now = datetime.datetime.now()
            d_str = now.strftime("%d.%m.%Y")
            return f"Today is {d_str}." if en else f"Сегодня: {d_str}.", "date", {"date": d_str}

    # 3. If no local action, consult OpenRouter Free Engine for smart desktop assistance / action planning
    if not actions_to_run:
        try:
            or_reply, or_acts = openrouter_engine.query_openrouter(resolved_text, user_name=user_name, history=history)
            if or_acts and len(or_acts) > 0:
                wants_close = any(k in resolved_text.lower() for k in ["закрой", "выйди", "выруби", "close", "kill", "exit", "quit"])
                if not wants_close:
                    or_acts = [a for a in or_acts if a.get("type") != "close_app"]
                if or_acts:
                    actions_to_run = or_acts
                    if or_reply and len(or_reply.strip()) > 2 and not openrouter_engine.is_reasoning_leak(or_reply):
                        ai_confirmed_reply = or_reply.strip()
            elif or_reply and len(or_reply.strip()) > 1 and not openrouter_engine.is_reasoning_leak(or_reply):
                return or_reply.strip(), "general", {}
        except Exception as e:
            print(f"[Argus OpenRouter Brain Notice]: {e}")

    # 4. If OpenRouter returned no action and no reply, consult neural action planner / conversational fallback
    if not actions_to_run:
        action_verb_count = len(re.findall(r'\b(открой|запусти|скриншот|скрин|закрой|сохрани|напиши|отправь|перейди|найди|search|close|open)\b', resolved_text, re.IGNORECASE))
        if action_verb_count >= 2:
            ai_plan = neural_action_planner(resolved_text)
            if ai_plan:
                actions_to_run = ai_plan

    # 5. If still no action found, handle conversational query via free AI reasoning engine with history
    if not actions_to_run:
        reply = get_conversational_reply(resolved_text, en, user_name, history=history)
        return reply, "general", {}

    # 6. Sequentially execute all planned actions
    executed_results = []
    primary_action_type = "multi_action" if len(actions_to_run) > 1 else actions_to_run[0].get("type", "general")
    primary_data = {}

    for act in actions_to_run:
        msg, a_type, a_data = execute_single_action(act)
        if a_type != "noop" and a_type != "wait":
            primary_data.update(a_data)
            if len(actions_to_run) == 1:
                primary_action_type = a_type
            elif a_type == "screenshot":
                primary_data["screenshot_path"] = a_data.get("path")
            if msg:
                executed_results.append(msg)

    # 7. Formulate clear Russian/English confirmation
    if ai_confirmed_reply:
        final_reply = ai_confirmed_reply
    elif executed_results:
        final_reply = ". ".join(executed_results)
        if not final_reply.endswith(('.', '!', '?', '»')):
            final_reply += "."
    else:
        final_reply = "Все задачи успешно выполнены." if not en else "All tasks completed successfully."

    return final_reply, primary_action_type, primary_data
