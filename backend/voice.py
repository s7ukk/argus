import asyncio
import base64
import io
import os
import re
import tempfile
import edge_tts
import speech_recognition as sr
from typing import Optional

import aiohttp
import ctypes

import threading
import time
import subprocess

def play_audio_file_system(file_path: str):
    """Directly plays an MP3 audio file through Windows native audio subsystem in background thread."""
    if os.name != "nt":
        return
    def _worker():
        try:
            norm_path = os.path.abspath(file_path).replace('/', '\\')
            alias = f"argus_sp_{int(time.time() * 1000) % 100000}"
            ctypes.windll.winmm.mciSendStringW(f'open "{norm_path}" type mpegvideo alias {alias}', None, 0, None)
            ctypes.windll.winmm.mciSendStringW(f'play {alias} wait', None, 0, None)
            ctypes.windll.winmm.mciSendStringW(f'close {alias}', None, 0, None)
            # Remove temp file after playing
            try:
                if os.path.exists(norm_path):
                    os.remove(norm_path)
            except Exception:
                pass
        except Exception as e:
            print(f"[Argus Direct Audio]: {e}")
    threading.Thread(target=_worker, daemon=True).start()

def speak_windows_sapi(text: str):
    """Speaks text using built-in Windows native SAPI speech synthesis (100% offline guarantee)."""
    if os.name != "nt" or not text.strip():
        return
    def _worker():
        try:
            clean = text.replace('"', ' ').replace("'", " ").replace('`', ' ')
            clean = re.sub(r'\s+', ' ', clean).strip()
            ps_code = f"""
            Add-Type -AssemblyName System.Speech
            $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
            try {{ $s.SelectVoice('Microsoft Irina Desktop') }} catch {{}}
            $s.Speak('{clean}')
            """
            subprocess.run(['powershell', '-NoProfile', '-Command', ps_code], timeout=15)
        except Exception as e:
            print(f"[Argus SAPI Speech]: {e}")
    threading.Thread(target=_worker, daemon=True).start()

async def generate_speech_fish_audio(text: str, api_key: str, model_id: Optional[str] = None) -> Optional[str]:
    """Generates speech via Fish Audio REST API and returns Base64 MP3."""
    if not text or not api_key:
        return None
    url = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }
    payload = {
        "text": text[:500],
        "reference_id": model_id.strip() if model_id else "e58b9062b01d4a138c202026778f67e5",
        "format": "mp3",
        "latency": "normal"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                if resp.status == 200:
                    audio_bytes = await resp.read()
                    if audio_bytes and len(audio_bytes) > 200:
                        return base64.b64encode(audio_bytes).decode("utf-8")
                else:
                    err_txt = await resp.text()
                    print(f"Fish Audio API error [{resp.status}]: {err_txt}")
    except Exception as e:
        print("Fish Audio request failed:", e)
    return None

def stop_all_audio():
    """Immediately stops all Windows native audio devices and MCI tracks."""
    if os.name == "nt":
        try:
            ctypes.windll.winmm.mciSendStringW('close all', None, 0, None)
        except Exception:
            pass

async def generate_speech_base64(
    text: str,
    voice: Optional[str] = None,
    rate: str = "+0%",
    fish_api_key: Optional[str] = None,
    fish_model_id: Optional[str] = None
) -> Optional[str]:
    """
    Generate speech audio and return as Base64 MP3 for clean single-source playback in frontend.
    """
    if not text or not text.strip():
        return None
        
    clean_text = text.replace("**", "").replace("*", "").replace("`", "").replace("#", "")
    if len(clean_text) > 400:
        clean_text = clean_text[:400] + "..."

    # 1. Try Fish Audio if key is provided
    if fish_api_key and fish_api_key.strip():
        fish_b64 = await generate_speech_fish_audio(clean_text, fish_api_key, fish_model_id)
        if fish_b64:
            return fish_b64

    # 2. High-quality Edge-TTS Neural Voices (Default: ru-RU-DmitryNeural male)
    target_voice = voice if (voice and "Svetlana" not in voice) else "ru-RU-DmitryNeural"
    voices_to_try = [target_voice, "ru-RU-DmitryNeural", "en-US-ChristopherNeural"]
    
    seen = set()
    deduped = []
    for v in voices_to_try:
        if v not in seen:
            seen.add(v)
            deduped.append(v)

    for v in deduped:
        try:
            communicate = edge_tts.Communicate(clean_text, v, rate=rate)
            audio_data = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])
                    
            if audio_data and len(audio_data) > 100:
                return base64.b64encode(audio_data).decode("utf-8")
        except Exception as e:
            print(f"[Edge-TTS Voice Notice]: Voice {v} attempt: {e}")
            continue

    return None

def transcribe_audio_wav_base64(wav_b64: str) -> Optional[str]:
    """Transcribe base64 encoded 16kHz WAV audio using Google Speech API."""
    try:
        audio_bytes = base64.b64decode(wav_b64)
        wav_io = io.BytesIO(audio_bytes)
        
        r = sr.Recognizer()
        r.energy_threshold = 100
        r.dynamic_energy_threshold = False
        
        with sr.AudioFile(wav_io) as source:
            audio = r.record(source)
            
        # Try Russian first
        try:
            return r.recognize_google(audio, language="ru-RU")
        except sr.UnknownValueError:
            # Fallback to English
            try:
                return r.recognize_google(audio, language="en-US")
            except Exception:
                return None
    except Exception as e:
        print("STT transcription error:", e)
        return None
