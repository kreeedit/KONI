const esc = (s) => String(s);

function _lemmaHtml(d, opts) {
  const r = d.result, w1 = d.work1, w2 = d.work2;
  const rows = r.rows || [];
  const acc = (r.rules && r.rules.accuracy) || null;
  const per1k = (n, total) => total ? (1000 * n / total) : 0;
  const head = `
    <div class="cmp-info">
      <b>${esc(w1.title || w1.aid)}</b> <span class="muted">(A, ${r.n_a.toLocaleString()} words)</span>
      &nbsp;→&nbsp;
      <b>${esc(w2.title || w2.aid)}</b> <span class="muted">(B, ${r.n_b.toLocaleString()} words)</span>
      <br><span class="muted">${r.n_forms.toLocaleString()} surface forms collapsed to
      ${r.n_lemmas.toLocaleString()} lemmas${r.compression ? ` (×${r.compression})` : ""}${opts && opts.dropProper
        ? " · proper nouns removed" : ""} · pooling: ${(r.params.variants || []).join(", ") || "off"}</span>
      ${(r.n_elided_a || r.n_elided_b) ? `<br><span class="muted">elision fragments excluded from the counts: ${r.n_elided_a.toLocaleString()} in A, ${r.n_elided_b.toLocaleString()} in B</span>` : ""}
      ${r.n_candidates > rows.length ? `<br><span class="warn">showing ${rows.length} of ${r.n_candidates.toLocaleString()} lemmas</span>` : ""}
      ${acc ? `<br><span class="warn">This column is produced by a rule table, not a
        lexicon. Measured against ${esc(acc.gold)}: ${(100 * acc.thucydides.exact).toFixed(1)}% of
        tokens get the gold headword exactly and ${(100 * acc.thucydides.within).toFixed(1)}% have it
        among the readings offered. Aggregation is what it is for — ${(100 * acc.thucydides.purity_noun).toFixed(0)}%
        of NOUNS and ${(100 * acc.thucydides.purity_verb).toFixed(0)}% of verbs keep all their forms under one
        key; the rest are irregular verb stems no suffix rule can undo. Read a
        single row as a candidate, not as a citation.</span>` : ""}
    </div>`;
  if (!rows.length) {
    return head + `<div class="reader-empty">No lemmas in common at these settings.</div>`;
  }
  /* The forms are the row. Sorted by the token count, they show at a glance
     whether the headword is the lexeme's real centre of gravity or whether the
     count is carried by one oblique case — which is exactly the thing that a
     surface-form table cannot show and this one exists to show. A form whose
     reading was ambiguous lists its rival readings, because that is the part of
     the row that is a judgement rather than a count. */
  const breakdown = (x) => `
    <tr class="lemma-forms" hidden><td colspan="7">
      <div class="arch-vsplit">${x.forms.map((f) => `
        <div><span class="arch-word" data-arch-word="${esc(f.form)}"
          title="click for the occurrences of this form">${esc(f.display)}</span>
          <span class="muted">${esc(f.pos)}${f.infl ? " · " + esc(f.infl) : ""}${
            f.source ? " · " + esc(f.source) : ""}${f.rule && f.rule !== f.source ? " · " + esc(f.rule) : ""}</span>
          <b>${f.count_a} / ${f.count_b}</b>${
            f.ambiguous ? `<span class="warn"> · ambiguous: ${
              f.readings.map((y) => esc(y.lemma)).join(", ")}</span>` : ""}</div>`).join("")}
      </div></td></tr>`;
  const body = rows.map((x) => `
    <tr class="lemma-row" data-lemma-toggle="${esc(x.key)}">
      <td class="arch-word">${esc(x.lemma)} <span class="muted">▸</span>${
        x.pos && x.pos.length ? `<span class="muted"> ${esc(x.pos[0])}</span>` : ""}</td>
      <td class="num">${x.count_a.toLocaleString()}</td>
      <td class="num">${per1k(x.count_a, r.n_a).toFixed(2)}</td>
      <td class="num">${x.count_b.toLocaleString()}</td>
      <td class="num">${per1k(x.count_b, r.n_b).toFixed(2)}</td>
      <td class="num muted" title="distinct surface forms in A / in B">${x.n_forms_a} / ${x.n_forms_b}</td>
      <td class="muted">${x.n_ambiguous_a + x.n_ambiguous_b ? `<span class="warn"
        title="tokens whose reading is separated from another only by accent or by syntax">${(x.n_ambiguous_a + x.n_ambiguous_b).toLocaleString()} amb.</span>` : ""}${
        x.n_unreduced_a + x.n_unreduced_b ? ` <span class="muted">${(x.n_unreduced_a + x.n_unreduced_b).toLocaleString()} unanalysed</span>` : ""}</td>
    </tr>${breakdown(x)}`).join("");
  return head + `
    <table class="arch-table">
      <thead><tr>
        <th>lemma</th>
        <th class="num" title="occurrences in the earlier work">A ×</th>
        <th class="num" title="per 1000 words in the earlier work">A /1000</th>
        <th class="num" title="occurrences in the younger work">B ×</th>
        <th class="num" title="per 1000 words in the younger work">B /1000</th>
        <th class="num" title="how many different spellings the count is spread over">forms A / B</th>
        <th></th>
      </tr></thead>
      <tbody>${body}</tbody>
    </table>
    <div id="arch-evidence" class="arch-evidence"></div>
    <div class="cmp-info"><span class="muted">Rows are ranked by the combined
    count, not by the collapse score — attaching a score to a lemma means
    re-running the rarity model on the lemma-keyed counts, which is a separate
    claim and should be made as one.</span></div>`;
}

const d = JSON.parse(require('fs').readFileSync('/home/tamask/github/KONI/.claude-isolated-config/jobs/88b99e67/tmp/lem.json','utf8'));
const h = _lemmaHtml(d, {dropProper:true});
console.log('OK len', h.length);
console.log(h.slice(0, 600));
