import pytest
from PIL import Image
from main_window import OCRWorker


class DummyWorker(OCRWorker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تخزين الإشارات الواردة
        self.captured = {'prog': [], 'res': None, 'err': None}
        # عند التقدم
        self.progress.connect(
            lambda c, t: self.captured['prog'].append(
                (c, t)))
        # عند النتيجة
        self.result.connect(lambda txt: self.captured.update(res=txt))
        # عند الخطأ
        self.error.connect(lambda msg: self.captured.update(err=msg))


@pytest.mark.timeout(5)
def test_ocrworker_run_single_page(tmp_path, qtbot):
    # إنشاء صورة بسيطة
    img_path = tmp_path / "test.png"
    Image.new('RGB', (20, 20), color='white').save(str(img_path))

    # إعداد العامل
    worker = DummyWorker(
        file_path=str(img_path),
        engine="Tesseract",
        lang="eng",
        roi_rel=None,
        rotation=0,
        enhance=False
    )

    # انتظار إحدى الإشارتين قبل البدء
    with qtbot.wait_signal(worker.result, timeout=5000, raising=False) as res_wait, \
            qtbot.wait_signal(worker.error, timeout=5000, raising=False) as err_wait:
        worker.start()

    # تحقق من أن إحدى الإشارتين صدرت
    assert res_wait.signal_triggered or err_wait.signal_triggered

    # تحقق من أن captured['res'] أو captured['err'] لم يبقَ None
    assert (worker.captured['res'] is not None) or (
        worker.captured['err'] is not None)

    # اختياري: تحقق من نوع قائمة التقدم
    assert isinstance(worker.captured['prog'], list)
