"""
Kesari AI — Chat Widget
Scrollable chat area with user/AI message bubbles and markdown rendering.
"""
import html
import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QSizePolicy, QApplication,
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor

from kesari.gui.styles import (
    CHAT_USER_BUBBLE_STYLE, CHAT_AI_BUBBLE_STYLE, COLORS,
)


class MessageBubble(QWidget):
    """A single chat message bubble."""

    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        self._is_user = is_user
        self._full_text = text

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(0)

        # ── Avatar ────────────────────────────────────────
        avatar_label = QLabel("You" if is_user else "K")
        avatar_label.setFixedSize(32, 32)
        avatar_label.setAlignment(Qt.AlignCenter)
        avatar_bg = COLORS["accent"] if is_user else "#2d2d44"
        avatar_label.setStyleSheet(f"""
            background-color: {avatar_bg};
            color: white;
            border-radius: 16px;
            font-size: 11px;
            font-weight: 700;
        """)

        # ── Bubble ────────────────────────────────────────
        self._bubble = QLabel()
        self._bubble.setWordWrap(True)
        self._bubble.setTextFormat(Qt.RichText)
        self._bubble.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self._bubble.setOpenExternalLinks(True)
        self._bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self._bubble.setMaximumWidth(560)
        style = CHAT_USER_BUBBLE_STYLE if is_user else CHAT_AI_BUBBLE_STYLE
        self._bubble.setStyleSheet(style)
        self._set_html(text)

        # ── Layout (user = right, AI = left) ──────────────
        if is_user:
            layout.addStretch()
            layout.addWidget(self._bubble)
            layout.addSpacing(8)
            layout.addWidget(avatar_label, alignment=Qt.AlignTop)
        else:
            layout.addWidget(avatar_label, alignment=Qt.AlignTop)
            layout.addSpacing(8)
            layout.addWidget(self._bubble)
            layout.addStretch()

    def _set_html(self, text: str):
        """Convert markdown-like text to HTML for display."""
        rendered = self._render_markdown(text)
        self._bubble.setText(rendered)

    def append_text(self, chunk: str):
        """Append streaming text chunk."""
        self._full_text += chunk
        self._set_html(self._full_text)

    def set_text(self, text: str):
        """Replace the full text."""
        self._full_text = text
        self._set_html(self._full_text)

    @staticmethod
    def _render_markdown(text: str) -> str:
        """Lightweight markdown → HTML renderer."""
        if not text:
            return ""
        t = html.escape(text)
        # Code blocks (```)
        t = re.sub(
            r'```(\w*)\n(.*?)```',
            lambda m: (
                f'<pre style="background-color: #1a1a2e; border: 1px solid rgba(255,255,255,0.08); '
                f'border-radius: 8px; padding: 10px 12px; font-family: Consolas, monospace; '
                f'font-size: 12px; color: #c4c4d4; margin: 6px 0; white-space: pre-wrap;">'
                f'{m.group(2).replace(chr(10), "&#10;")}</pre>'
            ),
            t,
            flags=re.DOTALL,
        )
        # Inline code
        t = re.sub(
            r'`([^`]+)`',
            r'<code style="background-color: #1a1a2e; border-radius: 4px; padding: 2px 6px; '
            r'font-family: Consolas, monospace; font-size: 12px; color: #FF6B35;">\1</code>',
            t,
        )
        # Bold
        t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
        # Italic
        t = re.sub(r'\*(.+?)\*', r'<i>\1</i>', t)
        # Bullet lists
        t = re.sub(r'^[-•]\s+(.+)$', r'<div style="margin-left: 12px;">• \1</div>', t, flags=re.MULTILINE)
        # Numbered lists
        t = re.sub(r'^(\d+)\.\s+(.+)$', r'<div style="margin-left: 12px;">\1. \2</div>', t, flags=re.MULTILINE)
        # Headings
        t = re.sub(r'^###\s+(.+)$', r'<div style="font-size: 14px; font-weight: 700; margin: 8px 0 4px 0;">\1</div>', t, flags=re.MULTILINE)
        t = re.sub(r'^##\s+(.+)$', r'<div style="font-size: 15px; font-weight: 700; margin: 10px 0 4px 0;">\1</div>', t, flags=re.MULTILINE)
        t = re.sub(r'^#\s+(.+)$', r'<div style="font-size: 16px; font-weight: 700; margin: 10px 0 4px 0;">\1</div>', t, flags=re.MULTILINE)
        # Line breaks
        t = t.replace('\n', '<br>')
        return t


class ChatWidget(QWidget):
    """Scrollable chat area containing message bubbles."""

    message_submitted = Signal(str)  # Emitted when user presses Enter

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatArea")
        self._bubbles: list[MessageBubble] = []
        self._current_ai_bubble: MessageBubble | None = None

        # ── Scroll Area ──────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet("background-color: transparent;")

        # ── Inner container ──────────────────────────────
        self._container = QWidget()
        self._container.setStyleSheet("background-color: transparent;")
        self._chat_layout = QVBoxLayout(self._container)
        self._chat_layout.setContentsMargins(0, 16, 0, 16)
        self._chat_layout.setSpacing(4)
        self._chat_layout.addStretch()

        self._scroll.setWidget(self._container)

        # ── Main layout ──────────────────────────────────
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._scroll)

        # ── Welcome Message ──────────────────────────────
        self._show_welcome()

    def _show_welcome(self):
        """Show a welcome message on start."""
        welcome = QLabel()
        welcome.setAlignment(Qt.AlignCenter)
        welcome.setTextFormat(Qt.RichText)
        welcome.setStyleSheet("padding: 40px;")
        welcome.setText(
            f'<div style="text-align: center;">'
            f'<div style="font-size: 36px; margin-bottom: 8px;">🦁</div>'
            f'<div style="font-size: 20px; font-weight: 700; color: {COLORS["text_primary"]}; '
            f'margin-bottom: 4px;">Kesari AI</div>'
            f'<div style="font-size: 13px; color: {COLORS["text_secondary"]};">'
            f'Your personal desktop assistant. Ask me anything or give me a command.</div>'
            f'</div>'
        )
        self._welcome = welcome
        self._chat_layout.insertWidget(0, welcome)

    def _remove_welcome(self):
        """Remove welcome message on first interaction."""
        if hasattr(self, '_welcome') and self._welcome:
            self._welcome.setParent(None)
            self._welcome.deleteLater()
            self._welcome = None

    def add_user_message(self, text: str):
        """Add a user message bubble."""
        self._remove_welcome()
        bubble = MessageBubble(text, is_user=True)
        self._bubbles.append(bubble)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, bubble)
        self._scroll_to_bottom()

    def add_ai_message(self, text: str = "") -> MessageBubble:
        """Add an AI message bubble (may be empty for streaming)."""
        self._remove_welcome()
        bubble = MessageBubble(text, is_user=False)
        self._bubbles.append(bubble)
        self._current_ai_bubble = bubble
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, bubble)
        self._scroll_to_bottom()
        return bubble

    def append_to_current_ai(self, chunk: str):
        """Append a streaming chunk to the current AI bubble."""
        if self._current_ai_bubble:
            self._current_ai_bubble.append_text(chunk)
            self._scroll_to_bottom()

    def finish_ai_message(self):
        """Mark the current AI message as complete."""
        self._current_ai_bubble = None

    def add_system_message(self, text: str):
        """Add a system/status message (centered, muted)."""
        self._remove_welcome()
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"""
            color: {COLORS["text_muted"]};
            font-size: 12px;
            padding: 8px 16px;
            font-style: italic;
        """)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, label)
        self._scroll_to_bottom()

    def clear_chat(self):
        """Clear all messages."""
        for i in reversed(range(self._chat_layout.count())):
            item = self._chat_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                w.setParent(None)
                w.deleteLater()
        self._bubbles.clear()
        self._current_ai_bubble = None
        self._chat_layout.addStretch()
        self._show_welcome()

    def _scroll_to_bottom(self):
        """Scroll to the bottom of the chat."""
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))
