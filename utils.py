import importlib
import os
import sys
import shutil
import subprocess

LOCK_FILE = "ocr_app.lock"

def check_dependencies():
    required_modules = {
        'PyQt5': 'PyQt5',
        'pytesseract': 'pytesseract',
        'easyocr': 'easyocr',
        'pdf2image': 'pdf2image',
        'numpy': 'numpy',
        'opencv-python': 'cv2',
        'python-dotenv': 'dotenv',
        'requests': 'requests'
    }
    missing = []
    for pkg, module in required_modules.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(pkg)
    # تحقق خاص من poppler-utils
    if not is_poppler_installed():
        missing.append('poppler-utils (system package)')
    return missing

def is_poppler_installed():
    # فحص وجود poppler-utils أو pdftoppm
    if sys.platform.startswith("win"):
        # فحص وجود pdftoppm.exe في PATH أو مجلد شائع
        possible_paths = [
            os.path.join("C:\\", "Program Files", "poppler-0.68.0", "bin", "pdftoppm.exe"),
            os.path.join("C:\\", "poppler", "bin", "pdftoppm.exe")
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return True
        # أو فحص في PATH
        return shutil.which("pdftoppm.exe") is not None
    else:
        # لينكس/ماك
        try:
            result = subprocess.run(["which", "pdftoppm"], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False

def get_poppler_install_hint():
    if sys.platform.startswith("win"):
        return "يرجى تحميل poppler من:\nhttps://github.com/oschwartz10612/poppler-windows/releases\nثم إضافة مسار bin إلى متغير PATH."
    elif sys.platform.startswith("linux"):
        return "ثبت poppler-utils بالأمر:\nsudo apt install poppler-utils"
    elif sys.platform == "darwin":
        return "ثبت poppler عبر Homebrew:\nbrew install poppler"
    else:
        return "يرجى تثبيت poppler-utils المناسب لنظامك."

def check_file_lock():
    if os.path.exists(LOCK_FILE):
        return True
    try:
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
        return False
    except:
        return True

def release_file_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)