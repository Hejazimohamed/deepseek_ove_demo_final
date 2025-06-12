from PIL import Image, UnidentifiedImageError
from image_preprocess import preprocess_image_advanced
import pytesseract

# تحديد المسار الصريح لـ Tesseract (ضروري لـ GitHub Actions)
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

try:
    if not pytesseract.get_tesseract_version():
        raise EnvironmentError("Tesseract OCR غير مثبت أو غير مضاف للمسار.")
except pytesseract.TesseractNotFoundError:
    raise EnvironmentError("Tesseract OCR غير مثبت أو غير مضاف للمسار.")

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
    return pytesseract.image_to_string(img, lang='eng+ara')