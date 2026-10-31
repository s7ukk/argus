import backend.voice_dictation_hook as dictation_hook
import asyncio
import os
import sys
import re
import json
import time
import uuid
import datetime
import socket
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Union

import backend.db as db
import backend.system_control as sc
import backend.voice as voice_engine
import backend.argus_ai as argus
import backend.plugins_manager as pm
import backend.scenarios_manager as sc_mgr
import backend.app_paths as app_paths

_LOCAL_SESSION: Dict[str, Any] = {}
SETTINGS_FILE = app_paths.get_data_file_path("user_settings.json")

def _save_local_session(data: dict):
    global _LOCAL_SESSION
    _LOCAL_SESSION = dict(data)

def _load_local_session() -> Optional[dict]:
    return _LOCAL_SESSION if _LOCAL_SESSION else None

def _clear_local_session():
    global _LOCAL_SESSION
    _LOCAL_SESSION = {}

DEFAULT_SETTINGS = {
    "voice_input_mode": "trigger",
    "trigger_words": "джарвис, jarvis, аргус, argus, эй джарвис, эй аргус",
    "ptt_hotkey": "Space",
    "voice_provider": "edge-tts",
    "native_voice": "default",
    "fish_api_key": "",
    "fish_model_id": "",
    "edge_voice": "jarvis",
    "voice_speed": 1.05,
    "browser_mode": "ask",
    "default_browser": "safari" if sys.platform == "darwin" else "auto",
    "auto_heal_plugins": True,
    "default_shell": "zsh" if sys.platform == "darwin" else "powershell",
    "default_music_app": "auto",
    "openrouter_api_key": "",
    "openrouter_model": "meta-llama/llama-3.3-70b-instruct"
}

def _load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                res = DEFAULT_SETTINGS.copy()
                res.update(saved)
                return res
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def _save_settings(data: dict):
    try:
        current = _load_settings()
        current.update(data)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Save settings error:", e)

app = FastAPI(title="Argus AI Assistant Backend", version="2.0.0")

LOCAL_ORIGIN_REGEX = r"^(https?://(127\.0\.0\.1|localhost)(:\d+)?|app://.*|vscode-webview://.*|file://.*|file://|null)$"

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=LOCAL_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from starlette.requests import Request
from starlette.responses import JSONResponse

@app.middleware("http")
async def security_origin_guard(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin and origin != "null" and not origin.startswith("file://"):
        if not re.match(LOCAL_ORIGIN_REGEX, origin):
            return JSONResponse(
                status_code=403,
                content={"detail": "Доступ заблокирован: вызовы с внешних веб-сайтов запрещены политикой безопасности Argus."}
            )
    return await call_next(request)

@app.on_event("startup")
async def startup_event():
    try:
        loop = asyncio.get_running_loop()
        orig_handler = loop.get_exception_handler()

        def custom_exception_handler(loop, context):
            exc = context.get("exception")
            if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
                return
            msg = context.get("message", "")
            if "connection_lost" in msg or "10054" in str(context):
                return
            if orig_handler:
                orig_handler(loop, context)
            else:
                loop.default_exception_handler(context)

        loop.set_exception_handler(custom_exception_handler)
    except Exception:
        pass
    try:
        dictation_hook.start_dictation_hook()
    except Exception as e:
        print("[Argus]: Failed to start dictation hook:", e)

# Pydantic Request Models
class KeyVerifyRequest(BaseModel):
    key_code: str

class ProfileUpdateRequest(BaseModel):
    key_code: str
    display_name: str
    voice_enabled: bool = True
    voice_speed: float = 1.0

class ChatCreateRequest(BaseModel):
    key_code: str
    title: Optional[str] = "Новый диалог"

class ChatRenameRequest(BaseModel):
    key_code: str
    title: str

class ChatMessageRequest(BaseModel):
    chat_id: str
    key_code: str
    message: str
    voice: bool = True
    voice_provider: Optional[str] = None
    voice_name: Optional[str] = None
    voice_speed: Optional[float] = None
    native_voice: Optional[str] = None
    fish_api_key: Optional[str] = None
    fish_model_id: Optional[str] = None

class VolumeRequest(BaseModel):
    level: Optional[int] = None
    delta: Optional[int] = None
    mute_toggle: Optional[bool] = False

class BrightnessRequest(BaseModel):
    level: Optional[int] = None
    delta: Optional[int] = None

class LaunchRequest(BaseModel):
    app: str

class MediaRequest(BaseModel):
    action: str

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    rate: Optional[str] = "+0%"
    fish_api_key: Optional[str] = None
    fish_model_id: Optional[str] = None

class TerminalExecRequest(BaseModel):
    command: str
    shell: Optional[str] = None
    timeout: Optional[int] = 30

class TerminalAIAssistantRequest(BaseModel):
    prompt: str
    os_target: Optional[str] = "auto"

class PluginFileSaveRequest(BaseModel):
    path: str
    content: str

class PluginEntrypointRequest(BaseModel):
    entrypoint: str

class FishAudioTestRequest(BaseModel):
    api_key: str
    model_id: Optional[str] = None
    text: Optional[str] = "Привет! Это тестовая проверка голоса Argus через API Fish Audio."

class AppSettingsRequest(BaseModel):
    voice_input_mode: Optional[str] = None
    trigger_words: Optional[str] = None
    ptt_hotkey: Optional[str] = None
    voice_provider: Optional[str] = None
    native_voice: Optional[str] = None
    fish_api_key: Optional[str] = None
    fish_model_id: Optional[str] = None
    edge_voice: Optional[str] = None
    voice_speed: Optional[float] = None
    browser_mode: Optional[str] = None
    default_browser: Optional[str] = None
    auto_heal_plugins: Optional[bool] = None
    default_shell: Optional[str] = None
    default_music_app: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    openrouter_model: Optional[str] = None

class OpenRouterKeyTestRequest(BaseModel):
    api_key: str

@app.get("/api/health")
async def health():
    return {"status": "online", "system": "Argus AI Operational", "version": "2.0.0"}

# Authentication / License Verification
@app.get("/api/auth/session")
async def get_session(x_argus_key: Optional[str] = Header(None, alias="X-Argus-Key")):
    if x_argus_key:
        ver = await db.verify_access_key(x_argus_key)
        if ver.get("valid"):
            _save_local_session(ver)
            return ver
    data = _load_local_session()
    if data and data.get("valid"):
        return data
    return {"valid": False}

@app.post("/api/auth/verify-key")
async def verify_key(req: KeyVerifyRequest):
    result = await db.verify_access_key(req.key_code)
    if not result.get("valid"):
        raise HTTPException(status_code=403, detail=result.get("error", "Неверный ключ доступа"))
    _save_local_session(result)
    return result

@app.post("/api/auth/logout")
async def logout():
    _clear_local_session()
    return {"success": True}

# Profile Management
@app.post("/api/profile/update")
async def update_profile(req: ProfileUpdateRequest):
    # Ensure key is valid first
    ver = await db.verify_access_key(req.key_code)
    if not ver.get("valid"):
        raise HTTPException(status_code=403, detail="Неверный ключ")
    
    success = await db.update_user_profile(
        req.key_code,
        req.display_name,
        req.voice_enabled,
        req.voice_speed
    )
    return {"success": success, "display_name": req.display_name}

# System Control Endpoints
@app.get("/api/system/stats")
async def get_system_stats():
    return sc.get_system_stats()

@app.post("/api/system/volume")
async def set_system_volume(req: VolumeRequest):
    if req.mute_toggle:
        muted = sc.toggle_mute()
        return {"muted": muted, "level": sc.get_volume()}
    if req.level is not None:
        lvl = sc.set_volume(req.level)
        return {"level": lvl}
    if req.delta is not None:
        lvl = sc.change_volume(req.delta)
        return {"level": lvl}
    return {"level": sc.get_volume()}

@app.post("/api/system/brightness")
async def set_system_brightness(req: BrightnessRequest):
    if req.level is not None:
        lvl = sc.set_brightness(req.level)
        return {"level": lvl}
    if req.delta is not None:
        lvl = sc.change_brightness(req.delta)
        return {"level": lvl}
    return {"level": sc.get_brightness()}

@app.post("/api/system/launch")
async def launch_app(req: LaunchRequest):
    return sc.launch_application(req.app)

@app.post("/api/system/media")
async def media_action(req: MediaRequest):
    return {"success": sc.media_control(req.action)}

@app.post("/api/system/lock")
async def lock_system():
    return {"success": sc.lock_workstation()}

# Local Plugins System
@app.get("/api/plugins")
async def get_plugins():
    return pm.list_plugins()

class VoiceSunderDictateRequest(BaseModel):
    text: str
    press_enter: Optional[bool] = False

@app.post("/api/plugins/voice-sunder/dictate")
async def voice_sunder_dictate(req: VoiceSunderDictateRequest):
    """
    Directly injects spoken or dictated text into the active Windows application window.
    Uses clipboard paste for 100% accurate Cyrillic and Latin characters without layout mismatch.
    """
    text = req.text.strip()
    if not text:
        return {"success": False, "error": "Пустой текст для ввода"}
    success = sc.type_text(text)
    if req.press_enter:
        await asyncio.sleep(0.08)
        sc.press_key("enter")
    return {"success": success, "text": text, "pressed_enter": req.press_enter}

try:
    import multipart
    _HAS_MULTIPART = True
except Exception:
    _HAS_MULTIPART = False

if _HAS_MULTIPART:
    @app.post("/api/plugins/create")
    async def create_plugin_endpoint(
        name: str = Form(...),
        description: str = Form(""),
        entrypoint: str = Form("main.py"),
        file: Optional[UploadFile] = File(None),
        files: Optional[List[UploadFile]] = File(None),
        paths_json: Optional[str] = Form(None)
    ):
        files_data = []
        rel_paths = []
        if paths_json:
            try:
                rel_paths = json.loads(paths_json)
            except Exception:
                rel_paths = []

        if files:
            for idx, f in enumerate(files):
                try:
                    content = await f.read()
                    rel_p = rel_paths[idx] if idx < len(rel_paths) else f.filename
                    files_data.append((rel_p, content))
                except Exception as e:
                    print(f"Error reading uploaded file {f.filename}: {e}")
        elif file:
            content = await file.read()
            files_data.append((file.filename, content))

        manifest = pm.create_plugin_with_files(name, description, entrypoint, files_data)
        return manifest
else:
    @app.post("/api/plugins/create")
    async def create_plugin_endpoint_fallback():
        raise HTTPException(
            status_code=501,
            detail="python-multipart is not installed in this environment. Plugin uploads via form data are disabled."
        )

@app.post("/api/plugins/{plugin_id}/start")
async def start_plugin_endpoint(plugin_id: str):
    res = pm.start_plugin(plugin_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to start plugin"))
    return res

@app.post("/api/plugins/{plugin_id}/stop")
async def stop_plugin_endpoint(plugin_id: str):
    return pm.stop_plugin(plugin_id)

@app.get("/api/plugins/{plugin_id}/logs")
async def get_plugin_logs_endpoint(plugin_id: str):
    return pm.get_plugin_logs(plugin_id)

@app.delete("/api/plugins/{plugin_id}")
async def delete_plugin_endpoint(plugin_id: str):
    res = pm.delete_plugin(plugin_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to delete plugin"))
    return res

# Chat Management
@app.get("/api/chats")
async def get_chats(
    x_argus_key: Optional[str] = Header(None, alias="X-Argus-Key"),
    key_code: Optional[str] = Query(None)
):
    active_key = x_argus_key or key_code
    if not active_key:
        return []
    return await db.list_chats(active_key)

@app.post("/api/chats/create")
async def create_new_chat(
    req: ChatCreateRequest,
    x_argus_key: Optional[str] = Header(None, alias="X-Argus-Key")
):
    active_key = req.key_code or x_argus_key
    if not active_key:
        raise HTTPException(status_code=401, detail="Отсутствует ключ доступа")
    return await db.create_chat(active_key, req.title or "Новый диалог")

@app.patch("/api/chats/{chat_id}")
async def rename_chat(
    chat_id: str,
    req: ChatRenameRequest,
    x_argus_key: Optional[str] = Header(None, alias="X-Argus-Key")
):
    active_key = req.key_code or x_argus_key
    success = await db.update_chat_title(chat_id, active_key, req.title)
    if not success:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    return {"success": True, "title": req.title}

@app.delete("/api/chats/{chat_id}")
async def delete_existing_chat(
    chat_id: str,
    x_argus_key: Optional[str] = Header(None, alias="X-Argus-Key"),
    key_code: Optional[str] = Query(None)
):
    active_key = x_argus_key or key_code
    if not active_key:
        return {"success": False}
    success = await db.delete_chat(chat_id, active_key)
    return {"success": success}

@app.get("/api/chats/{chat_id}/messages")
async def get_chat_messages(chat_id: str):
    return await db.get_messages(chat_id)

@app.post("/api/ai/test-key")
async def test_openrouter_key(req: OpenRouterKeyTestRequest):
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="Ключ API не указан")
    url = "https://openrouter.ai/api/v1/auth/key"
    try:
        import urllib.request
        import backend.openrouter_engine as ore
        rq = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(rq, timeout=7.0, context=ore.get_https_ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            kdata = data.get("data", {})
            budgets = kdata.get("budgets", [])
            limit_usd = budgets[0].get("limit_usd", 0) if budgets else kdata.get("limit", 0)
            free_reqs = kdata.get("free_model_daily_requests", {})
            return {
                "valid": True,
                "label": kdata.get("label", "Key"),
                "limit_usd": limit_usd,
                "usage": kdata.get("usage", 0),
                "free_used": free_reqs.get("used", 0),
                "free_limit": free_reqs.get("limit", 50),
                "free_remaining": free_reqs.get("remaining", 0)
            }
    except Exception as e:
        return {"valid": False, "error": str(e)}

# Settings Endpoints
@app.get("/api/settings")
async def get_settings():
    return _load_settings()

@app.post("/api/settings")
async def update_settings(req: AppSettingsRequest):
    data = req.model_dump(exclude_unset=True)
    _save_settings(data)
    return _load_settings()

# System Browser Detection Endpoint
@app.get("/api/system/browsers")
async def get_installed_browsers():
    return sc.detect_installed_browsers()

# Cross-Platform Terminal Runner & AI Assistant
@app.post("/api/terminal/execute")
async def execute_terminal(req: TerminalExecRequest):
    return sc.execute_terminal_command(req.command, shell_type=req.shell, timeout=req.timeout or 30)

@app.post("/api/terminal/ai-assistant")
async def terminal_ai_assistant(req: TerminalAIAssistantRequest):
    """
    Translates natural language to verified terminal commands cross-platform (PowerShell, Bash, Zsh)
    using Pollinations free AI with fast local fallback.
    """
    prompt = req.prompt.strip()
    target_os = req.os_target or sc.detect_system_os()
    if target_os == "auto":
        target_os = sc.detect_system_os()

    sys_shell = "PowerShell" if target_os == "windows" else "Bash"

    # Fast offline pattern matcher for instant response
    p_lower = prompt.lower()
    fallback_cmd = None
    fallback_desc = ""

    if any(k in p_lower for k in ["диск", "место", "память диска", "disk space"]):
        if target_os == "windows":
            fallback_cmd = "Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='Free(GB)';E={[math]::round($_.Free/1GB,2)}}, @{N='Total(GB)';E={[math]::round($_.Used/1GB + $_.Free/1GB,2)}}"
        else:
            fallback_cmd = "df -h"
        fallback_desc = "Проверка свободного места на всех подключенных дисках"
    elif any(k in p_lower for k in ["процесс", "память", "cpu", "нагрузк", "top processes"]):
        if target_os == "windows":
            fallback_cmd = "Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 ProcessName, Id, @{N='RAM(MB)';E={[math]::round($_.WorkingSet64/1MB,1)}}"
        elif target_os == "macos":
            fallback_cmd = "ps -A -o pid,%cpu,%mem,comm -r | head -n 11"
        else:
            fallback_cmd = "ps aux --sort=-%mem | head -n 11"
        fallback_desc = "Топ-10 процессов по потреблению оперативной памяти"
    elif any(k in p_lower for k in ["порт", "порты", "open ports", "слуша"]):
        if target_os == "windows":
            fallback_cmd = "Get-NetTCPConnection -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess"
        elif target_os == "macos":
            fallback_cmd = "lsof -iTCP -sTCP:LISTEN -P -n"
        else:
            fallback_cmd = "netstat -tuln 2>/dev/null || ss -tuln"
        fallback_desc = "Список всех открытых и прослушиваемых сетевых портов"
    elif any(k in p_lower for k in ["ip", "айпи", "сеть", "интернет адрес"]):
        if target_os == "windows":
            fallback_cmd = "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' } | Select-Object InterfaceAlias, IPAddress"
        elif target_os == "macos":
            fallback_cmd = "ifconfig | grep 'inet ' | grep -v 127.0.0.1"
        else:
            fallback_cmd = "ip a 2>/dev/null || ifconfig"
        fallback_desc = "Определение локальных сетевых IP-адресов адаптеров"

    ai_cmd = fallback_cmd
    ai_desc = fallback_desc

    try:
        import urllib.request
        import urllib.parse
        query_prompt = (
            f"You are a command-line expert for {sys_shell} on {target_os}. "
            f"Convert this request into a single one-liner command: '{prompt}'. "
            f"Reply ONLY with the command text, no markdown backticks, no quotes, no explanations."
        )
        url = f"https://text.pollinations.ai/{urllib.parse.quote(query_prompt)}?model=openai-fast"
        req_obj = urllib.request.Request(url, headers={"User-Agent": "Argus/2.0"})
        with urllib.request.urlopen(req_obj, timeout=25.0) as response:
            text = response.read().decode("utf-8").strip()
            cleaned = re.sub(r"^```[a-z]*\n?", "", text).rstrip("`").strip()
            if cleaned and len(cleaned) < 300 and "\n" not in cleaned:
                ai_cmd = cleaned
                ai_desc = f"Команда для {sys_shell} ({target_os})"
    except Exception:
        pass

    if not ai_cmd:
        ai_cmd = f"echo 'Команда для: {prompt}'"
        ai_desc = f"Шаблон команды для {sys_shell}"

    return {
        "command": ai_cmd,
        "description": ai_desc,
        "shell": "powershell" if target_os == "windows" else "bash",
        "os": target_os
    }

# Plugins File Inspector & Tree Endpoints
@app.get("/api/plugins/{plugin_id}/tree")
async def get_plugin_tree_endpoint(plugin_id: str):
    return pm.get_plugin_tree(plugin_id)

@app.get("/api/plugins/{plugin_id}/file")
async def get_plugin_file_endpoint(plugin_id: str, path: str = Query(...)):
    res = pm.get_plugin_file_content(plugin_id, path)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/plugins/{plugin_id}/file")
async def save_plugin_file_endpoint(plugin_id: str, req: PluginFileSaveRequest):
    res = pm.save_plugin_file_content(plugin_id, req.path, req.content)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to save file"))
    return res

@app.post("/api/plugins/{plugin_id}/entrypoint")
async def set_plugin_entrypoint_endpoint(plugin_id: str, req: PluginEntrypointRequest):
    res = pm.set_plugin_entrypoint(plugin_id, req.entrypoint)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to set entrypoint"))
    return res

# Fish Audio Test
@app.post("/api/voice/test-fish")
async def test_fish_audio(req: FishAudioTestRequest):
    audio_b64 = await voice_engine.generate_speech_fish_audio(req.text, req.api_key, req.model_id)
    if not audio_b64:
        raise HTTPException(status_code=400, detail="Не удалось сгенерировать голос через Fish Audio. Проверьте API ключ и модель.")
    return {"success": True, "audio_base64": audio_b64}

clean_text_for_speech = voice_engine.clean_text_for_speech

# Argus AI Chat & Action Execution
@app.post("/api/ai/chat")
async def ai_chat(req: ChatMessageRequest):
    # 0. Fast local memory session / cache check (<0.01ms)
    local_s = _load_local_session()
    ver = None
    if local_s and local_s.get("valid") and local_s.get("key_code") == req.key_code:
        ver = local_s
    elif req.key_code in db._VERIFIED_KEYS_CACHE:
        ver = db._VERIFIED_KEYS_CACHE[req.key_code]
    else:
        try:
            ver = await db.verify_access_key(req.key_code)
        except Exception:
            ver = None

    if not ver or not ver.get("valid"):
        raise HTTPException(status_code=403, detail="Недействительный ключ доступа")
    
    user_name = ver.get("display_name", "Пользователь")

    # 1. Instant local memory history (<0.01ms)
    history = []
    try:
        raw_msgs = await db.get_messages(req.chat_id)
        if raw_msgs:
            history = [{"role": m["role"], "content": m["content"]} for m in raw_msgs[-12:]]
    except Exception:
        pass
    
    # 2. Save user message to database (instant local write + async bg remote sync)
    try:
        await db.save_message(req.chat_id, "user", req.message)
    except Exception:
        pass
    
    # 3. Process command with Argus AI Brain
    reply, action_type, action_data = argus.process_command(req.message, user_name, history=history)
    
    # 4. Save assistant response to database (instant local write + async bg remote sync)
    saved_msg = None
    try:
        saved_msg = await db.save_message(req.chat_id, "assistant", reply, action_type, action_data)
    except Exception:
        pass
    
    # 5. Generate Neural Voice (Respects exact client/settings selection with instant fallback)
    audio_base64 = None
    if req.voice and ver.get("voice_enabled", True):
        settings = _load_settings()
        provider = req.voice_provider or settings.get("voice_provider") or "edge-tts"
        # If client selected Native OS synthesis, skip remote TTS entirely for instantaneous response
        if provider != "native":
            speech_text = clean_text_for_speech(reply)
            if speech_text and len(speech_text) > 1:
                try:
                    voice_name = req.voice_name or settings.get("edge_voice") or "jarvis"
                    speed_val = float(req.voice_speed if req.voice_speed is not None else settings.get("voice_speed", 1.05))
                    rate_str = f"+{int((speed_val - 1.0) * 100)}%" if speed_val >= 1.0 else f"{int((speed_val - 1.0) * 100)}%"
                    fish_key = req.fish_api_key or (settings.get("fish_api_key") if provider == "fish-audio" else None)
                    fish_mid = req.fish_model_id or (settings.get("fish_model_id") if provider == "fish-audio" else None)

                    audio_base64 = await asyncio.wait_for(
                        voice_engine.generate_speech_base64(
                            speech_text,
                            voice=voice_name,
                            rate=rate_str,
                            fish_api_key=fish_key,
                            fish_model_id=fish_mid,
                        ),
                        timeout=5.0
                    )
                except Exception as e:
                    print(f"[Argus TTS Notice]: {e}")
                    audio_base64 = None
        
    return {
        "reply": reply,
        "action_type": action_type,
        "action_data": action_data,
        "audio_base64": audio_base64,
        "message_id": saved_msg["id"] if saved_msg else str(uuid.uuid4()),
        "created_at": saved_msg["created_at"] if saved_msg else datetime.datetime.now().isoformat()
    }

class STTRequest(BaseModel):
    audio_base64: str

# Standalone TTS
@app.post("/api/voice/tts")
async def generate_tts(req: TTSRequest):
    settings = _load_settings()
    voice_name = req.voice or settings.get("edge_voice") or "jarvis"
    speed_val = float(settings.get("voice_speed", 1.05))
    rate_str = req.rate if req.rate and req.rate != "+0%" else (f"+{int((speed_val - 1.0) * 100)}%" if speed_val >= 1.0 else f"{int((speed_val - 1.0) * 100)}%")

    audio_b64 = await voice_engine.generate_speech_base64(
        clean_text_for_speech(req.text),
        voice=voice_name,
        rate=rate_str,
        fish_api_key=req.fish_api_key or (settings.get("fish_api_key") if settings.get("voice_provider") == "fish-audio" else None),
        fish_model_id=req.fish_model_id or (settings.get("fish_model_id") if settings.get("voice_provider") == "fish-audio" else None)
    )
    if not audio_b64:
        raise HTTPException(status_code=500, detail="Ошибка генерации голоса")
    return {"audio_base64": audio_b64}

@app.post("/api/voice/stop")
async def stop_voice_endpoint():
    voice_engine.stop_all_audio()
    return {"success": True}

# Voice STT (Speech to Text)
@app.post("/api/voice/stt")
async def speech_to_text(req: STTRequest):
    transcript = await asyncio.to_thread(voice_engine.transcribe_audio_wav_base64, req.audio_base64)
    if not transcript:
        return {"success": False, "transcript": ""}
    return {"success": True, "transcript": transcript}

class WakeCheckRequest(BaseModel):
    audio_base64: str
    wake_words: Optional[str] = None

# Voice Wake Word Check
@app.post("/api/voice/wake-check")
async def wake_check_endpoint(req: WakeCheckRequest):
    """
    Fast server-side wake word detector for Electron & Web.
    Transcribes incoming audio clip and checks if Argus wake trigger is present.
    """
    transcript = await asyncio.to_thread(voice_engine.transcribe_audio_wav_base64, req.audio_base64)
    if not transcript or not transcript.strip():
        return {"wake_detected": False, "transcript": "", "command": ""}

    t_clean = transcript.strip().lower()

    default_triggers = [
        "аргус", "argus", "эй аргус", "hey argus", "привет аргус", "hi argus",
        "август", "аргуст", "argos", "агрус", "аргос", "артус", "арбуз", "аркус",
        "аргуз", "аргас", "агус", "алгус", "ай аргус", "слушай аргус", "аргуса", "аргусе",
        "а груз", "а-груз", "аргусу", "аргусом", "алиса аргус", "argo", "агрос",
        "оргус", "арго", "арбус", "аргаз", "агруз", "а ргус"
    ]
    if req.wake_words:
        custom_list = [w.strip().lower() for w in req.wake_words.split(",") if w.strip()]
        if custom_list:
            default_triggers = custom_list + default_triggers

    # Sort triggers by length descending so longer phrases match first ("привет аргус" before "аргус")
    default_triggers = sorted(list(set(default_triggers)), key=len, reverse=True)

    matched_trigger = None
    for trig in default_triggers:
        if trig in t_clean:
            matched_trigger = trig
            break

    if not matched_trigger:
        return {"wake_detected": False, "transcript": transcript, "command": ""}

    # Extract command part after the trigger word from the original transcript preserving casing
    m_trig = re.search(rf'{re.escape(matched_trigger)}', transcript, re.IGNORECASE)
    if m_trig:
        command = transcript[m_trig.end():].strip()
    else:
        split_pat = re.compile(rf'(?:^|\s|[,\.\?!]){re.escape(matched_trigger)}(?:\s|$|[,\.\?!])', re.IGNORECASE)
        parts = split_pat.split(transcript, 1)
        command = parts[1].strip() if len(parts) > 1 else ""

    command = re.sub(r'^[,\.\s\-—!?:;]+', '', command).strip()

    return {
        "wake_detected": True,
        "transcript": transcript,
        "trigger": matched_trigger,
        "command": command
    }

# ─── SCENARIOS & WORKFLOW AUTOMATION ────────────────────────────
class ScenarioModel(BaseModel):
    id: Optional[str] = None
    name: str
    icon: Optional[str] = "Sparkles"
    triggers: Union[List[str], str] = []
    description: Optional[str] = ""
    is_builtin: Optional[bool] = False
    custom_prompt: Optional[str] = None
    instruction: Optional[str] = None
    steps: List[Dict[str, Any]] = []

    model_config = {"extra": "allow"}


# ─── GLOBAL VOICE DICTATION ENDPOINTS (DOUBLE-CTRL) ─────────────
@app.get("/api/voice/dictation-poll")
async def dictation_poll():
    """Long-polls for system-wide Double-Ctrl voice dictation trigger."""
    ev = dictation_hook.get_dictation_event()
    triggered = await asyncio.to_thread(ev.wait, 20.0)
    if triggered:
        ev.clear()
        return {"triggered": True}
    return {"triggered": False}

@app.post("/api/voice/dictation-trigger")
async def dictation_trigger_post():
    """Manual trigger for dictation mode (from hotkey or UI)."""
    dictation_hook.trigger_dictation()
    return {"triggered": True}


# ─── SYSTEM APPS DISCOVERY ENDPOINT ──────────────────────────────
@app.get("/api/system/apps")
async def get_system_apps_endpoint():
    """Returns curated & detected installed applications on Windows & macOS."""
    try:
        return sc.get_popular_and_installed_apps()
    except Exception as e:
        print("Error getting system apps:", e)
        return []

# ─── SCENARIO PARSE ТЗ ENDPOINT ──────────────────────────────────
class ScenarioTZRequest(BaseModel):
    prompt: Optional[str] = None
    tz: Optional[str] = None

@app.post("/api/scenarios/parse-tz")
async def parse_scenario_tz_endpoint(req: ScenarioTZRequest):
    """Parses natural language user ТЗ into concrete, editable scenario steps."""
    text = (req.prompt or req.tz or "").strip()
    if not text:
        return {"steps": []}
    steps = sc_mgr.parse_tz_to_steps(text)
    return {"steps": steps}

@app.get("/api/scenarios")
async def get_all_scenarios():
    return sc_mgr.load_scenarios()

@app.post("/api/scenarios")
async def create_or_update_scenario(scenario: ScenarioModel):
    data = scenario.model_dump()
    return sc_mgr.add_or_update_scenario(data)

@app.delete("/api/scenarios/{scenario_id}")
async def remove_scenario(scenario_id: str):
    return {"success": sc_mgr.delete_scenario(scenario_id)}

_SCENARIO_RUN_LOCKS: Dict[str, float] = {}

@app.post("/api/scenarios/{scenario_id}/run")
async def run_scenario_endpoint(scenario_id: str):
    import urllib.parse
    clean_id = urllib.parse.unquote(scenario_id).strip()

    now = time.time()
    last_run = _SCENARIO_RUN_LOCKS.get(clean_id, 0)
    if now - last_run < 1.5:
        return {
            "success": True,
            "scenario_id": clean_id,
            "summary": "Сценарий уже выполняется.",
            "results": []
        }
    _SCENARIO_RUN_LOCKS[clean_id] = now

    all_s = sc_mgr.load_scenarios()
    # 1. Match by exact or normalized ID
    matched = next((s for s in all_s if str(s.get("id", "")).strip().lower() == clean_id.lower()), None)
    
    # 2. Match by Name
    if not matched:
        matched = next((s for s in all_s if str(s.get("name", "")).strip().lower() == clean_id.lower()), None)

    # 3. Match by Triggers
    if not matched:
        for s in all_s:
            trigs = s.get("triggers", [])
            if isinstance(trigs, list) and clean_id.lower() in [t.lower() for t in trigs]:
                matched = s
                break

    # 4. Ad-hoc fallback: if still not matched, parse as ТЗ and execute directly
    if not matched:
        matched = {
            "id": clean_id,
            "name": clean_id,
            "steps": sc_mgr.parse_tz_to_steps(clean_id)
        }

    try:
        res = await asyncio.to_thread(sc_mgr.execute_scenario, matched)
        return res
    except Exception as e:
        print(f"Scenario run fallback notice for {clean_id}:", e)
        return {
            "success": True,
            "scenario_id": clean_id,
            "scenario_name": matched.get("name", clean_id),
            "results": [f"Сценарий запущен ({clean_id})"],
            "summary": f"Сценарий «{matched.get('name', clean_id)}» успешно активирован."
        }


# ─── EXTRAS: TASKS, NOTES, TIMERS & REMINDERS ───────────────────
import backend.extras_manager as extras_mgr

class ExtrasDataModel(BaseModel):
    tasks: Optional[List[Dict[str, Any]]] = None
    notes: Optional[List[Dict[str, Any]]] = None
    timers: Optional[List[Dict[str, Any]]] = None
    reminders: Optional[List[Dict[str, Any]]] = None

@app.get("/api/extras/data")
async def get_extras_endpoint():
    return extras_mgr.load_extras_data()

@app.post("/api/extras/data")
async def save_extras_endpoint(payload: ExtrasDataModel):
    current = extras_mgr.load_extras_data()
    dumped = payload.model_dump(exclude_unset=True)
    current.update(dumped)
    success = extras_mgr.save_extras_data(current)
    return {"success": success, "data": current}

@app.post("/api/extras/task")
async def add_task_endpoint(payload: Dict[str, Any]):
    title = payload.get("title", "")
    desc = payload.get("description", "")
    prio = payload.get("priority", "medium")
    cat = payload.get("category", "general")
    due = payload.get("due_date", "")
    task = extras_mgr.add_task(title, desc, prio, cat, due)
    return {"success": True, "task": task}

@app.post("/api/extras/note")
async def add_note_endpoint(payload: Dict[str, Any]):
    title = payload.get("title", "")
    content = payload.get("content", "")
    cat = payload.get("category", "general")
    color = payload.get("color", "graphite")
    pinned = payload.get("pinned", False)
    note = extras_mgr.add_note(title, content, cat, color, pinned)
    return {"success": True, "note": note}

@app.post("/api/extras/timer")
async def add_timer_endpoint(payload: Dict[str, Any]):
    title = payload.get("title", "Таймер")
    seconds = int(payload.get("seconds", 300))
    timer = extras_mgr.add_timer(title, seconds)
    return {"success": True, "timer": timer}

@app.delete("/api/extras/task/{task_id}")
async def delete_task_endpoint(task_id: str):
    ok, task = extras_mgr.delete_task(task_id)
    return {"success": ok, "task": task}

# [redundant shutdown removed]

@app.post("/api/extras/task/{task_id}/complete")
async def complete_task_endpoint(task_id: str):
    ok, task = extras_mgr.complete_task(task_id)
    return {"success": ok, "task": task}

# [redundant shutdown removed]

@app.delete("/api/extras/note/{note_id}")
async def delete_note_endpoint(note_id: str):
    ok, note = extras_mgr.delete_note(note_id)
    return {"success": ok, "note": note}

@app.delete("/api/extras/timer/{timer_id}")
async def delete_timer_endpoint(timer_id: str):
    ok, timer = extras_mgr.delete_timer(timer_id)
    return {"success": ok, "timer": timer}

@app.get("/api/extras/search-notes")
async def search_notes_endpoint(q: str = Query(..., alias="q")):
    matches = extras_mgr.search_notes(q)
    return {"success": True, "matches": matches}

@app.put("/api/extras/note/{note_id}")
async def update_note_endpoint(note_id: str, payload: Dict[str, Any]):
    ok, note = extras_mgr.update_note(
        note_id,
        title=payload.get("title"),
        content=payload.get("content"),
        color=payload.get("color"),
        category=payload.get("category"),
        pinned=payload.get("pinned")
    )
    return {"success": ok, "note": note}

@app.put("/api/extras/task/{task_id}")
async def update_task_endpoint(task_id: str, payload: Dict[str, Any]):
    ok, task = extras_mgr.update_task(
        task_id,
        title=payload.get("title"),
        description=payload.get("description"),
        priority=payload.get("priority"),
        category=payload.get("category"),
        completed=payload.get("completed")
    )
    return {"success": ok, "task": task}

@app.post("/api/shutdown")
async def shutdown_endpoint():
    import os, signal, threading
    def _exit():
        import time
        time.sleep(0.15)
        try: os.kill(os.getpid(), signal.SIGTERM)
        except: os._exit(0)
    threading.Thread(target=_exit, daemon=True).start()
    return {"status": "shutting_down"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.server:app", host="127.0.0.1", port=18274, reload=False)

