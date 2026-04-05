"""
Kesari AI — Open Website Tool
Opens URLs in the default browser.
"""
import webbrowser
import re
from kesari.tools.base_tool import BaseTool


class OpenWebsiteTool(BaseTool):
    @property
    def name(self) -> str:
        return "open_website"

    @property
    def description(self) -> str:
        return (
            "Open a website URL in the user's default web browser. "
            "Examples: 'https://google.com', 'youtube.com', 'github.com'."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to open (e.g. 'https://google.com' or 'youtube.com')",
                },
            },
            "required": ["url"],
        }

    async def execute(self, url: str) -> dict:
        url = url.strip()

        # Auto-add https:// if missing
        if not re.match(r'^https?://', url, re.IGNORECASE):
            url = f"https://{url}"

        try:
            webbrowser.open(url)
            return {
                "status": "success",
                "message": f"Opened {url} in browser",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to open {url}: {str(e)}",
            }
