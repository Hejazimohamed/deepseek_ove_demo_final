from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np

def preprocess_image_advanced(image_path):
    """
    تحسين الصورة عبر مجموعة من الفلاتر لتحسين نتائج OCR.
    """

    # فتح الصورة وتحويلها إلى تدرج الرمادي
    image = Image.open(image_path).convert("L")

    # تطبيق فلتر تقليل الضوضاء
    image = image.filter(ImageFilter.MedianFilter())

    # تعزيز التباين
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)

    # تحويل الصورة إلى مصفوفة NumPy لمزيد من المعالجة
    img_np = np.array(image)

    # تطبيق العتبة الثنائية باستخدام Otsu
    _, thresh = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # تحويل النتيجة إلى كائن صورة PIL
    final_image = Image.fromarray(thresh)
    return final_image
