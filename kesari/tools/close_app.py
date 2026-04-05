"""
Kesari AI — Close Application Tool
Closes applications on Windows by name.
"""
import psutil
from kesari.tools.base_tool import BaseTool

# Common names to process name mappings
PROCESS_MAP = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "notepad": "notepad.exe",
    "notepad++": "notepad++.exe",
    "explorer": "explorer.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "outlook": "OUTLOOK.EXE",
    "spotify": "Spotify.exe",
    "discord": "Discord.exe",
    "slack": "slack.exe",
    "zoom": "Zoom.exe",
    "vlc": "vlc.exe",
    "teams": "ms-teams.exe",
    "obs": "obs64.exe",
    "calculator": "CalculatorApp.exe",
}


class CloseAppTool(BaseTool):
    @property
    def name(self) -> str:
        return "close_app"

    @property
    def description(self) -> str:
        return (
            "Close a running application on the user's Windows PC by its name. "
            "Examples: 'Chrome', 'VS Code', 'Spotify'."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "The name of the application to close",
                },
            },
            "required": ["app_name"],
        }

    @property
    def requires_confirmation(self) -> bool:
        return True

    async def execute(self, app_name: str) -> dict:
        name_lower = app_name.lower().strip()
        process_name = PROCESS_MAP.get(name_lower, f"{name_lower}.exe")

        killed = 0
        errors = []

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pname = proc.info["name"]
                if pname and pname.lower() == process_name.lower():
                    proc.terminate()  # Graceful first
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                errors.append(str(e))

        if killed > 0:
            return {
                "status": "success",
                "message": f"Closed {killed} instance(s) of {app_name}",
            }
        elif errors:
            return {
                "status": "error",
                "message": f"Could not close {app_name}: access denied. Try running as administrator.",
            }
        else:
            return {
                "status": "not_found",
                "message": f"No running instance of {app_name} found.",
            }
