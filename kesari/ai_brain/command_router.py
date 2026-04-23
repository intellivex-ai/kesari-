"""
Kesari AI — Command Router
Instantly classifies commands as Direct (app launches), Smart (parametric), or AI (LLM routed).
"""
import logging
import os
import subprocess
import webbrowser
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class CommandRouter:
    def __init__(self, macro_recorder=None):
        self.macro_recorder = macro_recorder
        # Direct commands: Exact string match to executable or path
        self.direct_commands: Dict[str, str] = {
            "chrome": "chrome",
            "code": "code",
            "downloads": os.path.expanduser("~/Downloads"),
            "documents": os.path.expanduser("~/Documents"),
            "settings": "ms-settings:",
            "notepad": "notepad",
            "calc": "calc",
            "explorer": "explorer",
        }

        # Smart commands: Starts with key -> format url
        self.smart_commands: Dict[str, str] = {
            "yt ": "https://www.youtube.com/results?search_query={}",
            "google ": "https://www.google.com/search?q={}",
            "gpt ": "https://chatgpt.com/?q={}",
            "gh ": "https://github.com/search?q={}",
            "maps ": "https://www.google.com/maps/search/{}",
        }

    def get_suggestions(self, query: str) -> list[dict]:
        """Return instantaneous suggestions for the Command Palette."""
        query = query.strip().lower()
        if not query:
            return []

        suggestions = []

        # 1. Direct matches
        for cmd, path in self.direct_commands.items():
            if cmd.startswith(query) or query in cmd:
                suggestions.append({
                    "label": f"Launch: {cmd.capitalize()}",
                    "type": "direct",
                    "action": path
                })

        # 2. Smart matches
        for prefix, url_format in self.smart_commands.items():
            if query.startswith(prefix.strip()):
                search_term = query[len(prefix):].strip()
                if search_term:
                    suggestions.append({
                        "label": f"Search {prefix.strip().capitalize()} for '{search_term}'",
                        "type": "smart",
                        "action": url_format.format(search_term)
                    })

        # 3. Macros
        if query.startswith("record macro "):
            name = query[13:].strip()
            if name:
                suggestions.append({
                    "label": f"Start recording macro: '{name}'",
                    "type": "macro_record",
                    "action": name
                })
        elif query.startswith("play macro "):
            name = query[11:].strip()
            if name:
                suggestions.append({
                    "label": f"Play macro: '{name}'",
                    "type": "macro_play",
                    "action": name
                })
        elif query == "stop macro":
            suggestions.append({
                "label": "Stop recording current macro",
                "type": "macro_stop",
                "action": ""
            })

        # 4. AI intent
        suggestions.append({
            "label": f"Ask Kesari: '{query}'",
            "type": "ai",
            "action": query
        })

        return suggestions[:6]

    def execute_command(self, context: dict) -> Tuple[bool, str]:
        """
        Executes a direct or smart command instantly.
        Returns (handled_locally, response_message)
        If handled_locally is False, it should be passed to the LLM orchestrator.
        """
        cmd_type = context.get("type")
        action = context.get("action")

        if cmd_type == "direct":
            try:
                # Open directory or run program
                if os.path.exists(action):
                    os.startfile(action)
                else:
                    subprocess.Popen(action, shell=True)
                return True, f"Launched {action}"
            except Exception as e:
                logger.error(f"Failed to launch direct command {action}: {e}")
                return True, f"Error: Could not launch {action}"

        elif cmd_type == "smart":
            try:
                webbrowser.open(action)
                return True, f"Opened {action}"
            except Exception as e:
                logger.error(f"Failed to open smart command {action}: {e}")
                return True, f"Error: Could not open {action}"

        elif cmd_type == "macro_record":
            if hasattr(self, "macro_recorder"):
                self.macro_recorder.start_recording(action)
                return True, f"Started recording macro: {action}"
            return True, "Macro recorder not available"
            
        elif cmd_type == "macro_stop":
            if hasattr(self, "macro_recorder"):
                self.macro_recorder.stop_recording()
                return True, "Stopped recording macro"
            return True, "Macro recorder not available"
            
        elif cmd_type == "macro_play":
            if hasattr(self, "macro_recorder"):
                self.macro_recorder.play_macro(action)
                return True, f"Playing macro: {action}"
            return True, "Macro recorder not available"

        elif cmd_type == "ai":
            # Pass to AI orchestrator
            return False, action

        return False, "Unknown command type"
