"""
Kesari AI — Agent Orchestrator
Routes tasks to specialized sub-agents that each have a focused purpose and toolset.
The orchestrator decides which agent is best suited to handle a request, then
delegates and collects the streamed result.

Agents:
  - ResearchAgent   → web search + summarization
  - CodingAgent     → code/file manipulation + execution
  - SystemAgent     → OS-level automation (shell, apps, clipboard)
  - GeneralAgent    → catch-all conversational response
"""
import logging
import asyncio
from typing import AsyncGenerator, Any

logger = logging.getLogger(__name__)


# ── Per-agent NVIDIA NIM model overrides ─────────────────────────────────────
# We use different NVIDIA NIM models depending on the agent's specialization.
AGENT_MODELS: dict[str, str] = {
    "general":  "meta/llama-3.2-90b-vision-instruct",  # Multimodal (for screenshots)
    "coding":   "qwen/qwen2.5-coder-32b-instruct",     # Specialized in code
    "research": "nvidia/nemotron-4-340b-instruct",     # Heavy reasoning + knowledge
    "system":   "nvidia/llama-3.1-nemotron-nano-8b-v1",# Extremely fast, low latency
}

AGENT_REGISTRY: dict[str, dict] = {
    "research": {
        "name": "ResearchAgent",
        "description": "Use when the user needs web search, fact-finding, or information retrieval.",
        "system_prefix": (
            "You are ResearchAgent, a sub-agent of Kesari AI. "
            "Your specialty is finding, validating, and clearly summarizing information. "
            "Use available search/browser tools. Be factual and cite sources."
        ),
        "tool_keywords": ["web_search", "read_url", "screenshot"],
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


class AgentOrchestrator:
    """
    A lightweight router that selects the most appropriate agent for a user's request,
    injects the agent's system prefix, and delegates to WorkflowEngine.
    """

    def __init__(self, ai_client, tool_router, workflow_engine):
        self.ai_client = ai_client
        self.tool_router = tool_router
        self.workflow_engine = workflow_engine
        self._active_agent: str = "general"

    def select_agent(self, user_message: str) -> str:
        """
        Heuristically select the best agent.
        Priority: keyword match in tool_keywords → agent-specific phrase matching → general.
        """
        msg_lower = user_message.lower()

        # Research keywords
        if any(kw in msg_lower for kw in [
            "search", "find", "look up", "google", "what is", "who is",
            "latest", "news", "browse", "article", "wikipedia",
        ]):
            return "research"

        # Coding keywords
        if any(kw in msg_lower for kw in [
            "code", "write a", "debug", "function", "class", "script",
            "python", "javascript", "error", "fix", "refactor", "implement",
        ]):
            return "coding"

        # System/OS keywords
        if any(kw in msg_lower for kw in [
            "open ", "close ", "run ", "execute", "terminal", "screenshot",
            "clipboard", "copy", "paste", "kill process", "restart",
        ]):
            return "system"

        return "general"

    def _build_agent_context(self, agent_key: str, user_context: str) -> str:
        """Prepend the agent's system_prefix to the extra context."""
        agent = AGENT_REGISTRY[agent_key]
        prefix = agent["system_prefix"]
        if user_context:
            return f"{prefix}\n\n{user_context}"
        return prefix

    async def run(
        self,
        user_message: str,
        extra_context: str = "",
        max_steps: int = 5,
        override_agent: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Select agent, set context, and run the workflow with the agent's model.
        Yields the same event dicts as WorkflowEngine.run_workflow().
        """
        agent_key = override_agent or self.select_agent(user_message)
        # Validate agent key exists
        if agent_key not in AGENT_REGISTRY:
            agent_key = "general"
        self._active_agent = agent_key
        agent = AGENT_REGISTRY[agent_key]
        model = agent.get("model")  # agent-specific model override
        logger.info(f"AgentOrchestrator: routing to '{agent['name']}' (model={model or 'default'})")

        # Yield a meta event so the UI can show which agent is active
        yield {
            "type": "agent_selected",
            "agent": agent["name"],
            "key": agent_key,
            "model": model,
        }

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
