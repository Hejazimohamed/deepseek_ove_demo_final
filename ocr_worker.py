from PyQt5.QtCore import QObject, pyqtSignal
from ocr_logic import extract_text_from_image

class OCRWorker(QObject):
    result = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, file_path, engine="Tesseract", lang="eng", roi_rel=None, rotation=0, enhance=False):
        super().__init__()
        self.file_path = file_path
        self.engine = engine
        self.lang = lang
        self.roi_rel = roi_rel
        self.rotation = rotation
        self.enhance = enhance

    def run(self):
        try:
            text = extract_text_from_image(self.file_path)
            self.result.emit(text)
        except Exception as e:
            self.error.emit(str(e))
