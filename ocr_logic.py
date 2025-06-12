from PIL import Image, UnidentifiedImageError
from image_preprocess import preprocess_image_advanced
import pytesseract
import os

class TesseractNotConfiguredError(Exception):
    """استثناء مخصص لأخطاء تكوين Tesseract"""
    pass

def configure_tesseract():
    """دالة لضبط مسار Tesseract بشكل ديناميكي"""
    # قائمة بالمسارات المحتملة لـ Tesseract
    possible_paths = [
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
        'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
    ]
    
    # التحقق من وجود Tesseract في المسارات المحددة
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return
    
    raise TesseractNotConfiguredError(
        "لم يتم العثور على Tesseract في المسارات المتوقعة.\n"
        "يرجى تثبيت Tesseract أو ضبط المسار يدويًا."
    )

try:
    configure_tesseract()
    pytesseract.get_tesseract_version()
except (pytesseract.TesseractNotFoundError, TesseractNotConfiguredError) as e:
    raise TesseractNotConfiguredError(str(e))

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
        raise ValueError("تعذر فتح الملف كصورة متعددة الصفحات")

def extract_text_from_image(image_path):
    try:
        img = preprocess_image_advanced(image_path)
    except Exception as e:
        print(f"⚠️ خطأ في التحسين المسبق للصورة: {e}")
        img = Image.open(image_path)
    
    try:
        return pytesseract.image_to_string(img, lang='eng+ara')
    except pytesseract.TesseractNotFoundError:
        raise TesseractNotConfiguredError("فشل في استدعاء Tesseract أثناء معالجة الصورة")