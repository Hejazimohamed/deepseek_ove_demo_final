# __init__.py (محتوى اختياري)
from .ocr_parallel_ui import *  # لتصدير كل الدوال/الكلاسات
from images_fpr_test import ocr_parallel_ui  # صحيح مع وجود __init__.py
__all__ = ['func1', 'func2']   # تحديد ما يُصدر عند استيراد الحزمة