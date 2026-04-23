"""
Kesari AI — Web Search Tool
Multi-source search using DuckDuckGo (no API key required).
Returns structured results with title, URL, snippet, and source reliability score.
"""
import asyncio
import logging
import re
from typing import Optional
from kesari.tools.base_tool import BaseTool
from kesari.tools.knowledge_cache_tool import get_cache, TTL_MEDIUM

logger = logging.getLogger(__name__)

# Domain reliability scores (higher = more trustworthy)
DOMAIN_SCORES: dict[str, float] = {
    "wikipedia.org": 0.95,
    "britannica.com": 0.93,
    "bbc.com": 0.90, "bbc.co.uk": 0.90,
    "reuters.com": 0.90,
    "theguardian.com": 0.88,
    "nytimes.com": 0.87,
    "nature.com": 0.95,
    "arxiv.org": 0.92,
    "github.com": 0.85,
    "stackoverflow.com": 0.82,
    "python.org": 0.95,
    "docs.python.org": 0.96,
    "developer.mozilla.org": 0.95,
    "medium.com": 0.65,
    "reddit.com": 0.55,
    "quora.com": 0.50,
}

def _domain_score(url: str) -> float:
    """Return reliability score for a URL's domain."""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lstrip("www.")
        for known_domain, score in DOMAIN_SCORES.items():
            if known_domain in domain:
                return score
    except Exception:
        pass
    return 0.70  # Default score for unknown domains


async def _ddg_html_search(query: str, max_results: int = 8) -> list[dict]:
    """Fallback scraper for DuckDuckGo HTML version if API fails."""
    try:
        import urllib.request
        import urllib.parse
        from bs4 import BeautifulSoup
        
        encoded = urllib.parse.quote(query.replace(' ', '+'))
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        
        loop = asyncio.get_event_loop()
        def _fetch():
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.read()
                
        html = await loop.run_in_executor(None, _fetch)
        soup = BeautifulSoup(html, "html.parser")
        
        results = []
        for result in soup.find_all('div', class_='result'):
            a_tag = result.find('a', class_='result__url')
            snip_tag = result.find('a', class_='result__snippet')
            if a_tag and snip_tag:
                title = result.find('h2', class_='result__title').text.strip()
                href = a_tag.get('href', '')
                if href.startswith('//duckduckgo.com/l/?uddg='):
                    import urllib.parse
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    if 'uddg' in parsed:
                        href = parsed['uddg'][0]
                
                results.append({
                    "title": title,
                    "url": href,
                    "snippet": snip_tag.text.strip()[:400],
                    "score": _domain_score(href),
                    "source": "duckduckgo (html)",
                })
                if len(results) >= max_results:
                    break
        return results
    except Exception as e:
        logger.debug(f"DDG HTML fallback failed: {e}")
        return []


async def _ddg_search(query: str, max_results: int = 8) -> list[dict]:
    """Search via DuckDuckGo API, with HTML fallback."""
    results = []
    try:
        from duckduckgo_search import DDGS
        loop = asyncio.get_event_loop()
        
        def _sync_search():
            with DDGS() as ddgs:
                return list(ddgs.text(
                    query,
                    max_results=max_results,
                    region="wt-wt",      # worldwide
                    safesearch="moderate",
                ))
        
        raw = await loop.run_in_executor(None, _sync_search)
        for r in raw:
            url = r.get("href", "")
            results.append({
                "title":   r.get("title", ""),
                "url":     url,
                "snippet": r.get("body", "")[:400],
                "score":   _domain_score(url),
                "source":  "duckduckgo",
            })
    except Exception as e:
        logger.warning(f"DDG API search failed: {e}. Falling back to HTML.")
        
    if not results:
        # Fallback to HTML scraper if API returned [] or failed
        results = await _ddg_html_search(query, max_results)
        
    # Sort by reliability score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


async def _wikipedia_search(query: str) -> Optional[dict]:
    """Fetch a Wikipedia summary using the search API."""
    try:
        import urllib.parse
        import urllib.request
        import json as _json
        
        encoded = urllib.parse.quote(query)
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded}&utf8=&format=json"
        
        loop = asyncio.get_event_loop()
        def _fetch():
            req = urllib.request.Request(url, headers={"User-Agent": "KesariAI/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                return _json.loads(resp.read())
        
        data = await loop.run_in_executor(None, _fetch)
        results = data.get("query", {}).get("search", [])
        if not results:
            return None
            
        top_hit = results[0]
        title = top_hit.get("title", "")
        # Remove HTML tags from snippet
        snippet = re.sub(r'<[^>]+>', '', top_hit.get("snippet", ""))
        
        # Now fetch the actual summary for this exact title to get a better snippet
        encoded_title = urllib.parse.quote(title)
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
        
        def _fetch_summary():
            req = urllib.request.Request(summary_url, headers={"User-Agent": "KesariAI/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                return _json.loads(resp.read())
                
        try:
            summary_data = await loop.run_in_executor(None, _fetch_summary)
            snippet = summary_data.get("extract", snippet)
            page_url = summary_data.get("content_urls", {}).get("desktop", {}).get("page", "")
        except:
            page_url = f"https://en.wikipedia.org/wiki/{encoded_title}"
            
        return {
            "title":   title,
            "url":     page_url,
            "snippet": snippet[:600],
            "score":   0.95,
            "source":  "wikipedia",
        }
    except Exception as e:
        logger.debug(f"Wikipedia fetch skipped: {e}")
        return None


async def web_search(
    query: str,
    max_results: int = 6,
    include_wikipedia: bool = True,
) -> list[dict]:
    """
    Perform a multi-source web search.
    Returns a ranked list of {title, url, snippet, score, source}.
    """
    cache = get_cache()
    cache_key = f"search:{query}"
    cached = cache.get(cache_key)
    if cached:
        logger.info(f"Web search cache hit: {query!r}")
        return cached

    tasks = [_ddg_search(query, max_results)]
    if include_wikipedia:
        tasks.append(_wikipedia_search(query))

    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    combined: list[dict] = []
    # DDG results
    ddg_results = results_list[0]
    if isinstance(ddg_results, list):
        combined.extend(ddg_results)

    # Wikipedia result (prepend if high relevance)
    if include_wikipedia and len(results_list) > 1:
        wiki = results_list[1]
        if isinstance(wiki, dict) and wiki:
            # Only include if Wikipedia title is related to query
            if any(w in wiki["title"].lower() for w in query.lower().split()):
                combined.insert(0, wiki)

    # Deduplicate by URL
    seen_urls = set()
    deduped = []
    for r in combined:
        url = r.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped.append(r)

    final = deduped[:max_results]
    cache.set(cache_key, final, ttl=TTL_MEDIUM, intent="search", source="multi")
    return final


# ── Tool Class ────────────────────────────────────────────

class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the internet for information about any topic. "
        "Returns ranked results with titles, URLs, and summaries. "
        "Use this when the user asks to search, look up, find information, or asks about current events."
    )
    parameters = {
        "query": {
            "type": "string",
            "description": "The search query string",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return (1-10, default 6)",
        },
    }

    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        max_results = min(int(kwargs.get("max_results", 6)), 10)
        if not query:
            return "Error: No search query provided."
        results = await web_search(query, max_results=max_results)
        if not results:
            return f"No results found for: {query}"
        # Return structured JSON for the intelligence engine to process
        import json
        return json.dumps({
            "query": query,
            "results": results,
            "count": len(results),
        }, ensure_ascii=False)
