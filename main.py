import sys
import logging
import traceback
from utils import check_dependencies
from backup_manager import BackupManager

# تسجيل الأخطاء في ملف منفصل
logging.basicConfig(
    filename="ocr_app_errors.log",
    filemode="a",
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s]: %(message)s"
)

# التحقق من الاعتماديات
missing = check_dependencies()
if missing:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    app = QApplication(sys.argv)
    msg = "المتطلبات التالية غير متوفرة:\n- " + "\n- ".join(missing) + "\n\nيرجى تثبيتها أولاً."
    QMessageBox.critical(None, "نقص في المتطلبات", msg)
    sys.exit(1)

from main_window import send_email

def handle_exception(exc_type, exc_value, exc_traceback):
    """تسجيل الأعطال + إرسال تقرير عبر البريد + إنشاء نسخة احتياطية"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # تسجيل الخطأ في السجل
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    # إرسال تقرير بريد إلكتروني عن الخطأ
    try:
        error_details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        send_email(
            "تقرير عطل تلقائي - OCR App",
            f"حدث خطأ غير متوقع:\n\n{error_details}"
        )
    except Exception as e:
        logging.error(f"فشل إرسال تقرير العطل التلقائي: {e}")

    # إنشاء نسخة احتياطية مباشرة عند الكراش
    try:
        backup_manager = BackupManager()
        backup_manager.create_backup("crash_recovery")
    except Exception as e:
        logging.error(f"فشل في إنشاء نسخة بعد التعطل: {e}")

sys.excepthook = handle_exception

# تسجيل رسائل PyQt (critical/warning/fatal)
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
except Exception as e:
    logging.warning("qInstallMessageHandler غير مدعومة أو حدث خطأ.")

from PyQt5.QtWidgets import QApplication
from main_window import OCRMainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = OCRMainWindow()
    win.show()
    sys.exit(app.exec_())
