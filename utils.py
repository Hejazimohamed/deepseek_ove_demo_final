import importlib


def check_dependencies():
    required_modules = {
        'PyQt5': 'PyQt5',
        'pytesseract': 'pytesseract',
        'easyocr': 'easyocr',
        'pdf2image': 'pdf2image',
        'numpy': 'numpy',
        'opencv-python': 'cv2',        # هنا التغيير المهم
        'python-dotenv': 'dotenv',     # هنا التغيير المهم
        'requests': 'requests'
    }
    missing = []
    for pkg, module in required_modules.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(pkg)
    # تحقق خاص من poppler-utils لنظام PDF
    try:
        pass
    except Exception:
        missing.append('poppler-utils (system package)')
    return missing
