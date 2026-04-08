"""
Kesari AI — Wake Word Detection
Continuously listens for the wake word using OpenWakeWord.
"""
import logging
import threading
import numpy as np

logger = logging.getLogger(__name__)


class WakeWordDetector:
    def __init__(self, wake_word="hey_jarvis", threshold=0.5, callback=None):
        """
        :param wake_word: Pre-trained wake word model (e.g., 'hey_jarvis', 'alexa')
        :param threshold: Confidence threshold (0.0 to 1.0)
        :param callback: Function to call when wake word is detected
        """
        self.wake_word = wake_word
        self.threshold = threshold
        self.callback = callback
        
        self._running = False
        self._thread = None
        self.oww_model = None

    def start(self):
        if self._running:
            return
            
        try:
            from openwakeword.model import Model
            import sounddevice as sd
        except ImportError as e:
            logger.error(f"Required dependency missing for WakeWordDetector: {e}")
            return

        if self.oww_model is None:
            try:
                # Load the model
                # inference_framework="onnx" is recommended
                self.oww_model = Model(wakeword_models=[self.wake_word], inference_framework="onnx")
                logger.info(f"Loaded wake word model: {self.wake_word}")
            except Exception as e:
                logger.error(f"Failed to load OpenWakeWord model '{self.wake_word}': {e}")
                return

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Wake word detector started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Wake word detector stopped.")

    def _listen_loop(self):
        import sounddevice as sd
        
        # openwakeword requires 16kHz, 1-channel, 16-bit integer audio
        try:
            with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=1280) as stream:
                while self._running:
                    audio_data, overflowed = stream.read(1280)
                    if overflowed:
                        logger.warning("Wake word audio buffer overflow")
                        
                    # Flatten arrays for OWW
                    flat_audio = audio_data.flatten()
                    
                    # Predict
                    prediction = self.oww_model.predict(flat_audio)
                    
                    # Check scores
                    for mdl_name, score in prediction.items():
                        if score > self.threshold:
                            logger.info(f"Wake word detected by model {mdl_name}! Score: {score:.2f}")
                            if self.callback:
                                self.callback()
                            # Reset prediction buffer to prevent multiple rapid triggers
                            self.oww_model.reset()
                            
        except Exception as e:
            logger.error(f"Wake word listening loop error: {e}")
            self._running = False
