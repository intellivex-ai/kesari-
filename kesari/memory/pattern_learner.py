"""
Kesari AI — Pattern Learner
Logs active applications to a SQLite database and predicts user habits.
"""
import logging
import sqlite3
import os
from datetime import datetime
from kesari.automation.context_awareness import get_active_window_info

logger = logging.getLogger(__name__)

DB_PATH = os.path.expanduser("~/.kesari_ai/patterns.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

class PatternLearner:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    app_name TEXT,
                    window_title TEXT,
                    day_of_week INTEGER,
                    hour_of_day INTEGER
                )
            ''')
            conn.commit()

    def log_active_app(self):
        """Called periodically (e.g. every 5 mins) to log what the user is doing."""
        info = get_active_window_info()
        app_name = info.get("app_name")
        window_title = info.get("window_title")
        
        if not app_name or app_name == "Unknown":
            return
            
        now = datetime.now()
        day_of_week = now.weekday()
        hour_of_day = now.hour
        
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO app_usage_log (app_name, window_title, day_of_week, hour_of_day)
                    VALUES (?, ?, ?, ?)
                ''', (app_name, window_title, day_of_week, hour_of_day))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log app usage: {e}")

    def predict_likely_app(self, day_of_week: int, hour_of_day: int, min_samples: int = 5) -> str:
        """
        Returns the most common app for a given hour/day if it exceeds the minimum sample threshold.
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                # Get the most frequent app for this hour and day
                cursor.execute('''
                    SELECT app_name, COUNT(*) as c
                    FROM app_usage_log
                    WHERE day_of_week = ? AND hour_of_day = ?
                    GROUP BY app_name
                    ORDER BY c DESC
                    LIMIT 1
                ''', (day_of_week, hour_of_day))
                row = cursor.fetchone()
                
                if row and row[1] >= min_samples:
                    return row[0]
        except Exception as e:
            logger.error(f"Failed to predict app: {e}")
            
        return None
