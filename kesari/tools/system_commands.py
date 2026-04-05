"""
Kesari AI — System Command Tools
Screenshot, system info, and command execution.
"""
import os
import subprocess
import platform
import time
from pathlib import Path
from datetime import datetime

import psutil
from PIL import ImageGrab

from kesari.tools.base_tool import BaseTool


class ScreenshotTool(BaseTool):
    @property
    def name(self) -> str:
        return "take_screenshot"

    @property
    def description(self) -> str:
        return "Take a screenshot of the screen and save it to the Desktop."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Optional filename for the screenshot (default: screenshot_<timestamp>.png)",
                },
            },
        }

    async def execute(self, filename: str = "") -> dict:
        desktop = Path.home() / "Desktop"
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"

        filepath = desktop / filename
        try:
            img = ImageGrab.grab()
            img.save(str(filepath))
            return {
                "status": "success",
                "message": f"Screenshot saved to {filepath}",
                "path": str(filepath),
            }
        except Exception as e:
            return {"status": "error", "message": f"Screenshot failed: {str(e)}"}


class SystemInfoTool(BaseTool):
    @property
    def name(self) -> str:
        return "system_info"

    @property
    def description(self) -> str:
        return (
            "Get system information: CPU usage, RAM usage, disk usage, "
            "OS version, battery status, and uptime."
        )

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self) -> dict:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        info = {
            "os": f"{platform.system()} {platform.release()}",
            "os_version": platform.version(),
            "processor": platform.processor(),
            "cpu_cores": psutil.cpu_count(),
            "cpu_usage_percent": cpu_percent,
            "ram_total_gb": round(memory.total / (1024**3), 1),
            "ram_used_gb": round(memory.used / (1024**3), 1),
            "ram_usage_percent": memory.percent,
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "disk_used_gb": round(disk.used / (1024**3), 1),
            "disk_usage_percent": round(disk.percent, 1),
        }

        # Battery info (if available)
        battery = psutil.sensors_battery()
        if battery:
            info["battery_percent"] = battery.percent
            info["battery_plugged"] = battery.power_plugged

        # Uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        info["uptime"] = f"{hours}h {minutes}m"

        return {"status": "success", **info}


class RunCommandTool(BaseTool):
    @property
    def name(self) -> str:
        return "run_command"

    @property
    def description(self) -> str:
        return (
            "Run a command or PowerShell command on the user's PC. "
            "Use for system operations like shutdown, restart, sleep, "
            "or any other terminal commands. BE CAREFUL with destructive commands."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to run (e.g. 'shutdown /s /t 60', 'ipconfig')",
                },
                "shell": {
                    "type": "string",
                    "description": "Shell to use: 'cmd' or 'powershell' (default: powershell)",
                },
            },
            "required": ["command"],
        }

    @property
    def requires_confirmation(self) -> bool:
        return True

    async def execute(self, command: str, shell: str = "powershell") -> dict:
        # Block extremely dangerous commands
        dangerous = ["format", "del /s", "rm -rf", "rd /s", ":(){", "fork"]
        cmd_lower = command.lower()
        for d in dangerous:
            if d in cmd_lower:
                return {
                    "status": "blocked",
                    "message": f"Command blocked for safety: contains '{d}'",
                }

        try:
            if shell == "cmd":
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            else:
                result = subprocess.run(
                    ["powershell", "-Command", command],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

            output = result.stdout.strip() or result.stderr.strip()
            return {
                "status": "success" if result.returncode == 0 else "error",
                "return_code": result.returncode,
                "output": output[:2000],  # Limit output length
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "Command timed out after 30 seconds"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
