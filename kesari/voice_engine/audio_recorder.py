"""
Kesari AI — Audio Recorder
Microphone capture with push-to-talk support.
"""
import io
import wave
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Lazy import sounddevice — may not be available on all systems
_sd = None


def _get_sd():
    global _sd
    if _sd is None:
        try:
            import sounddevice as sd
            _sd = sd
        except (ImportError, OSError) as e:
            logger.error(f"sounddevice not available: {e}")
            raise RuntimeError(
                "Audio recording not available. Install 'sounddevice' and ensure "
                "a microphone is connected."
            ) from e
    return _sd


class AudioRecorder:
    """Records audio from the microphone and returns WAV bytes."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._recording = False
        self._frames: list[np.ndarray] = []
        self._stream = None
        self._audio_level: float = 0.0

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def audio_level(self) -> float:
        """Current audio input level (0.0 - 1.0)."""
        return self._audio_level

    def start(self):
        """Start recording from the microphone."""
        if self._recording:
            return

        sd = _get_sd()
        self._frames.clear()
        self._recording = True

        def callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"Audio recording status: {status}")
            if self._recording:
                self._frames.append(indata.copy())
                # Calculate RMS level
                rms = float(np.sqrt(np.mean(indata**2)))
                self._audio_level = min(1.0, rms * 10)  # Scale up

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                callback=callback,
                blocksize=1024,
            )
            self._stream.start()
            logger.info("Audio recording started")
        except Exception as e:
            self._recording = False
            logger.error(f"Failed to start recording: {e}")
            raise

    def stop(self) -> bytes:
        """Stop recording and return WAV bytes."""
        self._recording = False
        self._audio_level = 0.0

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if not self._frames:
            return b""

        # Concatenate all frames
        audio_data = np.concatenate(self._frames, axis=0)
        self._frames.clear()

        # Convert float32 to int16
        audio_int16 = (audio_data * 32767).astype(np.int16)

        # Write to WAV buffer
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())

        logger.info(f"Recording stopped: {len(audio_int16)} samples")
        return buf.getvalue()
