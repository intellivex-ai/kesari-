"""
Kesari AI — Configuration Manager
Loads environment variables and manages app settings.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
load_dotenv(_ENV_PATH)

# ─── Directories ──────────────────────────────────────────────
APP_DIR = Path.home() / ".kesari_ai"
APP_DIR.mkdir(exist_ok=True)
CONFIG_FILE = APP_DIR / "settings.json"
DB_FILE = APP_DIR / "memory.db"

# ─── API Keys ────────────────────────────────────────────────
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")

# ─── Defaults ─────────────────────────────────────────────────
DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "openai/gpt-4o")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
APP_NAME = "Kesari AI"
APP_VERSION = "1.0.0"
MAX_CONTEXT_MESSAGES = 20  # Sliding window for conversation

# ─── Voice Defaults ──────────────────────────────────────────
DEFAULT_TTS_LANGUAGE = "hi-IN"
DEFAULT_TTS_SPEAKER = "meera"
DEFAULT_STT_LANGUAGE = "hi-IN"
DEFAULT_SAMPLE_RATE = 22050

# ─── UI Constants ─────────────────────────────────────────────
WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 650
SIDEBAR_WIDTH = 260


class Settings:
    """Persistent user settings backed by a JSON file."""

    _defaults = {
        "openrouter_api_key": "",
        "sarvam_api_key": "",
        "default_model": DEFAULT_MODEL,
        "tts_language": DEFAULT_TTS_LANGUAGE,
        "tts_speaker": DEFAULT_TTS_SPEAKER,
        "stt_language": DEFAULT_STT_LANGUAGE,
        "theme": "dark",
        "confirm_dangerous_actions": True,
        "floating_hotkey": "ctrl+space",
    }

    def __init__(self):
        self._data: dict = {}
        self._load()

    # ── persistence ─────────────────────────────────────────
    def _load(self):
        if CONFIG_FILE.exists():
            try:
                self._data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        # Merge with defaults (keep user overrides)
        for key, default in self._defaults.items():
            self._data.setdefault(key, default)
        # Override with env vars if present
        if OPENROUTER_API_KEY:
            self._data["openrouter_api_key"] = OPENROUTER_API_KEY
        if SARVAM_API_KEY:
            self._data["sarvam_api_key"] = SARVAM_API_KEY

    def save(self):
        CONFIG_FILE.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── access ──────────────────────────────────────────────
    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    def __getitem__(self, key: str):
        return self._data[key]

    def __setitem__(self, key: str, value):
        self.set(key, value)


# Singleton instance
settings = Settings()
