"""
Kesari AI — Proactive Engine
Runs continuously in the background, evaluating triggers.
"""
import logging
from datetime import datetime
from PySide6.QtCore import QObject, QTimer, Signal

from kesari.automation.context_awareness import ContextAwareness

logger = logging.getLogger(__name__)

class ProactiveEngine(QObject):
    proactive_suggestion = Signal(str, str) # title, message

    def __init__(self, focus_system):
        super().__init__()
        self.focus_system = focus_system
        self.has_suggested_night = False
        self.wasted_time_mins = 0
        
        from kesari.memory.pattern_learner import PatternLearner
        self.pattern_learner = PatternLearner()
        self.last_predicted_hour = -1

        self.polling_timer = QTimer(self)
        self.polling_timer.timeout.connect(self._evaluate_rules)
        self.polling_timer.start(60000) # Check every 1 minute

    def _evaluate_rules(self):
        now = datetime.now()
        
        # Log app every 5 mins
        if now.minute % 5 == 0:
            self.pattern_learner.log_active_app()
            
        # Pattern Prediction (once per hour at the start of the hour)
        if now.minute < 5 and now.hour != self.last_predicted_hour:
            self.last_predicted_hour = now.hour
            predicted_app = self.pattern_learner.predict_likely_app(now.weekday(), now.hour)
            if predicted_app:
                # E.g., if we predict Code, ask if they want Coding Mode
                self.proactive_suggestion.emit(
                    "Pattern Detected",
                    f"You usually open {predicted_app} around this time. Ready to launch it?"
                )
        
        # Rule 1: Night Routine
        if now.hour >= 23 and not self.has_suggested_night:
            self.proactive_suggestion.emit(
                "Night Routine", 
                "It's getting late. Would you like me to close your apps and clean the RAM?"
            )
            self.has_suggested_night = True
            
        # Reset night routine flag in the morning
        if now.hour < 5:
            self.has_suggested_night = False

        # Rule 2: Distraction tracking (only if not in focus mode)
        if not self.focus_system.is_focused:
            active_app = ContextAwareness.get_active_app_name()
            if active_app in ["youtube", "discord"]:
                self.wasted_time_mins += 1
                if self.wasted_time_mins >= 30: # 30 mins wasted
                    self.proactive_suggestion.emit(
                        "Focus Alert", 
                        "You've been distracted for 30 minutes. Should we start Study Mode?"
                    )
                    self.wasted_time_mins = 0 # reset after suggesting
            else:
                self.wasted_time_mins = max(0, self.wasted_time_mins - 1)
