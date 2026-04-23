"""
Kesari AI — Deep Context Awareness (OCR)
Reads text from the primary screen using mss and pytesseract.
"""
import logging
import mss
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

# Default install path on Windows. If it's in PATH, this isn't strictly necessary, but helpful.
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def read_screen_text() -> str:
    """
    Captures the primary monitor and runs OCR to extract all visible text.
    """
    logger.info("Running screen OCR...")
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # 1 is primary monitor
            sct_img = sct.grab(monitor)
            
            # Convert mss screenshot to PIL Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
            # Extract text
            text = pytesseract.image_to_string(img)
            logger.info("Screen OCR completed.")
            return text.strip()
            
    except pytesseract.TesseractNotFoundError:
        msg = "[Error: Tesseract OCR is not installed or not in PATH. Please install from https://github.com/UB-Mannheim/tesseract/wiki]"
        logger.error(msg)
        return msg
    except Exception as e:
        msg = f"[OCR Error: {str(e)}]"
        logger.error(msg)
        return msg
