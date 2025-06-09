from PIL import Image
from main_window import preprocess_image_advanced


def test_preprocess_image_advanced_returns_image():
    img = Image.new('RGB', (100, 100), color='white')
    result = preprocess_image_advanced(img)

    assert isinstance(result, Image.Image)
    assert result.size == img.size
    assert result.mode in ('L', 'RGB', '1')
