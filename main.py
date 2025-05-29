import sys
import logging
import traceback
import os

from utils import check_dependencies, check_file_lock, release_file_lock, get_poppler_install_hint

logging.basicConfig(
    filename="ocr_app_errors.log",
    filemode="a",
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s]: %(message)s"
)

def is_headless():
    return os.environ.get("DISPLAY", "") == "" and sys.platform != "win32"

def show_critical_message(title, msg):
    try:
        if not is_headless():
            from PyQt5.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, title, msg)
        else:
            print(f"=== {title} ===\n{msg}")
    except Exception as e:
        print(f"خطأ أثناء عرض الرسالة: {e}\n{title}\n{msg}")

def check_and_alert_dependencies():
    missing = check_dependencies()
    if missing:
        msg = "المتطلبات التالية غير متوفرة:\n- " + "\n- ".join(missing)
        if 'poppler-utils (system package)' in missing:
            msg += "\n\n" + get_poppler_install_hint()
        msg += "\n\nيرجى تثبيتها أولاً عبر:\npip install -r requirements.txt"
        show_critical_message("نقص في المتطلبات", msg)
        sys.exit(1)

def check_environment():
    if sys.platform not in ("linux", "win32", "darwin"):
        show_critical_message("بيئة غير مدعومة", f"النظام ({sys.platform}) غير مدعوم رسمياً.")
        sys.exit(1)
    try:
        import PyQt5
        from PyQt5.QtCore import QT_VERSION_STR
        if tuple(map(int, QT_VERSION_STR.split('.'))) < (5, 12):
            show_critical_message("إصدار PyQt5 قديم", f"الحد الأدنى المدعوم: 5.12. الإصدار الحالي: {QT_VERSION_STR}")
            sys.exit(1)
    except Exception as e:
        show_critical_message("خطأ PyQt5", f"تعذر التحقق من إصدار PyQt5: {e}")
        sys.exit(1)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    error_details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    user_alerts = []

    try:
        from settings_manager import SettingsManager
        settings = SettingsManager()
        send_reports = settings.get("send_crash_reports", False)
    except Exception:
        send_reports = False

    if not send_reports:
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication(sys.argv)
            reply = QMessageBox.question(None, "إرسال تقرير عطل",
                                         "حدث خطأ غير متوقع.\nهل ترغب في إرسال تقرير (قد يحتوي بيانات حساسة)؟",
                                         QMessageBox.Yes | QMessageBox.No)
            send_reports = (reply == QMessageBox.Yes)
        except Exception:
            send_reports = False

    if send_reports:
        try:
            from main_window import send_email
            send_email(
                "تقرير عطل تلقائي - OCR App",
                (
                    "⚠️ تنويه: قد يحتوي تقرير العطل على بيانات حساسة. "
                    "يرجى مراجعة التقرير قبل مشاركته مع أي جهة خارجية.\n\n"
                    f"حدث خطأ غير متوقع:\n\n{error_details}"
                )
            )
        except Exception as e:
            logging.error(f"فشل إرسال تقرير العطل التلقائي: {e}")
            user_alerts.append("⚠️ تعذر إرسال تقرير العطل عبر البريد الإلكتروني.")

    try:
        from backup_manager import BackupManager
        backup_manager = BackupManager()
        backup_manager.create_backup("crash_recovery")
    except Exception as e:
        logging.error(f"فشل في إنشاء نسخة بعد التعطل: {e}")
        user_alerts.append("⚠️ تعذر إنشاء نسخة احتياطية تلقائية بعد العطل.")

    if user_alerts:
        show_critical_message("مشاكل أثناء معالجة العطل", "\n".join(user_alerts))

sys.excepthook = handle_exception

def setup_qt_logging():
    try:
        from PyQt5.QtCore import qInstallMessageHandler, QtMsgType

        def qt_message_handler(mode, context, message):
            if mode == QtMsgType.QtCriticalMsg:
                logging.error(f"QtCriticalMsg: {message}")
            elif mode == QtMsgType.QtWarningMsg:
                logging.warning(f"QtWarningMsg: {message}")
            elif mode == QtMsgType.QtFatalMsg:
                logging.error(f"QtFatalMsg: {message}")

        qInstallMessageHandler(qt_message_handler)
    except Exception:
        logging.warning("qInstallMessageHandler غير مدعومة أو حدث خطأ.")

if __name__ == "__main__":
    # حماية تشغيل التطبيق: file lock
    if check_file_lock():
        show_critical_message("تشغيل مكرر", "تم اكتشاف تشغيل آخر للتطبيق أو تعذر إنشاء ملف الحماية.\nيرجى إغلاق كل النوافذ أو حذف ocr_app.lock.")
        sys.exit(1)

    try:
        from event_log import log_user_event
        log_user_event("تم تشغيل التطبيق بنجاح.")
    except Exception:
        pass

    try:
        from PyQt5.QtWidgets import QApplication
        if QApplication.instance() is not None:
            show_critical_message("خطأ في التشغيل", "تم اكتشاف تشغيل غير طبيعي للتطبيق (QApplication مكرر). يرجى إغلاق جميع النوافذ والمحاولة من جديد.")
            sys.exit(1)
    except Exception:
        pass

    check_environment()
    check_and_alert_dependencies()
    setup_qt_logging()

    try:
        from PyQt5.QtWidgets import QApplication
        from main_window import OCRMainWindow
        app = QApplication(sys.argv)
        win = OCRMainWindow()
        win.show()
        sys.exit(app.exec_())
    except Exception:
        raise
    finally:
        release_file_lock()