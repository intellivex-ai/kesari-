"""
Kesari AI — Configuration Manager
Loads environment variables and manages app settings.
"""
import os
import json
import logging
import keyring
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
load_dotenv(_ENV_PATH)

SECRET_KEYS = {"sarvam_api_key", "nvidia_api_key"}

# ─── Directories ──────────────────────────────────────────────
APP_DIR = Path.home() / ".kesari_ai"
APP_DIR.mkdir(exist_ok=True)
CONFIG_FILE = APP_DIR / "settings.json"
DB_FILE = APP_DIR / "memory.db"
VECTOR_DB_DIR = APP_DIR / "vector_memory"

# ─── API Keys ────────────────────────────────────────────────
NVIDIA_API_KEY: str     = os.getenv("NVIDIA_API_KEY", "")
SARVAM_API_KEY: str     = os.getenv("SARVAM_API_KEY", "")

# ─── Defaults ─────────────────────────────────────────────────
DEFAULT_MODEL: str      = os.getenv("DEFAULT_MODEL", "meta/llama-3.3-70b-instruct")
NVIDIA_BASE_URL         = "https://integrate.api.nvidia.com/v1"
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
        "sarvam_api_key": "",
        "llm_provider": "custom_kesari",
        "tts_language": DEFAULT_TTS_LANGUAGE,
        "tts_speaker": DEFAULT_TTS_SPEAKER,
        "stt_language": DEFAULT_STT_LANGUAGE,
        "theme": "dark",
        "confirm_dangerous_actions": True,
        "floating_hotkey": "ctrl+space",
        "wake_word_enabled": False,
        "wake_word_model": "hey_jarvis",
        "enable_proactive_monitoring": True,
        "monitoring_interval": 60,
        "cpu_threshold": 85,
        "ram_threshold": 90,
        "disk_threshold": 95,
        "enable_companion_api": True,
        "companion_api_port": 8765,
        "enable_ngrok": os.getenv("ENABLE_NGROK", "False").lower() == "true",
        "ngrok_auth_token": os.getenv("NGROK_AUTH_TOKEN", ""),
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
        
        # Merge with defaults, but skip secrets in JSON logic initially
        for key, default in self._defaults.items():
            if key in SECRET_KEYS:
                try:
                    kr_val = keyring.get_password("KesariAI", key)
                    if kr_val:
                        self._data[key] = kr_val
                    elif key in self._data and self._data[key]:
                        # Migrate plaintext to keyring
                        val = self._data[key]
                        keyring.set_password("KesariAI", key, val)
                        self._data[key] = val
                    else:
                        self._data.setdefault(key, default)
                except Exception as e:
                    logger.warning(f"Failed to read {key} from keyring: {e}")
                    self._data.setdefault(key, default)
            else:
                self._data.setdefault(key, default)

        # Remove secrets from being accidentally serialized back later
        # (Though our save() method handles this, it's good safety to clean up old plaintexts in file)
        if any(k in self._data for k in SECRET_KEYS) and CONFIG_FILE.exists():
            try:
                # Re-save immediately to remove plaintexts from file
                self._save_to_disk()
            except Exception:
                pass

        # Override with env vars if present
        if NVIDIA_API_KEY:
            self._data["nvidia_api_key"] = NVIDIA_API_KEY
        if SARVAM_API_KEY:
            self._data["sarvam_api_key"] = SARVAM_API_KEY
        if os.getenv("LLM_PROVIDER"):
            self._data["llm_provider"] = os.getenv("LLM_PROVIDER")

    def save(self):
        """Save settings, persisting secrets to keyring and non-secrets to JSON."""
        # Handle secret keys
        for key in SECRET_KEYS:
            if key in self._data:
                try:
                    val = self._data[key]
                    if val:
                        keyring.set_password("KesariAI", key, val)
                    else:
                        try:
                            keyring.delete_password("KesariAI", key)
                        except keyring.errors.PasswordDeleteError:
                            pass
                except Exception as e:
                    logger.warning(f"Failed to write {key} to keyring: {e}")
        
        self._save_to_disk()

    def _save_to_disk(self):
        """Internal method to write non-secrets to JSON."""
        persistent_data = {k: v for k, v in self._data.items() if k not in SECRET_KEYS}
        CONFIG_FILE.write_text(
            json.dumps(persistent_data, indent=2, ensure_ascii=False),
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
