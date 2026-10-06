"""
Score fusion.

Combines the claim-verification branch (NLI label + entail/contra strength)
with the scam-signal branch (rule-based risk score) into one trust score,
a verdict, sub-scores and an explanation. This is the "Claim Verification
Engine" box in the architecture diagram.
"""

VERDICT_MAP = {
    "supported": "supported",
    "contradicted": "contradicted",
    "insufficient": "insufficient",
    "conflicting": "conflicting",
}

EXPLANATIONS = {
    "supported": "Retrieved evidence is consistent with this claim.",
    "contradicted": "Retrieved evidence does not support this claim; parts of it conflict with trusted sources.",
    "insufficient": "There is not enough matching evidence in the knowledge base to confirm or deny this claim.",
    "conflicting": "Different pieces of retrieved evidence point in different directions on this claim.",
}


def fuse(nli_result: dict, scam_result: dict, claim_text: str) -> dict:
    label = nli_result["label"]
    entail, contra = nli_result["entail"], nli_result["contra"]
    scam_risk = scam_result["scam_risk"]

    # Claim accuracy: how well the evidence-side reasoning supports the claim (0-100).
    if label == "supported":
        claim_accuracy = round(entail * 100)
    elif label == "contradicted":
        claim_accuracy = round((1 - contra) * 40)  # stays low
    elif label == "conflicting":
        claim_accuracy = 50
    else:
        claim_accuracy = 40  # insufficient: neither confirmed nor denied

    source_credibility = round(
        sum(e.get("credibility", 50) for e in nli_result.get("per_evidence", [])) /
        max(len(nli_result.get("per_evidence", [])), 1)
    ) if nli_result.get("per_evidence") else 40

    manipulation_risk = 10  # placeholder: no media-authenticity module wired in yet

    # Overall trust score: starts from claim accuracy, penalised by scam risk.
    trust_score = round(claim_accuracy * 0.6 + source_credibility * 0.2 - scam_risk * 0.4 + 20)
    trust_score = max(0, min(100, trust_score))

    if scam_risk >= 60:
        verdict = "likely_scam"
    else:
        verdict = VERDICT_MAP[label]

    confidence = round(max(entail, contra) * 100) if (entail or contra) else max(30, 100 - scam_risk if scam_result["flags"] else 45)
    confidence = max(30, min(97, confidence))

    explanation = EXPLANATIONS[label]
    if scam_result["flags"]:
        explanation += " In addition, this post shows patterns commonly seen in scam content."

    advice = []
    if verdict == "likely_scam":
        advice = ["Do not pay any fee or share personal documents", "Verify only through the official website", "Report the post on the platform"]
    elif verdict == "contradicted":
        advice = ["Treat this claim as inaccurate based on current evidence", "Check the cited sources for details"]
    elif verdict == "insufficient":
        advice = ["Look for the claim on an official or primary source before trusting it"]
    else:
        advice = ["Evidence generally supports this claim, but keep checking for updates"]

    return {
        "trust_score": trust_score,
        "verdict": verdict,
        "confidence": confidence,
        "summary": explanation,
        "sub_scores": {
            "claim_accuracy": claim_accuracy,
            "source_credibility": source_credibility,
            "scam_risk": scam_risk,
            "manipulation_risk": manipulation_risk,
        },
        "red_flags": scam_result["flags"],
        "advice": advice,
    }
