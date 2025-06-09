from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QCheckBox,
    QFileDialog,
    QListWidget,
    QMessageBox,
    QProgressBar)
import concurrent.futures
import sys
import time


def enhance_image_dummy(path):
    # دالة تحسين وهمية (استبدلها بدالة تحسينك الفعلية)
    time.sleep(0.5)
    return path  # في التطبيق الفعلي: أعد مسار الصورة المحسنة أو الصورة نفسها


def extract_text_from_image_dummy(path):
    # دالة OCR وهمية (استبدلها بدالة OCR الفعلية)
    time.sleep(1.5)
    return f"النص المستخرج من {path}"


class OCRParallelProgressWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OCR مع شريط تقدم وتحسين تلقائي")
        self.layout = QVBoxLayout()
        self.file_list = QListWidget()
        self.enhance_checkbox = QCheckBox("تحسين الصور تلقائيًا قبل الاستخراج")
        self.enhance_checkbox.setChecked(True)
        self.parallel_checkbox = QCheckBox(
            "معالجة متوازية (أسرع للملفات الكثيرة)")
        self.parallel_checkbox.setChecked(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.select_btn = QPushButton("اختر صورًا")
        self.start_btn = QPushButton("بدء الاستخراج")
        self.select_btn.clicked.connect(self.select_images)
        self.start_btn.clicked.connect(self.start_processing)
        self.layout.addWidget(self.file_list)
        self.layout.addWidget(self.enhance_checkbox)
        self.layout.addWidget(self.parallel_checkbox)
        self.layout.addWidget(self.progress_bar)
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

        self.progress_bar.setMaximum(len(self.selected_files))
        self.progress_bar.setValue(0)
        results = []
        counter = 0

        def process_one(path):
            img_path = path
            if self.enhance_checkbox.isChecked():
                img_path = enhance_image_dummy(
                    path)  # استبدلها بدالتك الحقيقية
            text = extract_text_from_image_dummy(img_path)
            return (path, text)

        if self.parallel_checkbox.isChecked():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_path = {
                    executor.submit(process_one, path): path
                    for path in self.selected_files
                }
                for future in concurrent.futures.as_completed(future_to_path):
                    path = future_to_path[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        results.append((path, f"خطأ: {e}"))
                    counter += 1
                    self.progress_bar.setValue(counter)
        else:
            for path in self.selected_files:
                try:
                    result = process_one(path)
                    results.append(result)
                except Exception as e:
                    results.append((path, f"خطأ: {e}"))
                counter += 1
                self.progress_bar.setValue(counter)

        msg = "\n\n".join([f"{path}:\n{text}" for path, text in results])
        QMessageBox.information(self, "النتائج", msg)
        self.progress_bar.setValue(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = OCRParallelProgressWidget()
    w.show()
    sys.exit(app.exec_())
