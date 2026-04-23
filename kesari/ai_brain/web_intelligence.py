"""
Kesari AI — Web Intelligence Engine
The core orchestration layer that:
  1. Classifies user intent (factual / research / comparison / realtime / news / scrape)
  2. Selects the right data sources
  3. Fetches and processes results
  4. Generates synthesized, human-readable answers
  5. Formats structured output for the GUI
"""
import asyncio
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# ── Intent Classification ─────────────────────────────────

INTENT_PATTERNS = {
    "realtime_weather": [
        r"\bweather\b", r"\btemperature\b", r"\bforecast\b",
        r"\bhow (is|will) (the )?weather\b", r"\b(it |)raining\b",
    ],
    "realtime_crypto": [
        r"\b(bitcoin|ethereum|btc|eth|solana|dogecoin|crypto|cryptocurrency)\b",
        r"\b(coin|token) price\b",
    ],
    "realtime_stock": [
        r"\bstock price\b", r"\bshare price\b", r"\b(nifty|sensex|nasdaq|dow)\b",
        r"\b([A-Z]{2,5})\s+(stock|share)\b",
    ],
    "news": [
        r"\b(latest|recent|today.?s|current) news\b",
        r"\bnews (on|about|in)\b",
        r"\bwhat.?s happening\b",
        r"\bheadlines\b",
        r"\bbreaking\b",
    ],
    "scrape": [
        r"\bsummariz(e|ing) (this |the |a )?(link|url|page|article|website)\b",
        r"\bread (this|the) (link|url|article)\b",
        r"https?://\S+",
    ],
    "comparison": [
        r"\b(vs|versus)\b", r"\bcompare\b", r"\bdifference between\b",
        r"\bbetter (than|or)\b", r"\bwhich (is|one|should)\b",
    ],
    "deep_research": [
        r"\bresearch\b", r"\bexplain (in detail|deeply|thoroughly)\b",
        r"\bhow does .+ work\b", r"\bdeep dive\b",
        r"\bbreak(ing)? down\b", r"\bcomprehensive\b",
    ],
    "factual": [
        r"\bwho is\b", r"\bwhat is\b", r"\bwhen (did|was|is)\b",
        r"\bwhere (is|was|are)\b", r"\bdefine\b", r"\bmeaning of\b",
    ],
}


def classify_intent(query: str) -> str:
    """Return the dominant intent for a user query."""
    q_lower = query.lower()
    for intent, patterns in INTENT_PATTERNS.items():
        if any(re.search(p, q_lower) for p in patterns):
            return intent
    # Default fallback
    return "search"


def extract_url(query: str) -> str | None:
    """Extract a URL from the user's query."""
    match = re.search(r'https?://\S+', query)
    return match.group(0) if match else None


def extract_city(query: str) -> str:
    """Best-effort city extraction from a weather query."""
    # Remove common phrases
    cleaned = re.sub(
        r'\b(weather|temperature|forecast|like|today|tomorrow|in|at|for|the|is|what|how)\b',
        ' ', query.lower()
    )
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned.title() if cleaned else "Mumbai"


def extract_crypto_name(query: str) -> str:
    """Extract crypto coin name from query."""
    known = ["bitcoin", "ethereum", "btc", "eth", "solana", "dogecoin", "bnb", "xrp", "ada", "dot"]
    q = query.lower()
    for name in known:
        if name in q:
            return name
    # Return first capitalized word
    words = query.split()
    return words[-1] if words else "bitcoin"


def extract_stock_symbol(query: str) -> str:
    """Extract stock symbol/name from query."""
    # Look for uppercase ticker
    match = re.search(r'\b([A-Z]{2,6})\b', query)
    if match:
        return match.group(1)
    # Return last word as fallback
    words = query.strip().split()
    return words[-1].upper() if words else "AAPL"


# ── Text Summarization ────────────────────────────────────

def _extractive_summary(texts: list[str], query: str, max_words: int = 150) -> str:
    """
    Simple extractive summarizer:
    Scores sentences by keyword overlap with query, picks top N.
    """
    query_words = set(re.findall(r'\w+', query.lower())) - {
        "the", "a", "an", "in", "on", "at", "for", "is", "are", "was", "were",
        "what", "who", "how", "where", "when", "why", "about", "tell", "me",
        "please", "can", "you", "i", "my", "your", "of", "to", "and", "or",
    }

    all_sentences: list[str] = []
    for text in texts:
        sents = re.split(r'(?<=[.!?])\s+', text)
        all_sentences.extend(s.strip() for s in sents if len(s.strip()) > 40)

    if not all_sentences:
        return texts[0][:400] if texts else "No information available."

    def score(s: str) -> float:
        words = set(re.findall(r'\w+', s.lower()))
        return len(words & query_words) / max(len(query_words), 1)

    scored = sorted(all_sentences, key=score, reverse=True)
    selected = []
    word_count = 0
    seen_starts = set()
    for sent in scored:
        start = sent[:20].lower()
        if start in seen_starts:
            continue
        seen_starts.add(start)
        words = len(sent.split())
        if word_count + words > max_words:
            break
        selected.append(sent)
        word_count += words

    return " ".join(selected) if selected else all_sentences[0][:400]


def _confidence_label(score: float) -> str:
    if score >= 0.90:
        return "✅ High"
    if score >= 0.70:
        return "⚡ Medium"
    return "⚠️ Low"


# ── WebResult Data Model ──────────────────────────────────

class WebResult:
    """Structured result from the web intelligence engine."""
    def __init__(
        self,
        intent: str,
        answer: str,
        key_points: list[str] | None = None,
        sources: list[dict] | None = None,
        raw_data: Any = None,
        is_deep_research: bool = False,
        report_sections: dict | None = None,
    ):
        self.intent = intent
        self.answer = answer
        self.key_points = key_points or []
        self.sources = sources or []
        self.raw_data = raw_data
        self.is_deep_research = is_deep_research
        self.report_sections = report_sections or {}

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "answer": self.answer,
            "key_points": self.key_points,
            "sources": self.sources,
            "raw_data": self.raw_data,
            "is_deep_research": self.is_deep_research,
            "report_sections": self.report_sections,
        }


# ── Main Engine ───────────────────────────────────────────

class WebIntelligenceEngine:
    """
    Orchestrates multi-source web queries, processes results,
    and generates synthesized answers with source transparency.
    """

    def __init__(self):
        self._cache = None

    def _get_cache(self):
        if self._cache is None:
            from kesari.tools.knowledge_cache_tool import get_cache
            self._cache = get_cache()
        return self._cache

    async def query(self, user_query: str, mode: str = "auto") -> WebResult:
        """
        Main entry point. Classifies intent and routes to the right handler.
        mode: 'auto' | 'search' | 'news' | 'research' | 'realtime'
        """
        intent = mode if mode != "auto" else classify_intent(user_query)
        logger.info(f"WebIntelligenceEngine: intent={intent!r} query={user_query[:60]!r}")

        try:
            if intent == "realtime_weather":
                return await self._handle_weather(user_query)
            elif intent == "realtime_crypto":
                return await self._handle_crypto(user_query)
            elif intent == "realtime_stock":
                return await self._handle_stock(user_query)
            elif intent == "news":
                return await self._handle_news(user_query)
            elif intent == "scrape":
                return await self._handle_scrape(user_query)
            elif intent == "deep_research":
                return await self._handle_deep_research(user_query)
            elif intent == "comparison":
                return await self._handle_comparison(user_query)
            else:
                # Default: web search (factual or general search)
                return await self._handle_search(user_query)
        except Exception as e:
            logger.error(f"WebIntelligenceEngine error: {e}", exc_info=True)
            return WebResult(
                intent=intent,
                answer=f"I encountered an error while searching: {str(e)[:100]}",
            )

    # ── Handlers ─────────────────────────────────────────

    async def _handle_search(self, query: str) -> WebResult:
        from kesari.tools.web_search_tool import web_search
        results = await web_search(query, max_results=6)
        if not results:
            return WebResult(
                intent="search",
                answer=f"I couldn't find information about: {query}",
            )
        snippets = [r["snippet"] for r in results if r.get("snippet")]
        answer = _extractive_summary(snippets, query, max_words=120)
        key_points = self._extract_key_points(snippets, max_points=4)
        return WebResult(
            intent="search",
            answer=answer,
            key_points=key_points,
            sources=results[:5],
            raw_data=results,
        )

    async def _handle_weather(self, query: str) -> WebResult:
        from kesari.tools.realtime_data_tool import get_weather
        city = extract_city(query)
        data = await get_weather(city)
        if "error" in data:
            return WebResult(intent="weather", answer=data["error"])
        answer = (
            f"{data['condition']} in **{data['city']}**\n"
            f"🌡️ Temperature: **{data['temperature']}**\n"
            f"💧 Humidity: {data['humidity']}\n"
            f"🌬️ Wind: {data['wind_speed']}"
        )
        return WebResult(
            intent="weather",
            answer=answer,
            raw_data=data,
        )

    async def _handle_crypto(self, query: str) -> WebResult:
        from kesari.tools.realtime_data_tool import get_crypto
        coin = extract_crypto_name(query)
        data = await get_crypto(coin)
        if "error" in data:
            return WebResult(intent="crypto", answer=data["error"])
        answer = (
            f"{data['trend']} **{data['symbol']}** — {data['price_usd']} (₹{data.get('price_inr', 'N/A')})\n"
            f"24h Change: **{data['change_24h']}**\n"
            f"Market Cap: {data.get('market_cap_usd', 'N/A')}"
        )
        return WebResult(intent="crypto", answer=answer, raw_data=data)

    async def _handle_stock(self, query: str) -> WebResult:
        from kesari.tools.realtime_data_tool import get_stock
        symbol = extract_stock_symbol(query)
        data = await get_stock(symbol)
        if "error" in data:
            return WebResult(intent="stock", answer=data["error"])
        answer = (
            f"{data['trend']} **{data.get('name', data['symbol'])}** ({data['symbol']})\n"
            f"Price: **{data['price']}**  |  Change: {data['change']} ({data['change_pct']})\n"
            f"Exchange: {data.get('exchange', 'N/A')}"
        )
        return WebResult(intent="stock", answer=answer, raw_data=data)

    async def _handle_news(self, query: str) -> WebResult:
        from kesari.tools.news_fetch_tool import fetch_news
        # Strip "news" keyword from query for better filtering
        topic = re.sub(r'\b(latest|recent|news|headlines|about|on)\b', '', query, flags=re.I).strip()
        items = await fetch_news(topic, max_items=6)
        if not items:
            return WebResult(intent="news", answer="Could not fetch news at this time.")

        lines = []
        for i, item in enumerate(items[:5], 1):
            lines.append(f"**{i}. {item['title']}**")
            if item.get("summary"):
                lines.append(f"   {item['summary'][:140]}...")
            lines.append(f"   🔗 [{item.get('source','Source')}]({item['url']})")

        answer = "\n".join(lines)
        sources = [
            {"title": item["title"], "url": item["url"],
             "snippet": item.get("summary", ""), "score": 0.8, "source": item.get("source", "")}
            for item in items
        ]
        return WebResult(intent="news", answer=answer, sources=sources, raw_data=items)

    async def _handle_scrape(self, query: str) -> WebResult:
        from kesari.tools.web_scraper_tool import scrape_url, _extract_key_sentences
        url = extract_url(query)
        if not url:
            return WebResult(intent="scrape", answer="No URL found in your message.")
        result = await scrape_url(url)
        content = result["content"]
        if not content or "Could not extract" in content:
            return WebResult(intent="scrape", answer=f"Could not read the content from: {url}")
        summary = _extract_key_sentences(content, query, max_sentences=8)
        key_points = self._extract_key_points([content], max_points=5)
        return WebResult(
            intent="scrape",
            answer=summary,
            key_points=key_points,
            sources=[{"title": "Scraped Article", "url": url, "snippet": summary[:100], "score": 0.8}],
        )

    async def _handle_comparison(self, query: str) -> WebResult:
        """Search both subjects and synthesize comparison."""
        # Extract subjects from comparison query
        patterns = [
            r'(.+?)\s+(?:vs|versus|or)\s+(.+)',
            r'(?:compare|difference between)\s+(.+?)\s+and\s+(.+)',
        ]
        subjects = []
        for pattern in patterns:
            m = re.search(pattern, query, re.I)
            if m:
                subjects = [m.group(1).strip(), m.group(2).strip()]
                break

        if len(subjects) < 2:
            # Fallback to regular search
            return await self._handle_search(query)

        from kesari.tools.web_search_tool import web_search
        results_a, results_b = await asyncio.gather(
            web_search(subjects[0], max_results=3),
            web_search(subjects[1], max_results=3),
        )

        def summarize_subject(results: list[dict], subject: str) -> str:
            snippets = [r["snippet"] for r in results if r.get("snippet")]
            return _extractive_summary(snippets, subject, max_words=60)

        sum_a = summarize_subject(results_a, subjects[0])
        sum_b = summarize_subject(results_b, subjects[1])

        answer = (
            f"**{subjects[0]}**\n{sum_a}\n\n"
            f"**{subjects[1]}**\n{sum_b}"
        )
        all_sources = results_a[:3] + results_b[:3]
        return WebResult(
            intent="comparison",
            answer=answer,
            sources=all_sources,
            report_sections={
                subjects[0]: sum_a,
                subjects[1]: sum_b,
            },
        )

    async def _handle_deep_research(self, query: str) -> WebResult:
        """Multi-step deep research: decompose → search → synthesize."""
        from kesari.tools.web_search_tool import web_search

        # Step 1: Decompose into sub-questions
        sub_questions = self._decompose_question(query)
        logger.info(f"Deep research: {len(sub_questions)} sub-questions")

        # Step 2: Search each sub-question concurrently
        search_tasks = [web_search(sq, max_results=4) for sq in sub_questions]
        all_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Step 3: Gather all snippets
        all_snippets: list[str] = []
        all_sources: list[dict] = []
        seen_urls: set[str] = set()

        for results in all_results:
            if isinstance(results, list):
                for r in results:
                    all_snippets.append(r.get("snippet", ""))
                    url = r.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_sources.append(r)

        # Step 4: Synthesize
        intro = _extractive_summary(all_snippets, query, max_words=80)
        key_points = self._extract_key_points(all_snippets, max_points=6)

        # Build section summaries
        sections = {}
        for i, (sq, results) in enumerate(zip(sub_questions, all_results)):
            if isinstance(results, list) and results:
                snippets = [r.get("snippet", "") for r in results]
                sections[sq] = _extractive_summary(snippets, sq, max_words=60)

        answer = intro
        return WebResult(
            intent="deep_research",
            answer=answer,
            key_points=key_points,
            sources=all_sources[:8],
            is_deep_research=True,
            report_sections=sections,
        )

    # ── Helpers ──────────────────────────────────────────

    def _decompose_question(self, question: str) -> list[str]:
        """Break a complex question into simpler sub-questions."""
        q = question.strip().rstrip("?")
        # Always include the original
        subs = [question]
        # Add "what is X" for the main topic
        topic_match = re.search(r'(?:about|explain|research|how does|how do)\s+(.+)', q, re.I)
        if topic_match:
            topic = topic_match.group(1)
            subs.append(f"what is {topic}")
            subs.append(f"{topic} how it works")
            subs.append(f"{topic} examples applications")
        else:
            words = q.split()
            if len(words) > 3:
                subs.append(f"overview of {q}")
                subs.append(f"{q} examples")
        return subs[:4]  # Cap at 4 sub-questions

    def _extract_key_points(self, texts: list[str], max_points: int = 5) -> list[str]:
        """Extract bullet-point key facts from search snippets."""
        all_sents: list[str] = []
        for text in texts:
            sents = re.split(r'(?<=[.!?])\s+', text)
            all_sents.extend(s.strip() for s in sents if 30 < len(s.strip()) < 200)

        # Deduplicate by first 30 chars
        seen: set[str] = set()
        unique: list[str] = []
        for sent in all_sents:
            key = sent[:30].lower()
            if key not in seen:
                seen.add(key)
                unique.append(sent)

        return unique[:max_points]
