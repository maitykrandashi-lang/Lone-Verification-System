"""
BERT-based document verification.

We use `sentence-transformers` (all-MiniLM-L6-v2), a small distilled BERT
model, to embed the OCR-extracted text and compare it against reference
"anchor" descriptions of a payslip and a bank statement using cosine
similarity. Whichever anchor scores highest tells us what kind of document
was actually uploaded, and how confident we are that it matches what the
user said they were uploading.

The model is downloaded automatically the first time this runs (needs
internet once); after that it is cached locally (~80MB).
"""
from sentence_transformers import SentenceTransformer, util

_model = None

ANCHORS = {
    "payslip": (
        "This is a salary slip / payslip document issued by an employer. "
        "It contains basic pay, HRA, allowances, gross earnings, "
        "deductions such as provident fund and tax, and net pay for an employee "
        "for a given month."
    ),
    "bankstatement": (
        "This is a bank account statement issued by a bank. "
        "It lists a series of transactions with dates, descriptions, "
        "debit and credit amounts, and a running account balance "
        "for a customer's savings or current account."
    ),
}

CONFIDENCE_THRESHOLD = 0.35  # below this, we flag the document as unverified


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def verify_document(extracted_text, expected_type):
    """
    Returns a dict:
      {
        "is_verified": bool,
        "predicted_type": "payslip" | "bankstatement",
        "confidence": float (0-1),
        "message": str
      }
    """
    text = (extracted_text or "").strip()

    if len(text) < 15:
        return {
            "is_verified": False,
            "predicted_type": None,
            "confidence": 0.0,
            "message": "Could not read enough text from the file. "
                       "Please upload a clearer image or PDF.",
        }

    model = _get_model()
    doc_embedding = model.encode(text, convert_to_tensor=True)

    scores = {}
    for doc_type, anchor_text in ANCHORS.items():
        anchor_embedding = model.encode(anchor_text, convert_to_tensor=True)
        scores[doc_type] = float(util.cos_sim(doc_embedding, anchor_embedding)[0][0])

    predicted_type = max(scores, key=scores.get)
    confidence = scores[predicted_type]

    if confidence < CONFIDENCE_THRESHOLD:
        return {
            "is_verified": False,
            "predicted_type": predicted_type,
            "confidence": round(confidence, 3),
            "message": "This does not look like a recognizable payslip or "
                       "bank statement. Please check the file and try again.",
        }

    if predicted_type != expected_type:
        return {
            "is_verified": False,
            "predicted_type": predicted_type,
            "confidence": round(confidence, 3),
            "message": f"This file looks like a {predicted_type.replace('bankstatement', 'bank statement')}, "
                       f"not a {expected_type.replace('bankstatement', 'bank statement')}. "
                       f"Please upload the correct document type.",
        }

    return {
        "is_verified": True,
        "predicted_type": predicted_type,
        "confidence": round(confidence, 3),
        "message": "Document verified successfully.",
    }
