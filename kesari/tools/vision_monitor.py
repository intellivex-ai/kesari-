"""
Kesari AI — Vision Monitor
Continuously captures background screen context without requiring
manual tool calls so that Kesari can "see" what you are pointing to.
"""
import base64
import io
import logging
import threading
import time
from typing import Optional

from PIL import Image

try:
    import mss
except ImportError:
    mss = None

logger = logging.getLogger(__name__)

class VisionMonitor:
    def __init__(self, interval_seconds: int = 10, max_size: tuple[int, int] = (800, 800)):
        self.interval = interval_seconds
        self.max_size = max_size
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_frame_b64: Optional[str] = None
        self._lock = threading.Lock()

    def start(self):
        if not mss:
            logger.warning("mss not installed. VisionMonitor is disabled.")
            return

        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="VisionMonitor")
        self._thread.start()
        logger.info(f"VisionMonitor started (interval={self.interval}s)")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def get_latest_frame(self) -> Optional[str]:
        with self._lock:
            return self._latest_frame_b64

    def _monitor_loop(self):
        with mss.mss() as sct:
            while self._running:
                try:
                    # Capture the primary monitor
                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)
                    
                    # Convert to PIL Image
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    
                    # Resize to prevent exploding API costs and latency
                    img.thumbnail(self.max_size, Image.Resampling.LANCZOS)
                    
                    # Convert to Base64 JPEG
                    buffered = io.BytesIO()
                    img.save(buffered, format="JPEG", quality=75)
                    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                    
                    with self._lock:
                        self._latest_frame_b64 = img_str

                except Exception as e:
                    logger.debug(f"VisionMonitor capture error: {e}")
                
                # Sleep in increments so stopping is fast
                for _ in range(self.interval):
                    if not self._running:
                        break
                    time.sleep(1.0)

# Global unified vision monitor instance
_global_monitor: Optional[VisionMonitor] = None

def start_vision_monitor(interval: int = 10):
    global _global_monitor
    if not _global_monitor:
        _global_monitor = VisionMonitor(interval_seconds=interval)
        _global_monitor.start()

def get_vision_context() -> Optional[str]:
    if _global_monitor:
        return _global_monitor.get_latest_frame()
    return None
