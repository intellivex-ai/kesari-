"""
Kesari AI — Main Window
Primary application window with sidebar, chat area, and input bar.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QSizePolicy,
    QSystemTrayIcon, QMenu, QApplication, QFrame,
    QSpacerItem, QTextEdit, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QEvent, QTimer
from PySide6.QtGui import QIcon, QFont, QCursor, QAction, QKeyEvent, QColor

from kesari.config import (
    APP_NAME, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, SIDEBAR_WIDTH, settings,
)
from kesari.gui.styles import (
    COLORS, SIDEBAR_BUTTON_STYLE, SEND_BUTTON_STYLE,
    VOICE_BUTTON_STYLE, NEW_CHAT_BUTTON_STYLE,
)
from kesari.gui.chat_widget import ChatWidget
from kesari.gui.voice_orb import VoiceOrb
from kesari.gui.agent_state import AgentStateTracker


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

        status_lbl = QLabel("🟢 Local AI")
        status_lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {COLORS['success']}; padding-left: 8px;")

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        layout.addWidget(status_lbl)
        layout.addStretch()

        # Window controls
        for text, slot, color in [
            ("─", "minimize", COLORS["text_muted"]),
            ("🗖", "maximize", COLORS["text_muted"]),
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
            elif slot == "maximize":
                btn.clicked.connect(self._toggle_maximize)
            else:
                btn.clicked.connect(self.close_clicked)
            layout.addWidget(btn)

    def _toggle_maximize(self):
        w = self.window()
        if w.isFullScreen() or w.isMaximized():
            w.showNormal()
        else:
            # Let's provide an actual full-screen option if the user wants an immersive experience
            w.showFullScreen()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_maximize()
            event.accept()

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
        # Container to hold the floating pill
        self.setObjectName("inputBar")
        self.setFixedHeight(84)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 0, 40, 24)  # Float above bottom with side margins
        
        inner_container = QWidget()
        inner_container.setObjectName("inputBarInner")
        
        # Add a subtle, premium glowing shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180)) # Deep shadow
        shadow.setOffset(0, 8)
        inner_container.setGraphicsEffect(shadow)

        layout = QHBoxLayout(inner_container)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Attach button
        self._attach_btn = QPushButton("+")
        self._attach_btn.setToolTip("Add Attachment")
        self._attach_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._attach_btn.setProperty("class", "attachBtn")
        from kesari.gui.styles import ATTACH_BUTTON_STYLE
        self._attach_btn.setStyleSheet(ATTACH_BUTTON_STYLE)
        layout.addWidget(self._attach_btn)

        # Voice button
        self._voice_btn = QPushButton("🎤")
        self._voice_btn.setCheckable(True)
        self._voice_btn.setToolTip("Push to talk (hold)")
        self._voice_btn.setCursor(QCursor(Qt.PointingHandCursor))
        from kesari.gui.styles import VOICE_BUTTON_STYLE
        self._voice_btn.setStyleSheet(VOICE_BUTTON_STYLE)
        self._voice_btn.pressed.connect(lambda: self.voice_toggled.emit(True))
        self._voice_btn.released.connect(lambda: self.voice_toggled.emit(False))
        layout.addWidget(self._voice_btn)

        # Text input
        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask Kesari anything...")
        self._input.setFixedHeight(40)
        self._input.setStyleSheet("border: none; background: transparent; font-size: 15px;")
        self._input.returnPressed.connect(self._on_submit)
        self._input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._input)

        # Send button (hidden initially, morphs with attach)
        self._send_btn = QPushButton("↑")
        self._send_btn.setToolTip("Send message")
        self._send_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._send_btn.setFixedSize(32, 32)
        from kesari.gui.styles import SEND_BUTTON_STYLE
        self._send_btn.setStyleSheet(SEND_BUTTON_STYLE)
        self._send_btn.clicked.connect(self._on_submit)
        self._send_btn.setVisible(False)
        layout.addWidget(self._send_btn)

        # ── Context Chips Layout ────────────────────────
        self._chips_container = QWidget()
        self._chips_layout = QHBoxLayout(self._chips_container)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(8)
        self._chips_layout.addStretch()
        
        main_layout.addWidget(self._chips_container)
        main_layout.addWidget(inner_container)

    def _on_text_changed(self, text):
        has_text = bool(text.strip())
        self._attach_btn.setVisible(not has_text)
        self._send_btn.setVisible(has_text)

    def set_context_chips(self, chips: list[str]):
        # Clear old chips
        while self._chips_layout.count() > 1:
            item = self._chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        for text in chips:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    color: #A1A1AA;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: rgba(245, 158, 11, 0.15);
                    color: #F59E0B;
                    border: 1px solid #F59E0B;
                }
            """)
            btn.clicked.connect(lambda checked=False, t=text: self.message_submitted.emit(t))
            self._chips_layout.insertWidget(self._chips_layout.count() - 1, btn)

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
    history_manager_clicked = Signal()
    memory_timeline_clicked = Signal()
    ai_os_mode_toggled = Signal(bool)
    plugin_manager_clicked = Signal()

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
        
        # ── History Manager Button ───────────────────────
        history_btn = QPushButton("🕰️ Manage History")
        history_btn.setCursor(QCursor(Qt.PointingHandCursor))
        history_btn.setStyleSheet(SIDEBAR_BUTTON_STYLE)
        history_btn.clicked.connect(self.history_manager_clicked)
        layout.addWidget(history_btn)

        # ── Memory Timeline Button ───────────────────────
        memory_btn = QPushButton("🧠 Memory Timeline")
        memory_btn.setCursor(QCursor(Qt.PointingHandCursor))
        memory_btn.setStyleSheet(SIDEBAR_BUTTON_STYLE)
        memory_btn.clicked.connect(self.memory_timeline_clicked)
        layout.addWidget(memory_btn)

        # ── Settings Button ──────────────────────────────
        settings_btn = QPushButton("⚙  Settings")
        settings_btn.setCursor(QCursor(Qt.PointingHandCursor))
        settings_btn.setStyleSheet(SIDEBAR_BUTTON_STYLE)
        settings_btn.clicked.connect(self.settings_clicked)
        layout.addWidget(settings_btn)

        # ── Plugin Manager ───────────────────────────────
        plugin_btn = QPushButton("🧩 Plugins")
        plugin_btn.setCursor(QCursor(Qt.PointingHandCursor))
        plugin_btn.setStyleSheet(SIDEBAR_BUTTON_STYLE)
        plugin_btn.clicked.connect(self.plugin_manager_clicked)
        layout.addWidget(plugin_btn)

        # ── AI OS Mode Toggle (Auto Mode) ────────────────────────────
        self.ai_os_mode_btn = QPushButton("🤖 Auto Mode: OFF")
        self.ai_os_mode_btn.setCheckable(True)
        self.ai_os_mode_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.ai_os_mode_btn.setStyleSheet(SIDEBAR_BUTTON_STYLE + """
            QPushButton:checked {
                color: #D2A8FF;
                background-color: rgba(210, 168, 255, 0.1);
                border: 1px solid rgba(210, 168, 255, 0.3);
            }
        """)
        self.ai_os_mode_btn.toggled.connect(self._on_auto_mode_toggled)
        layout.addWidget(self.ai_os_mode_btn)

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

    def _on_auto_mode_toggled(self, checked: bool):
        if checked:
            self.ai_os_mode_btn.setText("🤖 Auto Mode: ON")
        else:
            self.ai_os_mode_btn.setText("🤖 Auto Mode: OFF")
        self.ai_os_mode_toggled.emit(checked)


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
    history_manager_requested = Signal() # History manager clicked
    memory_timeline_requested = Signal() # Memory Timeline clicked
    ai_os_mode_requested = Signal(bool) # AI OS mode toggled
    plugin_manager_requested = Signal() # Plugin Manager clicked
    hidden_to_tray = Signal()           # Window closed to tray

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(1050, 720)

        # Frameless window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # ── Central Widget (Dynamic Background - Idea 2) ──
        central = QWidget()
        central.setStyleSheet(f"""
            QWidget {{
                background: qradialgradient(cx:0.5, cy:0.2, radius: 1.2, fx:0.5, fy:0.2, 
                                            stop:0 #121018, stop:1 {COLORS['bg_darkest']}); 
                border-radius: 12px;
            }}
        """)
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
        self._sidebar.history_manager_clicked.connect(self.history_manager_requested)
        self._sidebar.memory_timeline_clicked.connect(self.memory_timeline_requested)
        self._sidebar.ai_os_mode_toggled.connect(self.ai_os_mode_requested)
        self._sidebar.plugin_manager_clicked.connect(self.plugin_manager_requested)
        body_layout.addWidget(self._sidebar)

        # Chat area + input
        chat_panel = QWidget()
        chat_layout = QVBoxLayout(chat_panel)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        self.chat_widget = ChatWidget()
        self.chat_widget.message_submitted.connect(self.user_message)
        # Handle Inline Edits (Idea 17)
        self.chat_widget.edit_requested.connect(lambda text: self._chat_input._input.setText(text))
        chat_layout.addWidget(self.chat_widget, stretch=1)

        # Agent State Visualizer
        self.agent_state = AgentStateTracker()
        chat_layout.addWidget(self.agent_state)

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
        
        # Drag and Drop
        self.setAcceptDrops(True)
        
        # Auto Mode State
        self.auto_mode_enabled = False
        self.ai_os_mode_requested.connect(self._set_auto_mode)

        # ── Command Palette (Idea 11) ────────────────────────────
        self._cmd_palette = QLineEdit(central)
        self._cmd_palette.setObjectName("cmdPalette")
        self._cmd_palette.setPlaceholderText("Search commands or history...")
        self._cmd_palette.setStyleSheet("""
            QLineEdit {
                background: rgba(10, 10, 15, 0.95);
                border: 1px solid rgba(245, 158, 11, 0.5);
                border-radius: 12px;
                padding: 12px 20px;
                font-size: 16px;
                color: white;
            }
        """)
        self._cmd_palette.hide()
        self._cmd_palette.returnPressed.connect(self._on_cmd_submit)

        # ── Shortcuts ────────────────────────────────────────────
        from PySide6.QtGui import QShortcut, QKeySequence
        self._cmd_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        self._cmd_shortcut.activated.connect(self._toggle_cmd_palette)
        
        self._focus_shortcut = QShortcut(QKeySequence("F10"), self)
        self._focus_shortcut.activated.connect(self._toggle_focus_mode)

    # ── Public API ────────────────────────────────────────

    def _toggle_cmd_palette(self):
        if self._cmd_palette.isVisible():
            self._cmd_palette.hide()
            self.focus_input()
        else:
            # Center it
            w, h = 400, 50
            x = (self.width() - w) // 2
            y = (self.height() - h) // 3
            self._cmd_palette.setGeometry(x, y, w, h)
            self._cmd_palette.show()
            self._cmd_palette.raise_()
            self._cmd_palette.setFocus()
            # Add a drop shadow for the palette
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(30)
            shadow.setColor(QColor(0, 0, 0, 200))
            shadow.setOffset(0, 10)
            self._cmd_palette.setGraphicsEffect(shadow)

    def _set_auto_mode(self, enabled: bool):
        self.auto_mode_enabled = enabled
        if enabled:
            self.chat_widget.add_system_message("🤖 Auto Mode enabled. Safety gates bypassed for OS automation.")
        else:
            self.chat_widget.add_system_message("🤖 Auto Mode disabled. Will ask for permission before modifying system state.")

    def _on_cmd_submit(self):
        text = self._cmd_palette.text().strip().lower()
        self._cmd_palette.clear()
        self._cmd_palette.hide()
        self.focus_input()
        
        if text == "settings":
            self.settings_requested.emit()
        elif text == "history":
            self.history_manager_requested.emit()
        elif text == "new chat":
            self.new_chat_requested.emit()
        elif text == "analytics":
            self.analytics_requested.emit()
        elif text:
            # Pass as a normal message if not a command
            self.user_message.emit(text)

    def _toggle_focus_mode(self):
        """Toggle distraction-free focus mode."""
        self._sidebar.setVisible(not self._sidebar.isVisible())

    @property
    def voice_orb(self) -> VoiceOrb:
        return self._sidebar.voice_orb

    def set_input_enabled(self, enabled: bool):
        self._chat_input.set_enabled(enabled)

    def focus_input(self):
        self._chat_input.focus_input()

    def add_history_item(self, title: str, on_click=None):
        self._sidebar.add_history_item(title, on_click)

    def set_context_chips(self, chips: list[str]):
        self._chat_input.set_context_chips(chips)

    def clear_history(self):
        self._sidebar.clear_history()

    # ── Swipe Gestures (Idea 14) ──────────────────────────

    def event(self, e: QEvent):
        if e.type() == QEvent.NativeGesture:
            if e.gestureType() == Qt.PanNativeGesture:
                val = e.value()
                if val > 5.0:  # Swipe right
                    self._sidebar.setVisible(True)
                elif val < -5.0: # Swipe left
                    self._sidebar.setVisible(False)
                return True
        return super().event(e)

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

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # Dim background slightly
            self.setStyleSheet(f"background-color: {COLORS['bg_panel']}; border-radius: 12px;")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event):
        self.setStyleSheet("")
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self._chat_input._input.setText(f"Analyze this file: {path}")
            self.focus_input()
        event.acceptProposedAction()
