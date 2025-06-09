import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox, QCheckBox,
    QVBoxLayout, QHBoxLayout, QTextEdit, QProgressBar, QFileDialog, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt

button_style = """
QPushButton {
    background: qlineargradient(
        spread:pad,
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #ffe29f, stop:1 #ffc700
    );
    color: #7c4a02;
    border: 1px solid #ffe29f;
    border-radius: 7px;
    font-size: 12px;
    padding: 4px 14px;
    font-weight: bold;
    margin: 2px 2px;
    min-width: 70px;
    max-width: 110px;
}
QPushButton:hover {
    background: qlineargradient(
        spread:pad,
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #ffe29f, stop:1 #ffd700
    );
    color: #8b6a00;
}
QPushButton:pressed {
    background: #ffd700;
}
"""

report_btn_style = """
QPushButton {
    background: #FFFACD;
    color: #AA8800;
    font-weight: bold;
    font-size: 12px;
    border-radius: 6px;
    border: none;
    padding: 4px 0;
    min-height: 18px;
}
QPushButton:hover {
    background-color: #ffe066;
}
"""

update_btn_style = """
QPushButton {
    background: #E0FFFF;
    color: #008B8B;
    font-weight: bold;
    font-size: 12px;
    border-radius: 6px;
    border: none;
    padding: 4px 0;
    min-height: 18px;
}
QPushButton:hover {
    background-color: #b2ebf2;
}
"""


class OCRApp(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(840, 530)
        self.setMinimumSize(520, 340)
        self.setWindowTitle("الذكي OCR (عربي / إنجليزي)")
        self.setStyleSheet("font-family: Tahoma, Arial; font-size: 13px;")
        self.init_ui()

    def init_ui(self):
        toolbar = QHBoxLayout()
        toolbar.setSpacing(0)
        toolbar.setContentsMargins(10, 12, 10, 2)

        self.import_btn = QPushButton("استيراد صور")
        self.import_btn.setStyleSheet(button_style)
        self.import_btn.clicked.connect(self.import_image)
        self.rotate_btn = QPushButton("تدوير الصورة")
        self.rotate_btn.setStyleSheet(button_style)

        self.start_btn = QPushButton("إبدأ المعالجة")
        self.start_btn.setStyleSheet(button_style)
        self.save_btn = QPushButton("حفظ النص")
        self.save_btn.setStyleSheet(button_style)

        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Tesseract"])
        self.engine_combo.setStyleSheet(
            "font-size: 12px; min-width: 72px; max-width: 110px;")
        self.engine_combo.setMinimumWidth(72)
        self.engine_combo.setMaximumWidth(110)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["ara+eng", "ara", "eng"])
        self.lang_combo.setStyleSheet(
            "font-size: 12px; min-width: 72px; max-width: 110px;")
        self.lang_combo.setMinimumWidth(72)
        self.lang_combo.setMaximumWidth(110)

        self.enhance_checkbox = QCheckBox()
        self.enhance_checkbox.setToolTip(
            "تفعيل تحسين الصورة (تصحيح الميل والتباين)")
        self.enhance_checkbox.setFixedWidth(22)

        settings_bar = QHBoxLayout()
        settings_bar.setSpacing(0)
        spacing_between = 36

        settings_bar.addWidget(self.engine_combo)
        settings_bar.addSpacing(spacing_between)
        settings_bar.addWidget(self.lang_combo)
        settings_bar.addSpacing(spacing_between)
        settings_bar.addWidget(self.enhance_checkbox)

        toolbar.addWidget(self.import_btn)
        toolbar.addSpacing(16)
        toolbar.addWidget(self.rotate_btn)
        toolbar.addSpacing(28)
        toolbar.addLayout(settings_bar)
        toolbar.addStretch(1)
        toolbar.addWidget(self.start_btn)
        toolbar.addSpacing(16)
        toolbar.addWidget(self.save_btn)

        tips_label = QLabel(
            "يرجى رفع صورة واضحة، مسطحة، بدون ميل أو ظلال. للحصول على أفضل نتيجة، ضع الورقة على سطح مستوٍ وصوّر من الأعلى مباشرة."
        )
        tips_label.setFont(QFont("Tahoma", 12))
        tips_label.setStyleSheet(
            "background-color: #FFFACD; color: #222; padding: 8px 13px; border-radius: 8px; font-size: 12px; border:0;"
        )
        tips_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        root_vbox = QVBoxLayout(self)
        root_vbox.setSpacing(5)
        root_vbox.addLayout(toolbar)
        root_vbox.addWidget(tips_label)

        main_hbox = QHBoxLayout()
        main_hbox.setContentsMargins(8, 0, 8, 0)
        main_hbox.setSpacing(9)

        sidebar_widget = QWidget()
        sidebar_vbox = QVBoxLayout(sidebar_widget)
        sidebar_vbox.setSpacing(0)
        sidebar_vbox.setContentsMargins(0, 2, 0, 2)

        self.image_preview = QLabel("لم يتم تحميل صورة بعد")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setStyleSheet(
            "border: 1px solid #CCC; background: #F9F9F9; min-width: 120px; min-height: 200px; font-size: 12px; color: #888; border-radius: 10px;"
        )
        self.image_preview.setMinimumHeight(200)
        self.image_preview.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        sidebar_vbox.addWidget(self.image_preview, 6)

        sidebar_vbox.addSpacing(18)
        self.progress_bar_preview = QProgressBar()
        self.progress_bar_preview.setValue(0)
        self.progress_bar_preview.setTextVisible(True)
        self.progress_bar_preview.setFixedHeight(32)
        self.progress_bar_preview.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar_preview.setFormat(
            "%p%")  # سيظهر فقط النسبة (مثلاً "0%")
        # هنا: محاذاة النسبة لليسار مع padding مناسب + لون رصاصي خافت
        self.progress_bar_preview.setStyleSheet("""
            QProgressBar {
                font-size: 16px;
                border-radius: 7px;
                background: #fffbe9;
                border: 2px solid #e0c97c;
                text-align: left;
                padding-left: 22px;
                color: #888;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffe29f, stop:1 #ffc700);
                border-radius: 7px;
            }
        """)
        sidebar_vbox.addWidget(self.progress_bar_preview)
        sidebar_vbox.addSpacing(8)

        sidebar_vbox.addStretch(1)

        logo_label = QLabel()
        logo_pixmap = QPixmap("logos.png")
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaled(
                65, 65, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignHCenter)
        sidebar_vbox.addWidget(logo_label)

        org_name = QLabel("LES Benghazi")
        org_name.setAlignment(Qt.AlignHCenter)
        org_name.setStyleSheet("font-weight: bold; font-size: 13px;")
        sidebar_vbox.addWidget(org_name)

        org_desc = QLabel("نقابة المهندسين الهندسية بنغازي")
        org_desc.setAlignment(Qt.AlignHCenter)
        org_desc.setStyleSheet("font-size: 11px; color: #444;")
        sidebar_vbox.addWidget(org_desc)

        report_btn = QPushButton("إبلاغ عن مشكلة")
        report_btn.setStyleSheet(report_btn_style)
        sidebar_vbox.addWidget(report_btn)

        update_btn = QPushButton("تحديث التطبيق")
        update_btn.setStyleSheet(update_btn_style)
        sidebar_vbox.addWidget(update_btn)

        sidebar_vbox.addSpacing(5)

        sidebar_footer = QLabel(
            "E-mail: hejazi.mohamed@gmail.com   واتساب: 0927232437")
        sidebar_footer.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        sidebar_footer.setStyleSheet(
            "background: transparent; color:#222; font-size:11px; padding:5px 8px;")
        sidebar_vbox.addWidget(sidebar_footer)

        right_panel = QWidget()
        right_vbox = QVBoxLayout(right_panel)
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.setSpacing(0)
        self.output_box = QTextEdit()
        self.output_box.setPlaceholderText(
            "سيظهر النص المستخرج هنا بعد المعالجة...")
        self.output_box.setAlignment(Qt.AlignRight)
        self.output_box.setStyleSheet("""
            QTextEdit {
                font-size: 15px;
                border-radius: 13px;
                background: #fffbe9;
                padding: 10px 13px;
                border: 2px solid #e0c97c;
                box-shadow: 2px 2px 12px #f3e3a7 inset, -2px -2px 8px #fff inset;
            }
        """)
        right_vbox.addWidget(self.output_box)

        main_hbox.addWidget(sidebar_widget, 0)
        main_hbox.addWidget(right_panel, 1)
        root_vbox.addLayout(main_hbox, 1)

    def import_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "اختر صورة", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_name:
            pixmap = QPixmap(file_name)
            if not pixmap.isNull():
                target_width = max(120, int(self.image_preview.width()))
                target_height = max(200, int(self.image_preview.height()))
                scaled = pixmap.scaled(
                    target_width, target_height,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.image_preview.setPixmap(scaled)
            else:
                self.image_preview.setText("تعذر تحميل الصورة")
        else:
            self.image_preview.setText("لم يتم تحميل صورة بعد")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ocr_app = OCRApp()
    ocr_app.show()
    sys.exit(app.exec_())
