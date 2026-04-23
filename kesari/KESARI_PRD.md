# Product Requirements Document (PRD) - Kesari AI

## 1. Product Overview
**Kesari AI** is a standalone, local-first AI personal assistant desktop application. It has been built from the ground up to operate offline and API-free using a custom-trained PyTorch Transformer model. Kesari aims to be a high-performance, context-aware companion that natively integrates into the desktop environment through modern UI/UX principles, proactive system monitoring, and multimodal interactions.

## 2. Core Objectives
- **Local Intelligence:** Fully decouple from external LLM APIs (Nvidia, Ollama, HuggingFace) using a custom PyTorch GPT-style model.
- **Premium UX/UI:** Provide a world-class, fluid, and distraction-free native desktop experience (PySide6).
- **Multimodal & Voice-First:** Native Voice-in/Voice-out capabilities via Wake Word detection, Push-to-Talk, and STT/TTS integration.
- **Deep System Integration:** Proactively monitor the user's OS context (CPU, RAM, screen) and orchestrate desktop tools.
- **Persistent Memory:** Context-aware conversations with Vector-based RAG and SQLite long-term storage.

## 3. System Architecture & Tech Stack

### 3.1 AI Engine (`ai_brain/`)
- **Custom Model (`kesari_net.py`):** A bespoke, from-scratch PyTorch Transformer model (`KesariModel`). Includes multi-head self-attention, feed-forward layers, and custom token/positional embeddings.
- **Agent Orchestrator:** A multi-agent framework capable of reasoning, selecting tools, and streaming responses dynamically.
- **Workflow Engine:** Evaluates multi-step processes and coordinates tools safely (requires user approval for dangerous actions).

### 3.2 User Interface (`gui/`)
- **Framework:** PySide6 (Qt for Python).
- **Design System:** Dark mode, glassmorphic elements, fluid animations (typing indicators, fade-ins), custom scrollbars.
- **Core Views:**
  - **Main Window:** Chat interface, context-aware chips, settings, and analytics dashboard.
  - **Floating Widget (Focus Mode):** A Spotlight-like command menu summoned globally via `Ctrl+Space`.
  - **Voice Orb:** A dynamic audio visualizer showing listening/processing states.
  - **Tray Manager:** Silent background operations and notifications.

### 3.3 Voice & Audio Engine (`voice_engine/`)
- **Wake Word:** Continuous background listening for "Hey Jarvis" (or custom wake words) with Voice Activity Detection (VAD).
- **Speech-to-Text (STT) / Text-to-Speech (TTS):** Integrated with Sarvam API (configured for `hi-IN` and custom speakers like "meera").
- **Audio Rec/Play:** Direct sound device capturing and streaming.

### 3.4 Memory & State (`memory/`)
- **Vector Memory (RAG):** Local vector embeddings stored in `vector_memory/` for semantic search of past conversations.
- **Long Term Memory (SQLite):** Stores persistent conversation logs and metadata in `memory.db`.
- **Session Memory:** Sliding window of recent interactions to manage context limits.
- **User Profile Manager:** Tracks user preferences to personalize AI behavior.

### 3.5 Tools & Integrations (`tools/`, `plugins/`)
- **System Monitor:** Continuously tracks CPU, RAM, and Disk metrics. Alerts the AI to proactively warn the user if thresholds are breached (e.g., >85% CPU).
- **Vision Monitor:** Optional buffer that can capture screen context for the AI.
- **Plugin System:** Watcher directory for hot-reloading new Python tools/plugins.
- **Companion API (`api/`):** FastAPI/Uvicorn server running on port 8765, allowing the assistant to be accessed remotely via a local network or securely via a pyngrok tunnel.

## 4. Key Features & User Flows

1. **Global Access:** User presses `Ctrl+Space` anywhere on the OS -> Floating widget appears -> User types command -> AI executes tool or answers.
2. **Hands-Free Voice Mode:** User says "Hey Jarvis" -> Window focuses -> Voice Orb pulses with mic levels -> VAD detects silence -> Transcribes audio -> AI streams response -> TTS reads it aloud.
3. **Proactive Assistance:** System Monitor detects RAM is at 95% -> Triggers internal event -> AI pushes a message: "⚠️ High RAM usage detected. Want me to close some apps?"
4. **Contextual Memory:** User says "Remember my favorite color is Blue" -> Saved to VectorDB. In a new session, user asks "What's my favorite color?" -> AI retrieves context and answers correctly.
5. **Mobile Companion:** App spins up an Ngrok tunnel -> Prints a secure URL to chat -> User opens URL on their phone -> Uses phone mic/UI to talk to their desktop Kesari instance.

## 5. Directory Structure Overview
- `ai_brain/`: Agent orchestrator, workflow engine, custom local PyTorch model, and prompt templates.
- `api/`: FastAPI server for the Companion API.
- `automation/`: Scripts for system-level OS macros.
- `gui/`: All PySide6 views, widgets, and stylesheets.
- `memory/`: Vector DB, SQLite managers, and Audit Loggers.
- `plugins/`: Drop-in Python scripts that extend tool capabilities.
- `tools/`: Native system tools (System Monitor, Vision Buffer, Profile Updater).
- `voice_engine/`: STT, TTS, Wake Word, and audio processing logic.
- `config.py`: Environment loader, settings manager (Keyring integration).
- `main.py`: Entry point, asyncio worker thread management, app wiring.
