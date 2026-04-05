"""
Kesari AI — Browser Agent
Playwright-based browser automation for web tasks.
"""
import json
import logging
import asyncio

logger = logging.getLogger(__name__)


class BrowserAgent:
    """
    Automates browser actions using Playwright.
    Runs in headed mode so the user can see what's happening.
    """

    def __init__(self):
        self._browser = None
        self._page = None
        self._playwright = None

    async def _ensure_browser(self):
        """Launch browser if not already running."""
        if self._browser and self._page:
            return

        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=False,  # User can see the browser
                args=["--start-maximized"],
            )
            context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
            )
            self._page = await context.new_page()
            logger.info("Browser agent launched")
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install"
            )

    async def navigate(self, url: str) -> dict:
        """Navigate to a URL."""
        await self._ensure_browser()
        try:
            response = await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return {
                "status": "success",
                "url": self._page.url,
                "title": await self._page.title(),
                "http_status": response.status if response else None,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def click(self, selector: str) -> dict:
        """Click an element by CSS selector."""
        await self._ensure_browser()
        try:
            await self._page.click(selector, timeout=5000)
            return {"status": "success", "message": f"Clicked: {selector}"}
        except Exception as e:
            return {"status": "error", "message": f"Click failed on '{selector}': {e}"}

    async def type_text(self, selector: str, text: str) -> dict:
        """Type text into an input field."""
        await self._ensure_browser()
        try:
            await self._page.fill(selector, text, timeout=5000)
            return {"status": "success", "message": f"Typed into: {selector}"}
        except Exception as e:
            return {"status": "error", "message": f"Type failed on '{selector}': {e}"}

    async def screenshot(self, path: str = "") -> dict:
        """Take a screenshot of the current page."""
        await self._ensure_browser()
        try:
            if not path:
                from pathlib import Path
                from datetime import datetime
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = str(Path.home() / "Desktop" / f"browser_screenshot_{ts}.png")
            await self._page.screenshot(path=path)
            return {"status": "success", "path": path}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_text(self, selector: str = "body") -> dict:
        """Extract text content from an element."""
        await self._ensure_browser()
        try:
            text = await self._page.inner_text(selector, timeout=5000)
            return {"status": "success", "text": text[:3000]}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def search_google(self, query: str) -> dict:
        """Search Google and return results."""
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        nav_result = await self.navigate(f"https://www.google.com/search?q={encoded_query}")
        if nav_result.get("status") == "error":
            return nav_result
        
        await asyncio.sleep(1)
        try:
            title = await self._page.title()
            return {"status": "success", "title": title, "url": self._page.url}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def close(self):
        """Close the browser."""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        finally:
            self._browser = None
            self._page = None
            self._playwright = None
            logger.info("Browser agent closed")
