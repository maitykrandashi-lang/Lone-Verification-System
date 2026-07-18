# Loan Verification Analyser (BERT + OCR)

A two-page Flask app:
1. **Login page** — green "Login Successfully" / red "Login Failed!" message.
2. **Upload page** — pick document type (Salary Slip / Bank Statement), upload
   the file, OCR reads it, BERT verifies it matches the selected type, then
   a chart is generated:
   - Salary Slip → pie chart of pay components.
   - Bank Statement → pie chart (credit vs debit) + bar chart (monthly totals).

## How it works (pipeline)

```
Upload file
   │
   ▼
OCR (pytesseract) ── extracts raw text from image/PDF
   │
   ▼
BERT (bert-base-uncased) ── embeds the text, compares by cosine similarity
   │                         to reference phrases for each doc type
   ▼
Verified? ── if yes → regex-parse the numbers → matplotlib chart(s)
          ── if no  → show "could not verify", no chart
```

## Step-by-step setup

1. **Install Python 3.10+** and create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

2. **Install system dependencies** (needed by OCR):
   - Tesseract OCR engine:
     - Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
     - macOS: `brew install tesseract`
     - Windows: install from https://github.com/UB-Mannheim/tesseract/wiki
   - (Optional, for PDF uploads) Poppler:
     - Ubuntu/Debian: `sudo apt-get install poppler-utils`
     - macOS: `brew install poppler`

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   The first run will download `bert-base-uncased` (~440MB) from
   Hugging Face — this needs an internet connection once; it's cached
   locally after that.

4. **Run the app:**
   ```bash
   python app.py
   ```
   Visit `http://127.0.0.1:5000` in your browser.

5. **Log in** with a demo account:
   - `admin` / `admin123`
   - `analyst` / `loan@2026`

   (Replace `VALID_USERS` in `app.py` with a real user database before
   using this for anything beyond a demo.)

6. **Upload a document:**
   - Choose "Salary Slip" or "Bank Statement" from the dropdown.
   - Choose the file (image or PDF).
   - Click "Upload & Verify".
   - If BERT confirms the document text matches the selected type, you'll
     see a green "Verified" badge and the relevant chart(s). If it doesn't
     match (e.g. you picked "Salary Slip" but uploaded a bank statement),
     you'll see a red "Could not verify" message and no chart.

## Project structure

```
loan_verification_app/
├── app.py                  # Flask routes: login, upload/verify, logout
├── requirements.txt
├── templates/
│   ├── login.html
│   └── upload.html
├── static/
│   └── style.css
└── utils/
    ├── ocr_utils.py        # Tesseract OCR + regex field extraction
    ├── bert_verifier.py    # BERT embedding similarity verification
    └── chart_utils.py      # matplotlib pie/bar chart generation
```

## Notes & next steps

- **Why similarity instead of a trained classifier?** A "lone" verification
  analyser has no labelled training set. `bert_verifier.py` embeds the OCR
  text and compares it against reference phrases per document type using
  cosine similarity — no training data required. If you later collect
  labelled real/fake examples, swap that logic for a fine-tuned
  `BertForSequenceClassification` head without touching the rest of the app.
- **OCR accuracy** depends heavily on scan/photo quality. For production
  use, consider adding image pre-processing (deskew, contrast, binarization
  via OpenCV) before passing to Tesseract.
- **Field extraction** (`parse_salary_slip` / `parse_bank_statement`) uses
  regex tuned to common wording — you'll likely want to adjust the label
  keywords to match your users' actual document formats.
- **Security**: this demo stores credentials in a plain dict and uses a
  hardcoded Flask secret key — replace both before deploying anywhere real,
  and delete uploaded files after processing (already done in `app.py`).
