import json


class SettingsManager:
    def __init__(self, file_path='settings.json'):
        self.file_path = file_path
        self.settings = {
            "language": "ara+eng",
            "engine": "Tesseract",
            "auto_update": True
        }
        self.load()

    def load(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.settings.update(data)
        except FileNotFoundError:
            self.save()

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)

    def get(self, key):
        return self.settings.get(key)

    def set(self, key, value):
        self.settings[key] = value
        self.save()
