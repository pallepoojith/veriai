"""
VeriAI backend -- FastAPI app.

Run:
    uvicorn app.main:app --reload --port 8000

Endpoint:
    POST /api/analyze   {"url": "...", "selected_text": "...", "caption": "...", "page_text": "..."}
    -> matches the contract already used by the browser extension and the
       front-end prototype (see popup.js / index.html), so both can be
       pointed at this server with no changes on their side.

Pipeline: claim_extraction -> evidence_retrieval -> nli -> scam_signals -> scoring
(claim-verification and scam-signal branches run independently, then fuse.)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import claim_extraction, evidence_retrieval, nli, scam_signals, scoring

app = FastAPI(title="VeriAI backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your deployed frontend origin before shipping
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    url: str | None = None
    source: str | None = None
    title: str | None = None
    caption: str | None = None
    selected_text: str | None = None
    page_text: str | None = None
    text: str | None = None  # direct text input, e.g. from the prototype's search box


def _gather_text(req: AnalyzeRequest) -> str:
    parts = [req.text, req.selected_text, req.caption, req.title, req.page_text]
    combined = " ".join(p for p in parts if p)
    return combined.strip() or (req.url or "")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    raw_text = _gather_text(req)

    # 1. Claim extraction: pick the top check-worthy claim to drive the headline verdict,
    #    but keep all extracted claims for the per-claim breakdown.
    claims = claim_extraction.extract_claims(raw_text)
    top_claim = claims[0]["text"] if claims else raw_text

    # 2 & 3. Evidence retrieval + NLI verification, per claim.
    claim_results = []
    for c in claims:
        evidence = evidence_retrieval.retrieve_evidence(c["text"], top_k=3)
        nli_result = nli.aggregate(c["text"], evidence)
        claim_results.append({
            "text": c["text"],
            "label": nli_result["label"],
            "confidence": round(max(nli_result["entail"], nli_result["contra"], 0.3) * 100),
            "explanation": scoring.EXPLANATIONS[nli_result["label"]],
            "evidence": [{"source": e["source"], "url": "", "snippet": e["text"][:160]} for e in evidence],
        })

    # 4. Scam signal branch (runs on the raw text, independent of claim extraction).
    scam_result = scam_signals.analyze(raw_text)

    # 5. Fuse using the top claim's NLI result + the scam branch.
    top_evidence = evidence_retrieval.retrieve_evidence(top_claim, top_k=3)
    top_nli = nli.aggregate(top_claim, top_evidence)
    fused = scoring.fuse(top_nli, scam_result, top_claim)

    return {
        "trust_score": fused["trust_score"],
        "verdict": fused["verdict"],
        "summary": fused["summary"],
        "sub_scores": fused["sub_scores"],
        "red_flags": fused["red_flags"],
        "claims": claim_results,
        "advice": fused["advice"],
        "confidence": fused["confidence"],
    }
