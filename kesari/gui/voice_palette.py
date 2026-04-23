"""
Kesari AI — Voice Palette
Instant walkie-talkie style voice command execution.
"""
import logging
from pynput import keyboard
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

class VoicePalette(QObject):
    voice_start_requested = Signal()
    voice_stop_requested = Signal()

    def __init__(self):
        super().__init__()
        self.is_recording = False
        
        # Modifier state tracking
        self.ctrl_pressed = False
        self.shift_pressed = False
        self.space_pressed = False
        
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.daemon = True
        self.listener.start()

    def on_press(self, key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.ctrl_pressed = True
        elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
            self.shift_pressed = True
        elif key == keyboard.Key.space:
            self.space_pressed = True
            
        if self.ctrl_pressed and self.shift_pressed and self.space_pressed and not self.is_recording:
            self.is_recording = True
            self.voice_start_requested.emit()

    def on_release(self, key):
        was_recording = self.is_recording
        
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.ctrl_pressed = False
        elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
            self.shift_pressed = False
        elif key == keyboard.Key.space:
            self.space_pressed = False
            
        if was_recording and not (self.ctrl_pressed and self.shift_pressed and self.space_pressed):
            self.is_recording = False
            self.voice_stop_requested.emit()
