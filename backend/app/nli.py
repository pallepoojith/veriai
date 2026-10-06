"""
Natural Language Inference (claim vs. evidence comparison).

*** This module is a heuristic placeholder, not a trained NLI model. ***
It is real, working code -- it actually reads the two texts and computes a
label -- but it uses surface cues (negation words, absolute/complete
qualifiers, numeric mismatches, lexical overlap) instead of a learned
entailment model. It is intentionally documented this way so it is not
mistaken for a trained classifier in your report or viva.

Upgrade path for the full project: replace `compare()` with a call to a
transformer fine-tuned on MNLI/FEVER (e.g. a DeBERTa-v3-MNLI checkpoint via
`transformers.pipeline("text-classification")`), which outputs calibrated
entailment / contradiction / neutral probabilities. Keep the same return
shape ({"relation": ..., "score": ...}) and nothing else needs to change.
"""
import re

NEGATION = re.compile(r"\b(no|not|never|false|fraudulent|scam|fake|does not|isn't|is not)\b", re.I)
ABSOLUTE = re.compile(r"\b(completely|always|never|totally|100%|guarantee[d]?|cures?)\b", re.I)
NUMBER = re.compile(r"\b\d+([.,]\d+)?\b")

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "on", "for",
    "and", "or", "at", "by", "with", "that", "this", "it", "as", "be", "has", "have",
}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOPWORDS and len(w) > 2}


def compare(claim: str, evidence_text: str) -> dict:
    """Returns {"relation": "entailment"|"contradiction"|"neutral", "score": 0..1}."""
    claim_tokens, ev_tokens = _tokens(claim), _tokens(evidence_text)
    overlap = claim_tokens & ev_tokens
    union = claim_tokens | ev_tokens
    jaccard = len(overlap) / len(union) if union else 0.0

    claim_negated = bool(NEGATION.search(claim))
    ev_negated = bool(NEGATION.search(evidence_text))
    claim_absolute = bool(ABSOLUTE.search(claim))

    # Numeric mismatch: both mention numbers but they differ -> likely contradiction.
    claim_nums = set(NUMBER.findall(claim))
    ev_nums = set(NUMBER.findall(evidence_text))
    numeric_conflict = bool(claim_nums and ev_nums and not (claim_nums & ev_nums))

    if jaccard < 0.08:
        return {"relation": "neutral", "score": round(0.4 + jaccard, 2)}

    # An absolute/complete claim ("completely prevents", "cures") checked against
    # evidence that itself is not absolute reads as a mismatch -> contradiction.
    if claim_absolute and jaccard >= 0.08 and not ev_negated:
        strength = min(0.6 + jaccard, 0.95)
        return {"relation": "contradiction", "score": round(strength, 2)}

    if numeric_conflict:
        return {"relation": "contradiction", "score": round(min(0.55 + jaccard, 0.9), 2)}

    if claim_negated != ev_negated and jaccard >= 0.12:
        return {"relation": "contradiction", "score": round(min(0.5 + jaccard, 0.9), 2)}

    if jaccard >= 0.18:
        return {"relation": "entailment", "score": round(min(0.5 + jaccard, 0.95), 2)}

    return {"relation": "neutral", "score": round(0.4 + jaccard, 2)}


def aggregate(claim: str, evidence: list[dict]) -> dict:
    """Runs NLI against each evidence item and aggregates into an overall verdict."""
    if not evidence:
        return {"label": "insufficient", "entail": 0.0, "contra": 0.0, "per_evidence": []}

    per_evidence = []
    entail_scores, contra_scores = [], []
    for ev in evidence:
        r = compare(claim, ev["text"])
        weight = ev.get("credibility", 50) / 100
        per_evidence.append({**r, "source": ev["source"], "id": ev["id"]})
        if r["relation"] == "entailment":
            entail_scores.append(r["score"] * weight)
        elif r["relation"] == "contradiction":
            contra_scores.append(r["score"] * weight)

    entail = max(entail_scores, default=0.0)
    contra = max(contra_scores, default=0.0)

    if entail > 0.15 and contra > 0.15 and abs(entail - contra) < 0.15:
        label = "conflicting"
    elif contra >= entail and contra > 0.2:
        label = "contradicted"
    elif entail > contra and entail > 0.2:
        label = "supported"
    else:
        label = "insufficient"

    return {"label": label, "entail": round(entail, 2), "contra": round(contra, 2), "per_evidence": per_evidence}
