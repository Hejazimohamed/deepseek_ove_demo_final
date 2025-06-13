# ocr_logic.py
from PIL import Image, UnidentifiedImageError
import os
import logging
import subprocess

logger = logging.getLogger(__name__)

class TesseractNotConfiguredError(Exception):
    pass

def configure_tesseract():
    """Configure Tesseract path dynamically"""
    try:
        import pytesseract
    except ImportError:
        raise TesseractNotConfiguredError("pytesseract package not installed")

    tesseract_cmd = os.environ.get('TESSERACT_CMD')
    possible_paths = [
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
        '/opt/homebrew/bin/tesseract',
        'C:\\Program Files\\Tesseract-OCR\\tesseract.exe',
        '/bin/tesseract',
        '/usr/share/tesseract-ocr/tesseract'
    ]

    try:
        cmd = 'where' if os.name == 'nt' else 'which'
        detected_path = subprocess.check_output(
            [cmd, 'tesseract'], stderr=subprocess.DEVNULL
        ).decode().strip()
        if detected_path:
            possible_paths.insert(0, detected_path)
    except Exception:
        pass

    for path in filter(None, [tesseract_cmd] + possible_paths):
        try:
            if path and os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                logger.info(f"Using Tesseract at: {path}")
                return path
        except Exception as e:
            logger.warning(f"Path check failed for {path}: {str(e)}")
            continue

    raise TesseractNotConfiguredError(
        "Tesseract not found. Please install it or set TESSERACT_CMD environment variable.\n"
        "Installation instructions:\n"
        "- Linux: sudo apt install tesseract-ocr\n"
        "- Mac: brew install tesseract\n"
        "- Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki"
    )

try:
    tesseract_path = configure_tesseract()
    import pytesseract
    logger.info(f"Tesseract version: {pytesseract.get_tesseract_version()}")
except Exception as e:
    logger.error(f"Tesseract configuration failed: {str(e)}")
    pytesseract = None

class EasyOCRSingleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(EasyOCRSingleton, cls).__new__(cls)
        return cls._instance

def open_multi_page_image(path):
    try:
        return Image.open(path)
    except UnidentifiedImageError:
        raise ValueError("Cannot open file as multi-page image")

def extract_text_from_image(image_path):
    if pytesseract is None:
        raise TesseractNotConfiguredError("Tesseract OCR is not properly configured")

    try:
        from image_preprocess import preprocess_image_advanced
        img = preprocess_image_advanced(image_path)
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}")
        img = Image.open(image_path)

    try:
        return pytesseract.image_to_string(img, lang='eng+ara')
    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        raise TesseractNotConfiguredError(f"OCR processing error: {str(e)}")