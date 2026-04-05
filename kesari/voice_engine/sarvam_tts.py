"""
Kesari AI — Sarvam AI Text-to-Speech
Converts text to speech using Sarvam AI's bulbul:v3 model.
"""
import base64
import logging
import asyncio

logger = logging.getLogger(__name__)


class SarvamTTS:
    """Text-to-Speech using Sarvam AI API."""

    def __init__(
        self,
        api_key: str,
        language: str = "hi-IN",
        speaker: str = "meera",
    ):
        self._api_key = api_key
        self._language = language
        self._speaker = speaker
        self._client = None

    def _ensure_client(self):
        """Lazily create the Sarvam client."""
        if self._client is not None:
            return
        if not self._api_key:
            raise ValueError("Sarvam API key not set. Go to Settings → API Keys.")
        try:
            from sarvamai import SarvamAI
            self._client = SarvamAI(api_subscription_key=self._api_key)
        except ImportError:
            raise RuntimeError(
                "sarvamai package not installed. Run: pip install sarvamai"
            )

    async def synthesize(self, text: str) -> bytes:
        """
        Convert text to speech.
        Returns WAV audio bytes.
        """
        if not text.strip():
            return b""

        self._ensure_client()

        def _sync_synthesize():
            response = self._client.text_to_speech.synthesize(
                text=text,
                target_language_code=self._language,
                speaker=self._speaker,
                model="bulbul:v3",
            )

            # Extract audio content
            audio_b64 = None
            if hasattr(response, "audio_content"):
                audio_b64 = response.audio_content
            elif isinstance(response, dict):
                audios = response.get("audios")
                if audios and isinstance(audios, list):
                    audio_b64 = audios[0]
                else:
                    audio_b64 = response.get("audio_content")

            if audio_b64:
                return base64.b64decode(audio_b64)

            # If response has raw bytes
            if isinstance(response, bytes):
                return response

            logger.warning(f"Unexpected TTS response format: {type(response)}")
            return b""

        loop = asyncio.get_running_loop()
        audio_bytes = await loop.run_in_executor(None, _sync_synthesize)
        logger.info(f"TTS generated {len(audio_bytes)} bytes")
        return audio_bytes

    def set_language(self, language: str):
        self._language = language

    def set_speaker(self, speaker: str):
        self._speaker = speaker

    def update_api_key(self, api_key: str):
        self._api_key = api_key
        self._client = None
