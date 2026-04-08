"""
Kesari AI — QSS Stylesheets
Dark glassmorphism theme with saffron accent.
"""
from kesari.config import settings

THEMES = {
    "dark": {
        "bg_darkest": "#07070c",
        "bg_dark": "#0d0d14",
        "bg_panel": "#12121c",
        "bg_sidebar": "#0f0f18",
        "bg_input": "#161622",
        "bg_hover": "#1c1c2e",
        "bg_glass": "rgba(255, 255, 255, 0.03)",
        "border": "rgba(255, 255, 255, 0.07)",
        "border_light": "rgba(255, 255, 255, 0.12)",
        "text_primary": "#e8e8ed",
        "text_secondary": "#8e8ea0",
        "text_muted": "#5a5a6e",
        "accent": "#FF6B35",
        "accent_hover": "#FF8555",
        "accent_gradient_start": "#FF6B35",
        "accent_gradient_end": "#F7931E",
        "user_bubble": "#1e1e36",
        "ai_bubble": "#14141f",
        "success": "#4ade80",
        "warning": "#fbbf24",
        "error": "#f87171",
        "scrollbar": "rgba(255, 255, 255, 0.08)",
        "scrollbar_hover": "rgba(255, 255, 255, 0.15)",
    },
    "light": {
        "bg_darkest": "#f9fafb",
        "bg_dark": "#f3f4f6",
        "bg_panel": "#ffffff",
        "bg_sidebar": "#f8fafc",
        "bg_input": "#e5e7eb",
        "bg_hover": "#d1d5db",
        "bg_glass": "rgba(0, 0, 0, 0.03)",
        "border": "#e5e7eb",
        "border_light": "#d1d5db",
        "text_primary": "#111827",
        "text_secondary": "#4b5563",
        "text_muted": "#9ca3af",
        "accent": "#FF6B35",
        "accent_hover": "#FF8555",
        "accent_gradient_start": "#FF6B35",
        "accent_gradient_end": "#F7931E",
        "user_bubble": "#f3f4f6",
        "ai_bubble": "#ffffff",
        "success": "#22c55e",
        "warning": "#eab308",
        "error": "#ef4444",
        "scrollbar": "rgba(0, 0, 0, 0.1)",
        "scrollbar_hover": "rgba(0, 0, 0, 0.2)",
    },
    "saffron": {
        "bg_darkest": "#1a0f0b",
        "bg_dark": "#23150f",
        "bg_panel": "#2d1a12",
        "bg_sidebar": "#26160f",
        "bg_input": "#382016",
        "bg_hover": "#4a2a1d",
        "bg_glass": "rgba(255, 107, 53, 0.05)",
        "border": "rgba(255, 107, 53, 0.15)",
        "border_light": "rgba(255, 107, 53, 0.25)",
        "text_primary": "#fdf8f6",
        "text_secondary": "#e8bba6",
        "text_muted": "#a67c69",
        "accent": "#FF6B35",
        "accent_hover": "#FF8555",
        "accent_gradient_start": "#FF6B35",
        "accent_gradient_end": "#F7931E",
        "user_bubble": "#4a2a1d",
        "ai_bubble": "#2d1a12",
        "success": "#4ade80",
        "warning": "#fbbf24",
        "error": "#f87171",
        "scrollbar": "rgba(255, 107, 53, 0.1)",
        "scrollbar_hover": "rgba(255, 107, 53, 0.25)",
    }
}

current_theme_name = settings.get("theme", "dark")
COLORS = THEMES.get(current_theme_name, THEMES["dark"]).copy()


GLOBAL_STYLESHEET = f"""
/* ─── Global ────────────────────────────────────────────── */
* {{
    font-family: 'Inter', 'Segoe UI', sans-serif;
    color: {COLORS["text_primary"]};
    outline: none;
}}

QMainWindow, QDialog {{
    background-color: {COLORS["bg_darkest"]};
}}

QWidget {{
    background-color: transparent;
}}

/* ─── Scrollbars ────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {COLORS["scrollbar"]};
    border-radius: 3px;
    min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS["scrollbar_hover"]};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
    height: 0px;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS["scrollbar"]};
    border-radius: 3px;
    min-width: 40px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {COLORS["scrollbar_hover"]};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    background: none;
    width: 0px;
}}

/* ─── Buttons ───────────────────────────────────────────── */
QPushButton {{
    background-color: {COLORS["bg_input"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {COLORS["bg_hover"]};
    border-color: {COLORS["border_light"]};
}}
QPushButton:pressed {{
    background-color: {COLORS["bg_dark"]};
}}

QPushButton#accentButton {{
    background-color: {COLORS["accent"]};
    color: white;
    border: none;
    font-weight: 600;
}}
QPushButton#accentButton:hover {{
    background-color: {COLORS["accent_hover"]};
}}

/* ─── Text Input ────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {COLORS["bg_input"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 14px;
    selection-background-color: {COLORS["accent"]};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {COLORS["accent"]};
}}

/* ─── Labels ────────────────────────────────────────────── */
QLabel {{
    color: {COLORS["text_primary"]};
    font-size: 13px;
}}
QLabel#titleLabel {{
    font-size: 16px;
    font-weight: 700;
    color: {COLORS["text_primary"]};
}}
QLabel#subtitleLabel {{
    font-size: 12px;
    color: {COLORS["text_secondary"]};
}}
QLabel#mutedLabel {{
    font-size: 11px;
    color: {COLORS["text_muted"]};
}}

/* ─── Combo Box ─────────────────────────────────────────── */
QComboBox {{
    background-color: {COLORS["bg_input"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: {COLORS["text_primary"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS["bg_panel"]};
    border: 1px solid {COLORS["border_light"]};
    border-radius: 8px;
    selection-background-color: {COLORS["bg_hover"]};
    color: {COLORS["text_primary"]};
    padding: 4px;
}}

/* ─── ToolTip ───────────────────────────────────────────── */
QToolTip {{
    background-color: {COLORS["bg_panel"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border_light"]};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ─── Sidebar ───────────────────────────────────────────── */
QWidget#sidebar {{
    background-color: {COLORS["bg_sidebar"]};
    border-right: 1px solid {COLORS["border"]};
}}

/* ─── Chat Area ─────────────────────────────────────────── */
QWidget#chatArea {{
    background-color: {COLORS["bg_darkest"]};
}}

/* ─── Input Bar ─────────────────────────────────────────── */
QWidget#inputBar {{
    background-color: {COLORS["bg_dark"]};
    border-top: 1px solid {COLORS["border"]};
}}

/* ─── Title Bar ─────────────────────────────────────────── */
QWidget#titleBar {{
    background-color: {COLORS["bg_dark"]};
    border-bottom: 1px solid {COLORS["border"]};
}}

/* ─── Menu / Context ────────────────────────────────────── */
QMenu {{
    background-color: {COLORS["bg_panel"]};
    border: 1px solid {COLORS["border_light"]};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 8px 24px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {COLORS["bg_hover"]};
}}
"""

# ─── Component-specific styles ─────────────────────────────

CHAT_USER_BUBBLE_STYLE = f"""
    background-color: {COLORS["user_bubble"]};
    border: 1px solid {COLORS["border_light"]};
    border-radius: 16px;
    border-bottom-right-radius: 4px;
    padding: 12px 16px;
    color: {COLORS["text_primary"]};
    font-size: 14px;
    line-height: 1.5;
"""

CHAT_AI_BUBBLE_STYLE = f"""
    background-color: {COLORS["ai_bubble"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 16px;
    border-bottom-left-radius: 4px;
    padding: 12px 16px;
    color: {COLORS["text_primary"]};
    font-size: 14px;
    line-height: 1.5;
"""

SIDEBAR_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {COLORS["text_secondary"]};
        border: none;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: left;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: {COLORS["bg_hover"]};
        color: {COLORS["text_primary"]};
    }}
    QPushButton:checked {{
        background-color: {COLORS["bg_hover"]};
        color: {COLORS["text_primary"]};
        font-weight: 600;
    }}
"""

SEND_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {COLORS["accent"]};
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0px;
        font-size: 16px;
        font-weight: 700;
        min-width: 40px;
        min-height: 40px;
        max-width: 40px;
        max-height: 40px;
    }}
    QPushButton:hover {{
        background-color: {COLORS["accent_hover"]};
    }}
    QPushButton:pressed {{
        background-color: #e05a28;
    }}
    QPushButton:disabled {{
        background-color: {COLORS["bg_hover"]};
        color: {COLORS["text_muted"]};
    }}
"""

VOICE_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {COLORS["text_secondary"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 10px;
        padding: 0px;
        font-size: 18px;
        min-width: 40px;
        min-height: 40px;
        max-width: 40px;
        max-height: 40px;
    }}
    QPushButton:hover {{
        background-color: {COLORS["bg_hover"]};
        color: {COLORS["accent"]};
        border-color: {COLORS["accent"]};
    }}
    QPushButton:checked {{
        background-color: rgba(255, 107, 53, 0.15);
        color: {COLORS["accent"]};
        border-color: {COLORS["accent"]};
    }}
"""

NEW_CHAT_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {COLORS["accent"]};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {COLORS["accent_hover"]};
    }}
"""
