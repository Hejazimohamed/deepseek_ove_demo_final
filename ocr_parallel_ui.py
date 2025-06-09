import concurrent.futures
from ocr import extract_text_from_image  # دالة ocr الخاصة بك


def process_images_parallel(image_paths):
    results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # أرسل كل صورة ليتم معالجتها في خيط (Thread) مستقل
        future_to_path = {
            executor.submit(
                extract_text_from_image,
                path): path for path in image_paths}
        for future in concurrent.futures.as_completed(future_to_path):
            path = future_to_path[future]
            try:
                text = future.result()
                results.append((path, text))
            except Exception as exc:
                results.append((path, f"حدث خطأ: {exc}"))
    return results

# الاستخدام:
# image_paths = ["img1.jpg", "img2.jpg", ...]
# results = process_images_parallel(image_paths)
# for path, text in results:
#     print(f"نتيجة {path}:\n{text}")
