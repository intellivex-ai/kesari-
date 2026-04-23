"""
Kesari AI — Browser Agent Core
Uses Playwright to navigate websites, click elements, and extract text.
"""
import asyncio
import logging
from typing import Optional, Dict

try:
    from playwright.async_api import async_playwright, Page, Browser
except ImportError:
    async_playwright = None

logger = logging.getLogger(__name__)

class BrowserManager:
    """Manages a single global headless browser instance for performance."""
    _playwright = None
    _browser: Optional['Browser'] = None
    _page: Optional['Page'] = None

    @classmethod
    async def get_page(cls) -> 'Page':
        if not async_playwright:
            raise RuntimeError("Playwright is not installed. Run: pip install playwright && playwright install chromium")

        if cls._page is None:
            cls._playwright = await async_playwright().start()
            cls._browser = await cls._playwright.chromium.launch(headless=True)
            context = await cls._browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Kesari AI Assistant Browser/1.0"
            )
            cls._page = await context.new_page()
            
        return cls._page

    @classmethod
    async def cleanup(cls):
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None
        cls._page = None

# ─── Standard Tool Implementations ──────────────────────

async def browser_navigate(url: str) -> str:
    """Navigate to a URL and wait for it to load."""
    if not url.startswith("http"):
        url = "https://" + url
    page = await BrowserManager.get_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        title = await page.title()
        return f"Successfully navigated to {title} ({url})"
    except Exception as e:
        return f"Navigation failed: {str(e)}"

async def browser_extract_content() -> str:
    """Extract legible internal text from the currently loaded page."""
    page = await BrowserManager.get_page()
    try:
        # Quick eval to get innerText of body, stripping excess whitespace
        text = await page.evaluate("() => document.body.innerText")
        # Truncate to avoid context window explosion
        max_length = 8000
        if len(text) > max_length:
            return text[:max_length] + "\n...[Content Truncated]..."
        return text.strip() or "Page appears blank or could not be read."
    except Exception as e:
        return f"Extraction failed: {str(e)}"

async def browser_click(selector: str) -> str:
    """Click an element on the active page via CSS selector."""
    page = await BrowserManager.get_page()
    try:
        await page.click(selector, timeout=5000)
        # Wait a moment for dynamic rendering
        await page.wait_for_timeout(1500)
        return f"Clicked element matching '{selector}'."
    except Exception as e:
        return f"Click failed (selector might be wrong or invisible): {str(e)}"

async def browser_type(selector: str, text: str) -> str:
    """Type text into an input field on the active page."""
    page = await BrowserManager.get_page()
    try:
        await page.fill(selector, text, timeout=5000)
        return f"Typed text into '{selector}'."
    except Exception as e:
        return f"Typing failed: {str(e)}"

from kesari.tools.base_tool import BaseTool

class BrowserNavigateTool(BaseTool):
    name = "browser_navigate"
    description = "Navigate to a URL in the headless background browser."
    parameters = {
        "url": {"type": "string", "description": "The full HTTPS URL to load"}
    }
    async def execute(self, **kwargs) -> str:
        return await browser_navigate(kwargs["url"])

class BrowserExtractTool(BaseTool):
    name = "browser_extract"
    description = "Extract text content from the currently loaded page in the background browser."
    parameters = {}
    async def execute(self, **kwargs) -> str:
        return await browser_extract_content()

class BrowserClickTool(BaseTool):
    name = "browser_click"
    description = "Click an element using a CSS selector in the background browser."
    parameters = {
        "selector": {"type": "string", "description": "CSS selector of the element to click"}
    }
    async def execute(self, **kwargs) -> str:
        return await browser_click(kwargs["selector"])

class BrowserTypeTool(BaseTool):
    name = "browser_type"
    description = "Type text into an input field defined by a CSS selector in the background browser."
    parameters = {
        "selector": {"type": "string", "description": "CSS selector of the input field"},
        "text": {"type": "string", "description": "Text to type"}
    }
    async def execute(self, **kwargs) -> str:
        return await browser_type(kwargs["selector"], kwargs["text"])
