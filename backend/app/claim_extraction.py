"""
Claim extraction.

Splits input text into sentences and scores each one for how "check-worthy"
it is, using surface heuristics (numbers, named-entity-like capitalised
words, factual verb patterns) rather than opinion/question markers.

This is a real, working heuristic -- not a stub -- but it is not a trained
classifier. For the full project, replace `score_checkworthiness()` with a
fine-tuned transformer (e.g. RoBERTa on the ClaimBuster or CheckThat! Lab
dataset) that outputs a check-worthiness probability per sentence. The
function signature below is the seam: keep the same input/output shape and
nothing else in the pipeline needs to change.
"""
import re

OPINION_MARKERS = {"i think", "i feel", "in my opinion", "i believe", "i love", "i hate"}
QUESTION_START = re.compile(r"^\s*(who|what|when|where|why|how|is|are|do|does|can|will)\b", re.I)
FACTUAL_VERBS = re.compile(
    r"\b(is|are|was|were|has|have|had|launched|announced|hiring|cures?|prevents?|"
    r"causes?|costs?|increased|decreased|banned|approved|confirmed|denied)\b", re.I
)
NUMBER_PATTERN = re.compile(r"\b\d+([.,]\d+)?%?\b")
ENTITY_PATTERN = re.compile(r"\b([A-Z][a-zA-Z]{2,})\b")


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    # Simple sentence splitter: good enough for social captions / short posts.
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    return [p.strip() for p in parts if p.strip()]


def score_checkworthiness(sentence: str) -> float:
    """Returns 0..1: how likely this sentence is a verifiable factual claim."""
    s = sentence.lower()
    if any(m in s for m in OPINION_MARKERS):
        return 0.05
    if QUESTION_START.match(sentence) and sentence.strip().endswith("?"):
        return 0.05

    score = 0.15  # base
    if FACTUAL_VERBS.search(sentence):
        score += 0.35
    if NUMBER_PATTERN.search(sentence):
        score += 0.25
    if len(ENTITY_PATTERN.findall(sentence)) >= 1:
        score += 0.15
    if 4 <= len(sentence.split()) <= 40:
        score += 0.10
    return min(score, 0.98)


def extract_claims(text: str, threshold: float = 0.45, max_claims: int = 5) -> list[dict]:
    """Returns the check-worthy sentences, ranked, each with a confidence score."""
    sentences = split_sentences(text)
    scored = [{"text": s, "checkworthiness": round(score_checkworthiness(s), 2)} for s in sentences]
    scored = [c for c in scored if c["checkworthiness"] >= threshold]
    scored.sort(key=lambda c: c["checkworthiness"], reverse=True)
    if not scored and sentences:
        # Fall back to the longest sentence so the pipeline always has something to check.
        longest = max(sentences, key=len)
        scored = [{"text": longest, "checkworthiness": round(score_checkworthiness(longest), 2)}]
    return scored[:max_claims]
