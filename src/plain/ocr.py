import os
import json

import pytesseract
from pdf2image import convert_from_path
from tqdm import tqdm


def convert_pdf(image_path: str):
    images = convert_from_path(image_path)
    return images

def run_ocr(image_path: str, custom_config: str = r'--oem 3 --psm 0'):
    """
        image_path : path of pdf file (dirpath or filepath)
        --oem 3 : 최신 LSTM OCR 엔진 사용
        --psm 6 : 반구조화 텍스트 처리 시 사용, 모든 문자에 대해 예측 수행
    """
    def image_to_string(image_path, images):
        # image type : PIL
        pages = []
        for page, image in enumerate(tqdm(images)):
            text = pytesseract.image_to_string(image, lang='kor', config=custom_config)
            pages.append(dict(page=page, name=os.path.basename(image_path), ocr=json.dumps(text, ensure_ascii=False)))
        return pages
    
    if os.path.isfile(image_path):
        images = convert_pdf(image_path)
        pages = image_to_string(image_path, images)
        return pages
    images_path = [os.path.join(root, name) for root, _, files in os.walk(image_path)
                   for name in files if name.lower().endswith('pdf')]
    
    page_set = []
    for image_path in tqdm(images_path):
        images = convert_pdf(image_path)
        pages = image_to_string(image_path, images)
        page_set += pages
    return page_set   

if __name__ == "__main__":
    image_path = 'data/pdf'
    page_set = run_ocr(image_path)
