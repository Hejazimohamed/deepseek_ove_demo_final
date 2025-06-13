from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel


class LogsDialog(QDialog):
    def __init__(self, log_file="ocr_app_errors.log"):
        super().__init__()
        self.setWindowTitle("سجل الأحداث والأخطاء")
        self.resize(700, 400)
        self.log_file = log_file
        layout = QVBoxLayout()
        self.info_label = QLabel("سجل الأحداث الأخير (يمكنك التحديث):")
        layout.addWidget(self.info_label)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)
        self.refresh_btn = QPushButton("تحديث")
        self.refresh_btn.clicked.connect(self.load_log)
        layout.addWidget(self.refresh_btn)
        self.setLayout(layout)
        self.load_log()

    def load_log(self):
        try:
            with open(self.log_file, encoding="utf-8") as f:
                self.text_edit.setPlainText(f.read())
        except Exception:
            self.text_edit.setPlainText(
                "لا يوجد سجل أخطاء بعد أو حدث خطأ في قراءة الملف.")
