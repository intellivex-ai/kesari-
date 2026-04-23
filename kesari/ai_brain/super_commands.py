"""
Kesari AI — Super Commands
High-level macro routines for Life Automation.
"""
import logging
from PySide6.QtCore import QObject

logger = logging.getLogger(__name__)

class SuperCommands(QObject):
    def __init__(self, focus_system, command_router):
        super().__init__()
        self.focus_system = focus_system
        self.command_router = command_router

        # Map string commands to their routines
        self.routines = {
            "study mode": self.study_routine,
            "coding mode": self.coding_routine,
            "night routine": self.night_routine,
            "focus mode": self.basic_focus_routine
        }

    def execute_routine(self, routine_name: str) -> bool:
        """Executes a known routine if it exists."""
        routine = self.routines.get(routine_name.lower())
        if routine:
            routine()
            return True
        return False

    def study_routine(self):
        logger.info("Executing Super Command: Study Mode")
        # 1. Start Pomodoro
        self.focus_system.start_focus(mode="Study Mode", duration_mins=50)
        # 2. Open Notion or Notes (using command router)
        self.command_router.execute_command({"type": "smart", "action": "https://notion.so"})
        # 3. Open Spotify focus playlist
        self.command_router.execute_command({"type": "smart", "action": "https://open.spotify.com/playlist/37i9dQZF1DWZeKCadgRdKQ"})

    def coding_routine(self):
        logger.info("Executing Super Command: Coding Mode")
        # 1. Start focus block
        self.focus_system.start_focus(mode="Coding Mode", duration_mins=60, block_apps=["chrome.exe", "discord.exe"])
        # 2. Launch VS Code
        self.command_router.execute_command({"type": "direct", "action": "code"})
        # 3. Open Github
        self.command_router.execute_command({"type": "smart", "action": "https://github.com"})

    def night_routine(self):
        logger.info("Executing Super Command: Night Routine")
        # 1. Close apps (this could be done via powershell or psutil)
        import psutil
        safe_apps = ["explorer.exe", "svchost.exe", "python.exe", "kesari.exe"]
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name']
                if name and name.lower() not in safe_apps:
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
    def basic_focus_routine(self):
        self.focus_system.start_focus(mode="Deep Work", duration_mins=25)
