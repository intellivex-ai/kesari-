"""
Kesari AI — Agent State Tracker
Visualizes the internal multi-agent execution pipeline.
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from kesari.gui.styles import COLORS

class AgentStateTracker(QWidget):
    """Widget to show the current state of the AI (Planning, Executing, etc.)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("agentStateTracker")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(12)
        
        # Brain icon
        self.icon_label = QLabel("🧠")
        self.icon_label.setStyleSheet("font-size: 16px;")
        
        # Text label
        self.text_label = QLabel("Thinking...")
        self.text_label.setStyleSheet(f"""
            color: {COLORS["accent"]};
            font-size: 13px;
            font-weight: 600;
        """)
        
        # Container styling for glassmorphism
        self.container = QWidget()
        self.container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS["bg_glass"]};
                border: 1px solid {COLORS["border_light"]};
                border-radius: 16px;
                padding: 4px 12px;
            }}
        """)
        
        inner_layout = QHBoxLayout(self.container)
        inner_layout.setContentsMargins(8, 4, 12, 4)
        inner_layout.setSpacing(8)
        inner_layout.addWidget(self.icon_label)
        inner_layout.addWidget(self.text_label)
        
        layout.addWidget(self.container, alignment=Qt.AlignLeft)
        
        # Fade effect
        self._opacity = QGraphicsOpacityEffect()
        self._opacity.setOpacity(0)
        self.setGraphicsEffect(self._opacity)
        
        self.hide()

    def update_state(self, state: str, tool_name: str = None):
        """Update the visual state."""
        self.show()
        
        if state == "planning":
            self.icon_label.setText("🧠")
            self.text_label.setText("Planning...")
            self._fade_in()
        elif state == "executing":
            self.icon_label.setText("🔧")
            tool_text = tool_name if tool_name else "tools"
            self.text_label.setText(f"Using {tool_text}...")
        elif state == "memory":
            self.icon_label.setText("💾")
            self.text_label.setText("Searching memory...")
        elif state == "done":
            self.icon_label.setText("✅")
            self.text_label.setText("Done")
            QTimer.singleShot(1500, self._fade_out)

    def _fade_in(self):
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def _fade_out(self):
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(400)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.InCubic)
        self._anim.finished.connect(self.hide)
        self._anim.start()
