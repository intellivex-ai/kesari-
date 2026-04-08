from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import dateparser
from typing import Any

from .base_tool import BaseTool, ToolResult

class AddReminderArgs(BaseModel):
    task_name: str = Field(description="The name or description of the task to be reminded about.")
    time_str: str = Field(description="When the reminder should trigger. Understands natural language like 'in 5 minutes', 'tomorrow at 3pm', etc.")

class AddReminderTool(BaseTool):
    """Tool to schedule a reminder or task for the user."""
    name = "add_reminder"
    description = "Schedules a reminder for the user. Accepts natural language time expressions."
    args_schema = AddReminderArgs

    def __init__(self, app_context=None):
        self.app = app_context

    async def execute(self, **kwargs) -> ToolResult:
        task_name = kwargs.get("task_name")
        time_str = kwargs.get("time_str")

        # Parse the natural language time into a datetime object
        parsed_time = dateparser.parse(time_str, settings={'PREFER_DATES_FROM': 'future'})
        if not parsed_time:
            return ToolResult(
                success=False,
                data=f"Could not understand the time expression: '{time_str}'. Please use a format like 'in 10 minutes' or 'tomorrow at 9am'."
            )

        if parsed_time < datetime.now():
            return ToolResult(
                success=False,
                data=f"Parsed time {parsed_time.strftime('%Y-%m-%d %I:%M %p')} is in the past! Cannot schedule."
            )

        trigger_time_str = parsed_time.isoformat()

        # If app is running, register the task in SQLite and Memory
        if self.app and hasattr(self.app, 'long_term_memory'):
            task_id = await self.app.long_term_memory.add_task(task_name, trigger_time_str)
            # Notify the async worker/scheduler
            self.app._schedule_task_in_memory(task_id, task_name, parsed_time)
            
            return ToolResult(
                success=True,
                data=f"Reminder scheduled successfully for {parsed_time.strftime('%Y-%m-%d %I:%M %p')}."
            )
        else:
            return ToolResult(
                success=False,
                data="Application context missing. Cannot schedule task."
            )

class ListTasksArgs(BaseModel):
    pass

class ListTasksTool(BaseTool):
    """Tool to list all pending reminders/tasks."""
    name = "list_tasks"
    description = "Lists all pending scheduled tasks and reminders for the user."
    args_schema = ListTasksArgs

    def __init__(self, app_context=None):
        self.app = app_context

    async def execute(self, **kwargs) -> ToolResult:
        if self.app and hasattr(self.app, 'long_term_memory'):
            tasks = await self.app.long_term_memory.list_pending_tasks()
            if not tasks:
                return ToolResult(success=True, data="No pending tasks found.")
            
            output = "Pending Tasks:\n"
            for t in tasks:
                dt = datetime.fromisoformat(t['trigger_time'])
                formatted_dt = dt.strftime('%Y-%m-%d %I:%M %p')
                output += f"- [ID: {t['id']}] {t['task_name']} (Scheduled for: {formatted_dt})\n"
            return ToolResult(success=True, data=output)
        
        return ToolResult(success=False, data="Application context missing.")
