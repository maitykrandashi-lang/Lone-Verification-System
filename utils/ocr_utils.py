"""
OCR utilities.
Uses pytesseract (Tesseract OCR engine) to pull raw text out of an uploaded
document image (or PDF, via pdf2image), then applies light-weight regex
parsing to lift out the numbers we need for the charts.

Requires the Tesseract binary to be installed on the host machine:
  - Ubuntu/Debian: sudo apt-get install tesseract-ocr
  - Mac (brew):    brew install tesseract
  - Windows:        https://github.com/UB-Mannheim/tesseract/wiki

For PDF uploads, pdf2image also needs the 'poppler' binary:
  - Ubuntu/Debian: sudo apt-get install poppler-utils
  - Mac (brew):    brew install poppler
"""

import re
import os
from PIL import Image
import pytesseract

try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


def extract_text(file_path: str) -> str:
    """Run OCR on an image or PDF and return the raw extracted text."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        if not PDF_SUPPORT:
            raise RuntimeError("pdf2image/poppler not installed - cannot OCR PDFs.")
        
        # 🟢 আপনার সঠিক Poppler bin ফোল্ডারের পাথ এখানে যুক্ত করা হলো
        poppler_path = r"C:\Users\maity\Downloads\Release-26.02.0-0\poppler-26.02.0\Library\bin"
        
        # 🟢 convert_from_path এর ভেতর poppler_path প্যারামিটারটি দেওয়া হলো
        pages = convert_from_path(file_path, dpi=300, poppler_path=poppler_path)
        text = "\n".join(pytesseract.image_to_string(page) for page in pages)
    else:
        image = Image.open(file_path).convert("RGB")
        text = pytesseract.image_to_string(image)

    return text


def _find_amount(text: str, *labels) -> float:
    """Look for 'Label ... 12,345.00' style patterns and return the number."""
    for label in labels:
        pattern = rf"{label}[:\-\s]*\D*([\d,]+\.?\d*)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                continue
    return 0.0


def parse_salary_slip(text: str) -> dict:
    """Pull common salary-slip line items out of OCR text."""
    fields = {
        "Basic Pay": _find_amount(text, "basic pay", "basic"),
        "HRA": _find_amount(text, "hra", "house rent allowance"),
        "DA": _find_amount(text, "da", "dearness allowance"),
        "Other Allowances": _find_amount(text, "special allowance", "other allowance", "conveyance"),
        "Deductions": _find_amount(text, "total deduction", "deductions", "pf", "tax"),
        "Net Pay": _find_amount(text, "net pay", "net salary", "take home"),
    }
    # Fallback so the chart is never empty in a demo/test run
    if all(v == 0 for v in fields.values()):
        fields = {"Basic Pay": 0, "HRA": 0, "DA": 0, "Other Allowances": 0,
                   "Deductions": 0, "Net Pay": 0}
    return fields


def parse_bank_statement(text: str) -> dict:
    """
    Pull credit/debit transaction lines out of OCR text.
    Expected loose formats in the source doc, e.g.:
        01/03/2026  Salary Credit        CR   45,000.00
        05/03/2026  ATM Withdrawal       DR    3,000.00
    """
    credit_total, debit_total = 0.0, 0.0
    monthly_totals = {}

    line_pattern = re.compile(
        r"(\d{2}[/\-]\d{2}[/\-]\d{2,4}).{0,60}?(CR|DR|CREDIT|DEBIT).{0,20}?([\d,]+\.\d{2}|[\d,]+)",
        re.IGNORECASE,
    )

    for match in line_pattern.finditer(text):
        date_str, kind, amount_str = match.groups()
        try:
            amount = float(amount_str.replace(",", ""))
        except ValueError:
            continue

        month_key = date_str[3:] if "/" in date_str or "-" in date_str else "Unknown"
        monthly_totals.setdefault(month_key, {"credit": 0.0, "debit": 0.0})

        if kind.upper() in ("CR", "CREDIT"):
            credit_total += amount
            monthly_totals[month_key]["credit"] += amount
        else:
            debit_total += amount
            monthly_totals[month_key]["debit"] += amount

    return {
        "credit_total": credit_total,
        "debit_total": debit_total,
        "monthly_totals": monthly_totals,
    }