# 🦁 Kesari AI — Autonomous Personal Desktop Assistant

> A production-grade, modular AI assistant for Windows. Built with PySide6, OpenRouter, and a multi-agent architecture. Voice-powered, context-aware, and extendable.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%206.6+-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-E85D04)](LICENSE)

---

## ✨ Feature Overview

### 🧠 AI Brain & Multi-Agent Orchestration
- **OpenRouter API** — GPT-4o, Claude 3.5, Llama 3, Gemini, and more
- **Multi-Agent Routing** — Automatically dispatches to the right specialist:
  - 🔍 **ResearchAgent** — web search, fact-finding, summarization
  - 💻 **CodingAgent** — code writing, debugging, explanation
  - ⚙️ **SystemAgent** — OS automation, shell, clipboard
  - 💬 **GeneralAgent** — conversation, creative tasks
- **WorkflowEngine** — Iterative tool-calling loop (up to N steps per query)
- **Streaming responses** — Token-by-token display in real time
- **Audit Logger** — Every tool execution logged to `audit.db`

### 🎤 Voice Engine
- **Push-to-talk** — Hold mic button to speak
- **Wake Word** — Hands-free activation via openWakeWord
- **Sarvam AI STT** — Hindi + English speech-to-text
- **Sarvam AI TTS** — Interruptible natural voice responses
- **Animated voice orb** — Live visual feedback

### 💻 System Control
| Action | Example |
|---|---|
| Open apps | "Open Chrome", "Launch VS Code" |
| Close apps | "Close Spotify" |
| File search | "Find my resume PDF" |
| Screenshots | "Take a screenshot" |
| System info | "Show my system stats" |
| Clipboard | "Copy this to clipboard" |
| Shell commands | "Run `git status`" |

### 🌐 Browser Agent
- **Playwright automation** — Navigate, click, fill forms
- **Google search** — "Search Google for Python tutorials"
- **Web scraping** — Extract page content for AI context

### 🧠 Memory & Learning
- **Long-term memory** — SQLite conversation history
- **Vector RAG** — ChromaDB semantic search over past conversations
- **User Profile** — AI remembers your name, preferences, and facts
  - Persists to `~/.kesari_ai/user_profile.json`
  - AI can autonomously update the profile mid-conversation
- **Screen Context** — AI can optionally read your active screen

### 📊 Analytics Dashboard
- **Real-time system health** — CPU, RAM, Disk gauges (live refresh)
- **Usage statistics** — Messages, conversations, tasks completed
- **Tool breakdown** — Most-used tools ranked by execution count
- **Proactive alerts** — AI warns you when resources spike and offers tips

### 📱 Mobile Companion API
- **FastAPI server** — Access Kesari from your phone or tablet
- **WebSocket streaming** — Live token streaming over WebSocket
- **REST endpoint** — Simple `POST /chat` for integrations
- **Web client** — Mobile-optimised dark UI, no app install needed
- **Agent chip selector** — Pick a specialist agent from the web UI

### 🧩 Plugin System
- **JSON-based** — Define tools in `plugin.json`, implement in `main.py`
- **Hot-reload** — Drop plugins into `plugins/` while running
- **Audit trail** — Every plugin execution is logged

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Windows 10/11**
- **Microphone** (for voice features)

### 1. Clone & Create virtual environment

```bash
git clone https://github.com/your-username/kesari.git
cd kesari
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure API Keys

```bash
copy .env.example .env
```

Edit `.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
SARVAM_API_KEY=your-sarvam-key-here
DEFAULT_MODEL=openai/gpt-4o
```

**Get your keys:**
- OpenRouter → https://openrouter.ai/keys
- Sarvam AI → https://dashboard.sarvam.ai/

### 4. Run

```bash
python -m kesari.main
```

---

## 📁 Project Structure

```
kesari/
├── kesari/                       # Main package
│   ├── main.py                   # App entry point & orchestration
│   ├── config.py                 # Settings & environment config
│   │
│   ├── ai_brain/                 # LLM integration
│   │   ├── openrouter_client.py  # Streaming + tool calling
│   │   ├── tool_router.py        # Function call dispatcher
│   │   ├── workflow_engine.py    # Multi-step tool loop
│   │   ├── agent_orchestrator.py # Multi-agent routing ✨
│   │   └── prompts.py            # System prompts
│   │
│   ├── api/                      # Mobile Companion API ✨
│   │   ├── server.py             # FastAPI REST + WebSocket
│   │   └── web_client.html       # Mobile web front-end
│   │
│   ├── voice_engine/             # Voice system
│   │   ├── sarvam_stt.py         # Speech-to-text
│   │   ├── sarvam_tts.py         # Text-to-speech
│   │   ├── audio_recorder.py     # Mic capture
│   │   ├── audio_player.py       # Audio playback
│   │   └── wake_word.py          # Wake word detection
│   │
│   ├── gui/                      # PySide6 UI
│   │   ├── main_window.py        # Main window & sidebar
│   │   ├── chat_widget.py        # Chat bubbles + Markdown
│   │   ├── voice_orb.py          # Animated voice orb
│   │   ├── floating_widget.py    # Spotlight command bar
│   │   ├── settings_dialog.py    # Settings panel
│   │   ├── analytics_widget.py   # Analytics dashboard ✨
│   │   ├── tray_manager.py       # System tray
│   │   └── styles.py             # Dark theme QSS
│   │
│   ├── tools/                    # System control tools
│   │   ├── open_app.py
│   │   ├── close_app.py
│   │   ├── search_file.py
│   │   ├── open_website.py
│   │   ├── system_commands.py
│   │   ├── clipboard_tool.py
│   │   ├── screen_context.py     # Screen reading ✨
│   │   ├── system_monitor.py     # Resource monitoring ✨
│   │   ├── profile_tools.py      # Profile update tool ✨
│   │   ├── base_tool.py
│   │   ├── registry.py
│   │   └── plugin_loader.py
│   │
│   └── memory/                   # Persistence layer
│       ├── session_memory.py     # In-session history
│       ├── long_term_memory.py   # SQLite conversations & tasks
│       ├── vector_memory.py      # ChromaDB RAG ✨
│       ├── user_profile.py       # User preference learning ✨
│       └── audit_logger.py       # Tool execution log ✨
│
├── plugins/                      # Plugin directory
│   └── example_plugin/
├── requirements.txt
├── .env.example
└── README.md
```

> ✨ = added in the v1.0 upgrade cycle (Phases 3–6)

---

## 🤖 Agent Guide

Kesari automatically selects the best agent, but you can also direct it:

| Say…                        | Agent Selected   |
|-----------------------------|------------------|
| "Search for X"              | 🔍 ResearchAgent |
| "Write a Python script for…"| 💻 CodingAgent   |
| "Open Chrome"               | ⚙️ SystemAgent   |
| "Tell me a joke"            | 💬 GeneralAgent  |

The active agent name is shown in the chat as a subtle badge.

---

## 📱 Companion API

Access Kesari from any device on your local network.

### Enable

In Settings, enable **Companion API** (or call `kesari.start_api_server(port=8765)` in code).

### Use the web client

Navigate to `http://<your-pc-ip>:8765` on your phone or any browser.

### REST API

```bash
# Single-turn chat
curl -X POST http://localhost:8765/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What time is it?", "agent": "general"}'

# Health check
curl http://localhost:8765/health

# List agents
curl http://localhost:8765/agents
```

### WebSocket (streaming)
```javascript
const ws = new WebSocket("ws://localhost:8765/ws/chat");
ws.send(JSON.stringify({ message: "Tell me a joke", agent: null }));
ws.onmessage = (e) => {
  const event = JSON.parse(e.data);
  if (event.type === "token") process.stdout.write(event.content);
};
```

---

## 🧩 Creating Plugins

1. Create a folder in `plugins/`:
```
plugins/my_plugin/
├── plugin.json
└── main.py
```

2. Define in `plugin.json`:
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

4. Restart Kesari AI — the plugin loads automatically and hot-reloads on save.

---

## ⚙️ Settings Reference

| Setting | Default | Description |
|---|---|---|
| `openrouter_api_key` | — | LLM API key |
| `sarvam_api_key` | — | Voice API key |
| `default_model` | `openai/gpt-4o` | LLM model |
| `tts_language` | `hi-IN` | TTS language |
| `tts_speaker` | `meera` | TTS voice |
| `stt_language` | `hi-IN` | STT language |
| `enable_proactive_monitoring` | `true` | CPU/RAM/disk alerts |
| `cpu_threshold` | `85` | CPU alert % |
| `ram_threshold` | `90` | RAM alert % |
| `disk_threshold` | `95` | Disk alert % |
| `enable_companion_api` | `false` | Start HTTP API server |
| `companion_api_port` | `8765` | API server port |
| `confirm_dangerous_actions` | `true` | Confirmation gate |

---

## 🔐 Security

- API keys stored locally in `~/.kesari_ai/settings.json` (never sent anywhere except the intended API)
- Dangerous tools (shell commands, close app) are gated behind `DANGEROUS_TOOLS` approval list in `workflow_engine.py`
- Fork bombs and destructive shell patterns are blocked in `system_commands.py`
- Companion API runs on localhost only by default; bind to `0.0.0.0` at your own discretion (LAN only, no auth by default)
- Plugin code is sandboxed with module-level import isolation

---

## 📋 Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| GUI | PySide6 (Qt6) |
| LLM | OpenRouter API (OpenAI SDK) |
| Local LLM | Ollama |
| Voice STT | Sarvam AI `saaras:v3` |
| Voice TTS | Sarvam AI `bulbul:v3` |
| Audio I/O | sounddevice + numpy |
| Browser | Playwright (Chromium) |
| Database | SQLite (aiosqlite) |
| Vector DB | ChromaDB |
| API Server | FastAPI + Uvicorn |
| Monitoring | psutil |
| OS Control | psutil, subprocess, Pillow, mss |
| Wake Word | openWakeWord |

---

## 🗺️ Roadmap

- [x] Phase 1 — Core AI + voice + tool calling
- [x] Phase 2 — System control + browser automation + plugins
- [x] Phase 3 — Long-term memory + vector RAG + wake word
- [x] Phase 4 — Security hardening + audit logging + screen context
- [x] Phase 5 — Analytics dashboard + proactive monitoring + user profile learning
- [x] Phase 6 — Multi-agent orchestration + mobile companion API
- [ ] Phase 7 — Cloud sync, notifications, calendar integration

---

## 📄 License

MIT © 2024 — Built with 🦁 by the Kesari AI team.
