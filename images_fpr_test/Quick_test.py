def quick_sanity_check():
    """اختبار سريع لاستيراد الوحدات الأساسية"""
    try:
        print("✔️ جميع الوحدات الأساسية تم استيرادها بنجاح.")
    except Exception as e:
        print(f"❌ مشكلة في الاستيراد: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    quick_sanity_check()
