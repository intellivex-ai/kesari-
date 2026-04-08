"""
Kesari AI — Audit Logger
Creates an immutable ledger of sensitive tool executions for trust and safety transparency.
"""
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class AuditLogger:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        tool_name TEXT NOT NULL,
                        arguments TEXT,
                        status TEXT,
                        status_message TEXT,
                        workflow_id TEXT
                    )
                    """
                )
                conn.commit()
            logger.info(f"Audit logger initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize audit logger: {e}")

    def log_execution(
        self,
        tool_name: str,
        arguments: dict | str,
        status: str = "invoked",
        status_message: str = "",
        workflow_id: str = "none"
    ):
        """Append an event to the audit ledger."""
        arg_str = json.dumps(arguments) if isinstance(arguments, dict) else str(arguments)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO audit_log (timestamp, tool_name, arguments, status, status_message, workflow_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (datetime.now().isoformat(), tool_name, arg_str, status, status_message, workflow_id)
                )
                conn.commit()
            logger.debug(f"Audit log entry -> {tool_name} [{status}]")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def get_logs(self, limit: int = 100) -> list[dict]:
        """Fetch the most recent logs for review."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(
                    "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to fetch audit logs: {e}")
            return []
