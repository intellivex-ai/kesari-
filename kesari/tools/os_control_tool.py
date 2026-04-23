"""
Kesari AI - OS Control Tool
Provides autonomous agents with the ability to control the keyboard, mouse, and windows natively.
"""
import time
import subprocess
import logging
from typing import Optional, Any
from kesari.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class OSControlTool(BaseTool):
    """
    A tool that gives the AI native OS control capabilities (mouse, keyboard, window management).
    Requires explicit user approval for dangerous actions unless Auto Mode is enabled.
    """

    name = "os_control"
    description = "Control the OS natively: click, type text, press keys, open applications, and manage windows."
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["click", "type", "press", "open_app", "switch_window", "get_active_window"],
                "description": "The OS action to perform."
            },
            "x": {"type": "integer", "description": "X coordinate for click (optional)."},
            "y": {"type": "integer", "description": "Y coordinate for click (optional)."},
            "text": {"type": "string", "description": "Text to type or keys to press."},
            "app_path_or_name": {"type": "string", "description": "Path to executable or name of app to open."},
            "window_title": {"type": "string", "description": "Title of the window to switch to."}
        },
        "required": ["action"]
    }

    def __init__(self):
        super().__init__()
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.5
            self.has_pyautogui = True
        except ImportError:
            self.has_pyautogui = False
            logger.warning("pyautogui is not installed. OSControlTool will be limited.")

    async def execute(self, action: str, **kwargs) -> Any:
        try:
            if action == "click":
                return self._click(kwargs.get("x"), kwargs.get("y"))
            elif action == "type":
                return self._type(kwargs.get("text", ""))
            elif action == "press":
                return self._press(kwargs.get("text", ""))
            elif action == "open_app":
                return self._open_app(kwargs.get("app_path_or_name", ""))
            elif action == "switch_window":
                return self._switch_window(kwargs.get("window_title", ""))
            elif action == "get_active_window":
                return self._get_active_window()
            else:
                return f"Error: Unknown action '{action}'"
        except Exception as e:
            return f"OS Control Error: {str(e)}"

    def _click(self, x: Optional[int], y: Optional[int]) -> str:
        if not self.has_pyautogui: return "Error: pyautogui not installed."
        import pyautogui
        if x is not None and y is not None:
            pyautogui.click(x=x, y=y)
            return f"Clicked at ({x}, {y})"
        else:
            pyautogui.click()
            pos = pyautogui.position()
            return f"Clicked at current mouse position {pos}"

    def _type(self, text: str) -> str:
        if not self.has_pyautogui: return "Error: pyautogui not installed."
        import pyautogui
        pyautogui.write(text, interval=0.01)
        return f"Typed: {text}"

    def _press(self, key: str) -> str:
        if not self.has_pyautogui: return "Error: pyautogui not installed."
        import pyautogui
        keys = key.split('+')
        if len(keys) > 1:
            pyautogui.hotkey(*keys)
            return f"Pressed hotkey: {key}"
        else:
            pyautogui.press(key)
            return f"Pressed key: {key}"

    def _open_app(self, app_name: str) -> str:
        import platform
        sys_os = platform.system().lower()
        try:
            if sys_os == "windows":
                subprocess.Popen(["cmd", "/c", "start", "", app_name], shell=True)
            elif sys_os == "darwin":
                subprocess.Popen(["open", "-a", app_name])
            else:
                subprocess.Popen([app_name])
            return f"Successfully launched {app_name}"
        except Exception as e:
            return f"Failed to launch {app_name}: {e}"

    def _switch_window(self, window_title: str) -> str:
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(window_title)
            if not windows:
                return f"No window found with title containing '{window_title}'"
            win = windows[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            return f"Switched to window: {win.title}"
        except ImportError:
            return "Error: pygetwindow not installed."
        except Exception as e:
            return f"Failed to switch window: {e}"

    def _get_active_window(self) -> str:
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win:
                return f"Active window: {win.title}"
            return "No active window found."
        except ImportError:
            return "Error: pygetwindow not installed."
