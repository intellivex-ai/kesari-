"""
Kesari AI — User Profile
Maintains persistent user facts and preferences to allow personality learning.
"""
import os
import json
import logging
from pathlib import Path

from kesari.config import APP_DIR

logger = logging.getLogger(__name__)


class UserProfileManager:
    """Manages persistent context facts about the user."""
    
    def __init__(self, profile_path: str | None = None):
        self.profile_path = Path(profile_path) if profile_path else APP_DIR / "user_profile.json"
        self._data: dict = {
            "name": "User",
            "preferences": [],
            "facts": []
        }
        self.load()

    def load(self):
        if self.profile_path.exists():
            try:
                with open(self.profile_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._data.update(data)
                logger.debug("User profile loaded.")
            except Exception as e:
                logger.error(f"Failed to load user profile: {e}")

    def save(self):
        try:
            with open(self.profile_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save user profile: {e}")

    def add_preference(self, pref_string: str):
        """Add a general workflow or tone preference."""
        if pref_string not in self._data["preferences"]:
            self._data["preferences"].append(pref_string)
            self.save()

    def add_fact(self, fact_string: str):
        """Add a concrete fact about the user."""
        if fact_string not in self._data["facts"]:
            self._data["facts"].append(fact_string)
            self.save()
            
    def set_name(self, name: str):
        self._data["name"] = name
        self.save()

    def get_context_string(self) -> str:
        """Constructs a context string for injection into the system prompt."""
        if not self._data["preferences"] and not self._data["facts"]:
            return f"The user's name is {self._data['name']}."
            
        lines = [f"The user's name is {self._data['name']}. You should remember the following rules and facts about them:"]
        
        if self._data["preferences"]:
            lines.append("\nPreferences:")
            for p in self._data["preferences"]:
                lines.append(f"- {p}")
                
        if self._data["facts"]:
            lines.append("\nFacts:")
            for f in self._data["facts"]:
                lines.append(f"- {f}")
                
        return "\n".join(lines)
