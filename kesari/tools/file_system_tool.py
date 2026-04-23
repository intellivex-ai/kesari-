"""
Kesari AI - File System Tool
Provides autonomous agents with native file creation, editing, and organization capabilities.
"""
import os
import shutil
from pathlib import Path
import logging
from typing import Any, Optional
from kesari.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class FileSystemTool(BaseTool):
    """
    A tool for managing files natively. Can read, write, edit, delete, and organize files.
    """

    name = "file_system"
    description = "Manage the file system: read, write, append to files, or create directories."
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "write", "append", "mkdir", "delete", "list"],
                "description": "File system action to perform."
            },
            "path": {"type": "string", "description": "Absolute or relative file/folder path."},
            "content": {"type": "string", "description": "Content to write or append (optional)."}
        },
        "required": ["action", "path"]
    }

    def __init__(self):
        super().__init__()
        # Use user desktop or a safe directory as base if relative path provided
        self.base_dir = Path.home() / "Desktop"

    def _resolve_path(self, path_str: str) -> Path:
        p = Path(path_str)
        if not p.is_absolute():
            p = self.base_dir / p
        return p.resolve()

    async def execute(self, action: str, path: str, content: Optional[str] = None, **kwargs) -> Any:
        try:
            target_path = self._resolve_path(path)
            
            if action == "read":
                if not target_path.exists():
                    return f"Error: File '{target_path}' does not exist."
                with open(target_path, "r", encoding="utf-8") as f:
                    return f.read()
                    
            elif action == "write":
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(content or "")
                return f"Successfully wrote to '{target_path}'."
                
            elif action == "append":
                if not target_path.exists():
                    return f"Error: File '{target_path}' does not exist."
                with open(target_path, "a", encoding="utf-8") as f:
                    f.write(content or "")
                return f"Successfully appended to '{target_path}'."
                
            elif action == "mkdir":
                target_path.mkdir(parents=True, exist_ok=True)
                return f"Directory created at '{target_path}'."
                
            elif action == "delete":
                if not target_path.exists():
                    return f"Error: Path '{target_path}' does not exist."
                if target_path.is_file():
                    target_path.unlink()
                else:
                    shutil.rmtree(target_path)
                return f"Successfully deleted '{target_path}'."
                
            elif action == "list":
                if not target_path.exists() or not target_path.is_dir():
                    return f"Error: Path '{target_path}' is not a directory."
                items = os.listdir(target_path)
                return f"Contents of '{target_path}':\n" + "\n".join(items)
                
            else:
                return f"Error: Unknown action '{action}'"
        except Exception as e:
            return f"File System Error: {str(e)}"
