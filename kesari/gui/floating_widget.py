"""
Kesari AI — Floating Assistant Widget
Compact Spotlight-like floating input for quick commands.
Activated via global hotkey (Ctrl+Space).
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import (
    Qt, Signal, QPropertyAnimation, QEasingCurve, QPoint, QSize,
)
from PySide6.QtGui import QColor, QCursor, QScreen

from kesari.gui.styles import COLORS


class FloatingWidget(QWidget):
    """Compact floating command input (like macOS Spotlight)."""

    command_submitted = Signal(str)
    dismissed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(560, 72)

        # ── Container ───────────────────────────────────
        container = QWidget(self)
        container.setFixedSize(560, 72)
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS["bg_panel"]};
                border: 1px solid {COLORS["border_light"]};
                border-radius: 16px;
            }}
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 120))
        container.setGraphicsEffect(shadow)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 12, 12, 12)
        layout.setSpacing(10)

        # Kesari icon
        icon = QLabel("🦁")
        icon.setStyleSheet("font-size: 22px; background: transparent; border: none;")
        layout.addWidget(icon)

        # Input
        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask Kesari anything...")
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                color: {COLORS["text_primary"]};
                border: none;
                font-size: 16px;
                padding: 4px;
            }}
        """)
        self._input.returnPressed.connect(self._submit)
        layout.addWidget(self._input, stretch=1)

        # Send button
        send_btn = QPushButton("➤")
        send_btn.setFixedSize(36, 36)
        send_btn.setCursor(QCursor(Qt.PointingHandCursor))
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLORS["accent_hover"]};
            }}
        """)
        send_btn.clicked.connect(self._submit)
        layout.addWidget(send_btn)

        # ── Animation ────────────────────────────────────
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(200)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)

    def show_centered(self):
        """Show the widget centered on screen with fade-in."""
        screen = QWidget().screen() if not self.screen() else self.screen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + int(geo.height() * 0.3)
            self.move(x, y)

        self.setWindowOpacity(0)
        self.show()
        self.activateWindow()
        self._input.setFocus()
        self._input.clear()

        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def hide_animated(self):
        """Hide with fade-out."""
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self.hide)
        self._fade_anim.start()

    def _submit(self):
        text = self._input.text().strip()
        if text:
            self.command_submitted.emit(text)
            self._input.clear()
            self.hide_animated()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide_animated()
            self.dismissed.emit()
        super().keyPressEvent(event)
