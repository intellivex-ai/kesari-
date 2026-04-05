"""
Kesari AI — Audio Player
Plays audio from bytes or files using sounddevice.
"""
import io
import wave
import base64
import logging
import threading
import numpy as np

logger = logging.getLogger(__name__)

_sd = None


def _get_sd():
    global _sd
    if _sd is None:
        try:
            import sounddevice as sd
            _sd = sd
        except (ImportError, OSError) as e:
            logger.error(f"sounddevice not available: {e}")
            raise RuntimeError("Audio playback not available.") from e
    return _sd


class AudioPlayer:
    """Plays audio data with interruption support."""

    def __init__(self):
        self._playing = False
        self._stop_event = threading.Event()
        self._current_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def is_playing(self) -> bool:
        with self._lock:
            return self._playing

    def play_wav_bytes(self, wav_bytes: bytes, on_finished=None):
        """Play WAV audio data in a background thread."""
        self.stop()

        with self._lock:
            self._stop_event.clear()
            self._playing = True
            self._current_thread = threading.Thread(
                target=self._play_worker,
                args=(wav_bytes, on_finished),
                daemon=True,
            )
            self._current_thread.start()

    def play_base64_wav(self, b64_audio: str, on_finished=None):
        """Play base64-encoded WAV audio."""
        wav_bytes = base64.b64decode(b64_audio)
        self.play_wav_bytes(wav_bytes, on_finished)

    def stop(self):
        """Stop current playback."""
        with self._lock:
            if not self._playing:
                return
            self._stop_event.set()
            self._playing = False
        try:
            sd = _get_sd()
            sd.stop()
        except Exception:
            pass

    def _play_worker(self, wav_bytes: bytes, on_finished=None):
        """Worker thread for audio playback."""
        sd = _get_sd()

        try:
            buf = io.BytesIO(wav_bytes)
            with wave.open(buf, "rb") as wf:
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                frames = wf.readframes(wf.getnframes())

            # Convert to numpy array
            if sample_width == 2:
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
            elif sample_width == 4:
                audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483647.0
            else:
                audio = np.frombuffer(frames, dtype=np.uint8).astype(np.float32) / 127.5 - 1.0

            if channels > 1:
                audio = audio.reshape(-1, channels)

            # Play in chunks so we can check for interruption
            chunk_size = sample_rate // 4  # 250ms chunks
            for i in range(0, len(audio), chunk_size):
                if self._stop_event.is_set():
                    logger.info("Audio playback interrupted")
                    break
                chunk = audio[i:i + chunk_size]
                sd.play(chunk, samplerate=sample_rate, blocking=True)

        except Exception as e:
            logger.error(f"Audio playback error: {e}")
        finally:
            should_call_on_finished = False
            with self._lock:
                if self._current_thread == threading.current_thread():
                    self._playing = False
                    should_call_on_finished = not self._stop_event.is_set()
            if on_finished and should_call_on_finished:
                on_finished()
