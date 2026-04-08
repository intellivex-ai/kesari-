from pydantic import BaseModel, Field
from datetime import datetime
import dateparser
from typing import Any

from .base_tool import BaseTool

class AddReminderArgs(BaseModel):
    task_name: str = Field(description="The name or description of the task to be reminded about.")
    time_str: str = Field(description="When the reminder should trigger. Understands natural language like 'in 5 minutes', 'tomorrow at 3pm', etc.")

class AddReminderTool(BaseTool):
    """Tool to schedule a reminder or task for the user."""
    name = "add_reminder"
    description = "Schedules a reminder for the user. Accepts natural language time expressions."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "task_name": {"type": "string", "description": "The task name or description."},
                "time_str":  {"type": "string", "description": "When to remind — natural language, e.g. 'in 10 minutes'."},
            },
            "required": ["task_name", "time_str"],
        }

    def __init__(self, app_context=None):
        self.app = app_context

    async def execute(self, **kwargs) -> dict[str, Any]:
        task_name = kwargs.get("task_name")
        time_str = kwargs.get("time_str")

        parsed_time = dateparser.parse(time_str, settings={'PREFER_DATES_FROM': 'future'})
        if not parsed_time:
            return {"success": False, "error": f"Could not understand time: '{time_str}'."}

        if parsed_time < datetime.now():
            return {"success": False, "error": f"Time {parsed_time.strftime('%Y-%m-%d %I:%M %p')} is in the past."}

        trigger_time_str = parsed_time.isoformat()

        if self.app and hasattr(self.app, 'long_term_memory'):
            task_id = await self.app.long_term_memory.add_task(task_name, trigger_time_str)
            self.app._schedule_task_in_memory(task_id, task_name, parsed_time)
            return {"success": True, "result": f"Reminder set for {parsed_time.strftime('%Y-%m-%d %I:%M %p')}."}

        return {"success": False, "error": "Application context missing."}


class ListTasksArgs(BaseModel):
    pass


class ListTasksTool(BaseTool):
    """Tool to list all pending reminders/tasks."""
    name = "list_tasks"
    description = "Lists all pending scheduled tasks and reminders for the user."

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    def __init__(self, app_context=None):
        self.app = app_context

    async def execute(self, **kwargs) -> dict[str, Any]:
        if self.app and hasattr(self.app, 'long_term_memory'):
            tasks = await self.app.long_term_memory.list_pending_tasks()
            if not tasks:
                return {"success": True, "result": "No pending tasks found."}

            output = "Pending Tasks:\n"
            for t in tasks:
                dt = datetime.fromisoformat(t['trigger_time'])
                output += f"- [ID: {t['id']}] {t['task_name']} (at {dt.strftime('%Y-%m-%d %I:%M %p')})\n"
            return {"success": True, "result": output}

        return {"success": False, "error": "Application context missing."}



