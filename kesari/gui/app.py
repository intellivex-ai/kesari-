"""
Kesari AI — Application Entry (GUI Setup)
Initializes QApplication with theme, fonts, and event loop.
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtCore import Qt

from kesari.gui.styles import GLOBAL_STYLESHEET


def create_application(argv: list[str] | None = None) -> QApplication:
    """Create and configure the QApplication instance."""
    if argv is None:
        argv = sys.argv

    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(argv)
    app.setApplicationName("Kesari AI")
    app.setOrganizationName("KesariAI")
    app.setApplicationVersion("1.0.0")

    # ── Font ──────────────────────────────────────────────
    # Try to load Inter; fall back to Segoe UI (Windows) or system default
    font_id = QFontDatabase.addApplicationFont(":/fonts/Inter-Variable.ttf")
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    
    if families:
        app.setFont(QFont(families[0], 10))
    else:
        # Fallback
        fallback = QFont("Segoe UI", 10)
        fallback.setHintingPreference(QFont.PreferNoHinting)
        app.setFont(fallback)

    # ── Stylesheet ────────────────────────────────────────
    app.setStyleSheet(GLOBAL_STYLESHEET)

    return app
