"""
Kesari AI — Main Window
Primary application window with sidebar, chat area, and input bar.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QSizePolicy,
    QSystemTrayIcon, QMenu, QApplication, QFrame,
    QSpacerItem, QTextEdit,
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QEvent, QTimer
from PySide6.QtGui import QIcon, QFont, QCursor, QAction, QKeyEvent

from kesari.config import (
    APP_NAME, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, SIDEBAR_WIDTH, settings,
)
from kesari.gui.styles import (
    COLORS, SIDEBAR_BUTTON_STYLE, SEND_BUTTON_STYLE,
    VOICE_BUTTON_STYLE, NEW_CHAT_BUTTON_STYLE,
)
from kesari.gui.chat_widget import ChatWidget
from kesari.gui.voice_orb import VoiceOrb


class _TitleBar(QWidget):
    """Custom frameless title bar with drag support."""

    close_clicked = Signal()
    minimize_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(44)
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(8)

        # App icon + name
        icon_lbl = QLabel("🦁")
        icon_lbl.setStyleSheet("font-size: 18px;")
        title_lbl = QLabel(APP_NAME)
        title_lbl.setObjectName("titleLabel")
        title_lbl.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLORS['text_primary']};")

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        layout.addStretch()

        # Window controls
        for text, slot, color in [
            ("─", "minimize", COLORS["text_muted"]),
            ("✕", "close", COLORS["error"]),
        ]:
            btn = QPushButton(text)
            btn.setFixedSize(32, 32)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {COLORS["text_muted"]};
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background: {COLORS["bg_hover"]};
                    color: {color};
                }}
            """)
            if slot == "minimize":
                btn.clicked.connect(self.minimize_clicked)
            else:
                btn.clicked.connect(self.close_clicked)
            layout.addWidget(btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


class _ChatInput(QWidget):
    """Input bar with text field, send button, and voice button."""

    message_submitted = Signal(str)
    voice_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("inputBar")
        self.setFixedHeight(72)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(8)

        # Voice button
        self._voice_btn = QPushButton("🎤")
        self._voice_btn.setCheckable(True)
        self._voice_btn.setToolTip("Push to talk (hold)")
        self._voice_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._voice_btn.setStyleSheet(VOICE_BUTTON_STYLE)
        self._voice_btn.pressed.connect(lambda: self.voice_toggled.emit(True))
        self._voice_btn.released.connect(lambda: self.voice_toggled.emit(False))
        layout.addWidget(self._voice_btn)

        # Text input
        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask Kesari anything...")
        self._input.setFixedHeight(42)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS["bg_input"]};
                color: {COLORS["text_primary"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 12px;
                padding: 0 14px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS["accent"]};
            }}
        """)
        self._input.returnPressed.connect(self._on_submit)
        layout.addWidget(self._input)

        # Send button
        self._send_btn = QPushButton("➤")
        self._send_btn.setToolTip("Send message")
        self._send_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._send_btn.setStyleSheet(SEND_BUTTON_STYLE)
        self._send_btn.clicked.connect(self._on_submit)
        layout.addWidget(self._send_btn)

    def _on_submit(self):
        text = self._input.text().strip()
        if text:
            self.message_submitted.emit(text)
            self._input.clear()

    def set_enabled(self, enabled: bool):
        self._input.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)

    def focus_input(self):
        self._input.setFocus()


class _Sidebar(QWidget):
    """Left sidebar with new chat, history, and settings."""

    new_chat_clicked = Signal()
    settings_clicked = Signal()
    analytics_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)

        # ── New Chat Button ──────────────────────────────
        new_chat = QPushButton("✦  New Chat")
        new_chat.setCursor(QCursor(Qt.PointingHandCursor))
        new_chat.setStyleSheet(NEW_CHAT_BUTTON_STYLE)
        new_chat.clicked.connect(self.new_chat_clicked)
        layout.addWidget(new_chat)

        layout.addSpacing(8)

        # ── History label ────────────────────────────────
        history_lbl = QLabel("RECENT")
        history_lbl.setObjectName("mutedLabel")
        history_lbl.setStyleSheet(f"""
            color: {COLORS["text_muted"]};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
            padding: 4px 8px;
        """)
        layout.addWidget(history_lbl)

        # ── History items container ──────────────────────
        self._history_layout = QVBoxLayout()
        self._history_layout.setSpacing(2)
        layout.addLayout(self._history_layout)

        layout.addStretch()

        # ── Separator ────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']}; max-height: 1px;")
        layout.addWidget(sep)

        layout.addSpacing(4)

        # ── Voice Orb ────────────────────────────────────
        orb_container = QHBoxLayout()
        orb_container.setAlignment(Qt.AlignCenter)
        self.voice_orb = VoiceOrb(size=44)
        orb_container.addWidget(self.voice_orb)
        layout.addLayout(orb_container)

        layout.addSpacing(8)

        # ── Settings Button ──────────────────────────────
        settings_btn = QPushButton("⚙  Settings")
        settings_btn.setCursor(QCursor(Qt.PointingHandCursor))
        settings_btn.setStyleSheet(SIDEBAR_BUTTON_STYLE)
        settings_btn.clicked.connect(self.settings_clicked)
        layout.addWidget(settings_btn)

        # ── Analytics Button ────────────────────────────
        analytics_btn = QPushButton("📊  Analytics")
        analytics_btn.setCursor(QCursor(Qt.PointingHandCursor))
        analytics_btn.setStyleSheet(SIDEBAR_BUTTON_STYLE)
        analytics_btn.clicked.connect(self.analytics_clicked)
        layout.addWidget(analytics_btn)

    def add_history_item(self, title: str, on_click=None):
        """Add a conversation history item."""
        btn = QPushButton(f"  💬  {title}")
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setStyleSheet(SIDEBAR_BUTTON_STYLE)
        if on_click:
            btn.clicked.connect(on_click)
        self._history_layout.addWidget(btn)

    def clear_history(self):
        """Clear all history items."""
        while self._history_layout.count():
            item = self._history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class MainWindow(QMainWindow):
    """
    Primary application window.
    Layout: [Sidebar | Chat Area + Input Bar]
    """

    user_message = Signal(str)          # User sent a text message
    voice_toggle = Signal(bool)         # Voice button pressed/released
    new_chat_requested = Signal()       # New chat clicked
    settings_requested = Signal()       # Settings clicked
    analytics_requested = Signal()      # Analytics clicked
    hidden_to_tray = Signal()           # Window closed to tray

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(1050, 720)

        # Frameless window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # ── Central Widget ───────────────────────────────
        central = QWidget()
        central.setStyleSheet(f"background-color: {COLORS['bg_darkest']}; border-radius: 12px;")
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Title Bar ────────────────────────────────────
        self._title_bar = _TitleBar()
        self._title_bar.close_clicked.connect(self.close)
        self._title_bar.minimize_clicked.connect(self.showMinimized)
        root_layout.addWidget(self._title_bar)

        # ── Body ─────────────────────────────────────────
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Sidebar
        self._sidebar = _Sidebar()
        self._sidebar.new_chat_clicked.connect(self.new_chat_requested)
        self._sidebar.settings_clicked.connect(self.settings_requested)
        self._sidebar.analytics_clicked.connect(self.analytics_requested)
        body_layout.addWidget(self._sidebar)

        # Chat area + input
        chat_panel = QWidget()
        chat_layout = QVBoxLayout(chat_panel)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        self.chat_widget = ChatWidget()
        chat_layout.addWidget(self.chat_widget, stretch=1)

        self._chat_input = _ChatInput()
        self._chat_input.message_submitted.connect(self.user_message)
        self._chat_input.voice_toggled.connect(self.voice_toggle)
        chat_layout.addWidget(self._chat_input)

        body_layout.addWidget(chat_panel, stretch=1)
        root_layout.addWidget(body, stretch=1)

        # ── Resize grip support ──────────────────────────
        self._resize_margin = 6
        self._resize_dragging = False
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geom = None
        self.setMouseTracking(True)
        central.setMouseTracking(True)

    # ── Public API ────────────────────────────────────────

    @property
    def voice_orb(self) -> VoiceOrb:
        return self._sidebar.voice_orb

    def set_input_enabled(self, enabled: bool):
        self._chat_input.set_enabled(enabled)

    def focus_input(self):
        self._chat_input.focus_input()

    def add_history_item(self, title: str, on_click=None):
        self._sidebar.add_history_item(title, on_click)

    # ── Window resize from edges ──────────────────────────

    def _edge_at(self, pos: QPoint):
        rect = self.rect()
        m = self._resize_margin
        edges = []
        if pos.x() <= m:
            edges.append("left")
        elif pos.x() >= rect.width() - m:
            edges.append("right")
        if pos.y() <= m:
            edges.append("top")
        elif pos.y() >= rect.height() - m:
            edges.append("bottom")
        return tuple(edges) if edges else None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self._edge_at(event.position().toPoint())
            if edge:
                self._resize_dragging = True
                self._resize_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geom = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resize_dragging and self._resize_edge:
            diff = event.globalPosition().toPoint() - self._resize_start_pos
            geom = self._resize_start_geom
            new_geom = geom.adjusted(0, 0, 0, 0)
            if "right" in self._resize_edge:
                new_geom.setWidth(max(self.minimumWidth(), geom.width() + diff.x()))
            if "bottom" in self._resize_edge:
                new_geom.setHeight(max(self.minimumHeight(), geom.height() + diff.y()))
            if "left" in self._resize_edge:
                new_geom.setLeft(min(geom.right() - self.minimumWidth(), geom.left() + diff.x()))
            if "top" in self._resize_edge:
                new_geom.setTop(min(geom.bottom() - self.minimumHeight(), geom.top() + diff.y()))
            self.setGeometry(new_geom)
            event.accept()
            return
        # Cursor shape
        edge = self._edge_at(event.position().toPoint())
        if edge:
            if set(edge) == {"left", "top"} or set(edge) == {"right", "bottom"}:
                self.setCursor(Qt.SizeFDiagCursor)
            elif set(edge) == {"right", "top"} or set(edge) == {"left", "bottom"}:
                self.setCursor(Qt.SizeBDiagCursor)
            elif "left" in edge or "right" in edge:
                self.setCursor(Qt.SizeHorCursor)
            else:
                self.setCursor(Qt.SizeVerCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._resize_dragging = False
        self._resize_edge = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event: QEvent):
        """Hide window to tray instead of quitting."""
        self.hidden_to_tray.emit()
        event.accept()
