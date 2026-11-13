#!/usr/bin/env python3
"""
AGRI-SHIELD AI - local desktop application (M7).

Deliberately built on Python's standard library http.server with all CSS and
JavaScript inlined. No Flask, no Gradio, no CDN, no web fonts.

Why that matters: M8 requires the system to work with no network. A UI that
pulls a font or a JS bundle from a CDN fails that quietly, and a jury can catch
it with the network cable out. This page makes ZERO external requests, and that
is verifiable:

    grep -c "http://\\|https://" application/app.py     # expect 0 in served HTML

Run:
    python application/app.py --checkpoint runs/tomato4_scratch/best.pt
Then open http://127.0.0.1:8000 in any browser.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import sys
import tempfile
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "knowledge_base"))
sys.path.insert(0, str(ROOT / "llama_advisory"))
sys.path.insert(0, str(ROOT / "disease_detection" / "inference"))

STATE: dict = {}
HISTORY: list = []
HISTORY_FILE = ROOT / "logs" / "diagnosis_history.json"

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AGRI-SHIELD AI</title><style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#0f1510;color:#e8f0e6;padding:24px;line-height:1.5}
.wrap{max-width:860px;margin:0 auto}
h1{font-size:22px;margin-bottom:2px}
.sub{color:#8aa682;font-size:13px;margin-bottom:20px}
.card{background:#172017;border:1px solid #2b3a29;border-radius:10px;padding:18px;margin-bottom:16px}
.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
button{background:#2f6b33;color:#fff;border:0;border-radius:7px;padding:10px 18px;font-size:14px;cursor:pointer}
button:hover{background:#3a8440}button:disabled{background:#3a463a;cursor:not-allowed}
.lang button{background:#22302180;border:1px solid #2b3a29;padding:7px 16px}
.lang button.on{background:#2f6b33;border-color:#2f6b33}
input[type=file]{color:#b7c9b2;font-size:13px}
#prev{max-width:260px;border-radius:8px;margin-top:12px;display:none}
.k{color:#8aa682;font-size:12px;text-transform:uppercase;letter-spacing:.5px}
.v{font-size:18px;font-weight:600;margin-bottom:12px}
.bar{height:7px;background:#243024;border-radius:4px;overflow:hidden;margin:6px 0 12px}
.bar i{display:block;height:100%;background:#4e9c54}
.pill{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600}
.abstain{background:#6b4a1f;color:#ffd9a0}.prescriptive{background:#2f6b33;color:#d6f5d8}
.advice{background:#121a12;border-left:3px solid #4e9c54;padding:14px;border-radius:0 7px 7px 0;margin-top:10px;white-space:pre-wrap}
.warn{background:#3a2416;border-left:3px solid #c98434;padding:12px;border-radius:0 7px 7px 0;font-size:13px;margin-top:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
td,th{padding:7px 6px;border-bottom:1px solid #243024;text-align:left}
th{color:#8aa682;font-weight:500;font-size:11px;text-transform:uppercase}
.muted{color:#8aa682;font-size:12px}
.err{background:#3a1a1a;border-left:3px solid #c05050;padding:12px;border-radius:0 7px 7px 0}
</style></head><body><div class="wrap">
<h1>AGRI-SHIELD AI</h1>
<div class="sub">Offline crop disease detection and farmer advisory &middot; runs entirely on this machine</div>

<div class="card">
  <div class="row lang" style="margin-bottom:14px">
    <span class="k">Language</span>
    <button id="bEn" class="on" onclick="setLang('en')">English</button>
    <button id="bTa" onclick="setLang('ta')">&#2980;&#2990;&#3007;&#2996;&#3021;</button>
  </div>
  <div class="row">
    <input type="file" id="f" accept="image/*" onchange="preview()">
    <button id="go" onclick="go()" disabled>Diagnose</button>
  </div>
  <img id="prev">
</div>

<div id="out"></div>

<div class="card">
  <div class="k" style="margin-bottom:10px">Previous diagnoses</div>
  <div id="hist"><span class="muted">None yet.</span></div>
</div>
</div><script>
let lang='en', file=null;
function setLang(l){lang=l;
  document.getElementById('bEn').className = l==='en'?'on':'';
  document.getElementById('bTa').className = l==='ta'?'on':'';
  if(window.lastResult) render(window.lastResult);}
function preview(){const i=document.getElementById('f');
  if(!i.files.length)return; file=i.files[0];
  const r=new FileReader(); r.onload=e=>{const p=document.getElementById('prev');
    p.src=e.target.result; p.style.display='block';}; r.readAsDataURL(file);
  document.getElementById('go').disabled=false;}
function go(){if(!file)return;
  const go_=document.getElementById('go'); go_.disabled=true; go_.textContent='Working...';
  const r=new FileReader();
  r.onload=e=>{fetch('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({image:e.target.result,lang:lang})})
    .then(x=>x.json()).then(j=>{window.lastResult=j; render(j); hist();
      go_.disabled=false; go_.textContent='Diagnose';})
    .catch(err=>{document.getElementById('out').innerHTML=
      '<div class="card err">Request failed: '+err+'</div>';
      go_.disabled=false; go_.textContent='Diagnose';});};
  r.readAsDataURL(file);}
function esc(s){return String(s).replace(/[<>&]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]));}
function render(j){const o=document.getElementById('out');
  if(j.error){o.innerHTML='<div class="card err">'+esc(j.error)+'</div>';return;}
  const c=j.classification, s=j.severity, a=j.advisory, pct=(c.confidence*100).toFixed(1);
  let h='<div class="card">';
  h+='<div class="k">Detected</div><div class="v">'+esc(c.display)+'</div>';
  h+='<div class="k">Confidence</div><div class="bar"><i style="width:'+pct+'%"></i></div>';
  h+='<div class="v">'+pct+'% <span class="pill '+a.advisory_mode+'">'+a.advisory_mode+'</span></div>';
  h+='<div class="k">Estimated severity</div><div class="v">'+esc(s.severity)+
     (s.lesion_fraction!==null?' <span class="muted">('+(s.lesion_fraction*100).toFixed(1)+'% lesion area)</span>':'')+'</div>';
  h+='<div class="k">Advisory</div><div class="advice">'+esc(j.advice_text)+'</div>';
  if(j.is_mock) h+='<div class="warn"><b>Mock advisory.</b> Generated by a placeholder, '+
    'not by Llama on ExecuTorch. Mandatory requirements M3 and M4 are not satisfied by this output.</div>';
  if(a.advisory_mode==='abstain') h+='<div class="warn"><b>No treatment recommended.</b> '+
    esc(a.reason)+'. Confirm with your local agricultural extension officer.</div>';
  h+='<div class="k" style="margin-top:14px">Top predictions</div><table><tr><th>Class</th><th>Probability</th></tr>';
  c.top3.forEach(t=>{h+='<tr><td>'+esc(t.label)+'</td><td>'+(t.p*100).toFixed(1)+'%</td></tr>';});
  h+='</table></div>'; o.innerHTML=h;}
function hist(){fetch('/history').then(r=>r.json()).then(j=>{
  if(!j.length){return;} let h='<table><tr><th>Time</th><th>Result</th><th>Conf</th><th>Severity</th><th>Mode</th></tr>';
  j.slice().reverse().forEach(e=>{h+='<tr><td class="muted">'+esc(e.time)+'</td><td>'+esc(e.display)+
    '</td><td>'+(e.confidence*100).toFixed(0)+'%</td><td>'+esc(e.severity)+'</td><td>'+esc(e.mode)+'</td></tr>';});
  document.getElementById('hist').innerHTML=h+'</table>';});}
hist();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif self.path == "/history":
            self._send(200, json.dumps(HISTORY[-25:], ensure_ascii=False))
        elif self.path == "/health":
            self._send(200, json.dumps({"ok": True, "classes": STATE["classes"],
                                        "backend": STATE["backend"].name}))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path != "/analyze":
            return self._send(404, json.dumps({"error": "not found"}))
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n))
            raw = req["image"].split(",", 1)[-1]
            blob = base64.b64decode(raw)
            lang = req.get("lang", "en")

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                tf.write(blob)
                tmp = Path(tf.name)
            try:
                result = self._analyse(tmp, lang)
            finally:
                tmp.unlink(missing_ok=True)
            self._send(200, json.dumps(result, ensure_ascii=False))
        except Exception as e:
            traceback.print_exc()
            self._send(500, json.dumps({"error": f"{type(e).__name__}: {e}"}))

    def _analyse(self, path: Path, lang: str) -> dict:
        from predict import analyse
        from advisor import AdvisoryRequest, advise

        out = analyse(STATE["model"], STATE["classes"], STATE["tf"], path,
                      STATE["device"], STATE["kb"], STATE["threshold"], lang)
        c, s, a = out["classification"], out["severity"], out["advisory"]

        resp = advise(STATE["kb"],
                      AdvisoryRequest(c["class_label"], c["confidence"],
                                      s["severity"], lang, STATE["threshold"]),
                      STATE["backend"])

        pretty = c["class_label"].replace("___", " - ").replace("_", " ")
        ctx = a["prompt_context"]
        display = ctx.get("disease", pretty) if lang == "ta" else pretty

        HISTORY.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "display": display, "confidence": c["confidence"],
            "severity": s["severity"], "mode": a["advisory_mode"],
        })
        try:
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            HISTORY_FILE.write_text(json.dumps(HISTORY, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
        except Exception:
            pass

        c["display"] = display
        return {"classification": c, "severity": s, "advisory": a,
                "advice_text": resp.text, "is_mock": resp.is_mock,
                "guard": resp.guard}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--kb", default=None)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--threshold", type=float, default=0.70)
    ap.add_argument("--selftest", action="store_true",
                    help="start, hit the endpoints once, print results, exit")
    args = ap.parse_args()

    import torch
    from predict import load_model, preprocess
    from retrieval import KnowledgeBase, DEFAULT_KB
    from advisor import MockBackend

    device = torch.device("cpu")
    model, classes, ck = load_model(Path(args.checkpoint), device)
    STATE.update(model=model, classes=classes, device=device,
                 tf=preprocess(ck.get("img_size", 96)),
                 kb=KnowledgeBase(Path(args.kb) if args.kb else DEFAULT_KB),
                 threshold=args.threshold, backend=MockBackend())

    print(f"classes: {classes}")
    print(f"backend: {STATE['backend'].name} (MOCK - not Llama/ExecuTorch)")

    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    if args.selftest:
        import threading, urllib.request
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{args.port}"
        page = urllib.request.urlopen(base + "/").read().decode()
        ext = page.count("https://") + page.count("http://")
        print(f"\nGET /         {len(page)} bytes, external URLs in page: {ext}")
        print(f"GET /health   {urllib.request.urlopen(base+'/health').read().decode()}")
        srv.shutdown()
        return 0 if ext == 0 else 1

    print(f"\nAGRI-SHIELD AI running at http://127.0.0.1:{args.port}")
    print("Ctrl+C to stop. No external requests are made.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    sys.exit(main() or 0)
