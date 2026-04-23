"""
Kesari AI — Agent Orchestrator v2
Routes tasks to specialized sub-agents with web intelligence integration.
"""
import logging
import asyncio
from typing import AsyncGenerator, Any
import re

logger = logging.getLogger(__name__)

AGENT_MODELS: dict[str, str] = {
    "general":  "meta/llama-3.2-90b-vision-instruct",
    "coding":   "qwen/qwen2.5-coder-32b-instruct",
    "research": "nvidia/nemotron-4-340b-instruct",
    "system":   "nvidia/llama-3.1-nemotron-nano-8b-v1",
    "planner":  "meta/llama-3.2-90b-vision-instruct",
    "action":   "meta/llama-3.2-90b-vision-instruct",
    "safety":   "nvidia/llama-3.1-nemotron-nano-8b-v1",
}

AGENT_REGISTRY: dict[str, dict] = {
    "research": {
        "name": "ResearchAgent",
        "description": "Use when the user needs web search, fact-finding, news, or real-time data.",
        "system_prefix": (
            "You are ResearchAgent, a sub-agent of Kesari AI. "
            "Your specialty is finding, validating, and clearly summarizing information. "
            "Use available search/browser tools. Be factual and cite sources."
        ),
        "tool_keywords": ["web_search", "web_scraper", "news_fetch", "realtime_data", "read_url", "screenshot"],
        "model": AGENT_MODELS["research"],
    },
    "coding": {
        "name": "CodingAgent",
        "description": "Use when the user wants to write, edit, debug, or explain code.",
        "system_prefix": (
            "You are CodingAgent, a sub-agent of Kesari AI. "
            "Your specialty is writing clean, idiomatic, well-documented code. "
            "Think step-by-step, write the code, then explain what it does."
        ),
        "tool_keywords": ["read_file", "write_file", "run_command"],
        "model": AGENT_MODELS["coding"],
    },
    "system": {
        "name": "SystemAgent",
        "description": "Use when the user needs OS automation: running commands, opening apps, managing clipboard.",
        "system_prefix": (
            "You are SystemAgent, a sub-agent of Kesari AI. "
            "Your specialty is OS-level automation. Act carefully — always confirm before destructive operations."
        ),
        "tool_keywords": ["run_system_command", "close_application", "set_clipboard", "get_clipboard", "capture_screen"],
        "model": AGENT_MODELS["system"],
    },
    "planner": {
        "name": "PlannerAgent",
        "description": "Use when the user requests a complex workflow requiring multiple autonomous steps across the OS or browser.",
        "system_prefix": (
            "You are PlannerAgent. Your job is to break down a high-level user request into a sequence of atomic tool calls. "
            "Do NOT execute them blindly. Plan step-by-step using OSControl, FileSystem, and BrowserAutomation tools."
        ),
        "tool_keywords": ["plan", "workflow", "automate", "do this", "setup"],
        "model": AGENT_MODELS["planner"],
    },
    "action": {
        "name": "ActionAgent",
        "description": "Executes the precise OS, file system, or browser actions defined by the planner.",
        "system_prefix": (
            "You are ActionAgent. You physically interact with the OS using the os_control, file_system, and browser_automation tools. "
            "Execute the requested action exactly."
        ),
        "tool_keywords": ["click", "type", "open", "browser_automation", "os_control", "file_system"],
        "model": AGENT_MODELS["action"],
    },
    "safety": {
        "name": "SafetyAgent",
        "description": "Validates if an action is destructive before execution.",
        "system_prefix": (
            "You are SafetyAgent. Analyze the proposed tool call and decide if it poses a risk (data loss, system mutation). "
            "If yes, return 'BLOCKED', else 'SAFE'."
        ),
        "tool_keywords": [],
        "model": AGENT_MODELS["safety"],
    },
    "general": {
        "name": "GeneralAgent",
        "description": "Fallback for general conversation, creative tasks, scheduling, or unknown requests.",
        "system_prefix": (
            "You are Kesari AI, a helpful, warm, and intelligent personal assistant. "
            "Be concise, accurate, and friendly."
        ),
        "tool_keywords": [],
        "model": AGENT_MODELS["general"],
    },
}

# ── Command Patterns (checked before heuristics) ──────────
COMMAND_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # (pattern, agent, web_mode)
    (re.compile(r'^(search for|search|google|look up|find information on)\s+', re.I), "research", "search"),
    (re.compile(r'^(research|deep dive|deep research|explain in detail)\s+', re.I), "research", "deep_research"),
    (re.compile(r'^(latest news on|news about|news on|what.?s happening in|headlines)\s+', re.I), "research", "news"),
    (re.compile(r'^(compare|difference between|vs |versus )', re.I), "research", "comparison"),
    (re.compile(r'^(summarize this link|read this|summarize|tldr)\s+(https?://)', re.I), "research", "scrape"),
    (re.compile(r'^(weather in|weather for|temperature in|how.?s the weather)', re.I), "research", "realtime_weather"),
    (re.compile(r'^(price of|how much is|crypto price|stock price)', re.I), "research", "auto"),
    
    # ── OS Automation / Planner Patterns ──
    (re.compile(r'^(open|close|type|click|create a file|edit file|automate|do this|setup|prepare my)\s+', re.I), "planner", ""),
]

# ── Web-Triggering Keywords ────────────────────────────────
RESEARCH_KEYWORDS = [
    "search", "find", "look up", "google", "what is", "who is",
    "latest", "news", "browse", "article", "wikipedia", "tell me about",
    "research", "explain", "how does", "why does", "compare", "vs",
    "weather", "temperature", "stock price", "crypto", "bitcoin",
    "ethereum", "forecast", "headlines", "breaking news",
]


class AgentOrchestrator:
    def __init__(self, ai_client, tool_router, workflow_engine):
        self.ai_client = ai_client
        self.tool_router = tool_router
        self.workflow_engine = workflow_engine
        self._active_agent: str = "general"
        self._web_engine = None  # Lazy-loaded

    def _get_web_engine(self):
        if self._web_engine is None:
            from kesari.ai_brain.web_intelligence import WebIntelligenceEngine
            self._web_engine = WebIntelligenceEngine()
        return self._web_engine

    def select_agent(self, user_message: str) -> tuple[str, str | None]:
        """
        Returns (agent_key, web_mode) where web_mode is None for local processing
        or one of: 'auto', 'search', 'news', 'deep_research', 'comparison', 'scrape',
                   'realtime_weather', 'realtime_crypto', 'realtime_stock'
        """
        msg_lower = user_message.lower()

        # 1. Check explicit command patterns first
        for pattern, agent, web_mode in COMMAND_PATTERNS:
            if pattern.search(user_message):
                return agent, web_mode

        # 2. Check URL presence → scrape mode
        if re.search(r'https?://\S+', user_message):
            return "research", "scrape"

        # 3. Research keywords → research + auto intent detection
        if any(kw in msg_lower for kw in RESEARCH_KEYWORDS):
            return "research", "auto"

        # 4. Coding keywords
        if any(kw in msg_lower for kw in [
            "code", "write a", "debug", "function", "class", "script",
            "python", "javascript", "error", "fix", "refactor", "implement",
        ]):
            return "coding", None

        # 5. System/OS keywords
        if any(kw in msg_lower for kw in [
            "open ", "close ", "run ", "execute", "terminal", "screenshot",
            "clipboard", "copy", "paste", "kill process", "restart",
        ]):
            return "system", None

        return "general", None

    def _build_agent_context(self, agent_key: str, user_context: str) -> str:
        agent = AGENT_REGISTRY[agent_key]
        prefix = agent["system_prefix"]
        if user_context:
            return f"{prefix}\n\n{user_context}"
        return prefix

    def _format_web_result(self, result) -> str:
        """Convert WebResult into a formatted string for the KesariClient stream."""
        from kesari.ai_brain.web_intelligence import WebResult
        if not isinstance(result, WebResult):
            return str(result)

        lines = []

        # Intent-specific prefix
        intent_icons = {
            "weather": "🌤️",
            "crypto": "💰",
            "stock": "📈",
            "news": "📰",
            "scrape": "📄",
            "search": "🔍",
            "deep_research": "🧠",
            "comparison": "⚖️",
            "factual": "💡",
        }
        icon = intent_icons.get(result.intent, "🌐")
        lines.append(f"{icon} **Web Intelligence Result**\n")

        lines.append(result.answer)

        if result.key_points:
            lines.append("\n\n**Key Points:**")
            for pt in result.key_points:
                lines.append(f"• {pt}")

        if result.is_deep_research and result.report_sections:
            lines.append("\n\n**Research Breakdown:**")
            for section, content in result.report_sections.items():
                lines.append(f"\n**{section}**\n{content}")

        if result.sources:
            lines.append(f"\n\n**Sources** ({len(result.sources)}):")
            for i, src in enumerate(result.sources[:5], 1):
                title = src.get("title", "Source")[:60]
                url = src.get("url", "#")
                score = src.get("score", 0.7)
                confidence = "✅" if score >= 0.85 else "⚡" if score >= 0.65 else "⚠️"
                lines.append(f"{confidence} [{title}]({url})")

        return "\n".join(lines)

    async def run(
        self,
        user_message: str,
        extra_context: str = "",
        max_steps: int = 5,
        override_agent: str | None = None,
        override_web_mode: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Select agent, run web intelligence if needed, then stream the result.
        """
        agent_key, web_mode = self.select_agent(user_message)
        if override_agent:
            agent_key = override_agent
        if override_web_mode:
            web_mode = override_web_mode

        if agent_key not in AGENT_REGISTRY:
            agent_key = "general"
        self._active_agent = agent_key
        agent = AGENT_REGISTRY[agent_key]
        model = agent.get("model")
        logger.info(f"AgentOrchestrator: routing to '{agent['name']}' web_mode={web_mode!r}")

        yield {
            "type": "agent_selected",
            "agent": agent["name"],
            "key": agent_key,
            "model": model,
        }

        # ── Web Intelligence Path ─────────────────────────
        if web_mode and agent_key == "research":
            yield {"type": "web_searching", "mode": web_mode, "query": user_message}
            try:
                engine = self._get_web_engine()
                web_result = await engine.query(user_message, mode=web_mode)
                formatted = self._format_web_result(web_result)

                # Stream the formatted result character by character
                for char in formatted:
                    yield {"type": "token", "content": char}
                    await asyncio.sleep(0.004)

                yield {
                    "type": "web_result",
                    "intent": web_result.intent,
                    "sources": web_result.sources,
                    "raw_data": web_result.raw_data,
                    "is_deep_research": web_result.is_deep_research,
                    "key_points": web_result.key_points,
                }
                yield {"type": "done", "content": formatted}
                return
            except Exception as e:
                logger.error(f"Web intelligence error: {e}", exc_info=True)
                yield {"type": "error", "content": f"Web search failed: {str(e)[:100]}"}
                return

        # ── Local KesariClient Path ───────────────────────
        agent_context = self._build_agent_context(agent_key, extra_context)

        async for event in self.workflow_engine.run_workflow(
            extra_context=agent_context, max_steps=max_steps, model_override=model
        ):
            yield event

    @property
    def active_agent(self) -> str:
        return AGENT_REGISTRY[self._active_agent]["name"]

    @staticmethod
    def list_agents() -> list[dict]:
        return [
            {"key": k, "name": v["name"], "description": v["description"]}
            for k, v in AGENT_REGISTRY.items()
        ]
