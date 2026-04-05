"""
Kesari AI — OpenRouter Client
Handles LLM API calls with streaming and function/tool calling.
"""
import json
import asyncio
import logging
from typing import AsyncIterator

from openai import AsyncOpenAI

from kesari.config import settings, OPENROUTER_BASE_URL, MAX_CONTEXT_MESSAGES
from kesari.ai_brain.prompts import build_system_messages

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Async client for OpenRouter API with streaming + tool calling."""

    def __init__(self):
        self._client: AsyncOpenAI | None = None
        self._conversation: list[dict] = []

    # ── Setup ─────────────────────────────────────────────

    def _ensure_client(self):
        """Lazily create the OpenAI client pointed at OpenRouter."""
        api_key = settings.get("openrouter_api_key", "")
        if not api_key:
            raise ValueError(
                "OpenRouter API key not set. Go to Settings → API Keys."
            )
        self._client = AsyncOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://kesari-ai.local",
                "X-Title": "Kesari AI Desktop Assistant",
            },
        )

    @property
    def model(self) -> str:
        return settings.get("default_model", "openai/gpt-4o")

    # ── Conversation Management ───────────────────────────

    def clear_conversation(self):
        """Start a fresh conversation."""
        self._conversation.clear()

    def add_user_message(self, content: str):
        """Add a user message to the conversation history."""
        self._conversation.append({"role": "user", "content": content})
        self._trim_history()

    def add_assistant_message(self, content: str):
        """Add an assistant message to the conversation history."""
        self._conversation.append({"role": "assistant", "content": content})

    def add_tool_result(self, tool_call_id: str, name: str, content: str):
        """Add a tool result back into the conversation."""
        self._conversation.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content,
        })

    def _trim_history(self):
        """Keep conversation within the sliding window."""
        if len(self._conversation) > MAX_CONTEXT_MESSAGES:
            self._conversation = self._conversation[-MAX_CONTEXT_MESSAGES:]

    def _build_messages(self) -> list[dict]:
        """Build the full message list: system + conversation."""
        return build_system_messages() + list(self._conversation)

    # ── Streaming Chat ────────────────────────────────────

    async def stream_chat(
        self,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """
        Stream a chat completion. Yields dicts:
          {"type": "token", "content": "..."}
          {"type": "tool_call", "id": "...", "name": "...", "arguments": "..."}
          {"type": "done", "content": "full text"}
          {"type": "error", "content": "error message"}
        """
        self._ensure_client()
        messages = self._build_messages()

        kwargs = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            stream = await self._client.chat.completions.create(**kwargs)

            full_content = ""
            tool_calls_accumulator: dict[int, dict] = {}

            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                # ── Text content ──────────────────────
                if delta.content:
                    full_content += delta.content
                    yield {"type": "token", "content": delta.content}

                # ── Tool calls ────────────────────────
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_accumulator:
                            tool_calls_accumulator[idx] = {
                                "id": tc.id or "",
                                "name": tc.function.name or "" if tc.function else "",
                                "arguments": "",
                            }
                        if tc.id:
                            tool_calls_accumulator[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_accumulator[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_accumulator[idx]["arguments"] += tc.function.arguments

                # ── Finish reason ─────────────────────
                finish = chunk.choices[0].finish_reason if chunk.choices else None
                if finish == "tool_calls":
                    # Add assistant message with tool_calls to history FIRST
                    # (must happen before yield, since generator suspends at yield
                    #  and the caller will build follow-up messages immediately)
                    self._conversation.append({
                        "role": "assistant",
                        "content": full_content or None,
                        "tool_calls": [
                            {
                                "id": tool_calls_accumulator[i]["id"],
                                "type": "function",
                                "function": {
                                    "name": tool_calls_accumulator[i]["name"],
                                    "arguments": tool_calls_accumulator[i]["arguments"],
                                },
                            }
                            for i in sorted(tool_calls_accumulator.keys())
                        ],
                    })
                    # Now yield the tool call events for the UI/executor
                    for idx in sorted(tool_calls_accumulator.keys()):
                        tc_data = tool_calls_accumulator[idx]
                        yield {
                            "type": "tool_call",
                            "id": tc_data["id"],
                            "name": tc_data["name"],
                            "arguments": tc_data["arguments"],
                        }
                    return

                if finish == "stop":
                    break

            # Normal completion
            if full_content:
                self.add_assistant_message(full_content)
            yield {"type": "done", "content": full_content}

        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg:
                error_msg = "Invalid API key. Check your OpenRouter key in Settings."
            elif "429" in error_msg:
                error_msg = "Rate limit exceeded. Wait a moment and try again."
            elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                error_msg = f"Model '{self.model}' not found on OpenRouter."
            logger.error(f"OpenRouter error: {e}", exc_info=True)
            yield {"type": "error", "content": error_msg}

    # ── Non-streaming (for tool follow-up) ────────────────

    async def complete_after_tools(
        self,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """Resume streaming after tool results have been added."""
        async for event in self.stream_chat(tools=tools):
            yield event
