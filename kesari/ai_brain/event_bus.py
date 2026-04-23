"""
Kesari AI — Event Bus
Manages proactive AI triggers from system events, time changes, and user habits.
"""
from typing import Callable, Dict, List
import logging

logger = logging.getLogger("kesari.event_bus")

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to an event."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, **kwargs):
        """Publish an event to all subscribers."""
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(**kwargs)
                except Exception as e:
                    logger.error(f"Error in event subscriber for {event_type}: {e}")

    def trigger_proactive_suggestion(self, suggestion_text: str):
        """Helper to specifically trigger a proactive AI suggestion."""
        self.publish("proactive_suggestion", text=suggestion_text)
