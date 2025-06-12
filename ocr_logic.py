from PIL import Image, UnidentifiedImageError
from image_preprocess import preprocess_image_advanced
import pytesseract
import os
import logging

logger = logging.getLogger(__name__)

class TesseractNotConfiguredError(Exception):
    pass

def configure_tesseract():
    """Configure Tesseract path dynamically"""
    possible_paths = [
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
        '/opt/homebrew/bin/tesseract',
        'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
    ]
    
    tesseract_cmd = os.environ.get('TESSERACT_CMD')
    if tesseract_cmd and os.path.exists(tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        return

    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return

    raise TesseractNotConfiguredError(
        "Tesseract not found. Please install it or set TESSERACT_CMD environment variable."
    )

try:
    configure_tesseract()
    pytesseract.get_tesseract_version()
except Exception as e:
    logger.error(f"Tesseract configuration failed: {str(e)}")
    raise TesseractNotConfiguredError(f"Tesseract OCR is not properly configured: {str(e)}")

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
    try:
        img = preprocess_image_advanced(image_path)
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}")
        img = Image.open(image_path)
    
    try:
        return pytesseract.image_to_string(img, lang='eng+ara')
    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        raise TesseractNotConfiguredError(f"OCR processing error: {str(e)}")