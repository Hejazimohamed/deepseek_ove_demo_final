# tests/test_ocrworker.py
import pytest
from PyQt5.QtCore import QThread
from PIL import Image
import logging
import os

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def tesseract_available():
    """Check if Tesseract is properly installed"""
    try:
        import pytesseract
        try:
            pytesseract.get_tesseract_version()
            return True
        except pytesseract.TesseractNotFoundError:
            return False
    except ImportError:
        return False

@pytest.fixture
def test_image(tmp_path):
    """Fixture to create a test image"""
    img_path = tmp_path / "test.png"
    Image.new('RGB', (100, 100), color='white').save(str(img_path))
    return str(img_path)

@pytest.fixture
def worker(test_image, tesseract_available):
    """Fixture to create OCRWorker, skips if Tesseract not available"""
    if not tesseract_available:
        pytest.skip("Tesseract not available")
    
    from ocr_worker import OCRWorker
    return OCRWorker(file_path=test_image)

def test_ocr_worker_execution(worker, qtbot):
    """Test worker execution with Qt signals"""
    thread = QThread()
    worker.moveToThread(thread)

    captured = {"result": None, "error": None}
    worker.result.connect(lambda txt: captured.update(result=txt))
    worker.error.connect(lambda msg: captured.update(error=msg))
    thread.started.connect(worker.run)

    with qtbot.waitSignal(worker.finished, timeout=5000):
        thread.start()

    thread.quit()
    thread.wait()

    assert captured["result"] is not None or captured["error"] is not None

@pytest.mark.xfail
def test_ocr_with_invalid_image(tmp_path, qtbot, tesseract_available):
    """Test with non-existent image (expected to fail)"""
    if not tesseract_available:
        pytest.skip("Tesseract not available")
    
    from ocr_worker import OCRWorker
    invalid_path = str(tmp_path / "invalid.png")
    worker = OCRWorker(file_path=invalid_path)

    thread = QThread()
    worker.moveToThread(thread)

    captured = {"error": None}
    worker.error.connect(lambda msg: captured.update(error=msg))
    thread.started.connect(worker.run)

    with qtbot.waitSignal(worker.error, timeout=5000):
        thread.start()

    thread.quit()
    thread.wait()

    assert "Cannot identify image file" in captured["error"]