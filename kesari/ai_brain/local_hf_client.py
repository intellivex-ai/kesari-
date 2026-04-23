"""
Kesari AI — Local Hugging Face LLM Client
Client for running a lightweight transformers model directly in Python.
"""
import json
import logging
from typing import AsyncGenerator, Any
import asyncio
import torch
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer

from kesari.ai_brain.prompts import build_system_messages

logger = logging.getLogger(__name__)

class LocalHFClient:
    """Client for running a local Hugging Face transformer model entirely in Python."""

    def __init__(self, model_id: str = "Qwen/Qwen2.5-0.5B-Instruct"):
        self.model_id = model_id
        self._conversation: list[dict] = []
        
        # Load the model directly when the client is initialized.
        device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        logger.info(f"Loading local model '{self.model_id}' on {device}...")
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        
        # Ensure we do not use half precision on CPU unless supported, but usually float32 is safer for CPU.
        dtype = torch.float16 if device != "cpu" else torch.float32
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id, 
            torch_dtype=dtype,
            device_map="auto" if device != "cpu" else None
        )
        
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if device == "cuda" else -1 if device == "cpu" else None
        )
        logger.info(f"Local model '{self.model_id}' loaded successfully.")

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
        try:
            data = json.loads(result)
            if isinstance(data, dict) and "image_base64" in data:
                payload = data.get("description", "Attached screen capture")
        except Exception:
            pass

        msg = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": payload,
        }
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
        self, extra_context: str = "", tools: list[dict] | None = None, model_override: str | None = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream chat response yielding tokens.
        Runs generation in a thread to not block the asyncio event loop.
        """
        messages = self._build_messages(extra_context)
        
        # Format for the chat template
        prompt = self.tokenizer.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )

        try:
            def _generate():
                return self.pipe(
                    prompt, 
                    max_new_tokens=1024,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.95,
                    return_full_text=False
                )

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, _generate)
            
            full_content = result[0]['generated_text']
            
            # Yield token by token for UI effect
            chunk_size = 4
            for i in range(0, len(full_content), chunk_size):
                chunk = full_content[i:i+chunk_size]
                yield {"type": "token", "content": chunk}
                await asyncio.sleep(0.01)
                
            if full_content:
                self.add_assistant_message(full_content)
                
            yield {"type": "done", "content": full_content}

        except Exception as e:
            logger.error(f"Local model generation error: {e}", exc_info=True)
            yield {"type": "error", "content": f"Local Model Error: {e}"}

    async def complete_after_tools(self, tools: list[dict] | None = None, model_override: str | None = None) -> AsyncGenerator[dict[str, Any], None]:
        async for evt in self.stream_chat(tools=tools, model_override=model_override):
            yield evt
