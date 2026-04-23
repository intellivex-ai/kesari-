"""
Kesari AI — Command Palette
Instant-access, keyboard-first UI for power users.
"""
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListView, 
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QAbstractListModel, QModelIndex
from PySide6.QtGui import QColor, QFont

logger = logging.getLogger(__name__)

class CommandListModel(QAbstractListModel):
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self.items = items or []

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return self.items[index.row()]["label"]
        if role == Qt.UserRole:
            return self.items[index.row()]
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self.items)

    def update_items(self, new_items):
        self.beginResetModel()
        self.items = new_items
        self.endResetModel()

class CommandPalette(QWidget):
    """
    Spotlight-style floating command palette.
    """
    command_submitted = Signal(str, dict) # text, context
    escape_pressed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Frameless and Always on Top
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setFixedSize(600, 400)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Background container
        self.container = QWidget()
        self.container.setObjectName("paletteContainer")
        self.container.setStyleSheet("""
            #paletteContainer {
                background-color: rgba(18, 16, 24, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)
        
        # Drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Input Field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Kesari Command...")
        font = QFont("Inter", 16)
        self.input_field.setFont(font)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                color: #FFFFFF;
                padding: 16px 20px;
            }
        """)
        self.input_field.returnPressed.connect(self._on_submit)
        self.input_field.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.input_field)

        # Suggestions List
        self.list_view = QListView()
        self.list_model = CommandListModel()
        self.list_view.setModel(self.list_model)
        self.list_view.setStyleSheet("""
            QListView {
                background: transparent;
                border: none;
                color: #A1A1AA;
                font-size: 14px;
                padding: 8px;
            }
            QListView::item {
                padding: 12px;
                border-radius: 6px;
            }
            QListView::item:selected {
                background-color: rgba(255, 255, 255, 0.1);
                color: #FFFFFF;
            }
        """)
        self.list_view.clicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_view)

        main_layout.addWidget(self.container)

    def showEvent(self, event):
        super().showEvent(event)
        self.input_field.clear()
        self.input_field.setFocus()
        self._center_on_screen()

    def _center_on_screen(self):
        screen = self.screen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 3
        self.move(x, y)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
            self.escape_pressed.emit()
        elif event.key() == Qt.Key_Down:
            self._move_selection(1)
        elif event.key() == Qt.Key_Up:
            self._move_selection(-1)
        else:
            super().keyPressEvent(event)

    def _move_selection(self, delta):
        count = self.list_model.rowCount()
        if count == 0:
            return
        
        current = self.list_view.currentIndex()
        row = 0 if not current.isValid() else (current.row() + delta) % count
        
        index = self.list_model.index(row, 0)
        self.list_view.setCurrentIndex(index)

    def _on_text_changed(self, text):
        # We will connect this to the command router
        pass

    def _on_submit(self):
        text = self.input_field.text().strip()
        if not text:
            return
        
        current_idx = self.list_view.currentIndex()
        context = None
        if current_idx.isValid():
            context = self.list_model.data(current_idx, Qt.UserRole)
            
        self.command_submitted.emit(text, context or {})
        self.hide()

    def _on_item_clicked(self, index):
        if index.isValid():
            context = self.list_model.data(index, Qt.UserRole)
            self.command_submitted.emit(context["label"], context)
            self.hide()

    def set_suggestions(self, suggestions):
        self.list_model.update_items(suggestions)
        if suggestions:
            self.list_view.setCurrentIndex(self.list_model.index(0, 0))
