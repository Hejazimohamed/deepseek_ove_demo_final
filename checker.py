import sys


def safe_print(msg: str):
    """Print msg but silently ignore PermissionError on Windows."""
    try:
        print(msg)
    except PermissionError:
        try:
            sys.stderr.write(msg + "\n")
        except PermissionError:
            pass


def quick_sanity_check():
    """اختبار سريع لاستيراد الوحدات الأساسية"""
    try:
        safe_print("✔️ جميع الوحدات الأساسية تم استيرادها بنجاح.")
    except Exception as e:
        safe_print(f"❌ مشكلة في الاستيراد: {e}")
        sys.exit(1)


if __name__ == "__main__":
    quick_sanity_check()
