import sys
import os
import zipfile
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QListWidget, QMessageBox
)


class UpdateZipper(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("منشئ التحديث - ضغط الملفات")
        self.setGeometry(100, 100, 500, 400)

        self.layout = QVBoxLayout()

        self.label = QLabel("اختر الملفات التي تريد إضافتها للتحديث:")
        self.layout.addWidget(self.label)

        self.file_list = QListWidget()
        self.layout.addWidget(self.file_list)

        self.add_btn = QPushButton("➕ إضافة ملفات")
        self.add_btn.clicked.connect(self.add_files)
        self.layout.addWidget(self.add_btn)

        self.clear_btn = QPushButton("🧹 مسح القائمة")
        self.clear_btn.clicked.connect(self.clear_files)
        self.layout.addWidget(self.clear_btn)

        self.zip_btn = QPushButton("📦 إنشاء update_temp.zip")
        self.zip_btn.clicked.connect(self.create_zip)
        self.layout.addWidget(self.zip_btn)

        self.setLayout(self.layout)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "اختر الملفات", "", "All Files (*)")
        existing = {self.file_list.item(i).text()
                    for i in range(self.file_list.count())}
        for f in files:
            if f not in existing:
                self.file_list.addItem(f)
                existing.add(f)

    def clear_files(self):
        self.file_list.clear()

    def create_zip(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "تحذير", "لم يتم تحديد أي ملفات.")
            return

        zip_path = os.path.join(os.getcwd(), "update_temp.zip")
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for i in range(self.file_list.count()):
                    file_path = self.file_list.item(i).text()
                    if not os.path.isfile(file_path):
                        raise FileNotFoundError(
                            f"الملف غير موجود: {file_path}")
                    arcname = os.path.basename(file_path)
                    zipf.write(file_path, arcname)
            QMessageBox.information(self, "تم", f"تم إنشاء الملف:\n{zip_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل إنشاء ملف التحديث: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = UpdateZipper()
    win.show()
    sys.exit(app.exec_())
