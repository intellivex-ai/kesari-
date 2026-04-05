"""
Kesari AI — Settings Dialog
Configuration panel for API keys, model, voice, and theme settings.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QFrame, QTabWidget,
    QWidget, QFormLayout, QGroupBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from kesari.config import settings
from kesari.gui.styles import COLORS, SEND_BUTTON_STYLE


class SettingsDialog(QDialog):
    """Settings dialog for Kesari AI."""

    settings_saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings — Kesari AI")
        self.setFixedSize(520, 520)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS["bg_dark"]};
                border: 1px solid {COLORS["border_light"]};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # ── Title ────────────────────────────────────────
        title = QLabel("⚙  Settings")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {COLORS["text_primary"]};
            padding-bottom: 4px;
        """)
        layout.addWidget(title)

        # ── Tabs ─────────────────────────────────────────
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
                background-color: {COLORS["bg_panel"]};
            }}
            QTabBar::tab {{
                background-color: {COLORS["bg_input"]};
                color: {COLORS["text_secondary"]};
                border: 1px solid {COLORS["border"]};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS["bg_panel"]};
                color: {COLORS["text_primary"]};
            }}
        """)

        # ── API Keys Tab ─────────────────────────────────
        api_tab = QWidget()
        api_layout = QFormLayout(api_tab)
        api_layout.setSpacing(12)
        api_layout.setContentsMargins(16, 16, 16, 16)

        self._openrouter_key = QLineEdit(settings.get("openrouter_api_key", ""))
        self._openrouter_key.setEchoMode(QLineEdit.Password)
        self._openrouter_key.setPlaceholderText("sk-or-...")
        api_layout.addRow("OpenRouter API Key:", self._openrouter_key)

        self._sarvam_key = QLineEdit(settings.get("sarvam_api_key", ""))
        self._sarvam_key.setEchoMode(QLineEdit.Password)
        self._sarvam_key.setPlaceholderText("Your Sarvam AI key")
        api_layout.addRow("Sarvam AI Key:", self._sarvam_key)

        tabs.addTab(api_tab, "🔑 API Keys")

        # ── Model Tab ────────────────────────────────────
        model_tab = QWidget()
        model_layout = QFormLayout(model_tab)
        model_layout.setSpacing(12)
        model_layout.setContentsMargins(16, 16, 16, 16)

        self._model_combo = QComboBox()
        self._model_combo.addItems([
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-haiku",
            "meta-llama/llama-3.1-70b-instruct",
            "meta-llama/llama-3.1-8b-instruct",
            "google/gemini-pro-1.5",
            "google/gemini-flash-1.5",
            "mistralai/mistral-large",
        ])
        current_model = settings.get("default_model", "openai/gpt-4o")
        idx = self._model_combo.findText(current_model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        else:
            self._model_combo.setEditText(current_model)
        self._model_combo.setEditable(True)
        model_layout.addRow("Default Model:", self._model_combo)

        tabs.addTab(model_tab, "🤖 Model")

        # ── Voice Tab ────────────────────────────────────
        voice_tab = QWidget()
        voice_layout = QFormLayout(voice_tab)
        voice_layout.setSpacing(12)
        voice_layout.setContentsMargins(16, 16, 16, 16)

        self._tts_lang = QComboBox()
        self._tts_lang.addItems(["hi-IN", "en-IN", "ta-IN", "te-IN", "kn-IN", "ml-IN", "bn-IN"])
        current_lang = settings.get("tts_language", "hi-IN")
        lang_idx = self._tts_lang.findText(current_lang)
        if lang_idx >= 0:
            self._tts_lang.setCurrentIndex(lang_idx)
        voice_layout.addRow("TTS Language:", self._tts_lang)

        self._tts_speaker = QComboBox()
        self._tts_speaker.addItems(["meera", "pavithra", "maitreyi", "arvind", "karthik"])
        current_speaker = settings.get("tts_speaker", "meera")
        spk_idx = self._tts_speaker.findText(current_speaker)
        if spk_idx >= 0:
            self._tts_speaker.setCurrentIndex(spk_idx)
        voice_layout.addRow("Speaker Voice:", self._tts_speaker)

        self._stt_lang = QComboBox()
        self._stt_lang.addItems(["hi-IN", "en-IN", "ta-IN", "te-IN", "kn-IN", "bn-IN"])
        current_stt = settings.get("stt_language", "hi-IN")
        stt_idx = self._stt_lang.findText(current_stt)
        if stt_idx >= 0:
            self._stt_lang.setCurrentIndex(stt_idx)
        voice_layout.addRow("STT Language:", self._stt_lang)

        tabs.addTab(voice_tab, "🎤 Voice")

        # ── Security Tab ─────────────────────────────────
        sec_tab = QWidget()
        sec_layout = QVBoxLayout(sec_tab)
        sec_layout.setSpacing(12)
        sec_layout.setContentsMargins(16, 16, 16, 16)

        self._confirm_check = QCheckBox("Confirm before dangerous actions (shutdown, delete, etc.)")
        self._confirm_check.setChecked(settings.get("confirm_dangerous_actions", True))
        self._confirm_check.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px;")
        sec_layout.addWidget(self._confirm_check)
        sec_layout.addStretch()

        tabs.addTab(sec_tab, "🔐 Security")

        layout.addWidget(tabs, stretch=1)

        # ── Buttons ──────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(QCursor(Qt.PointingHandCursor))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("accentButton")
        save_btn.setCursor(QCursor(Qt.PointingHandCursor))
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _save(self):
        settings["openrouter_api_key"] = self._openrouter_key.text().strip()
        settings["sarvam_api_key"] = self._sarvam_key.text().strip()
        settings["default_model"] = self._model_combo.currentText().strip()
        settings["tts_language"] = self._tts_lang.currentText()
        settings["tts_speaker"] = self._tts_speaker.currentText()
        settings["stt_language"] = self._stt_lang.currentText()
        settings["confirm_dangerous_actions"] = self._confirm_check.isChecked()
        settings.save()
        self.settings_saved.emit()
        self.accept()
