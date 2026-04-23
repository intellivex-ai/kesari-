"""
Kesari AI — Neural Link Brain v2
Similarity engine with real tool execution and Interactive Training Mode.
Optimized for i5 3rd Gen / 8GB RAM. Zero training, instant response.
"""
import logging
import difflib
import os
import re
import json
import uuid
from typing import AsyncGenerator, Any
import asyncio

logger = logging.getLogger(__name__)

# Regex to find action tags like:  {ACTION: open_app {"app_name": "notepad"}}
_ACTION_RE = re.compile(r'\{ACTION:\s*(\w+)\s*(\{.*?\})?\}', re.DOTALL)


class KesariClient:
    def __init__(self, model_path: str = "kesari/dataset.txt"):
        self.dataset_path = model_path
        self._conversation = []
        self._tool_results = []
        self.knowledge = {}
        
        # Training Mode State
        self._training_state = "IDLE" # IDLE, AWAITING_QUESTION, AWAITING_ANSWER
        self._pending_question = None
        
        self._load_dataset()

    # ── Dataset Loading ──────────────────────────────────────

    def _load_dataset(self):
        """Read dataset.txt and store User/Kesari pairs."""
        if not os.path.exists(self.dataset_path):
            alt_path = os.path.join(os.path.dirname(__file__), "..", "dataset.txt")
            if os.path.exists(alt_path):
                self.dataset_path = alt_path
            else:
                logger.error(f"Dataset not found at {self.dataset_path}")
                return

        try:
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                content = f.read().splitlines()

            # Clear existing knowledge before reloading
            self.knowledge.clear()
            
            current_user = None
            for line in content:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("User: "):
                    current_user = line.replace("User: ", "").strip().lower()
                elif line.startswith("Kesari: ") and current_user:
                    self.knowledge[current_user] = line.replace("Kesari: ", "").strip()

            logger.info(f"Neural Link loaded {len(self.knowledge)} response patterns.")
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")

    def _append_to_dataset(self, question: str, answer: str):
        """Append a new User/Kesari pair directly to the dataset file."""
        try:
            with open(self.dataset_path, 'a', encoding='utf-8') as f:
                f.write(f"\nUser: {question}\n")
                f.write(f"Kesari: {answer}\n")
            logger.info(f"Appended new knowledge: {question} -> {answer}")
        except Exception as e:
            logger.error(f"Failed to append to dataset: {e}")

    # ── Conversation Management ──────────────────────────────

    def add_user_message(self, content: str):
        self._conversation.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        self._conversation.append({"role": "assistant", "content": content})

    def add_tool_result(self, tool_call_id: str, tool_name: str, result: str):
        """Accept tool results from WorkflowEngine (stored for context logging)."""
        self._tool_results.append({
            "id": tool_call_id,
            "name": tool_name,
            "result": result,
        })
        logger.debug(f"Tool '{tool_name}' result received: {result[:120]}")

    def clear_conversation(self):
        self._conversation.clear()
        self._tool_results.clear()

    # ── Core Matching & State Machine ────────────────────────

    def _find_response(self, user_input: str) -> str:
        """Return the best matching Kesari response, or handle training mode."""
        user_lower = user_input.lower().strip()

        # Handle Commands
        if user_lower == "/cancel":
            self._training_state = "IDLE"
            self._pending_question = None
            return "Action cancelled. I am back to normal mode."
            
        if user_lower == "/train":
            self._training_state = "AWAITING_QUESTION"
            return "Training mode activated! What question or command should I learn?"

        # Handle Training State Machine
        if self._training_state == "AWAITING_QUESTION":
            self._pending_question = user_input.strip()
            self._training_state = "AWAITING_ANSWER"
            return f"Got it. What should be my exact answer to: '{self._pending_question}'?"
            
        if self._training_state == "AWAITING_ANSWER":
            answer = user_input.strip()
            # Save to dataset
            self._append_to_dataset(self._pending_question, answer)
            # Reload into memory instantly
            self._load_dataset()
            # Reset state
            self._training_state = "IDLE"
            self._pending_question = None
            return "Saved! I have added this to my brain. Returning to normal mode."

        # Normal Flow: Exact match first (fastest path)
        if user_lower in self.knowledge:
            return self.knowledge[user_lower]

        # Fuzzy similarity match — cutoff=0.55 means at least 55% similar
        # Higher threshold = fewer false matches = no hallucination
        matches = difflib.get_close_matches(
            user_lower, self.knowledge.keys(), n=1, cutoff=0.55
        )
        if matches:
            return self.knowledge[matches[0]]

        # Honest fallback — never make something up
        return (
            "Yeh cheez mujhe nahi pata abhi, boss. Mujhe dataset.txt mein "
            "sikhao aur main next time perfect answer dunga!\n"
            "(Type /train to teach me right now!)"
        )

    # ── Action Tag Parsing ───────────────────────────────────

    def _parse_action(self, response: str) -> tuple[str, dict | None]:
        """
        Split a response into (visible_text, action_dict).
        Example:
          "Opening Notepad. {ACTION: open_app {\"app_name\": \"notepad\"}}"
          → ("Opening Notepad.", {"tool": "open_app", "args": {"app_name": "notepad"}, "id": "<uuid>"})
        """
        match = _ACTION_RE.search(response)
        if not match:
            return response.strip(), None

        # Clean visible text — strip the tag
        visible = _ACTION_RE.sub("", response).strip()

        tool_name = match.group(1)
        args_str = match.group(2) or "{}"
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in ACTION tag: {args_str}")
            args = {}

        action = {
            "tool": tool_name,
            "args": args,
            "id": str(uuid.uuid4()),
        }
        return visible, action

    # ── Streaming ────────────────────────────────────────────

    async def stream_chat(
        self,
        extra_context: str = "",
        tools: list[dict] | None = None,
        model_override: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Find the best match, stream the visible text, then fire a tool_call
        event if the response contained an {ACTION: ...} tag.
        """
        if not self._conversation:
            yield {"type": "error", "content": "No user message found."}
            return

        user_input = self._conversation[-1]["content"]
        
        # Merge extra context if present (e.g., Vision context from AgentOrchestrator)
        search_query = user_input
        if extra_context:
            search_query = f"{extra_context}\n\nUser: {user_input}"
            
        raw_response = self._find_response(search_query)
        
        # If no match and it's a planner intent, dynamically generate action
        if "Yeh cheez mujhe nahi pata" in raw_response:
            lower_input = user_input.lower()
            if "open chrome and search for" in lower_input:
                query = lower_input.split("search for", 1)[1].strip()
                raw_response = f"Opening Chrome and searching for {query}. {{ACTION: browser_automation {{\"action\": \"goto\", \"url\": \"https://google.com/search?q={query.replace(' ', '+')}\"}}}}"
            elif lower_input.startswith("open "):
                app = lower_input[5:].strip()
                raw_response = f"Opening {app}. {{ACTION: os_control {{\"action\": \"open_app\", \"app_path_or_name\": \"{app}\"}}}}"
            elif "screen" in lower_input or "look at" in lower_input or "see" in lower_input:
                if "Vision Context attached" in extra_context:
                    raw_response = "I can see your screen, but I need you to teach me how to interpret this specific visual in dataset.txt. Type /train to teach me."
            else:
                # Basic fallback for context chips
                if "expand on this" in lower_input or "summarize" in lower_input:
                    raw_response = "I need a real LLM connected to expand on this topic. Please add this to my dataset.txt or connect an API!"
            
        visible_text, action = self._parse_action(raw_response)

        # Stream visible text character by character
        for char in visible_text:
            yield {"type": "token", "content": char}
            await asyncio.sleep(0.008)

        # If there's an action, yield a tool_call event for WorkflowEngine
        if action:
            yield {
                "type": "tool_call",
                "id": action["id"],
                "name": action["tool"],
                "arguments": json.dumps(action["args"]),
            }
        else:
            # No tool — signal completion normally
            self.add_assistant_message(visible_text)
            yield {"type": "done", "content": visible_text}

    async def complete_after_tools(
        self,
        tools: list[dict] | None = None,
        model_override: str | None = None,
        **kwargs,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Called by WorkflowEngine after tool results are collected.
        We generate a confirmation message based on what tool ran.
        """
        confirmation = "Done! The action has been completed successfully."

        # Try to produce a smarter confirmation from the last tool result
        if self._tool_results:
            last = self._tool_results[-1]
            result_str = last.get("result", "")
            try:
                result_obj = json.loads(result_str)
                if isinstance(result_obj, dict):
                    msg = result_obj.get("message") or result_obj.get("result") or result_obj.get("output", "")
                    if msg:
                        confirmation = str(msg)
            except (json.JSONDecodeError, TypeError):
                pass

        for char in confirmation:
            yield {"type": "token", "content": char}
            await asyncio.sleep(0.008)

        self.add_assistant_message(confirmation)
        yield {"type": "done", "content": confirmation}
