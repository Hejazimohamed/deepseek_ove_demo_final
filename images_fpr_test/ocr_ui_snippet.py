from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QCheckBox,
    QFileDialog)
from PyQt5.QtGui import QPixmap
import cv2


class OCRWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OCR مع تحسين تلقائي للصورة")
        self.layout = QVBoxLayout()
        self.preview_label = QLabel("معاينة الصورة")
        self.enhanced_label = QLabel("معاينة بعد التحسين")
        self.enhance_checkbox = QCheckBox(
            "تحسين الصورة تلقائيًا قبل استخراج النص")
        self.enhance_checkbox.setChecked(True)
        self.select_btn = QPushButton("اختر صورة")
        self.select_btn.clicked.connect(self.select_image)
        self.layout.addWidget(self.preview_label)
        self.layout.addWidget(self.enhanced_label)
        self.layout.addWidget(self.enhance_checkbox)
        self.layout.addWidget(self.select_btn)
        self.setLayout(self.layout)

    def select_image(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "اختر صورة", "", "Images (*.png *.jpg *.bmp)")
        if fname:
            pix = QPixmap(fname)
            self.preview_label.setPixmap(pix.scaled(200, 200))
            if self.enhance_checkbox.isChecked():
                img = cv2.imread(fname, cv2.IMREAD_GRAYSCALE)
                # هنا تضع دالة التحسين
                # img = enhance_image(img)
                enhanced_path = "enhanced_tmp.jpg"
                cv2.imwrite(enhanced_path, img)
                self.enhanced_label.setPixmap(
                    QPixmap(enhanced_path).scaled(200, 200))
            else:
                self.enhanced_label.clear()

# الاستخدام:
# app = QApplication([])
# w = OCRWidget()
# w.show()
# app.exec_()
