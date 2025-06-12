import pytest
from PyQt5.QtCore import QThread
from PIL import Image
from ocr_worker import OCRWorker
from ocr_logic import TesseractNotConfiguredError

@pytest.mark.timeout(15)
def test_ocrworker_run_single_page(tmp_path, qtbot):
    # تحضير صورة بيضاء للاختبار
    img_path = tmp_path / "test.png"
    Image.new('RGB', (100, 100), color='white').save(str(img_path))

    try:
        # تحضير الـ worker وربطه بـ QThread
        thread = QThread()
        worker = OCRWorker(file_path=str(img_path))
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

    except TesseractNotConfiguredError as e:
        pytest.skip(f"تخطي الاختبار بسبب: {str(e)}")