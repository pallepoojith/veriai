"""
Scam signal detection.

Real, working rule-based checks over the raw post text and any link it
contains -- fee/payment requests, urgency language, non-official domains,
and off-platform contact requests. This is the branch that catches fraud
even when there is no clean factual claim to verify (e.g. "apply now,
limited seats!" has nothing an NLI model can entail or contradict).

Upgrade path: add a trained classifier (e.g. fine-tuned on a labelled job
scam / phishing dataset) as an additional signal, and/or a domain-registry
lookup service instead of the small OFFICIAL_DOMAINS map below.
"""
import re
from urllib.parse import urlparse

FEE_PATTERNS = re.compile(
    r"\b(registration fee|processing fee|security deposit|training fee|pay \u20b9|pay rs\.?|"
    r"refundable fee|small fee|advance payment)\b", re.I
)
URGENCY_PATTERNS = re.compile(
    r"\b(apply now|limited seats|hurry|within 24 hours|last date today|only today|"
    r"act fast|offer ends|don't miss|expires soon)\b", re.I
)
OFFPLATFORM_CONTACT = re.compile(r"\b(whatsapp|telegram)\b.{0,20}\b(contact|dm|message|apply)\b", re.I)
URL_PATTERN = re.compile(r"https?://[^\s]+", re.I)

# Small illustrative registry. In production this would be a maintained
# database of verified official domains for companies/institutions.
OFFICIAL_DOMAINS = {
    "tcs": ["tcs.com"],
    "infosys": ["infosys.com"],
    "wipro": ["wipro.com"],
}


def _mentioned_org(text: str) -> str | None:
    low = text.lower()
    for org in OFFICIAL_DOMAINS:
        if org in low:
            return org
    return None


def _link_domain_flags(text: str) -> list[str]:
    flags = []
    org = _mentioned_org(text)
    urls = URL_PATTERN.findall(text)
    if org and urls:
        official = OFFICIAL_DOMAINS[org]
        for u in urls:
            netloc = urlparse(u).netloc.lower()
            if not any(netloc == d or netloc.endswith("." + d) for d in official):
                flags.append(f"Link domain '{netloc}' does not match the official {org.upper()} domain")
    elif org and not urls:
        flags.append(f"Mentions {org.upper()} but includes no link to the official {OFFICIAL_DOMAINS[org][0]} domain")
    return flags


def analyze(text: str) -> dict:
    flags = []
    if FEE_PATTERNS.search(text):
        flags.append("Asks for a fee, deposit or advance payment")
    if URGENCY_PATTERNS.search(text):
        flags.append("Uses urgency language typical of scam posts")
    if OFFPLATFORM_CONTACT.search(text):
        flags.append("Directs contact to WhatsApp/Telegram instead of an official channel")
    flags.extend(_link_domain_flags(text))

    # Simple weighted score: each flag type contributes, capped at 100.
    weights = {"fee": 35, "urgency": 20, "offplatform": 20, "domain": 30}
    score = 0
    joined = " ".join(flags).lower()
    if "fee" in joined or "deposit" in joined or "payment" in joined:
        score += weights["fee"]
    if "urgency" in joined:
        score += weights["urgency"]
    if "whatsapp" in joined or "telegram" in joined:
        score += weights["offplatform"]
    if "domain" in joined:
        score += weights["domain"]
    score = min(score, 97) if flags else 5

    return {"scam_risk": score, "flags": flags}
