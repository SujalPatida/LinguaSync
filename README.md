# 🎙️ LinguaSync – Real-Time Voice Translator

**LinguaSync** is an AI-powered desktop voice translator and speech synthesizer built with Python and modern CustomTkinter. It listens to spoken audio in real time, recognizes the speech, translates it into the desired target language, and speaks the translated result aloud with natural text-to-speech audio.

---

## 🌟 Key Highlights & Modern Enhancements

This project is a recreation and major architectural upgrade of the original [real-time-voice-translator](https://github.com/SamirPaulb/real-time-voice-translator) repository, rewritten for modern macOS systems:

* **Sleek Modern UI:** Built with CustomTkinter featuring clean dark/light mode cards, rounded corners, dynamic status pill indicators, and high-DPI Retina support.
* **Non-Blocking Threaded Architecture:** Speech recognition and audio playback run in isolated background threads communicating through thread-safe queues. The desktop interface never freezes or shows macOS beachballs.
* **Native macOS Audio Playback:** Replaced the unstable `playsound 1.2.2` library with macOS's native `/usr/bin/afplay` player for instant, crash-free audio without file-lock bugs.
* **Automatic Language Detection & Swapping:** "Auto Detect" source mode with instant language detection, plus a 1-click swap button `⇄` to invert source and target languages.
* **Extensive Language Support:** English, Hindi (हिन्दी), Tamil (தமிழ்), Telugu (తెలుగు), Bengali (বাংলা), Spanish (Español), French (Français), German (Deutsch), Japanese (日本語), Korean (한국어), plus Arabic, Chinese, Gujarati, Kannada, Malayalam, Marathi, Portuguese, Punjabi, Russian, and more.
* **Dual Output Panels:** Side-by-side cards for Recognized Speech and Translated Text with character counters and one-click **📋 Copy** buttons.
* **Conversation History & Log Export:** Persistent scrollable history log tracking every turn with timestamps `[HH:MM:SS]`, language badges, and a **💾 Export Log** button.
* **Permission & Error Handling:** Proactive detection of microphone hardware and helpful macOS permission guidance dialogs.

---

## 🍎 Complete macOS Installation Guide (Beginner-Friendly)

Follow these step-by-step instructions in your macOS **Terminal**.

### 1. Prerequisites

Make sure you have **Homebrew** and **Python 3** installed. If you do not have Homebrew, install it with:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install PortAudio (Required for PyAudio)
PyAudio needs the `portaudio` C-library to capture microphone audio on macOS:
```bash
brew install portaudio
```

### 3. Open Project Directory
Open Terminal and navigate to the project folder:
```bash
cd /Users/sujalpatidar/Documents/LinguaSync
```

### 4. Create and Activate a Virtual Environment
A virtual environment keeps your project dependencies isolated and clean:
```bash
# Create the virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```
*(When activated, your terminal prompt will show `(venv)`).*

### 5. Install Dependencies
Run:
```bash
pip install -r requirements.txt
```

> **Note for Apple Silicon Macs (M1/M2/M3/M4):** If PyAudio ever asks for PortAudio header paths during installation, run:
> ```bash
> CFLAGS="-I/opt/homebrew/include" LDFLAGS="-L/opt/homebrew/lib" pip install pyaudio
> ```

---

## 🔒 Granting macOS Microphone Permissions

When you run LinguaSync for the first time, macOS will ask for permission to access your microphone.

If the prompt does not appear, or if you accidentally clicked "Don't Allow":
1. Open the **Apple menu ** in the top left corner of your screen.
2. Click **System Settings...** (or **System Preferences**).
3. In the sidebar, select **Privacy & Security**.
4. Scroll down and click on **Microphone**.
5. Find **Terminal** (or **VS Code** / **Cursor** / **Python**) in the list and toggle the switch to **ON (green)**.
6. Restart the application.

---

## 🚀 Running LinguaSync

With your virtual environment activated:
```bash
python3 main.py
```

---

## 📖 How to Use

1. **Select Source & Target Languages:**
   * Choose **Auto Detect** or pick your spoken language from the **Source Language** dropdown.
   * Pick the language you want to translate into from the **Target Language** dropdown (e.g., Hindi, Spanish, French, Japanese, Tamil, etc.).
2. **Start Listening:**
   * Click **🎙️ Start Listening**. The status badge in the header will turn green and display `🎙️ Listening...`.
3. **Speak into your Microphone:**
   * Speak naturally. LinguaSync will capture your audio, display the recognized text in the left panel, and display the translation in the right panel.
4. **Audio Playback:**
   * If **🔊 Auto-Play Speech** is enabled, LinguaSync will automatically speak the translation out loud.
   * You can also click the blue **🔊 Listen** button in the translated card at any time to replay the translation.
   * Click **🔇 Mute Audio** to stop any ongoing speech playback.
5. **Stop Listening:**
   * Click **⏹️ Stop** (or simply say *"stop"* / *"exit"* aloud into the microphone).
6. **Manage History:**
   * Review all conversation turns in the **Conversation History** box.
   * Click **💾 Export Log** to save the conversation transcript to a `.txt` file, or **🗑️ Clear History** to start fresh.

---

## 🏗️ Architecture & How It Works

```
                        ┌───────────────────────────────┐
                        │      Microphone Input         │
                        │    (MacBook Mic / Earbuds)    │
                        └──────────────┬────────────────┘
                                       │
                                       ▼
                        ┌───────────────────────────────┐
                        │    SpeechRecognition Engine   │
                        │  (Google Speech-to-Text API)  │
                        └──────────────┬────────────────┘
                                       │
                        ┌──────────────┴────────────────┐
                        │                               │
                        ▼                               ▼
             [Recognized Text]               [Source Lang Detected]
                        │                               │
                        └──────────────┬────────────────┘
                                       │
                                       ▼
                        ┌───────────────────────────────┐
                        │   Translator Engine Core      │
                        │ (Google Client API + Fallback)│
                        └──────────────┬────────────────┘
                                       │
                                       ▼
                        ┌───────────────────────────────┐
                        │   Translated Text Output      │
                        └──────────────┬────────────────┘
                                       │
                                       ▼
                        ┌───────────────────────────────┐
                        │   Google TTS Engine (gTTS)    │
                        │      + macOS afplay Player    │
                        └──────────────┬────────────────┘
                                       │
                                       ▼
                        ┌───────────────────────────────┐
                        │   Audio Output (Speakers)     │
                        └───────────────────────────────┘
```

### Module Breakdown
* `translator_engine.py`: Encapsulates speech recognition, translation strategy with auto-detection, and TTS generation with macOS `afplay`.
* `gui.py`: CustomTkinter user interface, queue polling, dark/light theme handling, and clipboard utilities.
* `main.py`: Entry point with dependency verification and user-friendly error guidance.

---

## 🛠️ Troubleshooting

* **Issue: "No matching distribution found" / "portaudio.h not found"**
  * *Fix:* Run `brew install portaudio`, then reinstall pyaudio with compiler flags:
    ```bash
    CFLAGS="-I/opt/homebrew/include" LDFLAGS="-L/opt/homebrew/lib" pip install pyaudio
    ```
* **Issue: "Certificate Verify Failed" on macOS Python**
  * *Fix:* Run the certificate installation script shipped with Python on macOS:
    ```bash
    /Applications/Python\ 3.14/Install\ Certificates.command
    ```
* **Issue: Microphone not picking up sound**
  * *Fix:* Verify that your input volume in **System Settings > Sound > Input** is set to at least 75%, and check that Terminal has microphone permissions under **System Settings > Privacy & Security > Microphone**.
