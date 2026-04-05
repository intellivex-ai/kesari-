"""
Kesari AI — Session Memory
In-memory conversation history for the current session.
"""
from datetime import datetime


class SessionMemory:
    """Short-term memory for the current conversation session."""

    def __init__(self, max_messages: int = 50):
        self._messages: list[dict] = []
        self._max = max(1, max_messages)
        self._session_start = datetime.now()
        self._metadata: dict = {}

    def add_message(self, role: str, content: str, **extra):
        """Add a message to session memory."""
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **extra,
        }
        self._messages.append(entry)
        if len(self._messages) > self._max:
            self._messages = self._messages[-self._max:]

    def get_messages(self) -> list[dict]:
        """Get all messages in the session."""
        return list(self._messages)

    def get_last_n(self, n: int) -> list[dict]:
        """Get the last N messages."""
        if n <= 0:
            return []
        return self._messages[-n:]

    def get_summary(self) -> str:
        """Generate a brief summary of the session."""
        if not self._messages:
            return "No messages yet."
        user_msgs = [m for m in self._messages if m["role"] == "user"]
        if user_msgs:
            first = user_msgs[0]["content"][:60]
            return f"Session started with: '{first}...' ({len(self._messages)} messages)"
        return f"Session with {len(self._messages)} messages"

    def get_title(self) -> str:
        """Get a short title for sidebar display."""
        user_msgs = [m for m in self._messages if m["role"] == "user"]
        if user_msgs:
            return user_msgs[0]["content"][:40]
        return "New Chat"

    def clear(self):
        """Clear the session."""
        self._messages.clear()
        self._session_start = datetime.now()

    def set_metadata(self, key: str, value):
        self._metadata[key] = value

    def get_metadata(self, key: str, default=None):
        return self._metadata.get(key, default)

    @property
    def message_count(self) -> int:
        return len(self._messages)

    @property
    def is_empty(self) -> bool:
        return len(self._messages) == 0
