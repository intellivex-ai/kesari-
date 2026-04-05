"""
Kesari AI — Clipboard Tool
Read and write clipboard content.
"""
import pyperclip
from kesari.tools.base_tool import BaseTool


class ClipboardReadTool(BaseTool):
    @property
    def name(self) -> str:
        return "clipboard_read"

    @property
    def description(self) -> str:
        return "Read the current content of the user's clipboard."

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self) -> dict:
        try:
            content = pyperclip.paste()
            return {
                "status": "success",
                "content": content[:5000],  # Limit length
                "length": len(content),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


class ClipboardWriteTool(BaseTool):
    @property
    def name(self) -> str:
        return "clipboard_write"

    @property
    def description(self) -> str:
        return "Write text to the user's clipboard so they can paste it."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to copy to the clipboard",
                },
            },
            "required": ["text"],
        }

    async def execute(self, text: str) -> dict:
        try:
            pyperclip.copy(text)
            return {
                "status": "success",
                "message": f"Copied {len(text)} characters to clipboard",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
