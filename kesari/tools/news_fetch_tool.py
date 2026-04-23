"""
Kesari AI — News Fetch Tool
Fetches live news from public RSS feeds. No API key required.
"""
import asyncio
import logging
import re
from kesari.tools.base_tool import BaseTool
from kesari.tools.knowledge_cache_tool import get_cache, TTL_SHORT

logger = logging.getLogger(__name__)

RSS_FEEDS = {
    "general": [
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://rss.reuters.com/reuters/topNews",
    ],
    "technology": [
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
    ],
    "science": [
        "https://www.sciencedaily.com/rss/top.xml",
    ],
    "business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://rss.reuters.com/reuters/businessNews",
    ],
    "sports": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
    ],
    "india": [
        "https://feeds.feedburner.com/ndtvnews-top-stories",
    ],
    "world": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
}


def _detect_category(query: str) -> str:
    q = query.lower()
    if any(w in q for w in ["tech", "ai", "software", "startup", "app", "gadget"]):
        return "technology"
    if any(w in q for w in ["science", "space", "research", "discovery"]):
        return "science"
    if any(w in q for w in ["business", "market", "economy", "finance"]):
        return "business"
    if any(w in q for w in ["sport", "cricket", "football", "ipl"]):
        return "sports"
    if any(w in q for w in ["india", "indian", "modi", "delhi"]):
        return "india"
    if any(w in q for w in ["world", "global", "international"]):
        return "world"
    return "general"


def _strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text or '').strip()


async def _fetch_rss(url: str) -> list[dict]:
    try:
        import feedparser
        loop = asyncio.get_event_loop()
        feed = await asyncio.wait_for(
            loop.run_in_executor(None, feedparser.parse, url),
            timeout=8.0
        )
        items = []
        for entry in feed.entries[:5]:
            title = _strip_html(entry.get("title", ""))
            summary = _strip_html(entry.get("summary", entry.get("description", "")))[:300]
            link = entry.get("link", "")
            published = entry.get("published", entry.get("updated", ""))
            if title and link:
                items.append({
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "published": published,
                    "source": feed.feed.get("title", url.split("/")[2]),
                })
        return items
    except ImportError:
        logger.warning("feedparser not installed. Run: pip install feedparser")
        return []
    except Exception as e:
        logger.debug(f"RSS error {url}: {e}")
        return []


def _deduplicate(items: list[dict]) -> list[dict]:
    seen, unique = [], []
    for item in items:
        title = item["title"].lower()
        if not any(
            len(set(title.split()) & set(t.split())) / max(len(title.split()), 1) > 0.7
            for t in seen
        ):
            seen.append(title)
            unique.append(item)
    return unique


async def fetch_news(query: str = "", max_items: int = 8) -> list[dict]:
    cache = get_cache()
    category = _detect_category(query)
    cache_key = f"news:{category}:{query[:50]}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    feed_urls = RSS_FEEDS.get(category, RSS_FEEDS["general"])
    tasks = [_fetch_rss(url) for url in feed_urls[:3]]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items: list[dict] = []
    for result in results:
        if isinstance(result, list):
            all_items.extend(result)

    deduped = _deduplicate(all_items)[:max_items]
    if deduped:
        cache.set(cache_key, deduped, ttl=TTL_SHORT, intent="news", source="rss")
    return deduped


class NewsFetchTool(BaseTool):
    name = "news_fetch"
    description = (
        "Fetch the latest news headlines and summaries. Use when user asks about "
        "current events, news, 'what's happening in...', 'latest news on...' etc."
    )
    parameters = {
        "query": {"type": "string", "description": "Topic to search news for"},
        "max_items": {"type": "integer", "description": "Maximum items (default 6)"},
    }

    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        max_items = min(int(kwargs.get("max_items", 6)), 10)
        items = await fetch_news(query, max_items=max_items)
        if not items:
            return f"No news found for: {query or 'general topics'}"
        import json
        return json.dumps({"query": query, "items": items, "count": len(items)}, ensure_ascii=False)
