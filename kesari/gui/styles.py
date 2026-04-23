"""
Kesari AI — QSS Stylesheets
Dark glassmorphism theme with saffron accent.
"""
from kesari.config import settings

THEMES = {
    "dark": {
        "bg_darkest": "#000000",        # Pure OLED black
        "bg_dark": "#0A0A0C",           # Very deep black-gray
        "bg_panel": "#111114",          # Slightly elevated panel
        "bg_sidebar": "#050508",        # Sidebar background
        "bg_input": "#141418",          # Input background
        "bg_hover": "#1C1C22",          # Hover state
        "bg_glass": "rgba(255, 255, 255, 0.05)",
        "border": "rgba(255, 255, 255, 0.08)",
        "border_light": "rgba(255, 255, 255, 0.12)",
        "text_primary": "#F9F9FA",      # Crisp white
        "text_secondary": "#A1A1AA",    # Muted zinc
        "text_muted": "#52525B",        # Very muted
        "accent": "#FF5722",            # Neon Orange
        "accent_hover": "#FF7A4D",
        "accent_gradient_start": "#FF5722",
        "accent_gradient_end": "#E64A19",
        "user_bubble": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(255, 87, 34, 0.1), stop:1 rgba(255, 87, 34, 0.02))",
        "ai_bubble": "transparent",     
        "success": "#10B981",
        "warning": "#FFB300",
        "error": "#F44336",
        "scrollbar": "rgba(255, 255, 255, 0.05)",
        "scrollbar_hover": "rgba(255, 255, 255, 0.1)",
    }
}

current_theme_name = "dark"
COLORS = THEMES["dark"].copy()

GLOBAL_STYLESHEET = f"""
/* ─── Global ────────────────────────────────────────────── */
* {{
    font-family: 'Inter', '-apple-system', 'SF Pro Display', 'Segoe UI', sans-serif;
    color: {COLORS["text_primary"]};
    outline: none;
}}

QMainWindow, QDialog {{
    background-color: {COLORS["bg_darkest"]};
}}

QWidget {{
    background-color: transparent;
}}

/* ─── Tooltips ──────────────────────────────────────────── */
QToolTip {{
    background-color: #1A1A24;
    color: #E2E8F0;
    border: 1px solid #333344;
    border-radius: 6px;
    padding: 6px;
    font-family: "SF Pro Text", "Inter", sans-serif;
    font-size: 12px;
}}

/* ─── Scrollbars ────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0px 0px 0px 0px;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.1);
    min-height: 20px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(245, 158, 11, 0.5); /* Saffron glow on hover */
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
    height: 0px;
}}

/* ─── Buttons ───────────────────────────────────────────── */
QPushButton {{
    background-color: {COLORS["bg_input"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}
QPushButton:hover {{
    background-color: {COLORS["bg_hover"]};
    border: 1px solid {COLORS["border_light"]};
}}
QPushButton:pressed {{
    background-color: {COLORS["bg_panel"]};
    border: 1px solid {COLORS["accent"]};
}}

/* ─── Text Input ────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {COLORS["bg_input"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 20px;
    padding: 14px 24px;
    font-size: 15px;
    line-height: 1.5;
    selection-background-color: {COLORS["accent"]};
    selection-color: #000000;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid rgba(245, 158, 11, 0.4);
    background-color: #161616;
}}

/* ─── Action Chips ──────────────────────────────────────── */
QPushButton.actionChip {{
    background-color: {COLORS["bg_glass"]};
    color: {COLORS["text_secondary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 18px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.2px;
}}
QPushButton.actionChip:hover {{
    background-color: {COLORS["bg_hover"]};
    color: {COLORS["accent"]};
    border: 1px solid {COLORS["accent"]};
}}

/* ─── Labels ────────────────────────────────────────────── */
QLabel {{
    color: {COLORS["text_primary"]};
    font-size: 14px;
}}
QLabel#titleLabel {{
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: {COLORS["text_primary"]};
}}
QLabel#mutedLabel {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.2px;
    color: {COLORS["text_muted"]};
    text-transform: uppercase;
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

/* ─── Input Bar Container ───────────────────────────────── */
QWidget#inputBar {{
    background-color: transparent;
}}
QWidget#inputBarInner {{
    background-color: {COLORS["bg_dark"]};
    border: 1px solid {COLORS["border_light"]};
    border-radius: 26px;
}}

/* ─── Title Bar ─────────────────────────────────────────── */
QWidget#titleBar {{
    background-color: {COLORS["bg_sidebar"]};
    border-bottom: 1px solid {COLORS["border"]};
}}

"""

# ─── Component-specific styles ─────────────────────────────

CHAT_USER_BUBBLE_STYLE = f"""
    background: {COLORS["user_bubble"]};
    border: 1px solid {COLORS["border_light"]};
    border-radius: 16px;
    border-top-right-radius: 4px;
    padding: 16px 24px;
    color: {COLORS["text_primary"]};
    font-size: 15px;
    font-weight: 400;
    line-height: 1.6;
"""

CHAT_AI_BUBBLE_STYLE = f"""
    background-color: transparent;
    border: none;
    padding: 12px 0px;
    color: {COLORS["text_primary"]};
    font-size: 16px;
    font-weight: 400;
    line-height: 1.8;
    letter-spacing: 0.1px;
"""

SIDEBAR_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {COLORS["text_secondary"]};
        border: none;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: left;
        font-size: 14px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {COLORS["bg_hover"]};
        color: {COLORS["text_primary"]};
    }}
"""

SEND_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {COLORS["accent"]};
        color: #000000;
        border: none;
        border-radius: 18px;
        padding: 0px;
        font-size: 16px;
        font-weight: 800;
        min-width: 36px;
        min-height: 36px;
        max-width: 36px;
        max-height: 36px;
    }}
    QPushButton:hover {{
        background-color: {COLORS["accent_hover"]};
    }}
    QPushButton:disabled {{
        background-color: {COLORS["bg_hover"]};
        color: {COLORS["text_muted"]};
    }}
"""

ATTACH_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {COLORS["text_secondary"]};
        border: none;
        border-radius: 18px;
        padding: 0px;
        font-size: 20px;
        min-width: 36px;
        min-height: 36px;
        max-width: 36px;
        max-height: 36px;
    }}
    QPushButton:hover {{
        background-color: {COLORS["bg_hover"]};
        color: {COLORS["text_primary"]};
    }}
"""

VOICE_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {COLORS["text_secondary"]};
        border: none;
        border-radius: 18px;
        padding: 0px;
        font-size: 16px;
        min-width: 36px;
        min-height: 36px;
        max-width: 36px;
        max-height: 36px;
    }}
    QPushButton:hover {{
        background-color: {COLORS["bg_hover"]};
        color: {COLORS["text_primary"]};
    }}
    QPushButton:checked {{
        background-color: rgba(245, 158, 11, 0.15);
        color: {COLORS["accent"]};
    }}
"""

NEW_CHAT_BUTTON_STYLE = f"""
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS["accent_gradient_start"]}, stop:1 {COLORS["accent_gradient_end"]});
        color: #000000;
        border: none;
        border-radius: 8px;
        padding: 10px;
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.3px;
    }}
    QPushButton:hover {{
        background: {COLORS["accent_hover"]};
    }}
"""

# ── Web Intelligence UI Styles ─────────────────────────────

WEB_RESULT_CARD_STYLE = """
    background: rgba(255, 87, 34, 0.04);
    border: 1px solid rgba(255, 87, 34, 0.18);
    border-radius: 12px;
    padding: 10px 14px;
"""

SOURCES_PANEL_BASE_STYLE = f"""
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 8px;
"""

SOURCES_TOGGLE_STYLE = f"""
    QPushButton {{
        background: transparent;
        color: {COLORS["text_secondary"]};
        border: none;
        text-align: left;
        font-size: 12px;
        font-weight: 600;
        padding: 4px 8px;
    }}
    QPushButton:hover {{ color: {COLORS["accent"]}; }}
"""

CONFIDENCE_HIGH_STYLE = """
    background: rgba(16, 185, 129, 0.15);
    color: #10B981;
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 700;
"""

CONFIDENCE_MEDIUM_STYLE = """
    background: rgba(245, 158, 11, 0.15);
    color: #F59E0B;
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 700;
"""

CONFIDENCE_LOW_STYLE = """
    background: rgba(239, 68, 68, 0.12);
    color: #EF4444;
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 700;
"""

REALTIME_CARD_STYLE = """
    background: rgba(16, 185, 129, 0.05);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 12px;
    padding: 12px 16px;
"""

NEWS_CARD_STYLE = f"""
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 10px 14px;
"""

RESEARCH_MODE_BUTTON_STYLE = f"""
    QPushButton {{
        background: transparent;
        color: {COLORS["text_muted"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 14px;
        padding: 4px 12px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton:checked {{
        background: rgba(139, 92, 246, 0.15);
        color: #8B5CF6;
        border: 1px solid rgba(139, 92, 246, 0.4);
    }}
    QPushButton:hover {{
        border: 1px solid {COLORS["border_light"]};
        color: {COLORS["text_secondary"]};
    }}
"""

SEARCHING_BADGE_STYLE = """
    background: rgba(139, 92, 246, 0.15);
    color: #8B5CF6;
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
"""
