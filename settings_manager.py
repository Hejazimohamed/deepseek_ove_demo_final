import json
import os

class SettingsManager:
    def __init__(self, file_path='settings.json'):
        self.file_path = file_path
        self.settings = {
            "language": "ara+eng",
            "engine": "Tesseract",
            "auto_update": True,
            "send_crash_reports": False
        }
        self.load()

    def load(self):
        try:
            if not os.path.exists(self.file_path):
                self.save()
                return
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.settings.update(data)
        except Exception:
            # الملف تالف أو حذف: إعادة الإنشاء الافتراضي
            self.save()

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()