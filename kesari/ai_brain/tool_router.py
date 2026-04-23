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
        if tool.name in self._tools:
            self._definitions = [d for d in self._definitions if d.get("function", {}).get("name") != tool.name]
        self._tools[tool.name] = tool
        self._definitions.append({
            "type": "function",
            "function": tool.definition,
        })
        logger.debug(f"Registered tool: {tool.name}")

    def get_definitions(self) -> list[dict]:
        """Return all tool definitions in OpenAI function-calling format."""
        return self._definitions
        
    def unregister(self, name: str):
        """Remove a tool by name."""
        if name in self._tools:
            del self._tools[name]
            self._definitions = [d for d in self._definitions if d.get("function", {}).get("name") != name]
            logger.debug(f"Unregistered tool: {name}")

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
            if not isinstance(args, dict):
                args = {}
        except json.JSONDecodeError:
            return json.dumps({"error": f"Invalid JSON arguments: {arguments_json}"})

        try:
            logger.debug(f"Executing tool: {name} with args: {args}")
            result = await tool.execute(**args)
            if isinstance(result, (dict, list)):
                return json.dumps(result, ensure_ascii=False, default=str)
            return str(result)
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}", exc_info=True)
            return json.dumps({"error": f"Tool '{name}' failed: {str(e)}"})

    # ── Inspection ────────────────────────────────────────

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_all_tools(self) -> dict[str, Any]:
        """Return the internal tools dictionary mapping names to tool instances."""
        return self._tools

    def has_tool(self, name: str) -> bool:
        return name in self._tools
