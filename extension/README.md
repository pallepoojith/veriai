# ClaimCheck browser extension (Manifest V3)

## Install (Chrome / Edge)
1. Unzip this folder.
2. Open chrome://extensions and turn on Developer mode.
3. Click "Load unpacked" and select the folder.
4. Pin the ClaimCheck icon.

## Try it
- Quick test with no server: open the popup, Settings, tick "Use demo result", press Check.
- With the stub server: `uvicorn backend_stub:app --port 8000`, then untick demo mode.
- Right-click any link, selected text or page and choose "Check ... with ClaimCheck".

## API contract (POST /api/analyze)
Request:  { url, source, title?, caption?, selected_text?, page_text? }
Response: {
  trust_score: 0-100 (higher = safer),
  verdict: likely_genuine | unverified | suspicious | likely_scam,
  summary: string,
  sub_scores: { claim_accuracy, source_credibility, scam_risk, manipulation_risk },  // 0-100; the last two: higher = worse
  red_flags: [string],
  claims: [{ text, label: supported|contradicted|insufficient|conflicting, confidence, explanation, evidence: [{source, url, snippet}] }],
  advice: [string]
}

## Deploying your backend
Add your server origin to "host_permissions" in manifest.json (for example "https://api.yourdomain.com/*"), reload the extension, and paste the URL in Settings.

## Privacy
The extension sends data only when the user clicks Check or uses the right-click menu. It reads the current tab only on that click (activeTab permission).
