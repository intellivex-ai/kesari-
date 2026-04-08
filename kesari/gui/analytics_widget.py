"""
Kesari AI — Analytics Widget
A sleek dashboard dialog showing usage stats, tool activity, and system health.
"""
import sqlite3
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget, QScrollArea, QFrame,
    QGridLayout,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from kesari.config import DB_FILE
from kesari.gui.styles import COLORS

logger = logging.getLogger(__name__)

AUDIT_DB = DB_FILE.parent / "audit.db"


def _stat_card(title: str, value: str, icon: str = "", accent: str = "") -> QWidget:
    """Create a single metric card widget."""
    card = QFrame()
    card.setObjectName("statCard")
    color = accent or COLORS.get("accent_primary", "#E85D04")
    card.setStyleSheet(f"""
        QFrame#statCard {{
            background: {COLORS.get('bg_card', '#1a1a2e')};
            border: 1px solid {color}44;
            border-radius: 12px;
            padding: 4px;
        }}
    """)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(6)

    header = QLabel(f"{icon}  {title}" if icon else title)
    header.setStyleSheet(f"color: {COLORS.get('text_muted', '#888')}; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;")

    val_lbl = QLabel(value)
    val_lbl.setObjectName("statValue")
    val_lbl.setStyleSheet(f"color: {COLORS.get('text_primary', '#fff')}; font-size: 26px; font-weight: 700;")

    layout.addWidget(header)
    layout.addWidget(val_lbl)
    card.value_label = val_lbl  # allow dynamic update
    return card


class AnalyticsWidget(QDialog):
    """Full-screen analytics dialog showing productivity stats."""

    def __init__(self, parent=None, system_monitor=None):
        super().__init__(parent)
        self.system_monitor = system_monitor
        self.setWindowTitle("Kesari Analytics")
        self.setMinimumSize(680, 520)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background: {COLORS.get('bg_darkest', '#0d0d1a')};
                border-radius: 16px;
            }}
            QLabel {{
                color: {COLORS.get('text_primary', '#ffffff')};
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(20)

        # --- Header ---
        header_row = QHBoxLayout()
        title = QLabel("📊  Kesari Analytics")
        title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {COLORS.get('accent_primary', '#E85D04')};")
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setFixedSize(80, 32)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.get('accent_primary', '#E85D04')}22;
                color: {COLORS.get('accent_primary', '#E85D04')};
                border: 1px solid {COLORS.get('accent_primary', '#E85D04')}66;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS.get('accent_primary', '#E85D04')}44;
            }}
        """)
        refresh_btn.clicked.connect(self._load_data)
        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(refresh_btn)
        root.addLayout(header_row)

        # --- Metric grid ---
        self._grid = QGridLayout()
        self._grid.setSpacing(12)

        self._card_total_msgs = _stat_card("Total Messages", "—", "💬")
        self._card_conversations = _stat_card("Conversations", "—", "📁")
        self._card_tasks_done = _stat_card("Tasks Completed", "—", "✅", accent="#22c55e")
        self._card_tools_run = _stat_card("Tool Executions", "—", "⚙️", accent="#3b82f6")

        self._grid.addWidget(self._card_total_msgs,   0, 0)
        self._grid.addWidget(self._card_conversations, 0, 1)
        self._grid.addWidget(self._card_tasks_done,   1, 0)
        self._grid.addWidget(self._card_tools_run,    1, 1)
        root.addLayout(self._grid)

        # --- System Live stats (if monitor present) ---
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {COLORS.get('border', '#333')};")
        root.addWidget(sep)

        sys_title = QLabel("🖥️  Live System")
        sys_title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {COLORS.get('text_secondary', '#aaa')};")
        root.addWidget(sys_title)

        sys_row = QHBoxLayout()
        self._card_cpu = _stat_card("CPU", "—", "🔄", accent="#f59e0b")
        self._card_ram = _stat_card("RAM", "—", "💾", accent="#8b5cf6")
        self._card_disk = _stat_card("Disk", "—", "📀", accent="#06b6d4")
        sys_row.addWidget(self._card_cpu)
        sys_row.addWidget(self._card_ram)
        sys_row.addWidget(self._card_disk)
        root.addLayout(sys_row)

        # --- Top tools list ---
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"color: {COLORS.get('border', '#333')};")
        root.addWidget(sep2)

        tools_title = QLabel("🔧  Most Used Tools")
        tools_title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {COLORS.get('text_secondary', '#aaa')};")
        root.addWidget(tools_title)

        self._tools_container = QWidget()
        self._tools_layout = QVBoxLayout(self._tools_container)
        self._tools_layout.setContentsMargins(0, 0, 0, 0)
        self._tools_layout.setSpacing(4)
        root.addWidget(self._tools_container)

        root.addStretch()

        self._load_data()
        # Auto-refresh system stats every 3 seconds while open
        self._sys_timer = QTimer(self)
        self._sys_timer.timeout.connect(self._refresh_system)
        self._sys_timer.start(3000)

    # ── Data Loading ──────────────────────────────────────

    def _load_data(self):
        self._load_memory_stats()
        self._load_tool_stats()
        self._refresh_system()

    def _load_memory_stats(self):
        try:
            with sqlite3.connect(str(DB_FILE)) as conn:
                total_msgs = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
                convs = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
                try:
                    tasks_done = conn.execute(
                        "SELECT COUNT(*) FROM tasks WHERE status='completed'"
                    ).fetchone()[0]
                except Exception:
                    tasks_done = 0

            self._card_total_msgs.value_label.setText(str(total_msgs))
            self._card_conversations.value_label.setText(str(convs))
            self._card_tasks_done.value_label.setText(str(tasks_done))
        except Exception as e:
            logger.error(f"Analytics memory load error: {e}")

    def _load_tool_stats(self):
        if not AUDIT_DB.exists():
            self._card_tools_run.value_label.setText("0")
            return
        try:
            with sqlite3.connect(str(AUDIT_DB)) as conn:
                total_runs = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
                top_tools = conn.execute(
                    "SELECT tool_name, COUNT(*) as cnt FROM audit_log GROUP BY tool_name ORDER BY cnt DESC LIMIT 5"
                ).fetchall()

            self._card_tools_run.value_label.setText(str(total_runs))

            # Clear old rows
            while self._tools_layout.count():
                item = self._tools_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            for tool_name, count in top_tools:
                row = QLabel(f"  {tool_name}  —  {count}×")
                row.setStyleSheet(f"color: {COLORS.get('text_secondary', '#aaa')}; font-size: 12px; padding: 3px 0;")
                self._tools_layout.addWidget(row)
        except Exception as e:
            logger.error(f"Analytics tool stats error: {e}")

    def _refresh_system(self):
        if not self.system_monitor:
            return
        try:
            snap = self.system_monitor.get_snapshot()
            self._card_cpu.value_label.setText(f"{snap['cpu_percent']:.1f}%")
            self._card_ram.value_label.setText(f"{snap['ram_percent']:.1f}%")
            self._card_disk.value_label.setText(f"{snap['disk_percent']:.1f}%")
        except Exception as e:
            logger.error(f"System refresh error: {e}")

    def closeEvent(self, event):
        self._sys_timer.stop()
        super().closeEvent(event)
