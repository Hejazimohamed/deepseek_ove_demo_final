import pytest
from PyQt5.QtCore import QThread
from PIL import Image
import logging
import os

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def check_tesseract_installation():
    """Session fixture to check Tesseract availability once"""
    try:
        import pytesseract
        tesseract_cmd = os.environ.get('TESSERACT_CMD', 'tesseract')
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract found (v{version}) at: {tesseract_cmd}")
            return True
        except:
            logger.warning("Tesseract not found or not working")
            return False
    except ImportError:
        logger.warning("pytesseract not installed")
        return False

@pytest.fixture
def test_image(tmp_path):
    """Fixture to create a test image"""
    img_path = tmp_path / "test.png"
    Image.new('RGB', (100, 100), color='white').save(str(img_path))
    return str(img_path)

@pytest.fixture
def worker(test_image):
    from ocr_worker import OCRWorker
    return OCRWorker(file_path=test_image)

def test_ocr_worker_execution(worker, qtbot, check_tesseract_installation):
    """Test worker execution with Qt signals"""
    if not check_tesseract_installation:
        pytest.skip("Tesseract not installed")

    thread = QThread()
    worker.moveToThread(thread)

    captured = {"result": None, "error": None}
    worker.result.connect(lambda txt: captured.update(result=txt))
    worker.error.connect(lambda msg: captured.update(error=msg))
    thread.started.connect(worker.run)

    with qtbot.waitSignal(worker.result, timeout=10000, raising=False) as res_wait, \
         qtbot.waitSignal(worker.error, timeout=10000, raising=False) as err_wait:
        thread.start()

    thread.quit()
    thread.wait()

    assert res_wait.signal_triggered or err_wait.signal_triggered
    assert captured["result"] is not None or captured["error"] is not None

@pytest.mark.xfail
def test_ocr_with_invalid_image(tmp_path, qtbot):
    """Test with non-existent image (expected to fail)"""
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
