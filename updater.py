import json
import requests
import logging
import zipfile
import os
import shutil
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QProgressDialog

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
                timeout=10
            )
            data = response.json()
            self.latest_version = data.get("version")
            self.changelog = data.get("changelog", "")
            is_newer = self.latest_version > self.current_version
            self.update_available.emit(is_newer, self.changelog)
        except Exception as e:
            logging.error(f"فشل التحقق من التحديث: {e}")

class UpdateApplier(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)  # إضافة رسالة مع النتيجة

    def __init__(self, update_url, app_path=None):
        super().__init__()
        self.update_url = update_url
        self.app_path = app_path or os.getcwd()
        self.temp_zip = os.path.join(self.app_path, "update_temp.zip")
        self.backup_dir = os.path.join(self.app_path, "backup_before_update")

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
                        self.progress.emit(int((downloaded / total_size) * 100))
            # 2. نسخ جميع ملفات المشروع احتياطياً (قبل فك الضغط)
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
            for fname in os.listdir(self.app_path):
                fpath = os.path.join(self.app_path, fname)
                if os.path.isfile(fpath) and fname != "update_temp.zip":
                    shutil.copy2(fpath, os.path.join(self.backup_dir, fname))
            # 3. فك الضغط
            with zipfile.ZipFile(self.temp_zip, 'r') as zipf:
                zipf.extractall(self.app_path)
            # حذف ملف zip بعد النجاح
            os.remove(self.temp_zip)
            self.finished.emit(True, "تم التحديث بنجاح! أعد تشغيل البرنامج.")
        except Exception as e:
            logging.error(f"فشل التحديث: {e}")
            self.finished.emit(False, f"فشل التحديث: {e}")

def prompt_user_for_update(changelog, parent=None):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle("تحديث متوفر")
    msg.setText("تحديث جديد متوفر!")
    msg.setInformativeText(f"سجل التغييرات:\n{changelog}\n\nهل تريد المتابعة بالتحديث؟")
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    return msg.exec_() == QMessageBox.Yes