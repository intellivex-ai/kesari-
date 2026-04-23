"""
Kesari AI - Browser Automation Tool
Allows agents to fully control a web browser (navigate, click, type, extract).
"""
import asyncio
import logging
from typing import Any, Optional
from kesari.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

# Global browser state to maintain session across tool calls
_playwright = None
_browser = None
_page = None

class BrowserAutomationTool(BaseTool):
    """
    A tool to automate web browsers natively using Playwright.
    Maintains a persistent session across calls.
    """

    name = "browser_automation"
    description = "Automate web browsing: navigate, click elements, fill forms, and extract content."
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["goto", "click", "fill", "extract_text", "close"],
                "description": "Browser action to perform."
            },
            "url": {"type": "string", "description": "URL to navigate to (for goto action)."},
            "selector": {"type": "string", "description": "CSS selector to click or fill."},
            "text": {"type": "string", "description": "Text to fill (for fill action)."}
        },
        "required": ["action"]
    }

    def __init__(self):
        super().__init__()

    async def _ensure_browser(self):
        global _playwright, _browser, _page
        if not _playwright:
            from playwright.async_api import async_playwright
            _playwright = await async_playwright().start()
            # Try to launch visible browser for "AI Agent" effect
            _browser = await _playwright.chromium.launch(headless=False)
            context = await _browser.new_context(viewport={"width": 1280, "height": 720})
            _page = await context.new_page()

    async def execute(self, action: str, **kwargs) -> Any:
        global _playwright, _browser, _page
        try:
            if action != "close":
                await self._ensure_browser()

            if action == "goto":
                url = kwargs.get("url")
                if not url: return "Error: Missing URL."
                if not url.startswith("http"): url = "https://" + url
                await _page.goto(url, wait_until="domcontentloaded")
                return f"Navigated to {url}. Page title is '{await _page.title()}'"

            elif action == "click":
                selector = kwargs.get("selector")
                if not selector: return "Error: Missing selector."
                await _page.click(selector)
                await _page.wait_for_timeout(1000) # give time for page reaction
                return f"Clicked element '{selector}'."

            elif action == "fill":
                selector = kwargs.get("selector")
                text = kwargs.get("text", "")
                if not selector: return "Error: Missing selector."
                await _page.fill(selector, text)
                return f"Filled '{text}' into '{selector}'."

            elif action == "extract_text":
                # Extract clean text from body
                text = await _page.evaluate("document.body.innerText")
                # Truncate to save context window, return first 2000 chars
                return f"Page content extracted ({len(text)} chars):\n{text[:2000]}"

            elif action == "close":
                if _browser:
                    await _browser.close()
                if _playwright:
                    await _playwright.stop()
                _playwright = _browser = _page = None
                return "Browser session closed."

            else:
                return f"Error: Unknown action '{action}'"
        except Exception as e:
            return f"Browser Automation Error: {str(e)}"
