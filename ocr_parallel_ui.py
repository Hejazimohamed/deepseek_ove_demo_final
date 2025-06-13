import os
import sys
from PIL import Image
import pytesseract
import concurrent.futures
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QListWidget, QListWidgetItem, QTextEdit
)
from PyQt5.QtCore import Qt

from image_preprocess import preprocess_image_advanced  # استخدم المعالجة المتقدمة

def extract_text_from_image(image_path):
    """قراءة النص من الصورة باستخدام Tesseract مع تحسين متقدم."""
    try:
        img = preprocess_image_advanced(image_path)
    except Exception:
        img = Image.open(image_path)  # fallback
    return pytesseract.image_to_string(img, lang='eng+ara')

def process_images_parallel(image_paths):
    results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_path = {
            executor.submit(extract_text_from_image, path): path for path in image_paths
        }
        for future in concurrent.futures.as_completed(future_to_path):
            path = future_to_path[future]
            try:
                text = future.result()
                results.append((path, text))
            except Exception as exc:
                results.append((path, f"حدث خطأ: {exc}"))
    return results

class OCRParallelApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("معالجة OCR متعددة")
        self.setGeometry(300, 100, 600, 400)
        self.selected_images = []

        self.layout = QVBoxLayout()
        self.select_btn = QPushButton("اختر الصور")
        self.select_btn.clicked.connect(self.select_images)
        self.layout.addWidget(self.select_btn)

        self.image_list = QListWidget()
        self.layout.addWidget(self.image_list)

        self.start_btn = QPushButton("ابدأ المعالجة")
        self.start_btn.clicked.connect(self.start_processing_threaded)
        self.layout.addWidget(self.start_btn)

        self.results_box = QTextEdit()
        self.results_box.setReadOnly(True)
        self.layout.addWidget(self.results_box)

        self.setLayout(self.layout)

    def select_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "اختر الصور", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if files:
            self.selected_images = files
            self.image_list.clear()
            for file in files:
                QListWidgetItem(os.path.basename(file), self.image_list)

    def start_processing_threaded(self):
        if not self.selected_images:
            self.results_box.setPlainText("يرجى اختيار صور أولاً.")
            return

        self.results_box.setPlainText("جارٍ المعالجة...")
        QApplication.processEvents()

        results = process_images_parallel(self.selected_images)

        output = []
        for path, text in results:
            output.append(f"📄 {os.path.basename(path)}:\n{text.strip()}\n" + "-"*40)

        self.results_box.setPlainText("\n".join(output))


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = OCRParallelApp()
    window.show()
    sys.exit(app.exec_())
