"""
Kesari AI — Base Tool
Abstract base class for all tools.
"""
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Base class for all Kesari AI tools.
    Subclass this and implement `execute()`.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier (e.g. 'open_app')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """JSON Schema for the tool's parameters."""
        ...

    @property
    def definition(self) -> dict:
        """OpenAI function-calling definition."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    @abstractmethod
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute the tool and return a result dict."""
        ...

    @property
    def requires_confirmation(self) -> bool:
        """Override to True for dangerous actions."""
        return False
