"""
Kesari AI — System Tray Manager
Handles the system tray icon, context menu, and background running state.
"""
import logging
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QStyle
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("kesari.tray")

class TrayManager(QObject):
    show_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Check if system tray is actually available on this OS
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray not available.")
            self.tray_icon = None
            return

        self.tray_icon = QSystemTrayIcon(self)
        
        # We try to use the application window icon if one is set, otherwise a generic computer icon
        app_icon = QApplication.windowIcon()
        if app_icon.isNull():
            app_icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(app_icon)
        
        self.tray_icon.setToolTip("Kesari AI")
        
        # Build context menu
        self.menu = QMenu()
        
        self.show_action = QAction("Show Kesari AI", self)
        self.show_action.triggered.connect(self.show_requested.emit)
        self.menu.addAction(self.show_action)
        
        self.menu.addSeparator()
        
        self.quit_action = QAction("Quit", self)
        self.quit_action.triggered.connect(self.quit_requested.emit)
        self.menu.addAction(self.quit_action)
        
        self.tray_icon.setContextMenu(self.menu)
        
        # Connect double-click to show
        self.tray_icon.activated.connect(self._on_activated)
        
        self.tray_icon.show()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_requested.emit()
            
    def show_message(self, title: str, message: str):
        """Show an OS notification via the system tray."""
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 3000)
