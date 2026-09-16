"""Render a validation report as a page a person can actually review.

    python -m atlas.pipeline.build.report_html atlas/results/phase2/validation_report.json
    python -m atlas.pipeline.build.report_html <report.json> --artifact out.html

Writes <report>.html beside the JSON (a standalone document), or with
--artifact an Artifact-ready fragment with no document skeleton. Standard
library only, so it runs anywhere the pipeline does.

The face-validity rows are the point: §11 requires them reviewed by hand each
build, and this is the surface for doing that.
"""
from __future__ import annotations

import html
import json
import sys
from datetime import date
from pathlib import Path

FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
         'family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400'
         '&family=Public+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;600'
         '&display=swap">')

CSS = """
:root{
  --paper:#fbfbfc; --raised:#ffffff; --ink:#171a20; --ink-2:#4a515e;
  --ink-3:#737b8a; --rule:#dfe2e8; --rule-2:#eceef2;
  --accent:#2f5d8a; --pass:#3f7a52; --warn:#8a6a1f; --crit:#9a3d3d;
  --chip:#eef1f6;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#14161a; --raised:#1a1d23; --ink:#e8eaee; --ink-2:#a8b0bd;
    --ink-3:#7b8494; --rule:#2a2e36; --rule-2:#22262d;
    --accent:#7fa9d4; --pass:#6ba57e; --warn:#c2a04f; --crit:#cf8080;
    --chip:#23272f;
  }
}
:root[data-theme="dark"]{
  --paper:#14161a; --raised:#1a1d23; --ink:#e8eaee; --ink-2:#a8b0bd;
  --ink-3:#7b8494; --rule:#2a2e36; --rule-2:#22262d;
  --accent:#7fa9d4; --pass:#6ba57e; --warn:#c2a04f; --crit:#cf8080;
  --chip:#23272f;
}
*{box-sizing:border-box}
body{background:var(--paper); color:var(--ink);
  font-family:"Public Sans",system-ui,-apple-system,sans-serif;
  font-size:15px; line-height:1.55; margin:0; padding-inline:20px;
  padding-block:0; -webkit-font-smoothing:antialiased}
.wrap{max-width:920px; margin:0 auto; padding-block:44px 72px;
  display:flex; flex-direction:column; gap:40px}
h1,h2,h3{font-family:Newsreader,Georgia,serif; font-weight:600;
  text-wrap:balance; margin:0; letter-spacing:-0.01em}
h1{font-size:2.1rem; line-height:1.15}
h2{font-size:1.35rem}
h3{font-size:1rem; font-family:"Public Sans",sans-serif; font-weight:600}
p{margin:0}
a{color:var(--accent)}
.eyebrow{font-size:.7rem; letter-spacing:.12em; text-transform:uppercase;
  color:var(--ink-3); font-weight:600}
.lede{color:var(--ink-2); max-width:62ch}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace;
  font-variant-numeric:tabular-nums}
header .meta{display:flex; flex-wrap:wrap; gap:6px 22px; margin-top:14px;
  font-size:.82rem; color:var(--ink-2)}
header .meta b{color:var(--ink); font-weight:600}
section{display:flex; flex-direction:column; gap:16px}
.verdict{display:flex; align-items:baseline; gap:12px; padding:14px 18px;
  border-left:3px solid var(--pass); background:var(--chip);
  font-size:.95rem}
.verdict.bad{border-left-color:var(--crit)}
.gates{display:flex; flex-direction:column; border-top:1px solid var(--rule)}
.gate{display:grid; grid-template-columns:150px 1fr auto; gap:4px 18px;
  padding:14px 0 14px 14px; border-bottom:1px solid var(--rule-2);
  border-left:3px solid var(--pass); align-items:baseline}
.gate .name{font-weight:600}
.gate .detail{color:var(--ink-2); font-size:.88rem}
.gate .stat{font-size:.8rem; letter-spacing:.06em; text-transform:uppercase;
  color:var(--pass); font-weight:600}
table{border-collapse:collapse; width:100%; font-size:.88rem}
th,td{text-align:left; padding:7px 12px 7px 0; border-bottom:1px solid var(--rule-2)}
th{font-size:.72rem; letter-spacing:.1em; text-transform:uppercase;
  color:var(--ink-3); font-weight:600}
td.num{text-align:right; padding-right:0}
.scroller{overflow-x:auto}
.note{font-size:.85rem; color:var(--ink-2); max-width:66ch}
.persona{margin-top:26px; padding-bottom:6px; border-bottom:1px solid var(--rule);
  display:flex; align-items:baseline; justify-content:space-between; gap:12px}
.persona .key{font-size:.8rem; color:var(--ink-3)}
.row{display:grid; grid-template-columns:64px 1fr; gap:0 18px;
  padding:16px 0; border-bottom:1px solid var(--rule-2)}
.row .gutter{display:flex; flex-direction:column; gap:2px}
.rank{font-family:Newsreader,Georgia,serif; font-size:1.5rem; line-height:1}
.gutter .sub{font-size:.72rem; color:var(--ink-3)}
.expl{display:flex; flex-direction:column; gap:3px}
.expl div:first-child{font-weight:600}
.expl div{color:var(--ink-2)}
.expl div:first-child{color:var(--ink)}
.chips{display:flex; flex-wrap:wrap; gap:6px; margin-top:8px}
.chip{font-size:.72rem; padding:2px 8px; border-radius:2px;
  background:var(--chip); color:var(--ink-2)}
.chip.warn{color:var(--warn); box-shadow:inset 0 0 0 1px currentColor}
.controls{display:flex; flex-wrap:wrap; gap:8px; margin-top:12px;
  align-items:center}
button{font:inherit; font-size:.82rem; padding:5px 12px; cursor:pointer;
  background:var(--raised); color:var(--ink-2);
  border:1px solid var(--rule); border-radius:2px}
button:hover{border-color:var(--ink-3)}
button[aria-pressed="true"]{background:var(--ink); color:var(--paper);
  border-color:var(--ink)}
button.flag[aria-pressed="true"]{background:var(--crit); border-color:var(--crit);
  color:#fff}
:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
input[type=text]{font:inherit; font-size:.85rem; flex:1 1 260px; min-width:0;
  padding:5px 9px; background:var(--raised); color:var(--ink);
  border:1px solid var(--rule); border-radius:2px}
.bar{position:sticky; top:0; z-index:5; background:var(--paper);
  border-bottom:1px solid var(--rule); padding:10px 0; margin-bottom:-8px;
  display:flex; flex-wrap:wrap; gap:12px; align-items:center;
  justify-content:space-between; font-size:.85rem}
.bar .count{color:var(--ink-2)}
footer{border-top:1px solid var(--rule); padding-top:20px;
  font-size:.85rem; color:var(--ink-2); display:flex;
  flex-direction:column; gap:10px}
@media (max-width:560px){
  .gate{grid-template-columns:1fr; padding-left:12px}
  .row{grid-template-columns:44px 1fr; gap:0 12px}
  h1{font-size:1.7rem}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""


def esc(x) -> str:
    return html.escape(str(x))


def pct(x, nd=1) -> str:
    return f"{x * 100:.{nd}f}%"


def gate_row(name, stat, ok, detail) -> str:
    cls = "gate" if ok else "gate bad"
    style = "" if ok else ' style="border-left-color:var(--crit)"'
    color = "var(--pass)" if ok else "var(--crit)"
    return (f'<div class="{cls}"{style}><div class="name">{esc(name)}</div>'
            f'<div class="detail">{detail}</div>'
            f'<div class="stat" style="color:{color}">{esc(stat)}</div></div>')


def build_inner(rep: dict) -> str:
    hard, soft = rep["hard"], rep["soft"]
    ic = hard["interval_calibration"]
    rs = hard["rank_stability"]
    aa = hard["adversarial_artifacts"]
    ws = soft["weight_sensitivity"]
    ec = soft["external_correlation"]
    fv = soft["face_validity"]
    rows = fv["rows"]
    failures = rep.get("hard_failures") or []

    shares = {k: v["share_replicates_with_>=8of10_overlap"]
              for k, v in rs["per_persona"].items()
              if "share_replicates_with_>=8of10_overlap" in v}
    skipped = {k: v["skipped"] for k, v in rs["per_persona"].items()
               if "skipped" in v}
    taus = ws["kendall_tau"]
    gen = rep.get("generated_by", {})
    stamp = ""
    if gen:
        sha = str(gen.get("git_sha", ""))[:10]
        dirty = " (dirty tree)" if gen.get("git_dirty") else ""
        stamp = (f'<span>generated by <b class="mono">{esc(sha)}{dirty}</b> '
                 f'at {esc(gen.get("generated_at", "?"))}</span>')

    out = ['<div class="wrap">']

    # Header
    out.append(f"""<header>
<p class="eyebrow">Dating Stats Atlas · validation</p>
<h1>Face-Validity Review</h1>
<p class="lede">Every result has to be explainable from its own attribution.
Automated gates check that the build still does what it did yesterday; this
page is the check on whether the answers are <em>plausible</em>. That part
only a person can do.</p>
<div class="meta"><span>build <b class="mono">{esc(rep['build'])}</b></span>
<span>model <b class="mono">{esc(rep['model_version'])}</b></span>
<span>rows to review <b>{len(rows)}</b></span>
<span>rendered {date.today().isoformat()}</span>{stamp}</div>
</header>""")

    # Verdict
    if failures:
        out.append('<div class="verdict bad"><b>Hard gate failure</b>'
                   f'<span>{esc(", ".join(map(str, failures)))}</span></div>')
    else:
        n_gates = len(hard)
        out.append(f'<div class="verdict"><b>All {n_gates} hard gates pass.</b>'
                   '<span>Nothing blocks the build; the soft checks and the '
                   'rows below are the judgment calls.</span></div>')

    # Hard gates
    g = []
    g.append(gate_row(
        "Intervals", "pass" if ic["pass"] else "fail", ic["pass"],
        f'Served margin covers the true margin on <b>{pct(ic["coverage"], 1)}</b> '
        f'of held-out points (gate ≥ {pct(ic["gates"]["coverage_min"], 0)}), '
        f'overstating it by <b>{pct(ic["median_overstatement"])}</b> at the median '
        f'(gate ≤ {pct(ic["gates"]["median_overstatement_max"], 0)}), '
        f'{pct(ic["p90_overstatement"])} at p90. '
        f'Mechanism: {esc(ic["mechanism"])}.'))
    g.append(gate_row(
        "Suppression", "pass" if hard["suppression_reasons_and_intervals"]["pass"]
        else "fail", hard["suppression_reasons_and_intervals"]["pass"],
        "The 12 pinned golden vectors reproduce exact rankings, scores, pools, "
        "served margins and suppression sets; only the n-only reason strings "
        "may appear (ADR 0002) and the middle tier never fires."))
    if "cube_vs_sql_differential" in hard:
        d = hard["cube_vs_sql_differential"]
        g.append(gate_row(
            "Cube vs SQL", "pass" if d["pass"] else "fail", d["pass"],
            f'<b>{d["shapes"]}</b> randomized filtered shapes computed through '
            f'the cube mask path and by SQL over the contribution table; '
            f'worst relative disagreement <b class="mono">'
            f'{d["worst_rel_err"]:.2e}</b> (tolerance {d["tolerance"]:.0e}). '
            f'The check that would have caught the Phase&nbsp;2a mask bug the '
            f'day it was written.'))
    if "explanation_invariants" in hard:
        e = hard["explanation_invariants"]
        g.append(gate_row(
            "Explanations", "pass" if e["pass"] else "fail", e["pass"],
            f'<b>{e["explanations_checked"]}</b> rendered explanations: no '
            f'§12.3 banned vocabulary anywhere, and the lead phrase is '
            f'position-unique — the duplicated-sentence defect this panel '
            f'caught by hand is checked by machine now.'))
    worst = min(shares.values()) if shares else 0.0
    g.append(gate_row(
        "Rank stability", "pass" if rs["pass"] else "fail", rs["pass"],
        f'Worst persona holds its top ten in <b>{pct(worst)}</b> of replicate '
        f'rankings (gate: {esc(rs["gate"])}). '
        f'{len(shares)} personas evaluable, {len(skipped)} skipped for too few '
        f'ranked metros.'))
    g.append(gate_row(
        "Group-quarters artifacts", "pass" if aa["pass"] else "fail", aa["pass"],
        f'<b>{len(aa["top10_appearances"])}</b> appearances by the '
        f'{len(aa["watchlist"])}-metro college/military/prison watchlist in any '
        f'persona top ten. Rule: {esc(aa["rule"])}.'))
    out.append('<section><h2>Hard gates</h2><div class="gates">'
               + "".join(g) + "</div></section>")

    # Soft checks
    tau_rows = "".join(
        f'<tr><td class="mono">{esc(k)}</td>'
        f'<td class="num mono">{v:.3f}</td></tr>' for k, v in taus.items())
    corr_rows = "".join(
        f'<tr><td>{esc(k.replace("_", " "))}</td>'
        f'<td class="num mono">{v["pearson"]:+.3f}</td>'
        f'<td class="num mono">{v["spearman"]:+.3f}</td></tr>'
        for k, v in ec["correlations"].items())
    out.append(f"""<section><h2>Soft checks</h2>
<h3>Weight sensitivity — Kendall's τ against baseline (target ≥ {ws['target']})</h3>
<p class="note">Every pillar perturbed ±20%. If one pillar were secretly the
whole model, its τ would collapse. Range here:
<span class="mono">{min(taus.values()):.3f}–{max(taus.values()):.3f}</span>.</p>
<div class="scroller"><table><thead><tr><th>Perturbation</th>
<th class="num">τ</th></tr></thead><tbody>{tau_rows}</tbody></table></div>
<h3>External correlation — {ec['n_metros']} ranked metros</h3>
<p class="note">{esc(ec['framing'])}</p>
<div class="scroller"><table><thead><tr><th>Pair</th><th class="num">Pearson</th>
<th class="num">Spearman</th></tr></thead><tbody>{corr_rows}</tbody></table></div>
<p class="note"><b>Source finding.</b> {esc(ec['b12007_finding'])}</p>
</section>""")

    # Review rows
    out.append('<section id="review"><h2>The 33 rows</h2>'
               f'<p class="note">{esc(fv["note"])}. Three things to look for: '
               'whether the <b>magnitude</b> is plausible for that metro, '
               'whether the stated edge actually follows from the '
               '<b>attribution</b>, and whether the <b>sentence itself</b> '
               'reads like something you would publish.</p>'
               '<div class="bar"><span class="count" id="progress">'
               '0 reviewed · 0 flagged</span>'
               '<button type="button" id="copy">Copy review notes</button></div>')

    by_persona: dict[str, list] = {}
    for r in rows:
        by_persona.setdefault(r["persona"], []).append(r)

    idx = 0
    for persona, prows in by_persona.items():
        out.append(f'<div class="persona"><h3>{esc(persona.replace("_", " "))}</h3>'
                   f'<span class="key mono">{len(prows)} rows</span></div>')
        for r in prows:
            idx += 1
            lines = "".join(f"<div>{esc(l)}</div>"
                            for l in r["explanation"].split("\n") if l.strip())
            chips = "".join(f'<span class="chip warn">{esc(f)}</span>'
                            for f in (r.get("flags") or []))
            chips += (f'<span class="chip">top pillar: {esc(r["top_pillar"])}</span>'
                      f'<span class="chip mono">CBSA {esc(r["cbsa"])}</span>')
            # the magnitude check needs the magnitudes: pool, served margin, n
            mag = ""
            if "pool" in r:
                mag = (f'<span class="chip mono">pool {r["pool"]:,}'
                       f' · margin at least {r["pool_moe"]:,}'
                       f' · n {r["n_unweighted"]:,}</span>')
            out.append(f"""<div class="row" data-id="{idx}"
 data-persona="{esc(persona)}" data-cbsa="{esc(r['cbsa'])}" data-rank="{r['rank']}">
<div class="gutter"><span class="rank">#{r['rank']}</span>
<span class="sub mono">{r['score']:.1f}</span>
<span class="sub">score</span></div>
<div><div class="expl">{lines}</div>
<div class="chips">{mag}{chips}</div>
<div class="controls">
<button type="button" class="ok" id="ok{idx}" aria-pressed="false">Reads right</button>
<button type="button" class="flag" id="flag{idx}" aria-pressed="false">Flag this</button>
<input type="text" id="note{idx}" placeholder="note (optional)">
</div></div></div>""")
    out.append("</section>")

    out.append("""<footer>
<p><b>The two gaps this page named in Phase 2a are closed.</b>
Every row now carries its pool, served margin and n, so the magnitude check
can be done from here. The duplicated lead sentence was diagnosed — the
committed panel had been rendered by a pre-commit renderer that keyed
phrasing on the magnitude bucket alone, and was never re-rendered after the
committed template fixed it — so this report is now stamped with the git
state that produced it, and a hard gate asserts the lead phrase is
position-unique in every rendered explanation.</p>
</footer></div>""")

    out.append("""<script>
(function(){
  var KEY = 'dsa-review-' + document.querySelector('.meta b').textContent.trim();
  var state = {};
  try { state = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) {}
  function save(){ try { localStorage.setItem(KEY, JSON.stringify(state)); }
                   catch (e) {} }
  function progress(){
    var done = 0, flagged = 0;
    Object.keys(state).forEach(function(k){
      if (state[k].v) done++;
      if (state[k].v === 'flag') flagged++;
    });
    document.getElementById('progress').textContent =
      done + ' of ' + document.querySelectorAll('.row').length +
      ' reviewed · ' + flagged + ' flagged';
  }
  document.querySelectorAll('.row').forEach(function(row){
    var id = row.dataset.id;
    var ok = row.querySelector('.ok'), flag = row.querySelector('.flag');
    var note = row.querySelector('input');
    var s = state[id] || (state[id] = {v: null, n: ''});
    function paint(){
      ok.setAttribute('aria-pressed', s.v === 'ok');
      flag.setAttribute('aria-pressed', s.v === 'flag');
    }
    note.value = s.n || '';
    paint();
    ok.addEventListener('click', function(){
      s.v = s.v === 'ok' ? null : 'ok'; paint(); save(); progress(); });
    flag.addEventListener('click', function(){
      s.v = s.v === 'flag' ? null : 'flag'; paint(); save(); progress(); });
    note.addEventListener('input', function(){ s.n = note.value; save(); });
  });
  progress();
  document.getElementById('copy').addEventListener('click', function(){
    var meta = document.querySelectorAll('.meta b');
    var out = ['# Face-validity review — build ' + meta[0].textContent.trim() +
               ', model ' + meta[1].textContent.trim(), ''];
    var flagged = [], noted = [];
    document.querySelectorAll('.row').forEach(function(row){
      var s = state[row.dataset.id] || {};
      var label = row.dataset.persona + ' · CBSA ' + row.dataset.cbsa +
                  ' · #' + row.dataset.rank;
      if (s.v === 'flag') flagged.push('- ' + label + (s.n ? ' — ' + s.n : ''));
      else if (s.n) noted.push('- ' + label + ' — ' + s.n);
    });
    out.push('Flagged: ' + flagged.length + ' of ' +
             document.querySelectorAll('.row').length);
    if (flagged.length) { out.push('', '## Flagged', ''); out = out.concat(flagged); }
    if (noted.length) { out.push('', '## Notes on rows that read right', '');
                        out = out.concat(noted); }
    var text = out.join('\\n');
    var btn = document.getElementById('copy');
    function done(){ btn.textContent = 'Copied'; 
      setTimeout(function(){ btn.textContent = 'Copy review notes'; }, 1600); }
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, done);
    else { window.prompt('Copy:', text); }
  });
})();
</script>""")
    return "".join(out)


SKELETON = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>{title}</title>{fonts}<style>{css}</style></head>'
            '<body>{inner}</body></html>')


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    src = Path(argv[0])
    rep = json.loads(src.read_text())
    inner = build_inner(rep)
    title = "Face-Validity Review"
    if "--artifact" in argv:
        dest = Path(argv[argv.index("--artifact") + 1])
        dest.write_text(f"<title>{title}</title>{FONTS}<style>{CSS}</style>"
                        + inner + "\n")
    else:
        dest = src.with_suffix(".html")
        dest.write_text(SKELETON.format(title=title, fonts=FONTS, css=CSS,
                                        inner=inner) + "\n")
    print(f"wrote {dest} ({dest.stat().st_size:,} bytes, "
          f"{len(rep['soft']['face_validity']['rows'])} review rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
