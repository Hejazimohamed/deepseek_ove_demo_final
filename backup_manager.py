import os
import shutil
import json
import logging
from datetime import datetime
from PyQt5.QtCore import QTimer


class BackupManager:
    def __init__(self, settings_path='settings.json', backup_dir='backups'):
        self.settings_path = settings_path
        self.backup_dir = backup_dir
        self._setup_backup_dir()
        self.backup_interval = 3600000  # كل ساعة (بالمللي ثانية)
        self.timer = QTimer()
        self.timer.timeout.connect(self.create_auto_backup)

    def _setup_backup_dir(self):
        """إنشاء مجلد النسخ الاحتياطي إذا لم يكن موجودًا"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def create_backup(self, comment=None):
        """إنشاء نسخة احتياطية يدوية أو تلقائية"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"settings_{timestamp}"
        if comment:
            backup_name += f"_{comment.replace(' ', '_')}"
        backup_path = os.path.join(self.backup_dir, f"{backup_name}.json")
        try:
            # تحقق من صحة الإعدادات الحالية قبل النسخ
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                json.load(f)
            shutil.copy2(self.settings_path, backup_path)
            return True, backup_path
        except Exception as e:
            logging.error(f"فشل في إنشاء النسخ الاحتياطي: {e}")
            return False, str(e)

    def create_auto_backup(self):
        """نسخ احتياطي تلقائي صامت"""
        self.create_backup("auto")

    def start_auto_backups(self):
        """بدء النسخ الاحتياطي التلقائي الدوري"""
        self.timer.start(self.backup_interval)

    def restore_backup(self, backup_path):
        """استعادة نسخة احتياطية"""
        try:
            # التحقق من صحة النسخة الاحتياطية
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            required_keys = ["language", "engine", "auto_update"]
            if not all(key in data for key in required_keys):
                raise ValueError("ملف النسخ الاحتياطي غير صالح")
            shutil.copy2(backup_path, self.settings_path)
            return True
        except Exception as e:
            logging.error(f"فشل في استعادة النسخة الاحتياطية: {e}")
            return False

    def get_available_backups(self):
        """الحصول على قائمة بالنسخ الاحتياطية المتاحة"""
        backups = []
        if not os.path.exists(self.backup_dir):
            return backups
        for f in os.listdir(self.backup_dir):
            if f.endswith('.json') and f.startswith('settings_'):
                file_path = os.path.join(self.backup_dir, f)
                stats = os.stat(file_path)
                backups.append({
                    'path': file_path,
                    'timestamp': datetime.fromtimestamp(stats.st_ctime),
                    'size': stats.st_size
                })
        return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
