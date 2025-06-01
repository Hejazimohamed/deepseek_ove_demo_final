from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QCheckBox

class SettingsDialog(QDialog):
    def __init__(self, settings_manager):
        super().__init__()
        self.setWindowTitle("الإعدادات")
        self.settings = settings_manager
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # اختيار اللغة
        lang_layout = QHBoxLayout()
        lang_label = QLabel("اللغة:")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["ara+eng", "ara", "eng"])
        self.lang_combo.setCurrentText(self.settings.get("language"))
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)

        # اختيار المحرك
        engine_layout = QHBoxLayout()
        engine_label = QLabel("المحرك:")
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Tesseract", "EasyOCR", "كلاهما"])
        self.engine_combo.setCurrentText(self.settings.get("engine"))
        engine_layout.addWidget(engine_label)
        engine_layout.addWidget(self.engine_combo)
        layout.addLayout(engine_layout)

        # خيار التحديث التلقائي
        self.auto_update_check = QCheckBox("تفعيل التحديث التلقائي")
        self.auto_update_check.setChecked(self.settings.get("auto_update"))
        layout.addWidget(self.auto_update_check)

        # أزرار الحفظ والإلغاء
        button_layout = QHBoxLayout()
        save_btn = QPushButton("حفظ")
        cancel_btn = QPushButton("إلغاء")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def save_settings(self):
        self.settings.set("language", self.lang_combo.currentText())
        self.settings.set("engine", self.engine_combo.currentText())
        self.settings.set("auto_update", self.auto_update_check.isChecked())
        self.accept()
