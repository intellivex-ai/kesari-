"""
Kesari AI — Context Awareness
Monitors active OS windows and user behavior.
"""
import logging
import pygetwindow as gw

logger = logging.getLogger(__name__)

class ContextAwareness:
    @staticmethod
    def get_active_window_title() -> str:
        """Returns the title of the currently focused window."""
        try:
            active_window = gw.getActiveWindow()
            if active_window:
                return active_window.title
        except Exception as e:
            logger.debug(f"Failed to get active window: {e}")
        return ""

    @staticmethod
    def get_active_app_name() -> str:
        """Heuristics to guess the app name from the window title."""
        title = ContextAwareness.get_active_window_title().lower()
        if not title:
            return ""
            
        if "google chrome" in title or "brave" in title or "edge" in title:
            return "browser"
        if "visual studio code" in title or "cursor" in title:
            return "code_editor"
        if "discord" in title:
            return "discord"
        if "youtube" in title:
            return "youtube"
            
        return "unknown"
