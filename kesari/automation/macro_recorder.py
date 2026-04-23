"""
Kesari AI — Macro Recorder
Records mouse and keyboard events with timing, and replays them.
"""
import json
import logging
import os
import time
import threading
from typing import List, Dict, Any
from pynput import keyboard, mouse

logger = logging.getLogger(__name__)

MACRO_DIR = os.path.expanduser("~/.kesari_ai/macros")
os.makedirs(MACRO_DIR, exist_ok=True)

class MacroRecorder:
    def __init__(self):
        self._recording = False
        self._events: List[Dict[str, Any]] = []
        self._start_time = 0.0
        
        self._mouse_listener = None
        self._keyboard_listener = None
        
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
        
        self.current_macro_name = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self, name: str):
        if self._recording:
            return
            
        self.current_macro_name = name
        self._events = []
        self._recording = True
        self._start_time = time.time()
        
        # Start listeners
        self._mouse_listener = mouse.Listener(
            on_click=self._on_click,
            on_scroll=self._on_scroll
        )
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        
        self._mouse_listener.start()
        self._keyboard_listener.start()
        logger.info(f"Started recording macro: {name}")

    def stop_recording(self):
        if not self._recording:
            return
            
        self._recording = False
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            
        # Clean up events (remove the hotkey strokes that stopped it, if any)
        # We will assume the user used Ctrl+Space or something, so we'll trim the last few keyboard events just in case
        
        # Save to disk
        if self.current_macro_name and self._events:
            path = os.path.join(MACRO_DIR, f"{self.current_macro_name}.json")
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self._events, f, indent=2)
                logger.info(f"Saved macro to {path}")
            except Exception as e:
                logger.error(f"Failed to save macro: {e}")
                
        self.current_macro_name = None

    def play_macro(self, name: str):
        path = os.path.join(MACRO_DIR, f"{name}.json")
        if not os.path.exists(path):
            logger.error(f"Macro {name} not found.")
            return False
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                events = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load macro: {e}")
            return False
            
        logger.info(f"Playing macro: {name}")
        threading.Thread(target=self._replay_thread, args=(events,), daemon=True).start()
        return True

    def _replay_thread(self, events: List[Dict[str, Any]]):
        if not events:
            return
            
        start_time = time.time()
        for i, event in enumerate(events):
            # Calculate sleep
            target_time = start_time + event['time_offset']
            now = time.time()
            if target_time > now:
                time.sleep(target_time - now)
                
            try:
                self._execute_event(event)
            except Exception as e:
                logger.error(f"Error executing event {event}: {e}")
                
        logger.info("Macro playback finished.")

    def _execute_event(self, event: Dict[str, Any]):
        etype = event.get('type')
        
        if etype == 'mouse_click':
            # Jump to position
            self.mouse_controller.position = (event['x'], event['y'])
            # We map string back to Button
            btn = getattr(mouse.Button, event['button'].split('.')[-1], mouse.Button.left)
            if event['pressed']:
                self.mouse_controller.press(btn)
            else:
                self.mouse_controller.release(btn)
                
        elif etype == 'mouse_scroll':
            self.mouse_controller.position = (event['x'], event['y'])
            self.mouse_controller.scroll(event['dx'], event['dy'])
            
        elif etype in ('key_press', 'key_release'):
            key_str = event['key']
            # Convert string back to Key or KeyCode
            # Handling standard keys vs special keys
            key = None
            if key_str.startswith("Key."):
                key = getattr(keyboard.Key, key_str.split('.')[-1], None)
            else:
                # It's a character
                key = keyboard.KeyCode.from_char(key_str.strip("'"))
                
            if key:
                if etype == 'key_press':
                    self.keyboard_controller.press(key)
                else:
                    self.keyboard_controller.release(key)

    # ── Listeners ──────────────────────────────────────────

    def _add_event(self, event_data: dict):
        if not self._recording:
            return
        event_data['time_offset'] = time.time() - self._start_time
        self._events.append(event_data)

    def _on_click(self, x, y, button, pressed):
        self._add_event({
            'type': 'mouse_click',
            'x': x,
            'y': y,
            'button': str(button),
            'pressed': pressed
        })

    def _on_scroll(self, x, y, dx, dy):
        self._add_event({
            'type': 'mouse_scroll',
            'x': x,
            'y': y,
            'dx': dx,
            'dy': dy
        })

    def _on_press(self, key):
        self._add_event({
            'type': 'key_press',
            'key': str(key)
        })

    def _on_release(self, key):
        self._add_event({
            'type': 'key_release',
            'key': str(key)
        })
