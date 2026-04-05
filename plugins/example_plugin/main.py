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
    import re
    import multiprocessing
    try:
        import simpleeval
    except ImportError:
        return {"status": "error", "message": "simpleeval not installed - required for safe sandbox"}

    if len(expression) > 100:
        return {"status": "error", "message": "Expression too long (max 100 chars)"}

    # Pre-validate to reject risky operators and very large numeric literals
    if "**" in expression or "pow(" in expression.lower():
        return {"status": "error", "message": "Exponentiation is not allowed"}
    if re.search(r'\d{10,}', expression):
        return {"status": "error", "message": "Numeric literals are too large"}

    # Relax \w to explicit alphabetical functions and operators
    if not re.match(r'^[\d\s\.\+\-\*\/\(\)a-zA-Z]+$', expression) or '__' in expression:
        return {"status": "error", "message": "Invalid characters or attributes in expression"}

    allowed_names = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sqrt": math.sqrt, "log": math.log,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "pi": math.pi, "e": math.e,
    }

    def _eval_worker(expr, q):
        try:
            s = simpleeval.SimpleEval(names=allowed_names)
            res = s.eval(expr)
            q.put({"status": "success", "result": res})
        except Exception as err:
            q.put({"status": "error", "message": str(err)})

    try:
        q = multiprocessing.Queue()
        p = multiprocessing.Process(target=_eval_worker, args=(expression, q))
        p.start()
        p.join(timeout=2.0)
        
        if p.is_alive():
            p.terminate()
            p.join()
            return {"status": "error", "message": "Evaluation timed out"}
        
        if not q.empty():
            res = q.get()
            if res["status"] == "error":
                raise ValueError(res["message"])
            result = res["result"]
        else:
            raise ValueError("Evaluation failed unexpectedly")
            
        # Guard against huge outputs forming
        if isinstance(result, (int, float)) and len(str(result)) > 1000:
            raise ValueError("Result too large")
            
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
