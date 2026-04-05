"""
Kesari AI — Application Entry Point
Wires together GUI, AI Brain, Voice Engine, Tools, and Memory.
"""
import sys
import asyncio
import logging
import threading

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
from kesari.config import settings
from kesari.gui.app import create_application
from kesari.gui.main_window import MainWindow
from kesari.gui.settings_dialog import SettingsDialog
from kesari.gui.floating_widget import FloatingWidget
from kesari.ai_brain.openrouter_client import OpenRouterClient
from kesari.ai_brain.tool_router import ToolRouter
from kesari.tools.registry import register_all_tools
from kesari.tools.plugin_loader import load_plugins
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def start(self):
        """Start the async event loop in a background daemon thread."""
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro):
        """Schedule a coroutine on the background event loop."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self._loop)

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
        self.ai_client = OpenRouterClient()
        self.tool_router = ToolRouter()
        self.session_memory = SessionMemory()
        self.long_term_memory = LongTermMemory()
        self.audio_recorder = AudioRecorder()
        self.audio_player = AudioPlayer()

        # ── Register Tools ───────────────────────────────
        register_all_tools(self.tool_router)
        load_plugins(self.tool_router)
        logger.info(f"Tools available: {self.tool_router.list_tools()}")

        # ── Async Worker (stays in main thread) ──────────
        self.worker = AsyncWorker(parent=self)
        self.worker.start()

        # ── GUI ──────────────────────────────────────────
        self.window = MainWindow()
        self.floating = FloatingWidget()
        self._is_processing = False

        # ── Connect GUI Signals (same thread — direct) ───
        self.window.user_message.connect(self._on_user_message)
        self.window.voice_toggle.connect(self._on_voice_toggle)
        self.window.new_chat_requested.connect(self._on_new_chat)
        self.window.settings_requested.connect(self._on_settings)
        self.floating.command_submitted.connect(self._on_user_message)

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

        # ── Register global hotkey (Ctrl+Space) ──────────
        self._setup_hotkey()

    def show(self):
        """Show the main window."""
        self.window.show()
        self.window.focus_input()

        # Check API key on startup
        if not settings.get("openrouter_api_key"):
            QTimer.singleShot(500, self._prompt_api_key)

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

        # Create AI bubble for streaming
        self.window.chat_widget.add_ai_message("")
        self.window.voice_orb.set_state("processing")

        # Stream AI response in background
        self.worker.run(self._stream_response())

    async def _stream_response(self):
        """Stream AI response with tool calling support."""
        tools = self.tool_router.get_definitions()
        full_text = ""

        try:
            async for event in self.ai_client.stream_chat(tools=tools if tools else None):
                if event["type"] == "token":
                    self.worker.token_received.emit(event["content"])
                    full_text += event["content"]

                elif event["type"] == "tool_call":
                    tool_name = event["name"]
                    tool_args = event["arguments"]
                    self.worker.tool_executing.emit(tool_name, tool_args)

                    # Execute the tool
                    result = await self.tool_router.execute(tool_name, tool_args)

                    # Log tool usage
                    try:
                        import json
                        await self.long_term_memory.log_tool_usage(
                            tool_name,
                            json.loads(tool_args) if tool_args else {},
                            result,
                        )
                    except Exception:
                        pass

                    # Send result back to LLM
                    self.ai_client.add_tool_result(
                        event["id"], tool_name, result
                    )

                    # Continue conversation with tool results
                    async for follow_event in self.ai_client.complete_after_tools(
                        tools=tools if tools else None
                    ):
                        if follow_event["type"] == "token":
                            self.worker.token_received.emit(follow_event["content"])
                            full_text += follow_event["content"]
                        elif follow_event["type"] == "done":
                            break
                        elif follow_event["type"] == "error":
                            self.worker.error_occurred.emit(follow_event["content"])
                            return
                        elif follow_event["type"] == "tool_call":
                            # Handle chained tool calls
                            t_name = follow_event["name"]
                            t_args = follow_event["arguments"]
                            self.worker.tool_executing.emit(t_name, t_args)
                            t_result = await self.tool_router.execute(t_name, t_args)
                            self.ai_client.add_tool_result(
                                follow_event["id"], t_name, t_result
                            )
                            # One more follow-up
                            async for final_event in self.ai_client.complete_after_tools():
                                if final_event["type"] == "token":
                                    self.worker.token_received.emit(final_event["content"])
                                    full_text += final_event["content"]
                                elif final_event["type"] == "done":
                                    break

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
        self._is_processing = False
        self.window.set_input_enabled(True)
        self.window.focus_input()
        self.window.voice_orb.set_state("idle")

        # Update sidebar with chat title
        if self.session_memory.message_count == 2:  # First exchange
            title = self.session_memory.get_title()
            self.window.add_history_item(title)

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

    # ── Voice Handling ───────────────────────────────────

    @Slot(bool)
    def _on_voice_toggle(self, pressed: bool):
        """Handle push-to-talk button."""
        if pressed:
            # Start recording
            try:
                self.audio_recorder.start()
                self.window.voice_orb.set_state("listening")
                self.session_memory.set_metadata("voice_mode", True)
                # Update audio level for orb
                self._audio_level_timer = QTimer(self)
                self._audio_level_timer.timeout.connect(self._update_audio_level)
                self._audio_level_timer.start(50)
            except Exception as e:
                self._on_error(f"Microphone error: {e}")
        else:
            # Stop recording and transcribe
            if hasattr(self, '_audio_level_timer'):
                self._audio_level_timer.stop()
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

    def _on_settings_saved(self):
        """Reload config after settings change."""
        # Recreate AI client with new key/model
        self.ai_client = OpenRouterClient()
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

    # ── Cleanup ──────────────────────────────────────────

    def cleanup(self):
        """Clean up resources."""
        self.worker.stop()
        if self.audio_recorder.is_recording:
            self.audio_recorder.stop()
        self.audio_player.stop()


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
