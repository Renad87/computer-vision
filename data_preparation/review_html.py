"""Click-through review page for the near-duplicate decisions (a local HTML file, no server, no model).

    python -m data_preparation.review_html --workdir <W>   # writes <W>/datasets/review/review.html

Open review.html in a browser, enter your reviewer id, click "same image" or "different" for every pair, then
"Download decisions CSV" and save it as <W>/datasets/review/near_duplicate_decisions.csv (same columns as
near_duplicate_candidates.csv). Re-run the v1 build afterwards. Images load from ../images/ (run layout first).
"""
import argparse
import json
import os
import sys

from .common import PACKAGE_ROOT, read_csv, write_text
from .neardup import CANDIDATE_FIELDS

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Near-duplicate review</title>
<style>
body{font-family:Segoe UI,Arial,sans-serif;margin:16px;background:#f6f7f9;color:#1d2330}
.bar{position:sticky;top:0;background:#fff;padding:10px;border:1px solid #ccd;border-radius:6px;z-index:2}
.pair{display:flex;gap:12px;align-items:flex-start;background:#fff;margin:10px 0;padding:10px;border:1px solid #dde;
border-radius:6px}.pair.done{border-color:#7a7}.pair img{width:260px;height:200px;object-fit:contain;background:#eee}
.meta{font-size:13px;line-height:1.6}button{padding:6px 12px;margin-right:6px;cursor:pointer}
button.sel{background:#2d6cdf;color:#fff}
</style></head><body>
<div class="bar">Reviewer id: <input id="rev" placeholder="e.g. shaden"> &nbsp; Date: <input id="date" type="date">
&nbsp; <span id="count"></span> &nbsp; <button onclick="dl()">Download decisions CSV</button>
<div style="font-size:12px;color:#666">same image = the same photograph (also cropped, resized or re-compressed).
different = two different photographs, even of the same subject.</div></div>
<div id="list"></div>
<script>
const FIELDS = __FIELDS__; const PAIRS = __PAIRS__;
const d = {};
function render(){const L=document.getElementById('list');L.innerHTML='';
PAIRS.forEach(p=>{const div=document.createElement('div');div.className='pair'+(d[p.pair_no]?' done':'');
div.innerHTML=`<img src="../images/${p.image_path_a.replace('datasets/images/','')}"><img src="../images/${p.image_path_b.replace('datasets/images/','')}">
<div class="meta"><b>pair ${p.pair_no}</b><br>A ${p.image_id_a} [${p.split_a}]<br>B ${p.image_id_b} [${p.split_b}]<br>
pHash ${p.phash_hamming} · CLIP ${p.clip_cosine} (${p.nominated_by})<br>
<button class="${d[p.pair_no]==='same_image'?'sel':''}" onclick="set(${p.pair_no},'same_image')">same image</button>
<button class="${d[p.pair_no]==='different'?'sel':''}" onclick="set(${p.pair_no},'different')">different</button></div>`;
L.appendChild(div)});document.getElementById('count').textContent=`${Object.keys(d).length} / ${PAIRS.length} decided`}
function set(n,v){d[n]=v;render()}
function esc(v){v=String(v??'');return /[",\\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v}
function dl(){const rev=document.getElementById('rev').value.trim(),date=document.getElementById('date').value;
if(!rev||!date){alert('Enter your reviewer id and the date first');return}
const rows=[FIELDS.join(',')];PAIRS.forEach(p=>{const r=Object.assign({},p);if(d[p.pair_no]){r.decision=d[p.pair_no];
r.reviewer_id=rev;r.date=date}else{r.decision='';r.reviewer_id='';r.date=''}rows.push(FIELDS.map(f=>esc(r[f])).join(','))});
const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([rows.join('\\n')+'\\n'],{type:'text/csv'}));
a.download='near_duplicate_decisions.csv';a.click()}
PAIRS.forEach(p=>{if(p.decision)d[p.pair_no]=p.decision});render();
</script></body></html>"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workdir", default=PACKAGE_ROOT)
    a = ap.parse_args(argv)
    w = os.path.abspath(a.workdir)
    rows = read_csv(os.path.join(w, "datasets", "review", "near_duplicate_decisions.csv"))
    for r in rows:
        r["pair_no"] = int(r["pair_no"])
    html = PAGE.replace("__FIELDS__", json.dumps(CANDIDATE_FIELDS)).replace("__PAIRS__", json.dumps(rows))
    write_text(os.path.join(w, "datasets", "review", "review.html"), html)
    print(f"{len(rows)} pairs -> datasets/review/review.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
