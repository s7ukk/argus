import asyncio
import base64
from typing import Dict, Any
# In-memory LRU audio cache for instantaneous voice playback (<0.01ms)
_VOICE_AUDIO_CACHE: Dict[str, str] = {}

import io
import os
import sys
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
    """Directly plays an MP3 audio file through system native audio subsystem in background thread."""
    if sys.platform == "darwin":
        def _mac_worker():
            try:
                subprocess.run(["afplay", file_path], check=False)
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
            except Exception as e:
                print(f"[Argus Mac Direct Audio]: {e}")
        threading.Thread(target=_mac_worker, daemon=True).start()
        return

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
    """Speaks text using built-in native speech synthesis (100% offline guarantee)."""
    if sys.platform == "darwin":
        def _mac_worker():
            try:
                subprocess.run(["say", text], timeout=15)
            except Exception as e:
                print(f"[Argus Mac Say]: {e}")
        threading.Thread(target=_mac_worker, daemon=True).start()
        return

    if os.name != "nt" or not text.strip():
        return
    def _worker():
        try:
            clean = text.replace('"', ' ').replace("'", " ").replace('`', ' ')
            clean = re.sub(r'\s+', ' ', clean).strip()
            ps_code = f"""
            Add-Type -AssemblyName System.Speech
            $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
            $male = $s.GetInstalledVoices() | Where-Object {{ $_.VoiceInfo.Gender -eq 'Male' -or $_.VoiceInfo.Name -match 'Dmitry|Pavel|Stefan|David|Male' }} | Select-Object -First 1
            if ($male) {{ try {{ $s.SelectVoice($male.VoiceInfo.Name) }} catch {{}} }}
            $s.Rate = -1
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
    """Immediately stops all system native audio devices and player tracks."""
    if sys.platform == "darwin":
        try:
            subprocess.run(["killall", "afplay"], capture_output=True)
        except Exception:
            pass
    elif os.name == "nt":
        try:
            ctypes.windll.winmm.mciSendStringW('close all', None, 0, None)
        except Exception:
            pass

def is_code_content(text: str) -> bool:
    """Detects if text contains programming code or script blocks."""
    if "```" in text:
        return True
    code_signatures = [
        "package main", "func main", "import (", "#include <", "int main(",
        "def main(", "class ", "import os", "import sys", "import asyncio",
        "const express", "require('", "from bs4", "console.log(", "public static void main"
    ]
    low = text.lower()
    return any(sig.lower() in low for sig in code_signatures)

def clean_text_for_speech(text: str) -> str:
    """Converts text into clean, natural spoken Russian. NEVER reads code scripts out loud."""
    if not text or not text.strip():
        return ""

    if "Автономный AI Агент" in text or "Автономный GUI Агент" in text:
        m_msg = re.search(r'Отправлено сообщение в ([^:\n]+): «([^»]+)»', text)
        if m_msg:
            return f"Сообщение в {m_msg.group(1)} успешно отправлено."
        m_act = re.search(r'выполнил (?:действие|задачу) в ([^:\n]+)', text)
        if m_act:
            return f"Действие в {m_act.group(1)} успешно выполнено."
        return "Действие успешно выполнено."

    # 1. SPECIAL CASE: Code blocks (```...```) - NEVER read code aloud!
    if "```" in text:
        parts = text.split("```")
        before_code = parts[0].strip()
        clean_intro = re.sub(r'[#*`_~]', '', before_code).strip()
        clean_intro = re.sub(r'[:—\-]+$', '', clean_intro).strip()
        if len(clean_intro) >= 8:
            first_sent = re.split(r'[.!?\n]', clean_intro)[0].strip()
            if len(first_sent) >= 8:
                return first_sent + ". Код выведен на экран."
        return "Код подготовлен и выведен на экран."

    # 2. Raw code without backticks
    if is_code_content(text):
        return "Код программы выведен на экран."

    t = text
    t = re.sub(r'`[^`]+`', ' код ', t)

    # 2. LaTeX math delimiters and environments
    t = re.sub(r'\\\[|\\\]|\\\(|\\\)', ' ', t)
    t = re.sub(r'\$\$|\$', ' ', t)

    # 3. LaTeX commands to natural spoken Russian words
    t = re.sub(r'\\Delta\b', 'Дискриминант ', t)
    t = re.sub(r'\\cdot\b|\\times\b', ' умножить на ', t)
    t = re.sub(r'\\pm\b', ' плюс-минус ', t)
    t = re.sub(r'\\sqrt\{([^}]+)\}', r' корень из \1 ', t)
    t = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r' \1 разделить на \2 ', t)
    t = re.sub(r'\\geq\b', ' больше либо равно ', t)
    t = re.sub(r'\\leq\b', ' меньше либо равно ', t)
    t = re.sub(r'\\neq\b', ' не равно ', t)
    t = re.sub(r'\^\{?2\}?', ' в квадрате ', t)
    t = re.sub(r'\^\{?3\}?', ' в кубе ', t)
    t = re.sub(r'\^\{?(\d+)\}?', r' в степени \1 ', t)
    t = re.sub(r'\\[a-zA-Z]+(?:\{([^}]*)\})?', r' \1 ', t)

    # 4. Remove comments like // ... and slashes
    t = re.sub(r'//[^\n]*', ' ', t)
    t = re.sub(r'/+', ' ', t)
    t = re.sub(r'\\+', ' ', t)

    # 5. Remove HTML tags
    t = re.sub(r'<[^>]+>', ' ', t)

    # 6. Strip phrases like "сохранено по пути: ...", "путь к файлу: ..."
    t = re.sub(r'(?:файл\s+)?(?:сохранен|сохранено|записан|записано|расположен|находится)\s+(?:по пути|по адресу|в директорию|в каталог|в папку|в)[\s:]+[^\n\.\,]+', 'файл успешно сохранен.', t, flags=re.IGNORECASE)
    t = re.sub(r'(?:путь|расположение|директория|папка)\s*(?:к файлу|сохранения)?[\s:]+[^\n\.\,]+', '', t, flags=re.IGNORECASE)

    # 7. Remove Windows absolute paths and URLs
    t = re.sub(r':\s*[a-zA-Z]:[\\/][^\s\)\"]+', '.', t)
    t = re.sub(r'[a-zA-Z]:[\\/][^\s\)\"]+', '', t)
    t = re.sub(r'https?://[^\s\)\"]+', '', t)
    t = re.sub(r'\b[\w\-_]+\.(?:png|jpg|jpeg|lnk|exe|py|json|txt|log|docx?|xlsx?)\b', '', t, flags=re.IGNORECASE)

    # 8. Clean markdown symbols & brackets
    t = t.replace('**', '').replace('*', '').replace('#', '').replace('•', '').replace('—', ' - ').replace('~', '')
    t = re.sub(r'[\[\]{}]', ' ', t)

    # 9. Trailing punctuation and duplicate spaces
    t = re.sub(r':\s*\.', '.', t)
    t = re.sub(r':\s*$', '.', t)
    t = re.sub(r'\s*([.,!?])\s*', r'\1 ', t)
    t = re.sub(r'\s+', ' ', t).strip()

    # Fast Wizard & List speech optimization
    if "выберите мессенджер" in t.lower():
        return "Выберите мессенджер для отправки сообщения."
    if "введите имя контакта" in t.lower() or "введите ник" in t.lower():
        return "Мессенджер выбран. Введите имя контакта или ник."
    if "введите текст сообщения" in t.lower():
        return "Контакт принят. Введите текст сообщения."
    if "успешно отправлено" in t.lower():
        return "Сообщение успешно отправлено."

    # Strip bullet points, numbered lists and examples from speech
    t = re.sub(r'(?m)^\s*\d+[\.\)]\s+.*$', '', t)
    t = re.sub(r'Например:.*', '', t, flags=re.DOTALL)
    t = re.sub(r'Нажмите кнопку ниже.*', '', t)
    t = re.sub(r'\s+', ' ', t).strip()

    # Filter out repetitive "сэр" to sound natural and modern
    t = re.sub(r'[,]\s*сэр\b', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\bсэр\b[,.!?]?', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*([.,!?])\s*', r'\1 ', t)
    t = re.sub(r'\s+', ' ', t).strip()

    # Natural intonation sentence selection: preserve full, complete sentences with expressive punctuation
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|[\r\n]+', t) if s.strip()]
    if sentences:
        chosen = []
        cur_len = 0
        for s in sentences:
            if cur_len + len(s) <= 240:
                chosen.append(s)
                cur_len += len(s)
            else:
                if not chosen:
                    m = re.match(r'^(.{40,200}?)[,;:\s]', s)
                    chosen.append((m.group(1).strip() + '.') if m else s[:180].strip())
                break
        t = ' '.join(chosen)
    elif len(t) > 240:
        m = re.match(r'^(.{40,200}?)[,;:\s]', t)
        t = (m.group(1).strip() + '.') if m else t[:180].strip()
    return t.strip()

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

    clean_text = clean_text_for_speech(text)
    if not clean_text or not clean_text.strip():
        return None

    target_voice = "ru-RU-DmitryNeural"
    if voice and "dmitry" in voice.lower():
        target_voice = "ru-RU-DmitryNeural"
    elif voice and "svetlana" not in voice.lower() and "christopher" not in voice.lower() and "jenny" not in voice.lower():
        target_voice = voice.strip()

    cache_key = f"{clean_text}_{target_voice}_{rate}"
    if cache_key in _VOICE_AUDIO_CACHE:
        return _VOICE_AUDIO_CACHE[cache_key]

    # 1. Try Fish Audio if key is provided
    if fish_api_key and fish_api_key.strip():
        fish_b64 = await generate_speech_fish_audio(clean_text, fish_api_key, fish_model_id)
        if fish_b64:
            return fish_b64

    # 2. High-quality Edge-TTS Neural Voices (Strictly Dmitry male voice: ru-RU-DmitryNeural)
    # Never fallback to Svetlana or English voices - Dmitry ONLY!
    target_voice = "ru-RU-DmitryNeural"
    if voice and "dmitry" in voice.lower():
        target_voice = "ru-RU-DmitryNeural"
    elif voice and "svetlana" not in voice.lower() and "christopher" not in voice.lower() and "jenny" not in voice.lower():
        target_voice = voice.strip()

    for attempt in range(2):
        try:
            async def _stream_voice(v_name: str):
                communicate = edge_tts.Communicate(clean_text, v_name, rate=rate)
                buf = bytearray()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        buf.extend(chunk["data"])
                return buf

            audio_data = await asyncio.wait_for(_stream_voice(target_voice), timeout=15.0)
            if audio_data and len(audio_data) > 100:
                b64_res = base64.b64encode(audio_data).decode("utf-8")
                if len(_VOICE_AUDIO_CACHE) > 500:
                    _VOICE_AUDIO_CACHE.clear()
                _VOICE_AUDIO_CACHE[cache_key] = b64_res
                return b64_res
        except Exception as e:
            print(f"[Edge-TTS Voice Notice]: Attempt {attempt + 1} Dmitry error: {e}")
            await asyncio.sleep(0.2)
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
            
        try:
            return r.recognize_google(audio, language="ru-RU")
        except sr.UnknownValueError:
            try:
                return r.recognize_google(audio, language="en-US")
            except Exception:
                return None
        except Exception as ge:
            print("Google STT error:", ge)
            return None
    except Exception as e:
        print("STT transcription error:", e)
        return None


def warmup_voice_cache():
    """Pre-generates in-memory audio for the most common responses in background thread for 0ms voice latency."""
    def _worker():
        common_phrases = [
            "Здравствуйте!",
            "Слушаю Вас.",
            "Готово.",
            "Все задачи успешно выполнены.",
            "Действие отменено.",
            "Остановил выполнение.",
            "Все системы работают в штатном режиме.",
            "Открываю.",
            "Вкладка закрыта.",
            "Скриншот сделан."
        ]
        target_voice = "ru-RU-DmitryNeural"
        for phrase in common_phrases:
            cache_key = f"{phrase}_{target_voice}_+0%"
            if cache_key in _VOICE_AUDIO_CACHE:
                continue
            try:
                communicate = edge_tts.Communicate(phrase, target_voice, rate="+0%")
                loop = asyncio.new_event_loop()
                async def _fetch():
                    b = bytearray()
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            b.extend(chunk["data"])
                    return b
                audio_data = loop.run_until_complete(_fetch())
                loop.close()
                if audio_data and len(audio_data) > 100:
                    b64_res = base64.b64encode(audio_data).decode("utf-8")
                    _VOICE_AUDIO_CACHE[cache_key] = b64_res
            except Exception:
                pass
            time.sleep(0.1)

    threading.Thread(target=_worker, daemon=True).start()

# Launch audio pre-warming upon module load
warmup_voice_cache()
