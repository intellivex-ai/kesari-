"""
Kesari AI — Plugin Manager
Marketplace-like UI to manage and install extensions.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QWidget, QPushButton, QFrame, QGridLayout
)
from PySide6.QtCore import Qt
from kesari.gui.styles import COLORS

class PluginManagerDialog(QDialog):
    """Dialog to view and toggle installed plugins/tools."""
    
    def __init__(self, parent=None, tool_router=None):
        super().__init__(parent)
        self.setWindowTitle("Kesari Plugins")
        self.setFixedSize(650, 500)
        self.tool_router = tool_router
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS["bg_darkest"]};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("🧩 Plugin Manager")
        header.setStyleSheet(f"""
            color: {COLORS["text_primary"]};
            font-size: 20px;
            font-weight: 700;
        """)
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["bg_input"]};
                color: {COLORS["text_primary"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS["bg_hover"]};
            }}
        """)
        refresh_btn.clicked.connect(self._load_plugins)
        header_layout.addWidget(refresh_btn)
        layout.addLayout(header_layout)
        
        # Grid Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("background-color: transparent;")
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(16)
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
        self._load_plugins()

    def _clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _load_plugins(self):
        self._clear_grid()
        if not self.tool_router:
            return
            
        tools = self.tool_router.get_all_tools()
        row = 0
        col = 0
        
        for name, tool in tools.items():
            card = self._create_plugin_card(name, tool.__doc__ or "No description provided.")
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1
                
        # Add stretch row
        self.grid_layout.setRowStretch(row + 1, 1)

    def _create_plugin_card(self, name: str, desc: str) -> QWidget:
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS["bg_panel"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 10px;
            }}
            QWidget:hover {{
                border: 1px solid rgba(255, 87, 34, 0.4);
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        title = QLabel(name)
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 15px; font-weight: 600; border: none;")
        layout.addWidget(title)
        
        desc_lbl = QLabel(desc.strip().split('\n')[0]) # Just first line
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; border: none;")
        desc_lbl.setMinimumHeight(35)
        desc_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(desc_lbl)
        
        layout.addStretch()
        
        bottom_layout = QHBoxLayout()
        status = QLabel("🟢 Enabled")
        status.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px; font-weight: 700; border: none;")
        bottom_layout.addWidget(status)
        bottom_layout.addStretch()
        
        toggle_btn = QPushButton("Disable")
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS["text_secondary"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {COLORS["bg_hover"]};
                color: {COLORS["text_primary"]};
            }}
        """)
        bottom_layout.addWidget(toggle_btn)
        layout.addLayout(bottom_layout)
        
        return card
