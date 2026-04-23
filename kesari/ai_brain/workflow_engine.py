"""
Kesari AI — Workflow Engine
A robust orchestrator that iteratively processes multi-step tool calls natively through the NVIDIA client.
Handles approval gates for destructive macro actions.
"""
import logging
from typing import AsyncGenerator, Any

logger = logging.getLogger(__name__)

# Tools that modify state and require explicit user approval in a workflow
DANGEROUS_TOOLS = {
    "run_system_command",
    "close_application",
    "os_control",
    "file_system",
}

class WorkflowEngine:
    def __init__(self, ai_client, tool_router, audit_logger=None, auto_mode_callback=None):
        self.ai_client = ai_client
        self.tool_router = tool_router
        self.audit_logger = audit_logger
        self.auto_mode_callback = auto_mode_callback

    def is_auto_mode(self) -> bool:
        if self.auto_mode_callback:
            return self.auto_mode_callback()
        return False

    async def run_workflow(self, extra_context: str, max_steps: int = 5, model_override: str | None = None) -> AsyncGenerator[dict[str, Any], None]:
        """
        Executes a streaming ai request, resolving subsequent tool calls automatically up to max_steps.
        Yields all tokens and events back to the UI.
        If model_override is set, uses that model instead of the default.
        """
        tools = self.tool_router.get_definitions()
        
        # Step 0: The initial stream
        stream = self.ai_client.stream_chat(extra_context=extra_context, tools=tools, model_override=model_override)
        
        steps_taken = 0
        while steps_taken < max_steps:
            steps_taken += 1
            tool_calls_this_turn = []
            
            async for event in stream:
                if event["type"] == "token":
                    yield event
                elif event["type"] == "tool_call":
                    tool_calls_this_turn.append(event)
                    yield event
                elif event["type"] == "done":
                    # Done with this chunk entirely, normal finish
                    yield event
                    return
                elif event["type"] == "error":
                    yield event
                    return
            
            # If no tools were called, this turn is done.
            if not tool_calls_this_turn:
                break
                
            # Execute all tools collected in this turn
            for event in tool_calls_this_turn:
                tool_name = event["name"]
                args = event["arguments"]
                t_id = event["id"]
                
                # Check for approval gate
                if tool_name in DANGEROUS_TOOLS and not self.is_auto_mode():
                    yield {
                        "type": "tool_executing", 
                        "tool_name": tool_name, 
                        "step_label": f"Blocked: {tool_name} requires Auto Mode"
                    }
                    result = f"BLOCKED BY SAFETY SYSTEM: '{tool_name}' is dangerous. You must ask the user to enable 'Auto Mode' to proceed."
                    if self.audit_logger:
                        self.audit_logger.log_execution(tool_name, args, status="blocked")
                    self.ai_client.add_tool_result(t_id, tool_name, str(result))
                    continue
                
                # Map action types to emojis for the UI ActionStepWidget
                step_label = f"Using {tool_name}"
                if tool_name == "os_control":
                    act = args.get("action", "")
                    if act == "click": step_label = "🖱️ Clicking on screen"
                    elif act == "type": step_label = f"⌨️ Typing '{args.get('text', '')}'"
                    elif act == "press": step_label = f"⌨️ Pressing '{args.get('text', '')}'"
                    elif act == "open_app": step_label = f"🖥️ Opening '{args.get('app_path_or_name', '')}'"
                elif tool_name == "file_system":
                    step_label = f"📁 Managing file '{args.get('path', '')}'"
                elif tool_name == "browser_automation":
                    act = args.get("action", "")
                    if act == "goto": step_label = f"🌐 Navigating to {args.get('url', '')}"
                    else: step_label = f"🌐 Browser action: {act}"

                yield {"type": "tool_executing", "tool_name": tool_name, "step_label": step_label}
                
                try:
                    result = await self.tool_router.execute(tool_name, args)
                    if self.audit_logger:
                        self.audit_logger.log_execution(tool_name, args, status="success")
                except Exception as e:
                    result = f"Error executing tool {tool_name}: {e}"
                    if self.audit_logger:
                        self.audit_logger.log_execution(tool_name, args, status="error", status_message=str(e))
                    
                self.ai_client.add_tool_result(t_id, tool_name, str(result))
                yield {"type": "tool_completed", "tool_name": tool_name}
                
            # Prepare streaming the result follow-up
            stream = self.ai_client.complete_after_tools(tools=tools, model_override=model_override)

        # Fallback if max steps exceeded
        if steps_taken >= max_steps:
            logger.warning(f"Workflow aborted: Exceeded max {max_steps} steps.")
            yield {"type": "error", "content": f"Workflow exceeded maximum allowed steps ({max_steps})."}
