"""
Kesari AI — Memory Timeline
Exposes the Vector DB contents, allowing the user to search past memories.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QScrollArea, QWidget, QPushButton, QFrame
)
from PySide6.QtCore import Qt
from kesari.gui.styles import COLORS

class MemoryTimelineDialog(QDialog):
    """Dialog to view and search the vector memory (RAG)."""
    
    def __init__(self, parent=None, vector_memory=None):
        super().__init__(parent)
        self.setWindowTitle("Kesari Memory Timeline")
        self.setFixedSize(600, 500)
        self.vector_memory = vector_memory
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS["bg_darkest"]};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("🧠 Memory Timeline")
        header.setStyleSheet(f"""
            color: {COLORS["text_primary"]};
            font-size: 18px;
            font-weight: 700;
        """)
        layout.addWidget(header)
        
        # Search Box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search past conversations or learned facts...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS["bg_input"]};
                color: {COLORS["text_primary"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 14px;
            }}
        """)
        self.search_input.textChanged.connect(self._on_search)
        layout.addWidget(self.search_input)
        
        # Scroll Area for memories
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("background-color: transparent;")
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.mem_layout = QVBoxLayout(self.container)
        self.mem_layout.setContentsMargins(0, 0, 0, 0)
        self.mem_layout.setSpacing(12)
        self.mem_layout.addStretch()
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
        # Load initial
        self._load_all_memories()

    def _clear_layout(self):
        # Keep the stretch at the end
        while self.mem_layout.count() > 1:
            item = self.mem_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _load_all_memories(self):
        self._clear_layout()
        if not self.vector_memory:
            return
            
        # The vector memory backend doesn't have a list_all method typically, 
        # but we can simulate a search for "" or use a dummy search if allowed.
        # Alternatively, we just say "Search to see memories" initially.
        label = QLabel("Type to search your memory database.")
        label.setStyleSheet(f"color: {COLORS['text_muted']}; font-style: italic;")
        label.setAlignment(Qt.AlignCenter)
        self.mem_layout.insertWidget(0, label)

    def _on_search(self, text: str):
        if not text.strip():
            self._load_all_memories()
            return
            
        self._clear_layout()
        if not self.vector_memory:
            return
            
        results = self.vector_memory.search(text, n_results=10)
        
        if not results:
            label = QLabel("No matching memories found.")
            label.setStyleSheet(f"color: {COLORS['text_muted']}; font-style: italic;")
            label.setAlignment(Qt.AlignCenter)
            self.mem_layout.insertWidget(0, label)
            return
            
        for i, res in enumerate(results):
            content = res.get("content", "")
            
            card = QWidget()
            card.setStyleSheet(f"""
                QWidget {{
                    background-color: {COLORS["bg_panel"]};
                    border: 1px solid {COLORS["border"]};
                    border-radius: 8px;
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)
            
            text_label = QLabel(content)
            text_label.setWordWrap(True)
            text_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px; border: none;")
            
            card_layout.addWidget(text_label)
            self.mem_layout.insertWidget(i, card)
