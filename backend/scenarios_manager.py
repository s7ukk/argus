import os
import json
import re
import time
from typing import List, Dict, Any, Optional
import backend.system_control as sc
import backend.app_paths as app_paths

SCENARIOS_FILE = app_paths.get_data_file_path("user_scenarios.json")

DEFAULT_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "work_mode",
        "name": "Рабочий режим",
        "icon": "Briefcase",
        "triggers": ["рабочий режим", "режим работы", "за работу", "work mode", "рабочее место"],
        "description": "Устанавливает звук на 30%, запускает VS Code, включает музыку и открывает GitHub",
        "is_builtin": True,
        "steps": [
            {"type": "volume_set", "level": 30, "label": "Громкость 30%"},
            {"type": "launch_app", "app": "vscode", "label": "Запуск VS Code"},
            {"type": "play_music", "service": "auto", "query": "lofi hip hop focus", "action": "play", "label": "Фокус-музыка"},
            {"type": "open_url", "url": "https://github.com", "label": "Открыть GitHub"}
        ]
    },
    {
        "id": "game_mode",
        "name": "Игровой режим",
        "icon": "Gamepad2",
        "triggers": ["игровой режим", "режим игры", "время играть", "погнали играть", "game mode"],
        "description": "Выставляет звук на 65%, запускает Discord и Steam, закрывает лишние программы",
        "is_builtin": True,
        "steps": [
            {"type": "volume_set", "level": 65, "label": "Громкость 65%"},
            {"type": "close_app", "app": "vscode", "label": "Закрыть редактор кода"},
            {"type": "launch_app", "app": "discord", "label": "Запуск Discord"},
            {"type": "launch_app", "app": "steam", "label": "Запуск Steam"},
            {"type": "brightness_set", "level": 100, "label": "Яркость 100%"}
        ]
    },
    {
        "id": "chill_mode",
        "name": "Режим отдыха",
        "icon": "Coffee",
        "triggers": ["режим отдыха", "чилл режим", "время отдыхать", "чилл", "chill mode"],
        "description": "Выставляет звук на 40%, открывает YouTube и запускает расслабляющий плейлист",
        "is_builtin": True,
        "steps": [
            {"type": "volume_set", "level": 40, "label": "Громкость 40%"},
            {"type": "open_url", "url": "https://www.youtube.com", "label": "Открыть YouTube"},
            {"type": "play_music", "service": "auto", "query": "chill vibes lofi", "action": "play", "label": "Чилл-музыка"}
        ]
    },
    {
        "id": "clean_desk",
        "name": "Чистый рабочий стол",
        "icon": "Sparkles",
        "triggers": ["чистый стол", "чистый рабочий стол", "наведи порядок", "очисти стол", "clean desk"],
        "description": "Закрывает лишние программы, очищает корзину и сохраняет снимок экрана",
        "is_builtin": True,
        "steps": [
            {"type": "close_all_except", "keep": ["chrome", "argus"], "label": "Закрыть лишние окна"},
            {"type": "empty_recycle", "label": "Очистить корзину"},
            {"type": "screenshot", "folder": "desktop", "label": "Снимок экрана на рабочий стол"}
        ]
    }
]

def load_scenarios() -> List[Dict[str, Any]]:
    """Loads scenarios with defaults merged."""
    scenarios_map = {s["id"]: s.copy() for s in DEFAULT_SCENARIOS}
    if os.path.exists(SCENARIOS_FILE):
        try:
            with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
                user_list = json.load(f)
                if isinstance(user_list, list):
                    for u in user_list:
                        if isinstance(u, dict) and "id" in u:
                            scenarios_map[u["id"]] = u
        except Exception as e:
            print("Load scenarios notice:", e)
    return list(scenarios_map.values())

def save_user_scenarios(scenarios: List[Dict[str, Any]]) -> bool:
    """Saves user-modified scenarios to disk."""
    try:
        # Only save custom or modified scenarios
        with open(SCENARIOS_FILE, "w", encoding="utf-8") as f:
            json.dump(scenarios, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("Save scenarios error:", e)
        return False

def add_or_update_scenario(scenario_data: Dict[str, Any]) -> Dict[str, Any]:
    all_s = load_scenarios()
    s_id = scenario_data.get("id") or f"custom_{int(time.time())}"
    scenario_data["id"] = s_id
    
    # Clean triggers
    raw_trigs = scenario_data.get("triggers", [])
    if isinstance(raw_trigs, str):
        raw_trigs = [t.strip().lower() for t in raw_trigs.split(",") if t.strip()]
    scenario_data["triggers"] = list(set([t.lower().strip() for t in raw_trigs if t.strip()]))
    
    updated = False
    for i, s in enumerate(all_s):
        if s["id"] == s_id:
            all_s[i] = scenario_data
            updated = True
            break
    if not updated:
        all_s.append(scenario_data)

    save_user_scenarios(all_s)
    return scenario_data

def delete_scenario(scenario_id: str) -> bool:
    all_s = load_scenarios()
    new_s = [s for s in all_s if s["id"] != scenario_id or s.get("is_builtin")]
    save_user_scenarios(new_s)
    return True

def match_scenario_by_trigger(text: str) -> Optional[Dict[str, Any]]:
    """Checks if incoming user instruction triggers any registered scenario with strict word boundaries."""
    raw_t = text.lower().strip()
    clean_t = re.sub(r'^(?:аргус|argus|эй\s+аргус|привет\s+аргус|включи|запусти|активируй|перейди\s+в|выполни)\s+', '', raw_t).strip()
    clean_t = re.sub(r'^(?:режим\s+)?', '', clean_t).strip()

    if not clean_t:
        return None

    all_s = load_scenarios()
    for s in all_s:
        for trig in s.get("triggers", []):
            trig_clean = trig.lower().strip()
            if not trig_clean:
                continue
            # 1. Exact match
            if clean_t == trig_clean or raw_t == trig_clean:
                return s
            # 2. Strict word boundary match (e.g. "включи режим отдыха")
            # Never allow short substrings like "hi" inside "chill mode"!
            if len(trig_clean) >= 3:
                pattern = rf'(?<![a-zA-Zа-яА-Я0-9]){re.escape(trig_clean)}(?![a-zA-Zа-яА-Я0-9])'
                if re.search(pattern, clean_t) or re.search(pattern, raw_t):
                    return s
    return None

def execute_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes all actions of a scenario sequentially with safety delays.
    Supports atomic structured steps and free-form natural language prompts (ТЗ).
    """
    # Import locally to avoid circular dependencies
    import backend.argus_ai as argus

    steps = scenario.get("steps", [])
    s_name = scenario.get("name", "Сценарий")
    results = []

    # 1. Top-level custom prompt (ТЗ) if provided
    top_prompt = scenario.get("custom_prompt") or scenario.get("instruction")
    if top_prompt and isinstance(top_prompt, str) and top_prompt.strip():
        try:
            planned_actions = argus.local_multi_action_planner(top_prompt.strip())
            for pact in planned_actions:
                msg, a_type, a_data = argus.execute_single_action(pact)
                if msg:
                    results.append(msg)
                time.sleep(0.35)
        except Exception as e:
            print(f"Top-level custom prompt execution error ({top_prompt}):", e)

    # 2. Structured & prompt steps
    for step in steps:
        try:
            stype = step.get("type", "")
            # Check for free-form custom text / prompt step
            if stype in ["custom_command", "prompt", "custom", "instruction"] or step.get("prompt"):
                p_text = step.get("prompt") or step.get("command") or step.get("label", "")
                if p_text:
                    pacts = argus.local_multi_action_planner(p_text)
                    for pa in pacts:
                        msg, a_type, a_data = argus.execute_single_action(pa)
                        if msg:
                            results.append(msg)
                        time.sleep(0.35)
            else:
                msg, a_type, a_data = argus.execute_single_action(step)
                if msg:
                    results.append(msg)
                time.sleep(0.35)
        except Exception as e:
            print(f"Scenario step error ({step}):", e)

    summary_lines = "\n".join([f"• {r}" for r in results]) if results else "Все шаги выполнены успешно."
    summary_text = f"Сценарий «{s_name}» успешно активирован:\n{summary_lines}"

    return {
        "success": True,
        "scenario_id": scenario.get("id"),
        "scenario_name": s_name,
        "results": results,
        "summary": summary_text
    }
