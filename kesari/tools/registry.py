"""
Kesari AI — Tool Registry
Discovers and registers all available tools.
"""
import logging
from kesari.ai_brain.tool_router import ToolRouter
from kesari.tools.open_app import OpenAppTool
from kesari.tools.close_app import CloseAppTool
from kesari.tools.search_file import SearchFileTool
from kesari.tools.open_website import OpenWebsiteTool
from kesari.tools.system_commands import (
    ScreenshotTool, SystemInfoTool, RunCommandTool,
)
from kesari.tools.clipboard_tool import ClipboardReadTool, ClipboardWriteTool
from kesari.tools.task_manager import AddReminderTool, ListTasksTool
from kesari.tools.screen_context import CaptureScreenTool

logger = logging.getLogger(__name__)


def register_all_tools(router: ToolRouter, app=None):
    """Register all built-in tools with the router."""
    tools = [
        OpenAppTool(),
        CloseAppTool(),
        SearchFileTool(),
        OpenWebsiteTool(),
        ScreenshotTool(),
        SystemInfoTool(),
        RunCommandTool(),
        ClipboardReadTool(),
        ClipboardWriteTool(),
        AddReminderTool(app_context=app),
        ListTasksTool(app_context=app),
        CaptureScreenTool()
    ]
    for tool in tools:
        router.register(tool)
    logger.info(f"Registered {len(tools)} built-in tools")
