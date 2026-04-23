"""
Kesari AI — Web Scraper Tool
Intelligent content extraction from web pages.
Uses Playwright (headless) with BeautifulSoup fallback.
Strips ads, nav, scripts — extracts clean article text.
"""
import asyncio
import logging
import re
from typing import Optional
from kesari.tools.base_tool import BaseTool
from kesari.tools.knowledge_cache_tool import get_cache, TTL_LONG

logger = logging.getLogger(__name__)

# Tags to remove (clutter)
_NOISE_TAGS = {
    "script", "style", "nav", "footer", "header", "aside",
    "advertisement", "iframe", "noscript", "form", "button",
}

# Content-bearing tags in priority order
_CONTENT_TAGS = ["article", "main", "section", "div"]


def _clean_text(raw: str) -> str:
    """Clean up whitespace and normalize text."""
    # Collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', raw)
    # Collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


async def _scrape_with_playwright(url: str) -> str:
    """Use headless Playwright to render and extract page content."""
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            # Try to get article text first
            text = await page.evaluate("""() => {
                // Remove noise elements
                ['script','style','nav','footer','header','aside','iframe'].forEach(tag => {
                    document.querySelectorAll(tag).forEach(el => el.remove());
                });
                // Try article first, then main, then body
                const article = document.querySelector('article') ||
                                document.querySelector('main') ||
                                document.querySelector('[role="main"]') ||
                                document.body;
                return article ? article.innerText : document.body.innerText;
            }""")
            await browser.close()
            return _clean_text(text)[:6000]
    except Exception as e:
        logger.warning(f"Playwright scrape failed for {url}: {e}")
        return ""


async def _scrape_with_requests(url: str) -> str:
    """Fallback: simple requests + BeautifulSoup scrape."""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
        loop = asyncio.get_event_loop()
        
        def _fetch():
            resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            resp.raise_for_status()
            return resp.text
        
        html = await loop.run_in_executor(None, _fetch)
        soup = BeautifulSoup(html, "lxml")
        
        # Remove noise
        for tag in _NOISE_TAGS:
            for el in soup.find_all(tag):
                el.decompose()
        
        # Extract main content
        content_el = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", class_=re.compile(r"(content|article|post|entry)", re.I))
            or soup.find("body")
        )
        
        text = content_el.get_text(separator="\n") if content_el else soup.get_text("\n")
        return _clean_text(text)[:6000]
    except ImportError:
        logger.warning("beautifulsoup4/lxml not installed. Run: pip install beautifulsoup4 lxml")
        return ""
    except Exception as e:
        logger.warning(f"Requests scrape failed for {url}: {e}")
        return ""


async def scrape_url(url: str) -> dict:
    """
    Scrape a URL and return {url, title, content, method}.
    Tries Playwright first, falls back to requests+BS4.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Check cache first
    cache = get_cache()
    cache_key = f"scrape:{url}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Try Playwright first (handles JS sites)
    content = await _scrape_with_playwright(url)
    method = "playwright"
    
    if not content or len(content) < 100:
        # Fallback to requests
        content = await _scrape_with_requests(url)
        method = "requests"

    result = {
        "url": url,
        "content": content if content else "Could not extract content from this page.",
        "length": len(content),
        "method": method,
    }

    if content and len(content) > 200:
        cache.set(cache_key, result, ttl=TTL_LONG, intent="scrape", source=method)

    return result


def _extract_key_sentences(text: str, query: str = "", max_sentences: int = 8) -> str:
    """
    Extractive summarization: score sentences by keyword overlap with query.
    Returns the top-scoring sentences in original order.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 40]
    
    if not sentences:
        return text[:800]
    
    query_words = set(query.lower().split()) if query else set()
    
    def score(s: str) -> float:
        words = set(s.lower().split())
        overlap = len(words & query_words)
        # Favor sentences with query keywords
        return overlap + (len(s) / 500.0)  # slight length bonus
    
    if query_words:
        scored = sorted(enumerate(sentences), key=lambda x: score(x[1]), reverse=True)
        top_indices = sorted([i for i, _ in scored[:max_sentences]])
        return " ".join(sentences[i] for i in top_indices)
    else:
        # No query: return first N sentences
        return " ".join(sentences[:max_sentences])


# ── Tool Class ────────────────────────────────────────────

class WebScraperTool(BaseTool):
    name = "web_scraper"
    description = (
        "Scrape and extract the main text content from any web page URL. "
        "Use this to read articles, documentation, blog posts, or any webpage. "
        "Also use this when user says 'summarize this link' or 'read this URL'."
    )
    parameters = {
        "url": {
            "type": "string",
            "description": "The full URL to scrape (must start with http:// or https://)",
        },
        "query": {
            "type": "string",
            "description": "Optional: what the user is looking for (improves extraction relevance)",
        },
    }

    async def execute(self, **kwargs) -> str:
        url = kwargs.get("url", "")
        query = kwargs.get("query", "")
        if not url:
            return "Error: No URL provided."
        result = await scrape_url(url)
        content = result["content"]
        if query and len(content) > 1000:
            # Extract key sentences relevant to query
            summary = _extract_key_sentences(content, query, max_sentences=10)
            content = summary
        import json
        return json.dumps({
            "url": url,
            "content": content[:4000],
            "method": result["method"],
        }, ensure_ascii=False)
