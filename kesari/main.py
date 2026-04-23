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
from kesari.ai_brain.kesari_client import KesariClient
from kesari.ai_brain.tool_router import ToolRouter
from kesari.tools.registry import register_all_tools
from kesari.memory.vector_memory import VectorMemory
from kesari.voice_engine.wake_word import WakeWordDetector
from kesari.tools.plugin_loader import load_plugins, start_plugin_watcher
from kesari.ai_brain.workflow_engine import WorkflowEngine
from kesari.ai_brain.agent_orchestrator import AgentOrchestrator
from kesari.ai_brain.event_bus import EventBus
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
    agent_state_changed = Signal(str, str)
    voice_transcribed = Signal(str)
    tts_ready = Signal(bytes)
    
    # History Memory Signals
    history_loaded = Signal(list)
    all_history_loaded = Signal(list)
    conversation_loaded = Signal(int, list)
    tasks_loaded = Signal(list)

    # Web Intelligence Signals
    web_searching = Signal(str)         # mode string
    web_result_received = Signal(list, str)  # (sources, user_query)

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
        self.workflow_engine = WorkflowEngine(
            self.ai_client, 
            self.tool_router, 
            self.audit_logger,
            auto_mode_callback=lambda: getattr(self.window, "auto_mode_enabled", False)
        )
        # ── Multi-Agent Orchestrator ─────────────────────
        self.orchestrator = AgentOrchestrator(
            self.ai_client, self.tool_router, self.workflow_engine
        )
        self.event_bus = EventBus()
        self.event_bus.subscribe("proactive_suggestion", self._on_proactive_suggestion)
        self._api_server_thread = None

        # ── Async Worker (stays in main thread) ──────────
        self.worker = AsyncWorker(parent=self)
        self.worker.start()

        # ── Core Power Systems ───────────────────────────
        from kesari.ai_brain.command_router import CommandRouter
        from kesari.ai_brain.super_commands import SuperCommands
        from kesari.memory.focus_system import FocusSystem
        from kesari.ai_brain.proactive_engine import ProactiveEngine

        from kesari.automation.macro_recorder import MacroRecorder
        self.macro_recorder = MacroRecorder()
        self.command_router = CommandRouter(macro_recorder=self.macro_recorder)
        self.focus_system = FocusSystem()
        self.super_commands = SuperCommands(self.focus_system, self.command_router)
        self.proactive_engine = ProactiveEngine(self.focus_system)
        self.proactive_engine.proactive_suggestion.connect(self._on_proactive_suggestion)
        self.focus_system.alert.connect(self._on_error)

        # ── GUI ──────────────────────────────────────────
        self.window = MainWindow()
        from kesari.gui.command_palette import CommandPalette
        self.palette = CommandPalette()
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
        self.window.history_manager_requested.connect(self._on_history_manager)
        self.window.memory_timeline_requested.connect(self._on_memory_timeline)
        self.window.ai_os_mode_requested.connect(self._on_ai_os_mode)
        self.window.plugin_manager_requested.connect(self._on_plugin_manager)
        self.window.hidden_to_tray.connect(self._on_window_hidden)
        self.palette.command_submitted.connect(self._on_palette_command)
        self.palette.input_field.textChanged.connect(self._on_palette_text_changed)

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
        self.worker.agent_state_changed.connect(
            self._on_agent_state, Qt.QueuedConnection
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
        self.worker.all_history_loaded.connect(
            self._on_all_history_loaded, Qt.QueuedConnection
        )
        self.worker.conversation_loaded.connect(
            self._on_conversation_loaded, Qt.QueuedConnection
        )
        self.worker.tasks_loaded.connect(
            self._on_tasks_loaded, Qt.QueuedConnection
        )
        # ── Web Intelligence Signals ──────────────────────
        self.worker.web_searching.connect(
            self._on_web_searching, Qt.QueuedConnection
        )
        self.worker.web_result_received.connect(
            self._on_web_result, Qt.QueuedConnection
        )

        # ── Start Initialization ─────────────────────────
        self.worker.run(self._load_history())

        # ── Register global hotkey (Ctrl+Space) ──────────
        self._setup_hotkey()
        
        # ── Start Scheduler ──────────────────────────────
        self._scheduler_timer = QTimer(self)
        self._scheduler_timer.timeout.connect(self._run_schedule)
        self._scheduler_timer.start(5000)  # Check every 5s

        # ── Vision Monitor ───────────────────────────────
        from kesari.tools.vision_monitor import start_vision_monitor
        if settings.get("enable_vision_buffer", True):
            start_vision_monitor(interval=settings.get("vision_polling_interval", 10))

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

        # Removed API key check on startup since we are using custom model

        # Start companion API if enabled
        if settings.get("enable_companion_api", True):
            api_port = settings.get("companion_api_port", 8765)
            QTimer.singleShot(1500, lambda: self.start_api_server(port=api_port))

    def start_api_server(self, port: int = 8765):
        """Start the FastAPI companion server in a daemon background thread."""
        if self._api_server_thread and self._api_server_thread.is_alive():
            logger.info("Companion API server already running.")
            return

        try:
            import uvicorn
            from kesari.api.server import app as api_app, configure as api_configure

            # Inject live service references
            api_configure(
                orchestrator=self.orchestrator,
                ai_client=self.ai_client,
                user_profile=self.user_profile,
                system_monitor=self.system_monitor,
                long_term_memory=self.long_term_memory,
            )

            config = uvicorn.Config(
                api_app,
                host="0.0.0.0",
                port=port,
                log_level="warning",
                loop="asyncio",
            )
            server = uvicorn.Server(config)

            def _run():
                import asyncio as _asyncio
                loop = _asyncio.new_event_loop()
                _asyncio.set_event_loop(loop)
                loop.run_until_complete(server.serve())

            self._api_server_thread = threading.Thread(
                target=_run, daemon=True, name="kesari-api"
            )
            self._api_server_thread.start()
            logger.info(f"Companion API started on http://0.0.0.0:{port}")
            
            # Start Ngrok Tunnel if enabled
            if settings.get("enable_ngrok", False):
                try:
                    from pyngrok import ngrok
                    auth_token = settings.get("ngrok_auth_token", "")
                    if auth_token:
                        ngrok.set_auth_token(auth_token)
                    public_url = ngrok.connect(port).public_url
                    logger.info(f"Ngrok Secure Tunnel Active: {public_url}")
                    # Use QTimer to safely update GUI from thread if needed, though this might be main thread.
                    # Wait, start_api_server is called from main thread, so it's safe!
                    self.window.chat_widget.add_system_message(
                        f"🔒 Secure Remote Access Enabled: {public_url}"
                    )
                except Exception as ne:
                    logger.error(f"Failed to start Ngrok tunnel: {ne}", exc_info=True)
                    self.window.chat_widget.add_system_message(f"❌ Ngrok tunnel failed: {ne}")

        except Exception as e:
            logger.error(f"Failed to start companion API: {e}", exc_info=True)

    # ── Message Handling ─────────────────────────────────

    @Slot(str)
    def _on_palette_text_changed(self, text: str):
        """Update Command Palette suggestions."""
        if not text:
            self.palette.set_suggestions([])
            return
            
        suggestions = self.command_router.get_suggestions(text)
        self.palette.set_suggestions(suggestions)

    @Slot(str, dict)
    def _on_palette_command(self, text: str, context: dict):
        """Handle execution from the Command Palette."""
        if not text:
            return

        # 1. Super Commands
        if self.super_commands.execute_routine(text):
            return

        # 2. Command Router (Direct/Smart/AI)
        if context:
            handled, msg = self.command_router.execute_command(context)
            if handled:
                logger.info(f"Instant command executed: {msg}")
                # Optional: Show a brief HUD popup here
                return

        # 3. Fallback to AI Processing (Chat)
        # It's an AI task, we can show the main window to render the chat,
        # or handle it silently in the background. For now, show main window.
        self.window.showNormal()
        self.window.activateWindow()
        self._on_user_message(text)

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
        
        # Subtle haptic/sound
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass

        # Add to AI context
        self.ai_client.add_user_message(text)

        # Retrieve relevant RAG context and user profile
        memories = self.vector_memory.search(text, n_results=3)
        rag_context = "\n".join([m["content"] for m in memories]) if memories else ""
        profile_context = self.user_profile.get_context_string()
        
        # Inject Vision Context
        from kesari.tools.vision_monitor import get_vision_context
        vision_frame = get_vision_context()
        vision_info = "[System Note: Vision Context attached.]" if vision_frame else ""
        
        # Deep Context Awareness (OCR)
        ocr_text = ""
        lower_text = text.lower()
        if any(kw in lower_text for kw in ["summarize this", "read my screen", "what am i looking at", "ocr"]):
            from kesari.automation.screen_ocr import read_screen_text
            extracted = read_screen_text()
            if extracted:
                ocr_text = f"\n[System Note: OCR extracted from screen:]\n{extracted}\n"
                # Add a UI message so user knows it happened
                self.window.chat_widget.add_system_message("👁️ Kesari scanned your screen...")
        
        extra_context = f"{profile_context}\n\n{rag_context}\n\n{vision_info}{ocr_text}".strip()

        # Show thinking indicator
        self.window.chat_widget.show_thinking()
        self.window.voice_orb.set_state("processing")
        self.worker.agent_state_changed.emit("planning", "")

        # Stream AI response in background (via AgentOrchestrator)
        self.worker.run(self._save_message_async("user", text))
        self.worker.run(self._stream_response(text, extra_context))

    async def _stream_response(self, user_message: str, extra_context: str = ""):
        """Stream AI response via the AgentOrchestrator."""
        full_text = ""
        _web_sources: list = []
        _is_web_result = False
        try:
            async for event in self.orchestrator.run(
                user_message=user_message,
                extra_context=extra_context,
            ):
                if event["type"] == "token":
                    self.worker.token_received.emit(event["content"])
                    full_text += event["content"]

                elif event["type"] == "agent_selected":
                    self.worker.agent_state_changed.emit("planning", event["agent"])

                elif event["type"] == "web_searching":
                    mode = event.get("mode", "search")
                    self.worker.agent_state_changed.emit("searching", mode)
                    self.worker.web_searching.emit(mode)

                elif event["type"] == "web_result":
                    _is_web_result = True
                    _web_sources = event.get("sources", [])

                elif event["type"] == "tool_call":
                    self.worker.agent_state_changed.emit("executing", event["name"])
                    
                elif event["type"] == "tool_executing":
                    # Emit action step to the UI
                    step_label = event.get("step_label", f"Using {event.get('tool_name')}")
                    self.worker.tool_executing.emit(event.get("tool_name", "tool"), step_label)

                elif event["type"] == "tool_completed":
                    # Notify UI that step is complete
                    self.worker.agent_state_changed.emit("executing", f"{event.get('tool_name')} complete")
                    # We can use a special format for tool_executing to mean 'completed' or add a new signal.
                    # For simplicity, we'll emit a specific string if needed, or add a signal.
                    # Actually, let's just emit tool_executing with "COMPLETE" flag.
                    self.worker.tool_executing.emit(event.get("tool_name", "tool"), "COMPLETE")

                elif event["type"] == "approval_required":
                    logger.warning(f"MACRO: Action {event['tool_name']} requires implicit trust.")

                elif event["type"] == "done":
                    pass

                elif event["type"] == "error":
                    self.worker.error_occurred.emit(event["content"])
                    return

            # Emit web result data if this was a web query
            if _is_web_result:
                self.worker.web_result_received.emit(_web_sources, user_message)

            self.worker.response_done.emit(full_text)

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            self.worker.error_occurred.emit(str(e))

    @Slot(str)
    def _on_token(self, token: str):
        """Handle a streaming token — runs in main thread."""
        # Remove searching indicator on first token (web result starting to stream)
        self.window.chat_widget.remove_searching()
        if not self.window.chat_widget._current_ai_bubble:
            self.window.chat_widget.add_ai_message("")
        self.window.chat_widget.append_to_current_ai(token)


    @Slot(str)
    def _on_response_done(self, full_text: str):
        """Handle completion of AI response — runs in main thread."""
        self.window.chat_widget.finish_ai_message()
        self.worker.agent_state_changed.emit("done", "")
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
        
        # Context Chips Population (Idea 16)
        chips = []
        low_text = full_text.lower()
        if "error" in low_text or "failed" in low_text:
            chips = ["Retry", "Show logs"]
        elif "code" in low_text or "def " in low_text or "```" in low_text:
            chips = ["Explain code", "Refactor"]
        else:
            chips = ["Summarize", "Expand on this"]
        self.window.set_context_chips(chips)

        self.window.focus_input()
        self.window.voice_orb.set_state("idle")

        # Subtle complete sound
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

        # Auto TTS if voice was used
        if self.session_memory.get_metadata("voice_mode") and full_text.strip():
            self._speak_response(full_text)

    @Slot(str, str)
    def _on_agent_state(self, state: str, detail: str):
        """Update the agent state tracker — runs in main thread."""
        self.window.agent_state.update_state(state, detail)

    @Slot(str, str)
    def _on_tool_executing(self, tool_name: str, step_label_or_args: str):
        """Show tool execution in the chat — runs in main thread."""
        if step_label_or_args == "COMPLETE":
            self.window.chat_widget.complete_action_step()
        elif step_label_or_args.startswith("{"): # It's JSON args from standard tools
            self.window.chat_widget.add_system_message(f"🔧 Executing: {tool_name}...")
        else: # It's a step label from autonomous OS action
            self.window.chat_widget.show_action_step(step_label_or_args)

    @Slot(str)
    def _on_error(self, error: str):
        """Handle an error — runs in main thread."""
        self.window.chat_widget.finish_ai_message()
        self.window.chat_widget.remove_searching()
        self.window.chat_widget.add_system_message(f"❌ Error: {error}")
        self._is_processing = False
        self.window.set_input_enabled(True)
        self.window.voice_orb.set_state("idle")

    # ── Web Intelligence Slots ────────────────────────────

    @Slot(str)
    def _on_web_searching(self, mode: str):
        """Show the searching indicator during web queries — runs in main thread."""
        self.window.chat_widget.show_searching(mode)
        self.window.voice_orb.set_state("processing")

    @Slot(list, str)
    def _on_web_result(self, sources: list, user_query: str):
        """Called after a web result is fully streamed — shows sources panel and chips."""
        if sources:
            self.window.chat_widget.add_sources_panel(sources)
        self.window.chat_widget.add_refine_search_chip(user_query)


    # ── Wake Word ────────────────────────────────────────

    def _init_llm_client(self):
        """Initialize the custom trained Kesari client."""
        self.ai_client = KesariClient(model_path="kesari/dataset.txt")
        logger.info("Initialized lightweight KesariClient (Similarity Engine).")
            
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
        # 1. Try to route it instantly as a Voice Command
        suggestions = self.command_router.get_suggestions(text)
        if suggestions:
            # We take the best match (e.g., if you said 'chrome', it launches Chrome)
            best_match = suggestions[0]
            if best_match["type"] != "ai":
                self._on_palette_command(text, best_match)
                self.window.chat_widget.add_system_message(f"🎙️ Voice Command: {text}")
                return
                
        # 2. Fallback to normal AI processing
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

    @Slot()
    def _on_history_manager(self):
        """Request all history to open the history manager dialog."""
        self.worker.run(self._load_all_history_async())

    @Slot()
    def _on_memory_timeline(self):
        """Open the memory timeline dialog."""
        from kesari.gui.memory_timeline import MemoryTimelineDialog
        dialog = MemoryTimelineDialog(self.window, vector_memory=self.vector_memory)
        dialog.exec()

    @Slot(bool)
    def _on_ai_os_mode(self, enabled: bool):
        """Handle AI OS Mode toggle."""
        if enabled:
            self.window.chat_widget.add_system_message("🧠 AI OS Mode Enabled. Kesari will now proactively monitor and suggest actions.")
            if not self.system_monitor.is_alive():
                self.system_monitor = SystemMonitor(
                    on_alert=lambda metric, val, thr: QTimer.singleShot(
                        0, lambda m=metric, v=val, t=thr: self._on_resource_alert(m, v, t)
                    ),
                    interval=settings.get("monitoring_interval", 60),
                )
                self.system_monitor.start()
        else:
            self.window.chat_widget.add_system_message("🛑 AI OS Mode Disabled. Proactive monitoring paused.")
            if self.system_monitor.is_alive():
                self.system_monitor.stop()

    @Slot()
    def _on_plugin_manager(self):
        """Open the Plugin Manager dialog."""
        from kesari.gui.plugin_store import PluginManagerDialog
        dialog = PluginManagerDialog(self.window, tool_router=self.tool_router)
        dialog.exec()

    async def _load_all_history_async(self):
        """Fetch all conversations for the history manager."""
        await self.long_term_memory.initialize()
        conversations = await self.long_term_memory.list_conversations(limit=100) # Get up to 100
        self.worker.all_history_loaded.emit(conversations)

    @Slot(list)
    def _on_all_history_loaded(self, conversations: list):
        """Open the history manager dialog with the loaded conversations."""
        from kesari.gui.history_dialog import HistoryDialog
        dialog = HistoryDialog(self.window, conversations)
        dialog.delete_requested.connect(self._on_delete_history)
        dialog.exec()

    @Slot(int)
    def _on_delete_history(self, conversation_id: int):
        """Delete a conversation from SQLite."""
        self.worker.run(self._delete_history_async(conversation_id))
        
        # If the active conversation was deleted, clear the chat
        if self.active_conversation_id == conversation_id:
            self._on_new_chat()

    async def _delete_history_async(self, conversation_id: int):
        """Async deletion of history."""
        await self.long_term_memory.delete_conversation(conversation_id)
        # Refresh the sidebar
        conversations = await self.long_term_memory.list_conversations()
        self.worker.history_loaded.emit(conversations)

    def _on_resource_alert(self, metric: str, value: float, threshold: float):
        """Handle a proactive system resource alert — runs in main thread via QTimer.singleShot."""
        msg = f"High {metric} usage detected: {value:.1f}% (threshold {threshold:.0f}%). Consider closing unused apps."
        logger.warning(f"Resource alert: {msg}")
        self.event_bus.publish("proactive_suggestion", text=msg)

    def _on_proactive_suggestion(self, text: str):
        """Called when EventBus pushes a proactive suggestion."""
        # Ensure we run on main UI thread
        QTimer.singleShot(0, lambda: self._handle_proactive_suggestion_ui(text))

    def _handle_proactive_suggestion_ui(self, text: str):
        self.window.chat_widget.add_system_message(f"💡 Proactive Suggestion: {text}")
        tip_prompt = f"[Proactive Suggestion Context] {text}. Respond as a helpful OS companion with a brief, 1-2 sentence recommendation. Be concise."
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

        # Generate (or reuse) a self-signed TLS cert so the web page is served
        # over HTTPS — required for microphone / camera access on LAN devices.
        ssl_keyfile = None
        ssl_certfile = None
        try:
            from kesari.utils.ssl_cert import ensure_ssl_cert, _get_local_ips
            cert_path, key_path = ensure_ssl_cert()
            ssl_certfile = str(cert_path)
            ssl_keyfile  = str(key_path)
            protocol = "https"
        except Exception as ssl_err:
            logger.warning(f"Could not generate SSL cert, falling back to HTTP: {ssl_err}")
            protocol = "http"

        config = uvicorn.Config(
            api_app,
            host=host,
            port=port,
            log_level="warning",
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
        )
        server = uvicorn.Server(config)

        def _run():
            import asyncio
            asyncio.run(server.serve())

        self._api_server_thread = threading.Thread(target=_run, daemon=True, name="KesariAPI")
        self._api_server_thread.start()
        logger.info(f"Kesari Companion API started at {protocol}://{host}:{port}")

        # Build list of LAN addresses to show the user
        try:
            from kesari.utils.ssl_cert import _get_local_ips
            lan_ips = [ip for ip in _get_local_ips() if ip != "127.0.0.1"]
        except Exception:
            lan_ips = []

        lan_msg = ""
        if lan_ips:
            lan_urls = "  |  ".join(f"{protocol}://{ip}:{port}" for ip in lan_ips)
            lan_msg = f"\nLAN access:  {lan_urls}"
        if protocol == "https":
            lan_msg += "\n⚠️  First visit: accept the self-signed certificate in your browser."

        self.window.chat_widget.add_system_message(
            f"📱 Companion API ready at {protocol}://localhost:{port}{lan_msg}"
        )

        # Always start ngrok tunnel for public HTTPS access (mic works everywhere)
        tunnel_url = f"{protocol}://localhost:{port}"  # fallback if ngrok fails
        try:
            from pyngrok import ngrok as _ngrok, conf as _ngrok_conf
            from kesari.config import settings as _cfg
            auth_token = _cfg.get("ngrok_auth_token", "")
            if auth_token:
                # Write token directly to ngrok's config file to bypass stale cache
                _ngrok_conf.get_default().auth_token = auth_token
                _ngrok.set_auth_token(auth_token)
            _tunnel = _ngrok.connect(f"https://localhost:{port}", bind_tls=True)
            tunnel_url = _tunnel.public_url
            logger.info(f"Ngrok Secure Tunnel Active: {tunnel_url}")
            self.window.chat_widget.add_system_message(
                f"🌐 Public HTTPS URL (share this with any device):\n{tunnel_url}"
            )
            # Copy to clipboard for convenience
            try:
                import pyperclip
                pyperclip.copy(tunnel_url)
                self.window.chat_widget.add_system_message("📋 Tunnel URL copied to clipboard!")
            except Exception:
                pass
        except Exception as ne:
            logger.warning(f"Ngrok tunnel not available, using local URL: {ne}")



        # Auto-open the tunnel URL (or localhost fallback) in the default browser
        import threading as _t
        def _open_browser():
            import time, webbrowser
            time.sleep(2)
            webbrowser.open(tunnel_url)
        _t.Thread(target=_open_browser, daemon=True, name="OpenBrowser").start()

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
        """Toggle the Command Palette."""
        if self.palette.isVisible():
            self.palette.hide()
        else:
            self.palette.show()

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
