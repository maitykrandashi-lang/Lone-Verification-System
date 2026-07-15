"""
OCR utility.
- Images (jpg/png) -> pytesseract directly.
- PDFs -> render each page to an image with PyMuPDF (fitz), then OCR each page.

Requires the Tesseract binary to be installed on the machine (this is a
separate program, not something `pip install` sets up for you):
  Windows : https://github.com/UB-Mannheim/tesseract/wiki  (installer .exe)
  Mac     : brew install tesseract
  Linux   : sudo apt-get install tesseract-ocr
"""
import os
import shutil
import pytesseract
from PIL import Image
import fitz  # PyMuPDF

# Auto-detect Tesseract on Windows if it's not already on PATH.
# (On Mac/Linux, `brew install` / `apt-get install` put it on PATH automatically.)
if shutil.which("tesseract") is None:
    _common_windows_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for _path in _common_windows_paths:
        if os.path.isfile(_path):
            pytesseract.pytesseract.tesseract_cmd = _path
            break


def extract_text_from_image(image_path):
    img = Image.open(image_path)
    try:
        return pytesseract.image_to_string(img)
    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract OCR is not installed (or not found automatically). "
            "Install it from https://github.com/UB-Mannheim/tesseract/wiki, "
            "then either restart the app, or open utils/ocr_utils.py and set "
            "pytesseract.pytesseract.tesseract_cmd to the exact path of "
            "tesseract.exe on your machine."
        )


def extract_text_from_pdf(pdf_path):
    text_chunks = []
    doc = fitz.open(pdf_path)
    for page in doc:
        # First try native text layer (fast, works for digitally generated PDFs)
        native_text = page.get_text().strip()
        if len(native_text) > 30:
            text_chunks.append(native_text)
            continue
        # Fallback: rasterize the page and OCR it (for scanned PDFs)
        pix = page.get_pixmap(dpi=300)
        img_path = pdf_path + f".page{page.number}.png"
        pix.save(img_path)
        text_chunks.append(extract_text_from_image(img_path))
        os.remove(img_path)
    doc.close()
    return "\n".join(text_chunks)


def extract_text(file_path):
    ext = file_path.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return extract_text_from_pdf(file_path)
    return extract_text_from_image(file_path)
