import os
import shutil
import logging
import zipfile
from typing import Optional

import requests
import gnupg
from packaging import version
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QWidget


class UpdateChecker(QThread):
    """
    يتحقَّق من ملف ‎version.json‎ على GitHub لمعرفة ما إذا كان هناك إصدار أحدث.
    يُصدِر الإشارة ‎update_available‎ مع:
        (is_newer: bool, changelog: str)
    """
    update_available = pyqtSignal(bool, str)

    def __init__(self, current_version: str) -> None:
        super().__init__()
        self.current_version: str = current_version
        self.latest_version: Optional[str] = None
        self.changelog: str = ""

    # -------------------------------- QThread --------------------------------
    def run(self) -> None:
        try:
            url = (
                "https://raw.githubusercontent.com/"
                "Hejazimohamed/ocr-update_final/main/version.json"
            )
            data = requests.get(url, timeout=10).json()
            self.latest_version = data.get("version")
            self.changelog = data.get("changelog", "")

            is_newer = (
                self.latest_version is not None
                and version.parse(self.latest_version) > version.parse(self.current_version)
            )
            self.update_available.emit(is_newer, self.changelog)
        except Exception as exc:  # noqa: BLE001
            logging.error("فشل التحقق من التحديث: %s", exc)


class UpdateApplier(QThread):
    """
    يُنزِّل ملف ZIP التحديث، يتحقَّق من توقيعه، ثم يفكّ الضغط مع عمل نسخة احتياطية.
    يُصدِر الإشارة ‎update_finished‎ مع:
        (success: bool, message: str)
    """
    progress = pyqtSignal(int)
    update_finished = pyqtSignal(bool, str)

    def __init__(
        self,
        update_url: str,
        app_path: Optional[str] = None,
        parent_widget: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent_widget)  # نمرّر الـ QObject parent إلى QThread
        self.update_url: str = update_url
        self.app_path: str = app_path or os.getcwd()
        self._parent_widget: Optional[QWidget] = parent_widget

        self.temp_zip = os.path.join(self.app_path, "update_temp.zip")
        self.temp_sig = os.path.join(self.app_path, "update_temp.zip.sig")
        self.backup_dir = os.path.join(self.app_path, "backup_before_update")
        self.public_key_path = os.path.join(self.app_path, "hejazi_public.asc")

    # -------------------------------- QThread --------------------------------
    def run(self) -> None:
        try:
            self._download_update()
            if not self._verify_signature():
                self._show_message(
                    "فشل التحقق من التحديث!",
                    "⚠️ لم يجتز ملف التحديث التوقيع الرقمي. أُلغيَ التحديث."
                    " تأكد من سلامة الملف أو اتصل بالمطوِّر.",
                    QMessageBox.Critical,
                )
                self.update_finished.emit(False, "فشل التحقق من سلامة التحديث.")
                self._clean_temp()
                return

            self._show_message(
                "جارٍ تثبيت التحديث",
                "✅ تم التحقق من سلامة التحديث، ويبدأ الآن فك الضغط والاستبدال.",
                QMessageBox.Information,
            )
            self._extract_and_backup()
            self.update_finished.emit(True, "تم التحديث بنجاح! أعد تشغيل البرنامج.")
        except Exception as exc:  # noqa: BLE001
            logging.error("فشل التحديث: %s", exc)
            self.update_finished.emit(False, f"فشل التحديث: {exc}")
        finally:
            self._clean_temp()

    # ----------------------------- خطوات التحديث ----------------------------- #
    def _download_update(self) -> None:
        """تنزيل ‏ZIP‏ والتوقيع الرقمي مع بثّ تقدم التنزيل."""
        response = requests.get(self.update_url, stream=True, timeout=10)
        total = int(response.headers.get("content-length", 0))

        with open(self.temp_zip, "wb") as outfile:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=4096):
                outfile.write(chunk)
                downloaded += len(chunk)
                if total:
                    self.progress.emit(int(downloaded / total * 100))

        # تنزيل ملف ‎.sig‎
        sig_resp = requests.get(self.update_url + ".sig", timeout=10)
        with open(self.temp_sig, "wb") as sig_file:
            sig_file.write(sig_resp.content)

    def _verify_signature(self) -> bool:
        """تحقق GPG للملف المضغوط."""
        if not os.path.exists(self.public_key_path):
            self._show_message(
                "مفتاح التحقق مفقود",
                "hejazi_public.asc غير موجود في مجلد التطبيق.",
                QMessageBox.Critical,
            )
            return False

        gpg = gnupg.GPG()
        with open(self.public_key_path, "r", encoding="utf-8") as key_file:
            gpg.import_keys(key_file.read())

        with open(self.temp_sig, "rb") as sig_file:
            verified = gpg.verify_file(sig_file, self.temp_zip)

        return verified.valid

    def _extract_and_backup(self) -> None:
        """فك الضغط مع إنشاء نسخة احتياطية للملفات التي ستُستبدل."""
        os.makedirs(self.backup_dir, exist_ok=True)

        with zipfile.ZipFile(self.temp_zip, "r") as zipped:
            for member in zipped.namelist():
                target = os.path.join(self.app_path, member)

                # إن كان الملف موجوداً سننسخه أولاً إلى نسخة احتياطية
                if os.path.isfile(target):
                    backup_target = os.path.join(self.backup_dir, member)
                    os.makedirs(os.path.dirname(backup_target), exist_ok=True)
                    shutil.copy2(target, backup_target)

                zipped.extract(member, self.app_path)

    # ------------------------------ أدوات مساعدة ----------------------------- #
    def _show_message(
        self,
        title: str,
        text: str,
        icon: QMessageBox.Icon = QMessageBox.Information,
    ) -> None:
        msg = QMessageBox(self._parent_widget)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.exec_()

    def _clean_temp(self) -> None:
        for path in (self.temp_zip, self.temp_sig):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:  # noqa: BLE001
                logging.warning("تعذّر حذف الملف المؤقت: %s", path)


def prompt_user_for_update(
    changelog: str,
    parent: Optional[QWidget] = None,
) -> bool:
    """
    حوار يسأل المستخدم إذا كان يريد تنزيل التحديث.
    يُرجع True إذا وافق المستخدم.
    """
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle("تحديث متوفر")
    msg.setText("تحديث جديد متوفر!")
    msg.setInformativeText(f"سجل التغييرات:\n{changelog}\n\nهل تريد متابعة التحديث؟")
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    return msg.exec_() == QMessageBox.Yes
