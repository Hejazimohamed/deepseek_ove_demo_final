import os
import sys
import logging
import smtplib
import time
from email.mime.text import MIMEText
from dotenv import load_dotenv
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QTextEdit, QComboBox, QProgressBar, QMessageBox, QLineEdit,
    QInputDialog, QCheckBox, QSizePolicy, QProgressDialog, QAction, QMenuBar, QDialog,
    QListWidget, QListWidgetItem
)
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PIL import Image, ImageEnhance, UnidentifiedImageError
from pdf2image import convert_from_path
import numpy as np
import cv2
from backup_manager import BackupManager
from settings_manager import SettingsManager
from updater import UpdateChecker, UpdateApplier, prompt_user_for_update

# تحميل بيانات البريد من .env
load_dotenv()
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
TO_EMAIL = SMTP_USER

def send_email(subject, body, to_email=TO_EMAIL):
    if not SMTP_USER or not SMTP_PASSWORD:
        logging.error("بيانات البريد ناقصة أو غير معرفة.")
        QMessageBox.critical(None, "خطأ", "إعدادات البريد الإلكتروني غير مكتملة!")
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
        logging.error(f"فشل في إرسال الإيميل: {e}")

def is_easyocr_enabled():
    try:
        with open("config.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("enable_easyocr"):
                    return line.strip().split("=")[1].strip() == "1"
    except Exception:
        return False
    return False

class EasyOCRSingleton:
    _instance = None
    _langs = None

    @classmethod
    def get_reader(cls, langs):
        import easyocr
        if cls._instance is None or cls._langs != langs:
            cls._instance = easyocr.Reader(langs, gpu=False, verbose=False)
            cls._langs = langs
        return cls._instance

def preprocess_image_advanced(pil_img):
    try:
        img_gray = pil_img.convert('L')
        img_enhanced = ImageEnhance.Contrast(img_gray).enhance(2.5)
        img_bright = ImageEnhance.Brightness(img_enhanced).enhance(1.15)
        img_sharp = ImageEnhance.Sharpness(img_bright).enhance(2.0)
        img_np = np.array(img_sharp)
        img_denoised = cv2.fastNlMeansDenoising(img_np, None, 24, 7, 21)
        _, img_bw = cv2.threshold(img_denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return Image.fromarray(img_bw)
    except Exception as ex:
        logging.error(f"preprocess_image_advanced error: {ex}")
        return pil_img

def open_multi_page_image(file_path):
    images = []
    try:
        im = Image.open(file_path)
        while True:
            images.append(im.copy())
            im.seek(im.tell() + 1)
    except EOFError:
        pass
    except UnidentifiedImageError:
        images = []
    except Exception as e:
        logging.error(f"خطأ في فتح TIFF: {e}")
        images = []
    return images

class OCRWorker(QThread):
    progress = pyqtSignal(int, int)
    result = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, file_path, engine, lang, roi_rel=None, rotation=0, enhance=False):
        super().__init__()
        self.file_path = file_path
        self.engine = engine
        self.lang = lang
        self.roi_rel = roi_rel
        self._cancelled = False
        self.rotation = rotation
        self.enhance = enhance

    def run(self):
        try:
            result_texts = []
            langs = []
            if "ara" in self.lang:
                langs.append("ar")
            if "eng" in self.lang:
                langs.append("en")
            if not langs:
                langs = ["en"]
            reader = None
            if self.engine in ["EasyOCR", "كلاهما"]:
                try:
                    self.progress.emit(0, 1)
                    reader = EasyOCRSingleton.get_reader(langs)
                except Exception as ex:
                    self.error.emit(f"خطأ في تهيئة EasyOCR: {ex}")
                    return
            custom_config = r'--oem 3 --psm 6'
            if self.file_path.lower().endswith('.pdf'):
                try:
                    images = convert_from_path(self.file_path, dpi=150)
                except Exception as ex:
                    self.error.emit(f"خطأ في تحويل PDF إلى صور: {ex}")
                    return
            elif self.file_path.lower().endswith(('.tiff', '.tif')):
                images = open_multi_page_image(self.file_path)
                if not images:
                    self.error.emit("خطأ في فتح ملف TIFF متعدد الصفحات.")
                    return
            else:
                images = [self.file_path]
            total_pages = len(images)
            if total_pages > 20:
                self.error.emit("تنبيه: الملف يحتوي على صفحات كثيرة. قد يسبب بطء أو استهلاك ذاكرة.")
            for idx, img in enumerate(images):
                if self._cancelled:
                    self.error.emit("تم إلغاء المعالجة من قبل المستخدم.")
                    return
                if isinstance(img, str):
                    try:
                        im = Image.open(img)
                    except Exception as ex:
                        self.error.emit(f"خطأ في فتح الصورة: {ex}")
                        return
                else:
                    im = img
                if self.rotation:
                    im = im.rotate(-self.rotation, expand=True)
                if self.roi_rel:
                    w, h = im.size
                    x_rel, y_rel, w_rel, h_rel = self.roi_rel
                    left = int(x_rel * w)
                    top = int(y_rel * h)
                    right = left + int(w_rel * w)
                    bottom = top + int(h_rel * h)
                    im = im.crop((left, top, right, bottom))
                if self.enhance:
                    im_proc = preprocess_image_advanced(im)
                else:
                    im_proc = im
                try:
                    if self.engine in ["Tesseract", "كلاهما"]:
                        import pytesseract
                        text_tess = pytesseract.image_to_string(im_proc, lang=self.lang, config=custom_config)
                        result_texts.append((f"Tesseract صفحة {idx+1}", text_tess.strip()))
                    if self.engine in ["EasyOCR", "كلاهما"] and reader:
                        img_np = np.array(im_proc)
                        result = reader.readtext(img_np, detail=0, paragraph=True)
                        text_easy = "\n".join(result).strip()
                        result_texts.append((f"EasyOCR صفحة {idx+1}", text_easy))
                except MemoryError:
                    self.error.emit("نفدت ذاكرة النظام أثناء المعالجة. حاول تقليل حجم الملف أو الصفحات.")
                    return
                except Exception as ex:
                    self.error.emit(f"خطأ أثناء معالجة الصفحة: {ex}")
                    return
                self.progress.emit(idx + 1, total_pages)
                del im
            text_parts = []
            for name, text in result_texts:
                text_parts.append(f"--- {name} ---\n{text}")
            self.result.emit("\n\n".join(text_parts).strip())
        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        self._cancelled = True

class OCRMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("تطبيق OCR الذكي")
        self.setWindowIcon(QIcon("app_icon.ico"))
        self.setAcceptDrops(True)
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        width = int(screen_size.width() * 0.7)
        height = int(screen_size.height() * 0.7)
        self.resize(width, height)
        self.setMinimumSize(900, 550)
        self.file_path = ""
        self.roi_rel = None
        self.ocr_thread = None
        self.current_image_rotation = 0
        self.settings = SettingsManager()
        self.backup_manager = BackupManager()
        self.backup_manager.start_auto_backups()
        self.init_ui()
        self.init_backup_ui()
        self.notify_update_if_available()
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.send_periodic_status)
        self.status_timer.start(60 * 60 * 1000)

    def notify_update_if_available(self):
        current_version = "1.1.0"
        self.update_checker = UpdateChecker(current_version)
        self.update_checker.update_available.connect(self.handle_update_notification)
        self.update_checker.start()

    def handle_update_notification(self, is_newer, changelog):
        if is_newer:
            agree = prompt_user_for_update(changelog, self)
            if agree:
                self.download_update()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QHBoxLayout()
        left_col = QVBoxLayout()
        right_col = QVBoxLayout()
        self.import_btn = QPushButton("استيراد صورة أو PDF")
        self.import_btn.clicked.connect(self.import_file)
        left_col.addWidget(self.import_btn)
        self.rotate_btn = QPushButton("تدوير")
        self.rotate_btn.clicked.connect(self.rotate_image)
        left_col.addWidget(self.rotate_btn)
        self.preview_label = QLabel("معاينة")
        self.preview_label.setFixedSize(180, 180)
        self.preview_label.setAlignment(Qt.AlignCenter)
        left_col.addWidget(self.preview_label)
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Tesseract", "EasyOCR", "كلاهما"])
        left_col.addWidget(QLabel("محرك التعرف:"))
        left_col.addWidget(self.engine_combo)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["ara+eng", "ara", "eng"])
        left_col.addWidget(QLabel("اللغة:"))
        left_col.addWidget(self.lang_combo)
        self.enhance_checkbox = QCheckBox("تفعيل تحسين الصورة (للنص المشوش)")
        self.enhance_checkbox.setChecked(False)
        left_col.addWidget(self.enhance_checkbox)
        self.process_btn = QPushButton("ابدأ المعالجة")
        self.process_btn.clicked.connect(self.start_ocr)
        self.process_btn.setEnabled(False)
        left_col.addWidget(self.process_btn)
        self.save_btn = QPushButton("حفظ النص")
        self.save_btn.clicked.connect(self.save_text)
        self.save_btn.setEnabled(False)
        left_col.addWidget(self.save_btn)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.clicked.connect(self.cancel_ocr)
        self.cancel_btn.setEnabled(False)
        left_col.addWidget(self.cancel_btn)
        self.report_btn = QPushButton("إبلاغ عن مشكلة")
        self.report_btn.clicked.connect(self.report_issue)
        left_col.addWidget(self.report_btn)
        self.update_btn = QPushButton("🔄 تحديث التطبيق")
        self.update_btn.clicked.connect(self.check_for_updates)
        left_col.addWidget(self.update_btn)
        left_col.addStretch()
        main_layout.addLayout(left_col)
        right_col.addWidget(QLabel("النص المستخرج:"))
        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        right_col.addWidget(self.result_edit)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        right_col.addWidget(self.progress_bar)
        main_layout.addLayout(right_col)
        self.central_widget.setLayout(main_layout)

    def init_backup_ui(self):
        self.menu = self.menuBar()
        backup_menu = self.menu.addMenu("النسخ الاحتياطي")
        manual_backup_action = QAction("إنشاء نسخة احتياطية يدوية", self)
        manual_backup_action.triggered.connect(self.manual_backup)
        backup_menu.addAction(manual_backup_action)
        restore_action = QAction("استعادة نسخة", self)
        restore_action.triggered.connect(self.restore_backup_dialog)
        backup_menu.addAction(restore_action)

    def manual_backup(self):
        comment, ok = QInputDialog.getText(
            self, "تعليق النسخة الاحتياطية",
            "أدخل تعليقًا وصفيًا (اختياري):"
        )
        if ok:
            success, path = self.backup_manager.create_backup(comment)
            if success:
                QMessageBox.information(self, "نجاح", f"تم إنشاء النسخة في: {path}")
            else:
                QMessageBox.critical(self, "خطأ", f"فشل في الإنشاء: {path}")

    def restore_backup_dialog(self):
        backups = self.backup_manager.get_available_backups()
        if not backups:
            QMessageBox.warning(self, "تحذير", "لا توجد نسخ احتياطية متاحة")
            return
        backup_list = QListWidget()
        for backup in backups:
            item = QListWidgetItem(
                f"{backup['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} "
                f"({backup['size']//1024} KB)"
            )
            item.setData(Qt.UserRole, backup['path'])
            backup_list.addItem(item)
        dialog = QDialog(self)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("اختر نسخة للاستعادة:"))
        layout.addWidget(backup_list)
        btn_restore = QPushButton("استعادة")
        btn_restore.clicked.connect(lambda: self.restore_selected(backup_list, dialog))
        layout.addWidget(btn_restore)
        dialog.setLayout(layout)
        dialog.exec_()

    def restore_selected(self, backup_list, dialog):
        selected = backup_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "تحذير", "لم تختر أي نسخة")
            return
        backup_path = selected.data(Qt.UserRole)
        if self.backup_manager.restore_backup(backup_path):
            QMessageBox.information(self, "نجاح", "تم الاستعادة بنجاح! أعد تشغيل التطبيق.")
            dialog.close()
        else:
            QMessageBox.critical(self, "خطأ", "فشل في استعادة النسخة")

    def import_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "استيراد صورة أو PDF", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff *.tif);;PDF Files (*.pdf)"
        )
        if file_path:
            self.file_path = file_path
            self.current_image_rotation = 0
            self.show_preview(file_path)
            self.process_btn.setEnabled(True)
            self.save_btn.setEnabled(False)
            self.result_edit.setPlainText("")

    def rotate_image(self):
        if self.file_path:
            self.current_image_rotation = (self.current_image_rotation + 90) % 360
            self.show_preview(self.file_path)

    def show_preview(self, file_path):
        try:
            if file_path.lower().endswith('.pdf'):
                images = convert_from_path(file_path, first_page=1, last_page=1, dpi=100)
                img = images[0]
            elif file_path.lower().endswith(('.tiff', '.tif')):
                images = open_multi_page_image(file_path)
                img = images[0] if images else None
            else:
                img = Image.open(file_path)
            if img and self.current_image_rotation:
                img = img.rotate(-self.current_image_rotation, expand=True)
            if img:
                img.thumbnail((200, 200))
                data = img.convert("RGB").tobytes("raw", "RGB")
                qimg = QImage(data, img.size[0], img.size[1], QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                self.preview_label.setPixmap(pixmap)
            else:
                self.preview_label.setText("خطأ في المعاينة!")
        except Exception as e:
            self.preview_label.setText("خطأ في المعاينة!")

    def start_ocr(self):
        self.progress_bar.setValue(0)
        self.result_edit.setPlainText("")
        self.process_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.ocr_start_time = time.time()
        self.ocr_thread = OCRWorker(
            self.file_path,
            self.engine_combo.currentText(),
            self.lang_combo.currentText(),
            self.roi_rel,
            self.current_image_rotation,
            self.enhance_checkbox.isChecked()
        )
        self.ocr_thread.progress.connect(self.update_progress)
        self.ocr_thread.result.connect(self.ocr_finished)
        self.ocr_thread.error.connect(self.handle_error)
        self.ocr_thread.start()

    def update_progress(self, current, total):
        percent = int((current / total) * 100)
        self.progress_bar.setValue(percent)

    def ocr_finished(self, text):
        elapsed = time.time() - self.ocr_start_time if hasattr(self, 'ocr_start_time') else None
        if elapsed:
            text += f"\n\n--------------------\nالمدة: {elapsed:.2f} ثانية"
        self.result_edit.setPlainText(text)
        self.process_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        if elapsed:
            QMessageBox.information(self, "وقت المعالجة", f"تمت معالجة الملف في {elapsed:.2f} ثانية")

    def handle_error(self, error_msg):
        self.result_edit.setPlainText("حدث خطأ أثناء استخراج النص:\n" + error_msg)
        self.process_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        send_email(
            "OCR App Error",
            f"تم رصد خطأ في التطبيق:\n{error_msg}"
        )

    def cancel_ocr(self):
        if self.ocr_thread is not None:
            self.ocr_thread.cancel()
        self.cancel_btn.setEnabled(False)

    def save_text(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "حفظ النص", "", "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            text = self.result_edit.toPlainText()
            if not text.strip():
                QMessageBox.warning(self, "تحذير", "لا يوجد نص للحفظ.")
                return
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(text)
                QMessageBox.information(self, "تم الحفظ", "تم حفظ النص بنجاح.")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"لم يتم حفظ النص:\n{e}")

    def report_issue(self):
        issue, ok = QInputDialog.getMultiLineText(self, "إبلاغ عن مشكلة", "يرجى وصف المشكلة:")
        if ok:
            if not issue.strip() or len(issue.strip()) < 3:
                QMessageBox.warning(self, "تحذير", "يجب كتابة وصف واضح للمشكلة (أكثر من 3 أحرف).")
                return
            try:
                with open("ocr_issue_reports.txt", "a", encoding="utf-8") as f:
                    f.write(issue.strip() + "\n" + "-"*60 + "\n")
            except Exception:
                pass
            send_email(
                "OCR App - بلاغ عن مشكلة",
                f"تم الإبلاغ عن مشكلة جديدة:\n\n{issue.strip()}"
            )
            QMessageBox.information(self, "شكرًا", "تم إرسال البلاغ بنجاح.\nشكرًا لمساهمتك!")

    def check_for_updates(self):
        current_version = "1.1.0"
        self.update_checker = UpdateChecker(current_version)
        self.update_checker.update_available.connect(self.handle_update_result)
        self.update_checker.start()

    def handle_update_result(self, is_newer, changelog):
        if is_newer:
            agree = prompt_user_for_update(changelog, self)
            if agree:
                self.download_update()
        else:
            QMessageBox.information(self, "لا يوجد تحديث", "أنت تستخدم آخر إصدار من التطبيق.")

    def download_update(self):
        update_url = "https://github.com/Hejazimohamed/ocr-update_final/releases/latest/download/update_temp.zip"
        self.update_applier = UpdateApplier(update_url)
        self.progress_dialog = QProgressDialog("جاري تحميل التحديث...", "إلغاء", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.canceled.connect(self.update_applier.requestInterruption)
        self.update_applier.progress.connect(self.progress_dialog.setValue)
        self.update_applier.finished.connect(self.finish_update)
        self.update_applier.start()
        self.progress_dialog.exec_()


    def finish_update(self, success):
        self.progress_dialog.close()
        if success:
            QMessageBox.information(self, "تم التحميل", "تم تحميل التحديث بنجاح في الملف: update_temp.zip\nيرجى فك الضغط واستبدال الملفات يدوياً.")
        else:
            QMessageBox.critical(self, "خطأ", "فشل تحميل التحديث.\nيرجى المحاولة لاحقاً.")

    def send_periodic_status(self):
        send_email(
            "OCR App - تقرير حالة تلقائي",
            "التطبيق يعمل بشكل طبيعي.\n(تقرير تلقائي كل ساعة.)"
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.file_path = file_path
            self.current_image_rotation = 0
            self.show_preview(file_path)
            self.process_btn.setEnabled(True)
            self.save_btn.setEnabled(False)
            self.result_edit.setPlainText("")

# نهاية الملف
