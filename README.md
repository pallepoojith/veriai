# VeriAI

An explainable AI system for real-time claim verification and misinformation analysis. VeriAI checks individual claims — not whole articles — against retrieved evidence, and flags scam patterns independently, through a web application and a browser extension.

## Repository structure

```
veriai/
├── backend/        FastAPI backend: claim extraction, evidence retrieval,
│                    NLI comparison, scam-signal detection, score fusion
├── extension/       Chrome/Edge browser extension (Manifest V3)
├── prototype/       Standalone front-end demo (index.html) — animated
│                    scorecard UI with English/Hindi/Telugu support and
│                    light/dark theme, not yet wired to the real backend
└── docs/            Architecture diagrams and the project presentation
```

## Status

| Component | Status |
|---|---|
| System architecture & design | Done |
| Front-end prototype (UI/UX demo) | Done — uses scripted mock data, multilingual (EN/HI/TE) |
| Backend pipeline (claim extraction, TF-IDF retrieval, scam rules, scoring) | Working, runnable |
| NLI verification | Heuristic placeholder — not yet a trained model (see `backend/README.md`) |
| Browser extension | Working, points at the backend API |
| Prototype ↔ backend integration | Not yet connected |
| Live evidence sources (replacing the static knowledge base) | Not yet started |

See `backend/README.md` for the exact pipeline breakdown and what still needs upgrading before submission-grade accuracy.

## Run the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Try the extension

Load `extension/` as an unpacked extension in Chrome (`chrome://extensions` → Developer mode → Load unpacked). See `extension/README.md`.

## Try the prototype

Open `prototype/index.html` directly in a browser, or publish it with any static host. It currently runs on pre-scripted demo data for seven example claims covering all four verdict types (Supported, Contradicted, Insufficient, Likely Scam), with a language switch (English/Hindi/Telugu) and a light/dark theme toggle. It is not yet connected to the real backend in `backend/`. An optional image-upload feature only activates inside Claude's own artifact preview and is safely hidden everywhere else, including GitHub and plain browsers.

## Tech stack

Python · FastAPI · scikit-learn (TF-IDF retrieval) · Manifest V3 · HTML/CSS/JS

## License

Academic project — add a license here if required by your institution.
