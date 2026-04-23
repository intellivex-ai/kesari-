"""
Kesari AI — Chat Widget
Scrollable chat area with user/AI message bubbles, web result cards, and source transparency.
"""
import html
import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QSizePolicy, QApplication, QPushButton, QFrame,
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, QUrl
from PySide6.QtGui import QFont, QColor, QDesktopServices

from kesari.gui.styles import (
    CHAT_USER_BUBBLE_STYLE, CHAT_AI_BUBBLE_STYLE, COLORS,
    WEB_RESULT_CARD_STYLE, SOURCES_PANEL_BASE_STYLE, SOURCES_TOGGLE_STYLE,
    CONFIDENCE_HIGH_STYLE, CONFIDENCE_MEDIUM_STYLE, CONFIDENCE_LOW_STYLE,
    NEWS_CARD_STYLE, REALTIME_CARD_STYLE, SEARCHING_BADGE_STYLE,
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
        # Status Ring (Idea 18): Glowing ring for AI
        border_style = "border: 2px solid #F59E0B;" if not is_user else "border: 1px solid rgba(255,255,255,0.1);"
        avatar_label.setStyleSheet(f"""
            background-color: {avatar_bg};
            color: white;
            border-radius: 16px;
            font-size: 11px;
            font-weight: 700;
            {border_style}
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

        # ── Fade-in Animation ──────────────────────────────
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        self._opacity = QGraphicsOpacityEffect()
        self._opacity.setOpacity(0)
        self.setGraphicsEffect(self._opacity)
        
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(400) # Smooth 400ms fade in
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def _set_html(self, text: str):
        """Convert markdown-like text to HTML for display."""
        rendered = self._render_markdown(text)
        self._bubble.setText(rendered)

    # ── Inline Edits (Idea 17) ─────────────────────────
    def mouseDoubleClickEvent(self, event):
        if self._is_user and event.button() == Qt.LeftButton:
            # Emit up to parent (handled dynamically via parent hierarchy if needed, or by chat widget)
            parent = self.parent()
            while parent:
                if hasattr(parent, 'edit_requested'):
                    parent.edit_requested.emit(self._full_text)
                    break
                parent = parent.parent()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

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
        
        def render_code_block(match):
            lang = match.group(1) or "code"
            code_content = match.group(2).replace(chr(10), "&#10;")
            
            # Very basic regex syntax highlighting for python/js
            keywords = ["def", "class", "import", "from", "return", "if", "else", "elif", "for", "while", "async", "await", "const", "let", "var", "function"]
            for kw in keywords:
                code_content = re.sub(rf'\b({kw})\b', rf'<span style="color: #FF7B72;">\1</span>', code_content)
                
            # Strings
            code_content = re.sub(r'("[^"]*")', rf'<span style="color: #A5D6FF;">\1</span>', code_content)
            code_content = re.sub(r"('[^']*')", rf'<span style="color: #A5D6FF;">\1</span>', code_content)
            
            # Syntax Highlighting Themes & Markdown Hover Actions (Idea 4 & 13)
            # Add a sleek header to the code block
            header = f"""<div style="background: #0D1117; border-bottom: 1px solid #30363D; border-top-left-radius: 8px; border-top-right-radius: 8px; padding: 6px 12px; font-size: 11px; font-weight: 600; color: #8B949E; text-transform: uppercase;">{lang}</div>"""
            code_body = f"""<pre style="background-color: #161B22; border: 1px solid #30363D; border-top: none; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; padding: 12px; font-family: Consolas, monospace; font-size: 13px; color: #C9D1D9; margin: 0; margin-bottom: 12px; white-space: pre-wrap;">{code_content}</pre>"""
            
            return header + code_body

        # Code blocks (```)
        t = re.sub(r'```(\w*)\n(.*?)```', render_code_block, t, flags=re.DOTALL)
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


class ThinkingBubble(QWidget):
    """Animated '•••' typing indicator."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        
        avatar_label = QLabel("K")
        avatar_label.setFixedSize(32, 32)
        avatar_label.setAlignment(Qt.AlignCenter)
        avatar_label.setStyleSheet(f"""
            background-color: #2d2d44;
            color: white;
            border-radius: 16px;
            font-size: 11px;
            font-weight: 700;
        """)
        
        self._bubble = QLabel("● ● ●")
        self._bubble.setStyleSheet(CHAT_AI_BUBBLE_STYLE)
        self._bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        
        layout.addWidget(avatar_label, alignment=Qt.AlignTop)
        layout.addSpacing(8)
        layout.addWidget(self._bubble)
        layout.addStretch()

        # Fade in
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        self._opacity = QGraphicsOpacityEffect()
        self._opacity.setOpacity(0)
        self.setGraphicsEffect(self._opacity)
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

        # Dot animation
        self._dots = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_dots)
        self._timer.start(400)

    def _animate_dots(self):
        self._dots = (self._dots + 1) % 4
        text = " ".join(["●"] * self._dots + ["○"] * (3 - self._dots))
        self._bubble.setText(f"<span style='color: #F59E0B;'>{text}</span>")


# ── Web Intelligence Widgets ──────────────────────────────

class SearchingIndicator(QWidget):
    """Animated 'Searching the web...' indicator shown during web queries."""

    _LABELS = {
        "search": "Searching the web", "news": "Fetching latest news",
        "deep_research": "Deep research in progress", "realtime_weather": "Fetching live weather",
        "realtime_crypto": "Fetching crypto prices", "realtime_stock": "Fetching stock data",
        "scrape": "Reading article", "comparison": "Comparing sources", "auto": "Searching",
    }
    _ICONS = {
        "search": "🔍", "news": "📰", "deep_research": "🧠",
        "realtime_weather": "🌤️", "realtime_crypto": "💰", "realtime_stock": "📈",
        "scrape": "📄", "comparison": "⚖️", "auto": "🌐",
    }

    def __init__(self, mode: str = "search", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(8)

        icon = self._ICONS.get(mode, "🌐")
        self._base_text = self._LABELS.get(mode, "Searching")

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setStyleSheet("font-size: 14px; background: transparent;")
        layout.addWidget(self._icon_lbl)

        self._text_lbl = QLabel(f"{self._base_text}...")
        self._text_lbl.setStyleSheet(SEARCHING_BADGE_STYLE)
        layout.addWidget(self._text_lbl)
        layout.addStretch()

        from PySide6.QtWidgets import QGraphicsOpacityEffect
        self._opacity = QGraphicsOpacityEffect()
        self._opacity.setOpacity(0)
        self.setGraphicsEffect(self._opacity)
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

        self._dots = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(500)

    def _animate(self):
        self._dots = (self._dots + 1) % 4
        self._text_lbl.setText(f"{self._base_text}{'.' * max(1, self._dots)}")


class ActionStepWidget(QWidget):
    """Animated indicator shown during autonomous OS action execution."""

    def __init__(self, step_label: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(8)

        # Extract icon from step label if present
        icon = "🤖"
        if step_label and len(step_label) > 1 and step_label[0] > '\u2000':
            icon = step_label[0]
            step_label = step_label[1:].strip()

        self._base_text = step_label

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setStyleSheet("font-size: 14px; background: transparent;")
        layout.addWidget(self._icon_lbl)

        self._text_lbl = QLabel(f"{self._base_text}...")
        self._text_lbl.setStyleSheet(SEARCHING_BADGE_STYLE.replace("#8B949E", "#D2A8FF")) # Slightly purple tint for OS actions
        layout.addWidget(self._text_lbl)
        layout.addStretch()

        from PySide6.QtWidgets import QGraphicsOpacityEffect
        self._opacity = QGraphicsOpacityEffect()
        self._opacity.setOpacity(0)
        self.setGraphicsEffect(self._opacity)
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

        self._dots = 0
        from PySide6.QtCore import QTimer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(500)

    def _animate(self):
        self._dots = (self._dots + 1) % 4
        self._text_lbl.setText(f"{self._base_text}{'.' * max(1, self._dots)}")
        
    def complete(self):
        self._timer.stop()
        self._text_lbl.setText(f"{self._base_text} ✅")


class SourceCard(QWidget):
    """A single clickable source link with confidence badge."""

    def __init__(self, title: str, url: str, score: float, source_name: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        badge = QLabel()
        if score >= 0.88:
            badge.setText("HIGH")
            badge.setStyleSheet(CONFIDENCE_HIGH_STYLE)
        elif score >= 0.65:
            badge.setText("MED")
            badge.setStyleSheet(CONFIDENCE_MEDIUM_STYLE)
        else:
            badge.setText("LOW")
            badge.setStyleSheet(CONFIDENCE_LOW_STYLE)
        badge.setFixedWidth(36)
        badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(badge)

        display = (title[:55] + "…") if len(title) > 55 else title
        link = QLabel(f'<a href="{url}" style="color: #A1A1AA; text-decoration: none;">{display}</a>')
        link.setOpenExternalLinks(True)
        link.setStyleSheet("font-size: 12px; background: transparent;")
        link.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(link)

        if source_name:
            src_lbl = QLabel(source_name[:20])
            src_lbl.setStyleSheet(
                f"font-size: 10px; color: {COLORS['text_muted']}; font-weight: 600; background: transparent;"
            )
            layout.addWidget(src_lbl)


class SourcesPanel(QWidget):
    """Collapsible sources panel shown after web results."""

    def __init__(self, sources: list, parent=None):
        super().__init__(parent)
        self._expanded = False
        self._sources = sources

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 2, 16, 4)
        main_layout.setSpacing(0)

        self._toggle_btn = QPushButton(f"🔗  {len(sources)} Sources  ▸")
        self._toggle_btn.setStyleSheet(SOURCES_TOGGLE_STYLE)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle)
        main_layout.addWidget(self._toggle_btn)

        self._container = QWidget()
        self._container.setStyleSheet(SOURCES_PANEL_BASE_STYLE)
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(6, 4, 6, 4)
        container_layout.setSpacing(3)

        for src in sources[:8]:
            card = SourceCard(
                title=src.get("title", "Source"),
                url=src.get("url", "#"),
                score=src.get("score", 0.7),
                source_name=src.get("source", ""),
            )
            container_layout.addWidget(card)

        self._container.hide()
        main_layout.addWidget(self._container)

    def _toggle(self):
        self._expanded = not self._expanded
        if self._expanded:
            self._container.show()
            self._toggle_btn.setText(f"🔗  {len(self._sources)} Sources  ▾")
        else:
            self._container.hide()
            self._toggle_btn.setText(f"🔗  {len(self._sources)} Sources  ▸")


class ChatWidget(QWidget):
    """Scrollable chat area containing message bubbles."""

    message_submitted = Signal(str)  # Emitted when user presses Enter
    edit_requested = Signal(str)     # Emitted when user double clicks bubble

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatArea")
        self._bubbles: list[MessageBubble] = []
        self._current_ai_bubble: MessageBubble | None = None
        self._thinking_bubble: ThinkingBubble | None = None
        self._searching_indicator = None  # Web search indicator

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
        """Show initial welcome message with quick actions."""
        self._welcome = QWidget()
        layout = QVBoxLayout(self._welcome)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(24)

        icon_lbl = QLabel("🦁")
        icon_lbl.setStyleSheet("font-size: 56px;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_lbl)

        welcome_lbl = QLabel("How can I help you today?")
        welcome_lbl.setStyleSheet("font-size: 28px; font-weight: 800; letter-spacing: -0.8px; color: #FFFFFF;")
        welcome_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome_lbl)

        desc_lbl = QLabel('Kesari runs <span style="color: #F59E0B; font-weight: 700;">100% locally</span> on your machine.')
        desc_lbl.setStyleSheet("color: #a1a1aa; font-size: 15px; letter-spacing: 0.2px;")
        desc_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_lbl)

        # Quick Actions
        self._quick_actions_container = QWidget()
        qa_layout = QHBoxLayout(self._quick_actions_container)
        qa_layout.setAlignment(Qt.AlignCenter)
        qa_layout.setSpacing(12)

        actions = [
            ("🔍 Search Web", "Search for latest AI news"),
            ("📰 News", "Latest news on technology"),
            ("🌤️ Weather", "Weather in Mumbai"),
            ("💰 Crypto", "price of bitcoin"),
            ("🧠 Research", "Research quantum computing"),
            ("⚙️ System", "Check PC Stats"),
        ]

        for action_text, action_query in actions:
            btn = QPushButton(action_text)
            btn.setProperty("class", "actionChip")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, q=action_query: self.message_submitted.emit(q))
            qa_layout.addWidget(btn)

        layout.addWidget(self._quick_actions_container)
        
        # Add to scroll layout
        self._chat_layout.insertWidget(0, self._welcome)
        self._welcome_stretch = self._chat_layout.insertStretch(1)

        # ── Fade-in Animation for Welcome Screen ───────────
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        self._welcome_opacity = QGraphicsOpacityEffect()
        self._welcome_opacity.setOpacity(0)
        self._welcome.setGraphicsEffect(self._welcome_opacity)
        
        self._welcome_anim = QPropertyAnimation(self._welcome_opacity, b"opacity")
        self._welcome_anim.setDuration(800) # Slower 800ms fade in for intro
        self._welcome_anim.setStartValue(0.0)
        self._welcome_anim.setEndValue(1.0)
        self._welcome_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._welcome_anim.start()

    def _remove_welcome(self):
        """Remove welcome message on first interaction."""
        if hasattr(self, '_welcome') and self._welcome:
            self._welcome.setParent(None)
            self._welcome.deleteLater()
            self._welcome = None
            if hasattr(self, '_quick_actions_container') and self._quick_actions_container:
                self._quick_actions_container.setParent(None)
                self._quick_actions_container.deleteLater()
                self._quick_actions_container = None
            if hasattr(self, '_welcome_stretch') and self._welcome_stretch:
                self._chat_layout.removeItem(self._welcome_stretch)
                self._welcome_stretch = None

    def add_user_message(self, text: str):
        """Add a user message bubble."""
        self._remove_welcome()
        bubble = MessageBubble(text, is_user=True)
        self._bubbles.append(bubble)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, bubble)
        self._scroll_to_bottom(force=True)

    def show_thinking(self):
        """Show the animated typing indicator."""
        self._remove_welcome()
        if not self._thinking_bubble:
            self._thinking_bubble = ThinkingBubble()
            self._chat_layout.insertWidget(self._chat_layout.count() - 1, self._thinking_bubble)
            self._scroll_to_bottom(force=True)

    def remove_thinking(self):
        """Remove the animated typing indicator."""
        if self._thinking_bubble:
            self._thinking_bubble.setParent(None)
            self._thinking_bubble.deleteLater()
            self._thinking_bubble = None

    def add_ai_message(self, text: str = "") -> MessageBubble:
        """Add an AI message bubble (may be empty for streaming)."""
        self.remove_thinking()
        self._remove_welcome()
        bubble = MessageBubble(text, is_user=False)
        self._bubbles.append(bubble)
        self._current_ai_bubble = bubble
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, bubble)
        self._scroll_to_bottom(force=True)
        return bubble

    def append_to_current_ai(self, chunk: str):
        """Append a streaming chunk to the current AI bubble."""
        if self._current_ai_bubble:
            self._current_ai_bubble.append_text(chunk)
            self._scroll_to_bottom()

    def finish_ai_message(self):
        """Mark the current AI message as complete."""
        self._current_ai_bubble = None
        self.remove_thinking()

    def add_system_message(self, text: str):
        """Add a system/status message (centered, muted)."""
        self.remove_thinking()
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
        self._scroll_to_bottom(force=True)

    def clear_chat(self):
        """Clear all messages."""
        self.remove_thinking()
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

    def _scroll_to_bottom(self, force=False):
        """Smart Auto-Scrolling. Only scroll if user hasn't scrolled up manually, unless forced."""
        sb = self._scroll.verticalScrollBar()
        if force or (sb.maximum() - sb.value() < 50):
            QTimer.singleShot(50, lambda: sb.setValue(sb.maximum()))

    # ── Web Intelligence Methods ──────────────────────────

    def show_searching(self, mode: str = "search"):
        """Show animated 'Searching...' indicator during web queries."""
        self._remove_welcome()
        self.remove_thinking()
        if hasattr(self, '_searching_indicator') and self._searching_indicator:
            return
        self._searching_indicator = SearchingIndicator(mode=mode)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, self._searching_indicator)
        self._scroll_to_bottom(force=True)

    def remove_searching(self):
        """Remove the searching indicator."""
        if hasattr(self, '_searching_indicator') and self._searching_indicator:
            self._searching_indicator.setParent(None)
            self._searching_indicator.deleteLater()
            self._searching_indicator = None

    def show_action_step(self, step_label: str):
        """Show animated action step indicator."""
        self._remove_welcome()
        self.remove_thinking()
        self.remove_action_step()
        self._action_step = ActionStepWidget(step_label=step_label)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, self._action_step)
        self._scroll_to_bottom(force=True)
        
    def complete_action_step(self):
        """Mark the current action step as complete."""
        if hasattr(self, '_action_step') and self._action_step:
            self._action_step.complete()
            # We intentionally leave it visible as history instead of removing it

    def remove_action_step(self):
        if hasattr(self, '_action_step') and self._action_step:
            self._action_step.setParent(None)
            self._action_step.deleteLater()
            self._action_step = None

    def add_sources_panel(self, sources: list):
        """Add a collapsible sources panel below the last AI message."""
        if not sources:
            return
        panel = SourcesPanel(sources)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, panel)
        self._scroll_to_bottom()

    def add_refine_search_chip(self, last_query: str):
        """Add a 'Refine Search' context chip after web results."""
        chip_widget = QWidget()
        chip_layout = QHBoxLayout(chip_widget)
        chip_layout.setContentsMargins(16, 2, 16, 8)
        chip_layout.setSpacing(8)
        chip_layout.addStretch()

        refine_btn = QPushButton("🔍 Refine Search")
        refine_btn.setProperty("class", "actionChip")
        refine_btn.setCursor(Qt.PointingHandCursor)
        refine_btn.setToolTip(f"Refine: {last_query[:50]}")
        refine_btn.clicked.connect(
            lambda: self.message_submitted.emit(f"Search for more details about: {last_query}")
        )
        chip_layout.addWidget(refine_btn)

        deeper_btn = QPushButton("🧠 Research Deeper")
        deeper_btn.setProperty("class", "actionChip")
        deeper_btn.setCursor(Qt.PointingHandCursor)
        deeper_btn.clicked.connect(
            lambda: self.message_submitted.emit(f"Research {last_query}")
        )
        chip_layout.addWidget(deeper_btn)

        self._chat_layout.insertWidget(self._chat_layout.count() - 1, chip_widget)
        self._scroll_to_bottom()
