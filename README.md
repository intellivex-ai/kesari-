# 🦁 Kesari AI — Personal Desktop Assistant

A powerful, modular desktop AI assistant built with Python. Features a modern dark UI, voice interaction, system control, browser automation, and an extensible plugin system.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green)
![License](https://img.shields.io/badge/License-MIT-orange)

---

## ✨ Features

### 🧠 AI Brain
- **OpenRouter API** — Access GPT-4o, Claude, Llama, Gemini, and more
- **Streaming responses** — Real-time token-by-token display
- **Function/Tool calling** — AI decides which tools to use automatically

### 🎤 Voice Assistant
- **Push-to-talk** — Hold the mic button to speak
- **Sarvam AI STT** — Speech-to-text in Hindi + English
- **Sarvam AI TTS** — Natural voice responses with interruptible playback
- **Animated voice orb** — Visual feedback during voice interaction

### 💻 System Control
- **Open/Close apps** — "Open Chrome", "Close Spotify"
- **File search** — "Find my resume PDF"
- **Screenshots** — "Take a screenshot"
- **System info** — "Show my system status"
- **Clipboard** — "Copy this to clipboard"
- **Commands** — Run PowerShell/CMD commands

### 🌐 Browser Agent
- **Playwright automation** — Navigate, click, type in real browsers
- **Google search** — "Search Google for..."
- **Web scraping** — Extract text from web pages

### 🧩 Plugin System
- **JSON-based registration** — Define tools in `plugin.json`
- **Dynamic loading** — Drop plugins into `plugins/` folder
- **Example included** — Time and calculator plugins

### 🖥️ Modern UI
- **Dark glassmorphism** — Premium dark theme with saffron accent
- **Chat bubbles** — Markdown rendering with code blocks
- **Floating widget** — Spotlight-like quick command (Ctrl+Space)
- **Frameless window** — Custom title bar with drag and resize

---

## 🚀 Setup

### Prerequisites
- Python 3.11 or higher
- Windows 10/11
- Microphone (for voice features)

### 1. Clone & Install

```bash
cd kesari
pip install -r requirements.txt
```

### 2. Install Playwright browsers (for browser automation)

```bash
playwright install chromium
```

### 3. Configure API Keys

Copy the example env file and add your keys:

```bash
copy .env.example .env
```

Edit `.env`:
```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
SARVAM_API_KEY=your-sarvam-key-here
DEFAULT_MODEL=openai/gpt-4o
```

**Get your keys:**
- OpenRouter: [https://openrouter.ai/keys](https://openrouter.ai/keys)
- Sarvam AI: [https://dashboard.sarvam.ai/](https://dashboard.sarvam.ai/)

### 4. Run

```bash
python -m kesari.main
```

---

## 📁 Project Structure

```
kesari/
├── kesari/                    # Main package
│   ├── main.py                # Entry point — wires everything
│   ├── config.py              # Configuration & settings
│   ├── ai_brain/              # LLM integration
│   │   ├── openrouter_client.py   # Streaming + tool calling
│   │   ├── tool_router.py         # Function call dispatcher
│   │   └── prompts.py             # System prompts
│   ├── voice_engine/          # Voice system
│   │   ├── sarvam_stt.py          # Speech-to-text
│   │   ├── sarvam_tts.py          # Text-to-speech
│   │   ├── audio_recorder.py      # Mic capture
│   │   └── audio_player.py        # Audio playback
│   ├── gui/                   # PySide6 UI
│   │   ├── main_window.py        # Main window layout
│   │   ├── chat_widget.py        # Chat bubbles
│   │   ├── voice_orb.py          # Animated orb
│   │   ├── floating_widget.py    # Spotlight command
│   │   ├── settings_dialog.py   # Settings panel
│   │   ├── styles.py            # Dark theme QSS
│   │   └── app.py               # QApplication setup
│   ├── tools/                 # System control tools
│   │   ├── open_app.py           # Open applications
│   │   ├── close_app.py          # Close applications
│   │   ├── search_file.py        # File search
│   │   ├── open_website.py       # Open URLs
│   │   ├── system_commands.py    # Screenshot, sysinfo, commands
│   │   ├── clipboard_tool.py     # Clipboard ops
│   │   ├── base_tool.py          # Tool base class
│   │   ├── registry.py           # Tool registration
│   │   └── plugin_loader.py      # Plugin system
│   ├── automation/            # Browser & workflows
│   │   ├── browser_agent.py      # Playwright browser
│   │   └── workflow_engine.py    # Multi-step execution
│   └── memory/                # Data persistence
│       ├── session_memory.py     # In-memory history
│       └── long_term_memory.py   # SQLite storage
├── plugins/                   # Plugin directory
│   └── example_plugin/
├── docs/                      # Documentation
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🎯 Usage Examples

| Command | What happens |
|---------|-------------|
| "Open Chrome" | Launches Google Chrome |
| "Close Spotify" | Terminates Spotify |
| "Find my resume PDF" | Searches Desktop/Documents/Downloads |
| "Take a screenshot" | Saves screenshot to Desktop |
| "What's my system status?" | Shows CPU, RAM, disk usage |
| "Open youtube.com" | Opens YouTube in browser |
| "What time is it?" | Calls the time plugin |

### Voice Mode
1. Hold the **🎤 button** and speak
2. Release — your speech is transcribed and sent to AI
3. AI responds in text + voice (TTS)

### Floating Mode
- Press **Ctrl+Space** anywhere to open the quick command input
- Type a command and press Enter
- Press **Escape** to dismiss

---

## 🧩 Creating Plugins

1. Create a folder in `plugins/`:
```
plugins/my_plugin/
├── plugin.json
└── main.py
```

2. Define tools in `plugin.json`:
```json
{
    "name": "my_plugin",
    "version": "1.0.0",
    "tools": [
        {
            "name": "my_tool",
            "function": "my_function",
            "description": "Does something useful",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Input text"}
                },
                "required": ["input"]
            }
        }
    ]
}
```

3. Implement in `main.py`:
```python
def my_function(input: str) -> dict:
    return {"status": "success", "result": f"Processed: {input}"}
```

4. Restart Kesari AI — the plugin is loaded automatically!

---

## ⚙️ Configuration

All settings are accessible via the **Settings** panel (⚙ button):

| Setting | Description |
|---------|-------------|
| OpenRouter API Key | Your API key for LLM access |
| Sarvam AI Key | API key for voice features |
| Default Model | LLM model (e.g., openai/gpt-4o) |
| TTS Language | Text-to-speech language |
| Speaker Voice | TTS voice selection |
| STT Language | Speech-to-text language |
| Confirm Actions | Require confirmation for dangerous commands |

---

## 🔐 Security

- API keys stored locally in `~/.kesari_ai/settings.json`
- Dangerous commands (shutdown, delete) require confirmation
- Fork bombs and destructive commands are blocked
- No data sent to external servers except API calls

---

## 📋 Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| GUI | PySide6 (Qt6) |
| LLM | OpenRouter API (OpenAI SDK) |
| Voice STT | Sarvam AI saaras:v3 |
| Voice TTS | Sarvam AI bulbul:v3 |
| Audio I/O | sounddevice + numpy |
| Browser | Playwright |
| Database | SQLite (aiosqlite) |
| OS Control | psutil, subprocess, PIL |
