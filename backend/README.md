# VeriAI backend (prototype)

A working FastAPI backend implementing the claim-verification + scam-signal
pipeline from the architecture diagram. This is a **real, runnable
implementation** of the pipeline shape, with two components clearly marked
as heuristic placeholders standing in for trained ML models (see below) —
built this way because this sandbox has no internet access to download
transformer models or call live search APIs. Everything else (claim
extraction heuristics, TF-IDF evidence retrieval, scam-signal rules, score
fusion, the API contract) is genuine working code you can build on directly.

## Run it

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Test it:
```bash
curl -X POST localhost:8000/api/analyze -H "Content-Type: application/json" \
  -d '{"text":"Drinking coffee completely prevents heart disease"}'
```

Try the three example claims from your slides: the coffee claim, a TCS
hiring scam post, and "onion rate is low today" — each produces a
different verdict for a different reason, computed from the code, not
hardcoded per example. All four were tested end to end while building this.

## Connect your existing frontends

- **Browser extension**: in the extension's Settings, set the API URL to
  `http://localhost:8000/api/analyze`. No code changes needed — the request/
  response shape already matches.
- **Web prototype** (`veriai-prototype.html`): currently uses mock data.
  To connect it for real, replace the mock lookup with a fetch call to this
  server. Ask and I can make this change for you directly.

## Pipeline modules

| File | What it does | Status |
|---|---|---|
| `claim_extraction.py` | Splits text into sentences, scores check-worthiness | Real heuristic |
| `evidence_retrieval.py` | TF-IDF + cosine similarity search over `knowledge_base.json` | Real (lexical, not neural) |
| `nli.py` | Compares claim vs. evidence text for entailment/contradiction | **Heuristic placeholder** — see below |
| `scam_signals.py` | Rule-based fee/urgency/domain-mismatch detection | Real |
| `scoring.py` | Fuses both branches into trust score + verdict | Real |
| `main.py` | FastAPI app wiring it all together | Real |

## What's a placeholder, and how to upgrade it

**`nli.py`** does not use a trained NLI model. It uses negation detection,
"completely/always/cures"-style absolute-language detection, numeric
mismatch detection, and lexical overlap to approximate entailment vs.
contradiction. This is real working logic, but it is not what your report
should call a "transformer-based NLI model" — be precise about this
distinction with your faculty; call it a rule-based comparison stage that
you plan to (or did) replace with a trained model.

To upgrade to a real model once you have internet access (your own machine,
Colab, or a cloud instance):
```python
from transformers import pipeline
nli_pipe = pipeline("text-classification", model="microsoft/deberta-v3-base-mnli")
# nli_pipe(f"{evidence_text} [SEP] {claim_text}") -> entailment/contradiction/neutral + score
```
Replace the body of `compare()` in `nli.py` with this call, keep the same
return shape `{"relation": ..., "score": ...}`, and nothing else in the
pipeline needs to change.

**`evidence_retrieval.py`** uses TF-IDF, a real but lexical (word-overlap)
method, not dense neural embeddings. To upgrade:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("BAAI/bge-base-en-v1.5")
# embed claim + KB texts, store in FAISS/Chroma, retrieve by cosine similarity
```

**`knowledge_base.json`** currently has 8 hand-written evidence documents
covering your three demo examples. For the real system, replace this with
live retrieval from Google Fact Check Tools API, news APIs, and a scraped/
curated trusted-source corpus.

## Known limitations to state in your report

- NLI is heuristic, not a trained model (see above) — this is the most
  important thing to be upfront about in your viva.
- The knowledge base is a small static file, not live retrieval.
- No media/deepfake check is wired in yet (`manipulation_risk` is a fixed placeholder).
- No database persistence, caching, or auth — add these before any real deployment.
