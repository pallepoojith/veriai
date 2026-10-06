"""
Evidence retrieval.

Loads the local knowledge base and indexes it with a TF-IDF vector space,
then retrieves the top-k most similar evidence documents for a claim using
cosine similarity. This is a genuine, working semantic-search stand-in --
TF-IDF captures word/phrase overlap weighted by rarity, which is a classic
and real (if lexical, not neural) retrieval method.

Upgrade path for the full project: replace TfidfVectorizer with dense
embeddings from a sentence-transformers model (e.g. bge-base, e5-base) and
swap cosine similarity over TF-IDF vectors for a FAISS or Chroma index.
Everything downstream (NLI, scoring) consumes the same `evidence` list
shape, so the swap is local to this file.
"""
import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KB_PATH = Path(__file__).parent / "knowledge_base.json"


class EvidenceIndex:
    def __init__(self, kb_path: Path = KB_PATH):
        self.docs = json.loads(kb_path.read_text())
        corpus = [d["text"] for d in self.docs]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(corpus)

    def search(self, query: str, top_k: int = 3, min_similarity: float = 0.05) -> list[dict]:
        q_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self.matrix)[0]
        ranked = sorted(zip(self.docs, sims), key=lambda x: x[1], reverse=True)
        results = []
        for doc, sim in ranked[:top_k]:
            if sim < min_similarity:
                continue
            results.append({
                "id": doc["id"],
                "source": doc["source"],
                "credibility": doc["credibility"],
                "text": doc["text"],
                "similarity": round(float(sim), 3),
            })
        return results


_index = None


def get_index() -> EvidenceIndex:
    global _index
    if _index is None:
        _index = EvidenceIndex()
    return _index


def retrieve_evidence(claim_text: str, top_k: int = 3) -> list[dict]:
    return get_index().search(claim_text, top_k=top_k)
