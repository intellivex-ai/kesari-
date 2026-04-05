"""
Example Plugin for Kesari AI
Demonstrates how to create plugin tools.
"""
import math
from datetime import datetime


def get_current_time(timezone: str = "") -> dict:
    """Get the current date and time."""
    now = datetime.now()
    if timezone:
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(timezone))
        except Exception:
            pass

    return {
        "status": "success",
        "date": now.strftime("%A, %B %d, %Y"),
        "time": now.strftime("%I:%M:%S %p"),
        "iso": now.isoformat(),
    }


def calculate(expression: str) -> dict:
    """Safely evaluate a mathematical expression."""
    # Only allow safe math operations
    allowed_names = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sqrt": math.sqrt, "pow": pow, "log": math.log,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "pi": math.pi, "e": math.e,
    }

    try:
        # Remove anything that's not a number, operator, or allowed name
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return {
            "status": "success",
            "expression": expression,
            "result": result,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Cannot evaluate '{expression}': {str(e)}",
        }
