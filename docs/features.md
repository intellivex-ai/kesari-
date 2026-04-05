# Core + Advanced Feature Set

## 🧠 Core AI Capabilities
* **Chat-based assistant**
* **Voice assistant** (push-to-talk + wake word)
* **Context-aware responses (remembers session)**
  * **Data & Privacy:** Session data is retained locally in encrypted storage. Only message history up to a defined limit is retained. Users can view/clear history through the UI and request permanent deletion with a "forget me" action.
* **Multi-model support** (switch models via OpenRouter or local options)

## 🎤 Voice System (Sarvam AI)
* **Speech-to-text** (real-time streaming)
* **Text-to-speech** (natural Hindi + English)
* **Voice interruption** (stop speaking midway)
* **Audio Storage & Transmission:** Audio is streamed to Sarvam AI for processing; local raw audio is kept only in transient memory buffers and not persisted to disk.
* **Retention Policy:** No permanent storage of raw audio. Transcripts are retained locally in session history.
* **Consent & Wake Word:** “Kesari” wake word detection runs locally. Users must explicitly opt-in to always-on listening.
* **Service Unavailability / Fallback:** Degrades gracefully to local-only speech-to-text/offline transcription if cloud services are offline or disabled.

## 💻 System Control (VERY IMPORTANT)
This is what makes it powerful. All system tools implement strict permission checks and audit logging.

* **OS Control Boundaries & Permissions**
  * **Open/Close apps, File search, Folder navigation:** Features restricted by sandboxing and system-path access boundaries. Protected system paths (e.g., Windows/System32) are default-deny. Requires least-privilege tokens and logs all accesses.
* **Automation** (“Open YouTube”, “Create folder”)
* **System commands (shutdown, restart):** Requires explicit user confirmation for destructive operations, checks authorization levels, enforces rate limiting, and records tamper-resistant audit logs.
* **Clipboard manager:**
  * **Privacy:** Transient clipboard access only. History is not permanently stored or encrypted at rest since it's retained strictly in memory during runtime. Explicit user override/toggle available to restrict clipboard reading unless manually invoked.

## 🌐 Browser Agent
* **Open websites & Session Management:** Uses secure, HttpOnly, scoped storage for cookies, and enforces session expiration. HTTPS is strictly enforced.
* **Fill forms:** Stores credentials in an encrypted local secrets vault using AES-256 rather than insecure plaintext. Access is least-privilege.
* **Post on social media / Scrape content:** 
  * **Legal & Compliance:** Explicitly flags platforms' TOS and anti-spam rules. Must respect `robots.txt` and requires an admin opt-in with explicit action logs.

## 📊 Productivity Features
* **Task manager**, **Daily planner**, **Notes**, **Reminders**, **Focus mode**
* **Data Location & Protection:** All productivity data is stored in locally encrypted SQLite databases (AES-256 at rest).
* **Storage & Sync:** If cloud sync is enabled, data is transferred via TLS 1.2+ and stored in the user's chosen region. Explicit controls exist to disable sync, change regions, and export/delete data completely.

## 🧩 Plugin System (VERY IMPORTANT FOR SCALING)
Add tools dynamically. 
* **Plugin Security Model:** Strict capability-based permissions and least-privilege scopes. All plugins undergo code-execution sandboxing and static analysis.
* **Review & Verification:** Plugin submission requires vetting, code-signing, and verification.
* **API Surface:** Plugins are restricted to a whitelist of allowed API endpoints and forbidden actions.
* **Email sender**, **File organizer**
* **WhatsApp automation:** *Legal Note: Automation of WhatsApp may violate Meta's Terms of Service. Verify policy and rate limits before use.*
* **Code runner:** Requires (1) mandatory VM/container sandboxing, (2) pre-execution static analysis, (3) limits on CPU/Mem/Network, (4) explicit per-execution user consent, and (5) default-deny local API access (`enableCodeRunner` flag).

## 🖥️ GUI Features
* **Floating assistant** (like macOS spotlight)
* **Sidebar chat panel** & **Voice orb animation**
* **Command history**
* **Settings panel (API keys, voice, model)**
  * **Encryption and Storage:** Keys are encrypted at rest via native Key Management Service (KMS) or AES. 
  * **Secure Input:** UI uses masked password fields with no plaintext echo.
  * **Key Rotation & Revocation:** Provides clear workflows for rotating API keys and revoking compromised tokens locally.

## 🔐 Privacy Mode
Integrated throughout the application:
* **Local-only mode:** Flags to disable all external requests (OpenRouter/Sarvam) and enforce local-only execution.
* **No logging mode:** Transient execution where no telemetry or input logs are retained on disk.
* **Permission system:** Role-based definitions for what agentic tools can run autonomously vs. requiring explicit user confirmation.