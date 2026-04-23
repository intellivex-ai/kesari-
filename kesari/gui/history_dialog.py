"""
Kesari AI — History Dialog
Allows the user to view and delete conversation history.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from kesari.gui.styles import COLORS

class HistoryDialog(QDialog):
    """Dialog to manage conversation history."""

    delete_requested = Signal(int)

    def __init__(self, parent=None, conversations=None):
        super().__init__(parent)
        self.setWindowTitle("History Manager")
        self.setFixedSize(500, 600)
        self.setStyleSheet(f"background-color: {COLORS['bg_darkest']}; color: {COLORS['text_primary']};")
        
        # Frameless for premium look, but keep default for simplicity if preferred.
        # Let's use a standard dialog with premium styling inside.
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title Bar
        title_bar = QWidget()
        title_bar.setFixedHeight(50)
        title_bar.setStyleSheet(f"background-color: {COLORS['bg_dark']}; border-bottom: 1px solid {COLORS['border']};")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 20, 0)
        
        lbl = QLabel("Manage History")
        lbl.setStyleSheet("font-size: 16px; font-weight: 600;")
        title_layout.addWidget(lbl)
        
        title_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLORS['text_muted']};
                font-size: 16px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_hover']};
                color: {COLORS['error']};
            }}
        """)
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)
        
        main_layout.addWidget(title_bar)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(20, 20, 20, 20)
        self.list_layout.setSpacing(8)
        
        if conversations:
            for conv in conversations:
                self.list_layout.addWidget(self._create_row(conv))
        else:
            empty = QLabel("No history found.")
            empty.setStyleSheet(f"color: {COLORS['text_muted']}; font-style: italic;")
            empty.setAlignment(Qt.AlignCenter)
            self.list_layout.addWidget(empty)
            
        self.list_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        # Add a subtle border around the whole dialog
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_darkest']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)

    def _create_row(self, conv: dict) -> QWidget:
        row = QWidget()
        row.setFixedHeight(60)
        row.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 0, 16, 0)
        
        # Title and Date
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 10, 0, 10)
        info_layout.setSpacing(2)
        
        title = QLabel(conv.get("title", "Unknown Conversation"))
        title.setStyleSheet("border: none; background: transparent; font-size: 14px; font-weight: 500;")
        
        date_str = conv.get("updated_at", "").split(".")[0] # Strip microseconds if any
        date = QLabel(date_str)
        date.setStyleSheet(f"border: none; background: transparent; color: {COLORS['text_muted']}; font-size: 11px;")
        
        info_layout.addWidget(title)
        info_layout.addWidget(date)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Delete Button
        del_btn = QPushButton("🗑️ Delete")
        del_btn.setCursor(QCursor(Qt.PointingHandCursor))
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                color: {COLORS['error']};
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_hover']};
                border-color: {COLORS['error']};
            }}
        """)
        del_btn.clicked.connect(lambda checked=False, cid=conv["id"], w=row: self._on_delete(cid, w))
        layout.addWidget(del_btn)
        
        return row

    def _on_delete(self, conversation_id: int, widget: QWidget):
        """Emit delete signal and hide the widget immediately."""
        widget.hide()
        self.delete_requested.emit(conversation_id)

