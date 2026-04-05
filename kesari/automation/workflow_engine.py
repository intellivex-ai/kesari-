"""
Kesari AI — Workflow Engine
Executes multi-step automated workflows.
"""
import logging
import asyncio
from typing import Any

logger = logging.getLogger(__name__)


class WorkflowStep:
    """A single step in a workflow."""

    def __init__(self, tool_name: str, args: dict, description: str = ""):
        self.tool_name = tool_name
        self.args = args
        self.description = description
        self.result: dict | None = None
        self.status: str = "pending"  # pending | running | success | error


class WorkflowEngine:
    """
    Executes multi-step workflows sequentially.
    Each step is a tool call with arguments.
    """

    def __init__(self, tool_router):
        self._router = tool_router
        self._running = False

    async def execute(
        self,
        steps: list[WorkflowStep],
        on_step_start=None,
        on_step_complete=None,
    ) -> list[WorkflowStep]:
        """
        Execute a list of workflow steps sequentially.
        Callbacks are called with (step_index, step) for real-time updates.
        """
        self._running = True

        for i, step in enumerate(steps):
            if not self._running:
                step.status = "cancelled"
                continue

            step.status = "running"
            if on_step_start:
                on_step_start(i, step)

            try:
                import json
                result_str = await self._router.execute(
                    step.tool_name,
                    json.dumps(step.args),
                )
                step.result = json.loads(result_str) if result_str else {}
                step.status = "success" if step.result.get("status") != "error" else "error"
            except Exception as e:
                step.result = {"status": "error", "message": str(e)}
                step.status = "error"

            if on_step_complete:
                on_step_complete(i, step)

            # Stop on error
            if step.status == "error":
                logger.warning(f"Workflow stopped at step {i}: {step.result}")
                break

            # Small delay between steps
            await asyncio.sleep(0.5)

        self._running = False
        return steps

    def cancel(self):
        """Cancel a running workflow."""
        self._running = False

    @staticmethod
    def create_steps(step_defs: list[dict]) -> list[WorkflowStep]:
        """
        Create WorkflowStep objects from a list of dicts:
        [{"tool": "open_website", "args": {"url": "..."}, "desc": "..."}]
        """
        return [
            WorkflowStep(
                tool_name=s["tool"],
                args=s.get("args", {}),
                description=s.get("desc", ""),
            )
            for s in step_defs
        ]
