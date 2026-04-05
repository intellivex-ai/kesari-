"""
Kesari AI — Open Application Tool
Opens applications on Windows by name.
"""
import subprocess
import os
import shutil
import glob
from kesari.tools.base_tool import BaseTool

# Common app name → executable/URI mappings for Windows
APP_MAP = {
    # Browsers
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    # Dev tools
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    # System
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "explorer": "explorer",
    "file explorer": "explorer",
    "cmd": "cmd",
    "command prompt": "cmd",
    "terminal": "wt",
    "windows terminal": "wt",
    "powershell": "powershell",
    "paint": "mspaint",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "control panel": "control",
    "snipping tool": "snippingtool",
    # Office
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    "teams": "ms-teams",
    # Media & Social
    "spotify": "spotify",
    "discord": "discord",
    "slack": "slack",
    "zoom": "zoom",
    "vlc": "vlc",
    "obs": "obs64",
    "obs studio": "obs64",
    "notepad++": "notepad++",
}

# Known install paths for apps not on PATH
KNOWN_PATHS = {
    "chrome": [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ],
    "firefox": [
        os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
    ],
    "discord": [
        os.path.expandvars(r"%LocalAppData%\Discord\Update.exe"),
    ],
    "spotify": [
        os.path.expandvars(r"%AppData%\Spotify\Spotify.exe"),
    ],
    "vlc": [
        os.path.expandvars(r"%ProgramFiles%\VideoLAN\VLC\vlc.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\VideoLAN\VLC\vlc.exe"),
    ],
}


class OpenAppTool(BaseTool):
    @property
    def name(self) -> str:
        return "open_app"

    @property
    def description(self) -> str:
        return (
            "Open an application on the user's Windows PC by its name. "
            "Examples: 'Chrome', 'VS Code', 'Calculator', 'Terminal', 'Spotify'."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "The name of the application to open (e.g. 'Chrome', 'VS Code', 'Calculator')",
                },
            },
            "required": ["app_name"],
        }

    async def execute(self, app_name: str) -> dict:
        name_lower = app_name.lower().strip()
        executable = APP_MAP.get(name_lower, name_lower)

        # 1. Handle URI schemes (ms-settings:, etc.)
        if executable.endswith(":"):
            try:
                os.startfile(executable)
                return {"status": "success", "message": f"Opened {app_name}"}
            except OSError as e:
                return {"status": "error", "message": f"Failed to open {app_name}: {e}"}

        DETACHED_PROCESS = 0x00000008

        # 2. Check if it's on PATH
        found = shutil.which(executable) or shutil.which(executable + ".exe")
        if found:
            try:
                subprocess.Popen([found], shell=False, creationflags=DETACHED_PROCESS)
                return {"status": "success", "message": f"Opened {app_name}"}
            except Exception as e:
                return {"status": "error", "message": f"Launch error: {e}"}

        # 3. Check known install paths
        for path in KNOWN_PATHS.get(executable, []):
            if os.path.exists(path):
                try:
                    if "Update.exe" in path:  # Discord uses --processStart
                        subprocess.Popen([path, "--processStart", "Discord.exe"], creationflags=DETACHED_PROCESS)
                    else:
                        subprocess.Popen([path], creationflags=DETACHED_PROCESS)
                    return {"status": "success", "message": f"Opened {app_name}"}
                except Exception as e:
                    return {"status": "error", "message": f"Launch error: {e}"}

        # 4. Try PowerShell Start-Process (resolves Start Menu shortcuts)
        import re
        if re.match(r"^[\w \-\+]+$", executable):
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f'Start-Process "{executable}"'],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    return {"status": "success", "message": f"Opened {app_name}"}
            except Exception:
                pass

        # 5. Try os.startfile as last resort
        try:
            os.startfile(app_name)
            return {"status": "success", "message": f"Opened {app_name}"}
        except OSError:
            pass

        return {
            "status": "error",
            "message": f"Could not find application: {app_name}. Try using the exact executable name.",
        }

