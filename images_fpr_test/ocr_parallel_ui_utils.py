from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QCheckBox,
    QFileDialog,
    QListWidget,
    QMessageBox)
import concurrent.futures
import sys


def extract_text_from_image(path):
    # مكان دالة ocr الخاصة بك
    import time
    time.sleep(2)  # محاكاة بطء المعالجة
    return f"النص المستخرج من {path}"


class OCRParallelWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OCR مع معالجة متوازية")
        self.layout = QVBoxLayout()
        self.file_list = QListWidget()
        self.parallel_checkbox = QCheckBox(
            "معالجة متوازية (أنصح بها للملفات الكثيرة)")
        self.parallel_checkbox.setChecked(True)
        self.select_btn = QPushButton("اختر صورًا")
        self.start_btn = QPushButton("بدء الاستخراج")
        self.select_btn.clicked.connect(self.select_images)
        self.start_btn.clicked.connect(self.start_processing)
        self.layout.addWidget(self.file_list)
        self.layout.addWidget(self.parallel_checkbox)
        self.layout.addWidget(self.select_btn)
        self.layout.addWidget(self.start_btn)
        self.setLayout(self.layout)
        self.selected_files = []

    def select_images(self):
        fnames, _ = QFileDialog.getOpenFileNames(
            self, "اختر صور", "", "Images (*.png *.jpg *.bmp)")
        if fnames:
            self.selected_files = fnames
            self.file_list.clear()
            self.file_list.addItems(fnames)

    def start_processing(self):
        if not self.selected_files:
            QMessageBox.warning(self, "تنبيه", "الرجاء اختيار صور أولاً.")
            return
        results = []
        if self.parallel_checkbox.isChecked():
            # معالجة متوازية
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_path = {
                    executor.submit(
                        extract_text_from_image,
                        path): path for path in self.selected_files}
                for future in concurrent.futures.as_completed(future_to_path):
                    path = future_to_path[future]
                    try:
                        text = future.result()
                        results.append((path, text))
                    except Exception as e:
                        results.append((path, f"خطأ: {e}"))
        else:
            # معالجة متسلسلة
            for path in self.selected_files:
                try:
                    text = extract_text_from_image(path)
                    results.append((path, text))
                except Exception as e:
                    results.append((path, f"خطأ: {e}"))
        # عرض النتائج (هنا فقط نافذة بسيطة)
        msg = "\n\n".join([f"{path}:\n{text}" for path, text in results])
        QMessageBox.information(self, "النتائج", msg)


# الاستخدام
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = OCRParallelWidget()
    w.show()
    sys.exit(app.exec_())
