"""
Kesari AI — Tool Router
Dispatches function calls from the LLM to actual tool implementations.
"""
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ToolRouter:
    """
    Routes tool/function calls from the LLM to registered tool implementations.
    Each tool must be registered with a name and an async callable.
    """

    def __init__(self):
        self._tools: dict[str, Any] = {}     # name → tool instance
        self._definitions: list[dict] = []    # OpenAI-format tool definitions

    # ── Registration ──────────────────────────────────────

    def register(self, tool):
        """Register a tool instance (must have .name, .definition, .execute())."""
        self._tools[tool.name] = tool
        self._definitions.append({
            "type": "function",
            "function": tool.definition,
        })
        logger.info(f"Registered tool: {tool.name}")

    def get_definitions(self) -> list[dict]:
        """Return all tool definitions in OpenAI function-calling format."""
        return self._definitions

    # ── Execution ─────────────────────────────────────────

    async def execute(self, name: str, arguments_json: str) -> str:
        """
        Execute a tool by name with JSON arguments.
        Returns the result as a string.
        """
        tool = self._tools.get(name)
        if not tool:
            return json.dumps({"error": f"Unknown tool: {name}"})

        try:
            args = json.loads(arguments_json) if arguments_json else {}
        except json.JSONDecodeError:
            return json.dumps({"error": f"Invalid JSON arguments: {arguments_json}"})

        try:
            logger.info(f"Executing tool: {name} with args: {args}")
            result = await tool.execute(**args)
            if isinstance(result, dict):
                return json.dumps(result, ensure_ascii=False)
            return str(result)
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}", exc_info=True)
            return json.dumps({"error": f"Tool '{name}' failed: {str(e)}"})

    # ── Inspection ────────────────────────────────────────

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        return name in self._tools
