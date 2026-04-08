"""
Kesari AI — Profile Tools
Allow the AI to proactively update the user's personality and preferences memory.
"""
from typing import Any
import logging

from kesari.tools.base_tool import BaseTool
from kesari.memory.user_profile import UserProfileManager

logger = logging.getLogger(__name__)

class UpdateProfileTool(BaseTool):
    """Tool to update the user's permanent profile facts and preferences."""

    def __init__(self, profile_manager: UserProfileManager):
        self.profile = profile_manager

    @property
    def name(self) -> str:
        return "update_user_profile"

    @property
    def description(self) -> str:
        return (
            "Store a preference, name, or fact about the user into permanent memory. "
            "Use this proactively when the user tells you about themselves, their workflow, "
            "how they like responses, or any personal details."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "'name', 'preference', or 'fact'",
                    "enum": ["name", "preference", "fact"]
                },
                "value": {
                    "type": "string",
                    "description": "The value to store. For 'name', just their name. For 'preference'/'fact', a short descriptive sentence."
                }
            },
            "required": ["category", "value"]
        }

    async def execute(self, category: str, value: str) -> dict[str, Any]:
        try:
            if category == "name":
                self.profile.set_name(value)
            elif category == "preference":
                self.profile.add_preference(value)
            elif category == "fact":
                self.profile.add_fact(value)
            else:
                return {"error": "Invalid category."}
            
            return {"status": "success", "message": f"{category.capitalize()} updated to '{value}'"}
        except Exception as e:
            logger.error(f"Failed to update profile: {e}")
            return {"error": str(e)}
