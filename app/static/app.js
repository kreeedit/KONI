/* KONI reader — vanilla JS single-page app (hash routing). */
"use strict";

const API = (p) => "/api" + p;
const $view = () => document.getElementById("view");
const toast = (msg) => {
  const t = document.getElementById("toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 2600);
};
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fetchJSON = async (url) => {
  const r = await fetch(url);
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
};

/* ---------- settings (font size / line-height / theme) ---------- */
const settings = {
  load() {
    try { return JSON.parse(localStorage.getItem("opentgl") || "{}"); }
    catch { return {}; }
  },
  save(o) { localStorage.setItem("opentgl", JSON.stringify(o)); },
};
function applySettings() {
  const s = settings.load();
  const size = s.size ?? 20, lh = s.lh ?? 1.8, theme = s.theme ?? "light";
  document.documentElement.style.setProperty("--reader-size", size + "px");
  document.documentElement.style.setProperty("--reader-lh", lh);
  document.body.dataset.theme = theme;
}
function changeSize(delta) {
  const s = settings.load();
  const size = Math.min(34, Math.max(14, (s.size ?? 20) + delta));
  settings.save({ ...s, size });
  applySettings();
}
function cycleLineHeight() {
  const s = settings.load();
  const steps = [1.5, 1.7, 1.8, 2.0, 2.3];
  const cur = s.lh ?? 1.8;
  const next = steps[(steps.indexOf(cur) + 1) % steps.length] ?? 1.8;
  settings.save({ ...s, lh: next });
  applySettings();
  toast("Line spacing: " + next);
}
function toggleTheme() {
  const s = settings.load();
  const theme = (s.theme ?? "light") === "light" ? "dark" : "light";
  settings.save({ ...s, theme });
  applySettings();
}

/* ---------- router ---------- */
function route() {
  const h = location.hash.replace(/^#/, "") || "/";
  const [pathPart, queryPart] = h.split("?");
  const parts = pathPart.split("/").filter(Boolean); // e.g. ["author","0012"]
  const q = {};
  if (queryPart) queryPart.split("&").forEach((kv) => {
    const [k, v] = kv.split("="); q[k] = decodeURIComponent(v || "");
  });
  if (parts[0] === "author" && parts[1]) return renderAuthor(parts[1]);
  if (parts[0] === "read" && parts[1] && parts[2]) return renderReader(parts[1], parts[2], parts[3] | 0);
  if (parts[0] === "compare") return renderCompare(q);
  renderHome();
}

/* ---------- home / search (client-side filter over all authors) ---------- */
let ALL_AUTHORS = null;   // full slim author list, loaded once
const PAGE = 150;         // authors shown per "load more" step
let _list = null;         // current filtered list
let _shown = 0;           // how many of _list are rendered

/* Latin -> Greek transliteration (Beta Code-style core), pure JS.
   Lets users type Latin without a Greek keyboard and still match polytonic
   names: "mhnin" -> "μηνιν", which matches "μῆνιν" via accent-stripped search. */
const _GMAP = { a: "α", b: "β", g: "γ", d: "δ", e: "ε", z: "ζ", h: "η", q: "θ",
  i: "ι", k: "κ", l: "λ", m: "μ", n: "ν", x: "ξ", o: "ο", p: "π", r: "ρ",
  t: "τ", u: "υ", f: "φ", c: "χ", y: "ψ", w: "ω" };
function latinToGreek(s) {
  s = (s || "").toLowerCase();
  let out = "";
  for (let i = 0; i < s.length; i++) {
    const ch = s[i], next = s[i + 1];
    if (ch === "s") out += (next === undefined || !/[a-z]/.test(next)) ? "ς" : "σ";
    else if (_GMAP[ch]) out += _GMAP[ch];
    else out += ch;
  }
  return out;
}
// Accent-insensitive Greek for matching (NFD + drop combining marks; ς -> σ).
function stripGreek(s) {
  return (s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .replace(/ς/g, "σ").toLowerCase();
}

function _blob(a) {
  const greek = a.author_name_greek || "";
  return [a.author_name_latin, greek, a.author_name_english, a.epitheton, a.author_id,
          stripGreek(greek)]
    .filter(Boolean).join("  ").toLowerCase();
}
function filterAuthors(all, q) {
  q = (q || "").trim().toLowerCase();
  if (!q) return all.slice(); // sorted by id already
  // Build alternate queries: Latin->Greek, and accent-stripped forms, so that
  // "mhnin" / "menin" also matches the polytonic "μῆνιν".
  const qgreek = latinToGreek(q);
  const variants = Array.from(new Set([q, qgreek, stripGreek(q), stripGreek(qgreek)]));
  let m;
  if (/^\d{1,4}$/.test(q)) {
    const qid = q.padStart(4, "0");
    m = all.filter((a) => a.author_id === qid || a.author_id.startsWith(qid));
  } else {
    m = all.filter((a) => {
      const blob = _blob(a);
      return variants.some((v) => v && blob.includes(v));
    });
  }
  const sw = (s) => (s || "").toLowerCase().startsWith(q);
  m.sort((a, b) => {
    const ra = a.author_id.startsWith(q) ? 0 : 1;
    const rb = b.author_id.startsWith(q) ? 0 : 1;
    if (ra !== rb) return ra - rb;
    const na = sw(a.author_name_latin) || sw(a.author_name_english) ? 0 : 1;
    const nb = sw(b.author_name_latin) || sw(b.author_name_english) ? 0 : 1;
    return na - nb;
  });
  return m;
}
function renderResults(list, n) {
  const ul = document.getElementById("results");
  if (!n) { ul.innerHTML = `<li class="spinner">No results.</li>`; return; }
  ul.innerHTML = list.slice(0, n).map(renderResult).join("");
  attachResultClicks(ul);
  renderMore(list, n);
}
function renderMore(list, n) {
  const box = document.getElementById("more");
  if (!box) return;
  if (n < list.length) {
    box.hidden = false;
    box.innerHTML = `<button id="more-btn" class="more-btn">${n} / ${list.length} authors — Load more</button>`;
    document.getElementById("more-btn").addEventListener("click", () => {
      _shown += PAGE; renderResults(_list, _shown);
    });
  } else {
    box.hidden = true;
  }
}
async function renderHome() {
  $view().innerHTML = `
    <div class="search-wrap">
      <span class="search-icon">⌕</span>
      <input id="search" class="search-input" type="search" autocomplete="off"
        placeholder="Search by author (Latin / Greek), work, or TLG id — or jump directly: 4031.002">
    </div>
    <p class="search-hint" id="hint">e.g. “Homerus”, “Ὅμηρος”, “0012”. 🟢 green-marked works are readable. For an exact author+work (e.g. <b>4031.002</b>) it jumps straight to the work.</p>
    <div class="stats" id="stats"></div>
    <ul id="results" class="result-list"><li class="spinner">Loading…</li></ul>
    <div id="more"></div>`;
  const input = document.getElementById("search");
  let timer;
  const PRECISE = /^(\d{1,4})\.(\d{3})$/;
  const apply = (q) => {
    _list = filterAuthors(ALL_AUTHORS, q);
    _shown = PAGE;
    const cnt = document.getElementById("count");
    if (cnt) cnt.textContent =
      `${_list.length} authors${_list.length > PAGE ? " (first " + PAGE + " shown)" : ""}`;
    renderResults(_list, _shown);
  };
  input.addEventListener("input", () => {
    const v = input.value.trim();
    const m = v.match(PRECISE);             // exact AUTHOR.WORK -> jump straight to reader
    if (m) { location.hash = `/read/${m[1].padStart(4, "0")}/${m[2]}`; return; }
    clearTimeout(timer); timer = setTimeout(() => apply(v), 120);
  });
  if (!ALL_AUTHORS) {
    try { ALL_AUTHORS = await fetchJSON(API("/authors?q=&limit=100000")); }
    catch { document.getElementById("results").innerHTML =
      `<li class="spinner">Failed to load the canon.</li>`; return; }
  }
  // totals
  const totA = ALL_AUTHORS.length;
  const totW = ALL_AUTHORS.reduce((s, a) => s + (a.work_count || 0), 0);
  const totR = ALL_AUTHORS.reduce((s, a) => s + (a.readable_count || 0), 0);
  document.getElementById("stats").innerHTML =
    `Total: <b>${totA}</b> authors · <b>${totW}</b> works` +
    ` (<b>${totR}</b> readable) · <span id="count">—</span>`;
  apply("");
  setTimeout(() => input.focus(), 30);
}
function renderResult(a) {
  const gr = a.author_name_greek ? `<span class="name-greek">${esc(a.author_name_greek)}</span>`
    : `<span class="name-greek greek-empty"></span>`;
  const meta = [a.epitheton, a.era].filter(Boolean).map(esc).join(" · ");
  const read = a.readable_count || 0, tot = a.work_count || 0;
  return `<li class="result" data-aid="${esc(a.author_id)}">
    <span class="aid">${esc(a.author_id)}</span>
    <span>
      <span class="name-latin">${esc(a.author_name_latin || a.author_name_english || "—")}</span>${gr}
      <div class="meta">${meta || "—"}</div>
    </span>
    <span class="count"><span class="read">${read}</span> / ${tot} works</span>
  </li>`;
}
function attachResultClicks(list) {
  list.querySelectorAll(".result").forEach((el) =>
    el.addEventListener("click", () => { location.hash = "/author/" + el.dataset.aid; }));
}

/* ---------- author page ---------- */
async function renderAuthor(aid) {
  $view().innerHTML = `<div class="spinner">Loading…</div>`;
  try {
    const a = await fetchJSON(API("/author/" + aid));
    const gr = a.author_name_greek ? `<span class="gr">${esc(a.author_name_greek)}</span>` : "";
    const pills = [a.epitheton, a.era].filter(Boolean)
      .map((p) => `<span class="pill">${esc(p)}</span>`).join(" ");
    const works = a.works.map((w) => renderWork(w, aid)).join("");
    const readCount = a.works.filter((w) => w.readable).length;
    $view().innerHTML = `
      <a class="back-link" href="#/">← back to search</a>
      <div class="author-card">
        <h1 class="author-name">${esc(a.author_name_latin || a.author_name_english || aid)} ${gr}</h1>
        <div class="author-meta">${pills} <span class="author-id">TLG ${esc(aid)}</span></div>
      </div>
      <div class="section-head">${a.works.length} works · ${readCount} readable &nbsp; <span class="legend">🔥 = Flame comparison</span></div>
      <div class="works-grid">${works || '<p class="reader-empty">No open text is available for this author yet.</p>'}</div>`;
    $view().querySelectorAll(".work.readable").forEach((el) =>
      el.addEventListener("click", () => { location.hash = "/read/" + aid + "/" + el.dataset.wid; }));
    $view().querySelectorAll(".flame-btn").forEach((el) =>
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        location.hash = "/compare?first=" + el.dataset.first;
      }));
  } catch {
    $view().innerHTML = `<div class="reader-empty">Author not found (${esc(aid)}).</div>`;
  }
}
function renderWork(w, aid) {
  // All works are clickable; the reader resolves real text on open
  // (repo TEI, First1K CTS, or Perseus Hopper) — or shows sources if none.
  // `readable` (from the API) = cts_confirmed OR in the Perseus repo map OR cached.
  const readable = w.readable !== undefined ? !!w.readable
    : !!(w.cts_confirmed || w.has_local_text);
  const badge = readable ? "📖" : "📖?";
  const gr = w.title_greek ? `<span class="w-gr">${esc(w.title_greek)}</span>` : "";
  const title = w.title_latin || w.title_english || w.title_greek || "(untitled)";
  const urn = `<div class="w-urn">${esc(w.cts_urn)}</div>` +
    (w.edition ? `<div class="w-edition" title="Print edition (from the canon)"> ${esc(w.edition)}</div>` : "") +
    (readable ? "" : `<div class="w-no">no open text known yet (sources shown after opening)</div>`);
  return `<div class="work readable" data-wid="${esc(w.work_id)}">
    <span class="badge">${badge}</span>
    <span>
      <span class="w-title">${esc(title)}</span>${gr}
      ${urn}
    </span>
    <button class="flame-btn" title="Flame comparison with this work" data-first="${esc(aid)}.${esc(w.work_id)}">🔥</button>
  </div>`;
}

/* ---------- reader ---------- */
let readerState = null;
async function renderReader(aid, wid, idx) {
  $view().innerHTML = `<div class="spinner">Loading… the first text download may take a few seconds.</div>`;
  try {
    const meta = await fetchJSON(API(`/text/${aid}/${wid}/sections`));
    const author = (await fetchJSON(API("/author/" + aid)).catch(() => ({})));
    const w = (author.works || []).find((x) => x.work_id === wid) || {};
    const titleLat = w.title_latin || w.title_english || meta.title || `${aid}.${wid}`;
    const titleGr = w.title_greek ? `<span class="gr">${esc(w.title_greek)}</span>` : "";
    const nav = meta.has_text ? meta.sections.map((s) =>
      `<button class="nav-item" data-idx="${s.index}">
        ${esc(s.label)}<span class="nav-meta">${s.block_count}</span></button>`).join("") : "";
    const textArea = meta.has_text
      ? `<div id="text" class="greek-text"><div class="spinner">Loading…</div></div>`
      : `<div class="reader-empty">This work is not readable here yet — no downloadable open Greek text.<br>Other sources (archive.org, BSB, Google Books, Gallica, HathiTrust) are searchable under <b>Sources</b> above.</div>`;
    $view().innerHTML = `
      <a class="back-link" href="#/author/${aid}">← ${esc(author.author_name_latin || aid)}</a>
      <div class="reader">
        <aside class="reader-nav">
          <h4>${meta.has_text ? "Chapters" : ""}</h4>
          ${nav || ""}
        </aside>
        <section class="reader-pane">
          <h1 class="reader-title">${esc(titleLat)} ${titleGr}</h1>
          <div class="reader-sub">
            <span class="urn">${esc(w.cts_urn || "")}</span>
            ${(meta.edition || w.edition) ? `<div class="w-edition"> ${(esc(meta.edition || w.edition))}</div>` : ""}
          </div>
          <details class="sources"><summary id="src-sum">Discover sources…</summary>
            <div id="sources" class="src-list"><span class="spinner">Searching sources…</span></div>
          </details>
          ${textArea}
        </section>
      </div>`;
    loadSources(aid, wid);
    if (meta.has_text) {
      readerState = { aid, wid, sections: meta.sections };
      $view().querySelectorAll(".nav-item").forEach((b) =>
        b.addEventListener("click", () => loadSection(aid, wid, +b.dataset.idx)));
      const first = idx && meta.sections.some((s) => s.index === idx) ? idx : (meta.sections[0]?.index ?? 0);
      loadSection(aid, wid, first);
    }
  } catch (e) {
    $view().innerHTML = `<div class="reader-empty">Error: ${esc(e.message)}</div>`;
  }
}
function srcBadge(s) {
  if (s.type === "text" && s.kind === "confirmed") return "📖 text";
  if (s.type === "text") return "📖 text?";
  if (s.type === "metadata") return "🛈 metadata";
  if (s.type === "scan" && s.kind === "discovered") return "📷 scanned edition?";
  if (s.type === "scan") return "🔎 search";
  return "🔗";
}
async function loadSources(aid, wid) {
  const box = document.getElementById("sources");
  const sum = document.getElementById("src-sum");
  if (!box) return;
  try {
    const d = await fetchJSON(API(`/sources/${aid}/${wid}`));
    const items = d.sources.map((s) =>
      `<a class="src-link ${s.kind}" href="${esc(s.url)}" target="_blank" rel="noopener">
        <span class="src-badge">${srcBadge(s)}</span>
        <span class="src-body">
          <span class="src-label">${esc(s.label)}</span>
          <span class="src-detail">${esc(s.detail || "")}</span>
          <span class="src-kind">${s.kind === "confirmed" ? "confirmed" : s.kind === "discovered" ? "discovered (to verify)" : "search link"}</span>
        </span>
      </a>`).join("");
    box.innerHTML = items || `<span class="spinner">No sources.</span>`;
    if (sum) sum.textContent = `Sources (${d.sources.length})`;
  } catch {
    box.innerHTML = `<span class="spinner">Failed to fetch sources.</span>`;
  }
}
async function loadSection(aid, wid, idx) {
  const text = document.getElementById("text");
  if (!text) return;
  text.innerHTML = `<div class="spinner">Loading…</div>`;
  $view().querySelectorAll(".nav-item").forEach((b) =>
    b.classList.toggle("active", +b.dataset.idx === idx));
  try {
    const sec = await fetchJSON(API(`/text/${aid}/${wid}/section/${idx}`));
    text.innerHTML = sec.blocks.map(renderBlock).join("") || `<p class="reader-empty">(empty)</p>`;
    text.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    text.innerHTML = `<p class="reader-empty">Failed to load: ${esc(e.message)}</p>`;
  }
}
function renderBlock(b) {
  if (b.kind === "head") return `<div class="block-head">${esc(b.text)}</div>`;
  if (b.kind === "line") {
    const n = b.n != null ? `<span class="lnum">${esc(b.n)}</span>` : `<span class="lnum"></span>`;
    return `<div class="line">${n}<span class="ltext">${esc(b.text)}</span></div>`;
  }
  return `<p class="para">${esc(b.text)}</p>`;
}

/* ---------- Flame text-reuse comparison (#/compare) ---------- */
function _cmpSideHtml(tokens, matched, bridges) {
  if (!tokens || !tokens.length) return "";
  return tokens.map((tok, t) => {
    if (matched && matched[t] != null)
      return `<span class="cmp-hl highlight clickable" data-match-id="${matched[t]}">${esc(tok)}</span>`;
    if (bridges && bridges[t] != null)
      return `<span class="dynamic-bridge-word" data-fuzz="${bridges[t]}">${esc(tok)}</span>`;
    return esc(tok);
  }).join(" ");
}

function applyCmpFilters() {
  const cos = parseFloat(document.getElementById("slider-cos")?.value || 0);
  const fuzz = parseFloat(document.getElementById("slider-fuzz")?.value || 0);
  document.querySelectorAll(".cmp-pair").forEach((el) => {
    const score = parseFloat(el.dataset.score);
    el.style.display = score >= cos ? "" : "none";
  });
  document.querySelectorAll(".dynamic-bridge-word").forEach((el) => {
    const f = parseFloat(el.dataset.fuzz);
    el.classList.toggle("is-similar", f >= fuzz);
    el.classList.toggle("is-dissimilar", f < fuzz);
  });
  const cl = document.getElementById("cos-val"); if (cl) cl.textContent = cos.toFixed(2);
  const fl = document.getElementById("fuzz-val"); if (fl) fl.textContent = fuzz.toFixed(0);
}

/* Flame compare state + streaming accumulation, shared across renders. */
let _cmpState = { ngram: 4, n_out: 1, chain: 2, fuzz: 0.75 };
let _cmpLast = null;
let _cmpAbort = null;
let _cmpTotal = 0;
let _cmpRenderTimer = null;
const CMP_RENDER_CAP = 60;

/* Streaming compare — fires ONLY on button click; renders incrementally. */
async function runCompare() {
  const a = _cmpState.p1 && _cmpState.p1.value();
  const b = _cmpState.p2 && _cmpState.p2.value();
  if (!a || !b) { toast("Select both works (author + work)."); return; }
  const ma = a.match(/^(\d{1,4})\.(\d{3})$/), mb = b.match(/^(\d{1,4})\.(\d{3})$/);
  if (!ma || !mb) { toast("Invalid work id."); return; }
  const box = document.getElementById("cmp-results");
  if (!box) return;
  if (_cmpAbort) { try { _cmpAbort.abort(); } catch (e) {} }
  _cmpAbort = new AbortController();
  _cmpLast = { work1: null, work2: null, result: {
    pairs: [], ngram: _cmpState.ngram, n_out: _cmpState.n_out,
    min_chain_words: _cmpState.chain, fuzz_threshold: _cmpState.fuzz,
    mode: "", used_threshold: 0, threshold: 0, mean: 0, vocab_size: 0,
    n_pairs_total: 0, n_candidates: 0, n_pairs_shown: 0,
  } };
  _cmpTotal = 0;
  renderCmpShell();
  setCmpStatus("preparing… (tokenizing units, searching for candidates)", null, 0);
  const url = API(`/compare_stream?auth1=${ma[1].padStart(4,"0")}&work1=${ma[2]}&auth2=${mb[1].padStart(4,"0")}&work2=${mb[2]}` +
    `&ngram=${_cmpState.ngram}&n_out=${_cmpState.n_out}&chain=${_cmpState.chain}&fuzz=${_cmpState.fuzz}`);
  try {
    const resp = await fetch(url, { signal: _cmpAbort.signal });
    if (!resp.ok || !resp.body) {
      let msg = "HTTP " + resp.status;
      try { const j = await resp.json(); if (j.error) msg = j.error; } catch (e) {}
      box.innerHTML = `<div class="reader-empty">Error: ${esc(String(msg))}</div>`;
      return;
    }
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, nl).trim();
        buf = buf.slice(nl + 1);
        if (line) { try { handleCmpEvent(JSON.parse(line)); } catch (e) {} }
      }
    }
    const tail = buf.trim();
    if (tail) { try { handleCmpEvent(JSON.parse(tail)); } catch (e) {} }
  } catch (e) {
    if (e && e.name === "AbortError") return;
    box.innerHTML = `<div class="reader-empty">Error: ${esc(e.message || String(e))}</div>`;
  }
}

function handleCmpEvent(ev) {
  if (!ev || !ev.t) return;
  if (ev.t === "head") {
    _cmpLast.work1 = ev.work1; _cmpLast.work2 = ev.work2;
  } else if (ev.t === "meta") {
    Object.assign(_cmpLast.result, {
      mode: ev.mode, used_threshold: ev.used_threshold, threshold: ev.threshold,
      mean: ev.mean, vocab_size: ev.vocab_size, n_pairs_total: ev.n_pairs_total,
      n_candidates: ev.n_candidates, ngram: ev.ngram, n_out: ev.n_out,
      min_chain_words: ev.min_chain_words, fuzz_threshold: ev.fuzz_threshold,
    });
    _cmpTotal = ev.n_chosen || ev.n_candidates || 0;
    const info = document.querySelector(".cmp-info");
    if (info) info.innerHTML = _cmpInfoHtml();
    setCmpStatus("searching for matches…", 0, 0);
  } else if (ev.t === "pair") {
    _cmpLast.result.pairs.push(ev.pair);
    scheduleCmpPairs();
    setCmpStatus(null, null, _cmpLast.result.pairs.length);
  } else if (ev.t === "progress") {
    const frac = ev.total ? ev.done / ev.total : null;
    setCmpStatus(null, frac, ev.found);
  } else if (ev.t === "done") {
    _cmpLast.result.n_pairs_shown = _cmpLast.result.pairs.length;
    renderCmpPairs();
    setCmpDone(ev.found != null ? ev.found : _cmpLast.result.pairs.length);
  } else if (ev.t === "error") {
    toast("Computation error: " + (ev.error || "?"));
    setCmpDone(_cmpLast.result.pairs.length);
  }
}

function _cmpInfoHtml() {
  const r = _cmpLast.result;
  return `Mode: <b class="cmp-mode">${esc(r.mode || "streaming")}</b> · ` +
    `Threshold (direct): <b>${r.used_threshold}</b> <span class="muted">(auto ${r.threshold} disabled)</span> · ` +
    `candidates: ${r.n_candidates} / ${Number(r.n_pairs_total || 0).toLocaleString()} pairs · mean: ${r.mean} · ` +
    `n-gram: ${r.ngram} (n_out=${r.n_out}, min chain=${r.min_chain_words}) · ` +
    `fuzzy threshold: ${r.fuzz_threshold} · vocab: ${r.vocab_size}`;
}

/* Build the static shell once: info, progress bar, button-gated controls,
   and an empty pairs container that streamed matches render into. */
function renderCmpShell() {
  const box = document.getElementById("cmp-results");
  if (!box) return;
  const st = _cmpState;
  box.innerHTML = `
    <div class="cmp-info">${_cmpInfoHtml()}</div>
    <div class="cmp-progress" id="cmp-progress">
      <span class="cmp-hourglass" aria-hidden="true">⏳</span>
      <div class="cmp-bar"><div class="cmp-bar-fill" id="cmp-bar-fill"></div></div>
      <span class="cmp-status" id="cmp-status">preparing…</span>
    </div>
    <div class="cmp-controls">
      <label>Cosine threshold: <input type="range" id="slider-cos" min="0" max="1" step="0.01" value="0"><span id="cos-val" class="slider-val"></span></label>
      <label>Fuzzy bridge threshold: <input type="range" id="slider-fuzz" min="0" max="100" step="1" value="60"><span id="fuzz-val" class="slider-val"></span></label>
      <label class="live">N-gram (word): <input type="range" id="slider-ng" min="3" max="8" step="1" value="${st.ngram}"><span id="ng-val" class="slider-val">${st.ngram}</span></label>
      <label class="live">Skip (n_out): <input type="range" id="slider-no" min="0" max="2" step="1" value="${st.n_out}"><span id="no-val" class="slider-val">${st.n_out}</span></label>
      <label class="live">Min. chain (word): <input type="range" id="slider-ch" min="2" max="10" step="1" value="${st.chain}"><span id="ch-val" class="slider-val">${st.chain}</span></label>
      <label class="live">Fuzzy threshold (Levenshtein): <input type="range" id="slider-fz" min="0.50" max="1.00" step="0.01" value="${st.fuzz}"><span id="fz-val" class="slider-val">${Number(st.fuzz).toFixed(2)}</span></label>
      <button id="cmp-recompute" class="more-btn cmp-recompute" title="Recompute with the set n-gram / n_out / min-chain / fuzzy values">↻ Recompute</button>
      <button id="cmp-export" class="more-btn" title="Download the current result list (TSV)">⤓ Export results</button>
    </div>
    <div class="cmp-note" id="cmp-note">After changing the server-side sliders (n-gram, n_out, min-chain, fuzzy), click the <b>↻ Recompute</b> button — you can adjust several settings in one pass. The cosine and bridge filters apply live.</div>
    <div class="cmp-pairs" id="cmp-pairs"></div>`;

  document.getElementById("slider-cos").addEventListener("input", applyCmpFilters);
  document.getElementById("slider-fuzz").addEventListener("input", applyCmpFilters);
  document.getElementById("cmp-export").addEventListener("click", exportCmpResults);

  const recompute = document.getElementById("cmp-recompute");
  const onLive = () => {
    _cmpState.ngram = +document.getElementById("slider-ng").value;
    _cmpState.n_out = +document.getElementById("slider-no").value;
    _cmpState.chain = +document.getElementById("slider-ch").value;
    _cmpState.fuzz = +document.getElementById("slider-fz").value;
    document.getElementById("ng-val").textContent = _cmpState.ngram;
    document.getElementById("no-val").textContent = _cmpState.n_out;
    document.getElementById("ch-val").textContent = _cmpState.chain;
    document.getElementById("fz-val").textContent = _cmpState.fuzz.toFixed(2);
    recompute.classList.add("is-dirty");           // mark pending; do NOT recompute
  };
  ["slider-ng", "slider-no", "slider-ch", "slider-fz"].forEach((id) =>
    document.getElementById(id).addEventListener("input", onLive));
  recompute.addEventListener("click", () => {
    recompute.classList.remove("is-dirty");
    runCompare();
  });

  applyCmpFilters();
}

function scheduleCmpPairs() {
  if (_cmpRenderTimer) return;
  _cmpRenderTimer = setTimeout(() => { _cmpRenderTimer = null; renderCmpPairs(); }, 150);
}

/* Re-render ONLY the pairs container from the accumulated, sorted pairs. */
function renderCmpPairs() {
  const host = document.getElementById("cmp-pairs");
  if (!host || !_cmpLast) return;
  const all = _cmpLast.result.pairs;
  const shown = all.slice().sort((a, b) => b.chain_len - a.chain_len).slice(0, CMP_RENDER_CAP);
  const d = _cmpLast;
  const t1 = (d.work1 && d.work1.title) || "1";
  const t2 = (d.work2 && d.work2.title) || "2";
  host.innerHTML = shown.map((p) => `
    <div class="cmp-pair" data-score="${p.score}">
      <div class="cmp-pair-head">
        <span class="cmp-score">cos ${p.score}</span>
        <span class="cmp-pair-sec">${esc(p.label_i)} ↔ ${esc(p.label_j)}</span>
        <span class="cmp-pair-cnt">${p.n_blocks} blocks → ${p.n_chained} chained bands · ${p.matched_words} words · chain ${p.chain_len}</span>
      </div>
      <div class="cmp-cols">
        <div class="cmp-col"><div class="cmp-col-title">${esc(t1)} · ${esc(p.label_i)}</div>
          <div class="cmp-text">${_cmpSideHtml(p.tokens_i, p.matched_i, p.bridges_i)}</div></div>
        <div class="cmp-col"><div class="cmp-col-title">${esc(t2)} · ${esc(p.label_j)}</div>
          <div class="cmp-text">${_cmpSideHtml(p.tokens_j, p.matched_j, p.bridges_j)}</div></div>
      </div>
    </div>`).join("") || '<p class="reader-empty">No matches to show yet…</p>';

  const note = document.getElementById("cmp-note");
  if (note) note.innerHTML = `Shown: ${shown.length}/${all.length} pairs (best chains) — <b>all</b> ${all.length} pairs are in the export (⤓). After a server-side slider: <b>↻ Recompute</b>.`;
  const info = document.querySelector(".cmp-info");
  if (info) info.innerHTML = _cmpInfoHtml();

  host.querySelectorAll(".cmp-hl").forEach((el) => {
    el.addEventListener("click", () => {
      const id = el.dataset.matchId;
      const pair = el.closest(".cmp-pair");
      pair.querySelectorAll(".cmp-hl").forEach((x) =>
        x.classList.toggle("cmp-active", x.dataset.matchId === id));
      const myCol = el.closest(".cmp-col");
      const other = [...pair.querySelectorAll(".cmp-col")].find((c) => c !== myCol);
      const target = other && other.querySelector(`[data-match-id="${CSS.escape(id)}"]`);
      if (target) target.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  });
  applyCmpFilters();
}

/* Progress UI: status text + determinate bar + count. frac=null => indeterminate. */
function setCmpStatus(text, frac, found) {
  const fill = document.getElementById("cmp-bar-fill");
  const status = document.getElementById("cmp-status");
  const prog = document.getElementById("cmp-progress");
  if (prog) prog.classList.remove("is-done");
  if (fill) {
    if (frac == null) { fill.classList.add("indeterminate"); }
    else { fill.classList.remove("indeterminate"); fill.style.width = Math.round(frac * 100) + "%"; }
  }
  if (status) {
    const parts = [];
    if (text) parts.push(text);
    if (found != null) parts.push(`${found} results`);
    if (frac != null) parts.push(`${Math.round(frac * 100)}%`);
    status.textContent = parts.join(" · ") || "…";
  }
}

function setCmpDone(found) {
  const fill = document.getElementById("cmp-bar-fill");
  const status = document.getElementById("cmp-status");
  const prog = document.getElementById("cmp-progress");
  if (fill) { fill.classList.remove("indeterminate"); fill.style.width = "100%"; }
  if (prog) prog.classList.add("is-done");
  if (status) status.textContent = `done · ${found} results`;
}

/* Export the accumulated results as TSV (academic metadata) — client-side Blob. */
function exportCmpResults() {
  if (!_cmpLast || !_cmpLast.result || !_cmpLast.result.pairs.length) { toast("No results to export yet."); return; }
  const d = _cmpLast, r = d.result;
  const w1 = (d.work1 && d.work1.meta) || {}, w2 = (d.work2 && d.work2.meta) || {};
  const head = [
    "source1_author_id", "source1_author_latin", "source1_author_greek", "source1_urn",
    "source1_work_title_latin", "source1_work_title_greek", "source1_edition",
    "source1_section", "source1_word_range", "source1_chapter",
    "source2_author_id", "source2_author_latin", "source2_author_greek", "source2_urn",
    "source2_work_title_latin", "source2_work_title_greek", "source2_edition",
    "source2_section", "source2_word_range", "source2_chapter",
    "cosine", "matched_words", "chain_len", "n_blocks", "n_chained",
    "excerpt_1", "excerpt_2"
  ];
  const row = (p) => [
    w1.author_id, w1.author_latin, w1.author_greek, w1.cts_urn,
    w1.title_latin, w1.title_greek, w1.edition,
    p.label_i, p.word_range_i, (p.tokens_i || []).join(" "),
    w2.author_id, w2.author_latin, w2.author_greek, w2.cts_urn,
    w2.title_latin, w2.title_greek, w2.edition,
    p.label_j, p.word_range_j, (p.tokens_j || []).join(" "),
    p.score, p.matched_words, p.chain_len, p.n_blocks, p.n_chained,
    p.snippet_i, p.snippet_j
  ].map((x) => (x == null ? "" : String(x)).replace(/\t/g, " ")).join("\t");
  const lines = [head.join("\t")];
  r.pairs.slice().sort((a, b) => b.chain_len - a.chain_len).forEach((p) => lines.push(row(p)));
  const blob = new Blob(["# KONI Flame — Result list (TSV)\n",
    "# n-gram=" + r.ngram + "  n_out=" + r.n_out + "  min_chain=" + r.min_chain_words
    + "  fuzz_threshold=" + r.fuzz_threshold
    + "  mode=" + r.mode + "  threshold=" + r.used_threshold + " (auto " + r.threshold + " disabled)\n#\n",
    lines.join("\n")], { type: "text/tab-separated-values;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  const f1 = (d.work1 && d.work1.aid) || "x", g1 = (d.work1 && d.work1.wid) || "x";
  const f2 = (d.work2 && d.work2.aid) || "x", g2 = (d.work2 && d.work2.wid) || "x";
  a.download = `koni_flame_${f1}.${g1}_vs_${f2}.${g2}.tsv`;
  document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  toast(`${r.pairs.length} rows exported (TSV).`);
}

/* Reusable author+work picker (autocomplete) for the Flame compare view. */
function makePicker(root, placeholder) {
  root.innerHTML = `
    <input class="picker-author" type="text" autocomplete="off" placeholder="${esc(placeholder)}">
    <div class="picker-suggest"></div>
    <select class="picker-work" disabled><option>-- select an author first --</option></select>`;
  const inp = root.querySelector(".picker-author");
  const sug = root.querySelector(".picker-suggest");
  const sel = root.querySelector(".picker-work");
  const state = { aid: null, wid: null, authorName: "" };
  let timer;
  inp.addEventListener("input", () => {
    state.aid = null; state.wid = null;
    clearTimeout(timer);
    const v = inp.value.trim();
    if (!v) { sug.innerHTML = ""; sug.style.display = "none"; return; }
    timer = setTimeout(() => {
      const res = filterAuthors(ALL_AUTHORS || [], v).slice(0, 8);
      if (!res.length) { sug.innerHTML = `<div class="picker-opt">No results</div>`; sug.style.display = "block"; return; }
      sug.innerHTML = res.map((a) =>
        `<div class="picker-opt" data-aid="${esc(a.author_id)}">
           <b>${esc(a.author_name_latin || a.author_name_english || a.author_id)}</b>
           <span class="picker-gr">${esc(a.author_name_greek || "")}</span>
           <span class="picker-id">${esc(a.author_id)}</span></div>`).join("");
      sug.style.display = "block";
      sug.querySelectorAll(".picker-opt[data-aid]").forEach((el) =>
        el.addEventListener("click", () => selectAuthor(el.dataset.aid)));
    }, 120);
  });
  inp.addEventListener("blur", () => setTimeout(() => { sug.style.display = "none"; }, 150));
  async function selectAuthor(aid) {
    if (!ALL_AUTHORS) ALL_AUTHORS = await fetchJSON(API("/authors?q=&limit=100000"));
    const a = ALL_AUTHORS.find((x) => x.author_id === aid);
    state.aid = aid; state.wid = null;
    state.authorName = a ? (a.author_name_latin || a.author_name_english || aid) : aid;
    inp.value = state.authorName + "  [" + aid + "]";
    sug.innerHTML = ""; sug.style.display = "none";
    sel.disabled = true;
    sel.innerHTML = `<option>-- loading works… --</option>`;
    try {
      const ad = await fetchJSON(API("/author/" + aid));
      const works = ad.works || [];
      sel.innerHTML = (works.length ? works : []).map((w) =>
        `<option value="${esc(w.work_id)}">${esc(w.work_id)} · ${esc(w.title_latin || w.title_english || w.title_greek || "(untitled)")}${w.readable ? "" : " (not readable)"}</option>`).join("")
        || `<option value="">-- no works --</option>`;
      sel.disabled = !works.length;
      if (works.length) { state.wid = works[0].work_id; sel.value = state.wid; }
    } catch { sel.innerHTML = `<option>-- error --</option>`; }
  }
  sel.addEventListener("change", () => { state.wid = sel.value; });
  return {
    state,
    selectAuthor,
    value: () => (state.aid && state.wid) ? `${state.aid}.${state.wid}` : null,
    setWork: (wid) => { if (wid && !sel.disabled) { state.wid = wid; sel.value = wid; } },
  };
}

async function renderCompare(q) {
  q = q || {};
  $view().innerHTML = `
    <h1 class="page-title">Flame · text reuse</h1>
    <p class="page-intro">Pick two works from the canon using the searchable dropdowns. The pure-Python Flame engine
    (Phase 1: BPE subword + leave-n-out rolling hash + TF-IDF cosine ranking;
    Phase 2: <code>Levenshtein</code>-tolerant word-block matching) compares the chapters of the two works.
    A work compared with itself gives cos=1.0; the sliders recompute in the background in real time.</p>
    <div class="cmp-pickers">
      <div class="picker" id="picker1"></div>
      <div class="picker" id="picker2"></div>
    </div>
    <div class="cmp-form"><button id="cmp-go" class="more-btn">Compare</button></div>
    <div id="cmp-results"></div>`;
  if (!ALL_AUTHORS) {
    try { ALL_AUTHORS = await fetchJSON(API("/authors?q=&limit=100000")); }
    catch { /* will be lazily loaded by picker */ }
  }
  const p1 = makePicker(document.getElementById("picker1"), "1. search author (e.g. Procopius, 4029, Ὅμηρος)");
  const p2 = makePicker(document.getElementById("picker2"), "2. search author");
  _cmpState = { p1, p2, ngram: 4, n_out: 1, chain: 2, fuzz: 0.75 };
  // Pre-fill from ?first=AID.WORK (e.g. a Flame button on the author page).
  if (q.first) {
    const m = q.first.match(/^(\d{1,4})\.(\d{3})$/);
    if (m) { p1.selectAuthor(m[1].padStart(4, "0")).then(() => p1.setWork(m[2])); }
  }
  document.getElementById("cmp-go").addEventListener("click", runCompare);
}

/* ---------- wire up ---------- */
window.addEventListener("hashchange", route);
document.getElementById("font-inc").addEventListener("click", () => changeSize(+1));
document.getElementById("font-dec").addEventListener("click", () => changeSize(-1));
document.getElementById("lh-toggle").addEventListener("click", cycleLineHeight);
document.getElementById("theme-toggle").addEventListener("click", toggleTheme);
applySettings();
route();