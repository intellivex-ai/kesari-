"""
Kesari AI — Plugin System
Loads and registers plugins from the plugins/ directory.
"""
import json
import importlib.util
import logging
from pathlib import Path
from typing import Any

from kesari.tools.base_tool import BaseTool
from kesari.ai_brain.tool_router import ToolRouter

logger = logging.getLogger(__name__)

PLUGINS_DIR = Path(__file__).resolve().parent.parent.parent / "plugins"


class PluginTool(BaseTool):
    """Dynamic tool wrapper for plugin-defined tools."""

    def __init__(self, name: str, description: str, parameters: dict, func):
        self._name = name
        self._description = description
        self._parameters = parameters
        self._func = func

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> dict:
        return self._parameters

    async def execute(self, **kwargs) -> dict:
        import asyncio
        if asyncio.iscoroutinefunction(self._func):
            return await self._func(**kwargs)
        return self._func(**kwargs)


def load_plugins(router: ToolRouter, plugins_dir: Path | None = None):
    """
    Scan plugins/ directory and register tools from each plugin.
    
    Each plugin must have:
    - plugin.json: manifest with name, description, tools
    - main.py: module with tool functions
    """
    search_dir = plugins_dir or PLUGINS_DIR
    if not search_dir.exists():
        search_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created plugins directory: {search_dir}")
        return

    for plugin_path in search_dir.iterdir():
        if not plugin_path.is_dir():
            continue

        manifest_path = plugin_path / "plugin.json"
        main_path = plugin_path / "main.py"

        if not manifest_path.exists():
            continue

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            plugin_name = manifest.get("name", plugin_path.name)

            if not main_path.exists():
                logger.warning(f"Plugin '{plugin_name}' has no main.py — skipped")
                continue

            if not plugin_path.name.replace("_", "").isalnum():
                logger.warning(f"Plugin directory '{plugin_path.name}' has invalid characters — skipped")
                continue

            # Load the plugin module
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_path.name}", str(main_path)
            )
            if spec is None or spec.loader is None:
                logger.error(f"Failed to create module spec for plugin {plugin_name}")
                continue
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Register each tool defined in the manifest
            for tool_def in manifest.get("tools", []):
                func_name = tool_def.get("function", tool_def["name"])
                func = getattr(module, func_name, None)
                if func is None:
                    logger.warning(
                        f"Plugin '{plugin_name}': function '{func_name}' not found"
                    )
                    continue

                tool = PluginTool(
                    name=tool_def["name"],
                    description=tool_def.get("description", ""),
                    parameters=tool_def.get("parameters", {"type": "object", "properties": {}}),
                    func=func,
                )
                router.register(tool)

            logger.info(f"Loaded plugin: {plugin_name} ({len(manifest.get('tools', []))} tools)")

        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_path}: {e}", exc_info=True)
