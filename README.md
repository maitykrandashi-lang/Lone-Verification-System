# StatementIQ — Bank Statement & Payslip Analyser

Login → Register → Dashboard → Upload Payslip (pie chart) or Bank Statement (bar chart),
with OCR text extraction and BERT-based document verification.

## 1. Install prerequisites

**Tesseract OCR (required, this is a separate program, not a pip package):**
- Windows: install from https://github.com/UB-Mannheim/tesseract/wiki, then in
  `utils/ocr_utils.py` uncomment and set:
  `pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"`
- Mac: `brew install tesseract`
- Linux: `sudo apt-get install tesseract-ocr`

**Python 3.9+**

## 2. Install Python packages

```bash
cd bank_analyser
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
```

The first run will download the small BERT model (`all-MiniLM-L6-v2`, ~80MB)
used for document verification — this needs an internet connection once, then
it's cached locally and works offline.

## 3. Run the app

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

## 4. How it works

1. **Login page** → **Register** creates an account (stored in SQLite,
   passwords hashed with Werkzeug).
2. **Dashboard** → two upload cards: Payslip and Bank Statement
   (accepts .jpg, .jpeg, .png, .pdf).
3. **OCR** (`utils/ocr_utils.py`) — pytesseract reads images directly;
   PDFs use PyMuPDF to grab the native text layer, or rasterize + OCR
   pages that are scanned images.
4. **BERT verification** (`utils/bert_verifier.py`) — a Sentence-BERT
   model embeds the extracted text and compares it (cosine similarity)
   against reference descriptions of a payslip vs. a bank statement, to
   confirm the uploaded file actually matches what the user says it is.
5. **Parsing** — regex-based extraction of line items:
   - Payslip → Basic Pay, HRA, Allowances, Bonus, PF, TDS, Net Pay → **pie chart**
   - Bank statement → dated Debit/Credit transactions → **bar chart**
     (credit vs debit per month), using Chart.js.

## 5. Project structure

```
bank_analyser/
├── app.py                      # Flask routes: auth, dashboard, upload
├── requirements.txt
├── utils/
│   ├── ocr_utils.py             # OCR (images + PDFs)
│   ├── bert_verifier.py         # BERT semantic verification
│   ├── payslip_parser.py        # Regex field extraction → pie chart data
│   └── bank_parser.py           # Regex transaction extraction → bar chart data
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── payslip_result.html      # pie chart
│   └── bankstatement_result.html # bar chart
├── static/css/style.css
├── uploads/                     # uploaded files land here
└── instance/app.db              # SQLite database (auto-created on first run)
```

## 6. Tips if you're short on time before submission

- If Tesseract install is slow on the lab machine, test first with a clean,
  computer-generated PDF (e.g., export a sample payslip to PDF from Word) —
  PyMuPDF will pull the text layer directly with no OCR needed at all.
- If internet is unreliable for downloading the BERT model, run
  `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"`
  once beforehand on a machine with internet, then copy the
  `~/.cache/torch/sentence_transformers` folder to the submission machine.
- The regex patterns in `payslip_parser.py` / `bank_parser.py` are written
  for common formats — if your sample payslip/statement uses different
  wording (e.g., "CTC" instead of "Gross Pay"), just add a line to
  `FIELD_PATTERNS` / adjust `TRANSACTION_PATTERN`.
