PRODUCT REQUIREMENTS DOCUMENT (PRD)
🧩 Product Name

Kesari AI – Personal Desktop Assistant

🎯 Objective

To build a local-first AI assistant that:

Enhances productivity
Controls the PC via voice + chat
Automates workflows using AI + browser agents
👤 Target Users
Developers
Students
Creators
Power users
🧱 Tech Stack
Backend (Core Engine)
Python
FastAPI (API layer)
AsyncIO (task handling)
AI Layer
OpenRouter API (LLMs)
Tool calling system (function calling)
Voice
Sarvam AI (STT + TTS)
PyAudio / sounddevice
GUI
PyQt6 / PySide6 (recommended - PySide6 chosen specifically for LGPL licensing compliance)
Custom CSS styling
Automation
PyAutoGUI (basic control)
Playwright (browser automation)
Storage
SQLite (local DB)
Redis (optional for caching)
🧠 Architecture
User Input (Voice/Text)
        ↓
Input Handler
        ↓
AI Brain (OpenRouter)
        ↓
Tool Router (Function Calling)
        ↓
Execution Layer
   ├── OS Control
   ├── Browser Agent
   ├── File System
   └── Plugins
        ↓
Response Generator
        ↓
Voice + GUI Output
⚙️ Key Modules
1. AI Brain
Handles reasoning
Decides which tool to call
2. Tool System
Functions like:
open_app()
search_file()
browse_web()
3. Voice Engine
Continuous listening
Wake word detection
4. GUI Manager
Chat interface
Voice visualization
5. Memory System
Session memory
Long-term memory (SQLite)
🔄 User Flow
Voice Flow
User says “Kesari”
Assistant activates
User gives command
AI processes
Executes action
Responds via voice
Chat Flow
User types command
AI interprets
Executes tools
Returns response
🔐 Security & Safety
- **Action Permissions:** Ask permission before system-level actions. Autonomous workflows operate under a whitelist of pre-approved actions preserving autonomy, while falling back to prompt-or-abort for anything under the default-deny rules.
- **Sandboxed execution:** Plugins and code runners MUST run inside isolated Docker containers with user namespaces and seccomp profiles. Alternative allowed runtimes: bubblewrap/firejail for native Linux sandboxes or WebAssembly (WASI) runtimes for language-level isolation. Security controls require strict resource limits, network egress policies, and privilege dropping.
- **API Key Storage:** API keys stored locally using AES-256-GCM encryption with Argon2id parameters, integrated with OS keyrings (Windows Credential Manager / macOS Keychain), enforcing key rotation and no plaintext logging.
- **Audit Logging:** Audit logs generated for all OS Control and Browser Agent interactions. Stored in a dedicated SQLite db, retained for 90 days with archival rules. Logs are AES-256 encrypted at rest, using structured JSON format with size rotation policies and strict RBAC access controls.
- **Input Validation:** Strict sanitization and whitelisting of user commands and AI-generated actions.
- **Prompt Injection Defenses:** Input/output filtering, template hardening, and model response validation.
- **Rate Limiting:** Enforces per-user and per-action API call limits and throttling.
- **Data Privacy:** Explicit enumeration of collected user data, local storage retention, and encryption in transit/at-rest without sharing to external services.
- **Least Privilege:** The app must run with minimal OS permissions and require explicit elevation for sensitive actions.
- **Safety Principles:** Autonomous workflows require bounded retry limits and explicit loop-breaking detection.
🔧 Error Handling & Reliability
- **Network Errors:** Implements exponential backoff and concrete fallback strategies including cached responses (TTL/invalidation), fallback to alternative API endpoints (primary/failover providers), degraded functionality modes, and falling back to a local LLM model (e.g., Llama 3 8B) when external endpoints fail.
- **Execution Timeouts:** All async execution layers enforce strict timeouts to prevent deadlocks and blocking I/O scenarios.
- **Invalid AI responses:** Mitigated via response validation/parsing layer, strict schema checks, function-call sanitization and fallback.
- **Resource exhaustion:** Guarded with quotas, graceful degradation, cleanup (memory/disk limits, eviction), and rate-limiting.
- **Dependency failures:** Health checks, fallback drivers, install checks, and clearer error messages for missing system dependencies.
- **Partial failures:** Orchestration patterns with idempotent steps, compensating actions, per-tool retries, and transactional/rollback behavior.
🧪 Testing Strategy
- **Unit Tests:** Enforce unit coverage across tools, memory states, and mock AI responses.
- **Integration tests:** Validate AI → Tool Router → Execution Layer interactions and failure modes.
- **E2E tests:** Full voice/chat input to output user flows.
- **Security tests:** Explicit cases for path traversal, privilege escalation, API key leakage, and prompt injection.
- **Performance tests:** Response latency and memory/CPU metrics under load.
- **Test coverage targets:** Minimum 85% code coverage.
🚀 MVP Features (Phase 1)
Chat + Voice assistant
Open apps + basic system control
OpenRouter integration
Simple GUI
⚡ Phase 2
Browser agent
Task planner
Plugin system
🧠 Phase 3
Autonomous workflows (operates under a whitelist of pre-approved actions preserving autonomy while respecting default-deny system rules)
Multi-step reasoning
Memory + personalization