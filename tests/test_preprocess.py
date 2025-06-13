# tests/test_preprocess.py
import sys
import os
import tempfile
import pytest
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session")
def tesseract_available():
    """Check if Tesseract is available"""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except (ImportError, pytesseract.TesseractNotFoundError):
        return False

@pytest.fixture
def test_image(tmp_path):
    """Create a test image"""
    img_path = tmp_path / "test.png"
    Image.new('RGB', (100, 100), color='white').save(str(img_path))
    return str(img_path)

def test_preprocess_image_advanced(test_image, tesseract_available):
    """Test image preprocessing function"""
    if not tesseract_available:
        pytest.skip("Tesseract not available")
    from ocr_logic import preprocess_image_advanced
    result = preprocess_image_advanced(test_image)
    assert isinstance(result, Image.Image)
    assert result.size == (100, 100)
    assert result.mode in ('L', 'RGB', '1')