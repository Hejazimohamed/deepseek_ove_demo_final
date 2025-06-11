
# === AUTO-MERGED FILE ===

import os
import sys
import logging
import smtplib
import time
from email.mime.text import MIMEText
from dotenv import load_dotenv

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QComboBox,
    QProgressBar, QMessageBox, QInputDialog, QCheckBox,
    QAction, QListWidget, QListWidgetItem, QDialog, QProgressDialog,
    QSizePolicy
)
from PyQt5.QtGui import QPixmap, QImage, QIcon, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

from PIL import Image, ImageEnhance, UnidentifiedImageError
from pdf2image import convert_from_path
import numpy as np
import cv2

from backup_manager import BackupManager
from settings_manager import SettingsManager
from updater import UpdateChecker, UpdateApplier

# —— تحميل متغيرات البيئة للبريد —— #
load_dotenv()
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
TO_EMAIL = os.getenv("TO_EMAIL", SMTP_USER)


def send_email(subject, body, to_email=TO_EMAIL):
    """إرسال بريد تنبيهي؛ إذا كانت الإعدادات ناقصة، نسجل فقط تحذيراً."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logging.warning("SMTP credentials missing—email skipped.")
        return
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        logging.error(f"Failed to send email: {e}")


def is_easyocr_enabled():
    """قراءة config.txt لاختبار تمكين EasyOCR."""
    try:
        with open("config.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("enable_easyocr"):
                    return line.strip().split("=")[1].strip() == "1"
    except Exception:
        return False
    return False

class OCRApp(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(840, 530)
        self.setMinimumSize(520, 340)
        self.setWindowTitle("الذكي OCR (عربي / إنجليزي)")
        self.setStyleSheet("font-family: Tahoma, Arial; font-size: 13px;")
        self.init_ui()

    def init_ui(self):
        toolbar = QHBoxLayout()
        toolbar.setSpacing(0)
        toolbar.setContentsMargins(10, 12, 10, 2)

        self.import_btn = QPushButton("استيراد صور")
        self.import_btn.setStyleSheet(button_style)
        self.import_btn.clicked.connect(self.import_image)

        self.rotate_btn = QPushButton("تدوير الصورة")
        self.rotate_btn.setStyleSheet(button_style)

        self.start_btn = QPushButton("إبدأ المعالجة")
        self.start_btn.setStyleSheet(button_style)

        self.save_btn = QPushButton("حفظ النص")
        self.save_btn.setStyleSheet(button_style)

        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Tesseract"])
        self.engine_combo.setStyleSheet(
            "font-size: 12px; min-width: 72px; max-width: 110px;"
        )
        self.engine_combo.setMinimumWidth(72)
        self.engine_combo.setMaximumWidth(110)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["ara+eng", "ara", "eng"])
        self.lang_combo.setStyleSheet(
            "font-size: 12px; min-width: 72px; max-width: 110px;"
        )
        self.lang_combo.setMinimumWidth(72)
        self.lang_combo.setMaximumWidth(110)

        self.enhance_checkbox = QCheckBox()
        self.enhance_checkbox.setToolTip(
            "تفعيل تحسين الصورة (تصحيح الميل والتباين)"
        )
        self.enhance_checkbox.setFixedWidth(22)

        settings_bar = QHBoxLayout()
        settings_bar.setSpacing(0)
        spacing_between = 36

        settings_bar.addWidget(self.engine_combo)
        settings_bar.addSpacing(spacing_between)
        settings_bar.addWidget(self.lang_combo)
        settings_bar.addSpacing(spacing_between)
        settings_bar.addWidget(self.enhance_checkbox)

        toolbar.addWidget(self.import_btn)
        toolbar.addSpacing(16)
        toolbar.addWidget(self.rotate_btn)
        toolbar.addSpacing(28)
        toolbar.addLayout(settings_bar)
        toolbar.addStretch(1)
        toolbar.addWidget(self.start_btn)
        toolbar.addSpacing(16)
        toolbar.addWidget(self.save_btn)

        tips_label = QLabel(
            "يرجى رفع صورة واضحة، مسطحة، بدون ميل أو ظلال. للحصول على أفضل نتيجة، ضَع الورقة على سطح مستوٍ وصوِّر من الأعلى مباشرة."
        )
        tips_label.setFont(QFont("Tahoma", 12))
        tips_label.setStyleSheet(
            "background-color: #FFFACD; color: #222; padding: 8px 13px; border-radius: 8px; font-size: 12px; border:0;"
        )
        tips_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        root_vbox = QVBoxLayout(self)
        root_vbox.setSpacing(5)
        root_vbox.addLayout(toolbar)
        root_vbox.addWidget(tips_label)

        main_hbox = QHBoxLayout()
        main_hbox.setContentsMargins(8, 0, 8, 0)
        main_hbox.setSpacing(9)

        sidebar_widget = QWidget()
        sidebar_vbox = QVBoxLayout(sidebar_widget)
        sidebar_vbox.setSpacing(0)
        sidebar_vbox.setContentsMargins(0, 2, 0, 2)

        self.image_preview = QLabel("لم يتم تحميل صورة بعد")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setStyleSheet(
            "border: 1px solid #CCC; background: #F9F9F9; min-width: 120px; min-height: 200px; font-size: 12px; color: #888; border-radius: 10px;"
        )
        self.image_preview.setMinimumHeight(200)
        self.image_preview.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        sidebar_vbox.addWidget(self.image_preview, 6)

        sidebar_vbox.addSpacing(18)
        self.progress_bar_preview = QProgressBar()
        self.progress_bar_preview.setValue(0)
        self.progress_bar_preview.setTextVisible(True)
        self.progress_bar_preview.setFixedHeight(32)
        self.progress_bar_preview.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        self.progress_bar_preview.setFormat("%p%")
        self.progress_bar_preview.setStyleSheet("""
            QProgressBar {
                font-size: 16px;
                border-radius: 7px;
                background: #fffbe9;
                border: 2px solid #e0c97c;
                text-align: left;
                padding-left: 22px;
                color: #888;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffe29f, stop:1 #ffc700);
                border-radius: 7px;
            }
        """)
        sidebar_vbox.addWidget(self.progress_bar_preview)
        sidebar_vbox.addSpacing(8)

        sidebar_vbox.addStretch(1)

        logo_label = QLabel()
        logo_pixmap = QPixmap("logos.png")
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaled(
                65, 65, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignHCenter)
        sidebar_vbox.addWidget(logo_label)

        org_name = QLabel("LES Benghazi")
        org_name.setAlignment(Qt.AlignHCenter)
        org_name.setStyleSheet("font-weight: bold; font-size: 13px;")
        sidebar_vbox.addWidget(org_name)

        org_desc = QLabel("نقابة المهندسين الهندسية بنغازي")
        org_desc.setAlignment(Qt.AlignHCenter)
        org_desc.setStyleSheet("font-size: 11px; color: #444;")
        sidebar_vbox.addWidget(org_desc)

        report_btn = QPushButton("إبلاغ عن مشكلة")
        report_btn.setStyleSheet(report_btn_style)
        sidebar_vbox.addWidget(report_btn)

        update_btn = QPushButton("تحديث التطبيق")
        update_btn.setStyleSheet(update_btn_style)
        sidebar_vbox.addWidget(update_btn)

        sidebar_vbox.addSpacing(5)

        sidebar_footer = QLabel(
            "E-mail: hejazi.mohamed@gmail.com   واتساب: 0927232437"
        )
        sidebar_footer.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        sidebar_footer.setStyleSheet(
            "background: transparent; color:#222; font-size:11px; padding:5px 8px;"
        )
        sidebar_vbox.addWidget(sidebar_footer)

        right_panel = QWidget()
        right_vbox = QVBoxLayout(right_panel)
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.setSpacing(0)

        self.output_box = QTextEdit()
        self.output_box.setPlaceholderText(
            "سيظهر النص المستخرج هنا بعد المعالجة..."
        )
        self.output_box.setAlignment(Qt.AlignRight)
        self.output_box.setStyleSheet("""
            QTextEdit {
                font-size: 15px;
                border-radius: 13px;
                background: #fffbe9;
                padding: 10px 13px;
                border: 2px solid #e0c97c;
                box-shadow: 2px 2px 12px #f3e3a7 inset, -2px -2px 8px #fff inset;
            }
        """)
        right_vbox.addWidget(self.output_box)

        main_hbox.addWidget(sidebar_widget, 0)
        main_hbox.addWidget(right_panel, 1)
        root_vbox.addLayout(main_hbox, 1)

    def import_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "اختر صورة", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_name:
            pixmap = QPixmap(file_name)
            if not pixmap.isNull():
                target_width = max(120, int(self.image_preview.width()))
                target_height = max(200, int(self.image_preview.height()))
                scaled = pixmap.scaled(
                    target_width, target_height,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.image_preview.setPixmap(scaled)
            else:
                self.image_preview.setText("تعذر تحميل الصورة")
        else:
            self.image_preview.setText("لم يتم تحميل صورة بعد")

# === Original logic from main_window.py ===

class OCRWorker(QThread):
    progress = pyqtSignal(int, int)
    result = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
            self,
            file_path,
            engine,
            lang,
            roi_rel=None,
            rotation=0,
            enhance=False):
        super().__init__()
        self.file_path = file_path
        self.engine = engine
        self.lang = lang
        self.roi_rel = roi_rel
        self.rotation = rotation
        self.enhance = enhance
        self._cancelled = False

    def run(self):
        try:
            # إعداد اللغات
            langs = []
            if "ara" in self.lang:
                langs.append("ar")
            if "eng" in self.lang:
                langs.append("en")
            if not langs:
                langs = ["en"]

            reader = None
            if self.engine in ["EasyOCR", "كلاهما"] and is_easyocr_enabled():
                reader = EasyOCRSingleton.get_reader(langs)
                self.progress.emit(0, 1)

            # جلب الصور من PDF (DPI=100 سريع)، TIFF أو ملف وحيد
            if self.file_path.lower().endswith('.pdf'):
                pages = convert_from_path(
                    self.file_path,
                    dpi=100,
                    thread_count=4
                )
            elif self.file_path.lower().endswith(('.tiff', '.tif')):
                pages = open_multi_page_image(self.file_path)
            else:
                pages = [self.file_path]

            total = len(pages)
            if total > 20:
                self.error.emit("تنبيه: الملف يحوي >20 صفحة وقد يبطئ العملية.")

            all_text = []
            for idx, item in enumerate(pages, start=1):
                if self._cancelled:
                    self.error.emit("تم إلغاء المعالجة.")
                    return

                im = Image.open(item) if isinstance(item, str) else item
                if self.rotation:
                    im = im.rotate(-self.rotation, expand=True)
                if self.roi_rel:
                    w, h = im.size
                    x, y, wr, hr = self.roi_rel
                    im = im.crop((int(x * w), int(y * h),
                                  int((x + wr) * w), int((y + hr) * h)))

                proc = preprocess_image_advanced(im) if self.enhance else im

                text_block = ""
                try:
                    if self.engine in ["Tesseract", "كلاهما"]:
                        import pytesseract
                        cfg = "--oem 3 --psm 6"
                        text_block += pytesseract.image_to_string(
                            proc, lang=self.lang, config=cfg).strip()
                    if reader:
                        arr = np.array(proc)
                        txt = reader.readtext(arr, detail=0, paragraph=True)
                        text_block += "\n".join(txt).strip()
                except MemoryError:
                    self.error.emit("نفدت الذاكرة خلال المعالجة.")
                    return
                except Exception as ex:
                    self.error.emit(f"خطأ في الصفحة {idx}: {ex}")
                    return

                all_text.append(f"--- صفحة {idx} ---\n{text_block}")
                self.progress.emit(idx, total)

            self.result.emit("\n\n".join(all_text).strip())
        except Exception as ex:
            self.error.emit(str(ex))

    def cancel(self):
        self._cancelled = True


class OCRMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("تطبيق OCR الذكي")
        self.setWindowIcon(QIcon("app_icon.ico"))
        self.setAcceptDrops(True)
        self.resize(840, 530)
        self.setMinimumSize(520, 340)
        self.setStyleSheet("font-family: Tahoma, Arial; font-size: 13px;")

        self.file_path = ""
        self.roi_rel = None
        self.current_rotation = 0
        self.ocr_start_time = None
        self.ocr_thread = None

        self.settings = SettingsManager()
        self.backup_manager = BackupManager()
        self.backup_manager.start_auto_backups()

        self._build_ui()
        self._build_menu()
        self.check_for_updates()

        timer = QTimer(self)
        timer.timeout.connect(self.send_periodic_status)
        timer.start(3600_000)

    def _build_ui(self):
        # أنماط الأزرار
        button_style = """
        QPushButton {
            background: qlineargradient(
                spread:pad,
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #ffe29f, stop:1 #ffc700
            );
            color: #7c4a02;
            border: 1px solid #ffe29f;
            border-radius: 7px;
            font-size: 12px;
            padding: 4px 14px;
            font-weight: bold;
            margin: 2px 2px;
            min-width: 70px;
            max-width: 110px;
        }
        QPushButton:hover {
            background: qlineargradient(
                spread:pad,
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #ffe29f, stop:1 #ffd700
            );
            color: #8b6a00;
        }
        QPushButton:pressed {
            background: #ffd700;
        }
        """

        report_btn_style = """
        QPushButton {
            background: #FFFACD;
            color: #AA8800;
            font-weight: bold;
            font-size: 12px;
            border-radius: 6px;
            border: none;
            padding: 4px 0;
            min-height: 18px;
        }
        QPushButton:hover {
            background-color: #ffe066;
        }
        """

        update_btn_style = """
        QPushButton {
            background: #E0FFFF;
            color: #008B8B;
            font-weight: bold;
            font-size: 12px;
            border-radius: 6px;
            border: none;
            padding: 4px 0;
            min-height: 18px;
        }
        QPushButton:hover {
            background-color: #b2ebf2;
        }
        """

        # إنشاء الواجهة الرئيسية
        central = QWidget()
        self.setCentralWidget(central)
        root_vbox = QVBoxLayout(central)
        root_vbox.setSpacing(5)

        # شريط الأدوات العلوي
        toolbar = QHBoxLayout()
        toolbar.setSpacing(0)
        toolbar.setContentsMargins(10, 12, 10, 2)

        self.import_btn = QPushButton("استيراد صور")
        self.import_btn.setStyleSheet(button_style)
        self.import_btn.clicked.connect(self.import_file)
        toolbar.addWidget(self.import_btn)

        self.rotate_btn = QPushButton("تدوير الصورة")
        self.rotate_btn.setStyleSheet(button_style)
        self.rotate_btn.clicked.connect(self.rotate_image)
        toolbar.addSpacing(16)
        toolbar.addWidget(self.rotate_btn)

        toolbar.addSpacing(28)

        # إعدادات المحرك واللغة
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Tesseract", "EasyOCR", "كلاهما"])
        self.engine_combo.setStyleSheet(
            "font-size: 12px; min-width: 72px; max-width: 110px;")
        self.engine_combo.setMinimumWidth(72)
        self.engine_combo.setMaximumWidth(110)
        toolbar.addWidget(self.engine_combo)

        toolbar.addSpacing(36)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["ara+eng", "ara", "eng"])
        self.lang_combo.setStyleSheet(
            "font-size: 12px; min-width: 72px; max-width: 110px;")
        self.lang_combo.setMinimumWidth(72)
        self.lang_combo.setMaximumWidth(110)
        toolbar.addWidget(self.lang_combo)

        toolbar.addSpacing(36)

        self.enhance_chk = QCheckBox()
        self.enhance_chk.setToolTip(
            "تفعيل تحسين الصورة (تصحيح الميل والتباين)")
        self.enhance_chk.setFixedWidth(22)
        toolbar.addWidget(self.enhance_chk)

        toolbar.addStretch(1)

        self.process_btn = QPushButton("إبدأ المعالجة")
        self.process_btn.setStyleSheet(button_style)
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self.start_ocr)
        toolbar.addWidget(self.process_btn)

        toolbar.addSpacing(16)

        self.save_btn = QPushButton("حفظ النص")
        self.save_btn.setStyleSheet(button_style)
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_text)
        toolbar.addWidget(self.save_btn)

        root_vbox.addLayout(toolbar)

        # تلميحات الاستخدام
        tips_label = QLabel(
            "يرجى رفع صورة واضحة، مسطحة، بدون ميل أو ظلال. للحصول على أفضل نتيجة، ضع الورقة على سطح مستوٍ وصوّر من الأعلى مباشرة."
        )
        tips_label.setFont(QFont("Tahoma", 12))
        tips_label.setStyleSheet(
            "background-color: #FFFACD; color: #222; padding: 8px 13px; border-radius: 8px; font-size: 12px; border:0;"
        )
        tips_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        root_vbox.addWidget(tips_label)

        # منطقة المحتوى الرئيسية
        main_hbox = QHBoxLayout()
        main_hbox.setContentsMargins(8, 0, 8, 0)
        main_hbox.setSpacing(9)

        # الشريط الجانبي الأيسر
        sidebar_widget = QWidget()
        sidebar_vbox = QVBoxLayout(sidebar_widget)
        sidebar_vbox.setSpacing(0)
        sidebar_vbox.setContentsMargins(0, 2, 0, 2)

        self.preview_label = QLabel("لم يتم تحميل صورة بعد")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(
            "border: 1px solid #CCC; background: #F9F9F9; min-width: 120px; min-height: 200px; font-size: 12px; color: #888; border-radius: 10px;"
        )
        self.preview_label.setMinimumHeight(200)
        self.preview_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        sidebar_vbox.addWidget(self.preview_label, 6)

        sidebar_vbox.addSpacing(18)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(32)
        self.progress_bar.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                font-size: 16px;
                border-radius: 7px;
                background: #fffbe9;
                border: 2px solid #e0c97c;
                text-align: left;
                padding-left: 22px;
                color: #888;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffe29f, stop:1 #ffc700);
                border-radius: 7px;
            }
        """)
        sidebar_vbox.addWidget(self.progress_bar)
        sidebar_vbox.addSpacing(8)

        sidebar_vbox.addStretch(1)

        # معلومات المؤسسة
        logo_label = QLabel()
        logo_pixmap = QPixmap("logos.png")
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaled(
                65, 65, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignHCenter)
        sidebar_vbox.addWidget(logo_label)

        org_name = QLabel("LES Benghazi")
        org_name.setAlignment(Qt.AlignHCenter)
        org_name.setStyleSheet("font-weight: bold; font-size: 13px;")
        sidebar_vbox.addWidget(org_name)

        org_desc = QLabel("نقابة المهندسين الهندسية بنغازي")
        org_desc.setAlignment(Qt.AlignHCenter)
        org_desc.setStyleSheet("font-size: 11px; color: #444;")
        sidebar_vbox.addWidget(org_desc)

        # أزرار التقارير والتحديث
        self.report_btn = QPushButton("إبلاغ عن مشكلة")
        self.report_btn.setStyleSheet(report_btn_style)
        self.report_btn.clicked.connect(self.report_issue)
        sidebar_vbox.addWidget(self.report_btn)

        self.update_btn = QPushButton("تحديث التطبيق")
        self.update_btn.setStyleSheet(update_btn_style)
        self.update_btn.clicked.connect(self.check_for_updates)
        sidebar_vbox.addWidget(self.update_btn)

        sidebar_vbox.addSpacing(5)

        # تذييل الشريط الجانبي
        sidebar_footer = QLabel(
            "E-mail: hejazi.mohamed@gmail.com   واتساب: 0927232437")
        sidebar_footer.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        sidebar_footer.setStyleSheet(
            "background: transparent; color:#222; font-size:11px; padding:5px 8px;")
        sidebar_vbox.addWidget(sidebar_footer)

        # منطقة عرض النتائج
        right_panel = QWidget()
        right_vbox = QVBoxLayout(right_panel)
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.setSpacing(0)

        self.result_edit = QTextEdit()
        self.result_edit.setPlaceholderText(
            "سيظهر النص المستخرج هنا بعد المعالجة...")
        self.result_edit.setReadOnly(True)
        self.result_edit.setAlignment(Qt.AlignRight)
        self.result_edit.setStyleSheet("""
            QTextEdit {
                font-size: 15px;
                border-radius: 13px;
                background: #fffbe9;
                padding: 10px 13px;
                border: 2px solid #e0c97c;
                box-shadow: 2px 2px 12px #f3e3a7 inset, -2px -2px 8px #fff inset;
            }
        """)
        right_vbox.addWidget(self.result_edit)

        main_hbox.addWidget(sidebar_widget, 0)
        main_hbox.addWidget(right_panel, 1)
        root_vbox.addLayout(main_hbox, 1)

        # إضافة زر الإلغاء (مخفي حالياً)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.cancel_ocr)

    def _build_menu(self):
        mbar = self.menuBar()
        backup_menu = mbar.addMenu("النسخ الاحتياطي")
        a1 = QAction("نسخ احتياطي يدوي", self)
        a1.triggered.connect(self.manual_backup)
        backup_menu.addAction(a1)
        a2 = QAction("استعادة نسخة", self)
        a2.triggered.connect(self.restore_backup_dialog)
        backup_menu.addAction(a2)

    def manual_backup(self):
        comment, ok = QInputDialog.getText(self, "نسخ احتياطي", "تعليق:")
        if ok:
            ok2, path = self.backup_manager.create_backup(comment)
            if ok2:
                QMessageBox.information(self, "نجاح", f"تم: {path}")
            else:
                QMessageBox.critical(self, "فشل", path)

    def restore_backup_dialog(self):
        backups = self.backup_manager.get_available_backups()
        if not backups:
            QMessageBox.warning(self, "تحذير", "لا توجد نسخ احتياطية.")
            return
        dlg = QDialog(self)
        lst = QListWidget()
        for b in backups:
            item = QListWidgetItem(f"{b['timestamp']} ({b['size']//1024}KB)")
            item.setData(Qt.UserRole, b['path'])
            lst.addItem(item)
        btn = QPushButton("استعادة", dlg)
        btn.clicked.connect(lambda: self.restore_selected(lst, dlg))
        layout = QVBoxLayout(dlg)
        layout.addWidget(lst)
        layout.addWidget(btn)
        dlg.exec_()

    def restore_selected(self, lst, dlg):
        it = lst.currentItem()
        path = it.data(Qt.UserRole) if it else None
        if path and self.backup_manager.restore_backup(path):
            QMessageBox.information(self, "تم", "استُعيد بنجاح.")
            dlg.close()
        else:
            QMessageBox.critical(self, "فشل", "لم يتم الاستعادة.")

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "استيراد", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff *.tif);;PDF Files (*.pdf)"
        )
        if not path:
            return
        self.file_path = path
        self.current_rotation = 0
        self.show_preview(path)
        self.process_btn.setEnabled(True)

    def rotate_image(self):
        if not self.file_path:
            return
        self.current_rotation = (self.current_rotation + 90) % 360
        self.show_preview(self.file_path)

    def show_preview(self, path):
        try:
            if path.lower().endswith('.pdf'):
                img = convert_from_path(
                    path,
                    first_page=1, last_page=1,
                    dpi=100,
                    thread_count=1
                )[0]
            else:
                img = Image.open(path)
            if self.current_rotation:
                img = img.rotate(-self.current_rotation, expand=True)
            img.thumbnail((200, 200))
            rgb = img.convert('RGB')
            w, h = rgb.size
            bpl = 3 * w
            data = rgb.tobytes('raw', 'RGB')
            qimg = QImage(data, w, h, bpl, QImage.Format_RGB888)
            pix = QPixmap.fromImage(qimg).scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(pix)
        except Exception as e:
            self.preview_label.setText("خطأ في المعاينة!")
            logging.error(f"Preview error: {e}")

    def start_ocr(self):
        self.result_edit.clear()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.process_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.save_btn.setEnabled(False)
        self.ocr_start_time = time.time()

        self.ocr_thread = OCRWorker(
            file_path=self.file_path,
            engine=self.engine_combo.currentText(),
            lang=self.lang_combo.currentText(),
            roi_rel=self.roi_rel,
            rotation=self.current_rotation,
            enhance=self.enhance_chk.isChecked()
        )
        self.ocr_thread.progress.connect(self.update_progress)
        self.ocr_thread.result.connect(self.ocr_finished)
        self.ocr_thread.error.connect(self.handle_error)
        self.ocr_thread.start()

    def update_progress(self, current, total):
        if total <= 1:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)

    def ocr_finished(self, text):
        elapsed = time.time() - self.ocr_start_time
        text += f"\n\n--- المدة: {elapsed:.2f} ثانية ---"
        self.result_edit.setPlainText(text)
        self.process_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        QMessageBox.information(
            self, "انتهى", f"اكتملت المعالجة في {elapsed:.2f} ثانية")

    def handle_error(self, msg):
        QMessageBox.critical(self, "خطأ في OCR", msg)
        self.result_edit.setPlainText("خطأ:\n" + msg)
        self.process_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        send_email("OCR App Error", msg)

    def cancel_ocr(self):
        if self.ocr_thread:
            self.ocr_thread.cancel()
        self.cancel_btn.setVisible(False)

    def save_text(self):
        fname, _ = QFileDialog.getSaveFileName(
            self, "حفظ النص", "", "Text Files (*.txt);;All Files (*)"
        )
        if not fname:
            return
        text = self.result_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "تحذير", "لا يوجد نص للحفظ.")
            return
        try:
            with open(fname, "w", encoding="utf-8") as f:
                f.write(text)
            QMessageBox.information(self, "تم", "تم حفظ النص بنجاح.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", str(e))

    def report_issue(self):
        issue, ok = QInputDialog.getMultiLineText(
            self, "إبلاغ عن مشكلة", "يرجى وصف المشكلة:"
        )
        if ok and len(issue.strip()) >= 3:
            with open("ocr_issue_reports.txt", "a", encoding="utf-8") as f:
                f.write(issue.strip() + "\n" + "-" * 60 + "\n")
            send_email("OCR App - بلاغ عن مشكلة", issue.strip())
            QMessageBox.information(self, "شكراً", "تم إرسال البلاغ بنجاح.")
        else:
            QMessageBox.warning(self, "تحذير", "يرجى كتابة وصف واضح للمشكلة.")

    def check_for_updates(self):
        current_version = "1.1.0"
        self.update_checker = UpdateChecker(current_version)
        self.update_checker.update_available.connect(
            self.handle_update_notification)
        self.update_checker.start()

    def handle_update_notification(self, is_newer, changelog):
        if is_newer:
            reply = QMessageBox.question(
                self, "تحديث متاح",
                "يوجد تحديث جديد، هل تريد تحميله؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.download_update()
        else:
            QMessageBox.information(
                self, "لا يوجد تحديث", "أنت تستخدم آخر إصدار.")

    def download_update(self):
        url = "https://github.com/Hejazimohamed/ocr-update_final/releases/latest/download/update_temp.zip"
        self.update_applier = UpdateApplier(url)
        dlg = QProgressDialog("تحميل التحديث...", "إلغاء", 0, 100, self)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.canceled.connect(self.update_applier.requestInterruption)
        self.update_applier.progress.connect(dlg.setValue)
        self.update_applier.finished.connect(self.finish_update)
        self.update_applier.start()
        dlg.exec_()

    def finish_update(self, success):
        if success:
            QMessageBox.information(
                self,
                "تم التحميل",
                "تم تحميل التحديث في `update_temp.zip`. يرجى استبدال الملفات يدويًا.")
        else:
            QMessageBox.critical(
                self,
                "فشل التحميل",
                "لم يتم تحميل التحديث. حاول لاحقًا.")

    def send_periodic_status(self):
        send_email("OCR App Status", "التطبيق يعمل بشكل طبيعي.")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.import_file()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OCRMainWindow()
    window.show()
    sys.exit(app.exec_())
