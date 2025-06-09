import requests
import logging
import zipfile
import os
import shutil
import gnupg
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from packaging import version  # لتحسين مقارنة الإصدارات


class UpdateChecker(QThread):
    update_available = pyqtSignal(bool, str)

    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version
        self.latest_version = None
        self.changelog = ""

    def run(self):
        try:
            response = requests.get(
                "https://raw.githubusercontent.com/Hejazimohamed/ocr-update_final/main/version.json",
                timeout=10)
            data = response.json()
            self.latest_version = data.get("version")
            self.changelog = data.get("changelog", "")

            # مقارنة الإصدارات النصية بدقة
            is_newer = version.parse(
                self.latest_version) > version.parse(
                self.current_version)
            self.update_available.emit(is_newer, self.changelog)
        except Exception as e:
            logging.error(f"فشل التحقق من التحديث: {e}")


class UpdateApplier(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)  # إضافة رسالة مع النتيجة

    def __init__(self, update_url, app_path=None, parent=None):
        super().__init__()
        self.update_url = update_url
        self.app_path = app_path or os.getcwd()
        self.temp_zip = os.path.join(self.app_path, "update_temp.zip")
        self.temp_sig = os.path.join(self.app_path, "update_temp.zip.sig")
        self.backup_dir = os.path.join(self.app_path, "backup_before_update")
        self.public_key_path = os.path.join(self.app_path, "hejazi_public.asc")
        self.parent = parent  # لعرض رسائل للواجهة

    def run(self):
        try:
            # 1. تنزيل ملف التحديث
            response = requests.get(self.update_url, stream=True)
            total_size = int(response.headers.get("content-length", 0))
            with open(self.temp_zip, "wb") as f:
                downloaded = 0
                for data in response.iter_content(chunk_size=4096):
                    f.write(data)
                    downloaded += len(data)
                    if total_size > 0:
                        self.progress.emit(
                            int((downloaded / total_size) * 100))

            # 2. تنزيل ملف التوقيع الرقمي
            sig_url = self.update_url + ".sig"
            sig_response = requests.get(sig_url, timeout=10)
            with open(self.temp_sig, "wb") as f:
                f.write(sig_response.content)

            # 3. تحقق من التوقيع الرقمي وأعرض رسالة للمستخدم
            if not self.verify_signature():
                self.show_message(
                    "فشل في التحقق من التحديث!",
                    "⚠️ ملف التحديث لم يجتز التحقق الرقمي. تم إلغاء التحديث لأسباب أمنية.",
                    icon=QMessageBox.Critical)
                self.finished.emit(
                    False, "فشل التحقق من سلامة التحديث (التوقيع الرقمي غير صحيح).")
                # حذف الملفات المؤقتة
                if os.path.exists(self.temp_zip):
                    os.remove(self.temp_zip)
                if os.path.exists(self.temp_sig):
                    os.remove(self.temp_sig)
                return

            # 4. إذا التحقق ناجح، أبلغ المستخدم وواصل التحديث
            self.show_message(
                "التحقق من التحديث",
                "✅ تم التحقق من سلامة التحديث. جاري تثبيت التحديث الآن.",
                icon=QMessageBox.Information
            )
            self.extract_and_backup()
            self.finished.emit(True, "تم التحديث بنجاح! أعد تشغيل البرنامج.")
        except Exception as e:
            logging.error(f"فشل التحديث: {e}")
            self.finished.emit(False, f"فشل التحديث: {e}")

    def show_message(self, title, message, icon=QMessageBox.Information):
        msg = QMessageBox(self.parent)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()

    def verify_signature(self):
        gpg = gnupg.GPG()
        # تأكد أن المفتاح العام موجود
        if not os.path.exists(self.public_key_path):
            logging.error("مفتاح التحقق العام غير موجود!")
            self.show_message(
                "خطأ في التحقق",
                "ملف المفتاح العام (hejazi_public.asc) غير موجود في مجلد التطبيق.",
                icon=QMessageBox.Critical)
            return False
        # استيراد المفتاح العام (مرة واحدة لكل جهاز)
        with open(self.public_key_path, 'r') as f:
            gpg.import_keys(f.read())
        # التحقق من التوقيع
        with open(self.temp_sig, 'rb') as sig_file, open(self.temp_zip, 'rb') as zip_file:
            verified = gpg.verify_file(sig_file, self.temp_zip)
        return verified.valid

    def extract_and_backup(self):
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        with zipfile.ZipFile(self.temp_zip, 'r') as zipf:
            for member in zipf.namelist():
                target_file = os.path.join(self.app_path, member)
                # إذا الملف موجود، انقله للباك اب قبل الاستبدال
                if os.path.isfile(target_file):
                    backup_target = os.path.join(self.backup_dir, member)
                    backup_folder = os.path.dirname(backup_target)
                    if not os.path.exists(backup_folder):
                        os.makedirs(backup_folder)
                    shutil.copy2(target_file, backup_target)
                zipf.extract(member, self.app_path)
        # حذف ملف zip وملف التوقيع بعد النجاح
        os.remove(self.temp_zip)
        if os.path.exists(self.temp_sig):
            os.remove(self.temp_sig)


def prompt_user_for_update(changelog, parent=None):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle("تحديث متوفر")
    msg.setText("تحديث جديد متوفر!")
    msg.setInformativeText(
        f"سجل التغييرات:\n{changelog}\n\nهل تريد المتابعة بالتحديث؟")
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    return msg.exec_() == QMessageBox.Yes
