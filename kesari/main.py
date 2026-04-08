"""
Kesari AI — Application Entry Point
Wires together GUI, AI Brain, Voice Engine, Tools, and Memory.
"""
import sys
import asyncio
import logging
import threading
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal, QObject, Slot
from PySide6.QtWidgets import QApplication, QMessageBox

# ─── Logging Setup ────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("kesari")

# ─── Imports ──────────────────────────────────────────────
from kesari.config import settings, VECTOR_DB_DIR, DB_FILE
from kesari.gui.app import create_application
from kesari.gui.main_window import MainWindow
from kesari.gui.settings_dialog import SettingsDialog
from kesari.gui.floating_widget import FloatingWidget
from kesari.gui.tray_manager import TrayManager
from kesari.ai_brain.openrouter_client import OpenRouterClient
from kesari.ai_brain.ollama_client import OllamaClient
from kesari.ai_brain.tool_router import ToolRouter
from kesari.tools.registry import register_all_tools
from kesari.memory.vector_memory import VectorMemory
from kesari.voice_engine.wake_word import WakeWordDetector
from kesari.tools.plugin_loader import load_plugins, start_plugin_watcher
from kesari.ai_brain.workflow_engine import WorkflowEngine
from kesari.ai_brain.agent_orchestrator import AgentOrchestrator
from kesari.memory.audit_logger import AuditLogger
from kesari.memory.user_profile import UserProfileManager
from kesari.tools.profile_tools import UpdateProfileTool
from kesari.tools.system_monitor import SystemMonitor
from kesari.gui.analytics_widget import AnalyticsWidget
from kesari.voice_engine.audio_recorder import AudioRecorder
from kesari.voice_engine.audio_player import AudioPlayer
from kesari.memory.session_memory import SessionMemory
from kesari.memory.long_term_memory import LongTermMemory


class AsyncWorker(QObject):
    """
    Manages a background asyncio event loop.
    Stays in the MAIN thread — only the event loop runs in a bg thread.
    Signals emitted from coroutines are cross-thread; use QueuedConnection
    when connecting from the main thread.
    """

    token_received = Signal(str)
    response_done = Signal(str)
    tool_executing = Signal(str, str)   # tool_name, args
    error_occurred = Signal(str)
    voice_transcribed = Signal(str)
    tts_ready = Signal(bytes)
    
    # History Memory Signals
    history_loaded = Signal(list)
    conversation_loaded = Signal(int, list)
    tasks_loaded = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._loop_ready = threading.Event()

    def start(self):
        """Start the async event loop in a background daemon thread."""
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop_ready.set()
        self._loop.run_forever()

    def run(self, coro):
        """Schedule a coroutine on the background event loop."""
        if not self._loop_ready.wait(timeout=5.0):
            raise RuntimeError("Timed out waiting for asyncio loop to start.")
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        else:
            raise RuntimeError("Asyncio loop is not running.")

    def stop(self):
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2)


class KesariApp(QObject):
    """
    Main application controller that wires all components.
    Extends QObject so Qt can properly dispatch cross-thread signals
    to slots in the main GUI thread.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # ── Core Components ──────────────────────────────
        self.tool_router = ToolRouter()
        self.session_memory = SessionMemory()
        self.long_term_memory = LongTermMemory()
        self.vector_memory = VectorMemory(str(VECTOR_DB_DIR))
        self.user_profile = UserProfileManager()
        self.audio_recorder = AudioRecorder()
        self.audio_player = AudioPlayer()
        self.active_conversation_id: int | None = None
        
        self.ai_client = None
        self._init_llm_client()
        
        self._pending_tasks = []

        # ── Register Tools ───────────────────────────────
        register_all_tools(self.tool_router, self)
        # Register profile tool with access to user_profile
        self.tool_router.register(UpdateProfileTool(self.user_profile))
        load_plugins(self.tool_router)
        start_plugin_watcher(self.tool_router)
        logger.info(f"Tools available: {self.tool_router.list_tools()}")
        # ── Workflow Engine & Memory ─────────────────────
        self.audit_logger = AuditLogger(str(DB_FILE.parent / "audit.db"))
        self.workflow_engine = WorkflowEngine(self.ai_client, self.tool_router, self.audit_logger)
        # ── Multi-Agent Orchestrator ─────────────────────
        self.orchestrator = AgentOrchestrator(
            self.ai_client, self.tool_router, self.workflow_engine
        )
        self._api_server_thread = None

        # ── Async Worker (stays in main thread) ──────────
        self.worker = AsyncWorker(parent=self)
        self.worker.start()

        # ── GUI ──────────────────────────────────────────
        self.window = MainWindow()
        self.floating = FloatingWidget()
        self.tray = TrayManager()
        self._is_processing = False
        self._notified_tray = False

        self.wake_word_detector = None
        self._init_wake_word()

        # ── Connect GUI Signals (same thread — direct) ───
        self.window.user_message.connect(self._on_user_message)
        self.window.voice_toggle.connect(self._on_voice_toggle)
        self.window.new_chat_requested.connect(self._on_new_chat)
        self.window.settings_requested.connect(self._on_settings)
        self.window.analytics_requested.connect(self._on_analytics)
        self.window.hidden_to_tray.connect(self._on_window_hidden)
        self.floating.command_submitted.connect(self._on_user_message)

        # ── Connect Tray Signals ─────────────────────────
        self.tray.show_requested.connect(self._on_tray_show)
        self.tray.quit_requested.connect(self._on_tray_quit)

        # ── Connect Worker Signals (cross-thread — QUEUED) ──
        # QueuedConnection ensures slots ALWAYS run in the main GUI thread
        self.worker.token_received.connect(
            self._on_token, Qt.QueuedConnection
        )
        self.worker.response_done.connect(
            self._on_response_done, Qt.QueuedConnection
        )
        self.worker.tool_executing.connect(
            self._on_tool_executing, Qt.QueuedConnection
        )
        self.worker.error_occurred.connect(
            self._on_error, Qt.QueuedConnection
        )
        self.worker.voice_transcribed.connect(
            self._on_voice_transcribed, Qt.QueuedConnection
        )
        self.worker.tts_ready.connect(
            self._on_tts_ready, Qt.QueuedConnection
        )
        self.worker.history_loaded.connect(
            self._on_history_loaded, Qt.QueuedConnection
        )
        self.worker.conversation_loaded.connect(
            self._on_conversation_loaded, Qt.QueuedConnection
        )
        self.worker.tasks_loaded.connect(
            self._on_tasks_loaded, Qt.QueuedConnection
        )

        # ── Start Initialization ─────────────────────────
        self.worker.run(self._load_history())

        # ── Register global hotkey (Ctrl+Space) ──────────
        self._setup_hotkey()
        
        # ── Start Scheduler ──────────────────────────────
        self._scheduler_timer = QTimer(self)
        self._scheduler_timer.timeout.connect(self._run_schedule)
        self._scheduler_timer.start(5000)  # Check every 5s

        # ── System Monitor ───────────────────────────────
        self.system_monitor = SystemMonitor(
            on_alert=lambda metric, val, thr: QTimer.singleShot(
                0, lambda m=metric, v=val, t=thr: self._on_resource_alert(m, v, t)
            ),
            interval=settings.get("monitoring_interval", 60),
        )
        if settings.get("enable_proactive_monitoring", True):
            self.system_monitor.start()

    def show(self):
        """Show the main window."""
        self.window.show()
        self.window.focus_input()

        # Check API key on startup
        if not settings.get("openrouter_api_key"):
            QTimer.singleShot(500, self._prompt_api_key)

        # Start companion API if enabled
        if settings.get("enable_companion_api", False):
            api_port = settings.get("companion_api_port", 8765)
            QTimer.singleShot(1000, lambda: self.start_api_server(port=api_port))

    # ── Message Handling ─────────────────────────────────

    @Slot(str)
    def _on_user_message(self, text: str):
        """Handle user text input."""
        if self._is_processing:
            return

        self._is_processing = True
        self.window.set_input_enabled(False)

        # Add to UI
        self.window.chat_widget.add_user_message(text)
        self.session_memory.add_message("user", text)

        # Add to AI context
        self.ai_client.add_user_message(text)

        # Retrieve relevant RAG context and user profile
        memories = self.vector_memory.search(text, n_results=3)
        rag_context = "\n".join([m["content"] for m in memories]) if memories else ""
        profile_context = self.user_profile.get_context_string()
        extra_context = f"{profile_context}\n\n{rag_context}".strip()

        # Create AI bubble for streaming
        self.window.chat_widget.add_ai_message("")
        self.window.voice_orb.set_state("processing")

        # Stream AI response in background (via AgentOrchestrator)
        self.worker.run(self._save_message_async("user", text))
        self.worker.run(self._stream_response(text, extra_context))

    async def _stream_response(self, user_message: str, extra_context: str = ""):
        """Stream AI response via the AgentOrchestrator."""
        full_text = ""
        try:
            async for event in self.orchestrator.run(
                user_message=user_message,
                extra_context=extra_context,
            ):
                if event["type"] == "token":
                    self.worker.token_received.emit(event["content"])
                    full_text += event["content"]

                elif event["type"] == "agent_selected":
                    # Show which agent is active as a subtle system note
                    self.worker.tool_executing.emit(
                        event["agent"], f'agent={event["key"]}'
                    )

                elif event["type"] == "tool_call":
                    self.worker.tool_executing.emit(event["name"], event.get("arguments", "{}"))

                elif event["type"] == "approval_required":
                    logger.warning(f"MACRO: Action {event['tool_name']} requires implicit trust.")

                elif event["type"] == "done":
                    pass

                elif event["type"] == "error":
                    self.worker.error_occurred.emit(event["content"])
                    return

            self.worker.response_done.emit(full_text)

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            self.worker.error_occurred.emit(str(e))

    @Slot(str)
    def _on_token(self, token: str):
        """Handle a streaming token — runs in main thread."""
        self.window.chat_widget.append_to_current_ai(token)

    @Slot(str)
    def _on_response_done(self, full_text: str):
        """Handle completion of AI response — runs in main thread."""
        self.window.chat_widget.finish_ai_message()
        self.session_memory.add_message("assistant", full_text)
        self.worker.run(self._save_message_async("assistant", full_text))
        
        # Save to vector memory so Kesari remembers what user said and what it replied
        user_msg = self.session_memory.get_messages()[-2]["content"] if self.session_memory.message_count >= 2 else ""
        if user_msg:
            memory_text = f"User: {user_msg}\nKesari: {full_text}"
            import uuid
            self.vector_memory.add_memory(str(uuid.uuid4()), memory_text)
            
        self._is_processing = False
        self.window.set_input_enabled(True)
        self.window.focus_input()
        self.window.voice_orb.set_state("idle")

        # Auto TTS if voice was used
        if self.session_memory.get_metadata("voice_mode") and full_text.strip():
            self._speak_response(full_text)

    @Slot(str, str)
    def _on_tool_executing(self, tool_name: str, args: str):
        """Show tool execution in the chat — runs in main thread."""
        self.window.chat_widget.add_system_message(
            f"🔧 Executing: {tool_name}..."
        )

    @Slot(str)
    def _on_error(self, error: str):
        """Handle an error — runs in main thread."""
        self.window.chat_widget.finish_ai_message()
        self.window.chat_widget.add_system_message(f"❌ Error: {error}")
        self._is_processing = False
        self.window.set_input_enabled(True)
        self.window.voice_orb.set_state("idle")

    # ── Wake Word ────────────────────────────────────────

    def _init_llm_client(self):
        """Initialize appropriate LLM client based on settings."""
        provider = settings.get("llm_provider", "auto")
        
        if provider == "ollama":
            model = settings.get("ollama_model", "llama3:8b")
            self.ai_client = OllamaClient(model=model)
            logger.info(f"Initialized OllamaClient with model {model}")
        else:
            self.ai_client = OpenRouterClient()
            logger.info("Initialized OpenRouterClient")
            
        # If we already have a workflow engine, update its client reference
        if hasattr(self, 'workflow_engine'):
            self.workflow_engine.ai_client = self.ai_client

    def _init_wake_word(self):
        if settings.get("wake_word_enabled", False):
            if not self.wake_word_detector:
                self.wake_word_detector = WakeWordDetector(
                    wake_word=settings.get("wake_word_model", "hey_jarvis"),
                    callback=self._on_wake_word_detected
                )
            self.wake_word_detector.start()
        else:
            if self.wake_word_detector:
                self.wake_word_detector.stop()

    def _on_wake_word_detected(self):
        QTimer.singleShot(0, self._handle_wake_word_ui)

    def _handle_wake_word_ui(self):
        if self._is_processing or self.audio_recorder.is_recording:
            return
            
        self.window.showNormal()
        self.window.activateWindow()
        
        self._on_voice_toggle(True)
        
        # Start VAD checking timer
        self._silence_ticks = 0
        if not hasattr(self, '_vad_timer'):
            self._vad_timer = QTimer(self.window)
            self._vad_timer.timeout.connect(self._check_vad)
        self._vad_timer.start(500)
        
    def _check_vad(self):
        if not self.audio_recorder.is_recording:
            self._vad_timer.stop()
            return
            
        if self.audio_recorder.audio_level < 0.05:
            self._silence_ticks += 1
        else:
            self._silence_ticks = 0
            
        # 2 seconds of silence = stop recording
        if self._silence_ticks >= 4:
            self._vad_timer.stop()
            self._on_voice_toggle(False)

    # ── Voice Handling ───────────────────────────────────

    @Slot(bool)
    def _on_voice_toggle(self, pressed: bool):
        """Handle push-to-talk button."""
        if pressed:
            # Stop wake word listener temporarily so audio block isn't held
            if self.wake_word_detector:
                self.wake_word_detector.stop()
                
            # Start recording
            try:
                self.audio_recorder.start()
                self.window.voice_orb.set_state("listening")
                self.session_memory.set_metadata("voice_mode", True)
                # Update audio level for orb
                if hasattr(self, '_audio_level_timer'):
                    self._audio_level_timer.stop()
                    self._audio_level_timer.deleteLater()
                self._audio_level_timer = QTimer(self)
                self._audio_level_timer.timeout.connect(self._update_audio_level)
                self._audio_level_timer.start(50)
            except Exception as e:
                self._on_error(f"Microphone error: {e}")
        else:
            # Stop recording and transcribe
            if hasattr(self, '_audio_level_timer'):
                self._audio_level_timer.stop()
                self._audio_level_timer.deleteLater()
            if self.audio_recorder.is_recording:
                wav_bytes = self.audio_recorder.stop()
                if wav_bytes:
                    self.window.voice_orb.set_state("processing")
                    self.worker.run(self._transcribe_audio(wav_bytes))
                else:
                    self.window.voice_orb.set_state("idle")

    def _update_audio_level(self):
        """Update voice orb with current audio level."""
        if self.audio_recorder.is_recording:
            self.window.voice_orb.set_audio_level(self.audio_recorder.audio_level)

    async def _transcribe_audio(self, wav_bytes: bytes):
        """Transcribe audio and emit the result."""
        try:
            from kesari.voice_engine.sarvam_stt import SarvamSTT
            stt = SarvamSTT(
                api_key=settings.get("sarvam_api_key", ""),
                language=settings.get("stt_language", "hi-IN"),
            )
            text = await stt.transcribe(wav_bytes)
            if text.strip():
                self.worker.voice_transcribed.emit(text.strip())
            else:
                self.worker.error_occurred.emit("Could not transcribe audio. Try speaking louder.")
        except Exception as e:
            self.worker.error_occurred.emit(f"STT error: {e}")

    @Slot(str)
    def _on_voice_transcribed(self, text: str):
        """Handle transcribed voice input — runs in main thread."""
        self._on_user_message(text)

    def _speak_response(self, text: str):
        """Convert AI response to speech and play it."""
        self.window.voice_orb.set_state("speaking")
        self.worker.run(self._synthesize_speech(text))

    async def _synthesize_speech(self, text: str):
        """Synthesize speech from text."""
        try:
            from kesari.voice_engine.sarvam_tts import SarvamTTS
            tts = SarvamTTS(
                api_key=settings.get("sarvam_api_key", ""),
                language=settings.get("tts_language", "hi-IN"),
                speaker=settings.get("tts_speaker", "meera"),
            )
            # Truncate for TTS (API limits)
            if len(text) > 500:
                logger.warning("TTS text truncated to 500 chars due to API limit")
            short_text = text[:500]
            audio_bytes = await tts.synthesize(short_text)
            if audio_bytes:
                self.worker.tts_ready.emit(audio_bytes)
        except Exception as e:
            logger.error(f"TTS error: {e}")
            self.worker.error_occurred.emit(f"TTS error: {e}")

    @Slot(bytes)
    def _on_tts_ready(self, audio_bytes: bytes):
        """Play synthesized speech — runs in main thread."""
        def on_finished():
            QTimer.singleShot(0, lambda: self.window.voice_orb.set_state("idle"))
        self.audio_player.play_wav_bytes(
            audio_bytes,
            on_finished=on_finished,
        )

    # ── New Chat ─────────────────────────────────────────

    @Slot()
    def _on_new_chat(self):
        """Start a new conversation."""
        if self._is_processing:
            return
            
        self.active_conversation_id = None
        self.window.chat_widget.clear_chat()
        self.ai_client.clear_conversation()
        self.session_memory.clear()
        self._is_processing = False
        self.window.set_input_enabled(True)
        self.window.focus_input()
        self.window.voice_orb.set_state("idle")

    # ── Settings ─────────────────────────────────────────

    @Slot()
    def _on_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self.window)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()

    @Slot()
    def _on_analytics(self):
        """Open the analytics dashboard dialog."""
        dialog = AnalyticsWidget(
            parent=self.window,
            system_monitor=getattr(self, "system_monitor", None)
        )
        dialog.exec()

    def _on_resource_alert(self, metric: str, value: float, threshold: float):
        """Handle a proactive system resource alert — runs in main thread via QTimer.singleShot."""
        msg = f"⚠️ High {metric} usage detected: {value:.1f}% (threshold {threshold:.0f}%). Consider closing unused apps."
        logger.warning(f"Resource alert: {msg}")
        self.window.chat_widget.add_system_message(msg)
        tip_prompt = f"[System Alert] {metric} usage is at {value:.1f}%. Give a brief helpful tip in 1-2 sentences."
        self.ai_client.add_user_message(tip_prompt)
        self.window.chat_widget.add_ai_message("")
        self.worker.run(self._stream_response(tip_prompt))

    # ── Mobile Companion API ──────────────────────────────────

    def start_api_server(self, host: str = "0.0.0.0", port: int = 8765):
        """Start the FastAPI companion server in a background daemon thread."""
        import threading
        import uvicorn
        from kesari.api.server import app as api_app, configure as api_configure

        api_configure(
            orchestrator=self.orchestrator,
            ai_client=self.ai_client,
            user_profile=getattr(self, "user_profile", None),
            system_monitor=getattr(self, "system_monitor", None),
            long_term_memory=self.long_term_memory,
        )

        config = uvicorn.Config(api_app, host=host, port=port, log_level="warning")
        server = uvicorn.Server(config)

        def _run():
            import asyncio
            asyncio.run(server.serve())

        self._api_server_thread = threading.Thread(target=_run, daemon=True, name="KesariAPI")
        self._api_server_thread.start()
        logger.info(f"Kesari Companion API started at http://{host}:{port}")
        self.window.chat_widget.add_system_message(
            f"📱 Companion API at http://localhost:{port} — open on any device on your network."
        )

    def stop_api_server(self):
        """Companion API server runs as daemon — it exits automatically with the app."""
        self._api_server_thread = None

    # ── History Memory Async Handlers ────────────────────


    async def _load_history(self):
        await self.long_term_memory.initialize()
        conversations = await self.long_term_memory.list_conversations()
        self.worker.history_loaded.emit(conversations)
        
        tasks = await self.long_term_memory.list_pending_tasks()
        self.worker.tasks_loaded.emit(tasks)

    @Slot(list)
    def _on_tasks_loaded(self, tasks: list):
        now = datetime.now()
        for t in tasks:
            try:
                dt = datetime.fromisoformat(t['trigger_time'])
                if dt <= now:
                    # Trigger immediately
                    self._trigger_reminder(t['id'], t['task_name'])
                else:
                    self._schedule_task_in_memory(t['id'], t['task_name'], dt)
            except Exception as e:
                logger.error(f"Failed to parse task time {t['trigger_time']}: {e}")

    @Slot(list)
    def _on_history_loaded(self, conversations: list):
        self.window.clear_history()
        for idx, conv in enumerate(conversations):
            if idx >= 15:
                break
            conv_id = conv["id"]
            title = conv["title"]
            
            # Create closure for button click
            def make_handler(cid):
                return lambda: self._on_history_item_clicked(cid)
                
            self.window.add_history_item(title, on_click=make_handler(conv_id))

    def _on_history_item_clicked(self, conversation_id: int):
        if self._is_processing:
            return
        self.worker.run(self._load_conversation_async(conversation_id))

    async def _load_conversation_async(self, conversation_id: int):
        messages = await self.long_term_memory.get_messages(conversation_id)
        self.worker.conversation_loaded.emit(conversation_id, messages)

    @Slot(int, list)
    def _on_conversation_loaded(self, conversation_id: int, messages: list):
        self.active_conversation_id = conversation_id
        self.session_memory.clear()
        self.ai_client.clear_conversation()
        self.window.chat_widget.clear_chat()
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            self.session_memory.add_message(role, content)
            
            if role == "user":
                self.window.chat_widget.add_user_message(content)
                self.ai_client.add_user_message(content)
            elif role == "assistant":
                self.window.chat_widget.add_ai_message("")
                self.window.chat_widget.append_to_current_ai(content)
                self.window.chat_widget.finish_ai_message()
                self.ai_client.add_assistant_message(content)
        
        self.window.chat_widget.add_system_message(f"Loaded historic chat.")

    async def _save_message_async(self, role: str, content: str):
        if self.active_conversation_id is None:
            # Create new conversation first
            title = content[:30] + ("..." if len(content) > 30 else "") if role == "user" else "New Chat"
            self.active_conversation_id = await self.long_term_memory.create_conversation(title)
            # Fetch latest to update sidebar
            conversations = await self.long_term_memory.list_conversations()
            self.worker.history_loaded.emit(conversations)

        await self.long_term_memory.save_message(
            self.active_conversation_id, role, content
        )

    # ── Scheduling Handlers ──────────────────────────────

    def _schedule_task_in_memory(self, task_id: int, task_name: str, trigger_dt: datetime):
        """Add a pending task to the volatile memory list so the QTimer checks it."""
        self._pending_tasks.append({
            'id': task_id,
            'name': task_name,
            'dt': trigger_dt
        })
        logger.info(f"Task scheduled in memory: {task_name} at {trigger_dt}")
        
    def _run_schedule(self):
        """Checks pending tasks queue every tick."""
        if not self._pending_tasks:
            return
            
        now = datetime.now()
        to_trigger = []
        for task in self._pending_tasks:
            if now >= task['dt']:
                to_trigger.append(task)
                
        for task in to_trigger:
            self._trigger_reminder(task['id'], task['name'])
            try:
                self._pending_tasks.remove(task)
            except ValueError:
                pass
                
    def _trigger_reminder(self, task_id: int, task_name: str):
        """Execution of a task when its time arrives."""
        logger.info(f"Triggering reminder: {task_name}")
        self._speak_response(f"Reminder: {task_name}")
        self.window.chat_widget.add_system_message(f"🔔 Reminder: {task_name}")
        # Bring window to front
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()
        
        # Mark as completed in DB
        self.worker.run(self.long_term_memory.mark_task_completed(task_id))

    def _on_settings_saved(self):
        """Reload config after settings change."""
        self._init_llm_client()
        self._init_wake_word()
        self.session_memory.clear()
        self.window.chat_widget.clear_chat()
        logger.info("Settings saved and applied")

    def _prompt_api_key(self):
        """Prompt user to set API key."""
        self.window.chat_widget.add_system_message(
            "👋 Welcome! Please configure your API keys in Settings (⚙) to get started."
        )

    # ── Global Hotkey ────────────────────────────────────

    def _setup_hotkey(self):
        """Set up Ctrl+Space global hotkey for floating widget."""
        try:
            from pynput import keyboard

            def on_activate():
                # Must be called from Qt thread
                QTimer.singleShot(0, self._toggle_floating)

            hotkey = keyboard.GlobalHotKeys({
                '<ctrl>+<space>': on_activate,
            })
            hotkey.daemon = True
            hotkey.start()
            logger.info("Global hotkey Ctrl+Space registered")
        except Exception as e:
            logger.warning(f"Could not register global hotkey: {e}")

    def _toggle_floating(self):
        """Toggle the floating widget."""
        if self.floating.isVisible():
            self.floating.hide_animated()
        else:
            self.floating.show_centered()

    # ── Tray Handling ────────────────────────────────────

    @Slot()
    def _on_tray_show(self):
        """Restore main window from system tray."""
        self.window.showNormal()
        self.window.activateWindow()
        self.window.focus_input()

    @Slot()
    def _on_window_hidden(self):
        """Notify user on first hide."""
        if not self._notified_tray and getattr(self.tray, "tray_icon", None):
            self.tray.show_message(
                "Kesari AI",
                "Kesari AI is running in the background.\nDouble-click the tray icon to restore."
            )
            self._notified_tray = True

    @Slot()
    def _on_tray_quit(self):
        """Quit the application completely."""
        self.cleanup()
        QApplication.quit()

    # ── Cleanup ──────────────────────────────────────────

    def cleanup(self):
        """Clean up resources."""
        self.worker.stop()
        if self.audio_recorder.is_recording:
            self.audio_recorder.stop()
        self.audio_player.stop()
        if hasattr(self, "system_monitor"):
            self.system_monitor.stop()


def main():
    """Application entry point."""
    app = create_application(sys.argv)

    kesari = KesariApp()
    kesari.show()

    # Cleanup on exit
    app.aboutToQuit.connect(kesari.cleanup)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
