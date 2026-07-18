"""
BERT-based document verifier.

Approach: this is a "lone verification analyser", meaning there is no
labelled training set of real salary slips / bank statements to fine-tune
a classifier on. Instead we use bert-base-uncased purely as a frozen
sentence-embedding engine:

  1. Encode the OCR'd document text with BERT -> a single vector
     (mean-pooled last hidden state).
  2. Encode a small set of reference/anchor sentences that describe what a
     genuine salary slip / bank statement looks like.
  3. Cosine-similarity the document vector against both anchor sets.
  4. Whichever type scores highest, and clears a minimum confidence
     threshold, is accepted as verified.

This gives a legitimate BERT-driven verification signal without requiring
a labelled dataset. If you later collect real labelled examples, swap the
`_embed` + cosine-similarity logic for a fine-tuned
`BertForSequenceClassification` head - the rest of the app (routes,
templates, chart code) does not need to change.
"""

import torch
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity

_MODEL_NAME = "bert-base-uncased"
_tokenizer = None
_model = None

# Reference anchor phrases per document type. Add more real examples of
# your own institution's document wording here to improve accuracy.
ANCHORS = {
    "Salary Slip": [
        "salary slip payslip basic pay HRA DA gross salary net pay deductions provident fund employee id",
        "monthly salary statement earnings allowances tax deducted at source take home pay",
    ],
    "Bank Statement": [
        "bank statement account number IFSC transaction date credit debit balance opening balance closing balance",
        "statement of account withdrawal deposit balance carried forward branch name",
    ],
}

_THRESHOLD = 0.55  # minimum cosine similarity to accept a match


def _load_model():
    global _tokenizer, _model
    if _model is None:
        _tokenizer = BertTokenizer.from_pretrained(_MODEL_NAME)
        _model = BertModel.from_pretrained(_MODEL_NAME)
        _model.eval()
    return _tokenizer, _model


def _embed(text: str):
    tokenizer, model = _load_model()
    inputs = tokenizer(
        text, return_tensors="pt", truncation=True, max_length=512, padding=True
    )
    with torch.no_grad():
        outputs = model(**inputs)
    # mean-pool the token embeddings for a single document vector
    embedding = outputs.last_hidden_state.mean(dim=1)
    return embedding.numpy()


def verify_document(ocr_text: str, claimed_type: str) -> dict:
    """
    Returns:
      {
        "verified": bool,
        "predicted_type": str,
        "confidence": float,     # similarity score for claimed_type
        "best_score": float,     # best score across all types
      }
    """
    if not ocr_text.strip():
        return {"verified": False, "predicted_type": "Unknown",
                "confidence": 0.0, "best_score": 0.0}

    doc_vec = _embed(ocr_text)

    scores = {}
    for doc_type, anchor_texts in ANCHORS.items():
        anchor_vecs = [_embed(a) for a in anchor_texts]
        sims = [cosine_similarity(doc_vec, av)[0][0] for av in anchor_vecs]
        scores[doc_type] = max(sims)

    predicted_type = max(scores, key=scores.get)
    best_score = scores[predicted_type]
    claimed_score = scores.get(claimed_type, 0.0)

    verified = (predicted_type == claimed_type) and (claimed_score >= _THRESHOLD)

    return {
        "verified": bool(verified),
        "predicted_type": predicted_type,
        "confidence": round(float(claimed_score), 3),
        "best_score": round(float(best_score), 3),
    }
