const DEFAULT_API = "http://localhost:8000/api/analyze";
const $ = (id) => document.getElementById(id);

const VERDICTS = {
  likely_genuine: { label: "Likely genuine", cls: "good" },
  unverified: { label: "Unverified", cls: "warn" },
  suspicious: { label: "Suspicious", cls: "bad" },
  likely_scam: { label: "Likely scam", cls: "danger" },
};
const CLAIM_LABELS = {
  supported: ["Supported by evidence", "good"],
  contradicted: ["Contradicted by evidence", "danger"],
  insufficient: ["Insufficient evidence", "warn"],
  conflicting: ["Conflicting evidence", "bad"],
};
// [key, label, higherIsWorse]
const SUB_SCORES = [
  ["claim_accuracy", "Claim accuracy", false],
  ["source_credibility", "Source credibility", false],
  ["scam_risk", "Scam risk", true],
  ["manipulation_risk", "Manipulation risk", true],
];

function h(tag, props = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") e.className = v;
    else e.setAttribute(k, v);
  }
  kids.flat().forEach((k) => e.append(k));
  return e;
}

const band = (score) => (score >= 70 ? "good" : score >= 40 ? "warn" : "danger");
const clamp = (n) => Math.max(0, Math.min(100, Math.round(Number(n) || 0)));

async function getPageContext(tab) {
  try {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const meta = (n) => document.querySelector(`meta[property="${n}"],meta[name="${n}"]`)?.content || "";
        return {
          title: document.title,
          caption: meta("og:description") || meta("description"),
          selected_text: String(getSelection()),
          page_text: (document.body?.innerText || "").slice(0, 4000),
        };
      },
    });
    return result;
  } catch {
    return null;
  }
}

async function analyze(payload) {
  const { apiUrl, demo } = await chrome.storage.local.get(["apiUrl", "demo"]);
  if (demo) return mockResult();
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 30000);
  try {
    const res = await fetch(apiUrl || DEFAULT_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: ctrl.signal,
    });
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

function setStatus(text, isError = false) {
  const s = $("status");
  s.hidden = !text;
  s.textContent = text || "";
  s.className = isError ? "error" : "";
}

function renderScore(r) {
  const score = clamp(r.trust_score);
  const v = VERDICTS[r.verdict] || VERDICTS.unverified;
  const circ = 2 * Math.PI * 42;
  const ring = h("div", { class: "ring" });
  ring.innerHTML = `<svg width="96" height="96" viewBox="0 0 96 96" aria-hidden="true">
    <circle class="track" cx="48" cy="48" r="42"/>
    <circle class="value ${band(score)}" cx="48" cy="48" r="42" stroke="currentColor"
      stroke-dasharray="${circ}" stroke-dashoffset="${circ * (1 - score / 100)}"/></svg>`;
  ring.append(h("span", { class: band(score), "aria-label": `Trust score ${score} out of 100` }, String(score)));
  return h("section", { class: "card summary" },
    ring,
    h("div", {},
      h("span", { class: `pill ${v.cls}` }, v.label),
      h("p", {}, r.summary || "Trust score out of 100. Higher means safer.")));
}

function renderSubScores(r) {
  const card = h("section", { class: "card" }, h("h2", {}, "Score breakdown"));
  for (const [key, label, worse] of SUB_SCORES) {
    if (r.sub_scores?.[key] == null) continue;
    const val = clamp(r.sub_scores[key]);
    const cls = band(worse ? 100 - val : val);
    card.append(h("div", { class: "sub" },
      h("span", {}, label), h("b", {}, String(val)),
      h("div", { class: "bar" }, Object.assign(h("div", { class: `fill ${cls}` }), { style: `width:${val}%` }))));
  }
  return card;
}

function renderList(title, items, extraClass = "") {
  if (!items?.length) return null;
  return h("section", { class: `card ${extraClass}` }, h("h2", {}, title),
    h("ul", {}, items.map((t) => h("li", {}, String(t)))));
}

function renderClaims(r) {
  if (!r.claims?.length) return null;
  const card = h("section", { class: "card" }, h("h2", {}, `Claims found (${r.claims.length})`));
  for (const c of r.claims) {
    const [label, cls] = CLAIM_LABELS[c.label] || CLAIM_LABELS.insufficient;
    const body = h("div", {}, h("p", {}, c.explanation || ""));
    for (const ev of c.evidence || []) {
      const safe = /^https?:\/\//i.test(ev.url || "");
      body.append(h("p", {},
        safe ? Object.assign(h("a", { target: "_blank", rel: "noreferrer noopener", href: ev.url }), { textContent: ev.source || ev.url }) : (ev.source || "Source"),
        ev.snippet ? `: ${ev.snippet}` : ""));
    }
    card.append(h("div", { class: "claim" },
      h("q", {}, c.text || ""),
      h("div", { class: "meta" }, h("b", { class: cls }, label), ` · confidence ${clamp(c.confidence)}%`),
      h("details", {}, h("summary", {}, "Why and evidence"), body)));
  }
  return card;
}

function render(r) {
  const out = $("result");
  out.replaceChildren(
    ...[renderScore(r), renderSubScores(r), renderList("Red flags", r.red_flags),
      renderClaims(r), renderList("What to do", r.advice, "advice")].filter(Boolean));
  out.hidden = false;
}

async function run(url, extra = {}) {
  $("result").hidden = true;
  $("go").disabled = true;
  setStatus("Checking claims and sources...");
  try {
    render(await analyze({ url, source: "extension", ...extra }));
    setStatus("");
  } catch (e) {
    const { apiUrl } = await chrome.storage.local.get("apiUrl");
    setStatus(`Could not get a result (${e.message}). Check that the server is running at ${apiUrl || DEFAULT_API}, or turn on the demo result in Settings.`, true);
  } finally {
    $("go").disabled = false;
  }
}

function mockResult() {
  return {
    trust_score: 18,
    verdict: "likely_scam",
    summary: "This looks like a fake hiring post. No matching announcement was found on the official careers page.",
    sub_scores: { claim_accuracy: 22, source_credibility: 15, scam_risk: 91, manipulation_risk: 74 },
    red_flags: ["Application link is not on the official company domain", "Asks for a registration fee", "Urgent deadline: apply within 24 hours"],
    claims: [{
      text: "TCS is hiring 10,000 freshers, apply now",
      label: "contradicted", confidence: 82,
      explanation: "The official careers page lists no drive of this kind, and the link points to a look-alike domain.",
      evidence: [{ source: "TCS Careers (official)", url: "https://www.tcs.com/careers", snippet: "No matching announcement found" }],
    }],
    advice: ["Do not pay any fee or share personal documents", "Apply only through the official careers page", "Report the post on the platform"],
  };
}

(async function init() {
  const { apiUrl, demo, pending } = await chrome.storage.local.get(["apiUrl", "demo", "pending"]);
  $("api").value = apiUrl || "";
  $("demo").checked = !!demo;
  $("api").addEventListener("change", (e) => chrome.storage.local.set({ apiUrl: e.target.value.trim() }));
  $("demo").addEventListener("change", (e) => chrome.storage.local.set({ demo: e.target.checked }));

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  $("form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = $("url").value.trim();
    const extra = tab && url === tab.url ? (await getPageContext(tab)) || {} : {};
    run(url, extra);
  });

  if (pending) {
    await chrome.storage.local.remove("pending");
    chrome.action.setBadgeText({ text: "" });
    $("url").value = pending.url;
    run(pending.url, { selected_text: pending.text });
  } else if (tab?.url && /^https?:/.test(tab.url)) {
    $("url").value = tab.url;
  }
})();
