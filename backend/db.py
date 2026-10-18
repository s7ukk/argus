import os
import time
import asyncio
import aiohttp
import json
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_file = os.path.join(_project_root, ".env")
if os.path.exists(_env_file):
    load_dotenv(_env_file)

CLOUD_URL = os.getenv("ARGUS_CLOUD_URL", "http://153.52.69.55:18274").rstrip('/')
ADMIN_KEY = os.getenv("ARGUS_ADMIN_KEY", "ARGUS-ADMIN-SUPER-KEY")
VIP_KEY = os.getenv("ARGUS_VIP_KEY", "ARGUS-ULTIMATE-2026-VIP")

import backend.app_paths as app_paths

LOCAL_STORAGE_FILE = app_paths.get_data_file_path("local_chats.json")

def is_valid_uuid(val: Any) -> bool:
    if not val:
        return False
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError, TypeError):
        return False

_VERIFIED_KEYS_CACHE: Dict[str, Dict[str, Any]] = {
    ADMIN_KEY: {
        "valid": True,
        "key_code": ADMIN_KEY,
        "tier": "ultimate",
        "assigned_to": "Повелитель",
        "display_name": "Повелитель",
        "voice_enabled": True,
        "voice_speed": 1.0,
        "theme": "black-purple",
        "expires_at": "2030-01-01T00:00:00+00:00",
        "days_left": 3650
    },
    VIP_KEY: {
        "valid": True,
        "key_code": VIP_KEY,
        "tier": "ultimate",
        "assigned_to": "VIP Пользователь",
        "display_name": "VIP Пользователь",
        "voice_enabled": True,
        "voice_speed": 1.0,
        "theme": "black-purple",
        "expires_at": "2027-01-01T00:00:00+00:00",
        "days_left": 365
    }
}

_LOCAL_CHATS: Dict[str, List[Dict[str, Any]]] = {}
_LOCAL_MESSAGES: Dict[str, List[Dict[str, Any]]] = {}

def _load_disk_storage():
    global _LOCAL_CHATS, _LOCAL_MESSAGES
    if os.path.exists(LOCAL_STORAGE_FILE):
        try:
            with open(LOCAL_STORAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _LOCAL_CHATS = data.get("chats", {})
                    _LOCAL_MESSAGES = data.get("messages", {})
        except Exception:
            pass

def _save_disk_storage():
    try:
        with open(LOCAL_STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump({"chats": _LOCAL_CHATS, "messages": _LOCAL_MESSAGES}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

_load_disk_storage()

async def verify_access_key(key_code: str) -> Dict[str, Any]:
    key_code = key_code.strip()
    if key_code in _VERIFIED_KEYS_CACHE:
        return _VERIFIED_KEYS_CACHE[key_code]
    
    if CLOUD_URL:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{CLOUD_URL}/api/auth/verify-key",
                    json={"key_code": key_code},
                    timeout=aiohttp.ClientTimeout(total=4)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        _VERIFIED_KEYS_CACHE[key_code] = data
                        return data
                    elif resp.status in (401, 403):
                        try:
                            err_data = await resp.json()
                            return {"valid": False, "error": err_data.get("detail", "Недействительный ключ доступа")}
                        except Exception:
                            return {"valid": False, "error": "Недействительный ключ доступа"}
        except Exception:
            pass

    return {"valid": False, "error": "Не удалось проверить ключ. Проверьте интернет-соединение."}

async def update_user_profile(key_code: str, display_name: str, voice_enabled: bool = True, voice_speed: float = 1.0) -> bool:
    key_code = key_code.strip()
    if key_code in _VERIFIED_KEYS_CACHE:
        _VERIFIED_KEYS_CACHE[key_code]["display_name"] = display_name.strip()
        _VERIFIED_KEYS_CACHE[key_code]["voice_enabled"] = voice_enabled
        _VERIFIED_KEYS_CACHE[key_code]["voice_speed"] = voice_speed

    if CLOUD_URL:
        async def _bg_sync():
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        f"{CLOUD_URL}/api/profile/update",
                        json={
                            "key_code": key_code,
                            "display_name": display_name,
                            "voice_enabled": voice_enabled,
                            "voice_speed": voice_speed
                        },
                        timeout=aiohttp.ClientTimeout(total=5)
                    )
            except Exception:
                pass
        asyncio.create_task(_bg_sync())
    return True

async def list_chats(key_code: str) -> List[Dict[str, Any]]:
    key_code = key_code.strip()
    if key_code in _LOCAL_CHATS and _LOCAL_CHATS[key_code]:
        return _LOCAL_CHATS[key_code]

    if CLOUD_URL:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{CLOUD_URL}/api/chats",
                    headers={"X-Argus-Key": key_code},
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as resp:
                    if resp.status == 200:
                        chats = await resp.json()
                        _LOCAL_CHATS[key_code] = chats
                        _save_disk_storage()
                        return chats
        except Exception:
            pass
    return _LOCAL_CHATS.get(key_code, [])

async def create_chat(key_code: str, title: str = "Новый диалог") -> Dict[str, Any]:
    key_code = key_code.strip()
    chat_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    new_chat = {
        "id": chat_id,
        "title": title,
        "created_at": now_iso,
        "updated_at": now_iso
    }
    if key_code not in _LOCAL_CHATS:
        _LOCAL_CHATS[key_code] = []
    _LOCAL_CHATS[key_code].insert(0, new_chat)
    _save_disk_storage()

    if CLOUD_URL:
        async def _bg_create():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{CLOUD_URL}/api/chats/create",
                        json={"key_code": key_code, "title": title},
                        timeout=aiohttp.ClientTimeout(total=4)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if key_code in _LOCAL_CHATS and _LOCAL_CHATS[key_code]:
                                _LOCAL_CHATS[key_code][0] = data
                                _save_disk_storage()
            except Exception:
                pass
        asyncio.create_task(_bg_create())
    return new_chat

async def update_chat_title(chat_id: str, key_code: str, new_title: str) -> bool:
    key_code = key_code.strip()
    new_title = new_title.strip()
    if key_code in _LOCAL_CHATS:
        for c in _LOCAL_CHATS[key_code]:
            if c["id"] == chat_id:
                c["title"] = new_title
                c["updated_at"] = datetime.now(timezone.utc).isoformat()
                break
        _save_disk_storage()

    if CLOUD_URL:
        async def _bg_rename():
            try:
                async with aiohttp.ClientSession() as session:
                    await session.patch(
                        f"{CLOUD_URL}/api/chats/{chat_id}",
                        json={"key_code": key_code, "title": new_title},
                        timeout=aiohttp.ClientTimeout(total=4)
                    )
            except Exception:
                pass
        asyncio.create_task(_bg_rename())
    return True

async def delete_chat(chat_id: str, key_code: str) -> bool:
    key_code = key_code.strip()
    if key_code in _LOCAL_CHATS:
        _LOCAL_CHATS[key_code] = [c for c in _LOCAL_CHATS[key_code] if c["id"] != chat_id]
        _LOCAL_MESSAGES.pop(chat_id, None)
        _save_disk_storage()

    if CLOUD_URL:
        async def _bg_delete():
            try:
                async with aiohttp.ClientSession() as session:
                    await session.delete(
                        f"{CLOUD_URL}/api/chats/{chat_id}",
                        headers={"X-Argus-Key": key_code},
                        timeout=aiohttp.ClientTimeout(total=4)
                    )
            except Exception:
                pass
        asyncio.create_task(_bg_delete())
    return True

async def get_messages(chat_id: str) -> List[Dict[str, Any]]:
    if chat_id in _LOCAL_MESSAGES and _LOCAL_MESSAGES[chat_id]:
        return _LOCAL_MESSAGES[chat_id]

    if CLOUD_URL:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{CLOUD_URL}/api/chats/{chat_id}/messages",
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as resp:
                    if resp.status == 200:
                        msgs = await resp.json()
                        _LOCAL_MESSAGES[chat_id] = msgs
                        _save_disk_storage()
                        return msgs
        except Exception:
            pass
    return _LOCAL_MESSAGES.get(chat_id, [])

async def save_message(chat_id: str, role: str, content: str, action_type: Optional[str] = None, action_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    msg_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    msg = {
        "id": msg_id,
        "chat_id": chat_id,
        "role": role,
        "content": content,
        "action_type": action_type,
        "action_data": action_data,
        "created_at": now_iso
    }
    if chat_id not in _LOCAL_MESSAGES:
        _LOCAL_MESSAGES[chat_id] = []
    _LOCAL_MESSAGES[chat_id].append(msg)
    _save_disk_storage()

    if CLOUD_URL:
        async def _bg_save():
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        f"{CLOUD_URL}/api/chats/{chat_id}/messages",
                        json={
                            "role": role,
                            "content": content,
                            "action_type": action_type,
                            "action_data": action_data
                        },
                        timeout=aiohttp.ClientTimeout(total=5)
                    )
            except Exception:
                pass
        asyncio.create_task(_bg_save())

    return msg
