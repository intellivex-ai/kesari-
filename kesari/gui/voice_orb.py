"""
Kesari AI — Voice Orb Widget
Animated circular orb that visualizes voice interaction states.
"""
import math
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    Property, QRect, QPoint,
)
from PySide6.QtGui import (
    QPainter, QRadialGradient, QColor, QPen,
    QBrush, QPainterPath, QLinearGradient,
)


class VoiceOrb(QWidget):
    """
    Animated orb for voice visualization.
    States: idle, listening, speaking, processing.
    """

    def __init__(self, size: int = 56, parent=None):
        super().__init__(parent)
        self._size = size
        self._state = "idle"  # idle | listening | speaking | processing
        self._pulse = 0.0
        self._wave_phase = 0.0
        self._ring_opacity = 0.0
        self._audio_level = 0.0  # 0.0 to 1.0

        self.setFixedSize(size + 20, size + 20)  # Extra space for glow
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # ── Animation Timer ──────────────────────────────
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)  # ~33 fps

        # ── Colors ───────────────────────────────────────
        self._color_idle = QColor("#FF6B35")
        self._color_listening = QColor("#FF8555")
        self._color_speaking = QColor("#F7931E")
        self._color_processing = QColor("#FF6B35")

    # ── Public API ────────────────────────────────────────

    def set_state(self, state: str):
        """Set orb state: 'idle', 'listening', 'speaking', 'processing'."""
        self._state = state
        self.update()

    def set_audio_level(self, level: float):
        """Set current audio input level (0.0 - 1.0)."""
        self._audio_level = max(0.0, min(1.0, level))

    @property
    def state(self) -> str:
        return self._state

    # ── Animation Loop ────────────────────────────────────

    def _tick(self):
        self._wave_phase += 0.08
        if self._state == "idle":
            self._pulse = 0.5 + 0.5 * math.sin(self._wave_phase * 0.5)
            self._ring_opacity = 0.1 + 0.05 * math.sin(self._wave_phase * 0.3)
        elif self._state == "listening":
            # Responsive to audio level
            target = 0.3 + 0.7 * self._audio_level
            self._pulse += (target - self._pulse) * 0.15
            self._ring_opacity = 0.3 + 0.4 * self._audio_level
        elif self._state == "speaking":
            self._pulse = 0.6 + 0.4 * math.sin(self._wave_phase * 1.5)
            self._ring_opacity = 0.2 + 0.3 * abs(math.sin(self._wave_phase))
        elif self._state == "processing":
            self._pulse = 0.5 + 0.5 * abs(math.sin(self._wave_phase * 2.0))
            self._ring_opacity = 0.15 + 0.15 * math.sin(self._wave_phase * 3.0)
        self.update()

    # ── Painting ──────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        cx = self.width() / 2
        cy = self.height() / 2
        base_r = self._size / 2

        # ── Outer glow ────────────────────────────────────
        glow_r = base_r + 10 * self._pulse
        glow_grad = QRadialGradient(cx, cy, glow_r)
        glow_color = self._current_color()
        glow_grad.setColorAt(0.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), int(60 * self._ring_opacity)))
        glow_grad.setColorAt(0.6, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), int(20 * self._ring_opacity)))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(int(cx), int(cy)), int(glow_r), int(glow_r))

        # ── Outer ring ────────────────────────────────────
        if self._state in ("listening", "speaking"):
            ring_r = base_r + 4 + 6 * self._pulse
            ring_pen = QPen(
                QColor(
                    glow_color.red(),
                    glow_color.green(),
                    glow_color.blue(),
                    int(100 * self._ring_opacity),
                ),
                1.5,
            )
            painter.setPen(ring_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPoint(int(cx), int(cy)), int(ring_r), int(ring_r))

        # ── Main orb ─────────────────────────────────────
        orb_r = base_r - 2 + 2 * self._pulse
        orb_grad = QRadialGradient(cx - orb_r * 0.3, cy - orb_r * 0.3, orb_r * 1.6)
        orb_grad.setColorAt(0.0, self._lighter(glow_color, 40))
        orb_grad.setColorAt(0.5, glow_color)
        orb_grad.setColorAt(1.0, self._darker(glow_color, 60))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(orb_grad))
        painter.drawEllipse(QPoint(int(cx), int(cy)), int(orb_r), int(orb_r))

        # ── Inner highlight ───────────────────────────────
        highlight_grad = QRadialGradient(cx - orb_r * 0.2, cy - orb_r * 0.35, orb_r * 0.5)
        highlight_grad.setColorAt(0.0, QColor(255, 255, 255, 45))
        highlight_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(highlight_grad))
        painter.drawEllipse(QPoint(int(cx), int(cy)), int(orb_r), int(orb_r))

        # ── Wave bars (speaking state) ────────────────────
        if self._state == "speaking":
            bar_count = 5
            bar_w = 3
            for i in range(bar_count):
                h = 8 + 12 * abs(math.sin(self._wave_phase + i * 0.8))
                bx = cx + (i - bar_count // 2) * 7
                by = cy - h / 2
                painter.setBrush(QColor(255, 255, 255, 180))
                painter.drawRoundedRect(int(bx), int(by), bar_w, int(h), 1.5, 1.5)

        # ── Processing spinner dots ───────────────────────
        if self._state == "processing":
            dot_count = 3
            for i in range(dot_count):
                angle = self._wave_phase * 3 + i * (2 * math.pi / dot_count)
                dx = cx + math.cos(angle) * (orb_r * 0.45)
                dy = cy + math.sin(angle) * (orb_r * 0.45)
                painter.setBrush(QColor(255, 255, 255, 200))
                painter.drawEllipse(QPoint(int(dx), int(dy)), 3, 3)

        painter.end()

    # ── Helpers ───────────────────────────────────────────

    def _current_color(self) -> QColor:
        return {
            "idle": self._color_idle,
            "listening": self._color_listening,
            "speaking": self._color_speaking,
            "processing": self._color_processing,
        }.get(self._state, self._color_idle)

    @staticmethod
    def _lighter(color: QColor, amount: int) -> QColor:
        return QColor(
            min(255, color.red() + amount),
            min(255, color.green() + amount),
            min(255, color.blue() + amount),
            color.alpha(),
        )

    @staticmethod
    def _darker(color: QColor, amount: int) -> QColor:
        return QColor(
            max(0, color.red() - amount),
            max(0, color.green() - amount),
            max(0, color.blue() - amount),
            color.alpha(),
        )
