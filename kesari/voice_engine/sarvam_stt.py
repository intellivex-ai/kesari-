"""
Kesari AI — Sarvam AI Speech-to-Text
Transcribes audio using Sarvam AI's saaras:v3 model.
"""
import io
import logging
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)


class SarvamSTT:
    """Speech-to-Text using Sarvam AI API."""

    def __init__(self, api_key: str, language: str = "hi-IN"):
        self._api_key = api_key
        self._language = language
        self._client = None

    def _ensure_client(self):
        """Lazily create the Sarvam client."""
        if not self._api_key:
            raise ValueError("Sarvam API key not set. Go to Settings → API Keys.")
        try:
            from sarvamai import SarvamAI
            self._client = SarvamAI(api_subscription_key=self._api_key)
        except ImportError:
            raise RuntimeError(
                "sarvamai package not installed. Run: pip install sarvamai"
            )

    async def transcribe(self, wav_bytes: bytes) -> str:
        """
        Transcribe WAV audio bytes to text.
        Returns the transcribed text string.
        """
        self._ensure_client()

        def _sync_transcribe():
            audio_file = io.BytesIO(wav_bytes)
            audio_file.name = "audio.wav"
            response = self._client.speech_to_text.transcribe(
                file=audio_file,
                model="saaras:v3",
                language_code=self._language,
            )
            # Response may be a dict or object
            if hasattr(response, "transcript"):
                return response.transcript
            elif isinstance(response, dict):
                return response.get("transcript", str(response))
            return str(response)

        # Run sync API call in thread pool
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, _sync_transcribe)
        logger.info(f"STT result: {text[:100]}...")
        return text

    def set_language(self, language: str):
        """Update the transcription language."""
        self._language = language

    def update_api_key(self, api_key: str):
        """Update the API key and reset client."""
        self._api_key = api_key
        self._client = None
