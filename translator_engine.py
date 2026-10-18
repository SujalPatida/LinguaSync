"""
LinguaSync Translator Engine
----------------------------
Handles microphone audio capture, speech-to-text recognition,
language translation with automatic source detection, and
text-to-speech generation with native macOS audio playback.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from typing import Callable, Optional, Tuple

import requests
import speech_recognition as sr
from gtts import gTTS

# Comprehensive language dictionary mapping user-friendly names to language codes
# Includes all requested languages: English, Hindi, Tamil, Telugu, Bengali,
# Spanish, French, German, Japanese, Korean, plus other popular languages.
SUPPORTED_LANGUAGES: dict[str, str] = {
    "Auto Detect": "auto",
    "English": "en",
    "Hindi (हिन्दी)": "hi",
    "Tamil (தமிழ்)": "ta",
    "Telugu (తెలుగు)": "te",
    "Bengali (বাংলা)": "bn",
    "Spanish (Español)": "es",
    "French (Français)": "fr",
    "German (Deutsch)": "de",
    "Japanese (日本語)": "ja",
    "Korean (한국어)": "ko",
    "Arabic (العربية)": "ar",
    "Chinese Simplified (简体中文)": "zh-CN",
    "Chinese Traditional (繁體中文)": "zh-TW",
    "Gujarati (ગુજરાતી)": "gu",
    "Italian (Italiano)": "it",
    "Kannada (ಕನ್ನಡ)": "kn",
    "Malayalam (മലയാളം)": "ml",
    "Marathi (मराठी)": "mr",
    "Portuguese (Português)": "pt",
    "Punjabi (ਪੰਜਾਬੀ)": "pa",
    "Russian (Русский)": "ru",
    "Turkish (Türkçe)": "tr",
    "Urdu (اردو)": "ur",
    "Vietnamese (Tiếng Việt)": "vi",
}

# Target languages do not include 'auto'
TARGET_LANGUAGES: dict[str, str] = {
    name: code for name, code in SUPPORTED_LANGUAGES.items() if code != "auto"
}

# Reverse lookup: code -> display name
CODE_TO_NAME: dict[str, str] = {
    code: name for name, code in SUPPORTED_LANGUAGES.items()
}


def get_language_display_name(code: str) -> str:
    """Returns a readable name for a language code (e.g. 'hi' -> 'Hindi (हिन्दी)')."""
    if code in CODE_TO_NAME:
        return CODE_TO_NAME[code]
    # Check 2-letter prefix match (e.g. 'en-US' -> 'en')
    short_code = code.split("-")[0].lower()
    for c, name in CODE_TO_NAME.items():
        if c.lower() == short_code:
            return name
    return code.upper()


class AudioPlayer:
    """Plays audio files cleanly on macOS using the native /usr/bin/afplay tool."""

    def __init__(self) -> None:
        self._current_process: Optional[subprocess.Popen] = None

    def play(self, audio_file_path: str, block: bool = True) -> bool:
        """Plays an audio file. If afplay is available, uses it natively."""
        self.stop()
        if not os.path.exists(audio_file_path):
            return False

        afplay_path = shutil.which("afplay")
        if afplay_path:
            try:
                proc = subprocess.Popen([afplay_path, audio_file_path])
                self._current_process = proc
                if block:
                    proc.wait()
                return True
            except Exception as e:
                print(f"[AudioPlayer] afplay error: {e}")
                return False
        else:
            # Fallback for non-macOS systems if needed
            try:
                from playsound import playsound
                playsound(audio_file_path)
                return True
            except Exception as e:
                print(f"[AudioPlayer] Fallback player error: {e}")
                return False

    def stop(self) -> None:
        """Stops any currently playing audio."""
        if self._current_process and self._current_process.poll() is None:
            try:
                self._current_process.terminate()
                self._current_process.wait(timeout=1)
            except Exception:
                try:
                    self._current_process.kill()
                except Exception:
                    pass
            self._current_process = None


class TranslatorEngine:
    """
    Core speech recognition, translation, and TTS engine.
    """

    def __init__(self) -> None:
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.player = AudioPlayer()

    @staticmethod
    def check_microphone_available() -> Tuple[bool, str]:
        """
        Verifies if PyAudio is working and at least one microphone is detected.
        Returns (is_available, status_message).
        """
        try:
            mic_names = sr.Microphone.list_microphone_names()
            if not mic_names:
                return (
                    False,
                    "No microphone devices found on this system. Please connect a microphone.",
                )
            return True, f"Found {len(mic_names)} audio device(s)."
        except Exception as e:
            err = str(e)
            if "portaudio" in err.lower() or "pyaudio" in err.lower():
                return (
                    False,
                    "PyAudio / PortAudio is not properly configured. On macOS, run 'brew install portaudio'.",
                )
            return False, f"Microphone access error: {err}"

    def listen_and_transcribe(
        self,
        source_language_code: str = "auto",
        timeout: float = 6.0,
        phrase_time_limit: float = 15.0,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Listens to the microphone and transcribes speech to text.
        Returns (transcribed_text, error_message).
        If successful, error_message is None.
        """
        try:
            with sr.Microphone() as source:
                # Adjust for ambient noise briefly
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                # Listen for speech
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )

            # Determine speech recognition language parameter
            # If auto, Google default is US English or system locale
            recog_lang = (
                None if source_language_code == "auto" else source_language_code
            )

            text = self.recognizer.recognize_google(audio, language=recog_lang)
            return text.strip(), None

        except sr.WaitTimeoutError:
            return None, "TIMEOUT"  # Normal silence timeout, can retry
        except sr.UnknownValueError:
            return None, "Could not understand audio. Please speak clearly."
        except sr.RequestError as e:
            return None, f"Speech recognition network error: {e}"
        except OSError as e:
            # Common macOS microphone permission denial error
            return (
                None,
                "Microphone access denied or audio hardware busy. Check macOS System Settings > Privacy & Security > Microphone.",
            )
        except Exception as e:
            return None, f"Audio error: {e}"

    @staticmethod
    def translate_text(
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en",
    ) -> Tuple[str, str]:
        """
        Translates text from source_lang to target_lang.
        Returns (translated_text, detected_source_lang_code).
        
        Uses a resilient dual-strategy:
        1. Google Translate API client endpoint (reliable, fast, no web-scraping rate limits).
        2. deep_translator.GoogleTranslator as automatic fallback.
        """
        if not text or not text.strip():
            return "", source_lang

        clean_text = text.strip()

        # If source and target are identical and not auto, return as-is
        if source_lang != "auto" and source_lang.lower() == target_lang.lower():
            return clean_text, source_lang

        # Strategy 1: Google Translate API endpoint (gtx)
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": source_lang,
                "tl": target_lang,
                "dt": "t",
                "q": clean_text,
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
            }
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Extract translated parts
            translated_chunks = []
            if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                for part in data[0]:
                    if part and len(part) > 0 and part[0]:
                        translated_chunks.append(part[0])
            translated_text = "".join(translated_chunks).strip()

            # Extract detected source language
            detected_lang = source_lang
            if len(data) > 2 and isinstance(data[2], str):
                detected_lang = data[2]

            if translated_text:
                return translated_text, detected_lang

        except Exception as api_err:
            print(f"[TranslatorEngine] Primary API attempt note: {api_err}. Trying fallback...")

        # Strategy 2: deep-translator fallback
        try:
            from deep_translator import GoogleTranslator

            src = "auto" if source_lang == "auto" else source_lang
            translator = GoogleTranslator(source=src, target=target_lang)
            translated = translator.translate(clean_text)
            return translated, source_lang
        except Exception as dt_err:
            raise RuntimeError(f"Translation failed: {dt_err}")

    def text_to_speech(
        self,
        text: str,
        lang_code: str = "en",
        play_audio: bool = True,
    ) -> Optional[str]:
        """
        Generates TTS audio file and optionally plays it via native player.
        Returns the path to the generated temporary audio file.
        """
        if not text or not text.strip():
            return None

        # Clean lang code (e.g. 'zh-CN' -> 'zh-CN', 'en-US' -> 'en')
        tts_lang = lang_code.split("-")[0].lower() if "-" in lang_code and lang_code not in ("zh-CN", "zh-TW") else lang_code

        temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        try:
            tts = gTTS(text=text, lang=tts_lang, slow=False)
            tts.save(temp_path)

            if play_audio:
                self.player.play(temp_path, block=True)

            return temp_path
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            print(f"[TranslatorEngine] TTS error for lang '{lang_code}': {e}")
            return None

    def stop_playback(self) -> None:
        """Immediately stops any ongoing TTS audio playback."""
        self.player.stop()
