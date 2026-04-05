"""
Kesari AI — Long-Term Memory
SQLite-backed persistent memory for conversations and preferences.
"""
import json
import logging
import aiosqlite
from datetime import datetime
from pathlib import Path

from kesari.config import DB_FILE

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_name TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tool_usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    arguments TEXT,
    result TEXT,
    success INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_tool_usage_time ON tool_usage_log(created_at);
"""


class LongTermMemory:
    """SQLite-backed persistent memory."""

    def __init__(self, db_path: Path | None = None):
        self._db_path = str(db_path or DB_FILE)
        self._initialized = False

    async def initialize(self):
        """Create tables if they don't exist."""
        if self._initialized:
            return
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(SCHEMA)
            await db.commit()
        self._initialized = True
        logger.info(f"Long-term memory initialized at {self._db_path}")

    # ── Conversations ────────────────────────────────────

    async def create_conversation(self, title: str) -> int:
        """Create a new conversation and return its ID."""
        await self.initialize()
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "INSERT INTO conversations (title) VALUES (?)",
                (title,),
            )
            await db.commit()
            return cursor.lastrowid

    async def list_conversations(self, limit: int = 20) -> list[dict]:
        """List recent conversations."""
        await self.initialize()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def delete_conversation(self, conversation_id: int):
        """Delete a conversation and its messages."""
        await self.initialize()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            await db.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            await db.commit()

    # ── Messages ─────────────────────────────────────────

    async def save_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        tool_name: str = None,
    ):
        """Save a message to a conversation."""
        await self.initialize()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO messages (conversation_id, role, content, tool_name) "
                "VALUES (?, ?, ?, ?)",
                (conversation_id, role, content, tool_name),
            )
            await db.execute(
                "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
                (conversation_id,),
            )
            await db.commit()

    async def get_messages(self, conversation_id: int) -> list[dict]:
        """Get all messages for a conversation."""
        await self.initialize()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at",
                (conversation_id,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ── Tool Usage Logging ───────────────────────────────

    async def log_tool_usage(
        self,
        tool_name: str,
        arguments: dict,
        result: str,
        success: bool = True,
    ):
        """Log a tool execution for analytics."""
        await self.initialize()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO tool_usage_log (tool_name, arguments, result, success) "
                "VALUES (?, ?, ?, ?)",
                (tool_name, json.dumps(arguments), result[:2000], int(success)),
            )
            await db.commit()

    async def get_frequent_tools(self, limit: int = 5) -> list[dict]:
        """Get most frequently used tools."""
        await self.initialize()
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT tool_name, COUNT(*) as count "
                "FROM tool_usage_log GROUP BY tool_name "
                "ORDER BY count DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
