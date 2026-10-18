"""
LinguaSync Automated Verification Test Suite
============================================
Runs comprehensive checks across all core features:
- Dependency imports
- Microphone hardware detection & permissions check
- Translation across all required languages:
  English, Hindi, Tamil, Telugu, Bengali, Spanish, French, German, Japanese, Korean
- Automatic language detection
- Speech recognition via AudioFile
- Text-to-speech generation
- Native audio player (afplay) availability
- GUI widget initialization & queue-based non-blocking updates
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from gtts import gTTS
import speech_recognition as sr

from translator_engine import (
    SUPPORTED_LANGUAGES,
    TARGET_LANGUAGES,
    TranslatorEngine,
    get_language_display_name,
)
from gui import LinguaSyncApp


class TestLinguaSync(unittest.TestCase):

    def setUp(self):
        self.engine = TranslatorEngine()

    def test_01_language_dictionary(self):
        """Verifies that all user-requested target languages exist in TARGET_LANGUAGES."""
        required_targets = [
            "English", "Hindi (हिन्दी)", "Tamil (தமிழ்)", "Telugu (తెలుగు)",
            "Bengali (বাংলা)", "Spanish (Español)", "French (Français)",
            "German (Deutsch)", "Japanese (日本語)", "Korean (한국어)"
        ]
        for lang in required_targets:
            self.assertIn(lang, TARGET_LANGUAGES, f"Missing target language: {lang}")
        self.assertIn("Auto Detect", SUPPORTED_LANGUAGES)

    def test_02_microphone_detection(self):
        """Verifies microphone enumeration and PyAudio integration."""
        is_avail, msg = self.engine.check_microphone_available()
        print(f"\n[Test] Microphone status: {is_avail} | {msg}")
        self.assertTrue(is_avail, f"Microphone check failed: {msg}")

    def test_03_multilingual_translations(self):
        """Tests translation across English, Hindi, Tamil, Telugu, Bengali, Spanish, French, German, Japanese, Korean."""
        test_phrase = "Hello, welcome to LinguaSync!"
        targets = {
            "hi": "Hindi",
            "ta": "Tamil",
            "te": "Telugu",
            "bn": "Bengali",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "ja": "Japanese",
            "ko": "Korean",
            "en": "English",
        }
        print("\n[Test] Testing translations:")
        for code, name in targets.items():
            translated, detected = self.engine.translate_text(test_phrase, source_lang="auto", target_lang=code)
            self.assertTrue(len(translated) > 0, f"Empty translation for {name}")
            print(f"  ✓ {name} ({code}): {translated} (detected: {detected})")

    def test_04_speech_recognition_pipeline(self):
        """Tests speech recognition using a dynamically synthesized audio file."""
        sample_text = "speech recognition test"
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            mp3_path = f.name
        wav_path = mp3_path.replace(".mp3", ".wav")

        try:
            # Generate speech
            tts = gTTS(sample_text, lang="en")
            tts.save(mp3_path)

            # Convert to standard 16kHz WAV using macOS afconvert
            subprocess.run(
                ["afconvert", "-f", "WAVE", "-d", "LEI16@16000", mp3_path, wav_path],
                check=True,
                capture_output=True,
            )

            # Transcribe
            r = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio = r.record(source)
                recognized = r.recognize_google(audio)

            print(f"\n[Test] Audio synthesis & speech recognition: '{recognized}'")
            self.assertIn("speech", recognized.lower())
            self.assertIn("recognition", recognized.lower())

        finally:
            for p in (mp3_path, wav_path):
                if os.path.exists(p):
                    os.remove(p)

    def test_05_tts_and_afplay_availability(self):
        """Verifies TTS MP3 generation and native macOS afplay availability."""
        afplay_path = shutil.which("afplay")
        self.assertIsNotNone(afplay_path, "Native macOS /usr/bin/afplay not found!")
        print(f"\n[Test] Native macOS audio player found: {afplay_path}")

        mp3_path = self.engine.text_to_speech("Audio verification", lang_code="en", play_audio=False)
        self.assertIsNotNone(mp3_path)
        self.assertTrue(os.path.exists(mp3_path))
        os.remove(mp3_path)
        print("  ✓ TTS generated and cleaned up successfully.")

    def test_06_gui_initialization_and_queue(self):
        """Verifies that the CustomTkinter GUI initializes, renders, and processes queue events safely."""
        app = LinguaSyncApp()
        app.update_idletasks()
        app.update()

        # Send test messages to queue
        app.msg_queue.put({"type": "status", "text": "● Unit Testing", "color": "#10B981"})
        app.msg_queue.put({"type": "recognized", "text": "Testing recognition"})
        app.msg_queue.put({
            "type": "translated",
            "text": "Prueba de traducción",
            "tgt_name": "Spanish (Español)",
            "tgt_code": "es",
            "detected_name": "English",
            "original_text": "Testing recognition",
        })

        app._process_queue()
        app.update_idletasks()

        recog_val = app.txt_recognized.get("1.0", "end-1c").strip()
        trans_val = app.txt_translated.get("1.0", "end-1c").strip()
        hist_val = app.txt_history.get("1.0", "end-1c").strip()

        self.assertEqual(recog_val, "Testing recognition")
        self.assertEqual(trans_val, "Prueba de traducción")
        self.assertIn("Prueba de traducción", hist_val)

        app._on_closing()
        print("\n[Test] GUI initialization and queue processing verified successfully.")


if __name__ == "__main__":
    unittest.main()
