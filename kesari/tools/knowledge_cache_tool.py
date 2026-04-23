"""
Kesari AI — Knowledge Cache Tool
SQLite-backed TTL cache for web search results, news, and real-time data.
Prevents redundant network calls and speeds up repeated queries.
"""
import sqlite3
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── TTL Tiers (seconds) ───────────────────────────────────
TTL_SHORT  = 300       # 5 min  — live news, stocks, crypto
TTL_MEDIUM = 3_600     # 1 hr   — weather, general facts
TTL_LONG   = 86_400    # 24 hrs — Wikipedia, stable reference
TTL_NEVER  = 0         # No expiry — user-trained facts


def _cache_db_path() -> Path:
    """Use the existing Kesari app dir for the cache database."""
    from kesari.config import APP_DIR
    return APP_DIR / "knowledge_cache.db"


class KnowledgeCache:
    """Thread-safe, TTL-aware SQLite cache for knowledge results."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or str(_cache_db_path())
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_cache (
                    key        TEXT PRIMARY KEY,
                    query_text TEXT NOT NULL,
                    result     TEXT NOT NULL,
                    intent     TEXT DEFAULT 'general',
                    source     TEXT DEFAULT 'unknown',
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    hit_count  INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON knowledge_cache(expires_at)
            """)
        logger.info(f"KnowledgeCache initialized at {self._db_path}")

    @staticmethod
    def _make_key(query: str) -> str:
        """Normalize query to a stable cache key."""
        normalized = query.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    def get(self, query: str) -> Optional[dict]:
        """Return cached result if it exists and hasn't expired."""
        key = self._make_key(query)
        now = time.time()
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM knowledge_cache WHERE key=? AND expires_at > ?",
                    (key, now)
                ).fetchone()
                if row:
                    # Increment hit count
                    conn.execute(
                        "UPDATE knowledge_cache SET hit_count=hit_count+1 WHERE key=?",
                        (key,)
                    )
                    result = json.loads(row["result"])
                    logger.debug(f"Cache HIT for: {query[:60]!r} (hits={row['hit_count']+1})")
                    return result
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None

    def set(
        self,
        query: str,
        result: Any,
        ttl: int = TTL_MEDIUM,
        intent: str = "general",
        source: str = "unknown",
    ):
        """Store a result with a TTL."""
        key = self._make_key(query)
        now = time.time()
        expires_at = now + ttl if ttl > 0 else float("inf")
        try:
            with self._connect() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO knowledge_cache
                    (key, query_text, result, intent, source, created_at, expires_at, hit_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """, (key, query, json.dumps(result, ensure_ascii=False), intent, source, now, expires_at))
            logger.debug(f"Cache SET for: {query[:60]!r} (ttl={ttl}s)")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    def invalidate(self, query: str):
        """Remove a specific cached entry."""
        key = self._make_key(query)
        try:
            with self._connect() as conn:
                conn.execute("DELETE FROM knowledge_cache WHERE key=?", (key,))
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")

    def purge_expired(self) -> int:
        """Remove all expired entries. Returns count of removed rows."""
        now = time.time()
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "DELETE FROM knowledge_cache WHERE expires_at <= ?", (now,)
                )
                count = cur.rowcount
            if count:
                logger.info(f"Cache: purged {count} expired entries")
            return count
        except Exception as e:
            logger.warning(f"Cache purge error: {e}")
            return 0

    def stats(self) -> dict:
        """Return cache statistics."""
        now = time.time()
        try:
            with self._connect() as conn:
                total = conn.execute("SELECT COUNT(*) FROM knowledge_cache").fetchone()[0]
                active = conn.execute(
                    "SELECT COUNT(*) FROM knowledge_cache WHERE expires_at > ?", (now,)
                ).fetchone()[0]
                total_hits = conn.execute(
                    "SELECT COALESCE(SUM(hit_count), 0) FROM knowledge_cache"
                ).fetchone()[0]
            return {"total": total, "active": active, "expired": total - active, "total_hits": total_hits}
        except Exception:
            return {"total": 0, "active": 0, "expired": 0, "total_hits": 0}

    def list_recent(self, limit: int = 20) -> list[dict]:
        """Return the most recent cached queries."""
        try:
            with self._connect() as conn:
                rows = conn.execute("""
                    SELECT query_text, intent, source, created_at, hit_count
                    FROM knowledge_cache
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,)).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []


# ── Singleton ─────────────────────────────────────────────
_cache_instance: Optional[KnowledgeCache] = None


def get_cache() -> KnowledgeCache:
    """Return the global cache singleton."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = KnowledgeCache()
    return _cache_instance
