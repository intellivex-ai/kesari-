"""
Kesari AI — Screen Context Tool
Allows the AI to capture a screenshot to gain visual context.
"""
import io
import base64
import logging
from typing import Any
import mss
from PIL import Image

from kesari.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class CaptureScreenTool(BaseTool):
    """
    Takes a screenshot of the primary monitor and returns its base64 representation.
    The response format is handled specifically by the AI clients to convert it into a multimodal vision payload.
    """

    @property
    def name(self) -> str:
        return "capture_screen"

    @property
    def description(self) -> str:
        return (
            "Take a screenshot of the user's primary screen. "
            "Use this tool when the user asks you to look at their screen, read something visible, "
            "or if you need visual context of their current desktop state."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, **kwargs) -> dict[str, Any]:
        try:
            with mss.mss() as sct:
                # monitor 1 is the primary monitor, monitor 0 is all monitors combined
                monitor = sct.monitors[1]
                sct_img = sct.grab(monitor)
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                # Resize if it's too large to save tokens and bandwidth
                max_dim = 1920
                if img.width > max_dim or img.height > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                
                buffer = io.BytesIO()
                # Use JPEG to compress
                img.save(buffer, format="JPEG", quality=85)
                b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                logger.info(f"Screen captured successfully: {img.width}x{img.height}")
                
                return {
                    "image_base64": b64_str,
                    "media_type": "image/jpeg",
                    "description": "Screen captured successfully."
                }
        except Exception as e:
            logger.error(f"Failed to capture screen: {e}")
            return {"error": str(e)}
