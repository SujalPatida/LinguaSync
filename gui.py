"""
LinguaSync - Modern Desktop GUI
-------------------------------
Built with CustomTkinter for a sleek, responsive, macOS-native look and feel.
Features:
- Live speech recognition and real-time translation
- Distinct panels for recognized and translated text
- Conversation history log with timestamps and language badges
- Start / Stop microphone controls with status indicators
- Auto-play voice toggle and manual 'Listen Again' button
- Copy to clipboard and history management
- 100% thread-safe background architecture (zero UI freezing)
"""

from __future__ import annotations

import datetime
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from translator_engine import (
    SUPPORTED_LANGUAGES,
    TARGET_LANGUAGES,
    TranslatorEngine,
    get_language_display_name,
)

# Set global appearance mode and color theme
ctk.set_appearance_mode("System")  # Follows macOS Light/Dark mode
ctk.set_default_color_theme("blue")


class LinguaSyncApp(ctk.CTk):
    """Modern Desktop GUI for LinguaSync Real-Time Voice Translator."""

    def __init__(self) -> None:
        super().__init__()

        # Window Configuration
        self.title("LinguaSync – Real-Time Voice Translator")
        self.geometry("980x780")
        self.minsize(860, 680)

        # Initialize Backend Engine and Queues
        self.engine = TranslatorEngine()
        self.msg_queue: queue.Queue = queue.Queue()
        self.is_listening = False
        self.worker_thread: Optional[threading.Thread] = None

        # Last translated audio path for replay
        self.last_audio_file: Optional[str] = None
        self.last_translated_text: str = ""
        self.last_target_code: str = "en"

        # Build Interface
        self._build_ui()

        # Start thread-safe queue poller
        self.after(50, self._process_queue)

        # Window closing handler for clean shutdown
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Pre-check microphone status
        self.after(400, self._initial_mic_check)

    def _build_ui(self) -> None:
        """Constructs all GUI components."""
        # Top Header Bar
        self.header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=("gray90", "gray17"))
        self.header_frame.pack(fill="x", padx=20, pady=(15, 10))

        # Title & Subtitle
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=12)

        self.lbl_title = ctk.CTkLabel(
            title_box,
            text="🎙️ LinguaSync",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        self.lbl_title.pack(anchor="w")

        self.lbl_subtitle = ctk.CTkLabel(
            title_box,
            text="Real-Time Multilingual Voice Translator & Speech Synthesizer",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray65"),
        )
        self.lbl_subtitle.pack(anchor="w")

        # Right-side status badge
        self.status_badge = ctk.CTkLabel(
            self.header_frame,
            text="● Ready",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("gray80", "gray25"),
            corner_radius=16,
            padx=14,
            pady=6,
            text_color=("gray20", "gray85"),
        )
        self.status_badge.pack(side="right", padx=16, pady=12)

        # Appearance mode toggle (Dark / Light)
        self.theme_menu = ctk.CTkOptionMenu(
            self.header_frame,
            values=["System", "Dark", "Light"],
            command=self._change_appearance_mode,
            width=90,
            height=28,
            font=ctk.CTkFont(size=11),
        )
        self.theme_menu.pack(side="right", padx=(0, 10), pady=12)

        # Controls & Language Selection Frame
        self.controls_card = ctk.CTkFrame(self, corner_radius=12)
        self.controls_card.pack(fill="x", padx=20, pady=8)

        # Control Row 1: Languages
        lang_row = ctk.CTkFrame(self.controls_card, fg_color="transparent")
        lang_row.pack(fill="x", padx=16, pady=(12, 6))

        # Source Language Selector
        src_box = ctk.CTkFrame(lang_row, fg_color="transparent")
        src_box.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkLabel(src_box, text="Source Language:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 4))
        self.src_lang_menu = ctk.CTkOptionMenu(
            src_box,
            values=list(SUPPORTED_LANGUAGES.keys()),
            dynamic_resizing=False,
            height=34,
        )
        self.src_lang_menu.set("Auto Detect")
        self.src_lang_menu.pack(fill="x")

        # Swap Button
        self.btn_swap = ctk.CTkButton(
            lang_row,
            text="⇄",
            width=38,
            height=34,
            font=ctk.CTkFont(size=18, weight="bold"),
            command=self._swap_languages,
        )
        self.btn_swap.pack(side="left", padx=6, pady=(20, 0))

        # Target Language Selector
        tgt_box = ctk.CTkFrame(lang_row, fg_color="transparent")
        tgt_box.pack(side="left", fill="x", expand=True, padx=(8, 0))

        ctk.CTkLabel(tgt_box, text="Target Language:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 4))
        self.tgt_lang_menu = ctk.CTkOptionMenu(
            tgt_box,
            values=list(TARGET_LANGUAGES.keys()),
            dynamic_resizing=False,
            height=34,
        )
        self.tgt_lang_menu.set("Spanish (Español)")
        self.tgt_lang_menu.pack(fill="x")

        # Control Row 2: Action Buttons & Options
        btn_row = ctk.CTkFrame(self.controls_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(8, 14))

        # Start Listening Button
        self.btn_start = ctk.CTkButton(
            btn_row,
            text="🎙️ Start Listening",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            height=38,
            command=self.start_listening,
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        # Stop Listening Button
        self.btn_stop = ctk.CTkButton(
            btn_row,
            text="⏹️ Stop",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#EF4444",
            hover_color="#DC2626",
            height=38,
            state="disabled",
            command=self.stop_listening,
        )
        self.btn_stop.pack(side="left", padx=10)

        # Auto-Speak Switch
        self.auto_speak_var = ctk.BooleanVar(value=True)
        self.switch_speak = ctk.CTkSwitch(
            btn_row,
            text="🔊 Auto-Play Speech",
            variable=self.auto_speak_var,
            font=ctk.CTkFont(size=12),
        )
        self.switch_speak.pack(side="left", padx=18)

        # Stop Audio Playback Button
        self.btn_stop_audio = ctk.CTkButton(
            btn_row,
            text="🔇 Mute Audio",
            font=ctk.CTkFont(size=12),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            height=32,
            width=100,
            command=self.engine.stop_playback,
        )
        self.btn_stop_audio.pack(side="right")

        # Dual Text Panels: Recognized & Translated
        panels_container = ctk.CTkFrame(self, fg_color="transparent")
        panels_container.pack(fill="both", expand=True, padx=20, pady=6)

        # Configure 2 equal columns
        panels_container.grid_columnconfigure(0, weight=1, uniform="group1")
        panels_container.grid_columnconfigure(1, weight=1, uniform="group1")
        panels_container.grid_rowconfigure(0, weight=1)

        # Left Panel: Recognized Speech
        self.recog_card = ctk.CTkFrame(panels_container, corner_radius=12)
        self.recog_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)

        recog_top = ctk.CTkFrame(self.recog_card, fg_color="transparent")
        recog_top.pack(fill="x", padx=12, pady=(10, 4))

        self.lbl_recog_header = ctk.CTkLabel(
            recog_top,
            text="🗣️ Recognized Speech",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.lbl_recog_header.pack(side="left")

        self.btn_copy_recog = ctk.CTkButton(
            recog_top,
            text="📋 Copy",
            width=65,
            height=26,
            font=ctk.CTkFont(size=11),
            command=lambda: self._copy_to_clipboard(self.txt_recognized.get("1.0", "end-1c")),
        )
        self.btn_copy_recog.pack(side="right")

        self.txt_recognized = ctk.CTkTextbox(
            self.recog_card,
            wrap="word",
            font=ctk.CTkFont(size=13),
            corner_radius=8,
        )
        self.txt_recognized.pack(fill="both", expand=True, padx=12, pady=(4, 8))

        self.lbl_recog_footer = ctk.CTkLabel(
            self.recog_card,
            text="Language: Auto Detect",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray65"),
        )
        self.lbl_recog_footer.pack(anchor="w", padx=14, pady=(0, 8))

        # Right Panel: Translated Output
        self.trans_card = ctk.CTkFrame(panels_container, corner_radius=12)
        self.trans_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)

        trans_top = ctk.CTkFrame(self.trans_card, fg_color="transparent")
        trans_top.pack(fill="x", padx=12, pady=(10, 4))

        self.lbl_trans_header = ctk.CTkLabel(
            trans_top,
            text="🌐 Translated Output",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.lbl_trans_header.pack(side="left")

        self.btn_listen_again = ctk.CTkButton(
            trans_top,
            text="🔊 Listen",
            width=70,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#3B82F6",
            hover_color="#2563EB",
            command=self._replay_translation,
        )
        self.btn_listen_again.pack(side="right", padx=(6, 0))

        self.btn_copy_trans = ctk.CTkButton(
            trans_top,
            text="📋 Copy",
            width=65,
            height=26,
            font=ctk.CTkFont(size=11),
            command=lambda: self._copy_to_clipboard(self.txt_translated.get("1.0", "end-1c")),
        )
        self.btn_copy_trans.pack(side="right")

        self.txt_translated = ctk.CTkTextbox(
            self.trans_card,
            wrap="word",
            font=ctk.CTkFont(size=13),
            corner_radius=8,
        )
        self.txt_translated.pack(fill="both", expand=True, padx=12, pady=(4, 8))

        self.lbl_trans_footer = ctk.CTkLabel(
            self.trans_card,
            text="Language: Spanish (Español)",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray65"),
        )
        self.lbl_trans_footer.pack(anchor="w", padx=14, pady=(0, 8))

        # Conversation History Section
        self.history_card = ctk.CTkFrame(self, corner_radius=12)
        self.history_card.pack(fill="both", expand=True, padx=20, pady=(6, 15))

        hist_top = ctk.CTkFrame(self.history_card, fg_color="transparent")
        hist_top.pack(fill="x", padx=14, pady=(8, 4))

        ctk.CTkLabel(
            hist_top,
            text="📜 Conversation History",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left")

        self.btn_save_history = ctk.CTkButton(
            hist_top,
            text="💾 Export Log",
            width=85,
            height=26,
            font=ctk.CTkFont(size=11),
            command=self._export_history,
        )
        self.btn_save_history.pack(side="right", padx=(6, 0))

        self.btn_clear_history = ctk.CTkButton(
            hist_top,
            text="🗑️ Clear History",
            width=90,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            command=self._clear_history,
        )
        self.btn_clear_history.pack(side="right")

        self.txt_history = ctk.CTkTextbox(
            self.history_card,
            wrap="word",
            font=ctk.CTkFont(size=12),
            corner_radius=8,
            height=120,
        )
        self.txt_history.pack(fill="both", expand=True, padx=12, pady=(4, 10))

    def _initial_mic_check(self) -> None:
        """Runs an initial check for microphone availability."""
        avail, msg = self.engine.check_microphone_available()
        if not avail:
            self._set_status("⚠️ Mic Error", "#EF4444")
            self._append_history("SYSTEM", f"Microphone Warning: {msg}\nCheck macOS System Settings > Privacy & Security > Microphone.")
            messagebox.showwarning(
                "Microphone Check",
                f"{msg}\n\nPlease verify that your microphone is plugged in and that Terminal/Python has microphone permission granted in macOS System Settings.",
            )
        else:
            self._set_status("● Ready", "#10B981")

    def _change_appearance_mode(self, new_mode: str) -> None:
        """Switches between Dark, Light, and System themes."""
        ctk.set_appearance_mode(new_mode)

    def _swap_languages(self) -> None:
        """Swaps source and target languages if source is not Auto Detect."""
        src_name = self.src_lang_menu.get()
        tgt_name = self.tgt_lang_menu.get()

        if src_name == "Auto Detect":
            messagebox.showinfo("Swap Languages", "Cannot swap when Source is 'Auto Detect'. Please select a specific source language to swap.")
            return

        if src_name in TARGET_LANGUAGES and tgt_name in SUPPORTED_LANGUAGES:
            self.src_lang_menu.set(tgt_name)
            self.tgt_lang_menu.set(src_name)

    def _set_status(self, text: str, color: str) -> None:
        """Updates the status pill badge on the header."""
        self.status_badge.configure(text=text, text_color=color)

    def start_listening(self) -> None:
        """Starts the background listening and translation worker thread."""
        if self.is_listening:
            return

        self.is_listening = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.src_lang_menu.configure(state="disabled")
        self.tgt_lang_menu.configure(state="disabled")
        self.btn_swap.configure(state="disabled")
        self._set_status("🎙️ Listening...", "#10B981")

        # Launch worker thread
        self.worker_thread = threading.Thread(
            target=self._listening_worker_loop,
            daemon=True,
            name="LinguaSyncWorker",
        )
        self.worker_thread.start()

    def stop_listening(self) -> None:
        """Signals the background worker to halt listening."""
        self.is_listening = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.src_lang_menu.configure(state="normal")
        self.tgt_lang_menu.configure(state="normal")
        self.btn_swap.configure(state="normal")
        self._set_status("● Ready", "#3B82F6")

    def _listening_worker_loop(self) -> None:
        """
        Background loop: listens for speech, transcribes, translates, and speaks.
        Pushes results to the thread-safe message queue.
        """
        while self.is_listening:
            src_name = self.src_lang_menu.get()
            tgt_name = self.tgt_lang_menu.get()
            src_code = SUPPORTED_LANGUAGES.get(src_name, "auto")
            tgt_code = TARGET_LANGUAGES.get(tgt_name, "es")

            self.msg_queue.put({"type": "status", "text": "🎙️ Listening...", "color": "#10B981"})

            # Capture speech
            transcribed_text, err = self.engine.listen_and_transcribe(
                source_language_code=src_code,
                timeout=5.0,
                phrase_time_limit=15.0,
            )

            if not self.is_listening:
                break

            if err == "TIMEOUT":
                # Regular silence timeout, continue listening loop
                continue

            if err:
                self.msg_queue.put({"type": "error", "message": err})
                time.sleep(1.0)
                continue

            if transcribed_text:
                self.msg_queue.put({
                    "type": "recognized",
                    "text": transcribed_text,
                    "src_name": src_name,
                })

                # Check for stop voice commands
                if transcribed_text.lower() in ("exit", "stop", "quit", "stop listening"):
                    self.msg_queue.put({"type": "stop"})
                    break

                self.msg_queue.put({"type": "status", "text": "⚙️ Translating...", "color": "#F59E0B"})

                try:
                    translated_text, detected_code = self.engine.translate_text(
                        text=transcribed_text,
                        source_lang=src_code,
                        target_lang=tgt_code,
                    )

                    detected_name = get_language_display_name(detected_code)

                    self.msg_queue.put({
                        "type": "translated",
                        "text": translated_text,
                        "tgt_name": tgt_name,
                        "tgt_code": tgt_code,
                        "detected_name": detected_name,
                        "original_text": transcribed_text,
                    })

                    # Text to speech if auto-speak is enabled
                    if self.auto_speak_var.get() and self.is_listening:
                        self.msg_queue.put({"type": "status", "text": "🔊 Speaking...", "color": "#8B5CF6"})
                        self.engine.text_to_speech(
                            text=translated_text,
                            lang_code=tgt_code,
                            play_audio=True,
                        )

                except Exception as ex:
                    self.msg_queue.put({"type": "error", "message": f"Translation failed: {ex}"})

            time.sleep(0.1)

        self.msg_queue.put({"type": "status", "text": "● Stopped", "color": "#6B7280"})

    def _process_queue(self) -> None:
        """Safely processes updates from the worker thread on the main GUI thread."""
        try:
            while not self.msg_queue.empty():
                msg = self.msg_queue.get_nowait()
                mtype = msg.get("type")

                if mtype == "status":
                    self._set_status(msg.get("text", "● Ready"), msg.get("color", "#3B82F6"))

                elif mtype == "recognized":
                    text = msg.get("text", "")
                    self.txt_recognized.delete("1.0", "end")
                    self.txt_recognized.insert("1.0", text)

                elif mtype == "translated":
                    text = msg.get("text", "")
                    tgt_name = msg.get("tgt_name", "")
                    tgt_code = msg.get("tgt_code", "en")
                    detected_name = msg.get("detected_name", "")
                    original = msg.get("original_text", "")

                    self.txt_translated.delete("1.0", "end")
                    self.txt_translated.insert("1.0", text)

                    # Update footer indicators
                    self.lbl_recog_footer.configure(text=f"Detected: {detected_name}")
                    self.lbl_trans_footer.configure(text=f"Target: {tgt_name}")

                    # Store for manual replay
                    self.last_translated_text = text
                    self.last_target_code = tgt_code

                    # Record in Conversation History
                    self._append_history(
                        f"{detected_name} ➔ {tgt_name}",
                        f"Recognized: {original}\nTranslated: {text}",
                    )

                elif mtype == "error":
                    err_msg = msg.get("message", "An unexpected error occurred.")
                    self._set_status("⚠️ Notice", "#EF4444")
                    self.txt_translated.delete("1.0", "end")
                    self.txt_translated.insert("1.0", f"[{err_msg}]")
                    self._append_history("ERROR", err_msg)

                elif mtype == "stop":
                    self.stop_listening()

        except queue.Empty:
            pass
        finally:
            # Continue polling every 50 milliseconds
            self.after(50, self._process_queue)

    def _append_history(self, header: str, content: str) -> None:
        """Appends a new turn into the conversation history text box."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{header}]\n{content}\n{'-' * 45}\n"
        self.txt_history.insert("end", entry)
        self.txt_history.see("end")

    def _clear_history(self) -> None:
        """Clears the conversation history text area."""
        if messagebox.askyesno("Clear History", "Are you sure you want to clear the conversation history?"):
            self.txt_history.delete("1.0", "end")

    def _export_history(self) -> None:
        """Exports the conversation history to a text file."""
        content = self.txt_history.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showinfo("Export History", "Conversation history is currently empty.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Export Conversation History",
            initialfile=f"LinguaSync_History_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Export Successful", f"History saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Could not save file: {e}")

    def _replay_translation(self) -> None:
        """Re-synthesizes and speaks the most recent translated text on demand."""
        text = self.txt_translated.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showinfo("Listen", "No translated text to speak.")
            return

        tgt_name = self.tgt_lang_menu.get()
        tgt_code = TARGET_LANGUAGES.get(tgt_name, "en")

        def run_tts():
            self._set_status("🔊 Speaking...", "#8B5CF6")
            self.engine.text_to_speech(text, lang_code=tgt_code, play_audio=True)
            self._set_status("● Ready", "#10B981" if self.is_listening else "#3B82F6")

        threading.Thread(target=run_tts, daemon=True).start()

    def _copy_to_clipboard(self, text: str) -> None:
        """Copies given text to the macOS system clipboard."""
        clean = text.strip()
        if not clean:
            return
        self.clipboard_clear()
        self.clipboard_append(clean)
        self.update()
        self._set_status("📋 Copied!", "#10B981")
        self.after(1500, lambda: self._set_status("🎙️ Listening..." if self.is_listening else "● Ready", "#10B981" if self.is_listening else "#3B82F6"))

    def _on_closing(self) -> None:
        """Clean shutdown when user closes window."""
        self.is_listening = False
        self.engine.stop_playback()
        self.destroy()


def run_gui() -> None:
    """Launches the LinguaSync desktop GUI application."""
    app = LinguaSyncApp()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
