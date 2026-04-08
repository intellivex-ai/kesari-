"""
Kesari AI — System Monitor
Background daemon that watches CPU, RAM, and disk usage.
Emits a signal when thresholds are exceeded so Kesari can proactively warn the user.
"""
import logging
import threading
import time
from typing import Callable

import psutil

logger = logging.getLogger(__name__)

# Default thresholds
CPU_THRESHOLD = 85      # %
RAM_THRESHOLD = 90      # %
DISK_THRESHOLD = 95     # %


class SystemMonitor:
    """
    Polls system resources every `interval` seconds in a daemon thread.
    When a threshold is breached, `on_alert(metric, value, threshold)` is called
    from the background thread — callers must marshal to the Qt thread if needed.
    """

    def __init__(
        self,
        on_alert: Callable[[str, float, float], None],
        interval: int = 60,
        cpu_threshold: float = CPU_THRESHOLD,
        ram_threshold: float = RAM_THRESHOLD,
        disk_threshold: float = DISK_THRESHOLD,
    ):
        self.on_alert = on_alert
        self.interval = interval
        self.cpu_threshold = cpu_threshold
        self.ram_threshold = ram_threshold
        self.disk_threshold = disk_threshold
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        # Track last alert time per metric to avoid spam (min 5 min cooldown)
        self._last_alert: dict[str, float] = {}
        self._cooldown = 300  # seconds

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="SystemMonitor")
        self._thread.start()
        logger.info(f"SystemMonitor started (interval={self.interval}s)")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("SystemMonitor stopped")

    def get_snapshot(self) -> dict:
        """Return current system resource values synchronously."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "ram_percent": psutil.virtual_memory().percent,
            "ram_used_gb": round(psutil.virtual_memory().used / (1024 ** 3), 2),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
            "disk_percent": psutil.disk_usage("/").percent,
        }

    def _should_alert(self, metric: str) -> bool:
        now = time.time()
        last = self._last_alert.get(metric, 0)
        if now - last >= self._cooldown:
            self._last_alert[metric] = now
            return True
        return False

    def _run(self):
        while not self._stop_event.wait(self.interval):
            try:
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage("/").percent

                if cpu > self.cpu_threshold and self._should_alert("cpu"):
                    logger.warning(f"CPU alert: {cpu}%")
                    self.on_alert("CPU", cpu, self.cpu_threshold)

                if ram > self.ram_threshold and self._should_alert("ram"):
                    logger.warning(f"RAM alert: {ram}%")
                    self.on_alert("RAM", ram, self.ram_threshold)

                if disk > self.disk_threshold and self._should_alert("disk"):
                    logger.warning(f"Disk alert: {disk}%")
                    self.on_alert("Disk", disk, self.disk_threshold)

            except Exception as e:
                logger.error(f"SystemMonitor error: {e}")
