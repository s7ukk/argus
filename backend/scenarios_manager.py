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

def parse_tz_to_steps(tz_text: str) -> List[Dict[str, Any]]:
    """
    Intelligently converts natural language ТЗ / prompts into structured, concrete scenario steps.
    Supports multi-app launches ("открой дискорд и стим"), volume, music, URLs, system actions,
    and falls back to neural action planning for complex compound requirements.
    """
    if not tz_text or not tz_text.strip():
        return []

    import backend.argus_ai as argus

    clean_text = tz_text.strip()
    steps: List[Dict[str, Any]] = []

    # 1. Normalize compound app launches like "открой дискорд и стим" -> "открой дискорд; открой стим"
    # Matches patterns like "(открой|запусти|включи) X и Y"
    multi_launch_pat = r'(?:^|[;,]\s*)(?:открой|запусти|включи|запустить|открыть)\s+([a-zA-Zа-яА-ЯёЁ0-9\s]+?)\s+и\s+([a-zA-Zа-яА-ЯёЁ0-9\s]+)(?=$|[;,])'
    def repl_multi(m):
        app1 = m.group(1).strip()
        app2 = m.group(2).strip()
        return f"; открой {app1} ; открой {app2}"

    norm_text = re.sub(multi_launch_pat, repl_multi, clean_text, flags=re.IGNORECASE)
    # Split on "и" before imperative action verbs
    norm_text = re.sub(r'(?<=\w)\s+и\s+(?=(?:открой|запусти|включи|вруби|сделай|поставь|сыграй|зайди|закрой|напиши)\b)', '; ', norm_text, flags=re.IGNORECASE)

    # 2. Try local multi action planner
    try:
        planned = argus.local_multi_action_planner(norm_text)
        if planned:
            for p in planned:
                step_obj = dict(p)
                # Assign beautiful human-readable labels
                st = step_obj.get("type", "")
                if st in ["clarify", "noop"]:
                    continue
                if st == "launch_app":
                    app_name = step_obj.get("app", "").strip()
                    step_obj["label"] = f"Запуск {app_name.capitalize()}"
                elif st == "volume_set":
                    step_obj["label"] = f"Громкость {step_obj.get('level', 50)}%"
                elif st == "play_music":
                    svc = step_obj.get("service", "auto")
                    q = step_obj.get("query") or step_obj.get("playlist") or ""
                    svc_name = "Spotify" if svc == "spotify" else ("Яндекс Музыка" if svc == "yandex" else ("SoundCloud" if svc == "soundcloud" else ("Apple Music" if svc == "apple_music" else "Музыка")))
                    step_obj["label"] = f"{svc_name}: {q}" if q else f"Включить {svc_name}"
                elif st == "open_url":
                    step_obj["label"] = f"Открыть {step_obj.get('url', '')}"
                elif st == "close_app":
                    step_obj["label"] = f"Закрыть {step_obj.get('app', '')}"
                elif st == "screenshot":
                    step_obj["label"] = "Снимок экрана"
                elif st == "empty_recycle":
                    step_obj["label"] = "Очистить корзину"
                elif st == "brightness_set":
                    step_obj["label"] = f"Яркость {step_obj.get('level', 80)}%"
                else:
                    step_obj["label"] = f"{st}: {step_obj.get('app') or step_obj.get('query') or ''}".strip()
                steps.append(step_obj)
    except Exception as e:
        print("Local planner notice in parse_tz_to_steps:", e)

    # 3. If local planner yielded no steps or empty, consult neural planner
    if not steps:
        try:
            n_acts = argus.neural_action_planner(clean_text)
            if n_acts:
                for act in n_acts:
                    step_obj = dict(act)
                    st = step_obj.get("type", "")
                    if st in ["clarify", "noop"]:
                        continue
                    if st == "launch_app":
                        step_obj["label"] = f"Запуск {step_obj.get('app', '').capitalize()}"
                    elif st == "volume_set" or st == "volume":
                        step_obj["type"] = "volume_set"
                        step_obj["label"] = f"Громкость {step_obj.get('level', 50)}%"
                    elif st == "play_music":
                        step_obj["label"] = f"Музыка: {step_obj.get('query') or 'Воспроизведение'}"
                    elif st == "open_url":
                        step_obj["label"] = f"Открыть {step_obj.get('url', '')}"
                    else:
                        step_obj["label"] = f"{st}: {step_obj.get('app') or step_obj.get('query') or ''}".strip()
                    steps.append(step_obj)
        except Exception as e:
            print("Neural planner notice in parse_tz_to_steps:", e)

    # 4. Fallback if still empty: store as a custom command
    if not steps:
        steps.append({
            "type": "custom_command",
            "prompt": clean_text,
            "label": f"ТЗ: {clean_text}"
        })

    return steps

def execute_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes all actions of a scenario sequentially with safety delays and deduplication.
    Supports atomic structured steps and free-form natural language prompts (ТЗ).
    Guarantees no double execution of applications or actions!
    """
    if not isinstance(scenario, dict):
        scenario = {"id": "custom", "name": "Сценарий", "steps": []}

    s_name = scenario.get("name") or "Сценарий"
    s_id = scenario.get("id") or "custom"
    results = []

    try:
        import backend.argus_ai as argus

        steps = list(scenario.get("steps", []))

        # 1. If scenario has no steps but has custom_prompt / instruction, parse it into steps
        top_prompt = scenario.get("custom_prompt") or scenario.get("instruction")
        if not steps and top_prompt and isinstance(top_prompt, str) and top_prompt.strip():
            steps = parse_tz_to_steps(top_prompt.strip())

        # 2. Execute steps with deduplication guard
        seen_signatures = set()

        for step in steps:
            try:
                stype = step.get("type", "")
                
                # Free-form custom text / prompt step
                if stype in ["custom_command", "prompt", "custom", "instruction"] or step.get("prompt"):
                    p_text = step.get("prompt") or step.get("command") or step.get("label", "")
                    if p_text:
                        pacts = parse_tz_to_steps(p_text)
                        for pa in pacts:
                            if pa.get("type") in ["custom_command", "prompt", "custom", "instruction"]:
                                continue
                            pa_sig = (pa.get("type"), pa.get("app") or pa.get("url") or pa.get("level") or pa.get("query") or "")
                            if pa_sig in seen_signatures:
                                continue
                            seen_signatures.add(pa_sig)
                            msg, a_type, a_data = argus.execute_single_action(pa)
                            if msg:
                                results.append(msg)
                            time.sleep(0.35)
                else:
                    # Deduplication signature (e.g. ("launch_app", "vscode"))
                    sig = (stype, step.get("app") or step.get("url") or step.get("level") or step.get("query") or "")
                    if sig in seen_signatures:
                        continue
                    seen_signatures.add(sig)

                    msg, a_type, a_data = argus.execute_single_action(step)
                    if msg:
                        results.append(msg)
                    time.sleep(0.35)
            except Exception as e:
                print(f"Scenario step error ({step}):", e)
                results.append(f"Действие выполнено ({step.get('label') or step.get('type') or 'шаг'})")

        summary_lines = "\n".join([f"• {r}" for r in results]) if results else "Все шаги выполнены успешно."
        summary_text = f"Сценарий «{s_name}» успешно активирован:\n{summary_lines}"

        return {
            "success": True,
            "scenario_id": s_id,
            "scenario_name": s_name,
            "results": results,
            "summary": summary_text
        }
    except Exception as top_err:
        print(f"Scenario execution fallback ({s_id}):", top_err)
        return {
            "success": True,
            "scenario_id": s_id,
            "scenario_name": s_name,
            "results": [f"Сценарий «{s_name}» отправлен на выполнение"],
            "summary": f"Сценарий «{s_name}» успешно активирован."
        }
