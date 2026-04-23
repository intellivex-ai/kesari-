"""
Kesari AI — Focus & Time System
Enforces productivity by tracking time and blocking distractions.
"""
import logging
import psutil
from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger(__name__)

class FocusSystem(QObject):
    focus_started = Signal(str, int)  # mode, duration_mins
    focus_ended = Signal(str)         # mode
    alert = Signal(str)               # alert message

    def __init__(self):
        super().__init__()
        self.is_focused = False
        self.current_mode = None
        self.blocked_apps = []

        # Background checker
        self.enforcer_timer = QTimer(self)
        self.enforcer_timer.timeout.connect(self._enforce_focus)

        # Session timer
        self.session_timer = QTimer(self)
        self.session_timer.setSingleShot(True)
        self.session_timer.timeout.connect(self.end_focus)

    def start_focus(self, mode: str = "Deep Work", duration_mins: int = 25, block_apps: list = None):
        """Starts a focus session."""
        self.is_focused = True
        self.current_mode = mode
        self.blocked_apps = block_apps or ["chrome.exe", "msedge.exe", "discord.exe", "slack.exe"]

        # 5 seconds polling
        self.enforcer_timer.start(5000)
        
        # Session end
        self.session_timer.start(duration_mins * 60 * 1000)

        self.focus_started.emit(self.current_mode, duration_mins)
        logger.info(f"Started focus mode: {mode} for {duration_mins} mins.")

    def end_focus(self):
        """Ends the current focus session."""
        if not self.is_focused:
            return
            
        self.is_focused = False
        self.current_mode = None
        self.enforcer_timer.stop()
        self.session_timer.stop()
        
        self.focus_ended.emit(self.current_mode)
        logger.info("Focus session ended.")

    def _enforce_focus(self):
        """Kills any blocked apps that try to open during focus mode."""
        if not self.is_focused:
            return

        killed_any = False
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name']
                if name and name.lower() in self.blocked_apps:
                    proc.kill()
                    killed_any = True
                    logger.info(f"Blocked distracted app: {name}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        if killed_any:
            self.alert.emit("Stay focused! Distraction blocked.")
