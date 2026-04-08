"""
Kesari AI — Local LLM Fallback
Ollama client for offline AI interactions.
"""
import json
import logging
from typing import AsyncGenerator, Any
import ollama

from kesari.ai_brain.prompts import build_system_messages

logger = logging.getLogger(__name__)

class OllamaClient:
    """Client for local Ollama LLM, designed to mirror OpenRouterClient stream semantics."""

    def __init__(self, model: str = "llama3"):
        self.model = model
        self.client = ollama.AsyncClient()
        self._conversation: list[dict] = []

    def clear_conversation(self):
        """Reset the conversation history."""
        self._conversation.clear()

    def add_user_message(self, content: str):
        self._conversation.append({"role": "user", "content": content})
        self._trim_history()

    def add_assistant_message(self, content: str):
        self._conversation.append({"role": "assistant", "content": content})
        self._trim_history()

    def add_tool_result(self, tool_call_id: str, tool_name: str, result: str):
        payload = result
        images = []
        try:
            data = json.loads(result)
            if isinstance(data, dict) and "image_base64" in data:
                payload = data.get("description", "Attached screen capture")
                images.append(data["image_base64"])
        except Exception:
            pass

        msg = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": payload,
        }
        if images:
            msg["images"] = images
            
        self._conversation.append(msg)
        self._trim_history()

    def _trim_history(self, max_messages: int = 20):
        if len(self._conversation) > max_messages:
            self._conversation = self._conversation[-max_messages:]

    def _build_messages(self, extra_context: str = "") -> list[dict]:
        messages = build_system_messages(extra_context)
        messages.extend(self._conversation)
        return messages

    async def stream_chat(
        self, extra_context: str = "", tools: list[dict] | None = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream chat response mimicking previous implementation yielding tokens, tool_calls, done, error.
        NOTE: Ollama tooling format is similar but client has some differences.
        """
        messages = self._build_messages(extra_context)
        
        # Format tools from openrouter standard to ollama (which also takes standard OpenAI dicts usually)
        # Ollama's python client supports pure dict format for functions:
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            # We must pass definitions unwrapped depending on ollama version.
            # Usually OpenAI format is supported native in latest ollama
            kwargs["tools"] = tools

        try:
            stream = await self.client.chat(**kwargs)
            
            full_content = ""
            
            # The ollama client returns a stream of async objects
            async for response in stream:
                msg = response.get('message', {})
                
                # Check for tool calls
                if msg.get('tool_calls'):
                    # Ollama usually yields tool calls fully formed in a single chunk
                    tcs = msg['tool_calls']
                    
                    self._conversation.append({
                        "role": "assistant",
                        "content": full_content or None,
                        "tool_calls": tcs
                    })
                    
                    for tc in tcs:
                        yield {
                            "type": "tool_call",
                            "id": "call_" + tc["function"]["name"],  # Dummy ID if none
                            "name": tc["function"]["name"],
                            "arguments": json.dumps(tc["function"]["arguments"]),
                        }
                    return
                
                # Normal tokens
                if msg.get('content'):
                    content = msg['content']
                    full_content += content
                    yield {"type": "token", "content": content}
                    
                if response.get('done'):
                    if full_content:
                        self.add_assistant_message(full_content)
                    yield {"type": "done", "content": full_content}
                    break

        except Exception as e:
            logger.error(f"Ollama stream error: {e}", exc_info=True)
            yield {"type": "error", "content": f"Ollama Error: {e}"}

    async def complete_after_tools(self, tools: list[dict] | None = None) -> AsyncGenerator[dict[str, Any], None]:
        # Simple recursive redirect to stream_chat after appending tools
        async for evt in self.stream_chat(tools=tools):
            yield evt
