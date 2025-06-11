import sys
import os
import tempfile
from PIL import Image
from ocr_logic import preprocess_image_advanced

# تأكد من إضافة مسار المشروع للواردات
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_preprocess_image_advanced_returns_image():
    # أنشئ صورة بيضاء بسيطة للاختبار
    img = Image.new('RGB', (100, 100), color='white')

    # أنشئ ملف مؤقت لحفظ الصورة
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        temp_path = tmp.name
        img.save(temp_path)

    try:
        # نفّذ دالة المعالجة على مسار الصورة
        result = preprocess_image_advanced(temp_path)

        # تحقق من أن النتيجة صورة
        assert isinstance(result, Image.Image)

        # تحقق من أبعاد الصورة
        assert result.size == img.size

        # تحقق من نمط الصورة بعد التحويل
        assert result.mode in ('L', 'RGB', '1')
    finally:
        # نظف الملف المؤقت
        if os.path.exists(temp_path):
            os.remove(temp_path)
