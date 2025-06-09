def quick_sanity_check():
    """اختبار سريع لاستيراد الوحدات الأساسية"""
    try:
        import PyQt5
        from backup_manager import BackupManager
        from utils import check_dependencies
        from main_window import OCRMainWindow, send_email
        print("✔️ جميع الوحدات الأساسية تم استيرادها بنجاح.")
    except Exception as e:
        print(f"❌ مشكلة في الاستيراد: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    quick_sanity_check()
